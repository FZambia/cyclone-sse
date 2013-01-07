;(function(jQuery) {
	jQuery.extend({
		sse : function(options) {
			var defaults = {
				url : '/sse/',
				selector : '.sse',
				channelAttr : 'data-sse-channels',
				eventAttr: 'data-sse-events',
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
			          handler_channels = handler.attr(options.channelAttr);
			          handler_events = handler.attr(options.eventAttr);
			          if (handler_channels && handler_channels.length) {
			            var channel_list = handler_channels.split(',')
			            for (i in channel_list) {
			              var c = jQuery.trim(channel_list[i]);
			              if (jQuery.inArray(c, channels) === -1) {
			                channels.push(c);
			              }
			            }
			          }
			          if (handler_events && handler_events.length) {
			            var event_list = handler_events.split(',');
			            for (i in event_list) {
			              var e = jQuery.trim(event_list[i]);
			              if (!( e in compliance)) {
			                compliance[e] = [];
			              }
			              compliance[e].push(handler);
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
