# coding: utf-8
import sys

import cyclone.web
import cyclone.escape
import cyclone.redis
import cyclone.sqlite
from cyclone.sse import SSEHandler

from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log


class RedisMixin(object):
    _source = None
    _channels = {}
    _mbuffer = ""

    @classmethod
    def setup(self, host, port, dbid, poolsize):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
        reactor.connectTCP(host, port, qf)

        # Normal client connection
        RedisMixin._source = cyclone.redis.lazyConnectionPool(host, port, dbid, poolsize)

    def subscribe(self, client):
        channels = self.get_channels()
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
                (self.request.remote_ip, channel))

    def unsubscribe(self, client):
        for channel, clients in RedisMixin._channels.iteritems():
            if client in clients:
                log.msg('Unsubscribing client from channel %s' % channel)
                clients.remove(client)

    def broadcast(self, pattern, channel, message):
        print 'pattern: ', pattern
        print 'channel: ', channel
        print 'message: ', message
        print RedisMixin._channels
        clients = RedisMixin._channels[channel]
        #chunks = (self._mbuffer + message.replace("\x1b[J", "")).split("\x1b[H")
        for client in clients:
            client.sendEvent(str(message)) 


class QueueProtocol(cyclone.redis.SubscriberProtocol, RedisMixin):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        RedisMixin.broadcast(self, pattern, channel, message)

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


class BroadcastHandler(SSEHandler, RedisMixin):

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
