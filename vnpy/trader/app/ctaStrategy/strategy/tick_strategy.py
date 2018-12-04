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
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)


########################################################################
class tick_strategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'CN'
    author = u'张安翔'
    buyOrderIDList = []                 # 委托买入开仓的委托号
    shortOrderIDList = []               # 委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'maxHold',
                 'maxWin',
                 'minLose',
                 'mutiple',
                 'volume',
                 'init_asset',
                 'minEnterPrice',
                 'MaxTolerate']

    # 变量列表，保存了变量的名称
    varList = ['LongSignalSpread',
               'ShortSignalSpread',
               'pos',
               'atrValue',
               'atrMa',
               'rsiValue',
               'rsiBuy',
               'rsiSell']

    def __init__(self, ctaEngine, setting):

        # 策略参数
        self.contract_size = 100
        self.MaxTolerate = 0
        self.maxHold = 0
        self.Ticks = 4 #追单数量
        self.stopping = False
        self.stoppingdt = None # 止损后最小开仓时间
        self.stoppPeriods = 15  # 止损后15分钟不能开仓
        self.ShortSignalSpread = None
        self.LongSignalSpread = None
        self.short_enter_price = None
        self.short_exit_price = None
        self.long_enter_price = None
        self.long_exit_price = None
        self.maxHold = 0
        self.maxWin = 0
        self.minLose = 0
        self.mutiple = 0
        self.minEnterPrice = 0
        self.volume = 0
        self.init_asset = 0

        """Constructor"""
        super(tick_strategy, self).__init__(ctaEngine, setting)

        # 策略变量
        self.bm = BarManager(self.onBar, 1)     # 创建K线合成器对象
        self.am = ArrayManager()

        # # time.sleep(5)
        # ct = VtContractData()
        # ct.gatewayName = "ONETOKEN"
        # ct.symbol = 'huobip/btc.usdt'
        # ct.exchange = 'huobip'
        # ct.vtSymbol = 'huobip/btc.usdt'
        # self.ctaEngine.mainEngine.dataEngine.contractDict['huobip/btc.usdt'] = ct
        # self.ctaEngine.mainEngine.dataEngine.saveContracts()
        # ctaEngine.subscribe(req, 'ONETOKEN')


    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值

        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        #     self.onBar(bar)

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bm.updateTick(tick)
        dt = tick.datetime
        # TODO: 计算spread
        preSpread = self.spread
        self.spread = new_spread # 更近spread
        spread = self.spread

        price = tick.lastPrice
        if self.long_enter:  # 判断信号
            if self.LongSignalSpread + self.MaxTolerate > spread:
                self.buyOrderIDList.append(self.buy(price, 1))  # 开多
                self.count = 0
                self.maxdt = dt + datetime.timedelta(minutes=self.maxHold)  # 只持仓到那个时间点
                self.minExitdt = dt + datetime.timedelta(minutes=0.5)  # TODO:半分钟，or不要？
            else:
                if self.count == self.Ticks:
                    self.qidan(price, dt, spread, direction='long')
                    self.count = 0

                else:
                    self.count += 1

        elif self.short_enter:
            if self.ShortSignalSpread - self.MaxTolerate < spread:
                self.shortOrderIDList.append(self.short(price, 1))  # 卖空
                self.count = 0
                self.maxdt = dt + datetime.timedelta(minutes=self.maxHold)
                self.minExitdt = dt + datetime.timedelta(minutes=0.5)  # TODO

            else:  # 经过几个tick后还未达到想要的价格，就弃单
                if self.count == self.Ticks:
                    self.qidan(price, dt, spread, direction='short')
                    self.count = 0

                else:
                    self.count += 1

        elif self.short_exit:
            if self.count == self.Ticks:
                self.buyOrderIDList.append(self.cover(price, 1)) # 平空
                self.count = 0
                if self.stopwinning or self.stopLosing:
                    self.stopping = True
                    self.stoppingdt = dt + datetime.timedelta(minutes=self.stoppPeriods)
                    self.maxdt = None
                    self.minExitdt = None

                else:
                    self.maxdt = None
                    self.minExitdt = None
                    self.minEnterdt = dt + datetime.timedelta(minutes=0.5)

            else:
                self.count += 1

        elif self.long_exit:
            if self.count == self.Ticks:
                self.shortOrderIDList.append(self.sell(price, 1)) # 平多
                self.count = 0
                if self.stopwinning or self.stopLosing:
                    self.stopping = True
                    self.stoppingdt = dt + datetime.timedelta(minutes=self.stoppPeriods)
                    self.maxdt = None
                    self.minExitdt = None

                else:
                    self.maxdt = None
                    self.minExitdt = None
                    self.minEnterdt = dt + datetime.timedelta(minutes=0.5)
            else:
                self.count += 1


        self.ResetSignal()
        dtAbove = datetime.datetime.combine(dt.date(), datetime.time(dt.hour, dt.minute))
        try:
            # TODO: 需要计算Std，std是一小时1min_bar的收盘价的std
            std = self.cal_std()
        except:
            std = np.nan

        # 开空仓信号
        if not self.stopping:
            if self.pos == 0:
                if dt > self.minEnterdt:  # 如果满足最小进场时间
                    if preSpread:
                        if ((spread - preSpread) > self.minEnterPrice) or (spread-preSpread) >  + self.mutiple * std:
                            self.short_enter = True
                            self.ShortSignalSpread = spread

                        elif ((preSpread - spread) > self.minEnterPrice) or (preSpread - spread) > self.mutiple * std:
                            self.long_enter = True
                            self.LongSignalSpread = spread
                        else:
                            pass

            if self.pos == -1:
                if dt > self.minExitdt: # 如果满足最小进场时间
                    if dt >= self.maxdt: # 如果超过最大持仓时间
                        self.short_exit = True
                        self.ShortSignalSpread = spread

                    else:
                        if (self.short_enter_price - spread) > self.maxWin: # 止盈
                            self.short_exit = True
                            self.stopwinning = True
                            self.ShortSignalSpread = spread

                        elif (spread - self.short_enter_price) > self.minLose: # 止损
                            self.short_exit = True
                            self.stopLosing = True
                            self.ShortSignalSpread = spread
                        else:
                            pass

            if self.pos == 1: # 若有仓位
                if dt > self.minExitdt: # 若符合最小进场时间
                    if dt >= self.maxdt: # 若超过最大持仓周期
                        self.long_exit = True
                        self.LongSignalSpread = spread

                    else:
                        if (spread - self.long_enter_price) > self.maxWin: # 止盈
                            self.long_exit = True
                            self.stopwinning = True
                            self.LongSignalSpread = spread

                        elif (self.long_enter_price - spread) > self.minLose: # 止损
                            self.long_exit = True
                            self.stopLosing = True
                            self.LongSignalSpread = spread

                        else:
                            pass
        else:
            if dt >= self.stoppingdt:
                self.stopping = False
                self.stoppingdt = None


    def updateTick(self, event):
        print('-' * 30, 'strategy_updateTick', '-' * 30)

    def onBar(self, bar):
        self.bm.updateBar(bar)

    '''交易后的账户余额或保证金'''


    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # print(order)
        # self.writeCtaLog(u'委托变化推送: %s' % order)
        # pass

    def onTrade(self, trade):
        if self.pos != 0:
            # 多头开仓成交后，撤消空头委托
            if self.pos > 0:
                for shortOrderID in self.shortOrderIDList:
                    self.cancelOrder(shortOrderID)
            # 反之同样
            elif self.pos < 0:
                for buyOrderID in self.buyOrderIDList:
                    self.cancelOrder(buyOrderID)

            # 移除委托号
            for orderID in (self.buyOrderIDList + self.shortOrderIDList):
                if orderID in self.orderList:
                    self.orderList.remove(orderID)

        # 发出状态更新事件
        self.putEvent()


    def ResetSignal(self):
        self.long_enter = False
        self.long_exit = False
        self.short_enter = False
        self.short_exit = False
        self.stopwinning = False
        self.stopLosing = False

    def cal_std(self):
        pass

    def getPos(self):
        """获取cn仓位"""
        # 0:空仓，1：做多，-1：做空 老版本的，已废除
        # fileName = 'CTA_setting.json'
        # try:
        #     f = file(fileName)
        # except IOError:
        #     print('读取param参数配置出错，请检查')
        # # 解析json文件-----------------------------------------------------
        # mysetting = json.load(f)
        # if self.pair == 'sc_wti':
        #     cnvtSymbol = str(mysetting[0]['vtSymbol'])
        #     usvtSymbol = str(mysetting[1]['vtSymbol']).split('.')[0]
        # elif self.pair == 'brent_sc':
        #     cnvtSymbol = str(mysetting[3]['vtSymbol'])
        #     usvtSymbol = str(mysetting[2]['vtSymbol']).split('.')[0]
        # reqID = self.api.getTrades({'instrument': usvtSymbol})
        # cnPosObj = self.banzhuan_query_position(cnvtSymbol)
        cnPosObj = self.banzhuan_query_position()  # 已改为不传参数，待测试是否有效
        # print '-------------------------昨仓今仓-------------------------\nlongYd:', cnPosObj.longYd, '\nlongTd:', cnPosObj.longTd, '\nshortYd:', cnPosObj.shortYd, '\nshortTd:', cnPosObj.shortTd
        # self.longYd = cnPosObj.longYd   # vtEngine.py 633行。昨仓今仓分别获取。
        # self.longTd = cnPosObj.longTd
        # self.shortYd = cnPosObj.shortYd
        # self.shortTd = cnPosObj.shortTd
        self.r.set('cnpositionlongYd', cnPosObj.longYd)
        self.r.set('cnpositionlongTd', cnPosObj.longTd)
        self.r.set('cnpositionshortYd', cnPosObj.shortYd)
        self.r.set('cnpositionshortTd', cnPosObj.shortTd)

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
