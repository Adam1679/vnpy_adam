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
class cnBanZhuanStrategyDR(CtaTemplate):
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
        self.contract_size = 0
        self.slowMaLength = 0
        self.fastMaLength = 0
        self.margin_percent = 0
        self.stop_profit = 0

        """Constructor"""
        super(cnBanZhuanStrategyDR, self).__init__(ctaEngine, setting)
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

        self.getPos()

        self.upperLimit = None
        self.lowerLimit = None
        # self.longYd = 0 # 这四个是昨仓今仓
        # self.longTd = 0
        # self.shortYd = 0
        # self.shortTd = 0
        # self.r.set('sc_wtiusPos', 0)    # 初始化仓位
        # self.r.set('brent_scusPos', 0)



    def onInit(self):
        """初始化策略（必须由用户继承实现）"""

        self.writeCtaLog(u'%s策略初始化' % self.name)

        # 初始化RSI入场阈值
        # self.rsiBuy = 50 + self.rsiEntry
        # self.rsiSell = 50 - self.rsiEntry

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
        self.r.set('cnpositionlongYd', cnPosObj.longYd)
        self.r.set('cnpositionlongTd', cnPosObj.longTd)
        self.r.set('cnpositionshortYd', cnPosObj.shortYd)
        self.r.set('cnpositionshortTd', cnPosObj.shortTd)



    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 过滤异常值
        pass

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

