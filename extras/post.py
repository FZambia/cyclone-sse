# coding: utf:8
"""
help script to test http broker
"""
import urllib
import urllib2
import json
import sys

channel = sys.argv[1]

try:
    port = sys.argv[2]
except:
    port = '8888'

if __name__ == '__main__':
    data = {'channel': channel, 'message': json.dumps([123, 124])}
    encoded = urllib.urlencode(data)
    urllib2.urlopen("http://localhost:%s/publish" % port, encoded, timeout=2)
