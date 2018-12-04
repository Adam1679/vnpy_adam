import redis

rd = redis.Redis(host="172.17.0.1", port=6379, db=8)

rd.set('a', '123')
a = float(rd.get('a'))
