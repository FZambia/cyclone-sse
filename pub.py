#!/usr/bin/env python
import pika
import sys
import json
connection = pika.BlockingConnection(pika.ConnectionParameters(
          host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='test',
                         type='fanout')

message = json.dumps(['comment', '123'])
channel.basic_publish(exchange='test',
                      routing_key='base',
                      body=message)
print " [x] Sent %r" % (message,)
connection.close()
