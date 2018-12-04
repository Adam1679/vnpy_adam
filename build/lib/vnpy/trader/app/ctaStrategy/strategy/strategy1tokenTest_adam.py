# encoding: UTF-8

"""
一个ATR-RSI指标结合的交易策略，适合用在股指的1分钟和5分钟线上。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
3. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略
"""
import datetime
import tushare as ts
import redis
import json
import talib
import numpy as np
from retry import retry
from vnpy.trader.app.ctaStrategy.ctaBase import ENGINETYPE_TRADING
from restclient import GET
import os
import time
from vnpy.trader.gateway import onetokenGateway
from vnpy.trader.vtConstant import (EMPTY_STRING, EMPTY_UNICODE,
                                    EMPTY_FLOAT, EMPTY_INT)

from vnpy.trader.vtObject import *
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate


########################################################################
class onetokenGatewayTestStrategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'CN'
    author = u'用Python的交易员'

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'atrLength',
                 'fastMaLength',
                 'slowMaLength',
                 'rsiLength',
                 'rsiEntry',
                 'trailingPercent']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'atrValue',
               'atrMa',
               'rsiValue',
               'rsiBuy',
               'rsiSell']

    def __init__(self, ctaEngine, setting):
        # fileName = 'param.json'
        # try:
        #     f = file(fileName)
        # except IOError:
        #     print('读取param参数配置出错，请检查')
        # # 解析json文件-----------------------------------------------------
        # mysetting = json.load(f)
        # redisHost = str(mysetting['redisHost'])  #
        # self.r = redis.Redis(host=redisHost, port=6379, db=8)
        self.a = 0
        self.contract_size = 0
        self.slowMaLength = 0
        self.fastMaLength = 0
        self.margin_percent = 0
        self.stop_profit = 0

        """Constructor"""
        super(onetokenGatewayTestStrategy, self).__init__(ctaEngine, setting)
        self.flag = -1

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

        self.last_entry_price = 0
        self.pos = 0
        self.inited = False
        self.trading = False
        self.init_data_loaded = False

        # 策略变量
        self.bar = None  # K线对象
        self.barMinute = EMPTY_STRING  # K线当前的分钟

        self.bufferSize = 100  # 需要缓存的数据的大小
        self.bufferCount = 0  # 目前已经缓存了的数据的计数
        self.highArray = np.zeros(self.bufferSize)  # K线最高价的数组
        self.lowArray = np.zeros(self.bufferSize)  # K线最低价的数组
        self.closeArray = np.zeros(self.bufferSize)  # K线收盘价的数组

        self.atrCount = 0  # 目前已经缓存了的ATR的计数
        self.atrArray = np.zeros(self.bufferSize)  # ATR指标的数组
        self.atrValue = 0  # 最新的ATR指标数值
        self.atrMa = 0  # ATR移动平均的数值
        self.no_data = 0
        self.rsiValue = 0  # RSI指标的数值
        self.rsiBuy = 0  # RSI买开阈值
        self.rsiSell = 0  # RSI卖开阈值
        self.intraTradeHigh = 0  # 移动止损用的持仓期内最高价
        self.intraTradeLow = 0  # 移动止损用的持仓期内最低价
        # self.orderList = []  # 保存委托代码的列表
        self.initCapital = 10000.0
        self.initDays = 2
        self.barHour = -1
        self.stop = 0  # 用于判断上一个交易是否是止盈操作
        self.posType = 0    # 应该持仓的方式。1 2 3
        self.longYd = 0 # 这四个是昨仓今仓
        self.longTd = 0
        self.shortYd = 0
        self.shortTd = 0
        self.symbol = 'USD.CNH'
        self.exchange = "IDEALPRO"
        self.currency = ''
        self.productClass = "外汇"

        self.atrLength = 0
        self.rsiLength = 0
        self.rsiEntry = 0
        self.trailingPercent = 0
        # # 订阅合约 zls添加ib使用
        req = VtSubscribeReq()
        self.symbol = 'btc.usdt'
        self.exchange = "huobip"
        self.currency = ''
        self.productClass = "CASH"
        req.symbol = self.symbol
        req.exchange = self.exchange
        req.currency = self.currency
        req.productClass = self.productClass
        # time.sleep(5)
        ct = VtContractData()
        ct.gatewayName = "ONETOKEN"
        ct.symbol = 'huobip/btc.usdt'
        ct.exchange = 'huobip'
        ct.vtSymbol = 'huobip/btc.usdt'
        self.ctaEngine.mainEngine.dataEngine.contractDict['huobip/btc.usdt'] = ct
        self.ctaEngine.mainEngine.dataEngine.saveContracts()
        ctaEngine.subscribe(req, 'ONETOKEN')


    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        # 初始化RSI入场阈值
        # self.rsiBuy = 50 + self.rsiEntry
        # self.rsiSell = 50 - self.rsiEntry
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # position = self.ctaEngine.query_position()
        # print('qry postion: {0}'.format(position))

        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        #     self.onBar(bar)
        #
        # self.init_data_loaded = True
        # self.putEvent()


    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        # self.ctaEngine.test()
        self.writeCtaLog(u'%s策略启动' % self.name)
        # self.writeCtaLog(u'----------strategyIBTest.py line 167----------')
        self.putEvent()


    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    def choose_pair(self, setting):
        """选择交易对，sc_wti brent_sc"""
        if not setting['name'].find == -1:
            split_list = setting['name'].split('_')
            pair = split_list[0]+'_'+split_list[1]
            return pair
        else:
            print('-----------choose_pair()出错----------')
            return

    def getPos(self):
        """获取cn和us的仓位,us的仓位在vnoanda.py里面实现"""

        # 0:空仓，1：做多，-1：做空
        fileName = 'CTA_setting.json'
        try:
            f = file(fileName)
        except IOError:
            print('读取param参数配置出错，请检查')
        # 解析json文件-----------------------------------------------------
        mysetting = json.load(f)
        # if self.pair == 'sc_wti':
        #     cnvtSymbol = str(mysetting[0]['vtSymbol'])
        #     usvtSymbol = str(mysetting[1]['vtSymbol']).split('.')[0]
        # elif self.pair == 'brent_sc':
        #     cnvtSymbol = str(mysetting[3]['vtSymbol'])
        #     usvtSymbol = str(mysetting[2]['vtSymbol']).split('.')[0]
        reqID = self.api.getTrades({'instrument': usvtSymbol})
        cnPosObj = self.banzhuan_query_position(cnvtSymbol)
        # print '-------------------------昨仓今仓-------------------------\nlongYd:', cnPosObj.longYd, '\nlongTd:', cnPosObj.longTd, '\nshortYd:', cnPosObj.shortYd, '\nshortTd:', cnPosObj.shortTd
        self.longYd = cnPosObj.longYd   # vtEngine.py 633行。昨仓今仓分别获取。
        self.longTd = cnPosObj.longTd
        self.shortYd = cnPosObj.shortYd
        self.shortTd = cnPosObj.shortTd
        # print '--------------longPos,shortPos--------------:',cnPosObj.longPos,cnPosObj.shortPos

        # self.r.set(self.pair+'cnPos', cnPosObj.longPos-cnPosObj.shortPos) #cn仓位

        # print cnPosObj.vtSymbol, cnPosObj.long_position, cnPosObj.short_position, '<--------------------搬砖cn仓位查询'

        return usvtSymbol

    # def usdcnh_units(self, units):
    #     usdcnh = float(self.r.get('usdcnyRate')) # 获取usdcnh价格，这个价格五分钟更新一次
    #     # cnprice = float(self.r.get(self.pair+'cnlastPrice'))    # 获取美油价格
    #     whunits = int(cnprice/usdcnh*units)
    #     return whunits

    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        print '-'*30, 'strategy_onTick', '-'*30, tick.lastPrice
        if self.a == 0:
            self.buy(tick.lastPrice, 1)
            print '-'*30, 'strategy_onTick', '-'*30, tick.lastPrice, "买入"
            self.a = 1

    def updateTick(self, event):
        print '-' * 30, 'strategy_updateTick', '-' * 30

    def onBar(self, bar):
        # postion = self.ctaEngine.query_position(self)
        # print(postion.long_position)
        pass
        '''
        print '-'*20,'onBar777','-'*20


        if self.barHour != int(bar.datetime.hour):
            self.barHour = int(bar.datetime.hour)
            self.bar = VtBarData()
            self.bar.open = bar.open
            self.bar.high = bar.high
            self.bar.low = bar.low
            self.bar.close = bar.close
            self.bar.datetime = bar.datetime

        else:

            self.bar.high = max(bar.high, self.bar.high)
            self.bar.low = min(bar.low, self.bar.low)
            self.bar.close = bar.close
            return

        if bar.close == self.closeArray[-1]:
            self.no_data += 1
        else:
            self.no_data = 0

        if self.no_data > 10:  # 无数的周期过多时进行过滤
            return

        # print("initCapital {0}".format(self.initCapital))
        # for orderID in self.orderList:
        #     self.cancelOrder(orderID)
        # self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close

        self.bufferCount += 1

        if not self.init_data_loaded or self.bufferCount < self.slowMaLength:
            return
        slow_arr = talib.MA(self.closeArray, self.slowMaLength)
        fast_arr = talib.MA(self.closeArray, self.fastMaLength)
        # slow_arr = talib.WMA(self.closeArray, self.slowMaLength)
        # fast_arr = talib.WMA(self.closeArray, self.fastMaLength)

        slow_1 = slow_arr[-1]
        slow_2 = slow_arr[-2]
        # slow_3 = slow_arr[-4]

        fast_1 = fast_arr[-1]
        fast_2 = fast_arr[-2]
        # fast_3 = fast_arr[-5]

        # 判断买卖
        crossOver = fast_1 > slow_1 and fast_2 <= slow_2  # 上穿
        crossBelow = fast_1 < slow_1 and fast_2 >= slow_2  # 下穿
        increasing = fast_1 > slow_1  # 快线在上
        decreasing = fast_1 < slow_1  # 快线在下

        if self.ctaEngine.engineType == ENGINETYPE_TRADING:
            # 加载没有完成成交的订单
            incomplete_orders = self.ctaEngine.load_incomplete_orders(self)
            for order in incomplete_orders:
                incomplete_amount = order['order_amount'] - order['deal_amount']
                if increasing and order['order_type'] == 1:  # 开多
                    self.buy(bar.close, incomplete_amount)
                elif decreasing and order['order_type'] == 2:  # 开空
                    self.short(bar.close, incomplete_amount)
                elif decreasing and order['order_type'] == 3:  # 平多
                    self.sell(bar.close, incomplete_amount)
                elif increasing and order['order_type'] == 4:  # 平空
                    self.cover(bar.close, incomplete_amount)
            # account_right = self.ctaEngine.query_account().balance  # btc 账户权益
            account_right = self.ctaEngine.query_account(self).info[self.vtSymbol[:3].lower()]['account_rights']
            strategy_margin = self.margin_percent * account_right * bar.close  # 用些策略的金额

            postion = self.ctaEngine.query_position(self)[self.vtSymbol]
            if postion.long_position == 0 and postion.short_position == 0:
                self.pos = 0
            elif postion.short_position > 0:
                self.pos = - postion.short_position
            elif postion.long_position > 0:
                self.pos = postion.long_position


        else:
            strategy_margin = self.initCapital

        self.cancelAll()
        if self.pos == 0:
            volume = strategy_margin / self.contract_size
            if crossOver:
                if self.stop == 0:
                    self.buy(bar.close, int(volume * 0.5))
                else:
                    self.stop -= 1
            elif crossBelow:
                if self.stop == 0:
                    self.short(bar.close, int(volume * 2))
                else:
                    self.stop -= 1

        # 持有多头仓位
        elif self.pos > 0:
            sell_order = short_order = False
            if self.last_entry_price > 0 and (
                bar.close - self.last_entry_price) / self.last_entry_price > self.stop_profit:
                self.stop = 4
                sell_order = True
                # print("*"*20)
            elif crossBelow:
                sell_order = short_order = True

            if sell_order:
                self.sell(bar.close, abs(self.pos))
                if self.ctaEngine.engineType != ENGINETYPE_TRADING:
                    self.initCapital = self.trade_result(bar)
                    strategy_margin = self.initCapital

            if short_order:
                volume = strategy_margin / self.contract_size
                self.short(bar.close, int(volume * 2))

        # 持有空头仓位
        elif self.pos < 0:
            cover_order = long_order = False
            if self.last_entry_price > 0 and (
                self.last_entry_price - bar.close) / self.last_entry_price > self.stop_profit:
                self.stop = 4
                cover_order = True
                # print("*" * 20)
            elif crossOver:
                cover_order = long_order = True

            if cover_order:
                self.cover(bar.close, abs(self.pos))
                if self.ctaEngine.engineType != ENGINETYPE_TRADING:
                    self.initCapital = self.trade_result(bar)
                    strategy_margin = self.initCapital

            if long_order:
                volume = strategy_margin / self.contract_size
                self.buy(bar.close, int(volume * 0.5))

        # 发出状态更新事件
        self.putEvent()
        '''


    '''交易后的账户余额或保证金'''

    def trade_result(self, bar):
        from ctaBacktestingDollar import TradingResult
        result = TradingResult(self.last_entry_price, None,
                               bar.close, None,
                               self.pos, self.ctaEngine.rate,
                               self.ctaEngine.slippage, self.contract_size)
        # print('{0},{1},{2}'.format(self.initCapital, result.pnl, self.initCapital + result.pnl))
        return (self.initCapital / self.last_entry_price + result.pnl) * bar.close

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # print(order)
        # self.writeCtaLog(u'委托变化推送: %s' % order)
        # pass

    def onTrade(self, trade):
        # print('%s %s, price:%s, volume:%.4f, capital:%.2f' %(trade.dt,trade.direction, trade.price, trade.volume,trade.price * trade.volume))

        # self.writeCtaLog(u'成交信息推送: %s' % trade)
        # 发出状态更新事件
        self.putEvent()


class VtSubscribeReq(object):
    """订阅行情时传入的对象类"""

    def __init__(self):
        """Constructor"""
        self.symbol = EMPTY_STRING  # 代码
        self.exchange = EMPTY_STRING  # 交易所

        # 以下为IB相关
        self.productClass = EMPTY_UNICODE  # 合约类型
        self.currency = EMPTY_STRING  # 合约货币
        self.expiry = EMPTY_STRING  # 到期日
        self.strikePrice = EMPTY_FLOAT  # 行权价
        self.optionType = EMPTY_UNICODE  # 期权类型
