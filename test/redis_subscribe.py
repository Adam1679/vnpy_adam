# -*-coding:utf8-*-
"""
@Author     zls
@Datetime   11/18/18 12:12 PM
"""

import redis

r = redis.Redis(host='localhost', port=6379, db=8)

p = r.pubsub()
p.subscribe(['test1'])

for item in p.listen():
    if item['type'] == 'message':
        print(item['channel'])
        print(item['data'])