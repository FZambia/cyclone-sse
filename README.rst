inspired by `tornado_sse <https://github.com/truetug/tornado-sse>`_ by `Sergey Trofimov <https://github.com/truetug>`_

Overview
===========

EventSource (or Server-Sent-Events) is a technology that allows your server to push data into client browser.
Read these excellent articles for more information:

`html5rocks.com <http://www.html5rocks.com/en/tutorials/eventsource/basics/>`_

`html5doctor.com <http://html5doctor.com/server-sent-events/>`_


The goal of this repo is to provide you a server for SSE event broadcasting and to give some useful information what to do on client side. 


Installing::

	virtualenv --no-site-packages env
	. env/bin/activate
	pip install git+https://github.com/FZambia/cyclone_sse.git


Server side
===========


To run server in development::

	twistd -n cyclone_sse


Use ``-h`` option to see available options::

	twistd -n cyclone_sse -h


Due to the power of ``twistd``, this application can be easily deployed in
production, with all the basic features of standard daemons::

    twistd --uid=www-data --gid=www-data --reactor=epoll \
           --logfile=/var/log/cyclone_sse.log --pidfile=/var/run/cyclone_sse.pid \
           cyclone__sse --port=8080 --listen=0.0.0.0


If your main server in behind Nginx you should proxy SSE like this::

    location /sse/ {
        rewrite                 ^(.*)$ / break; # to root of our tornado
        proxy_buffering         off; # to push immediately
        proxy_pass              http://127.0.0.1:8888;
    }


Client side
===========

in browser::

	<!DOCTYPE html>
	<html lang="en">
		<head>
			<meta charset="utf-8"/>
			<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js"></script>
			<script type="text/javascript" src="https://raw.github.com/FZambia/cyclone_sse/master/media/jquery.eventsource.js"></script>
			<script type="text/javascript" src="https://raw.github.com/FZambia/cyclone_sse/master/media/jquery.sse.js"></script>
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

	
As you can see we use `Rick Waldron's <https://github.com/rwldrn>`_ jQuery polyfill `jquery.eventsource <https://github.com/rwldrn/jquery.eventsource>`_
And it seems to work nice even with Internet Explorer using long polling.


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
client side and decide what to do with incoming message. This is a payment for crossbrowser compability.





