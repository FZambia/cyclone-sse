# coding:utf-8
import sys
import uuid

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log

import cyclone.redis
from cyclone_sse.amqp import AmqpSubscriberFactory
from cyclone_sse.amqp import AmqpSubscriberProtocol


class Broker(object):
    """
    base class, which goal is to keep state of connections and to
    broadcast new messages to all clients of certain channel.
    """
    def __init__(self, settings):
        self._source = None
        self._channels = {}
        self._cache = []
        self._cache_size = 200
        self._clients = []
        self._settings = settings
        self.setup(self._settings)

    def setup(self, settings):
        self.connect(settings)
        # ping clients periodically to keep their connections alive
        self.lc = task.LoopingCall(self.ping)
        self.lc.start(15)

    def connect(self, settings):
        raise NotImplementedError('please, provide implementation for connect method')

    def _subscribe(self, channel):
        if channel not in self._channels:
            self._channels[channel] = []
            log.msg("Subscribing entire server to %s" % channel)
            if self._source:
                self.subscribe(channel)

    def _unsubscribe(self, channel):
        log.msg('Unsubscribing entire server from channel %s' % channel)
        try:
            del self._channels[channel]
        except KeyError:
            pass

    def add_client(self, client):
        self._clients.append(client)

        channels = client.get_channels()
        if not channels:
            raise cyclone.web.HTTPError(400)
        for channel in channels:
            self._subscribe(channel)

            if client not in self._channels[channel]:
                self._channels[channel].append(client)

            log.msg("Client %s subscribed to %s" % (client.request.remote_ip, channel))

        self.send_cache(client)

    def remove_client(self, client):
        self._clients.remove(client)

        empty = []
        for channel, clients in self._channels.iteritems():
            if client in clients:
                log.msg('Unsubscribing client from channel %s' % channel)
                clients.remove(client)
            if len(clients) == 0:
                empty.append(channel)

        for channel in empty:
            self._unsubscribe(channel)

    def subscribe(self, channel):
        raise NotImplementedError('please, provide implementation for subscribe method')

    def unsubscribe(self, channel):
        raise NotImplementedError('please, provide implementation for unsubscribe method')

    def ping(self):
        for client in self._clients:
            client.sendPing()
            if 'X-Requested-With' in client.request.headers:
                client.flush()
                client.finish()

    def broadcast(self, pattern, channel, message):
        """
        pass
        """
        if self.is_pattern_blocked(pattern):
            return True
        clients = self._channels[channel]
        args = (str(len(clients)), pattern, channel, message)
        log.msg('BROADCASTING to %s clients: pattern: %s, channel: %s, message: %s' % args)
        if clients:
            for client in clients:
                self.send_event(client, channel, message)

    def is_pattern_blocked(self, pattern):
        return False

    def send_event(self, client, channel, message, eid=None):
        if eid is None:
            eid = str(uuid.uuid4())
            self.update_cache(eid, channel, message)
        client.sendEvent(message, eid=eid)
        if 'X-Requested-With' in client.request.headers:
            client.flush()
            client.finish()

    def send_cache(self, client):
        last_event_id = client.request.headers.get('Last-Event-Id', None)
        if last_event_id:
            i = 0
            for i, msg in enumerate(self._cache, 1):
                if msg['eid'] == last_event_id:
                    break

            for item in self._cache[i:]:
                if item['channel'] in client.get_channels():
                    self.send_event(client, item['channel'], item['message'], eid=item['eid'])

    def update_cache(self, eid, channel, message):
        self._cache.append({
            'eid': eid,
            'channel': channel,
            'message': message
        })
        if len(self._cache) > self._cache_size:
            self._cache = self._cache[-self._cache_size:]


class RedisBroadcastProtocol(cyclone.redis.SubscriberProtocol):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        self.factory.broker.broadcast(pattern, channel, message)

    def connectionMade(self):
        self.factory.broker._source = self
        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self.factory.broker._channels:
            self.factory.broker._subscribe(channel)

    def connectionLost(self, why):
        self.factory.broker._source = None


class RedisBroker(Broker):
    """
    listens Redis channels and broadcasts to clients
    """
    def connect(self, settings):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.broker = self
        qf.maxDelay = 20
        qf.protocol = RedisBroadcastProtocol
        reactor.connectTCP(settings["redis-host"], settings["redis-port"], qf) 

    def is_pattern_blocked(self, pattern):
        return pattern in ['unsubscribe', 'subscribe']

    def subscribe(self, channel):
        if "*" in channel:
            self._source.psubscribe(channel)
        else:
            self._source.subscribe(channel)

    def unsubscribe(self, channel):
        if "*" in channel:
            self._source.punsubscribe(channel)
        else:
            self._source.unsubscribe(channel)


class AmqpBroadcastProtocol(AmqpSubscriberProtocol):
    def messageReceived(self, pattern, channel, message):
        # broadcast this message to all HTTP clients
        self.factory.broker.broadcast(pattern, channel, message)

    def channelReady(self):
        self.factory.broker._source = self
        # If we lost connection during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self.factory.broker._channels:
            self.factory.broker._subscribe(channel)   

    def connectionLost(self, why):
        self.factory.broker._source = None
        AmqpSubscriberProtocol.connectionLost(self, why)


class AmqpBroker(Broker):
    def connect(self, settings):
        # PubSub client connection
        qf = AmqpSubscriberFactory()
        qf.broker = self
        qf.protocol = AmqpBroadcastProtocol
        reactor.connectTCP("127.0.0.1", 5672, qf)

    def subscribe(self, channel):
        self._source.consume(channel)

    def unsubscribe(self, channel):
        self._source.cancel(channel)
