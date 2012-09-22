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

from cyclone_sse.handlers import BroadcastHandler
from cyclone_sse.handlers import PublishHandler
from cyclone_sse.handlers import StatsHandler

from cyclone_sse.brokers import HttpBroker
from cyclone_sse.brokers import RedisBroker
from cyclone_sse.brokers import AmqpBroker


class App(cyclone.web.Application):
    def __init__(self, settings):
        handlers = [
            (r"/", BroadcastHandler),
            (r"/stats", StatsHandler),
        ]

        if settings["broker"] == 'amqp':
            broker = AmqpBroker
        elif settings["broker"] == 'redis':
            broker = RedisBroker
        else:
            broker = HttpBroker
            handlers.append((r"/publish", PublishHandler))

        self.broker = broker(settings)
        cyclone.web.Application.__init__(self, handlers)

