#!/usr/bin/env python
import pika
import sys
import json

queue_name = sys.argv[1]

connection = pika.BlockingConnection(pika.ConnectionParameters(
          host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='sse-cyclone-server',
                         type='direct')

message = json.dumps(['comment', '123'])
channel.basic_publish(exchange='sse-cyclone-server',
                      routing_key=queue_name,
                      body=message)
print " [x] Sent %r" % (message,)
connection.close()
