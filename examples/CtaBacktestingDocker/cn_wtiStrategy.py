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
import pandas as pd
from retry import retry
from vnpy.trader.app.ctaStrategy.ctaBase import ENGINETYPE_TRADING

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate



########################################################################
class cn_wtiStrategy(CtaTemplate):
    """结合ATR和RSI指标的一个分钟线交易策略"""
    className = 'cn_wtiStrategy'
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
        self.contract_size = 0
        self.slowMaLength = 0
        self.fastMaLength = 0
        self.margin_percent = 0
        self.stop_profit = 0
        """Constructor"""
        super(cn_wtiStrategy, self).__init__(ctaEngine, setting)

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
        self.closeList = []

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

    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:
            if self.bar:
                self.onBar(self.bar)

            bar = VtBarData()
            bar.vtSymbol = 'cn_wti.cnus'
            bar.symbol = 'cn_wti'
            bar.exchange = 'cnus'
            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    def onBar(self, bar):
        # print '--------------bar.datetime-----------------', bar.datetime
        # if self.barHour != int(bar.datetime.day):
        #     self.barHour = int(bar.datetime.day)
        #     self.bar = VtBarData()
        #     self.bar.open = bar.open
        #     self.bar.high = bar.high
        #     self.bar.low = bar.low
        #     self.bar.close = bar.close
        #     self.bar.datetime = bar.datetime
        #     k_line_new = True
        # else:
        #     self.bar.high = max(bar.high, self.bar.high)
        #     self.bar.low = min(bar.low, self.bar.low)
        #     self.bar.close = bar.close
        #     k_line_new = False
        #     # return
        #
        # # 保存K线数据
        # if k_line_new:
        #     if bar.close == self.closeArray[-1]:
        #         self.no_data += 1
        #     else:
        #         self.no_data = 0
        #
        #     if self.no_data > 10:  # 无数的周期过多时进行过滤
        #         return
        #     self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]
        #     self.bufferCount += 1
        #
        # self.closeArray[-1] = bar.close

        # if not self.init_data_loaded or self.bufferCount < self.slowMaLength:
        #     return

        # slow_arr = talib.MA(self.closeArray, self.slowMaLength)
        self.closeList.append(bar.close)
        # print(self.closeArray)

        if self.bufferCount < 120:
            self.bufferCount += 1
            return

        if len(self.closeList) > self.fastMaLength:
            self.closeList = self.closeList[-120:]
        df = pd.Series(self.closeList)
        trend = pd.Series.ewm(df, span=self.fastMaLength).mean()
        std = pd.Series.ewm(df, span=self.fastMaLength).std()
        high = trend + 1.8 * std
        low = trend - 1.8 * std

        ema120_1 = trend.iloc[-1]
        ema120_2 = trend.iloc[-2]

        price_1 = self.closeList[-1]
        price_2 = self.closeList[-2]

        high_1 = high.iloc[-1]
        high_2 = high.iloc[-2]
        low_1 = low.iloc[-1]
        low_2 = low.iloc[-2]

        # 判断买卖
        crossOver = price_2 <= high_2 and price_1 > high_1  # 向上突破
        crossBelow = price_2 >= low_2 and price_1 < low_1  # 向下突破
        decreaseback = price_2 >= ema120_2 and price_1 < ema120_1  # 从上回到中线
        increaseback = price_2 <= ema120_2 and price_1 > ema120_1  # 从下回到中线
        increasing = price_1 > high_1  # 价格线在上
        decreasing = price_1 < low_1  # 价格线在下

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
            account_right = self.ctaEngine.query_account().info[self.vtSymbol[:3].lower()]['account_rights']
            strategy_margin = self.margin_percent * account_right * bar.close  # 用些策略的金额
        else:
            strategy_margin = self.initCapital

        self.cancelAll()
        if self.pos == 0:
            volume = strategy_margin / self.contract_size
            if crossOver: # 向上突破
                # if self.stop == 0:

                    self.short(bar.close, int(volume))  # short 卖开
                # else:
                #     self.stop -= 1
            elif crossBelow:    # 向下突破
                # if self.stop == 0:
                    self.buy(bar.close, int(volume))    # buy 买开

                # else:
                #     self.stop -= 1

        # 持有多头仓位
        elif self.pos > 0:
            sell_order = False
            # if self.last_entry_price > 0 and (
            # bar.close - self.last_entry_price) / self.last_entry_price > self.stop_profit:
            # self.stop = 4
            # sell_order = True
            # print("*"*20)
            if increaseback:    # 从下回到中线
                # sell_order = True   # sell 卖平
                self.sell(bar.close, abs(self.pos))
                if self.ctaEngine.engineType != ENGINETYPE_TRADING:
                    self.initCapital = self.trade_result(bar)
                    strategy_margin = self.initCapital

            # if sell_order:
            #     self.sell(bar.close, abs(self.pos))
            #     if self.ctaEngine.engineType != ENGINETYPE_TRADING:
            #         self.initCapital = self.trade_result(bar)
            #         strategy_margin = self.initCapital



        # 持有空头仓位
        elif self.pos < 0:
            cover_order = False # cover 买平
            # if self.last_entry_price > 0 and (
            # self.last_entry_price - bar.close) / self.last_entry_price > self.stop_profit:
            # self.stop = 4
            # cover_order = True
            # print("*" * 20)
            if decreaseback:
                # cover_order = True
                self.cover(bar.close, abs(self.pos))
                if self.ctaEngine.engineType != ENGINETYPE_TRADING:
                    self.initCapital = self.trade_result(bar)
                    strategy_margin = self.initCapital

            # if cover_order:
            #     self.cover(bar.close, abs(self.pos))
            #     if self.ctaEngine.engineType != ENGINETYPE_TRADING:
            #         self.initCapital = self.trade_result(bar)
            #         strategy_margin = self.initCapital

        # 发出状态更新事件
        self.putEvent()

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
        pass

    def onTrade(self, trade):
        # print('%s %s, price:%s, volume:%.4f, capital:%.2f' %(trade.dt,trade.direction, trade.price, trade.volume,trade.price * trade.volume))

        # self.writeCtaLog(u'成交信息推送: %s' % trade)
        # 发出状态更新事件
        self.putEvent()

