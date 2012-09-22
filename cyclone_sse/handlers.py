# coding: utf-8
#
# Copyright 2012 Alexandr Emelin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import cyclone.web
from cyclone.sse import SSEHandler

from twisted.internet import defer
from twisted.internet import base
from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log


class ExtendedSSEHandler(SSEHandler):

    def reset_ping(self):
        self.del_ping()
        self.set_ping()

    def set_ping(self):
        """
        sets delayed call for this client
        """
        ping = defer.Deferred()
        ping.addCallback(self.send_ping)
        ping.addErrback(lambda err: log.err(err))
        self.ping = reactor.callLater(30, ping.callback, True)

    def del_ping(self):
        """
        cancels delayed call for this client
        """
        if hasattr(self, 'ping') and isinstance(self.ping, base.DelayedCall):
            if not self.ping.called and not self.ping.cancelled:
                self.ping.cancel()

    def send_ping(self, _ignored):
        """
        sends comment line to keep connection with client opened as mentioned here:
        https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
        """
        self.transport.write(": %s\n\n" % 'sse ping')
        if self.is_xhr():
            # we should close connection with XMLHttpRequest clients to make them reconnect
            self.unbind()
        else:
            self.set_ping()

    def is_xhr(self):
        return self.request.headers.get('X-Requested-With', None) == 'XMLHttpRequest'


class BroadcastHandler(ExtendedSSEHandler):

    sse_headers = {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    }

    def initialize(self):
        for name, value in self.sse_headers.iteritems():
            self.set_header(name, value)

    def get_channels(self):
        """
        retrieves channels client wants to subscribe
        """
        channels = self.get_arguments('channels')
        return channels

    def authorize(self):
        pass

    def bind(self):
        """
        called when new connection established 
        """
        log.msg(self.request.headers)
        self.authorize()
        self.write('\n\n')
        self.flush()
        self.application.broker.add_client(self)

    def unbind(self):
        """
        called when connection with client lost
        """
        self.application.broker.remove_client(self)


class StatsHandler(cyclone.web.RequestHandler):
    """
    current connection statistics
    """
    def get(self):
        self.write(str([(k, len(v)) for k, v in self.application.broker._channels.iteritems()]))
        self.finish()


class PublishHandler(cyclone.web.RequestHandler):
    """
    handler that listens to incoming messages and publishes new into HTTP broker
    """
    def post(self):
        key = self.get_argument("key", None)
        secret_key = self.application.broker.secret_key
        if secret_key and key != secret_key:
            raise cyclone.web.HTTPError(401)
        message = self.get_argument('message', None)
        channel = self.get_argument("channel", None)
        if channel and message:
            self.application.broker.publish(channel, message)
            self.set_header("Content-Type", "application/json")
            self.write({'status':'ok'})
        else:
            return cyclone.web.HTTPError(400)