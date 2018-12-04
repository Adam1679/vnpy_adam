# encoding: UTF-8

"""
一个ATR-RSI指标结合的交易策略，适合用在股指的1分钟和5分钟线上。

注意事项：
1. 作者不对交易盈利做任何保证，策略代码仅供参考
2. 本策略需要用到talib，没有安装的用户请先参考www.vnpy.org上的教程安装
3. 将IF0000_1min.csv用ctaHistoryData.py导入MongoDB后，直接运行本文件即可回测策略

"""

import talib
import numpy as np


from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate



########################################################################
class AtrRsiStrategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'AtrRsiStrategy'
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

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(AtrRsiStrategy, self).__init__(ctaEngine, setting)
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

        self.last_entry_price = 0
        self.pos = 0

        # 策略参数
        # self.atrLength = 22  # 计算ATR指标的窗口数
        # self.fastMaLength = 15  # 计算ATR均线的窗口数
        # self.slowMaLength = 30
        # self.rsiLength = 5  # 计算RSI的窗口数
        # self.rsiEntry = 16  # RSI的开仓信号
        # self.trailingPercent = 0.8  # 百分比移动止损
        # self.initDays = 2  # 初始化数据所用的天数

        # self.fixedSize = 1  # 每次交易的数量

        # 策略变量
        self.bar = None  # K线对象
        self.barMinute = EMPTY_STRING  # K线当前的分钟

        self.bufferSize = 30  # 需要缓存的数据的大小
        self.bufferCount = 0  # 目前已经缓存了的数据的计数
        self.highArray = np.zeros(self.bufferSize)  # K线最高价的数组
        self.lowArray = np.zeros(self.bufferSize)  # K线最低价的数组
        self.closeArray = np.zeros(self.bufferSize)  # K线收盘价的数组

        self.atrCount = 0  # 目前已经缓存了的ATR的计数
        self.atrArray = np.zeros(self.bufferSize)  # ATR指标的数组
        self.atrValue = 0  # 最新的ATR指标数值
        self.atrMa = 0  # ATR移动平均的数值

        self.rsiValue = 0  # RSI指标的数值
        self.rsiBuy = 0  # RSI买开阈值
        self.rsiSell = 0  # RSI卖开阈值
        self.intraTradeHigh = 0  # 移动止损用的持仓期内最高价
        self.intraTradeLow = 0  # 移动止损用的持仓期内最低价
        self.orderList = []  # 保存委托代码的列表

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        
        self.writeCtaLog(u'%s策略初始化' %self.name)


        # 初始化RSI入场阈值
        # self.rsiBuy = 50 + self.rsiEntry
        # self.rsiSell = 50 - self.rsiEntry
        self.initCapital = 10000.0
        self.initDays = 1
        self.barHour = -1
        self.no_data = 0
        # 载入历史数据，并采用回放计算的方式初始化策略数值

        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)




        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""

        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:    
            if self.bar:
                self.onBar(self.bar)

            bar = VtBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间

            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):

        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        slippage = 0.0

        # if self.barHour != int(bar.datetime.isocalendar()[1]):
        #     self.barHour = int(bar.datetime.isocalendar()[1])
        if self.barHour != int(bar.datetime.day):
            self.barHour = int(bar.datetime.day)
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
        self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize-1] = self.closeArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close

        self.bufferCount += 1

        if self.bufferCount < self.slowMaLength:
            return

        slow_arr = talib.MA(self.closeArray, self.slowMaLength)
        # fast_arr = talib.MA(self.closeArray, self.fastMaLength)

        delay_day = self.fastMaLength

        slow_1 = slow_arr[-2 - delay_day]
        slow_2 = slow_arr[-3 - delay_day]
        slow_3 = slow_arr[-4 - delay_day]

        # fast_1 = fast_arr[-2]
        # fast_2 = fast_arr[-3]
        # fast_3 = fast_arr[-4]

        # 判断买卖
        # crossOver = fast_1 > slow_1 and fast_2 < slow_2  # 上穿
        # crossBelow = fast_1 < slow_1 and fast_2 > slow_2   # 下穿

        slow_up = slow_1 > slow_2 and slow_2 < slow_3  # 慢线上升
        slow_down = slow_1 < slow_2 and slow_2 > slow_3  # 慢线下降


        if self.pos == 0:

            # print 'date:%s,volume:%s' %(bar.datetime, self.initCapital)
            volume = round(self.initCapital / bar.close, 4)
            if slow_up:
                self.cancelAll()
                self.buy(bar.close * (1 + slippage), volume)

            elif slow_down:
                self.cancelAll()
                self.sell(bar.close * (1 - slippage), volume)

        # 持有多头仓位
        elif self.pos > 0:

            if slow_down:
                self.cancelAll()
                volume = round(self.initCapital / bar.close, 4)
                orderID = self.sell(bar.close * (1 - slippage), abs(self.pos))
                # self.initCapital = self.trade_result(bar)

                volume = round(self.initCapital / bar.close, 4)
                orderID = self.short(bar.close * (1 - slippage), volume)
                # self.initCapital = self.trade_result(bar)

        # 持有空头仓位
        elif self.pos < 0:

            if slow_up:
                self.cancelAll()
                volume = round(self.initCapital / bar.close, 4)
                orderID = self.cover(bar.close * (1 + slippage), abs(self.pos))
                # self.initCapital = self.trade_result(bar)

                volume = round(self.initCapital / bar.close, 4)
                orderID = self.buy(bar.close * (1 + slippage), volume)
                # self.initCapital = self.trade_result(bar)


        # 发出状态更新事件
        self.putEvent()

    '''交易后的账户余额或保证金'''
    def trade_result(self, bar):
        from ctaBacktesting import TradingResult
        result = TradingResult(self.last_entry_price, None,
                               bar.close, None,
                               self.pos, self.ctaEngine.rate,
                               self.ctaEngine.slippage, self.ctaEngine.size)
        #  # print('{0},{1},{2}'.format(self.initCapital, result.pnl, self.initCapital + result.pnl))
        return self.initCapital + result.pnl



    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # print('%s %s, price:%s, volume:%.4f, capital:%.2f' %(trade.dt,trade.direction, trade.price, trade.volume,trade.price * trade.volume))

        # 发出状态更新事件
        self.putEvent()

