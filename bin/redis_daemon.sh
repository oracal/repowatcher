#!/bin/bash
SERVICE='redis_results'

if ps -u oracal -o command | grep -v grep | egrep '/home/oracal/bin/redis-server /home/oracal/var/redis/redis_results.conf' > /dev/null
then
   echo "$SERVICE running, nothing done"
else
   echo "$SERVICE not running, starting..."
   /home/oracal/bin/redis-server /home/oracal/var/redis/redis_results.conf &
fi
SERVICE='redis_cache'

if ps -u oracal -o command | grep -v grep | egrep '/home/oracal/bin/redis-server /home/oracal/var/redis/redis_cache.conf' > /dev/null
then
   echo "$SERVICE running, nothing done"
else
   echo "$SERVICE not running, starting..."
   /home/oracal/bin/redis-server /home/oracal/var/redis/redis_cache.conf &
fi
SERVICE='redis_broker'

if ps -u oracal -o command | grep -v grep | egrep '/home/oracal/bin/redis-server /home/oracal/var/redis/redis_broker.conf' > /dev/null
then
   echo "$SERVICE running, nothing done"
else
   echo "$SERVICE not running, starting..."
   /home/oracal/bin/redis-server /home/oracal/var/redis/redis_broker.conf &
fi
