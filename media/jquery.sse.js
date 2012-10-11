;(function(jQuery) {
	jQuery.extend({
		sse : function(options) {
			var defaults = {
				url : '/sse/',
				selector : '.sse',
				attr : 'data-sse-channels',
				debug : false,
				label : "default",
				type : "json",
				eventPrefix : 'sse.'
			}

			var options = jQuery.extend(defaults, options);

			function init() {
				if (!jQuery.eventsource) {
					console.log("jquery eventsource polyfill not found");
					return;
				}

				// now we should find all channels we want to listen
				var channels = [];
				var handlers = jQuery(options.selector);
				var compliance = {};
				if (handlers.length === 0) {
					if (options.debug === true) {
						console.log("no eventsource handlers found on page");
					}
					return;
				}
				handlers.each(function(index, element) {
					var handler = jQuery(element);
					handler_channels = handler.attr(options.attr);
					if (handler_channels.length) {
						var channel_list = handler_channels.split(',')
						for (i in channel_list) {
							var c = jQuery.trim(channel_list[i]);

							if (!( c in compliance)) {
								compliance[c] = [];
							}
							compliance[c].push(handler);

							if (jQuery.inArray(c, channels) === -1) {
								channels.push(c);
							}
						}
					}
				});
				if (channels.length === 0) {
					if (options.debug === true) {
						console.log("no channels found");
					}
					return;
				}

				// make appropriate query
				var query = jQuery.param({
					'channels' : channels
				}, true);
				if (options.debug === true) {
					console.log('sse url: ' + options.url + '?' + query);
				}

				// create EventSource object using Rick Waldron's jquery.eventsource.js
				jQuery.eventsource({
					label : options.label,
					url : options.url,
					data : query,
					dataType : options.type,

					open : function() {
						if (options.debug === true) {
							console.log('sse connection opened');
						}
						handlers.each(function(index, element) {
							jQuery(element).trigger(options.eventPrefix + 'open');
						});
					},

					error : function(err) {
						if (options.debug === true) {
							console.log('sse connection error');
							console.log(msg);
						}
						handlers.each(function(index, element) {
							jQuery(element).trigger(options.eventPrefix + 'error', err);
						});
					},

					message : function(msg, event) {
						if (options.debug === true) {
							console.log(msg);
							console.log(event);
						}
						// msg can be null in case of ping sse messages
						if (msg) {
							var customEvent = options.eventPrefix;
							var eventType = msg[0];
							var eventData = msg[1];
							customEvent += eventType;
							if (options.debug === true) {
								console.log("triggering event: " + customEvent);
							}
							if ( eventType in compliance) {
								var eventHandlers = compliance[eventType];
								jQuery.each(eventHandlers, function(index, element) {
									jQuery(element).trigger(customEvent, eventData);
								});
							}
						}
					}
				});
			}

			return init();

		}
	})
})(jQuery)