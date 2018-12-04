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


from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)
import time


########################################################################
class tick_strategy_cn(CtaTemplate):
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
    buyOrderIDList = []                 # 委托买入开仓的委托号
    shortOrderIDList = []               # 委托卖出开仓的委托号
    orderList = []                      # 保存委托代码的列表

    def __init__(self, ctaEngine, setting):
        fileName = 'param.json'
        try:
            f = file(fileName)
        except IOError:
            print('读取param参数配置出错，请检查')
        # 解析json文件-----------------------------------------------------
        mysetting = json.load(f)
        redisHost = str(mysetting['redisHost'])  #
        redisPort = str(mysetting['redisPort'])
        self.r = redis.Redis(host=redisHost, port=int(redisPort), db=8)
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
        self.bm = BarManager(self.onBar, 1)  # 创建K线合成器对象
        """Constructor"""
        super(tick_strategy_cn, self).__init__(ctaEngine, setting)

        # 策略变量
        self.bar = None  # K线对象
        self.bm = BarManager(self.onBar, 1)  # 创建K线合成器对象
        self.barMinute = EMPTY_STRING  # K线当前的分钟

        self.bufferSize = 100  # 需要缓存的数据的大小
        self.bufferCount = 0  # 目前已经缓存了的数据的计数
        self.highArray = np.zeros(self.bufferSize)  # K线最高价的数组
        self.lowArray = np.zeros(self.bufferSize)  # K线最低价的数组
        self.closeArray = np.zeros(self.bufferSize)  # K线收盘价的数组
        self.getPos()
        # self.longYd = 0 # 这四个是昨仓今仓
        # self.longTd = 0
        # self.shortYd = 0
        # self.shortTd = 0
        # self.r.set('sc_wtiusPos', 0)    # 初始化仓位
        # self.r.set('brent_scusPos', 0)

    def onInit(self):
        """初始化策略（必须由用户继承实现）"""

        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # position = self.ctaEngine.query_position()
        # print('qry postion: {0}'.format(position))

        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.init_data_loaded = True
        self.putEvent()

    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        # self.ctaEngine.test()
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    def getPos(self):
        """获取cn仓位"""
        cnPosObj = self.banzhuan_query_position()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 过滤异常值
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bm.updateTick(tick)
        dt = tick.datetime
        set_data = self.r.get('set_data')
        if set_data == 'True':
            us_close = float(self.r.get('us_close')) # TODO: US_CLOSE 没有初始化
            self.r.set('set_data', 'False')
        else:
            pass
        ex_rate = self.usdcnhRate() # 获取汇率
        spread = tick.lastPrice - ex_rate * us_close # 计算新的价差
        preSpread = self.spread # 保存过去的价差
        self.spread = spread  # 更近价差

        price = tick.lastPrice
        if self.long_enter:  # 判断信号
            if self.LongSignalSpread + self.MaxTolerate > spread:
                self.buyOrderIDList.append(self.buy(price, 1))  # 开多
                self.count = 0
                self.maxdt = dt + datetime.timedelta(minutes=self.maxHold)  # 只持仓到那个时间点
                self.minExitdt = dt + datetime.timedelta(minutes=0.5)  # TODO:半分钟，or不要？
            else:
                if self.count == self.Ticks:
                    self.qidan(price, dt, spread, direction='long') # TODO: 经过几个tick后还未达到想要的价格，就弃单
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
                self.buyOrderIDList.append(self.cover_today(price, 1))  # 平今空
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
                self.shortOrderIDList.append(self.sell_today(price, 1))  # 平今多
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
                        if ((spread - preSpread) > self.minEnterPrice) or (spread - preSpread) > + self.mutiple * std:
                            self.short_enter = True
                            self.ShortSignalSpread = spread

                        elif ((preSpread - spread) > self.minEnterPrice) or (preSpread - spread) > self.mutiple * std:
                            self.long_enter = True
                            self.LongSignalSpread = spread
                        else:
                            pass

            if self.pos == -1:
                if dt > self.minExitdt:  # 如果满足最小进场时间
                    if dt >= self.maxdt:  # 如果超过最大持仓时间
                        self.short_exit = True
                        self.ShortSignalSpread = spread

                    else:
                        if (self.short_enter_price - spread) > self.maxWin:  # 止盈
                            self.short_exit = True
                            self.stopwinning = True
                            self.ShortSignalSpread = spread

                        elif (spread - self.short_enter_price) > self.minLose:  # 止损
                            self.short_exit = True
                            self.stopLosing = True
                            self.ShortSignalSpread = spread
                        else:
                            pass

            if self.pos == 1:  # 若有仓位
                if dt > self.minExitdt:  # 若符合最小进场时间
                    if dt >= self.maxdt:  # 若超过最大持仓周期
                        self.long_exit = True
                        self.LongSignalSpread = spread

                    else:
                        if (spread - self.long_enter_price) > self.maxWin:  # 止盈
                            self.long_exit = True
                            self.stopwinning = True
                            self.LongSignalSpread = spread

                        elif (self.long_enter_price - spread) > self.minLose:  # 止损
                            self.long_exit = True
                            self.stopLosing = True
                            self.LongSignalSpread = spread

                        else:
                            pass
        else:
            if dt >= self.stoppingdt:
                self.stopping = False
                self.stoppingdt = None

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onXminBar(self, bar):

        """交易后的账户余额或保证金"""
        pass

    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # print(order)
        # self.writeCtaLog(u'委托变化推送: %s' % order)
        pass

    def onTrade(self, trade):
        # print('%s %s, price:%s, volume:%.4f, capital:%.2f' %(trade.dt,trade.direction, trade.price, trade.volume,trade.price * trade.volume))

        # self.writeCtaLog(u'成交信息推送: %s' % trade)
        # 发出状态更新事件
        self.putEvent()

    def usdcnhRate(self):
        url = 'http://webforex.hermes.hexun.com/forex/quotelist?code=FOREXUSDCNH&column=Code,Price'
        r = GET(url)
        data = json.loads(r[1:-2])
        rate = float(data['Data'][0][0][1]) / 10000.0
        # print '------------------rate---------------\n',rate
        self.r.set('usdcnhRate', rate)

    def ResetSignal(self):
        self.long_enter = False
        self.long_exit = False
        self.short_enter = False
        self.short_exit = False
        self.stopwinning = False
        self.stopLosing = False
