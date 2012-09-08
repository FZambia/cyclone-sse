import urllib
import urllib2
import json
data = {'channel': 'base', 'message':json.dumps([123, 124])}

encoded = urllib.urlencode(data)

urllib2.urlopen("http://localhost:8888/publish", encoded, timeout=2)