Nginx configuration
===================
In Chrome or Safari you can come across with::
	
	Uncaught Error: SECURITY_ERR: DOM Exception 18 

This probably bug of those browsers. You should use the same domain to avoid this restriction.

This is full nginx config for development purposes. It assumes that your main application is on port 8000, and cyclone_sse server is on port 8888.
After setup go to : ``http://localhost:9090/``::

	#user  nobody;
	worker_processes  1;
	
	#error_log  logs/error.log;
	#error_log  logs/error.log  notice;
	#error_log  logs/error.log  info;
	
	#pid        logs/nginx.pid;

	events {
	    worker_connections  1024;
	    use epoll;
	}
	
	http {
	    include       mime.types;
	    default_type  application/octet-stream;
	
	    #log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
	    #                  '$status $body_bytes_sent "$http_referer" '
	    #                  '"$http_user_agent" "$http_x_forwarded_for"';
	
	    #access_log  logs/access.log  main;
	
	    sendfile        on;
	    #tcp_nopush     on;
	
	    #keepalive_timeout  0;
	    keepalive_timeout  65;
	
	    #gzip  on;
	
	    server {
	        listen       8080;
	        server_name  localhost;
	
	        #charset koi8-r;
	
	        #access_log  logs/host.access.log  main;
	
	        location /sse/ {
	            rewrite ^(.*)$ / break;
	            proxy_buffering off;
	            proxy_pass http://127.0.0.1:8888;
	        }
	        location / {
	            proxy_pass http://127.0.0.1:8000;
	            proxy_redirect http://127.0.0.1:8000 http://localhost:8080;
	        }
	        #error_page  404              /404.html;
	
	        # redirect server error pages to the static page /50x.html
	        #
	        error_page   500 502 503 504  /50x.html;
	        location = /50x.html {
	            root   html;
	        }
	    }
	
	}
