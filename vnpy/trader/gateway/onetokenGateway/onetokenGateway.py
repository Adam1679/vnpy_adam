# encoding: UTF-8
import os
import json
from datetime import datetime
from time import sleep
from copy import copy
from threading import Condition
from Queue import Queue
from threading import Thread
from time import sleep

from vnpy.api.okcoin import vnokcoin
from vnpy.trader.language.english.constant import *
from vnpy.trader.vtGateway import *
from vnpy.trader.vtFunction import getJsonPath
from vnpy.api.zls_api_test.onetoken.websocketApi2 import onetokenWebsocketApi
from vnpy.trader.language import text
# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = 'b'
directionMap[DIRECTION_SHORT] = 's'
directionMapReverse = {v: k for k, v in directionMap.items()}
SECRET = 'tRJs6HQP-cnpMnEB7-T9xRGOGM-TOusHtG7'
API_KEY = '9rsmJL65-ztLxddIV-H1a2c1xw-gcwWTFOM'

class onetokenGateway(VtGateway):
    """1Token接口"""

    def __init__(self, eventEngine, gatewayName='ONETOKEN'):
        """Constructor"""
        super(onetokenGateway, self).__init__(eventEngine, gatewayName)
        self.api = Api(self)
        self.rest_api = None
        self.leverage = 0
        self.sync_orders = False
        self.connected = False
        self.fileName = self.gatewayName + '_connect.json'
        self.filePath = getJsonPath(self.fileName, __file__)             
        
    def connect(self):
        """连接"""
        # 载入json文件
        try:
            f = file(self.filePath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取连接配置出错，请检查'
            self.onLog(log)
            return
        
        # 解析json文件
        setting = json.load(f)
        try:
            apiKey = str(setting['apiKey'])
            secretKey = str(setting['secretKey'])
            account = str(setting['account'])

        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return
        self.api.active = True
        self.api.connect(account, apiKey, secretKey)
        
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'接口初始化成功'
        self.onLog(log)
        
        # 启动查询
        self.initQuery()
        self.startQuery()
    
    def subscribe(self, subscribeReq):
        """订阅行情, 暂时默认为Tick数据"""
        symbol = subscribeReq.symbol
        exchange = subscribeReq.exchange
        contract = "%s/%s" % (exchange, symbol)
        self.api.subscribeTick(contract)
        
    def sendOrder(self, orderReq):
        """发单"""
        # return self.api.spotSendOrder(orderReq)
        return self.api.SendOrder(orderReq)

    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        # self.api.spotCancel(cancelOrderReq)
        self.api.Cancel(cancelOrderReq)

    # 查询最近提交的订单信息
    def qryOrders(self, event):
        # TODO:
        contracts = ["huobip/btc.usdt"]
        for contract in contracts:
            order_info = self.api.qryOrder(contract=contract)
            for data in order_info:
                self.api.onQryOrder(data)
                sleep(1)

    def close(self):
        """关闭"""
        self.api.active = False
        self.api.close()
        
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryAccount, self.qryPosition]
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 2         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()  
    
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
                
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
        if self.sync_orders:
            self.eventEngine.register(EVENT_TIMER_30_MINUTES, self.qryOrders)

    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled

    def qryAccount(self):
        """查询账户资金"""
        data = self.api.qryAccount()
        self.api.onSpotUserInfo(data)

    def qryPosition(self):
        """查询持仓"""
        data = self.api.qryAccount()
        position_info = data['position']
        self.api.onPosition(position_info)

    def qryTrasaction(self):
        """查询持仓
        {
    "account": "binance/test_account",                  # 账户名
    "contract": "binance/ltc.usdt",                     # 合约标识
    "bs": "b",                                          # "b"对应买或"s"对应卖
    "client_oid": "binance/ltc.usdt-xxx123",            # 由用户给定或由OneToken系统生成的订单追踪ID
    "exchange_oid": "binance/ltc.usdt-xxx456",          # 由交易所生成的订单追踪ID
    "exchange_tid": "binance/ltc.usdt-xxx789",          # 由交易所生成的成交ID
    "dealt_amount": 1,                                  # 成交数量
    "dealt_price": 0,                                   # 成交价格
    "dealt_time": "2018-04-03T12:22:56+08:00",          # 成交时间
    "dealt_type": "maker",                              # 主动成交"taker"、被动成交"maker"
    "commission": 0.0025,                               # 成交手续费
    "commission_currency": "ltc",                       # 手续费币种
    "tags": {}                                          #
}
"""

        data = self.api.qryTrasaction()
        self.api.onTrasaction(data)


########################################################################
class Api(onetokenWebsocketApi):
    def __init__(self, gateway):
        """Constructor"""
        super(Api, self).__init__()
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.active = False             # 若为True则会在断线后自动重连

        self.cbDict = {}
        self.tickDict = {}
        self.klineDict = {}
        self.orderDict = {}
        
        self.localNo = 0                # 本地委托号
        self.localNoQueue = Queue()     # 未收到系统委托号的本地委托号队列
        self.localNoDict = {}           # key为本地委托号，value为系统委托号
        self.orderIdDict = {}           # key为系统委托号，value为本地委托号
        self.cancelDict = {}            # key为本地委托号，value为撤单请求

        self.initCallback()
        
    def onMessage(self, ws, evt):
        """信息推送"""
        if ws.data_type == 'bar' or ws.data_type == 'tick':
            data = self.readData(evt)
            if 'uri' in data.keys():
                if data['uri'] == "auth" or data['uri'] == "pong":
                    return
            # print(data)
        else:
            data = json.loads(evt)
        if ws.data_type == 'bar' or ws.data_type == 'tick' or ws.data_type == 'info':
            callback = self.cbDict[ws.data_type]
            callback(data)
        else:
            raise ValueError("返回数据类型不对")

    # def onError(self, ws, evt):
    #     """错误推送"""
    #     error = VtErrorData()
    #     error.gatewayName = self.gatewayName
    #     error.errorMsg = str(evt)
    #     self.gateway.onError(error)
    #
    # def onClose(self, ws):
    #     """接口断开"""
    #     # 如果尚未连上，则忽略该次断开提示
    #     if not self.gateway.connected:
    #         return
    #
    #     self.gateway.connected = False
    #     self.writeLog(u'服务器连接断开')
    #
    #     # 重新连接
    #     if self.active:
    #         def reconnect():
    #             while not self.gateway.connected:
    #                 self.writeLog(u'等待10秒后重新连接')
    #                 sleep(10)
    #                 if not self.gateway.connected:
    #                     self.reconnect()
    #
    #         t = Thread(target=reconnect)
    #         t.start()
    #
    # def onOpen(self, ws):
    #     """连接成功"""
    #     self.gateway.connected = True
    #     self.writeLog(u'服务器连接成功')
    #
    #     # # 链接上就订阅相关的数据
    #     # self.subscribeTick(contract='huobip/btc.usdt')
    #     #
    #     # l = self.generateUsdContract()
    #     #
    #     # for contract in l:
    #     #     contract.gatewayName = self.gatewayName
    #     #     self.gateway.onContract(contract)

    def writeLog(self, content):
        """快速记录日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)
        
    def initCallback(self):
        """初始化回调函数"""
        # Tick数据的回调
        self.cbDict['tick'] = self.onTicker # tick
        # self.cbDict['zhubi'] = self.onZhubi # 逐笔
        self.cbDict['bar'] = self.onKLine # K线
        self.cbDict['info'] = self.onSpotUserInfo # 账户信息
        self.cbDict['trade'] = self.onTrade

    def onTicker(self, data):
        if 'data' not in data:
            return
        rawData = data['data']
        symbol = rawData['contract']
        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.vtSymbol = symbol
            tick.gatewayName = self.gatewayName
            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        

        tick.askPrice1, tick.askVolume1 = float(rawData['asks'][0]['price']), float(rawData['asks'][0]['volume'])
        tick.askPrice2, tick.askVolume2 = float(rawData['asks'][1]['price']), float(rawData['asks'][1]['volume'])
        tick.askPrice3, tick.askVolume3 = float(rawData['asks'][2]['price']), float(rawData['asks'][2]['volume'])
        tick.askPrice4, tick.askVolume4 = float(rawData['asks'][3]['price']), float(rawData['asks'][3]['volume'])
        tick.askPrice5, tick.askVolume5 = float(rawData['asks'][4]['price']), float(rawData['asks'][4]['volume'])

        tick.lastPrice = float(rawData['last'])
        tick.volume = float(rawData['volume'])
        if 'exchange_time' in rawData:
            tick.date, tick.time = generateDateTime(rawData['exchange_time'])
        else:
            now = datetime.now()
            tick.time = now.strftime("%H:%M:%S.%f")
            tick.date = now.strftime('%Y%m%d')

        newtick = copy(tick)
        self.gateway.onTick(newtick)

    def onKLine(self, data):
        if 'contract' not in data.keys():
            return
        symbol = data['contract']
        if symbol not in self.klineDict:
            bar = VtBarData()
            bar.symbol = symbol
            bar.vtSymbol = symbol
            bar.gatewayName = self.gatewayName
            self.klineDict[symbol] = bar
        else:
            bar = self.klineDict[symbol]

        bar.datetime = datetime.fromtimestamp(float(data['time'])/1e3)
        bar.date, bar.time = generateDateTime(data['time'])
        bar.open = float(data['open'])
        bar.high = float(data['high'])
        bar.low = float(data['low'])
        bar.close = float(data['close'])
        bar.volume = float(data['volume'])
        newBar = copy(bar)
        self.gateway.onKLine(newBar)

    def onSpotUserInfo(self, data):
        """账户信息推送"""
        if "position" not in data.keys():
            return
        rawData = data
        position_info = rawData['position']
        # 账户资金
        account = VtAccountData()
        account.gatewayName = self.gatewayName
        account.accountID = self.gatewayName
        account.vtAccountID = account.accountID
        account.balance = rawData['balance']
        account.info = position_info
        account.available = rawData['cash']
        self.gateway.onAccount(account)
        self.onPosition(position_info)

    def onPosition(self, position_info):
        # 现货的仓位推送
        if len(position_info) > 0:
            for info in position_info:
                if "contract" not in info.keys():
                    continue
                posUsd = VtPositionData()
                posUsd.position = info['total_amount']
                if posUsd.position > 0:
                    posUsd.direction = DIRECTION_LONG
                elif posUsd.position < 0:
                    posUsd.direction = DIRECTION_SHORT

                posUsd.gatewayName = self.gatewayName
                posUsd.symbol = info['contract']
                posUsd.exchange = self.gatewayName  # EXCHANGE_OKCOIN
                posUsd.vtSymbol = posUsd.exchange
                posUsd.vtPositionName = posUsd.vtSymbol
                posUsd.ydPosition = info['total_amount']
                posUsd.market_value = info['market_value']
                posUsd.frozen = info['frozen']
                posUsd.available = info['available']
                posUsd.type = info['type']
                if posUsd.type == "future":
                    # 期货仓位
                    posUsd.long_position = info["available_long"]
                    posUsd.short_position = info["available_short"]

                self.gateway.onPosition(posUsd)

    def onTrasaction(self, transaction_info):
        if len(transaction_info) > 0:
            for transaction in transaction_info:
                trans = VtTradeData()
                trans.symbol = transaction_info['contract']
                trans.vtSymbol = transaction_info['contract']
                trans.exchange = self.gatewayName
                if transaction_info['bs'] == 'b':
                    trans.order_type = DIRECTION_LONG
                else:
                    trans.order_type = DIRECTION_SHORT
                trans.fee = transaction_info['commission']
                trans.vtOrderID = transaction_info['exchange_oid']
                self.gateway.onTransaction(trans)

    def onQryOrder(self, data):
        if data:
            order = VtOrderData()
            order.symbol = data['contract']
            order.orderID = data['exchange_oid']
            order.direction = directionMapReverse[data['bs']]
            order.price = data["entrust_price"]
            order.tradedVolume = data['entrust_amount']
            order.tradedVolume = data['last_dealt_amount']
            order.orderTime = data['entrust_time']
            order.cancelTime = data['canceled_time']
            order.status = data['status']
            self.gateway.onOrder(order)

    def SendOrder(self, req):
        """发单"""
        # 本地委托号加1，并将对应字符串保存到队列中，返回基于本地委托号的vtOrderID
        self.localNo += 1
        self.localNoQueue.put(str(self.localNo))

        self.sendOrder(symbol=req.symbol,
                       amount=req.volume,
                       price=req.price,
                       direction=directionMap[req.direction],
                       client_oid = str(self.localNo), # 传入人工的订单号来,使用本地来记录订单号
                       )

        vtOrderID = '.'.join([self.gatewayName, str(self.localNo)])

        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.vtSymbol = req.symbol
        order.symbol = req.symbol
        order.orderID = str(self.localNo)
        order.price = req.price
        order.totalVolume = req.volume
        order.direction, offset = req.direction, req.offset
        order.orderTime = datetime.now()  # datetime.fromtimestamp(float(rawData['create_date']) / 1000)
        self.orderDict[str(self.localNo)] = order
        self.gateway.onOrder(copy(order))

    def Cancel(self, req):
        """撤单"""
        self.cancelOrder(exchange_oid=req.orderID)

    def connect(self, account, apiKey, secretKey):
        data_type_list = ['tick',
                          #'bar',
                          #'info'
                          ]
        self.login(account, apiKey, secretKey)
        for data_type in data_type_list:
            self.ws_connect(data_type=data_type)
        self.startReq()

    def onKLine(self, data):
        pass

def generateDateTime(s):
    """生成时间"""
    dt, _ = s.split("+")
    dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f")
    time = str(dt.time())
    date = str(dt.date().strftime("%Y%m%d"))
    return date, time


