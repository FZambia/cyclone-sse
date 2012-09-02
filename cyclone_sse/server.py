# coding: utf-8
#
# Copyright 2012 Alexandr Emelin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
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
        log.msg('ping client %s' % self.request.remote_ip)
        self.transport.write(": %s\n\n" % 'sse ping')


class RedisMixin(object):
    _source = None
    _channels = {}
    _cache = []
    _cache_size = 200
    _clients = []

    @classmethod
    def setup(cls, host, port, dbid, poolsize):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
        reactor.connectTCP(host, port, qf)

        # Normal client connection
        cls._source = cyclone.redis.lazyConnectionPool(host, port, dbid, poolsize)

        # ping clients periodically to keep their connections alive
        cls.lc = task.LoopingCall(cls.ping)
        cls.lc.start(15)

    @classmethod
    def subscribe(cls, client):
        cls._clients.append(client)

        channels = client.get_channels()
        if not channels:
            raise cyclone.web.HTTPError(400)
        for channel in channels:
            if channel not in RedisMixin._channels:
                cls._channels[channel] = []
                log.msg("Subscribing entire server to %s" % channel)
                if "*" in channel:
                    cls._source.psubscribe(channel)
                else:
                    cls._source.subscribe(channel)

            if client not in cls._channels[channel]:
                cls._channels[channel].append(client)

        log.msg("Client %s subscribed to %s" % \
                (client.request.remote_ip, channel))
        
        cls.send_cache(client)

    @classmethod
    def unsubscribe(cls, client):
        empty = []
        for channel, clients in cls._channels.iteritems():
            if client in clients:
                log.msg('Unsubscribing client from channel %s' % channel)
                clients.remove(client)
            if len(clients) == 0:
                empty.append(channel)

        cls._clients.remove(client)

        for channel in empty:
            log.msg('Unsubscribing entire server from channel %s' % channel)
            if "*" in channel:
                cls._source.punsubscribe(channel)
            else:
                cls._source.unsubscribe(channel)
            del cls._channels[channel]

    @classmethod
    def ping(cls):
        for client in cls._clients:
            client.sendPing()
            if 'X-Requested-With' in client.request.headers:
                client.flush()
                client.finish()

    @classmethod
    def broadcast(cls, pattern, channel, message):
        if pattern == 'unsubscribe' or pattern == 'subscribe':
            return True
        clients = cls._channels[channel]
        if clients:
            args = (str(len(clients)), pattern, channel, message)
            log.msg('BROADCASTING to %s clients: pattern: %s, channel: %s, message: %s' % args)
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


class QueueProtocol(cyclone.redis.SubscriberProtocol):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        RedisMixin.broadcast(pattern, channel, message)

    def connectionMade(self):
        RedisMixin._source = self

        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in RedisMixin._channels:
            if "*" in channel:
                self.psubscribe(channel)
            else:
                self.subscribe(channel)

    def connectionLost(self, why):
        RedisMixin._source = None


class BroadcastHandler(ExtendedSSEHandler):

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
        #headers = self._generate_headers()
        #self.write(headers)
        log.msg(self.request.headers)
        self.write(':\n')
        self.flush()
        RedisMixin.subscribe(self)

    def unbind(self):
        RedisMixin.unsubscribe(self)


class App(cyclone.web.Application):
    def __init__(self, settings):
        handlers = [
            (r"/", BroadcastHandler)
        ]
        RedisMixin.setup(settings["redis-host"],
                         settings["redis-port"],
                         settings["redis-dbid"],
                         settings["redis-pool"])
        cyclone.web.Application.__init__(self, handlers)

