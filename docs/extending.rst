EXtending standard behaviour
============================

Here is an example of code which allows to extend standard cyclone-sse behaviour (let it be file ``custom.py``)::

	import cyclone.web
	
	from cyclone_sse.handlers import BroadcastHandler
	from cyclone_sse.handlers import PublishHandler
	from cyclone_sse.handlers import StatsHandler
	
	from cyclone_sse.brokers import HttpBroker
	
	class CustomBroadcastHandler(BroadcastHandler):
	    
	    def authorize(self):
	        raise cyclone.web.HTTPAuthenticationRequired
	
	
	class App(cyclone.web.Application):
	    def __init__(self, settings):
	        handlers = [
	            (r"/", CustomBroadcastHandler),
	            (r"/publish", PublishHandler),
	            (r"/stats", StatsHandler),
	        ]
	
	        self.broker = HttpBroker(settings)
	        cyclone.web.Application.__init__(self, handlers)


Run server using ``-r`` option::

	twistd -n cyclone-sse -r "custom.App"
