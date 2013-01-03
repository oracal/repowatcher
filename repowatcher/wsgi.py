import os
import sys
import site
site.addsitedir('/home/oracal/.virtualenvs/repowatcher/lib/python2.7/site-packages')


from django.core.handlers.wsgi import WSGIHandler
os.environ["CELERY_LOADER"] = "django"
os.environ['DJANGO_SETTINGS_MODULE'] = 'repowatcher.settings'
application = WSGIHandler()
