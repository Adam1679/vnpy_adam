# coding:utf8
# 转换时间格式后发现时间非连续的，有错乱，需要按照datetime排序。
# author:zls
# date：2018-10-09

import pymongo
import datetime

dbClient = pymongo.MongoClient('127.0.0.1', 27017)
collection = dbClient['crude']['bar_5min']
collection2 = dbClient['crude']['bar_5min2']
data = collection.find()
data.sort('datetime')
for i in data:
    collection2.insert_one(i)
