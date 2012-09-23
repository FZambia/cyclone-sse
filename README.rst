CYCLONE SSE
===========

inspired by `Sergey Trofimov's <https://github.com/truetug>`_ `tornado_sse <https://github.com/truetug/tornado-sse>`_.

--------
Overview
--------

EventSource (or Server-Sent-Events) is a technology for providing push data (notifications, content updates) from a server to a browser client in the form of DOM events.
Read these excellent articles for more information:

`html5rocks.com <http://www.html5rocks.com/en/tutorials/eventsource/basics/>`_

`html5doctor.com <http://html5doctor.com/server-sent-events/>`_


The goal of this repo is to provide you a server for SSE event broadcasting and to give some useful information what to do on client side.
Broadcasting server built on top of `cyclone <https://github.com/fiorix/cyclone>`_ - it is fully asynchronous and extremely fast.


Installing::

	virtualenv --no-site-packages env
	. env/bin/activate
	pip install cyclone-sse


Let's describe on example one of possible use cases::

	1) Your web application's visitor opens a page. Let it be a text translation
	of new Apple iPhone 6 presentation or, if you do not like Apple, Samsung Galaxy S4.
	Javascript creates EventSource object and establishes connection with our cyclone
	server. In GET parameters of url to connect we provide a channel name we want 
	to listen to.
	
	2) Asynchronous broadcast server accepts this connection and keeps it open to
	transfer data when this will be necessary.
	
	3) Wow, just now text translation's author got a specifications of new phone!!
	Of course he wants to share it with our visitors. He submits special form with specification text.
	Your php (or django, or nodejs, or ror) application saves it in database as usually.
	Then in the simpliest case - this data must be POSTed on our cyclone server. We should
	not forget to provide a channel name we want to publish this text in. Our cyclone server
	has a special handler which listens to such POSTs and then broadcasts data to
	all our clients (visitors). Event in web browser fires and our client side 
	javascript code draws phone specification message in activity feed.
	The new phone has 8 cores - what a good news!!


That was only one example of using SSE technology, it is also well suited for things like comments,
dynamic charts, stats etc..


-----------
Server side
-----------

To run server in development::

	twistd -n cyclone-sse


Use ``-h`` option to see available options::

	twistd -n cyclone-sse -h


Due to the power of ``twistd``, this application can be easily deployed in
production, with all the basic features of standard daemons::

    twistd --uid=www-data --gid=www-data --reactor=epoll \
           --logfile=/var/log/cyclone-sse.log --pidfile=/var/run/cyclone-sse.pid \
           cyclone-sse --port=8080 --listen=0.0.0.0


If your main server in behind Nginx you should proxy SSE like this::

    location /sse/ {
        rewrite                 ^(.*)$ / break; # to root of our tornado
        proxy_buffering         off; # to push immediately
        proxy_pass              http://127.0.0.1:8888;
    }


Also read `this <https://github.com/FZambia/cyclone-sse/blob/master/docs/nginx.rst>`_ to avoid some possible problems


-----------
Client side
-----------

in browser::

	<!DOCTYPE html>
	<html lang="en">
		<head>
			<meta charset="utf-8"/>
			<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js"></script>
			<script type="text/javascript" src="https://raw.github.com/FZambia/cyclone-sse/master/media/jquery.eventsource.js"></script>
			<script type="text/javascript" src="https://raw.github.com/FZambia/cyclone-sse/master/media/jquery.sse.js"></script>
			<script type="text/javascript">
				$(function(){
					$('#sse-handler').sse({'debug':true});
				})
			</script>
		</head>
		<body>
			<div id="sse-handler" data-sse-address="http://localhost:8888/" data-sse-channels="base"></div>
		</body>
	</html>

	
We use an extremely modified `Rick Waldron's <https://github.com/rwldrn>`_ jQuery polyfill `jquery.eventsource <https://github.com/rwldrn/jquery.eventsource>`_.
If browser does not natively support EventSource, then we use ``long-polling``, so it works nice even in Internet Explorer.


To check that everything work fine with redis - open your web browser console, then go to redis console (``redis-cli``) and type::

	publish base '[1, 2, 3]'
	
You published message ``[1, 2, 3]`` into the channel ``base``.
You should see an array in browser console (``debug`` option of sse jquery plugin must be ``true``).
There is a moment to keep attention at: your message must be json encoded data - if you want to receive plain text then
add ``'type': 'text'`` in jquery sse plugin initialization options.


Or if you are using default HTTP broker::

	curl --dump-header - -X POST -d "message=%5B123%2C+124%5D&channel=base" http://localhost:8888/publish

You published message ``[123, 124]`` into channel ``base``. Do not forget to encode your message as json!!


SSE provides a possibility to use custom Event type. This app does not use it, because some web browsers recognize only
standard event type - ``message``. But it does not mean you can not use custom event types. All you need to do is, for example, to put your
custom event type in the first place of message array. (``["your_event_type", "data"]``). In this way you can detect event type on
client side and decide what to do with incoming message. This is a payment for crossbrowser compatibility.


----------------------------
Available publish mechanisms
----------------------------

* HTTP
The simpliest mechanism. All you need to do is to POST message on ``/publish`` url of broadcast server in the 
following format::

	{"key": "secret key to prove your right to publish",
	"channel": "channel name",
	"message": "new message data"}

* Redis
This broker allows you to listen to Redis channels and broadcasts incoming messages. txRedisApi library is used for this.

* AMQP
Allows to listen AMQP toolkits, such as RabbitMQ, Qpid etc. In this case you should provide amqp specification XML file. txAMQP is used for this.

------------
Load testing
------------
On this moment application was tested on 3600 simultanious connections using HTTP broker.
``/stats`` handler showed following state::
	
	[(u'cats', 946), (u'extras', 899), (u'dogs', 864), (u'base', 877), (u'general', 3586)]
	
As you can see, all clients were connected to ``general`` channel, and to one of other 4 channels.
Test took place on local machine - macbook Air (core i5, 4GB RAM) using kqueue reactor.
Results are perfect - about 200 ms for broadcasting into channel ``general`` and about 50 ms for broadcasting into one of others channels.
And this has been done in a nondaemon twistd mode - so real results could be much better.
I will update this information as soon as I make new load tests.

You can do your own measurements using ``client.py`` script from ``extras`` directory.

---------------------------
Extending standard behavior
---------------------------
You may want to extend cyclone-sse.
In this case you can run cyclone-sse plugin
with option --app that allows you to use your own
cyclone.web.Application. So you can decide what handlers
or brokers you need, write your own or extend existing
from cyclone_sse.handlers and cyclone_sse.brokers.

------------
Known Issues
------------

* According to `http://stackoverflow.com/questions/7340784/easy-install-pyopenssl-error <http://stackoverflow.com/questions/7340784/easy-install-pyopenssl-error>`_
their is no OpenSSL 0.9.8f distribution for ``CentOS 5``. So for CentOS 5 we use ``pyopenssl`` of version 0.12 (not latest)