# -*-encoding=utf8-*-
from pymongo import MongoClient
import datetime
import json

class MongoDB(object):
    def __init__(self, db, collection):
        fileName = 'param.json'
        try:
            f = file(fileName)
        except IOError:
            print('读取param参数配置出错，请检查')
        # 解析json文件-----------------------------------------------------
        mysetting = json.load(f)
        mongoHost = str(mysetting['mongoHost'])
        conn = MongoClient(mongoHost, 27017) # 参数读取

        # conn = MongoClient('localhost', 27017)    # 本机上测试用

        # conn = MongoClient('docker.host', 27017)    # 服务器上使用

        # 连接banzhuan数据库，没有则自动创建
        self.db = conn[db]
        # 使用sc_wti集合，没有则自动创建
        self.my_set = self.db[collection]


    def insertdb(self, data):
        '''插入数据（insert插入一个列表多条数据不用遍历，效率高）'''
        # example: data = {"name": "sc_wti_4param", "top": top, "top2mid": top2mid, "bottom2mid": bottom2mid, "bottom": bottom, "ct": ct}
        self.my_set.insert(data)


    def querydb(self, *args, **kwargs):
        '''查询数据（查询不到则返回None）'''
        # 查询全部
        # for i in self.my_set.find():
        #     print(i)
        #查询name=sc_wti_4param的
        # for i in self.my_set.find():
        #     print(i)
        return self.my_set.find_one(*args, **kwargs)


    def querydball(self, *args, **kwargs):
        # for i in self.my_set.find({"name":"sc_wti_4param"}):
        #     print(i)
        return self.my_set.find(*args, **kwargs)


    def querydballlimit(self, num, *args, **kwargs):
        '''倒序查询最后num条'''
        return self.my_set.find(*args, **kwargs).sort([('datetime', -1)]).limit(num)

    def updatedb(self, top, top2mid, bottom2mid, bottom, ct):
        '''仅用于todo的是个参数更新！
            my_set.update(
           <query>,    #查询条件
           <update>,    #update的对象和一些更新的操作符
           {
             upsert: <boolean>,    #如果不存在update的记录，是否插入
             multi: <boolean>,        #可选，mongodb 默认是false,只更新找到的第一条记录
             writeConcern: <document>    #可选，抛出异常的级别。
           }
        )'''
        # 如果要更新的数据不存在，就先插入
        if self.my_set.find_one({"name":"sc_wti_4param"}) is None:
            self.my_set.insert(
                {"name": "sc_wti_4param", "top": top, "top2mid": top2mid, "bottom2mid": bottom2mid, "bottom": bottom, "ct": ct})
        else:
            # 更新数据
            self.my_set.update({"name":"sc_wti_4param"},{'$set':{"top":top, "top2mid":top2mid, "bottom2mid":bottom2mid, "bottom":bottom, "ct": ct}})


if __name__ == '__main__':
    # import time
    # ct = time.localtime(int(time.time()))
    # for_mat = '%Y-%m-%d,%H:%M:%S'
    # ct = time.strftime(for_mat, ct)
    # mdb = MongoDB('banzhuan', 'sc_wti')
    # mdb.updatedb(2,3,4,5.5, ct)
    # mdb.querydb({"name":"sc_wti_4param"})
    # mdb.updatedb(4,3,4,5.5, ct)
    # mdb.updatedb(5,3,5,5.5, ct)
    # mdb.updatedb(6,3,4,5.5, ct)
    # mdb.querydb({"name":"sc_wti_4param"})

    # mdb_cnh = MongoDB('VnTrader_1Min_Db', 'USD_CNH.OANDA')
    # # data = mdb_cnh.querydball({"close":{"$gte":6.635}})
    # query = {"datetime": {"$gte": datetime.datetime(2018, 7, 9, 7, 46)}}
    # data = mdb_cnh.querydball(query)
    # for i in data:
    #     # 将标准时间转换为北京时间
    #     if i['datetime'].minute%5==0:
    #         # print(i['datetime'])
    #         print(i['datetime']+datetime.timedelta(hours=8))

    # result = {}
    # nowdatetime = datetime.datetime.now()
    # monthagodatetime = nowdatetime - datetime.timedelta(days=30)
    # mdb_cnh = MongoDB('VnTrader_1Min_Db', 'USD_CNH.OANDA')
    # # mdb_wti = MongoDB('VnTrader_1Min_Db', 'WTICO_USD.OANDA')
    # # mdb_sc = MongoDB('VnTrader_1Min_Db', 'sc1809')
    # query = {"datetime": {"$gte": monthagodatetime}}
    # datacnh = mdb_cnh.querydball(query)
    # for data in datacnh:
    #     # 将标准时间转换为北京时间
    #     if data['datetime'].minute % 5 == 0:
    #         result[data['datetime']] = data['close']
    # print(result)

    m = MongoDB('crude', 'bar_5min')
    data = m.querydballlimit(5, {}, {"datetime": 1, "close": 1, "_id": 0})
    for d in data:
        print d