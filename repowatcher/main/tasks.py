from celery.exceptions import SoftTimeLimitExceeded
from celery.task import task
from eventlet.green import urllib2
import eventlet
import json
import requests
import urllib


#@task
#def get_events(url, **kwargs):
#    try:
#        r = requests.get(url, params=kwargs)
#        try:
#            events = json.loads(r.text)
#        except ValueError:
#            events = None
#    except SoftTimeLimitExceeded:
#        events = None
#    return events

json = eventlet.import_patched('json')
@task
def get_events(url):
    try:
        body = urllib2.urlopen(url).read()
        events = json.loads(body)
    except Exception:
        events = None
    return events
