#!/bin/bash
SERVICE='celeryd'

if ps -u oracal -o command | grep -v grep | egrep '/home/oracal/webapps/repowatcher/manage.py celeryd' > /dev/null
then
   echo "$SERVICE running, nothing done"
else
   echo "$SERVICE not running, starting..."
   /home/oracal/.virtualenvs/repowatcher/bin/python /home/oracal/webapps/repowatcher/manage.py celeryd -l info --concurrency=100 --pool=eventlet &
fi
