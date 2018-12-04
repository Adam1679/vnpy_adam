# encoding: UTF-8

'''
本文件中包含的是CTA模块的回测引擎，回测引擎的API和CTA引擎一致，
可以使用和实盘相同的代码进行回测。
'''
from __future__ import division
from __future__ import print_function

from datetime import datetime, timedelta
from collections import OrderedDict
from itertools import product
import multiprocessing
import pymongo

from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtObject import VtTickData, VtBarData
from vnpy.trader.vtConstant import *
from vnpy.trader.vtGateway import VtOrderData, VtTradeData

from vnpy.trader.app.ctaStrategy.ctaBase import *


########################################################################
class BacktestingEngine(object):
    """
    CTA回测引擎
    函数接口和策略引擎保持一样，
    从而实现同一套代码从回测到实盘。
    """
    
    TICK_MODE = 'tick'
    BAR_MODE = 'bar'

    def __init__(self):
        """Constructor"""

        
        # 引擎类型为回测
        self.engineType = ENGINETYPE_BACKTESTING
        
        # 回测相关
        self.strategy = None        # 回测策略
        self.mode = self.BAR_MODE   # 回测模式，默认为K线
        
        self.startDate = ''
        self.initDays = 0        
        self.endDate = ''

        self.slippage = 0           # 回测时假设的滑点
        self.rate = 0               # 回测时假设的佣金比例（适用于百分比佣金）
        self.size = 1               # 合约大小，默认为1    
        self.priceTick = 0          # 价格最小变动 

        self.dbName = ''            # 回测数据库名
        self.symbol = ''            # 回测集合名
        
        self.dataStartDate = None       # 回测数据开始日期，datetime对象
        self.dataEndDate = None         # 回测数据结束日期，datetime对象
        self.strategyStartDate = None   # 策略启动日期（即前面的数据用于初始化），datetime对象
        self.initData = []
        self.__init2__()

    def __init2__(self):

        self.initData = []  # 初始化用的数据


        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)

        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}  # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}  # 停止单撤销后会从本字典中删除

        self.limitOrderDict = OrderedDict()  # 限价单字典
        self.workingLimitOrderDict = OrderedDict()  # 活动限价单字典，用于进行撮合用
        self.limitOrderCount = 0  # 限价单编号

        self.tradeCount = 0  # 成交编号
        self.tradeDict = OrderedDict()  # 成交字典

        self.logList = []  # 日志记录

        # 当前最新数据，用于模拟成交用
        self.tick = None
        self.bar = None
        self.dt = None  # 最新的时间

        self.firstVolume = 0
        self.lastPrice = 0

        self.dbClient = None  # 数据库客户端
        self.dbCursor = None  # 数据库指针

    def initStrategy(self, strategyClass, setting=None):
        self.__init2__()
        """
        初始化策略
        setting是策略的参数设置，如果使用类中写好的默认设置则可以不传该参数
        """
        self.strategy = strategyClass(self, setting)
        self.strategy.name = self.strategy.className

    def setStartDate(self, startDate='20100416', initDays=10):
        """设置回测的启动日期"""
        self.startDate = startDate
        self.initDays = initDays
        
        self.dataStartDate = datetime.strptime(startDate, '%Y%m%d')
        
        initTimeDelta = timedelta(initDays)
        self.strategyStartDate = self.dataStartDate + initTimeDelta
        
    def setEndDate(self, endDate=''):
        """设置回测的结束日期"""
        self.endDate = endDate
        
        if endDate:
            self.dataEndDate = datetime.strptime(endDate, '%Y%m%d')
            
            # 若不修改时间则会导致不包含dataEndDate当天数据
            self.dataEndDate = self.dataEndDate.replace(hour=23, minute=59)    
        
    def setBacktestingMode(self, mode):
        """设置回测模式"""
        self.mode = mode
    
    def setDatabase(self, dbName, symbol):
        """设置历史数据所用的数据库"""
        self.dbName = dbName
        self.symbol = symbol
    
    def loadHistoryData(self):
        """载入历史数据"""
        self.dbClient = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
        collection = self.dbClient[self.dbName][self.symbol]          

        # self.output(u'开始载入数据')
      
        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
            func = self.newBar
        else:
            dataClass = VtTickData
            func = self.newTick

        # 载入初始化需要用的数据
        flt = {'datetime':{'$gte':self.dataStartDate,
                           '$lt':self.strategyStartDate}}        
        initCursor = collection.find(flt)
        
        # 将数据从查询指针中读取出，并生成列表
        self.initData = []              # 清空initData列表
        for d in initCursor:
            data = dataClass()
            data.__dict__ = d
            self.initData.append(data)

        # 载入回测数据
        if not self.dataEndDate:
            flt = {'datetime':{'$gte':self.strategyStartDate}}   # 数据过滤条件
        else:
            flt = {'datetime':{'$gte':self.strategyStartDate,
                               '$lte':self.dataEndDate}}
        self.dbCursor = collection.find(flt)
        self.dbCursor.batch_size(4*1024*1024)

    def runBacktesting(self, position=1, task_text='1/1'):
        # import pdb
        # pdb.set_trace()

        """运行回测"""
        # 载入历史数据
        self.loadHistoryData()

        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
            func = self.newBar
        else:
            dataClass = VtTickData
            func = self.newTick

        # self.output(u'开始回测')
        
        self.strategy.inited = True
        self.strategy.onInit()
        # self.output(u'策略初始化完成')
        
        self.strategy.trading = True
        self.strategy.onStart()
        # self.output(u'策略启动完成')
        
        # self.output(u'开始回放数据')



        # 进度条
        # from tqdm import tqdm
        # count = self.dbCursor.count()
        # total = count-1
        # text = "progresser #{}".format(task_text)
        # progress = tqdm(
        #     total=total,
        #     position=position,
        #     desc=text
        # )

        # 基准回撤代码
        # price_list = []
        # price_max = 0
        # dd_list = []


        for d in self.dbCursor:
            data = dataClass()
            data.__dict__ = d
            func(data)

            if self.firstVolume == 0:
                self.firstVolume = 10000.0/d['close']
            self.lastPrice = d['close']

            # progress.update()

            # 基准回撤代码
            # price_list.append(d['close'])
            # price_max = max(d['close'], price_max)
            # dd_list.append((d['close'] - price_max)/price_max)

        # progress.close()

        # print("dd_max:{0}".format(min(dd_list)))

        # 基准回撤代码


        # self.output(u'数据回放结束')


    def newBar(self, bar):
        """新的K线"""
        self.bar = bar
        self.dt = bar.datetime
        self.crossOrder()      # 撮合吃单
        # self.crossLimitOrder()      # 先撮合限价单
        # self.crossStopOrder()       # 再撮合停止单
        self.strategy.onBar(bar)    # 推送K线到策略中

    def newTick(self, tick):
        """新的Tick"""
        self.tick = tick
        self.dt = tick.datetime
        tick.askPrice1 = tick.lastPrice
        tick.bidPrice1 = tick.lastPrice
        tick.close = tick.lastPrice
        self.crossOrder()  # 撮合吃单
        # self.crossLimitOrder() # 先撮合限价单
        # self.crossStopOrder() # 再撮合停止单
        self.strategy.onTick(tick)

    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)
        
        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = self.roundToPriceTick(price)
        order.totalVolume = volume
        order.status = STATUS_NOTTRADED     # 刚提交尚未成交
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = str(self.dt)
        
        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE     
        
        # 保存到限价单字典中
        self.workingLimitOrderDict[orderID] = order
        self.limitOrderDict[orderID] = order
        
        return orderID
    
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        if vtOrderID in self.workingLimitOrderDict:
            order = self.workingLimitOrderDict[vtOrderID]
            order.status = STATUS_CANCELLED
            order.cancelTime = str(self.dt)
            del self.workingLimitOrderDict[vtOrderID]
        
    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.price = self.roundToPriceTick(price)
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        
        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE           
        
        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so
        
        return stopOrderID
    
    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]

    def cancelAll(self, name):
        """全部撤单"""
        # 撤销限价单
        for orderID in self.workingLimitOrderDict.keys():
            self.cancelOrder(orderID)

        # 撤销停止单
        for stopOrderID in self.workingStopOrderDict.keys():
            self.cancelStopOrder(stopOrderID)



    #----------------------------------------------------------------------
    def crossLimitOrder(self):
        """基于最新数据撮合限价单"""
        # 先确定会撮合成交的价格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low        # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = self.bar.high      # 若卖出方向限价单价格低于该价格，则会成交
            buyBestCrossPrice = self.bar.open   # 在当前时间点前发出的买入委托可能的最优成交价
            sellBestCrossPrice = self.bar.open  # 在当前时间点前发出的卖出委托可能的最优成交价
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1
        
        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict.items():


            # 判断是否会成交
            buyCross = (order.direction==DIRECTION_LONG and 
                        order.price>=buyCrossPrice and
                        buyCrossPrice > 0)      # 国内的tick行情在涨停时askPrice1为0，此时买无法成交
            
            sellCross = (order.direction==DIRECTION_SHORT and 
                         order.price<=sellCrossPrice and
                         sellCrossPrice > 0)    # 国内的tick行情在跌停时bidPrice1为0，此时卖无法成交
            
            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset
                # print(order.totalVolume)
                # 以买入为例：
                # 1. 假设当根K线的OHLC分别为：100, 125, 90, 110
                # 2. 假设在上一根K线结束(也是当前K线开始)的时刻，策略发出的委托为限价105
                # 3. 则在实际中的成交价会是100而不是105，因为委托发出时市场的最优价格是100
                if buyCross:
                    trade.price = min(order.price, buyBestCrossPrice)
                    # print("{0},{1}".format(order.price, buyBestCrossPrice))
                    if self.strategy.pos == 0:  # 做多

                        order.totalVolume = self.strategy.initCapital / trade.price
                        self.strategy.pos += self.strategy.initCapital / trade.price
                        self.strategy.initCapital = 0
                        # print(order.totalVolume)
                    else:  # 平空

                        result = TradingResult(self.strategy.last_entry_price, None,
                                               trade.price, None,
                                               -order.totalVolume, self.rate, 0.0, self.size)

                        self.strategy.pos += order.totalVolume
                        self.strategy.initCapital = order.totalVolume * self.strategy.last_entry_price + result.pnl
                        # print("{0},{1}".format(order.totalVolume, order.price))
                else:
                    trade.price = max(order.price, sellBestCrossPrice)
                    # print("{0},{1}".format(order.price, sellBestCrossPrice))
                    if self.strategy.pos == 0:  # 做空
                        order.totalVolume = self.strategy.initCapital / trade.price
                        self.strategy.pos -= self.strategy.initCapital / trade.price
                        self.strategy.initCapital = 0
                    else:  # 平多
                        result = TradingResult(self.strategy.last_entry_price, None,
                                               trade.price, None,
                                               +order.totalVolume, self.rate, 0.0, self.size)

                        self.strategy.pos -= order.totalVolume
                        self.strategy.initCapital = order.totalVolume * self.strategy.last_entry_price + result.pnl
                        # print("{0},{1}".format(order.totalVolume, order.price))
                # print(self.strategy.pos)
                self.strategy.last_entry_price = trade.price
                trade.volume = order.totalVolume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                self.strategy.onTrade(trade)
                
                self.tradeDict[tradeID] = trade

                # print(u'{0},{1},{2},{3},{4}'.format(order.orderTime ,order.price, order.totalVolume, order.offset, order.direction))

                # 推送委托数据
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
                self.strategy.onOrder(order)
                
                # 从字典中删除该限价单
                del self.workingLimitOrderDict[orderID]

                # 每个tick只成交一单，用于平仓后算保证金，下一周期再持仓
                # break
                
    #----------------------------------------------------------------------
    def crossStopOrder(self):
        """基于最新数据撮合停止单"""
        # 先确定会撮合成交的价格，这里和限价单规则相反
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.high    # 若买入方向停止单价格低于该价格，则会成交
            sellCrossPrice = self.bar.low    # 若卖出方向限价单价格高于该价格，则会成交
            bestCrossPrice = self.bar.open   # 最优成交价，买入停止单不能低于，卖出停止单不能高于
        else:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            bestCrossPrice = self.tick.lastPrice
        
        # 遍历停止单字典中的所有停止单
        for stopOrderID, so in self.workingStopOrderDict.items():
            # 判断是否会成交
            buyCross = so.direction==DIRECTION_LONG and so.price<=buyCrossPrice
            sellCross = so.direction==DIRECTION_SHORT and so.price>=sellCrossPrice
            
            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = so.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                
                if buyCross:
                    self.strategy.pos += so.volume
                    trade.price = max(bestCrossPrice, so.price)
                else:
                    self.strategy.pos -= so.volume
                    trade.price = min(bestCrossPrice, so.price)                
                
                self.limitOrderCount += 1
                orderID = str(self.limitOrderCount)
                trade.orderID = orderID
                trade.vtOrderID = orderID
                
                trade.direction = so.direction
                trade.offset = so.offset
                trade.volume = so.volume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                self.strategy.onTrade(trade)
                
                self.tradeDict[tradeID] = trade
                
                # 推送委托数据
                so.status = STOPORDER_TRIGGERED
                
                order = VtOrderData()
                order.vtSymbol = so.vtSymbol
                order.symbol = so.vtSymbol
                order.orderID = orderID
                order.vtOrderID = orderID
                order.direction = so.direction
                order.offset = so.offset
                order.price = so.price
                order.totalVolume = so.volume
                order.tradedVolume = so.volume
                order.status = STATUS_ALLTRADED
                order.orderTime = trade.tradeTime
                self.strategy.onOrder(order)
                
                self.limitOrderDict[orderID] = order
                
                # 从字典中删除该限价单
                if stopOrderID in self.workingStopOrderDict:
                    del self.workingStopOrderDict[stopOrderID]        

    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """考虑到回测中不允许向数据库插入数据，防止实盘交易中的一些代码出错"""
        pass
    
    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Bar"""
        return self.initData
    
    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Tick"""
        return self.initData
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录日志"""
        log = str(self.dt) + ' ' + content 
        self.logList.append(log)
        
    #----------------------------------------------------------------------
    def output(self, content):
        """输出内容"""
        print(str(datetime.now()) + "\t" + content)
    
    #----------------------------------------------------------------------
    def calculateBacktestingResult(self):
        """
        计算回测结果
        """
        # self.output(u'计算回测结果')
        
        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        resultList = []             # 交易结果列表
        
        longTrade = []              # 未平仓的多头交易
        shortTrade = []             # 未平仓的空头交易
        
        tradeTimeList = []          # 每笔成交时间戳
        posList = [0]               # 每笔成交后的持仓情况        

        for trade in self.tradeDict.values():

            # 多头交易
            if trade.direction == DIRECTION_LONG:
                # 如果尚无空头交易
                if not shortTrade:
                    longTrade.append(trade)
                # 当前多头交易为平空
                else:
                    while True:
                        entryTrade = shortTrade[0]
                        exitTrade = trade
                        
                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt, 
                                               exitTrade.price, exitTrade.dt,
                                               -closedVolume, self.rate, 0, self.size)
                        resultList.append(result)
                        
                        posList.extend([-1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])
                        
                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume
                        
                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            shortTrade.pop(0)
                        
                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break
                        
                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not shortTrade:
                                longTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass
                        
            # 空头交易        
            else:
                # 如果尚无多头交易
                if not longTrade:
                    shortTrade.append(trade)
                # 当前空头交易为平多
                else:                    
                    while True:
                        entryTrade = longTrade[0]
                        exitTrade = trade
                        
                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt, 
                                               exitTrade.price, exitTrade.dt,
                                               closedVolume, self.rate, 0, self.size)
                        resultList.append(result)
                        
                        posList.extend([1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume
                        


                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            longTrade.pop(0)
                        
                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break
                        
                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not longTrade:
                                shortTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass                    
                    
        # 检查是否有交易
        if not resultList:
            # self.output(u'无交易结果')
            return {}
        
        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等        
        capital = 0             # 资金
        maxCapital = 0          # 资金最高盈利,
        maxNetCapital = 0       # 资金最高净值,
        drawdown = 0            # 回撤
        
        totalResult = 0         # 总成交数量
        totalTurnover = 0       # 总成交金额（合约面值）
        totalCommission = 0     # 总手续费
        totalSlippage = 0       # 总滑点
        
        timeList = []           # 时间序列
        pnlList = []            # 每笔盈亏序列
        capitalList = []        # 盈亏汇总的时间序列
        drawdownList = []       # 回撤的时间序列
        drawdownRateList = []       # 回撤的时间序列
        netCapitalList = []     # 基准收益
        trade_detail = []

        winningResult = 0       # 盈利次数
        losingResult = 0        # 亏损次数		
        totalWinning = 0        # 总盈利金额		
        totalLosing = 0         # 总亏损金额      

        for result in resultList:
            capital += result.pnl
            maxCapital = max(capital, maxCapital)
            maxNetCapital = maxCapital + 10000.0
            drawdown = capital - maxCapital
            
            pnlList.append(result.pnl)
            timeList.append(result.exitDt)      # 交易的时间戳使用平仓时间
            capitalList.append(capital)
            drawdownList.append(drawdown)
            drawdownRateList.append(drawdown/maxNetCapital)
            netCapitalList.append(result.exitPrice*self.firstVolume - 10000)
            if result.volume > 0:
                txt = "平多仓,价格:{0}".format(result.exitPrice)
            else:
                txt = "平空仓,价格:{0}".format(result.exitPrice)

            trade_detail.append(txt)

            totalResult += 1
            totalTurnover += result.turnover
            totalCommission += result.commission
            totalSlippage += result.slippage
            
            if result.pnl >= 0:
                winningResult += 1
                totalWinning += result.pnl
            else:
                losingResult += 1
                totalLosing += result.pnl
                
        # 计算盈亏相关数据
        winningRate = winningResult/totalResult*100         # 胜率
        
        averageWinning = 0                                  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0
        
        if winningResult:
            averageWinning = totalWinning/winningResult     # 平均每笔盈利
        if losingResult:
            averageLosing = totalLosing/losingResult        # 平均每笔亏损
        if averageLosing:
            profitLossRatio = -averageWinning/averageLosing     # 盈亏比

        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['drawdownRateList'] = drawdownRateList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['posList'] = posList
        d['tradeTimeList'] = tradeTimeList
        d['netCapitalList'] = netCapitalList
        d['trade_detail'] = trade_detail
        d['baseRate'] = (self.lastPrice * self.firstVolume - 10000.0) / 10000.0 * 100.0

        return d

    @classmethod
    def show_result_array_header(cls):
        print(u'初始净值：\t%s' % formatNumber(10000.0))
        print('短线周期\t长线周期\t', end='')
        print("交易次数\t第一笔交易\t最后一笔交易\t期末净值\t基准收益\t回测收益\t最大回撤率\t胜率")

    def show_result_array(self, *args):
        d = self.calculateBacktestingResult()
        # print('\r', end='')
        if 'totalResult' not in d:
            return

        for param in args:
            print('%s\t\t' % param, end='')

        print("%s\t\t%s\t%s\t%s\t%.2f%%\t\t%.2f%%\t%.2f%%\t%s%%" %
                    (d['totalResult'],
                    d['timeList'][0].strftime("%Y-%m-%d"),
                    d['timeList'][-1].strftime("%Y-%m-%d"),
                    formatNumber(10000.0 + d['capital']),
                    (self.lastPrice * self.firstVolume - 10000.0) / 10000.0 * 100.0,
                    d['capital'] / 10000 * 100,
                    min(d['drawdownRateList']) * 100,
                    formatNumber(d['winningRate'])
                    ))


    def show_KLine(self, filename='test'):
        self.dbClient = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
        collection = self.dbClient[self.dbName][self.symbol]

        from datetime import datetime
        # 载入初始化需要用的数据
        start_date_str = '20160801'
        end_date_str = '20160909'
        start_date = datetime.strptime(start_date_str, '%Y%m%d')
        end_date = datetime.strptime(end_date_str, '%Y%m%d')
        filename = '{0}-{1}'.format(start_date_str,end_date_str)
        flt = {'datetime': {'$gt': start_date, '$lt': end_date}}
        initCursor = collection.find(flt)

        kurse_dates = []
        kurse_o = []
        kurse_h = []
        kurse_l = []
        kurse_c = []
        count = 0

        tmp_hour = -1
        tmp_datetime = -1
        tmp_open = -1
        tmp_high = -1
        tmp_low = -1
        tmp_close = -1
        for d in initCursor:
            if tmp_hour != d['datetime'].hour:
                if tmp_hour != -1:
                    kurse_dates.append(tmp_datetime)
                    kurse_o.append(tmp_open)
                    kurse_h.append(tmp_high)
                    kurse_l.append(tmp_low)
                    kurse_c.append(tmp_close)
                tmp_hour = d['datetime'].hour
                tmp_datetime = d['datetime'].replace(minute=0, second=0, microsecond=0)
                tmp_open = d['open']
                tmp_high = d['high']
                tmp_low = d['low']
                tmp_close = d['close']

            else:
                tmp_high = max(tmp_high, d['high'])
                tmp_low = min(tmp_low, d['low'])
                tmp_close = d['close']

        import numpy as np
        import talib
        ma_1 = talib.MA(np.array(kurse_c), 20)
        ma_2 = talib.MA(np.array(kurse_c), 26)

        import plotly.plotly as py
        import plotly.offline as of
        import plotly.graph_objs as go

        import pandas_datareader.data as web
        from datetime import datetime


        hour = go.Candlestick(x=kurse_dates,
                               open=kurse_o,
                               high=kurse_h,
                               low=kurse_l,
                               close=kurse_c, name='1 Hour')
        ma1 = go.Scatter(x=kurse_dates, y=ma_1, marker={'color': 'orange'}, name="MA 20")
        ma2 = go.Scatter(x=kurse_dates, y=ma_2, marker={'color': 'blue'}, name="MA 26")
        data = [hour, ma1, ma2]
        # py.iplot(data, filename=filename)
        of.offline.plot(data)

    def showBacktestingResult(self):
        """显示回测结果"""
        d = self.calculateBacktestingResult()

        # 输出
        self.output('-' * 30)
        self.output(u'第一笔交易：\t%s' % d['timeList'][0])
        self.output(u'最后一笔交易：\t%s' % d['timeList'][-1])

        self.output(u'初始净值：\t%s' % formatNumber(10000.0))
        self.output(u'期末净值：\t%s' %(formatNumber(10000.0 + d['capital'])))
        self.output(u'基准收益：\t%.2f%%' % (d['baseRate']))

        self.output(u'回测收益：\t%.2f%%' % (d['capital']/10000 * 100))

        self.output(u'总交易次数：\t%s' % formatNumber(d['totalResult']))
        self.output(u'总盈亏：\t%s' % (formatNumber(d['capital'])))
        self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))
        self.output(u'最大回撤率: \t%.2f%%' % (min(d['drawdownRateList'])*100))

        self.output(u'平均每笔盈利：\t%s' %formatNumber(d['capital']/d['totalResult']))
        self.output(u'平均每笔滑点：\t%s' %formatNumber(d['totalSlippage']/d['totalResult']))
        self.output(u'平均每笔佣金：\t%s' %formatNumber(d['totalCommission']/d['totalResult']))

        self.output(u'胜率\t\t%s%%' %formatNumber(d['winningRate']))
        self.output(u'盈利交易平均值\t%s' %formatNumber(d['averageWinning']))
        self.output(u'亏损交易平均值\t%s' %formatNumber(d['averageLosing']))
        self.output(u'盈亏比：\t%s' %formatNumber(d['profitLossRatio']))

        # 绘图
        # import matplotlib.pyplot as plt
        # import matplotlib.finance as mpf
        import numpy as np
        import plotly.plotly as py
        import plotly.offline as of
        import plotly.graph_objs as go

        # import pandas_datareader.data as web
        # from datetime import datetime

        if d['posList'][-1] == 0:
            del d['posList'][-1]
        tradeTimeIndex = [item.strftime("%Y%m%d %H:%M") for item in d['timeList']]
        # xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex)/10))
        xindex = np.arange(0, len(tradeTimeIndex), np.int(1))
        tradeTimeIndex = map(lambda i: tradeTimeIndex[i], xindex)

        trace0 = go.Scatter(x=d['timeList'], y=d['capitalList'], text=d['trade_detail'], marker={'color': 'red'}, name="策略收益")
        trace1 = go.Scatter(x=d['timeList'], y=d['netCapitalList'], marker={'color': 'blue'}, name="基准收益")
        data = [trace0,trace1]
        # py.iplot(data, filename='hour_ma20_26')
        of.offline.plot(data)

        # self.send_ding_msg(u'远程任务执行完毕')

        # pCapital = plt.subplot(2, 1, 1)
        # pCapital.set_ylabel("capital")
        # pCapital.plot(d['capitalList'], color='r', lw=0.8)
        # pCapital.plot(d['netCapitalList'], color='b', lw=0.8)
        #
        # pDD = plt.subplot(2, 1, 2)
        # pDD.set_ylabel("DD")
        # pDD.bar(range(len(d['drawdownRateList'])), d['drawdownRateList'], color='g')
        #
        # ax2 = pCapital.axes
        # ax2.scatter(d['drawdownRateList'], tradeTimeIndex)
        #
        # pCapital.get_shared_x_axes().join(pCapital, pDD)
        # plt.tight_layout()
        # plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15
        # plt.gcf().autofmt_xdate()
        # plt.show()




    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """发送策略更新事件，回测中忽略"""
        pass

    #----------------------------------------------------------------------
    def setSlippage(self, slippage):
        """设置滑点点数"""
        self.slippage = slippage

    #----------------------------------------------------------------------
    def setSize(self, size):
        """设置合约大小"""
        self.size = size

    #----------------------------------------------------------------------
    def setRate(self, rate):
        """设置佣金比例"""
        self.rate = rate

    #----------------------------------------------------------------------
    def setPriceTick(self, priceTick):
        """设置价格最小变动"""
        self.priceTick = priceTick

    #----------------------------------------------------------------------
    def runOptimization(self, strategyClass, optimizationSetting):
        """优化参数"""
        # 获取优化设置
        settingList = optimizationSetting.generateSetting()
        targetName = optimizationSetting.optimizeTarget

        # 检查参数设置问题
        if not settingList or not targetName:
            self.output(u'优化设置有问题，请检查')

        # 遍历优化
        resultList = []
        for setting in settingList:
            self.clearBacktestingResult()
            self.output('-' * 30)
            self.output('setting: %s' %str(setting))
            self.initStrategy(strategyClass, setting)
            self.runBacktesting()
            d = self.calculateBacktestingResult()
            try:
                targetValue = d[targetName]
            except KeyError:
                targetValue = 0
            resultList.append(([str(setting)], targetValue))

        # 显示结果
        resultList.sort(reverse=True, key=lambda result:result[1])
        self.output('-' * 30)
        self.output(u'优化结果：')
        for result in resultList:
            self.output(u'%s: %s' %(result[0], result[1], result[2]))
        return result

    #----------------------------------------------------------------------
    def clearBacktestingResult(self):
        """清空之前回测的结果"""
        # 清空限价单相关
        self.limitOrderCount = 0
        self.limitOrderDict.clear()
        self.workingLimitOrderDict.clear()

        # 清空停止单相关
        self.stopOrderCount = 0
        self.stopOrderDict.clear()
        self.workingStopOrderDict.clear()

        # 清空成交相关
        self.tradeCount = 0
        self.tradeDict.clear()

    #----------------------------------------------------------------------
    def runParallelOptimization(self, strategyClass, optimizationSetting):
        """并行优化参数"""
        # 获取优化设置
        settingList = optimizationSetting.generateSetting()
        targetName = optimizationSetting.optimizeTarget

        # 检查参数设置问题
        if not settingList or not targetName:
            self.output(u'优化设置有问题，请检查')

        # 多进程优化，启动一个对应CPU核心数量的进程池
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        cpu_count = multiprocessing.cpu_count()
        # pool = multiprocessing.Pool(1)
        l = []
        index = 0
        for setting in settingList:
            index += 1

            l.append(pool.apply_async(optimize, (strategyClass, setting,
                                                 targetName, self.mode,
                                                 self.startDate, self.initDays, self.endDate,
                                                 self.slippage, self.rate, self.size,
                                                 self.dbName, self.symbol, (index-1) % cpu_count +1, '{0}/{1}'.format(index, len(settingList)))))
        pool.close()
        pool.join()

        # 显示结果
        resultList = [res.get() for res in l]
        resultList.sort(reverse=True, key=lambda result:result[1])
        self.output('-' * 30)
        self.output(u'基准收益：%.2f%%' % resultList[0][4])
        self.output(u'优化值，策略收益，最大回撤率')
        for result in resultList:
            self.output(u'%s: %.2f, %.2f%%, %.2f%%' % (result[0], result[1], result[2], result[3]))

        self.send_ding_msg(u'远程任务执行完毕')

    #----------------------------------------------------------------------
    def roundToPriceTick(self, price):
        """取整价格到合约最小价格变动"""
        if not self.priceTick:
            return price

        newPrice = round(price/self.priceTick, 0) * self.priceTick
        return newPrice

    def send_ding_msg(self, msg):
        from restclient import GET, POST
        import json
        import urllib
        from urllib import quote
        from datetime import datetime

        content = {"content": msg+"\n" + datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        r = GET('https://oapi.dingtalk.com/gettoken?corpid=ding04bb33ecbbcad5f535c2f4657eb6378f&corpsecret=MorKrE3_R8owWfhF62_4dFW3SeV_wmclDAMRZ_lOt2PAZZcx35XF5uAluCL7NzqV')
        access_token = json.loads(r)['access_token']
        params = {'format': 'json', 'method': 'dingtalk.corp.message.corpconversation.asyncsend', 'v': '2.0',
                  'agent_id': '153447248', 'msgtype': 'text', 'to_all_user': 'false'}
        params['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        params['session'] = access_token
        params['userid_list'] = 'manager1879'
        params['msgcontent'] = json.dumps(content)
        POST("https://eco.taobao.com/router/rest", params=params,
                 headers={'Content-Type': 'application/x-www-form-urlencoded', 'charset': 'utf-8'})



########################################################################
class TradingResult(object):
    """每笔交易的结果"""

    #----------------------------------------------------------------------
    def __init__(self, entryPrice, entryDt, exitPrice,
                 exitDt, volume, rate, slippage, size):
        """Constructor"""
        self.entryPrice = entryPrice    # 开仓价格
        self.exitPrice = exitPrice      # 平仓价格

        self.entryDt = entryDt          # 开仓时间datetime
        self.exitDt = exitDt            # 平仓时间

        self.volume = volume    # 交易数量（+/-代表方向）+ 平多仓，- 平空仓
        self.turnover = (self.entryPrice+self.exitPrice)*size*abs(volume)   # 成交金额
        self.commission = self.turnover*rate                                # 手续费成本
        # self.slippage = slippage*2*size*abs(volume)                         # 滑点成本
        self.slippage = slippage * self.turnover
        self.pnl = ((self.exitPrice - self.entryPrice) * volume * size
                    - self.commission - self.slippage)                      # 净盈亏



########################################################################
class OptimizationSetting(object):
    """优化设置"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.paramDict = OrderedDict()

        self.optimizeTarget = ''        # 优化目标字段

    #----------------------------------------------------------------------
    def addParameter(self, name, start, end=None, step=None):
        """增加优化参数"""
        if end is None and step is None:
            self.paramDict[name] = [start]
            return

        if end < start:
            print(u'参数起始点必须不大于终止点')
            return

        if step <= 0:
            print(u'参数布进必须大于0')
            return

        l = []
        param = start

        while param <= end:
            l.append(param)
            param += step

        self.paramDict[name] = l

    #----------------------------------------------------------------------
    def generateSetting(self):
        """生成优化参数组合"""
        # 参数名的列表
        nameList = self.paramDict.keys()
        paramList = self.paramDict.values()

        # 使用迭代工具生产参数对组合
        productList = list(product(*paramList))

        # 把参数对组合打包到一个个字典组成的列表中
        settingList = []
        for p in productList:
            d = dict(zip(nameList, p))

            # if d['fastMaLength'] >= d['slowMaLength']:
            #     continue

            settingList.append(d)

        return settingList

    #----------------------------------------------------------------------
    def setOptimizeTarget(self, target):
        """设置优化目标字段"""
        self.optimizeTarget = target


#----------------------------------------------------------------------
def formatNumber(n):
    """格式化数字到字符串"""
    rn = round(n, 2)        # 保留两位小数
    return format(rn, ',')  # 加上千分符


#----------------------------------------------------------------------
def optimize(strategyClass, setting, targetName,
             mode, startDate, initDays, endDate,
             slippage, rate, size,
             dbName, symbol, index, task_text):
    """多进程优化时跑在每个进程中运行的函数"""
    engine = BacktestingEngine()
    engine.setBacktestingMode(mode)
    engine.setStartDate(startDate, initDays)
    engine.setEndDate(endDate)
    engine.setSlippage(slippage)
    engine.setRate(rate)
    engine.setSize(size)
    engine.setDatabase(dbName, symbol)

    engine.initStrategy(strategyClass, setting)
    engine.runBacktesting(index, task_text)
    d = engine.calculateBacktestingResult()
    targetValue2 = 0
    targetValue3 = 0
    targetValue4 = 0

    try:
        targetValue = d[targetName]
        targetValue2 = d['capital']/10000 * 100  # 回测收益
        targetValue3 = min(d['drawdownRateList'])*100  # 最大回撤率
        targetValue4 = d['baseRate']
    except KeyError:
        targetValue = 0            
    return (str(setting), targetValue, targetValue2, targetValue3, targetValue4)
    