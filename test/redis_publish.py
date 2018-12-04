import redis
import time
import datetime

r = redis.Redis(host='localhost', port=6379, db=8)

while True:
    r.publish('test1', datetime.datetime.now())
    time.sleep(60)
