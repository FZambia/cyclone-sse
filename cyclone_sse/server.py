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
from cyclone.sse import SSEHandler

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log

from cyclone_sse.brokers import RedisBroker, Broker


from cyclone_sse.amqp import AmqpSubscriberFactory, AmqpConsumerProtocol


class AmqpBroker(Broker):
    def connect(self, settings):
        # PubSub client connection
        qf = AmqpSubscriberFactory()
        qf.broker = self
        qf.protocol = QueueProtocol
        reactor.connectTCP("127.0.0.1", 5672, qf)

    def subscribe(self, channel):
        self._source.consume(channel)

class QueueProtocol(AmqpConsumerProtocol):
    def messageReceived(self, pattern, channel, message):
        # When new messages are published to Redis channels or patterns,
        # they are broadcasted to all HTTP clients subscribed to those
        # channels.
        self.factory.broker.broadcast(pattern, channel, message)

    def connectionMade(self):
        AmqpConsumerProtocol.connectionMade(self)
        self.factory.broker._source = self
        # If we lost connection with Redis during operation, we
        # re-subscribe to all channels once the connection is re-established.
        for channel in self.factory.broker._channels:
            if "*" in channel:
                self.factory.broker.consume(channel)
            else:
                self.factory.broker.subscribe(channel)

    def connectionLost(self, why):
        self.factory.broker._source = None
        AmqpConsumerProtocol.connectionLost(self, why)

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
        self.broker = AmqpBroker(settings)
        cyclone.web.Application.__init__(self, handlers)

