(function($){
    $.fn.extend({
        sse: function(options) {
            var defaults = {
                address: null,
                channels: [],
                type: "json",
                label: 'sse-channel',
                debug: false
            }

            var options = $.extend(defaults, options);

            return this.each(function(){
                var self = $(this);
			    if($.eventsource) {
			    	// detect sse server address part
			        var url = self.attr('data-sse-address') || options.address;
			        if (!url) {
			        	console.log('no sse server address specified')
			        	return false;
			        }

			        // detect sse channels to bind
			        var channel_raw = self.attr('data-sse-channels');
			        if (channel_raw.length) {
			        	var channel_list = channel_raw.split(',')
			        } else {
			        	var channel_list = options.channels;
			        }

			        if (channel_list.length) {
			        	var channels =  $.param({'channels': channel_list}, true);
			        } else {
			        	var channels = null;
			        }

			        if (channel_list.length === 0 && options.debug === true) {
			        	console.log('no channels specified, you will listen to default channel');
			        }

			        if (options.debug === true) {
			        	console.log(url);
			        }

					// create EventSource object using Rick Waldron's jquery.eventsource.js
			        $.eventsource({
			            label: options.label,
			            url: url,
			            data: channels,
			            dataType: options.type,
						open: function() {
							if (options.debug === true) {
								console.log('sse connection opened');
							}
						    self.trigger('sse.open');
						},
						message: function(msg) {
							if (options.debug === true) {
								console.log(msg);	
							}
							// msg can be null in case of ping sse messages
							if (msg) {
						    	self.trigger('sse.message', msg);
						    }
						},
						error: function(msg) {
							if (options.debug === true) {
								console.log('sse connection error:');
								console.log(msg);
							}
						    self.trigger('sse.error', msg);
			            }
			        });
			    }
            });
        }
    })
})
(jQuery)
