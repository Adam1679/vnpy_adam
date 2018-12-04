# coding:utf8
# csv导入到mongo的datetime是unicode编码，不是日期时间的格式。需要进行转换。
# author:zls

import pymongo
import datetime

dbClient = pymongo.MongoClient('127.0.0.1', 27017)
collection = dbClient['crude']['bar_5min']
data = collection.find()
# print(type(data['datetime']))
for i in data:
    if not isinstance(i['datetime'], datetime.datetime):
        d = i['datetime']
        year = int(d[:4])
        month = int(d[5:7])
        day = int(d[8:10])
        hour = int(d[11:13])
        minute = int(d[14:16])
        i['datetime'] = datetime.datetime(year, month, day, hour, minute)
        collection.find_and_modify({'datetime': d}, i)
# print(data.count())
