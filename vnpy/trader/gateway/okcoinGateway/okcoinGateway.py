# encoding: UTF-8

'''
vn.okcoin的gateway接入

注意：
1. 前仅支持USD和CNY的现货交易，USD的期货合约交易暂不支持
'''


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
from vnpy.trader.vtGateway import *
from vnpy.trader.vtFunction import getJsonPath
from vnpy.api.okcoin.OkcoinFutureAPI import OKCoinFuture

# 价格类型映射
priceTypeMap = {}
priceTypeMap['buy'] = (DIRECTION_LONG, PRICETYPE_LIMITPRICE)
priceTypeMap['buy_market'] = (DIRECTION_LONG, PRICETYPE_MARKETPRICE)
priceTypeMap['sell'] = (DIRECTION_SHORT, PRICETYPE_LIMITPRICE)
priceTypeMap['sell_market'] = (DIRECTION_SHORT, PRICETYPE_MARKETPRICE)
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()}

futurePriceTypeMap = {}
futurePriceTypeMap[1] = (DIRECTION_LONG, OFFSET_OPEN)
futurePriceTypeMap[2] = (DIRECTION_SHORT, OFFSET_OPEN)
futurePriceTypeMap[3] = (DIRECTION_SHORT, OFFSET_CLOSE)
futurePriceTypeMap[4] = (DIRECTION_LONG, OFFSET_CLOSE)
futurepriceTypeMapReverse = {v: k for k, v in futurePriceTypeMap.items()}



# 方向类型映射
directionMap = {}
directionMapReverse = {v: k for k, v in directionMap.items()}

# 委托状态印射
statusMap = {}
statusMap[-1] = STATUS_CANCELLED
statusMap[0] = STATUS_NOTTRADED
statusMap[1] = STATUS_PARTTRADED
statusMap[2] = STATUS_ALLTRADED
statusMap[4] = STATUS_UNKNOWN

############################################
## 交易合约代码
############################################

# USD
BTC_USD_QUARTER = 'BTC_USD_QUARTER'
LTC_USD_QUARTER = 'LTC_USD_QUARTER'
ETH_USD_QUARTER = 'ETH_USD_QUARTER'
ETC_USD_QUARTER = 'ETC_USD_QUARTER'
BCH_USD_QUARTER = 'BCH_USD_QUARTER'

# 印射字典
spotSymbolMap = {}
# spotSymbolMap['ltc_usd'] = LTC_USD_SPOT
# spotSymbolMap['btc_usd'] = BTC_USD_SPOT
# spotSymbolMap['ltc_cny'] = LTC_CNY_SPOT
# spotSymbolMap['btc_cny'] = BTC_CNY_SPOT
# spotSymbolMap['eth_cny'] = ETH_CNY_SPOT
# spotSymbolMapReverse = {v: k for k, v in spotSymbolMap.items()}

futureSymbolMap = {}
futureSymbolMap['ltc_usd'] = LTC_USD_QUARTER
futureSymbolMap['btc_usd'] = BTC_USD_QUARTER
futureSymbolMap['eth_usd'] = ETH_USD_QUARTER
futureSymbolMap['etc_usd'] = ETC_USD_QUARTER
futureSymbolMap['bch_usd'] = BCH_USD_QUARTER
futureSymbolMapReverse = {v: k for k, v in futureSymbolMap.items()}


############################################
## Channel和Symbol的印射
############################################
channelSymbolMap = {}

# Future

channelSymbolMap['ok_sub_futureusd_btc_ticker_quarter'] = BTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_ltc_ticker_quarter'] = LTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_eth_ticker_quarter'] = ETH_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_etc_ticker_quarter'] = ETC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_bch_ticker_quarter'] = BCH_USD_QUARTER

channelSymbolMap['ok_sub_futureusd_btc_depth_quarter_20'] = BTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_ltc_depth_quarter_20'] = LTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_eth_depth_quarter_20'] = ETH_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_etc_depth_quarter_20'] = ETC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_bch_depth_quarter_20'] = BCH_USD_QUARTER

channelSymbolMap['ok_sub_futureusd_btc_kline_quarter_1min'] = BTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_ltc_kline_quarter_1min'] = LTC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_eth_kline_quarter_1min'] = ETH_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_etc_kline_quarter_1min'] = ETC_USD_QUARTER
channelSymbolMap['ok_sub_futureusd_bch_kline_quarter_1min'] = BCH_USD_QUARTER


class OkcoinGateway(VtGateway):
    """OkCoin接口"""

    def __init__(self, eventEngine, gatewayName='OKCOIN'):
        """Constructor"""
        super(OkcoinGateway, self).__init__(eventEngine, gatewayName)
        
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
            host = str(setting['host'])
            apiKey = str(setting['apiKey'])
            secretKey = str(setting['secretKey'])
            trace = setting['trace']
            leverage = setting['leverage']
            if 'sync_orders' in setting:
                self.sync_orders = setting['sync_orders']  # 是否同步历史订单信息

        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return            
        
        # 初始化接口
        self.leverage = leverage

        if host == 'CNY':
            host = vnokcoin.OKCOIN_CNY
        elif host == 'USD':
            host = vnokcoin.OKCOIN_USD
        elif host == 'OkExContract':
            host = vnokcoin.OKEX_CONTRACT
        elif host == 'OkExSpot':
            host = vnokcoin.OKEX_SPOT
        
        self.api.active = True
        self.api.connect(host, apiKey, secretKey, trace)
        okcoinRESTURL = 'www.okex.com'
        # self.rest_api = OKCoinFuture(okcoinRESTURL, apiKey, secretKey)
        
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = u'接口初始化成功'
        self.onLog(log)
        
        # 启动查询
        self.initQuery()
        self.startQuery()
    
    def subscribe(self, subscribeReq):
        """订阅行情"""
        pass
        
    def sendOrder(self, orderReq):
        """发单"""
        # return self.api.spotSendOrder(orderReq)
        return self.api.futureSendOrder(orderReq)

    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        # self.api.spotCancel(cancelOrderReq)
        self.api.futureCancel(cancelOrderReq)

    # 查询最近提交的订单信息
    def qryOrders(self, event):
        currency = ['btc_usd', 'ltc_usd']

        for symbol in currency:
            for status in [-1,0,1,2,3,4]:
                json_orders = self.api.future_orders(symbol, status)
                orders = json.loads(json_orders)
                # print(orders)
                if orders['result']:
                    self.api.onQryOrders(orders)
                sleep(1)  # api 请求频率限制

    def qryAccount(self):
        """查询账户资金"""
        # self.api.spotUserInfo()
        self.api.futureUserInfo()

    def qryPosition(self):
        """查询持仓"""
        positions = {}
        for vtSymbol in ['BTC_USD_QUARTER', 'LTC_USD_QUARTER']:
            symbol = futureSymbolMapReverse[vtSymbol]
            data = self.api.future_postion(symbol)
            # print(data)
            sleep(0.5)  # api频率限制
            posUsd = VtPositionData()
            posUsd.gatewayName = self.gatewayName
            posUsd.symbol = symbol
            posUsd.exchange = self.gatewayName # EXCHANGE_OKCOIN
            posUsd.vtSymbol = vtSymbol
            posUsd.vtPositionName = posUsd.vtSymbol
            if data:
                posUsd.long_position = data['long']
                posUsd.short_position = data['short']
            # posUsd.frozen = data['frozen_usd_display']
                self.api.gateway.onPosition(posUsd)
        # return positions

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
    


########################################################################
class Api(vnokcoin.OkCoinApi):
    """OkCoin的API实现"""

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
        data = self.readData(evt)[0]
        if 'channel' not in data:
            # print('channel not in data: {0}'.format(data))
            return
        channel = data['channel']

        # 无意义的callback
        if channel in ['addChannel', 'login', 'ok_sub_spot_key_usdt_order', 'ok_sub_spot_key_usdt_balance' ]:
            return

        callback = self.cbDict[channel]
        callback(data)
        
    def onError(self, ws, evt):
        """错误推送"""
        error = VtErrorData()
        error.gatewayName = self.gatewayName
        error.errorMsg = str(evt)
        self.gateway.onError(error)
        
    def onClose(self, ws):
        """接口断开"""
        # 如果尚未连上，则忽略该次断开提示
        if not self.gateway.connected:
            return
        
        self.gateway.connected = False
        self.writeLog(u'服务器连接断开')
        
        # 重新连接
        if self.active:
            
            def reconnect():
                while not self.gateway.connected:            
                    self.writeLog(u'等待10秒后重新连接')
                    sleep(10)
                    if not self.gateway.connected:
                        self.reconnect()
            
            t = Thread(target=reconnect)
            t.start()
        
    def onOpen(self, ws):
        """连接成功"""
        self.gateway.connected = True
        self.writeLog(u'服务器连接成功')
        
        # 连接后查询账户和委托数据
        self.login()

        # 如果连接的是USD网站则订阅期货相关回报数据
        # if self.currency == vnokcoin.CURRENCY_USD:
        self.subscribeFutureTrades()

        self.subscribeFutureTicker(vnokcoin.SYMBOL_LTC, 'quarter')
        self.subscribeFutureTicker(vnokcoin.SYMBOL_BTC, 'quarter')
        self.subscribeFutureTicker(vnokcoin.SYMBOL_ETH, 'quarter')
        self.subscribeFutureTicker(vnokcoin.SYMBOL_ETC, 'quarter')
        self.subscribeFutureTicker(vnokcoin.SYMBOL_BCH, 'quarter')

        self.subscribeFutureDepth(vnokcoin.SYMBOL_BTC, 'quarter', vnokcoin.DEPTH_20)
        self.subscribeFutureDepth(vnokcoin.SYMBOL_LTC, 'quarter', vnokcoin.DEPTH_20)
        self.subscribeFutureDepth(vnokcoin.SYMBOL_ETH, 'quarter', vnokcoin.DEPTH_20)
        self.subscribeFutureDepth(vnokcoin.SYMBOL_ETC, 'quarter', vnokcoin.DEPTH_20)
        self.subscribeFutureDepth(vnokcoin.SYMBOL_BCH, 'quarter', vnokcoin.DEPTH_20)

        self.subscribeFutureKline(vnokcoin.SYMBOL_BTC, 'quarter', '1min')
        self.subscribeFutureKline(vnokcoin.SYMBOL_LTC, 'quarter', '1min')
        self.subscribeFutureKline(vnokcoin.SYMBOL_ETH, 'quarter', '1min')
        self.subscribeFutureKline(vnokcoin.SYMBOL_ETC, 'quarter', '1min')
        self.subscribeFutureKline(vnokcoin.SYMBOL_BCH, 'quarter', '1min')


        # 返回合约信息
        # if self.currency == vnokcoin.CURRENCY_CNY:
        #     l = self.generateCnyContract()
        # else:
        l = self.generateUsdContract()
            
        for contract in l:
            contract.gatewayName = self.gatewayName
            self.gateway.onContract(contract)
            
    def writeLog(self, content):
        """快速记录日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)
        
    def initCallback(self):
        """初始化回调函数"""


        # USD_FUTURES
        self.cbDict['ok_sub_futureusd_btc_ticker_quarter'] = self.onTicker
        self.cbDict['ok_sub_futureusd_ltc_ticker_quarter'] = self.onTicker
        self.cbDict['ok_sub_futureusd_eth_ticker_quarter'] = self.onTicker
        self.cbDict['ok_sub_futureusd_etc_ticker_quarter'] = self.onTicker
        self.cbDict['ok_sub_futureusd_bch_ticker_quarter'] = self.onTicker

        self.cbDict['ok_sub_futureusd_btc_depth_quarter_20'] = self.onDepth
        self.cbDict['ok_sub_futureusd_ltc_depth_quarter_20'] = self.onDepth
        self.cbDict['ok_sub_futureusd_eth_depth_quarter_20'] = self.onDepth
        self.cbDict['ok_sub_futureusd_etc_depth_quarter_20'] = self.onDepth
        self.cbDict['ok_sub_futureusd_bch_depth_quarter_20'] = self.onDepth

        self.cbDict['ok_sub_futureusd_btc_kline_quarter_1min'] = self.onKLine
        self.cbDict['ok_sub_futureusd_ltc_kline_quarter_1min'] = self.onKLine
        self.cbDict['ok_sub_futureusd_eth_kline_quarter_1min'] = self.onKLine
        self.cbDict['ok_sub_futureusd_etc_kline_quarter_1min'] = self.onKLine
        self.cbDict['ok_sub_futureusd_bch_kline_quarter_1min'] = self.onKLine

        self.cbDict['ok_futureusd_userinfo'] = self.on_future_user_info
        self.cbDict['ok_sub_futureusd_trades'] = self.on_future_sub_trades
        self.cbDict['ok_sub_futureusd_userinfo'] = self.on_future_sub_user_info
        self.cbDict['ok_sub_futureusd_positions'] = self.on_future_sub_postions

        self.cbDict['ok_futureusd_trade'] = self.on_future_trade
        self.cbDict['ok_futureusd_cancel_order'] = self.on_future_cancel_order

    def onTicker(self, data):
        if 'data' not in data:
            return
        
        channel = data['channel']
        symbol = channelSymbolMap[channel]
        
        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.vtSymbol = symbol
            tick.gatewayName = self.gatewayName
            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        rawData = data['data']
        tick.highPrice = float(rawData['high'])
        tick.lowPrice = float(rawData['low'])
        tick.lastPrice = float(rawData['last'])
        tick.volume = float(rawData['vol'])
        if 'timestamp' in rawData:
            tick.date, tick.time = generateDateTime(rawData['timestamp'])
        else:
            now = datetime.now()
            tick.time = now.strftime("%H:%M:%S.%f")
            tick.date = now.strftime('%Y%m%d')

        newtick = copy(tick)
        self.gateway.onTick(newtick)

    def onKLine(self, data):
        # print(data)
        """"""
        if 'data' not in data:
            return

        channel = data['channel']
        symbol = channelSymbolMap[channel]

        if symbol not in self.klineDict:
            bar = VtBarData()
            bar.symbol = symbol
            bar.vtSymbol = symbol
            bar.gatewayName = self.gatewayName
            self.klineDict[symbol] = bar
        else:
            bar = self.klineDict[symbol]

        rawData = data['data']
        # print(rawData)

        for kline in rawData:
            bar.datetime = datetime.fromtimestamp(float(kline[0])/1e3)
            bar.date, bar.time = generateDateTime(kline[0])
            bar.open = float(kline[1])
            bar.high = float(kline[2])
            bar.low = float(kline[3])
            bar.close = float(kline[4])
            bar.volume = float(kline[5])
            newBar = copy(bar)
            self.gateway.onKLine(newBar)


    
    def onDepth(self, data):
        """"""
        if 'data' not in data:
            return
        
        channel = data['channel']
        symbol = channelSymbolMap[channel]
        
        if symbol not in self.tickDict:
            tick = VtTickData()
            tick.symbol = symbol
            tick.vtSymbol = symbol
            tick.gatewayName = self.gatewayName
            self.tickDict[symbol] = tick
        else:
            tick = self.tickDict[symbol]
        
        if 'data' not in data:
            return
        rawData = data['data']
        # [Price, Amount(Contract), Amount(Coin), Cumulant(Coin), Cumulant(Contract)]
        # print(rawData)
        tick.bidPrice1, _, tick.bidVolume1, _, _ = rawData['bids'][0]
        tick.bidPrice2, _, tick.bidVolume2, _, _ = rawData['bids'][1]
        tick.bidPrice3, _, tick.bidVolume3, _, _ = rawData['bids'][2]
        tick.bidPrice4, _, tick.bidVolume4, _, _ = rawData['bids'][3]
        tick.bidPrice5, _, tick.bidVolume5, _, _ = rawData['bids'][4]

        tick.askPrice1, _, tick.askVolume1, _, _ = rawData['asks'][-1]
        tick.askPrice2, _, tick.askVolume2, _, _ = rawData['asks'][-2]
        tick.askPrice3, _, tick.askVolume3, _, _ = rawData['asks'][-3]
        tick.askPrice4, _, tick.askVolume4, _, _ = rawData['asks'][-4]
        tick.askPrice5, _, tick.askVolume5, _, _ = rawData['asks'][-5]
        
        tick.date, tick.time = generateDateTime(rawData['timestamp'])
        
        newtick = copy(tick)
        self.gateway.onTick(newtick)

    def on_future_user_info(self, data):
        """现货账户资金推送"""

        rawData = data['data']
        # print(rawData)
        info = rawData['info']
        # funds = rawData['info']['funds']

        # {u'ltc':
        #      {u'keep_deposit': 0.0, u'profit_unreal': 0.0, u'profit_real': 0.0, u'risk_rate': 10000.0,
        #       u'account_rights': 0.00086325},

        # 持仓信息
        # for symbol in ['btc', 'ltc', 'eth', self.currency]:
        account_rights = 0
        profit_unreal = 0
        profit_real = 0

        #
        # for symbol, symbol_data in info.items():
        #     account_rights += symbol_data['account_rights']
        #     profit_unreal += symbol_data['profit_unreal']
        #     profit_real += symbol_data['profit_real']

        account_rights = info['btc']['account_rights']
        profit_unreal = info['btc']['profit_unreal']
        profit_real = info['btc']['profit_real']

        # 账户资金
        account = VtAccountData()
        account.gatewayName = self.gatewayName
        account.accountID = self.gatewayName
        account.vtAccountID = account.accountID
        account.balance = account_rights
        account.positionProfit = profit_unreal
        account.closeProfit = profit_real
        account.info = info
        self.gateway.onAccount(account)

    def on_future_sub_user_info(self, data):
        # TODO 用户信息
        # print('TODO： ok_sub_futureusd_userinfo')
        pass

    def on_future_sub_postions(self, data):
        # pos = VtPositionData()
        pass

    # def on_future_sub_user_info(self, data):
    #     """现货账户资金推送"""
    #     if 'data' not in data:
    #         return
    #
    #     rawData = data['data']
    #     info = rawData['info']
    #
    #     # 持仓信息
    #     for symbol in ['btc', 'ltc', 'eth', self.currency]:
    #         if symbol in info['free']:
    #             pos = VtPositionData()
    #             pos.gatewayName = self.gatewayName
    #
    #             pos.symbol = symbol
    #             pos.vtSymbol = symbol
    #             pos.vtPositionName = symbol
    #             pos.direction = DIRECTION_NET
    #
    #             pos.frozen = float(info['freezed'][symbol])
    #             pos.position = pos.frozen + float(info['free'][symbol])
    #
    #             self.gateway.onPosition(pos)

    def on_future_sub_trades(self, data):
        """成交和委托推送"""
        if 'data' not in data:
            return
        rawData = data['data']

        # 本地和系统委托号
        orderId = str(rawData['orderid'])

        if orderId not in self.orderIdDict:
            ''' NOT TODO 
                如果下单后没有成交，策略重启后需要加载未完成订单，目前策略重启时要保证所有订单都完全成交，
                如果程序在此期间意外终止，需要手动保存仓位信息和策略执行的完成信息。不开发自己动加载单据功能的原因是
                重启过程也可能有订单状态的改变，信息无法同步。
            '''
            print('{0} is not in orderIdDict'.format(orderId))
            return
        self.writeLog('成交和委托推送 : %s' % rawData)
        localNo = self.orderIdDict[orderId]
        order = self.orderDict[localNo]
        order.status = statusMap[rawData['status']]
        # order.gatewayName = self.gatewayName
        # contract_name = rawData['contract_name'][:3].lower() + '_usd'
        # order.symbol = futureSymbolMap[contract_name]
        # order.vtSymbol = order.symbol
        # order.orderID = localNo
        # order.vtOrderID = '.'.join([self.gatewayName, order.orderID])
        # order.price = float(rawData['price'])
        # order.totalVolume = float(rawData['amount'])
        # order.direction, offset = futurePriceTypeMap[rawData['type']]

        self.writeLog('on trade: %s' % order)
        self.gateway.onOrder(copy(order))

        tradedVolume = order.tradedVolume  # 上一个订单回报的成交数据
        deal_amount = float(rawData['deal_amount'])  # 本次订单回报的成交数量

        # 成交信息
        if deal_amount > tradedVolume:
            volume = deal_amount - tradedVolume
            order.tradedVolume = deal_amount
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
            trade.order_price = float(rawData['price'])
            trade.order_amount = float(rawData['amount'])

            trade.symbol = order.symbol
            trade.vtSymbol = order.symbol
            trade.order_type = int(rawData['type'])
            trade.tradeID = str(rawData['orderid'])
            trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])

            trade.orderID = localNo
            trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])
            trade.fee = float(rawData['fee'])
            trade.price = float(rawData['price_avg'])
            trade.volume = volume
            trade.sum_volume = deal_amount
            trade.direction, trade.offset = futurePriceTypeMap[rawData['type']]
            trade.tradeTime = datetime.now().strftime('%H:%M:%S')

            self.gateway.onTrade(trade)

    def generateSpecificContract(self, contract, symbol):
        """生成合约"""
        new = copy(contract)
        new.symbol = symbol
        new.vtSymbol = symbol
        new.name = symbol
        return new

    def generateCnyContract(self):
        """生成CNY合约信息"""
        contractList = []

        contract = VtContractData()
        contract.exchange = EXCHANGE_OKCOIN
        contract.productClass = PRODUCT_SPOT
        contract.size = 1
        contract.priceTick = 0.01

        return contractList
    
    def generateUsdContract(self):
        """生成USD合约信息"""
        contractList = []
        
        # 现货
        contract = VtContractData()
        contract.exchange = EXCHANGE_OKCOIN
        contract.productClass = PRODUCT_SPOT
        contract.size = 1
        contract.priceTick = 0.01

        # 期货
        contract.productClass = PRODUCT_FUTURES
        
        # contractList.append(self.generateSpecificContract(contract, BTC_USD_THISWEEK))
        # contractList.append(self.generateSpecificContract(contract, BTC_USD_NEXTWEEK))
        contractList.append(self.generateSpecificContract(contract, BTC_USD_QUARTER))
        # contractList.append(self.generateSpecificContract(contract, LTC_USD_THISWEEK))
        # contractList.append(self.generateSpecificContract(contract, LTC_USD_NEXTWEEK))
        contractList.append(self.generateSpecificContract(contract, LTC_USD_QUARTER))
        # contractList.append(self.generateSpecificContract(contract, ETH_USD_THISWEEK))
        # contractList.append(self.generateSpecificContract(contract, ETH_USD_NEXTWEEK))
        contractList.append(self.generateSpecificContract(contract, ETH_USD_QUARTER))
        
        return contractList

    def on_future_trade(self, data):
        """委托回报"""
        self.writeLog('委托回报: %s' % data)

        rawData = data['data']
        if 'errorcode' in rawData:
            print('errorcode: {0}'.format(rawData['errorcode']))
        orderId = str(rawData['order_id'])

        # 尽管websocket接口的委托号返回是异步的，但经过测试是
        # 符合先发现回的规律，因此这里通过queue获取之前发送的
        # 本地委托号，并把它和推送的系统委托号进行映射
        localNo = self.localNoQueue.get_nowait()

        self.localNoDict[localNo] = orderId
        self.orderIdDict[orderId] = localNo

        order = self.orderDict[localNo]
        order.trade_order_id = orderId
        self.gateway.onOrder(copy(order))

        # 检查是否有系统委托号返回前就发出的撤单请求，若有则进行撤单操作
        if localNo in self.cancelDict:
            req = self.cancelDict[localNo]
            self.futureCancel(req)
            del self.cancelDict[localNo]

    def on_future_cancel_order(self, data):
        """撤单回报"""
        pass

    def futureSendOrder(self, req):
        """发单"""
        symbol = futureSymbolMapReverse[req.symbol][:4]  # 'btc_'
        type_ = futurepriceTypeMapReverse[(req.direction, req.offset)]
        self.futureTrade(symbol, type_, str(req.price), str(req.volume))

        # 本地委托号加1，并将对应字符串保存到队列中，返回基于本地委托号的vtOrderID
        self.localNo += 1
        self.localNoQueue.put(str(self.localNo))
        vtOrderID = '.'.join([self.gatewayName, str(self.localNo)])

        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.vtSymbol = req.symbol
        order.symbol = req.symbol
        order.orderID = str(self.localNo)
        order.vtOrderID = vtOrderID
        order.order_type = type_
        order.price = req.price
        order.totalVolume = req.volume
        order.direction, offset = req.direction, req.offset
        order.orderTime = datetime.now()  # datetime.fromtimestamp(float(rawData['create_date']) / 1000)
        self.orderDict[str(self.localNo)] = order
        self.gateway.onOrder(copy(order))

        return vtOrderID

    def futureCancel(self, req):
        """撤单"""
        symbol = futureSymbolMapReverse[req.symbol][:4]  # 'btc_'
        localNo = req.orderID
        # print('cancelAll 4 symbol: %s,localNo:%s, localNoDict: %s ' % (symbol, localNo, self.localNoDict))
        if localNo in self.localNoDict:
            orderID = self.localNoDict[localNo]
            self.futureCancelOrder(symbol, orderID)
        else:
            # 如果在系统委托号返回前客户就发送了撤单请求，则保存
            # 在cancelDict字典中，等待返回后执行撤单任务
            self.cancelDict[localNo] = req

    def onQryOrders(self, orders):
        orders['gateway_name'] = self.gatewayName
        self.gateway.onSyncOrders(orders)

def generateDateTime(s):
    """生成时间"""
    dt = datetime.fromtimestamp(float(s)/1e3)
    # datetime.fromtimestamp(int(s) / 1e3)
    time = dt.strftime("%H:%M:%S.%f")
    date = dt.strftime("%Y%m%d")
    return date, time