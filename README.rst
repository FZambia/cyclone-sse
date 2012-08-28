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
	<script type="text/javascript">
		$(function(){
			channels = ['test1', 'test2'];
			
			suffix = $.param({'channels': channels})
			
			var source = new EventSource('http://localhost:8888/'+'?'+suffix);
			
			source.addEventListener('message', function(e) {
			  console.log(e.data);
			}, false);
			
			source.addEventListener('open', function(e) {
			  console.log('connected');
			}, false);
			
			source.addEventListener('error', function(e) {
			  if (e.readyState == EventSource.CLOSED) {
			    console.log('closed');
			  }
			}, false);
		})
	</script>



