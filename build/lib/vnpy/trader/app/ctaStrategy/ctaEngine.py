# encoding: UTF-8

'''
本文件中实现了CTA策略引擎，针对CTA类型的策略，抽象简化了部分底层接口的功能。

关于平今和平昨规则：
1. 普通的平仓OFFSET_CLOSET等于平昨OFFSET_CLOSEYESTERDAY
2. 只有上期所的品种需要考虑平今和平昨的区别
3. 当上期所的期货有今仓时，调用Sell和Cover会使用OFFSET_CLOSETODAY，否则
   会使用OFFSET_CLOSE
4. 以上设计意味着如果Sell和Cover的数量超过今日持仓量时，会导致出错（即用户
   希望通过一个指令同时平今和平昨）
5. 采用以上设计的原因是考虑到vn.trader的用户主要是对TB、MC和金字塔类的平台
   感到功能不足的用户（即希望更高频的交易），交易策略不应该出现4中所述的情况
6. 对于想要实现4中所述情况的用户，需要实现一个策略信号引擎和交易委托引擎分开
   的定制化统结构（没错，得自己写）
'''

from __future__ import division

import json
import os
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta

from vnpy.event import Event
from vnpy.trader.vtEvent import *
from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtTickData, VtBarData
from vnpy.trader.vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData
from vnpy.trader.vtFunction import todayDate, getJsonPath
from .WeixinMessage import WeixinMessage

from .ctaBase import *
from .strategy import STRATEGY_CLASS
import sys
reload(sys)  # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入
sys.setdefaultencoding('utf-8')




########################################################################
class CtaEngine(object):
    """CTA策略引擎"""
    settingFileName = 'CTA_setting.json'
    settingfilePath = getJsonPath(settingFileName, __file__)
    
    STATUS_FINISHED = set([STATUS_REJECTED, STATUS_CANCELLED, STATUS_ALLTRADED])

    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()
        
        # 保存策略实例的字典
        # key为策略名称，value为策略实例，注意策略名称不允许重复
        self.strategyDict = {}
        
        # 保存vtSymbol和策略实例映射的字典（用于推送tick数据）
        # 由于可能多个strategy交易同一个vtSymbol，因此key为vtSymbol
        # value为包含所有相关strategy对象的list
        self.tickStrategyDict = {}
        
        # 保存vtOrderID和strategy对象映射的字典（用于推送order和trade数据）
        # key为vtOrderID，value为strategy对象
        self.orderStrategyDict = {}     
        
        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)
        
        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}      # 停止单撤销后会从本字典中删除
        
        # 保存策略名称和委托号列表的字典
        # key为name，value为保存orderID（限价+本地停止）的集合
        self.strategyOrderDict = {}
        
        # 成交号集合，用来过滤已经收到过的成交推送
        self.tradeSet = set()
        
        # 引擎类型为实盘
        self.engineType = ENGINETYPE_TRADING
        
        # 注册日式事件类型
        self.mainEngine.registerLogEvent(EVENT_CTA_LOG)
        
        # 注册事件监听
        self.registerEvent()

        # 微信消息接收人
        # self.user_list = ['aaron']
        self.user_list = []

 
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        contract = self.mainEngine.getContract(vtSymbol)
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange

        # print req.exchange,'<---------------------------------'
        req.vtSymbol = contract.vtSymbol
        req.price = self.roundToPriceTick(contract.priceTick, price)
        req.volume = volume
        
        req.productClass = strategy.productClass
        req.currency = strategy.currency        
        
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = PRICETYPE_LIMITPRICE
        # req.priceType = PRICETYPE_MARKETPRICE     # 需要增加一个市价单的方法。或者看懂停止单
        msg_str = ''

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_OPEN
            msg_str = '做多'

        elif orderType == CTAORDER_SELL:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_CLOSE
            msg_str = '平昨多'

        elif orderType == CTAORDER_SELL_TODAY:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_CLOSETODAY
            msg_str = '平今多'
                
        elif orderType == CTAORDER_SHORT:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_OPEN
            msg_str = '做空'
            
        elif orderType == CTAORDER_COVER:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_CLOSE
            msg_str = '平昨空'

        elif orderType == CTAORDER_COVER_TODAY:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_CLOSETODAY
            msg_str = '平今空'

        # 委托转换
        reqList = self.mainEngine.convertOrderReq(req)
        vtOrderIDList = []
        if not reqList:
            return vtOrderIDList
        for convertedReq in reqList:
            vtOrderID = self.mainEngine.sendOrder(convertedReq, contract.gatewayName)    # 发单
            self.orderStrategyDict[vtOrderID] = strategy                                 # 保存vtOrderID和策略的映射关系
            self.strategyOrderDict[strategy.name].add(vtOrderID)                         # 添加到策略委托号集合中
            vtOrderIDList.append(vtOrderID)
        self.writeCtaLog(u'策略%s发送委托，%s，%s，%s@%s'
                         %(strategy.name, vtSymbol, msg_str, volume, price))

        # self.send_ding_msg(u'策略%s发送委托，%s，%s，%s@%s'
        #                  %(strategy.name, vtSymbol, msg_str, volume, price))

        # if contract.gatewayName == 'OKEX':
        #     account_right = self.query_account().info[vtSymbol[:3].lower()]['account_rights']
            # balance = round(account_right * price, 2)
            # weixin = WeixinMessage()
            # result = weixin.send(contract.gatewayName, strategy.name, vtSymbol,
            #                  '%s%s张$%s，账户权益%s≈$%s，%s' %
            #                  (msg_str, volume, price, account_right,
            #                   balance, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            #                  self.user_list)
        # self.writeCtaLog('weixin.send: %s' % result)
        # else:
        #     account_right = self.query_account().info[vtSymbol[:3].lower()]['account_rights']

        return vtOrderIDList

    # zls增加，发单市价单
    def sendMarketOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        contract = self.mainEngine.getContract(vtSymbol)
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange

        # print req.exchange,'<---------------------------------'
        req.vtSymbol = contract.vtSymbol
        req.price = self.roundToPriceTick(contract.priceTick, price)
        req.volume = volume

        req.productClass = strategy.productClass
        req.currency = strategy.currency

        # 设计为CTA引擎发出的委托只允许使用限价单
        # req.priceType = PRICETYPE_LIMITPRICE
        req.priceType = PRICETYPE_MARKETPRICE     # 需要增加一个市价单的方法。或者看懂停止单
        msg_str = ''

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_OPEN
            msg_str = '做多'

        elif orderType == CTAORDER_SELL:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_CLOSE
            msg_str = '平昨多'

        elif orderType == CTAORDER_SELL_TODAY:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_CLOSETODAY
            msg_str = '平今多'

        elif orderType == CTAORDER_SHORT:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_OPEN
            msg_str = '做空'

        elif orderType == CTAORDER_COVER:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_CLOSE
            msg_str = '平昨空'

        elif orderType == CTAORDER_COVER_TODAY:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_CLOSETODAY
            msg_str = '平今空'

        # 委托转换
        reqList = self.mainEngine.convertOrderReq(req)
        vtOrderIDList = []
        if not reqList:
            return vtOrderIDList
        for convertedReq in reqList:
            vtOrderID = self.mainEngine.sendOrder(convertedReq, contract.gatewayName)  # 发单
            self.orderStrategyDict[vtOrderID] = strategy  # 保存vtOrderID和策略的映射关系
            self.strategyOrderDict[strategy.name].add(vtOrderID)  # 添加到策略委托号集合中
            vtOrderIDList.append(vtOrderID)
        self.writeCtaLog(u'策略%s发送委托，%s，%s，%s@%s'
                         % (strategy.name, vtSymbol, msg_str, volume, price))

        # self.send_ding_msg(u'策略%s发送委托，%s，%s，%s@%s'
        #                  %(strategy.name, vtSymbol, msg_str, volume, price))

        # if contract.gatewayName == 'OKEX':
        #     account_right = self.query_account().info[vtSymbol[:3].lower()]['account_rights']
        # balance = round(account_right * price, 2)
        # weixin = WeixinMessage()
        # result = weixin.send(contract.gatewayName, strategy.name, vtSymbol,
        #                  '%s%s张$%s，账户权益%s≈$%s，%s' %
        #                  (msg_str, volume, price, account_right,
        #                   balance, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        #                  self.user_list)
        # self.writeCtaLog('weixin.send: %s' % result)
        # else:
        #     account_right = self.query_account().info[vtSymbol[:3].lower()]['account_rights']

        return vtOrderIDList

    def query_position_failed_msg(self, strategy):
        vtSymbol = strategy.vtSymbol
        contract = self.mainEngine.getContract(vtSymbol)
        print contract.gatewayName, strategy.name, vtSymbol, '仓位获取失败', self.user_list
        # weixin = WeixinMessage()
        # weixin.send(contract.gatewayName, strategy.name, vtSymbol, '仓位获取失败', self.user_list)



    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 查询报单对象
        order = self.mainEngine.getOrder(vtOrderID)
        # self.writeCtaLog('cancelAll 2 %s' % order)
        # 如果查询成功
        if order:
            # 检查是否报单还有效，只有有效时才发出撤单指令
            orderFinished = (order.status==STATUS_ALLTRADED or order.status==STATUS_CANCELLED)
            if not orderFinished:
                req = VtCancelOrderReq()
                req.symbol = order.symbol
                req.exchange = order.exchange
                req.frontID = order.frontID
                req.sessionID = order.sessionID
                req.orderID = order.orderID
                self.mainEngine.cancelOrder(req, order.gatewayName)    

    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.orderType = orderType
        so.price = price
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
        
        # 保存stopOrderID到策略委托号集合中
        self.strategyOrderDict[strategy.name].add(stopOrderID)
        
        # 推送停止单状态
        strategy.onStopOrder(so)
        
        return [stopOrderID]
    
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            strategy = so.strategy
            
            # 更改停止单状态为已撤销
            so.status = STOPORDER_CANCELLED
            
            # 从活动停止单字典中移除
            del self.workingStopOrderDict[stopOrderID]
            
            # 从策略委托号集合中移除
            s = self.strategyOrderDict[strategy.name]
            if stopOrderID in s:
                s.remove(stopOrderID)
            
            # 通知策略
            strategy.onStopOrder(so)

    def processStopOrder(self, tick):
        """收到行情后处理本地停止单（检查是否要立即发出）"""
        vtSymbol = tick.vtSymbol
        
        # 首先检查是否有策略交易该合约
        if vtSymbol in self.tickStrategyDict:
            # 遍历等待中的停止单，检查是否会被触发
            for so in self.workingStopOrderDict.values():
                if so.vtSymbol == vtSymbol:
                    longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice>=so.price        # 多头停止单被触发
                    shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice<=so.price     # 空头停止单被触发
                    
                    if longTriggered or shortTriggered:
                        # 买入和卖出分别以涨停跌停价发单（模拟市价单）
                        if so.direction==DIRECTION_LONG:
                            price = tick.upperLimit
                        else:
                            price = tick.lowerLimit
                        
                        # 发出市价委托
                        self.sendOrder(so.vtSymbol, so.orderType, price, so.volume, so.strategy)
                        
                        # 从活动停止单字典中移除该停止单
                        del self.workingStopOrderDict[so.stopOrderID]
                        
                        # 从策略委托号集合中移除
                        s = self.strategyOrderDict[so.strategy.name]
                        if so.stopOrderID in s:
                            s.remove(so.stopOrderID)
                        
                        # 更新停止单状态，并通知策略
                        so.status = STOPORDER_TRIGGERED
                        so.strategy.onStopOrder(so)

    def processTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
        self.processStopOrder(tick)

        # print tick.vtSymbol, [contract for contract in self.tickStrategyDict.values()]
        
        # 推送tick到对应的策略实例进行处理
        if tick.vtSymbol in self.tickStrategyDict:
            # tick时间可能出现异常数据，使用try...except实现捕捉和过滤
            try:
                # 添加datetime字段
                if not tick.datetime:
                    tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
            except ValueError:
                self.writeCtaLog(traceback.format_exc())
                return
                
            # 逐个推送到策略实例中
            l = self.tickStrategyDict[tick.vtSymbol]
            for strategy in l:
                self.callStrategyFunc(strategy, strategy.onTick, tick)

    # def processPositionEvent(self, event):  # zls添加
    #     """处理行情推送"""
    #     pos = event.dict_['data']
    #
    #     # 推送tick到对应的策略实例进行处理
    #     # print pos.vtSymbol, [contract.vtSymbol for contract in self.tickStrategyDict.values()]
    #     if pos.vtSymbol in self.tickStrategyDict:
    #         # tick时间可能出现异常数据，使用try...except实现捕捉和过滤
    #         try:
    #             # 添加datetime字段
    #             if not pos.datetime:
    #                 pos.datetime = datetime.datetime.now().strftime('%Y%m%d %H:%M:%S.%f')
    #
    #         except ValueError:
    #             self.writeCtaLog(traceback.format_exc())
    #             return
    #
    #         # 逐个推送到策略实例中
    #         l = self.tickStrategyDict[pos.vtSymbol]
    #         for strategy in l:
    #             self.callStrategyFunc(strategy, strategy.onPosition, pos)
    
    def processOrderEvent(self, event):
        """处理委托推送"""
        order = event.dict_['data']
        
        vtOrderID = order.vtOrderID
        
        if vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[vtOrderID]            
            
            # 如果委托已经完成（拒单、撤销、全成），则从活动委托集合中移除
            if order.status in self.STATUS_FINISHED:
                s = self.strategyOrderDict[strategy.name]
                if vtOrderID in s:
                    s.remove(vtOrderID)
            
            self.callStrategyFunc(strategy, strategy.onOrder, order)
            # 保存策略执行日志
            # if order.trade_order_id is not None:
            #     self.save_strategy_order(order, strategy)
    
    def processTradeEvent(self, event):
        """处理成交推送"""
        # print('处理成交推送 processTradeEvent')
        trade = event.dict_['data']
        
        # 过滤已经收到过的成交回报
        # if trade.vtTradeID in self.tradeSet:
        #     return
        # self.tradeSet.add(trade.vtTradeID)
        
        # 将成交推送到策略对象中
        if trade.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[trade.vtOrderID]
            
            # 计算策略持仓
            if trade.direction == DIRECTION_LONG:
                strategy.pos += trade.volume
            else:
                strategy.pos -= trade.volume

            if trade.offset == OFFSET_OPEN:
                strategy.last_entry_price = trade.price

            self.callStrategyFunc(strategy, strategy.onTrade, trade)
            
            # 保存策略持仓到数据库
            # self.savePosition(strategy)
            # 保存策略执行日志
            # self.save_strategy_trade(trade, strategy)
    
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_SYNC_ORDERS, self.processSyncOrders)
        self.eventEngine.register(EVENT_REDIS, self.processRedisEvent)

    def processRedisEvent(self, event):
        # zls添加用于Redis订阅推送实现一键下单
        data = event.dict_['data']  # data是json格式
        # 推送tick到对应的策略实例进行处理
        # 根据data的格式来看这里怎么处理，希望能够直接调用到两个策略里面！！！ 待完成
        # data=[{"vtsymbol":"xxx","volume":"xxx","direct":"xxx"},{"vtsymbol":"xxx","volume":"xxx","direct":"xxx"}]
        for da in data:
            if da['vtSymbol'] in self.tickStrategyDict:
                # 逐个推送到策略实例中
                l = self.tickStrategyDict[da['vtSymbol']]
                for strategy in l:
                    self.callStrategyFunc(strategy, strategy.onRedis, da)

    def processSyncOrders(self, event):
        data = event.dict_['data']
        orders = data['orders']
        gateway_name = data['gateway_name']
        for order in orders:
            flt = {'order_id': str(order['order_id'])}
            symbol = order['symbol']
            order['order_id'] = str(order['order_id'])
            order['create_date'] = datetime.fromtimestamp(order['create_date']/1000)
            self.mainEngine.dbUpdate(ORDER_DB_NAME, '%s_%s' % (gateway_name, symbol),
                                     order, flt, True)

    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是VtTickData或者VtBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)
    
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        barData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in barData:
            bar = VtBarData()
            bar.__dict__ = d
            l.append(bar)
        return l
    
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        tickData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in tickData:
            tick = VtTickData()
            tick.__dict__ = d
            l.append(tick)
        return l    
    
    def writeCtaLog(self, content):
        """快速发出CTA模块日志事件"""
        log = VtLogData()
        log.logContent = content
        log.gatewayName = 'CTA_STRATEGY'
        event = Event(type_=EVENT_CTA_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    
    def loadStrategy(self, setting):
        """载入策略"""
        try:
            name = setting['name']
            className = setting['className']
        except Exception as e:
            self.writeCtaLog(u'载入策略出错：%s' %e)
            return

        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        if not strategyClass:
            self.writeCtaLog(u'找不到策略类：%s' %className)
            return

        # 防止策略重名
        if name in self.strategyDict:
            self.writeCtaLog(u'策略实例重名：%s' %name)

        else:
            # 创建策略实例
            strategy = strategyClass(self, setting)
            self.strategyDict[name] = strategy

            # 创建委托号列表
            self.strategyOrderDict[name] = set()

            # 保存Tick映射关系
            if strategy.vtSymbol in self.tickStrategyDict:
                l = self.tickStrategyDict[strategy.vtSymbol]
            else:
                l = []
                self.tickStrategyDict[strategy.vtSymbol] = l
            l.append(strategy)

            # 订阅合约
            # print(strategy.vtSymbol)
            contract = self.mainEngine.getContract(strategy.vtSymbol)
            # print '222222222222222222222222222222   ctaEngine.py_line471    contract:', contract
            if contract:
                # print(3333333333333333333333333333, 'ctaEngine.py_line473')
                req = VtSubscribeReq()
                req.symbol = contract.symbol
                req.exchange = contract.exchange

                # 对于IB接口订阅行情时所需的货币和产品类型，从策略属性中获取
                req.currency = strategy.currency
                req.productClass = strategy.productClass
                # print(req.productClass) #这个的编码待修改
                self.mainEngine.subscribe(req, contract.gatewayName)

            else:
                # # 下面是zls自己添加的，是否保存待确定
                # req = VtSubscribeReq()
                # req.symbol = 'USD.CNH'
                # req.exchange = 'IDEALPRO'
                # # 对于IB接口订阅行情时所需的货币和产品类型，从策略属性中获取
                # req.currency = ''
                # req.productClass = ''
                # self.mainEngine.subscribe(req, 'IB')

                self.writeCtaLog(u'%s的交易合约%s无法找到' %(name, strategy.vtSymbol))

    def subscribe(self, req, gatewayName):
        self.mainEngine.subscribe(req, gatewayName)

    def initStrategy(self, name):
        """初始化策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if not strategy.inited:
                strategy.inited = True
                self.callStrategyFunc(strategy, strategy.onInit)
            else:
                self.writeCtaLog(u'请勿重复初始化策略实例：%s' %name)
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)        

    def startStrategy(self, name):
        """启动策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.inited and not strategy.trading:
                strategy.trading = True
                self.callStrategyFunc(strategy, strategy.onStart)
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)
    
    def stopStrategy(self, name):
        """停止策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.trading:
                strategy.trading = False
                self.callStrategyFunc(strategy, strategy.onStop)
                
                # 对该策略发出的所有限价单进行撤单
                for vtOrderID, s in self.orderStrategyDict.items():
                    if s is strategy:
                        self.cancelOrder(vtOrderID)
                
                # 对该策略发出的所有本地停止单撤单
                for stopOrderID, so in self.workingStopOrderDict.items():
                    if so.strategy is strategy:
                        self.cancelStopOrder(stopOrderID)   
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)    
            
    def initAll(self):
        """全部初始化"""
        for name in self.strategyDict.keys():
            self.initStrategy(name)    
            
    def startAll(self):
        """全部启动"""
        for name in self.strategyDict.keys():
            self.startStrategy(name)

    def stopAll(self):
        """全部停止"""
        for name in self.strategyDict.keys():
            self.stopStrategy(name)    
    
    def saveSetting(self):
        """保存策略配置"""
        with open(self.settingfilePath, 'w') as f:
            l = []
            
            for strategy in self.strategyDict.values():
                setting = {}
                for param in strategy.paramList:
                    setting[param] = strategy.__getattribute__(param)
                l.append(setting)
            
            jsonL = json.dumps(l, indent=4)
            f.write(jsonL)
    
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingfilePath) as f:
            l = json.load(f)
            
            for setting in l:
                self.loadStrategy(setting)
                
        # self.loadPosition()
    
    def getStrategyVar(self, name):
        """获取策略当前的变量字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            varDict = OrderedDict()
            
            for key in strategy.varList:
                varDict[key] = strategy.__getattribute__(key)
            
            return varDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None
    
    def getStrategyParam(self, name):
        """获取策略的参数字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            paramDict = OrderedDict()
            
            for key in strategy.paramList:  
                paramDict[key] = strategy.__getattribute__(key)
            
            return paramDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None   
        
    def putStrategyEvent(self, name):
        """触发策略状态变化事件（通常用于通知GUI更新）"""
        event = Event(EVENT_CTA_STRATEGY+name)
        self.eventEngine.put(event)
        
    def callStrategyFunc(self, strategy, func, params=None):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            # 停止策略，修改状态为未初始化
            strategy.trading = False
            strategy.inited = False
            
            # 发出日志
            content = '\n'.join([u'策略%s触发异常已停止' %strategy.name,
                                traceback.format_exc()])
            self.writeCtaLog(content)
            
    def savePosition(self, strategy):
        """保存策略的持仓情况到数据库"""
        flt = {'name': strategy.name,
               'vtSymbol': strategy.vtSymbol}
        
        d = {'name': strategy.name,
             'vtSymbol': strategy.vtSymbol,
             'pos': strategy.pos,
             'last_entry_price': strategy.last_entry_price}
        
        self.mainEngine.dbUpdate(POSITION_DB_NAME, strategy.className,
                                 d, flt, True)
        
        content = '策略%s持仓保存成功，当前持仓%s' %(strategy.name, strategy.pos)
        # print(content)
        self.writeCtaLog(content)

    def banzhuan_query_position(self, vtSymbol):
        """根据下面的函数修改的搬砖策略查询仓位"""
        # vtSymbol = strategy.vtSymbol
        # contract = self.mainEngine.getContract(vtSymbol)
        # return self.mainEngine.qryPosition(contract.gatewayName)
        return self.mainEngine.dataEngine.getPositionDetail(vtSymbol)

    def query_position(self, strategy):
        vtSymbol = strategy.vtSymbol
        # contract = self.mainEngine.getContract(vtSymbol)
        # return self.mainEngine.qryPosition(contract.gatewayName)
        return self.mainEngine.dataEngine.getPositionDetail(vtSymbol)

    def query_account(self, strategy):
        contract = self.mainEngine.getContract(strategy.vtSymbol)
        return self.mainEngine.dataEngine.accountDict[contract.gatewayName]

    def loadPosition(self):
        """从数据库载入策略的持仓情况"""
        for strategy in self.strategyDict.values():
            flt = {'name': strategy.name,
                   'vtSymbol': strategy.vtSymbol}
            posData = self.mainEngine.dbQuery(POSITION_DB_NAME, strategy.className, flt)
            
            for d in posData:
                strategy.pos = d['pos']
                if 'last_entry_price' in d:
                    strategy.last_entry_price = d['last_entry_price']
                
    def roundToPriceTick(self, priceTick, price):
        """取整价格到合约最小价格变动"""
        if not priceTick:
            return price
        
        newPrice = round(price/priceTick, 0) * priceTick
        return newPrice    
    
    def stop(self):
        """停止"""
        pass
    
    def cancelAll(self, name):
        """全部撤单"""
        s = self.strategyOrderDict[name]

        # self.writeCtaLog('cancelAll 1 %s' % s)
        # 遍历列表，全部撤单
        # 这里不能直接遍历集合s，因为撤单时会修改s中的内容，导致出错
        for orderID in list(s):
            if STOPORDERPREFIX in orderID:
                self.cancelStopOrder(orderID)
            else:
                self.cancelOrder(orderID)

    def save_strategy_trade(self, trade, strategy):
        """保存策略的执行情况到数据库"""
        print("保存策略的执行情况到数据库")
        flt = {'order_id': trade.tradeID}

        # profit = trade.volume * trade.price

        d = {
             'price_avg': trade.price,
             'deal_amount': trade.sum_volume,
             'fee': trade.fee
             }

        self.mainEngine.db_update_one(STRATEGY_DB_NAME, strategy.className,
                                 d, flt, True)

    def save_strategy_order(self, order, strategy):
        print("保存下单情况到数据库")
        flt = {'order_id': order.trade_order_id}
        d = {'name': strategy.name,
             'vtSymbol': strategy.vtSymbol,
             'order_id': order.trade_order_id,
             'order_price': order.price,
             'order_amount': order.totalVolume,
             'order_time': order.orderTime,
             'unit_amount': strategy.contract_size,
             'order_type': order.order_type,
             'price_avg': 0,
             'deal_amount': 0,
             'fee': 0,
             'status': order.status
             }

        self.mainEngine.db_update_one(STRATEGY_DB_NAME, strategy.className,
                                 d, flt, True)

    def load_incomplete_orders(self, strategy):
        flt = {'name': strategy.name,
               'vtSymbol': strategy.vtSymbol,
               'status': {'$in': [STATUS_NOTTRADED, STATUS_PARTTRADED]}}
        orders = self.mainEngine.dbQueryLimit(STRATEGY_DB_NAME, strategy.className, flt, sortKey='$natural', sortDirection=-1, limit=5)

        incomplete_orders = []
        for d in orders:
            if d['deal_amount'] < d['order_amount']:
                incomplete_orders.append(d)
        return incomplete_orders
