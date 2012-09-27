from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task

class UdpExport(DatagramProtocol):

    def __init__(self, broker, host, port, interval=60):
        self.broker = broker
        self.host = host
        self.port = port
        self.interval = interval
        reactor.listenUDP(0, self)

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        lc = task.LoopingCall(self.sendDatagram)
        lc.start(self.interval, now=False)

    def sendDatagram(self):
        data = str(self.broker.stats())
        self.transport.write(data)
        print 'sent %s' % data