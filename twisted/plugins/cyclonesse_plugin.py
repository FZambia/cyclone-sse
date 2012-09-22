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

import sys

from twisted.application import internet
from twisted.application import service
from twisted.plugin import IPlugin
from twisted.python import usage
from twisted.python import reflect
from zope.interface import implements

from cyclone_sse.server import App

try:
    from twisted.internet import ssl
except ImportError:
    ssl_support = False
else:
    ssl_support = True


class Options(usage.Options):
    optParameters = [
        ["port", "p", 8888, "tcp port to listen on", int],
        ["listen", "l", "127.0.0.1", "interface to listen on"],
        ["app", "r", None, "custom application to run"],

        ["use-ssl", None, 0, "use ssl", int],
        ["ssl-port", None, 8443, "port to listen on for ssl", int],
        ["ssl-listen", None, "127.0.0.1", "interface to listen on for ssl"],
        ["ssl-cert", None, "server.crt", "ssl certificate"],
        ["ssl-key", None, "server.key", "ssl server key"],
        ["ssl-app", None, None, "ssl application (same as --app)"],
        ["ssl-appopts", None, None, "arguments to the ssl application"],

        ["broker", None, "http", "publish provider"],

        ["http-secret", None, "", "secret key to publish via HTTP"],

        ["redis-host", None, "127.0.0.1", "redis host"],
        ["redis-port", None, 6379, "redis port", int],
        
        ["amqp-host", None, "127.0.0.1", "amqp broker's host"],
        ["amqp-port", None, 5672, "amqp broker's port", int],
        ["amqp-vhost", None, "/", "amqp broker's virtual host"],
        ["amqp-spec", None, "rabbit.xml", "path to AMQP specification XML file"],
        ["amqp-username", None, "guest", "username"],
        ["amqp-password", None, "guest", "password"],
        ["amqp-exchange-name", None, "sse-cyclone-server", "amqp exchange name"],
        ["amqp-exchange-type", None, "direct", "amqp exchange type"],
        ["amqp-channel", None, 1, "amqp channel number", int],
    ]


class ServiceMaker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = "cyclone-sse"
    description = "SSE (EventSource) broadcasting server"
    options = Options

    def makeService(self, options):
        srv = service.MultiService()
        s = None

        if options["app"]:
            app = reflect.namedAny(options["app"])
        else:
            app = App

        # http
        s = internet.TCPServer(options["port"], app(options),
                               interface=options["listen"])
        s.setServiceParent(srv)

        # https
        if options["use-ssl"]:
            if ssl_support:
                s = internet.SSLServer(options["ssl-port"], app(options),
                                       ssl.DefaultOpenSSLContextFactory(
                                       options["ssl-key"],
                                       options["ssl-cert"]),
                                       interface=options["ssl-listen"])
                s.setServiceParent(srv)
            else:
                print("SSL is not supported. Please install PyOpenSSL.")

        if s is None:
            print("Nothing to do. Try --help")
            sys.exit(1)

        return srv

serviceMaker = ServiceMaker()