inspired by `tornado_sse <https://github.com/truetug/tornado-sse>`_ by `Sergey Trofimov <https://github.com/truetug>`_

EventSource (or Server-Sent-Events) is a technology that allows your server to push data into client browser.
Read this excellent articles for more information:

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

	<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js"></script>
	<script type="text/javascript" src="jquery.eventsource.js"></script>
	<script type="text/javascript">
		$(function(){
			channels = ['test1', 'test2'];
			
			suffix = $.param({'channels': channels})
			
			var url = 'http://localhost:8888/'+'?'+suffix;
			
			$.eventsource({
			    label: 'sys-sse',
			    url: url,
			    dataType: 'json',
			    open: function() {
			    	console.log('sse connection opened');
			    },
			    message: function(msg) {
			    	console.log('sse message:');	
			    	console.log(msg);	
			    },
			    error: function(msg) {
			    	console.log('sse connection error:');
			    	console.log(msg);
			    }
			});
		})
	</script>



