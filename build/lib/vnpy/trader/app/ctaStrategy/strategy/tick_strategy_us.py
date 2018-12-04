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
import os
import time


from vnpy.trader.vtObject import *
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)
import time


########################################################################
class tick_strategy_cn(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'CN'
    author = u'Adam Zhang'

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
        # 策略参数
        self.bm = BarManager(self.onBar, 1)  # 创建K线合成器对象
        """Constructor"""
        super(tick_strategy_cn, self).__init__(ctaEngine, setting)

        # 策略变量
        self.bm = BarManager(self.onBar, 1)  # 创建K线合成器对象

        # 订阅合约 zls添加IB使用
        req = VtSubscribeReq()
        self.symbol = 'USD.CNH'
        self.exchange = "IDEALPRO"
        # self.currency = ''
        self.productClass = "CASH"
        req.symbol = self.symbol
        req.exchange = self.exchange
        req.currency = self.currency
        req.productClass = self.productClass
        # time.sleep(5)
        ctaEngine.subscribe(req, 'IB')


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

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.r.set('close', str(bar.close))
        self.r.set('set_data', 'True')


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

