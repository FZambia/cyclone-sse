/*!
 * jQuery.EventSource (jQuery.eventsource)
 *
 * Copyright (c) 2011 Rick Waldron
 * Dual licensed under the MIT and GPL licenses.
 */

(function(jQuery, global) {

	jQuery.extend(jQuery.ajaxSettings.accepts, {
		stream : "text/event-stream"
	});

	var stream = {

		defaults : {
			// Stream identity
			label : null,
			// Source url
			url : null,
			// Custom events
			events : null,
			// Default Reconnect timeout
			retry : 500,

			// Event Callbacks
			open : jQuery.noop,
			message : jQuery.noop,
			error : jQuery.noop
		},
		setup : {
			stream : {},
			lastEventId : 0,
			hasNativeSupport : false,
			retry : 500,
			history : [],
			options : {}
		},
		cache : {}
	}, pluginFns = {

		public : {
			close : function(label) {

				var tmp = {};

				if (!label || label === "*") {
					for (var prop in stream.cache) {
						if (stream.cache[prop].hasNativeSupport) {
							stream.cache[prop].stream.close();
						}
					}

					stream.cache = {};

					return stream.cache;
				}

				for (var prop in stream.cache) {
					if (label !== prop) {
						tmp[prop] = stream.cache[prop];
					} else {
						if (stream.cache[prop].hasNativeSupport) {
							stream.cache[prop].stream.close();
						}
					}
				}

				stream.cache = tmp;

				return stream.cache;
			},
			streams : function(label) {

				if (!label || label === "*") {
					return stream.cache;
				}

				return stream.cache[label] || {};
			}
		},
		_private : {

			// Open a host api event source
			openEventSource : function(options) {

				var label = options.label;

				stream.cache[label].stream.addEventListener("open", function(event) {
					if (stream.cache[label]) {

						this.label = label;

						stream.cache[label].options.open.call(this, event);
					}
				}, false);

				stream.cache[label].stream.addEventListener("error", function(err) {
					if (stream.cache[label]) {

						this.label = label;

						stream.cache[label].options.error.call(this, err);

					}
				}, false);

				stream.cache[label].stream.addEventListener("message", function(event) {

					var streamData = null;
					var msg;

					if (stream.cache[label]) {

						if (options.dataType === 'json') {
							msg = jQuery.parseJSON(event.data);
						} else {
							msg = event.data;
						}

						streamData = msg;

						this.label = label;

						stream.cache[label].lastEventId = event.lastEventId;
						stream.cache[label].history.push([event, streamData]);
						stream.cache[label].options.message.call(this, streamData ? streamData : null, event);

					}
				}, false);

				return stream.cache[label].stream;
			},
			// open fallback event source
			openPollingSource : function(options) {
				var label = options.label;
				var source;

				if (stream.cache[label]) {
					var lastEventId = stream.cache[label].lastEventId ? stream.cache[label].lastEventId : null;

					source = jQuery.ajax({
						type : "GET",
						url : options.url,
						data : options.data,
						beforeSend : function(xhr) {
							if (lastEventId !== null) {
								xhr.setRequestHeader("Last-Event-Id", lastEventId);
							}
							if (stream.cache[label]) {
								this.label = label;
								stream.cache[label].options.open.call(this);
							}
						},
						error : function(err) {
							if (stream.cache[label]) {
								this.label = label;
								stream.cache[label].options.error.call(this, err);
							}

						},
						success : function(rawData) {
							var label = options.label;
							var messages = rawData.split('\n\n');
							for (i in messages) {
								var data = messages[i];
								if (data === "") {
									continue;
								}
								rows = data.split('\n');
								lines = jQuery.grep(rows, function(row) {
									return row !== '';
								});

								var fallbackEvent = {
									lastEventId : null,
									data : null,
									retry : null,
									type : "message",
									timeStamp : new Date().getTime()
								};
								var tmpdata = [];
								var streamData = null;

								var rgx = {
									"id" : /^id:/,
									"event" : /^event:/,
									"retry" : /^retry:/,
									"data" : /^data:/
								}

								if (jQuery.isArray(lines)) {

									jQuery.each(lines, function(index, line) {

										if (rgx.event.test(line)) {
											content = jQuery.trim(line.split(':').slice(1).join(':'));
											if (content.length) {
												fallbackEvent.eventType = content;
											}
										} else if (rgx.id.test(line)) {
											content = jQuery.trim(line.split(':').slice(1).join(':'));
											if (content.length) {
												fallbackEvent.lastEventId = content;
											}
										} else if (rgx.retry.test(line)) {
											content = jQuery.trim(line.split(':').slice(1).join(':'));
											if (content && /^\d+$/.test(content)) {
												fallbackEvent.retry = parseInt(content);
											}
										} else if (rgx.data.test(line)) {
											content = line.split(':').slice(1).join(':');
											if (content.length) {
												tmpdata.push(jQuery.trim(content));
											}
										}
									});

									if (tmpdata.length) {
										data = tmpdata.join('\n');
										fallbackEvent.data = data;
										if (options.dataType === "json") {
											streamData = jQuery.parseJSON(data);
										} else {
											streamData = data;
										}
									}

								}

								if (stream.cache[label]) {

									this.label = label;

									stream.cache[label].retry = stream.cache[label].options.retry = fallbackEvent.retry;
									if (fallbackEvent.lastEventId) {
										stream.cache[label].lastEventId = stream.cache[label].options.lastEventId = fallbackEvent.lastEventId;
									}
									stream.cache[label].history.push([fallbackEvent, streamData])//[stream.cache[label].lastEventId] = parsedData;

									stream.cache[label].options.message.call(this, streamData, fallbackEvent);
								}
							}

							if (stream.cache[label]) {
								setTimeout(function() {
									pluginFns._private.openPollingSource.call(this, options);
								},
								// Use server sent retry time if exists or default retry time if not
								(stream.cache[label] && stream.cache[label].retry) || options.retry);
							}
						},
						cache : false,
						timeout : 50000
					});
				}
				return source;
			}
		}
	}, hasNativeSupport = global.EventSource ? true : false;

	jQuery.eventsource = function(options) {

		var streamType, opts;

		// Plugin sub function
		if (options && !jQuery.isPlainObject(options) && pluginFns.public[options]) {
			// If no label was passed, send message to all streams
			return pluginFns.public[options](arguments[1] ? arguments[1] : "*");
		}

		// If params were passed in as an object, normalize to a query string
		options.data = options.data && jQuery.isPlainObject(options.data) ? jQuery.param(options.data) : options.data;

		// Mimick the host api behavior?
		if (!options.url || typeof options.url !== "string") {
			throw new SyntaxError("Not enough arguments: Must provide a url");
		}

		// If no explicit label, set internal label
		options.label = !options.label ? options.url + "?" + options.data : options.label;

		// Create new options object
		opts = jQuery.extend({}, stream.defaults, options);

		// Create empty object in `stream.cache`
		stream.cache[opts.label] = {
			options : opts
		};

		// Determine and declare `event stream` source,
		// whether will be host api or XHR fallback
		streamType = !hasNativeSupport ?
		// If not host api, open a polling fallback
		pluginFns._private.openPollingSource(opts) : new EventSource(opts.url + (opts.data ? "?" + opts.data : ""));

		// Add to event sources
		stream.cache[opts.label] = jQuery.extend({}, stream.setup, {
			stream : streamType,
			hasNativeSupport : hasNativeSupport,
			options : opts
		});

		if (hasNativeSupport) {
			pluginFns._private.openEventSource(opts);
		}

		return stream.cache;
	};

	jQuery.each(["close", "streams"], function(idx, name) {
		jQuery.eventsource[name] = function(arg) {
			return jQuery.eventsource(name, arg || "*");
		};
	});

})(jQuery, window);
