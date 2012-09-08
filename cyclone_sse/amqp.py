# coding:utf-8
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
            yield self.start({'LOGIN': self.factory.username, 'PASSWORD': self.factory.password})
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
    def consume(self, queue_name):
        try:
            yield self.chan.exchange_declare(exchange="test-direct", type="direct")
        except Exception, e:
            log.err(e)
            defer.returnValue(None)    
        
        try:
            yield self.chan.queue_declare(queue=queue_name)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

        try:
            yield self.chan.queue_bind(exchange="test-direct", queue=queue_name, routing_key=queue_name)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)    

        try:
            yield self.chan.basic_consume(queue=queue_name, no_ack=True, consumer_tag=queue_name)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

        queue = yield self.queue(queue_name)

        while True:
            log.msg('consuming %s' % queue_name)
            try:
                msg = yield queue.get()
            except Exception, e:
                defer.returnValue(None)
            self.messageReceived(None, msg.routing_key, msg.content.body)

    @defer.inlineCallbacks
    def cancel(self, queue_name):
        try:
            yield self.chan.basic_cancel(consumer_tag=queue_name)
        except Exception, e:
            log.err(e)
            defer.returnValue(None)

    def messageReceived(self, pattern, channel, message):
        pass


class AmqpSubscriberFactory(protocol.ReconnectingClientFactory):
    maxDelay = 120
    continueTrying = True
    protocol = AmqpSubscriberProtocol

    def __init__(self, spec_file=None, vhost=None, host=None, port=None, username=None, password=None, channel=None):
        spec_file = spec_file or 'rabbit.xml'
        self.spec = txamqp.spec.load(spec_file)
        self.username = username or 'guest'
        self.password = password or 'guest'
        self.vhost = vhost or '/'
        self.host = host or 'localhost'
        self.port = port or 5672
        self.chan = channel or 1
        self.delegate = TwistedDelegate()

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
