 # encoding: UTF-8

'''
vn.oanda的gateway接入

由于OANDA采用的是外汇做市商的交易模式，因此和国内接口方面有若干区别，具体如下：

* 行情数据反映的是OANDA的报价变化，因此只有买卖价，而没有成交价

* OANDA的持仓管理分为单笔成交持仓（Trade数据，国内没有）
  和单一资产汇总持仓（Position数据）

* OANDA系统中的所有时间都采用UTC时间（世界协调时，中国是UTC+8）

* 由于采用的是外汇做市商的模式，用户的限价委托当价格被触及时就会立即全部成交，
  不会出现部分成交的情况，因此委托状态只有已报、成交、撤销三种

* 外汇市场采用24小时交易，因此OANDA的委托不像国内收盘后自动失效，需要用户指定
  失效时间，本接口中默认设置为24个小时候失效
'''
import sys

sys.path.append('..')
sys.path.append('../../')

import logging
# from vtFunction import AppLoger
#
# apploger = AppLoger()
# apploger.set_log_level(logging.INFO)
# agentLog = apploger.get_logger()

import os
import json
import datetime

from vnpy.api.oanda import OandaApiV3
from vnpy.trader.vtGateway import *
from vnpy.trader.vtFunction import getJsonPath

# 价格类型映射
priceTypeMap = {}
priceTypeMap[PRICETYPE_LIMITPRICE] = 'limit'
priceTypeMap[PRICETYPE_MARKETPRICE] = 'market'
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()}

# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = 'buy'
directionMap[DIRECTION_SHORT] = 'sell'
directionMapReverse = {v: k for k, v in directionMap.items()}


########################################################################
class OandaGateway(VtGateway):
    """OANDA接口"""

    # ----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='OANDA'):
        """Constructor"""
        super(OandaGateway, self).__init__(eventEngine, gatewayName)

        self.api = ApiV3(self)

        self.qryEnabled = False  # 是否要启动循环查询

    # ----------------------------------------------------------------------
    def connect(self):
        """连接"""
        # print '+'*30,'connect','+'*30
        # 载入json文件
        fileName = self.gatewayName + '_connect.json'
        path = os.path.abspath(os.path.dirname(__file__))
        fileName = os.path.join(path, fileName)

        try:
            f = file(fileName)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取连接配置出错，请检查'
            self.onLog(log)
            return

        # 解析json文件
        setting = json.load(f)
        try:
            token = str(setting['token'])
            accountId = str(setting['accountId'])
            settingName = str(setting['settingName'])
        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return

            # 初始化接口
        self.api.init(settingName, token, accountId)
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'接口初始化成功'
        self.onLog(log)

        # 查询信息
        self.api.qryInstruments()
        self.api.qryOrders()
        self.api.qryTrades()

        # 初始化并启动查询
        self.initQuery()

    # ----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""

        pass

    # ----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        return self.api.sendOrder_(orderReq)

    # ----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.api.cancelOrder_(cancelOrderReq)

    # ----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户资金"""
        self.api.getAccountInfo()

    # ----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.api.getPositions()

    # ----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.api.exit()

    # ----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryAccount, self.qryPosition, self.qryTick]

            self.qryCount = 0  # 查询触发倒计时
            self.qryTrigger = 1  # 查询触发点
            self.qryNextFunction = 0  # 上次运行的查询函数索引
            self.startQuery()

    def qryTick(self):
        # print '+'*30,'qryTick','+'*30
        self.api.getPrices({'instruments': 'WTICO_USD'})
        self.api.getPrices({'instruments': 'BCO_USD'})
        self.api.getPrices({'instruments': 'USD_CNH'})
        # self.api.sendRequest(1, {'instruments': 'WTICO_USD'}, self.api.onPrice)




    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)

    # ----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled


########################################################################
'''
class Api(OandaApi):
    """OANDA的API实现"""

    # ----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(Api, self).__init__()

        self.gateway = gateway  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称

        self.orderDict = {}  # 缓存委托数据

    # ----------------------------------------------------------------------
    def onError(self, error, reqID):
        """错误信息回调"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorMsg = error
        self.gateway.onError(err)

    # ----------------------------------------------------------------------
    def onGetInstruments(self, data, reqID):
        """回调函数"""
        if not 'instruments' in data:
            return
        l = data['instruments']
        for d in l:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName

            contract.symbol = d['instrument']
            contract.name = d['displayName']
            contract.exchange = EXCHANGE_OANDA
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            contract.priceTick = float(d['pip'])
            contract.size = 1
            contract.productClass = PRODUCT_FOREX
            self.gateway.onContract(contract)

        self.writeLog(u'交易合约信息查询完成')

    # ----------------------------------------------------------------------
    def onGetAccountInfo(self, data, reqID):
        """回调函数"""
        account = VtAccountData()
        account.gatewayName = self.gatewayName

        account.accountID = str(data['accountId'])
        account.vtAccountID = '.'.join([self.gatewayName, account.accountID])

        account.available = data['marginAvail']
        account.margin = data['marginUsed']
        account.closeProfit = data['realizedPl']
        account.positionProfit = data['unrealizedPl']
        account.balance = data['balance']

        self.gateway.onAccount(account)

    # ----------------------------------------------------------------------
    def onGetOrders(self, data, reqID):
        """回调函数"""
        if not 'orders' in data:
            return
        l = data['orders']

        for d in l:
            order = VtOrderData()
            order.gatewayName = self.gatewayName

            order.symbol = d['instrument']
            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])

            order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED  # OANDA查询到的订单都是活动委托

            order.price = d['price']
            order.totalVolume = d['units']
            order.orderTime = getTime(d['time'])

            order.vtOrderID = '.'.join([self.gatewayName, order.orderID])

            self.gateway.onOrder(order)

            self.orderDict[order.orderID] = order

        self.writeLog(u'委托信息查询完成')

    # ----------------------------------------------------------------------
    def onGetPositions(self, data, reqID):
        """回调函数"""
        if not 'positions' in data:
            return
        l = data['positions']

        for d in l:
            pos = VtPositionData()
            pos.gatewayName = self.gatewayName

            pos.symbol = d['instrument']
            pos.exchange = EXCHANGE_OANDA
            pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
            pos.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            pos.position = d['units']
            pos.price = d['avgPrice']
            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])

            self.gateway.onPosition(pos)

    # ----------------------------------------------------------------------
    def onGetTransactions(self, data, reqID):
        """回调函数"""
        if not 'transactions' in data:
            return
        l = data['transactions']

        for d in l:
            # 这里我们只关心委托成交
            if d['type'] == 'ORDER_FILLED':
                trade = VtTradeData()
                trade.gatewayName = self.gatewayName

                trade.symbol = d['instrument']
                trade.exchange = EXCHANGE_OANDA
                trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
                trade.tradeID = str(d['id'])
                trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
                trade.orderID = str(d['orderId'])
                trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])
                trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
                trade.offset = OFFSET_NONE
                trade.price = d['price']
                trade.volume = d['units']
                trade.tradeTime = getTime(d['time'])

                self.gateway.onTrade(trade)

        self.writeLog(u'成交信息查询完成')

    # ----------------------------------------------------------------------
    def onPrice(self, data):
        """行情推送"""
        if 'tick' not in data:
            return
        d = data['tick']

        tick = VtTickData()
        tick.gatewayName = self.gatewayName

        tick.symbol = d['instrument']
        tick.exchange = EXCHANGE_OANDA
        tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
        tick.bidPrice1 = d['bid']
        tick.askPrice1 = d['ask']
        tick.time = getTime(d['time'])

        # 做市商的TICK数据只有买卖的报价，因此最新价格选用中间价代替
        tick.lastPrice = (tick.bidPrice1 + tick.askPrice1) / 2
        # agentLog.info("tick is %s " % tick)
        self.gateway.onTick(tick)

    # ----------------------------------------------------------------------
    def onEvent(self, data):
        """事件推送（成交等）"""
        if 'transaction' not in data:
            return

        d = data['transaction']

        # 委托成交
        if d['type'] == 'ORDER_FILLED':
            # 推送成交事件
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName

            trade.symbol = d['instrument']
            trade.exchange = EXCHANGE_OANDA
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])

            trade.tradeID = str(d['id'])
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])

            trade.orderID = str(d['orderId'])
            trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])

            trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            trade.offset = OFFSET_NONE

            trade.price = d['price']
            trade.volume = d['units']
            trade.tradeTime = getTime(d['time'])

            self.gateway.onTrade(trade)

            # 推送委托事件
            order = self.orderDict.get(str(d['orderId']), None)
            if not order:
                return
            order.status = STATUS_ALLTRADED
            self.gateway.onOrder(order)

            # 委托下达
        elif d['type'] in ['MARKET_ORDER_CREATE', 'LIMIT_ORDER_CREATE']:
            order = VtOrderData()
            order.gatewayName = self.gatewayName

            order.symbol = d['instrument']
            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])
            order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED
            order.price = d['price']
            order.totalVolume = d['units']
            order.orderTime = getTime(d['time'])
            order.vtOrderID = '.'.join([self.gatewayName, order.orderID])

            self.gateway.onOrder(order)
            self.orderDict[order.orderID] = order

        # 委托撤销
        elif d['type'] == 'ORDER_CANCEL':
            order = self.orderDict.get(str(d['orderId']), None)
            if not order:
                return
            order.status = STATUS_CANCELLED
            self.gateway.onOrder(order)

    # ----------------------------------------------------------------------
    def writeLog(self, logContent):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = logContent
        self.gateway.onLog(log)

    # ----------------------------------------------------------------------
    def qryInstruments(self):
        """查询合约"""
        params = {'accountId': self.accountId}
        self.getInstruments(params)

    # ----------------------------------------------------------------------
    def qryOrders(self):
        """查询委托"""
        self.getOrders({})

    # ----------------------------------------------------------------------
    def qryTrades(self):
        """查询成交"""
        # 最多查询100条记录
        self.getTransactions({'count': 100})

    # ----------------------------------------------------------------------
    def sendOrder_(self, orderReq):
        """发送委托"""
        params = {}
        params['instrument'] = orderReq.symbol
        params['units'] = orderReq.volume
        params['side'] = directionMap.get(orderReq.direction, '')
        params['price'] = orderReq.price
        params['type'] = priceTypeMap.get(orderReq.priceType, '')

        # 委托有效期24小时
        expire = datetime.datetime.now() + datetime.timedelta(days=1)
        params['expiry'] = expire.isoformat('T') + 'Z'

        self.sendOrder(params)

    # ----------------------------------------------------------------------
    def cancelOrder_(self, cancelOrderReq):
        """撤销委托"""
        self.cancelOrder(cancelOrderReq.orderID)


# ----------------------------------------------------------------------
def getTime(t):
    """把OANDA返回的时间格式转化为简单的时间字符串"""
    return t[11:19]

'''
# oanda v20 版本的api
########################################################################
class ApiV3(OandaApiV3):
    """OANDA的API实现"""


    # ----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(ApiV3, self).__init__()

        self.gateway = gateway  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称

        self.orderDict = {}  # 缓存委托数据

    # ----------------------------------------------------------------------
    def onError(self, error, reqID):
        """错误信息回调"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorMsg = error
        self.gateway.onError(err)

    # ----------------------------------------------------------------------
    def onGetInstruments(self, data, reqID):
        """回调函数"""
        if not 'instruments' in data:
            return
        l = data['instruments']
        for d in l:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName
            contract.symbol = d['displayName']
            contract.name = d['name']
            contract.exchange = EXCHANGE_OANDA
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            iDisplayPrecision = int(d['displayPrecision'])
            contract.priceTick = "%.5f" % (float(1) / pow(10, iDisplayPrecision))
            contract.size = 1
            contract.productClass = PRODUCT_FOREX
            self.gateway.onContract(contract)

        self.writeLog(u'交易合约信息查询完成')

    # def getPrices(self, params):
    #     OandaApiV3.getPrices(params)

    # ----------------------------------------------------------------------
    def onGetAccountInfo(self, data, reqID):
        """回调函数"""
        account = VtAccountData()
        account.gatewayName = self.gatewayName

        # V20和V1有很大不同具体去下面链接查
        # http://developer.oanda.com/rest-live-v20/account-ep/
        if not 'account' in data:
            return
        d = data['account']
        account.accountID = str(d['id'])
        account.vtAccountID = '.'.join([self.gatewayName, account.accountID])
        account.available = d['marginAvailable']
        account.margin = d['marginUsed']
        account.closeProfit = d['resettablePL']
        account.positionProfit = d['unrealizedPL']
        account.balance = d['balance']

        self.gateway.onAccount(account)

    # ----------------------------------------------------------------------
    def onGetOrders(self, data, reqID):
        """回调函数"""
        if not 'orders' in data:
            return
        l = data['orders']

        for d in l:
            order = VtOrderData()
            order.gatewayName = self.gatewayName
            # 下面3中订单没有instument字段
            if d['type'] in ['STOP_LOSS', 'TAKE_PROFIT', 'TRAILING_STOP_LOSS']:
                order.symbol = 'UNKOWN'
            else:
                order.symbol = d['instrument']
                # self.orderInstrument.append(order.symbol)

            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])
            # v20消息没有side字段
            # order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            if int(d['units']) > 0:
                trade.direction = directionMap[DIRECTION_LONG]
            elif int(d['units']) < 0:
                trade.direction = directionMap[DIRECTION_SHORT]

            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED  # OANDA查询到的订单都是活动委托
            order.price = float(d['price'])
            order.totalVolume = int(d['units'])
            order.orderTime = getTime(d['createTime'])
            order.vtOrderID = '.'.join([self.gatewayName, order.orderID])

            self.gateway.onOrder(order)

            self.orderDict[order.orderID] = order

        self.writeLog(u'委托信息查询完成')

    # ----------------------------------------------------------------------
    def onGetPositions(self, data, reqID):
        """回调函数"""
        if not 'positions' in data:
            return
        l = data['positions']

        for d in l:
            pos = VtPositionData()
            pos.gatewayName = self.gatewayName

            pos.symbol = d['instrument']
            pos.exchange = EXCHANGE_OANDA
            pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
            # v20消息没有side字段
            # pos.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            longPosition = d['long']
            if int(longPosition['units']) > 0:
                pos.direction = directionMap[DIRECTION_LONG]
                pos.position = longPosition['units']
                pos.price = longPosition['averagePrice']
            elif int(longPosition['units']) < 0:
                pos.direction = directionMap[DIRECTION_SHORT]
                pos.position = longPosition['units']
                pos.price = longPosition['averagePrice']

            shortPosition = d['short']
            if int(shortPosition['units']) > 0:
                pos.direction = directionMap[DIRECTION_SHORT]
                pos.position = shortPosition['units']
                pos.price = shortPosition['averagePrice']
            elif int(shortPosition['units'] < 0):
                pos.direction = directionMap[DIRECTION_LONG]
                pos.position = shortPosition['units']
                pos.price = shortPosition['averagePrice']

            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])

            self.gateway.onPosition(pos)

    # ----------------------------------------------------------------------
    def onGetTransactions(self, data, reqID):
        """回调函数"""
        if not 'count' in data:
            return
        idrange = int(data['count'])

        for idTransaction in range(1, idrange + 1):
            self.getTransactionInfo(optional=str(idTransaction))

    # ---------------------------------------------------------------------
    def onGetTransactionInfo(self, data, reqID):
        if not 'transaction' in data:
            return
        d = data['transaction']

        # for d in l:
        # 这里我们只关心委托成交
        # print d['type']
        if d['type'] == 'ORDER_FILL':
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName

            trade.symbol = d['instrument']
            trade.exchange = EXCHANGE_OANDA
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
            trade.tradeID = str(d['id'])
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
            trade.orderID = str(d['orderID'])
            trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])
            # v20版本的消息没有方向的字段
            # trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            if int(d['units']) > 0:
                trade.direction = directionMap[DIRECTION_LONG]
            elif int(d['units']) < 0:
                trade.direction = directionMap[DIRECTION_SHORT]

            # trade.direction = d['type']
            trade.offset = OFFSET_NONE
            trade.price = float(d['price'])
            trade.volume = int(d['units'])
            trade.tradeTime = getTime(d['time'])

            self.gateway.onTrade(trade)

            self.writeLog(u'成交信息查询完成')

    # ----------------------------------------------------------------------
    def onPrice(self, data, reqID):
        """行情推送"""
        # print '----------------onPrice------------------\n',data
        # if 'type' in data:
        #     return
        d = data['prices'][0]

        if d['type'] == 'PRICE':
            tick = VtTickData()
            tick.gatewayName = self.gatewayName

            tick.symbol = d['instrument']
            tick.exchange = EXCHANGE_OANDA
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            # 取出价格列表里最后一个报价
            tick.bidPrice1 = d['bids'][-1]['price']
            tick.askPrice1 = d['asks'][-1]['price']
            tick.time = getTime(d['time'])
            tick.date = getDate(d['time'])

            # 做市商的TICK数据只有买卖的报价，因此最新价格选用中间价代替
            tick.lastPrice = (float(tick.bidPrice1) + float(tick.askPrice1)) / 2.0

            # agentLog.info("get tick %s" % d)
            # print '-------------------tick----------------\n', tick.symbol, tick.bidPrice1, tick.askPrice1, tick.time
            self.gateway.onTick(tick)


            # 待修改
            bar = VtBarData()
            bar.symbol = tick.symbol
            bar.vtSymbol = tick.vtSymbol
            bar.gatewayName = self.gatewayName

            # bar.datetime = datetime.fromtimestamp(float(d['time']) / 1e3)
            bar.date = tick.date
            bar.time = tick.time.split(':')[0] + ':' + tick.time.split(':')[1] + ':00.0'
            bar.close = tick.lastPrice
            self.gateway.onKLine(bar)

        else:
            print "heartbeat"

    def generateDateTime(self, s):
        """生成时间"""
        dt = datetime.fromtimestamp(float(s) / 1e3)
        # datetime.fromtimestamp(int(s) / 1e3)
        time = dt.strftime("%H:%M:%S.%f")
        date = dt.strftime("%Y%m%d")
        return date, time

    # ----------------------------------------------------------------------
    def onEvent(self, data):
        """事件推送（成交等）"""

        # if 'transaction' not in data:
        #     return
        # print "enter onEvent"
        # d = data['transaction']
        d = data
        # v20 版本的数据流
        # 委托成交
        if d['type'] == 'ORDER_FILL':
            # 推送成交事件
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName

            trade.symbol = d['instrument']
            trade.exchange = EXCHANGE_OANDA
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])

            trade.tradeID = str(d['id'])
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])

            trade.orderID = str(d['orderID'])
            trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])

            # trade.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            # v20 没有side字段
            if int(d['units']) > 0:
                trade.direction = directionMap[DIRECTION_LONG]
            elif int(d['units']) < 0:
                trade.direction = directionMap[DIRECTION_SHORT]

            trade.offset = OFFSET_NONE

            trade.price = float(d['price'])
            trade.volume = int(d['units'])
            trade.tradeTime = getTime(d['time'])

            self.gateway.onTrade(trade)

            # 推送委托事件
            order = self.orderDict.get(str(d['orderID']), None)
            if not order:
                return
            order.status = STATUS_ALLTRADED
            self.gateway.onOrder(order)

            # 委托下达
        elif d['type'] in ['MARKET_ORDER', 'LIMIT_ORDER']:
            order = VtOrderData()
            order.gatewayName = self.gatewayName

            order.symbol = d['instrument']
            order.exchange = EXCHANGE_OANDA
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderID = str(d['id'])
            # order.direction = directionMapReverse.get(d['side'], DIRECTION_UNKNOWN)
            # v20没有side字段
            if int(d['units']) > 0:
                trade.direction = directionMap[DIRECTION_LONG]
            elif int(d['units']) < 0:
                trade.direction = directionMap[DIRECTION_SHORT]

            order.offset = OFFSET_NONE
            order.status = STATUS_NOTTRADED
            order.price = float(d['price'])
            order.totalVolume = int(d['units'])
            order.orderTime = getTime(d['time'])
            order.vtOrderID = '.'.join([self.gatewayName, order.orderID])

            self.gateway.onOrder(order)
            self.orderDict[order.orderID] = order

        # 委托撤销
        elif d['type'] == 'ORDER_CANCEL':
            order = self.orderDict.get(str(d['orderID']), None)
            if not order:
                return
            order.status = STATUS_CANCELLED
            self.gateway.onOrder(order)

    # ----------------------------------------------------------------------
    def writeLog(self, logContent):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = logContent
        self.gateway.onLog(log)

    # ----------------------------------------------------------------------
    def qryInstruments(self):
        """查询合约"""
        params = {}
        self.getInstruments(params)

    # ----------------------------------------------------------------------
    def qryOrders(self):
        """查询委托"""
        self.getOrders({})

    # ----------------------------------------------------------------------
    def qryTrades(self):
        """查询成交"""
        # 最多查询100条记录
        self.getTransactions({'count': 100})

    # ----------------------------------------------------------------------
    def sendOrder_(self, orderReq):
        """发送委托"""
        params = {}
        params['instrument'] = orderReq.symbol
        params['units'] = orderReq.volume
        params['side'] = directionMap.get(orderReq.direction, '')
        params['price'] = orderReq.price
        params['type'] = priceTypeMap.get(orderReq.priceType, '')

        # 委托有效期24小时
        expire = datetime.datetime.now() + datetime.timedelta(days=1)
        params['expiry'] = expire.isoformat('T') + 'Z'
        self.sendOrder(params)

    # ----------------------------------------------------------------------
    def cancelOrder_(self, cancelOrderReq):
        """撤销委托"""
        self.cancelOrder(cancelOrderReq.orderID)


# ----------------------------------------------------------------------
def getTime(t):
    """把OANDA返回的时间格式转化为简单的时间字符串"""
    return t[11:-4]

def getDate(time):
    return time[0:4] + time[5:7] + time[8:10]


# ----------------------------------------------------------------------
def test():
    """测试"""
    # from PyQt4 import QtCore
    import sys

    # def print_log(event):
    #     log = event.dict_['data']
    #     # print ':'.join([log.logTime, log.logContent])

    # app = QtCore.QCoreApplication(sys.argv)

    eventEngine = EventEngine()
    # eventEngine.register(EVENT_LOG, print_log)
    eventEngine.start()

    gateway = OandaGateway(eventEngine)
    gateway.connect()

    # sys.exit(app.exec_())


if __name__ == '__main__':
    test()
