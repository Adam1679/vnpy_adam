# coding=utf-8
import csv
from datetime import datetime, timedelta
from time import time
import pymongo
from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData


def loadCoinCsv(fileName, dbName, symbol):
    """
        将数字货币数据导出的csv格式的历史分钟数据插入到Mongo数据库中
    """
    start = time()
    print('开始读取CSV文件%s中的数据插入到%s的%s中' % (fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient('localhost', 27017)
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    reader = csv.reader(open(fileName, "r"))
    i = 0
    for d in reader:
        if i != 0:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol, bar.exchange = symbol, "Nan"

            bar.datetime = datetime.strptime(d[9], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y%m%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')
            if bar.datetime:
                bar.high = float(d[-1])
                bar.low = float(d[-1])
                bar.open = float(d[-1])
                bar.close = float(d[-1])
                bar.volume = float(d[6])

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)
            print('%s \t %s' % (bar.date, bar.time))

        i += 1

    print('插入完毕，耗时：%s' % (time() - start))

if __name__ == "__main__":
    loadCoinCsv('data/crude2.csv', "test", 'dif_price')