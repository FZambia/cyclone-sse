inspired by `tornado_sse <https://github.com/truetug/tornado-sse>`_ by `Sergey Trofimov <https://github.com/truetug>`_

installing::

	git clone git@github.com:FZambia/cyclone_sse.git cyclone_sse/
	cd cyclone_sse
	virtualenv --no-site-packages env
	. env/bin/activate
	pip install -r requirements.txt

to run server::

	twistd -n cyclone -r server.Application -l 0.0.0.0 -p 8888

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



