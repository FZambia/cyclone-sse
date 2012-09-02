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

    def add_client(self, client):
        self._clients.append(client)

        channels = client.get_channels()
        if not channels:
            raise cyclone.web.HTTPError(400)
        for channel in channels:
            if channel not in self._channels:
                self._channels[channel] = []
                log.msg("Subscribing entire server to %s" % channel)
                self.subscribe(channel)

            if client not in self._channels[channel]:
                self._channels[channel].append(client)

        log.msg("Client %s subscribed to %s" % \
                (client.request.remote_ip, channel))

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
            log.msg('Unsubscribing entire server from channel %s' % channel)
            self.unsubscribe(channel)
            del self._channels[channel]

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
        if clients:
            args = (str(len(clients)), pattern, channel, message)
            log.msg('BROADCASTING to %s clients: pattern: %s, channel: %s, message: %s' % args)
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


class RedisBroker(Broker):
    """
    listens Redis channels and broadcasts to clients
    """
    def connect(self, settings):
        # PubSub client connection
        qf = cyclone.redis.SubscriberFactory()
        qf.broker = self
        qf.maxDelay = 20
        qf.protocol = QueueProtocol
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


class QueueProtocol(cyclone.redis.SubscriberProtocol):
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
            if "*" in channel:
                self.factory.broker.psubscribe(channel)
            else:
                self.factory.broker.subscribe(channel)

    def connectionLost(self, why):
        self.factory.broker._source = None


class ExtendedSSEHandler(SSEHandler):
    def sendPing(self):
        # send comment line to keep connection with client opened as mentioned here:
        # https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
        log.msg('ping client %s' % self.request.remote_ip)
        self.transport.write(": %s\n\n" % 'sse ping')


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
        """
        called when new connection established 
        """
        #headers = self._generate_headers()
        #self.write(headers)
        log.msg(self.request.headers)
        self.write(':\n')
        self.flush()
        self.application.broker.add_client(self)

    def unbind(self):
        """
        called when connection with client lost
        """
        self.application.broker.remove_client(self)


class App(cyclone.web.Application):
    def __init__(self, broker, settings):
        handlers = [
            (r"/", BroadcastHandler)
        ]
        self.broker = RedisBroker(settings)
        cyclone.web.Application.__init__(self, handlers)

