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
import uuid
from copy import copy

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
    def __init__(self, settings, name='unknown'):
        self._name = name
        self._source = None
        self._clients = {}
        self._channels = {}
        self._cache = []
        self._cache_size = 50
        self._settings = settings
        self.setup(self._settings)

    def setup(self, settings):
        self.connect(settings)

    def connect(self, settings):
        raise NotImplementedError('please, provide implementation for connect method')

    def _subscribe(self, channel):
        if channel not in self._channels:
            self._channels[channel] = {}
            log.msg("Subscribing entire server to %s" % channel)
            if self._source:
                self.subscribe(channel)

    def _unsubscribe(self, channel):
        if channel in self._channels:
            del self._channels[channel]
            log.msg('Unsubscribing entire server from channel %s' % channel)
            if self._source:
                self.unsubscribe(channel)

    def add_client(self, client):
        """
        registers new client in broker
        """
        client.uid = str(uuid.uuid4())
        client.channels = client.get_channels()
        if not client.channels:
            raise cyclone.web.HTTPError(400)

        self._clients[client.uid] = client
        client.set_ping()

        for channel in client.channels:
            self._subscribe(channel)
            self._channels[channel][client.uid] = 1
            log.msg("Client %s subscribed to %s" % (client.request.remote_ip, channel))

        self.send_cache(client)

    def remove_client(self, client):
        """
        unregisters client
        """
        if client.uid in self._clients:
            del self._clients[client.uid]
            client.del_ping()
            try:
                client.flush()
                client.finish()
            except defer.AlreadyCalledError:
                # client connection has already been finished
                pass

        # channels that have no clients
        empty = []

        # removing client from channels
        for channel in client.channels:
            clients = self._channels.get(channel, None)
            if clients and client.uid in clients:
                del clients[client.uid]
                log.msg('Unsubscribing client from channel %s' % channel)
            if not clients:
                empty.append(channel)

        # clean server subscription
        for channel in empty:
            self._unsubscribe(channel)

    def subscribe(self, channel):
        raise NotImplementedError('please, provide implementation for subscribe method')

    def unsubscribe(self, channel):
        raise NotImplementedError('please, provide implementation for unsubscribe method')

    def broadcast(self, pattern, channel, message):
        """
        sends message to all clients of certain channel
        """
        if self.is_pattern_blocked(pattern):
            return True
        clients = copy(self._channels.get(channel, None))

        if clients:
            args = (str(len(clients)), pattern, channel, message)
            log.msg('BROADCASTING to %s clients: pattern: %s, channel: %s, message: %s' % args)            

            # put this message into cache
            eid = str(uuid.uuid4())
            self.update_cache(eid, channel, message)

            # sent message to all clients
            for uid in clients:
                client = self._clients.get(uid, None)
                if client:
                    client.reset_ping()
                    self.send_event(client, message, eid=eid)

    def is_pattern_blocked(self, pattern):
        """
        must return true if we do not want to send messages of this pattern
        """
        return False

    def send_event(self, client, message, eid):
        client.sendEvent(message, eid=eid)
        if client.is_xhr():
            client.unbind()

    def send_cache(self, client):
        """
        sends missed messages to client
        """
        last_event_id = client.request.headers.get('Last-Event-Id', None)
        if last_event_id:
            i = 0
            for i, msg in enumerate(self._cache, 1):
                if msg['eid'] == last_event_id:
                    break

            for item in self._cache[i:]:
                if item['channel'] in client.get_channels():
                    self.send_event(client, item['message'], item['eid'])
                    if client.is_xhr():
                        break

    def update_cache(self, eid, channel, message):
        """
        adds message into broker cache
        """
        self._cache.append({
            'eid': eid,
            'channel': channel,
            'message': message
        })
        if len(self._cache) > self._cache_size:
            self._cache = self._cache[-self._cache_size:]


class HttpBroker(Broker):

    def __init__(self, *args, **kwargs):
        super(HttpBroker, self).__init__(*args, **kwargs)

    def connect(self, settings):
        self.secret_key = settings["http-secret"]
        self.queue = defer.DeferredQueue()
        self._source = True
        self.start_consuming()

    @defer.inlineCallbacks
    def start_consuming(self):
        while True:
            msg = yield self.queue.get()
            self.broadcast(None, msg['channel'], msg['message'])

    def subscribe(self, channel):
        pass

    def unsubscribe(self, channel):
        pass

    def publish(self, channel, message):
        if channel in self._channels:
            self.queue.put({'channel': channel, 'message': message})


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
        qf = AmqpSubscriberFactory(spec_file=settings["amqp-spec"],
                                   vhost=settings["amqp-vhost"],
                                   username=settings["amqp-username"],
                                   password=settings["amqp-password"],
                                   exchange_name=settings["amqp-exchange-name"],
                                   exchange_type=settings["amqp-exchange-type"],
                                   channel=settings["amqp-channel"])
        qf.broker = self
        qf.protocol = AmqpBroadcastProtocol
        reactor.connectTCP(settings["amqp-host"], settings["amqp-port"], qf)

    def subscribe(self, channel):
        self._source.consume(channel)

    def unsubscribe(self, channel):
        self._source.cancel(channel)
