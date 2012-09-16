from twisted.internet.protocol import Protocol
from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer
from twisted.web.client import Agent,  HTTPConnectionPool
from twisted.internet import reactor, defer
from twisted.web.http_headers import Headers
import random
import urllib

import sys
try:
    NUM = int(sys.argv[1])
except:
    NUM = 350

class Printer(Protocol):
    def __init__(self, finished):
        self.finished = finished

    def dataReceived(self, bytes):
        print bytes

    def connectionLost(self, reason):
        #print reason
        #reactor.stop()
        pass
        #self.finished.callback(None)

def http_get(channel):
    pool = HTTPConnectionPool(reactor)
    agent = Agent(reactor, pool=pool)
    df = agent.request(
        'GET',
        'http://localhost:8888/?channels=%s&channels=general' % channel,
        Headers({'User-Agent': ['twisted-monitor'],       
                'Origin': ['http://localhost:8000'],
                'Accept-Language': ['ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3'],
                'Accept-Encoding': ['gzip, deflate'],
                'Connection': ['keep-alive'],
                'Accept': ['text/event-stream'],
                'Host': ['192.168.1.34:8888'],
                'Referer': ['http://localhost:8000/'],
                'Pragma': ['no-cache'],
                'Cache-Control': ['no-cache']}
        ),
        None
    )
    return df

def cbRequest(response):
    print 'Response version:', response.version
    print 'Response code:', response.code
    print 'Response phrase:', response.phrase
    print 'Response headers:'
    print list(response.headers.getAllRawHeaders())
    finished = defer.Deferred()
    response.deliverBody(Printer(finished))
    return finished

def cbShutdown(ignored):
    reactor.stop()

def error(err):
    print err

if __name__ == '__main__':
    channels = ['base', 'extras', 'cats', 'dogs']
    
    for i in range (1, NUM):
        channel = random.choice(channels)
        df = http_get(channel)
        df.addCallback(cbRequest)
        df.addErrback(error)
        df.addBoth(cbShutdown)
    
    reactor.run()
