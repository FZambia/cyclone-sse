Nginx configuration
===================
In Chrome or Safari you can across with::
	
	Uncaught Error: SECURITY_ERR: DOM Exception 18 

This probably bug of those browsers. You should use the same domain to avoid this restriction.

This is full nginx config for development purposes. It assumes that your main application is on port 8000, and cyclone_sse server is on port 8888.
After setup go to : ``http://localhost:9090/``::

	user  nginx;
	worker_processes  10;
	worker_rlimit_nofile 100000;
	
	error_log   /var/log/nginx/error.log;
	#error_log  /var/log/nginx/error.log  notice;
	#error_log  /var/log/nginx/error.log  info;
	
	pid        /var/run/nginx.pid;
	
	
	events {
	    worker_connections  1024;
	    use epoll;
	}
	
	
	http {
	    include       /etc/nginx/mime.types;
	    default_type  application/octet-stream;
	
	    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
	                      '$status $body_bytes_sent "$http_referer" '
	                      '"$http_user_agent" "$http_x_forwarded_for"';
	
	    access_log  /var/log/nginx/access.log  main;
	
	    sendfile        on;
	    tcp_nopush      on;
	    tcp_nodelay     on;
	    server_tokens   off;
	    gzip            on;
	    gzip_static     on;
	    gzip_comp_level 5;
	    gzip_min_length 1024;
	    keepalive_timeout  65;
	    limit_conn_zone   $binary_remote_addr  zone=addr:10m;
	
	    # Load config files from the /etc/nginx/conf.d directory
	    include /etc/nginx/conf.d/*.conf;
	
	    server {
	        limit_conn addr 10;
	        listen       9090;
	        server_name  _;
	
	        #charset koi8-r;
	
	        #access_log  logs/host.access.log  main;
	
	        location /sse/ {
	            rewrite ^(.*)$ / break;
	            proxy_buffering off;
	            proxy_pass http://127.0.0.1:8888;
	        }
	
	        location / {
	            proxy_pass http://127.0.0.1:8000;
	            proxy_redirect http://127.0.0.1:8000 http://lab1.dev.mail.ru:9090;
	        }
	
	        # redirect server error pages to the static page /50x.html
	        #
	        error_page   500 502 503 504  /50x.html;
	        location = /50x.html {
	            root   /usr/share/nginx/html;
	        }
	    }
	}