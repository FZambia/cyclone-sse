from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task
import json
import time


class ImproperlyConfigured(Exception):
    pass


class UdpExport(DatagramProtocol):

    def __init__(self, broker, settings):
        self.broker = broker
        self.host = settings['export-host']
        self.port = settings['export-port']
        self.interval = settings['export-interval']
        self.path = settings['export-path']
        if not self.broker or not self.host or not self.port:
            raise ImproperlyConfigured("not enough arguments for \
                                        periodic stats export")
        reactor.listenUDP(0, self)

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        lc = task.LoopingCall(self.sendDatagram)
        lc.start(self.interval, now=False)

    def sendDatagram(self):
        data = self.broker.stats()
        if data:
            prepared_data = self.prepare(data)
            self.transport.write(prepared_data)

    def prepare(self, data):
        return json.dumps(data)


class GraphiteExport(UdpExport):
    """
    sends stats to graphite
    http://graphite.wikidot.com/
    """
    def prepare(self, data):
        if not self.path.endswith('.'):
            self.path = "%s." % self.path

        lines = []
        timestamp = str(time.time()).split('.')[0]

        for channel, clients in data:
            key = "%s%s" % (self.path, channel)
            lines.append("%s %s %s" % (key, str(clients), timestamp))

        message = '\n'.join(lines) + '\n'
        return message
