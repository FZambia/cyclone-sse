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
from twisted.internet import reactor
from twisted.internet import defer
from twisted.internet import protocol
from twisted.python import log

from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
from txamqp.content import Content
import txamqp


class AmqpSubscriberProtocol(AMQClient):

    def connectionMade(self):
        AMQClient.connectionMade(self)
        df = self.connect()
        df.addCallback(self.connect_success)

    def connect_success(self, channel):
        self.connected = 1
        self.channelReady()
        self.factory.addConnection(self)
        
    def channelReady(self):
        pass

    def connection_error(self, err):
        log.err(err)
        self.factory.continueTrying = False
        self.transport.loseConnection()

    @defer.inlineCallbacks
    def connect(self):
        try:
            yield self.start({'LOGIN': self.factory.username,
                              'PASSWORD': self.factory.password})
        except Exception, e:
            self.connection_error(e)
            defer.returnValue(None)

        try:
            self.chan = yield self.channel(self.factory.chan)
        except Exception, e:
            self.connection_error(e)
            defer.returnValue(None)

        try:
            yield self.chan.channel_open()
        except Exception, e:
            self.connection_error(e)
            defer.returnValue(None)

        defer.returnValue(self.chan)

    def connectionLost(self, reason):
        AMQClient.connectionLost(self, reason)
        self.connected = 0
        self.factory.delConnection(self)

    @defer.inlineCallbacks
    def consume(self, routing_key):
        # declaring exchange
        try:
            yield self.chan.exchange_declare(exchange=self.factory.exchange_name,
                                             type=self.factory.exchange_type)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)    

        # declaring queue
        try:
            result = yield self.chan.queue_declare(exclusive=True)
            queuename = result.fields[0]
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

        # binding queue to exchange with routing_key = queue name
        try:
            yield self.chan.queue_bind(exchange=self.factory.exchange_name,
                                       queue=queuename,
                                       routing_key=routing_key)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)    

        # subscribing on queue
        try:
            yield self.chan.basic_consume(queue=queuename,
                                          no_ack=True,
                                          consumer_tag=routing_key)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

        queue = yield self.queue(routing_key)

        while True:
            log.msg('consuming %s' % routing_key)
            try:
                msg = yield queue.get()
            except Exception, e:
                defer.returnValue(None)
            self.messageReceived(None, msg.routing_key, msg.content.body)

    @defer.inlineCallbacks
    def cancel(self, queue_name):
        try:
            yield self.chan.basic_cancel(consumer_tag=queue_name)
            print '%s stopped' % queue_name
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

    def messageReceived(self, pattern, channel, message):
        pass


class AmqpSubscriberFactory(protocol.ReconnectingClientFactory):
    maxDelay = 120
    continueTrying = True
    protocol = AmqpSubscriberProtocol

    def __init__(self, spec_file=None, vhost=None,
                 host=None, port=None, username=None,
                 password=None, exchange_name="",
                 exchange_type="fanout", channel=None):
        spec_file = spec_file or 'extras/rabbitmq-specification.xml'
        self.spec = txamqp.spec.load(spec_file)
        self.username = username or 'guest'
        self.password = password or 'guest'
        self.vhost = vhost or '/'
        self.chan = channel or 1
        self.delegate = TwistedDelegate()
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type

    def buildProtocol(self, addr):
        p = self.protocol(self.delegate, self.vhost, self.spec)
        p.factory = self # Tell the protocol about this factory.
        # Reset the reconnection delay since we're connected now.
        self.resetDelay()
        return p

    def addConnection(self, conn):
        pass

    def delConnection(self, conn):
        pass
