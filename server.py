# coding: utf-8
import sys
import uuid

import cyclone.web
import cyclone.redis
from cyclone.sse import SSEHandler

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log


class ExtendedSSEHandler(SSEHandler):
    def sendPing(self):
        # send comment line to keep connection with client opened as mentioned here:
        # https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
        print 'ping'
        self.transport.write(": %s\n\n" % 'sse ping')


class RedisMixin(object):
    _source = None
    _channels = {}
    _cache = []
    _cache_size = 200
    _clients = []
    #_mbuffer = ""

    @classmethod
    def setup(cls, host, port, dbid, poolsize):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
        reactor.connectTCP(host, port, qf)

        # Normal client connection
        cls._source = cyclone.redis.lazyConnectionPool(host, port, dbid, poolsize)

        # 
        cls.lc = task.LoopingCall(cls.ping)
        cls.lc.start(15)

    def subscribe(self, client):
        RedisMixin._clients.append(client)

        channels = client.get_channels()
        if not channels:
            raise cyclone.web.HTTPError(400)
        print RedisMixin._channels
        for channel in channels:
            if channel not in RedisMixin._channels:
                RedisMixin._channels[channel] = []
                log.msg("Subscribing entire server to %s" % channel)
                if "*" in channel:
                    RedisMixin._source.psubscribe(channel)
                else:
                    RedisMixin._source.subscribe(channel)

            if client not in RedisMixin._channels[channel]:
                RedisMixin._channels[channel].append(client)

        log.msg("Client %s subscribed to %s" % \
                (client.request.remote_ip, channel))
        
        RedisMixin.send_cache(client)


    def unsubscribe(self, client):
        empty = []
        for channel, clients in RedisMixin._channels.iteritems():
            if client in clients:
                log.msg('Unsubscribing client from channel %s' % channel)
                clients.remove(client)
            if len(clients) == 0:
                empty.append(channel)

        RedisMixin._clients.remove(client)

        for channel in empty:
            log.msg('Unsubscribing entire server from channel %s' % channel)
            if "*" in channel:
                RedisMixin._source.punsubscribe(channel)
            else:
                RedisMixin._source.unsubscribe(channel)
            del RedisMixin._channels[channel]

    @classmethod
    def ping(cls):
        for client in cls._clients:
            client.sendPing()
            if 'X-Requested-With' in client.request.headers:
                client.flush()
                client.finish()

    @classmethod
    def broadcast(cls, pattern, channel, message):
        print 'pattern: ', pattern
        print 'channel: ', channel
        print 'message: ', message
        if pattern == 'unsubscribe' or pattern == 'subscribe':
            return True
        print cls._channels
        clients = cls._channels[channel]
        #chunks = (self._mbuffer + message.replace("\x1b[J", "")).split("\x1b[H")
        for client in clients:
            cls.send_event(client, channel, message)

    @classmethod
    def send_event(cls, client, channel, message, eid=None):
        if eid is None:
            eid = str(uuid.uuid4())
            cls.update_cache(eid, channel, message)
        client.sendEvent(message, eid=eid)
        if 'X-Requested-With' in client.request.headers:
            client.flush()
            client.finish()

    @classmethod
    def send_cache(cls, client):
        last_event_id = client.request.headers.get('Last-Event-Id', None)
        if last_event_id:
            i = 0
            for i, msg in enumerate(cls._cache, 1):
                if msg['eid'] == last_event_id:
                    break

            for item in cls._cache[i:]:
                if item['channel'] in client.get_channels():
                    cls.send_event(client, item['channel'], item['message'], eid=item['eid'])

    @classmethod
    def update_cache(cls, eid, channel, message):
        cls._cache.append({
            'eid': eid,
            'channel': channel,
            'message': message
        })
        if len(cls._cache) > cls._cache_size:
            cls._cache = cls._cache[-cls._cache_size:]


class QueueProtocol(cyclone.redis.SubscriberProtocol, RedisMixin):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        RedisMixin.broadcast(pattern, channel, message)

    def connectionMade(self):
        RedisMixin._source = self

        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self._channels:
            if "*" in channel:
                self.psubscribe(channel)
            else:
                self.subscribe(channel)

    def connectionLost(self, why):
        RedisMixin._source = None


class BroadcastHandler(ExtendedSSEHandler, RedisMixin):

    sse_headers = {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    }

    def initialize(self):
        for name, value in self.sse_headers.iteritems():
            self.set_header(name, value)

    def get_channels(self):
        channels = self.get_arguments('channels[]')
        return channels

    def bind(self):
        import pprint
        pprint.pprint(self.request.headers)
        print 'binding'
        headers = self._generate_headers()
        self.write(headers)
        self.flush()
        self.subscribe(self)

    def unbind(self):
        print 'unbinding'
        self.unsubscribe(self)


RedisMixin.setup("127.0.0.1", 6379, 0, 10)
Application = lambda: cyclone.web.Application([(r"/", BroadcastHandler)])
