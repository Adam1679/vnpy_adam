# encoding: UTF-8

import multiprocessing
from time import sleep
from datetime import datetime, time
from threading import Event
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from vnpy.event import EventEngine2
from vnpy.trader.vtEvent import EVENT_LOG
from vnpy.trader.vtEngine import MainEngine, LogEngine
from vnpy.trader.gateway import ibGateway, ctpGateway
from vnpy.trader.app import ctaStrategy, riskManager, dataRecorder
from vnpy.trader.app.ctaStrategy.ctaBase import EVENT_CTA_LOG


#----------------------------------------------------------------------
def runChildProcess():
    """子进程运行函数"""
    # print('-'*20)
    
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_WARN)
    # le.addConsoleHandler()
    le.addFileHandler()

    le.info(u'启动CTA策略运行子进程')
    
    ee = EventEngine2()
    le.info(u'事件引擎创建成功')
    
    me = MainEngine(ee)

    me.addGateway(ctpGateway)
    me.addGateway(ibGateway)

    me.addApp(riskManager)
    me.addApp(ctaStrategy)
    # me.addApp(dataRecorder)
    le.info(u'主引擎创建成功')

    ee.register(EVENT_LOG, le.processLogEvent)
    ee.register(EVENT_CTA_LOG, le.processLogEvent)
    le.info(u'注册日志事件监听')

    me.connect('IB')
    le.info(u'连接IB接口')
    sleep(5)    # 等待接口初始化
    me.connect('CTP')
    le.info(u'连接CTP接口')

    # sleep(10)    # 等待接口初始化
    can_done1 = Event()
    can_done1.wait(timeout=10)
    cta = me.getApp(ctaStrategy.appName)
    cta.loadSetting()
    le.info(u'CTA策略载入成功')

    cta.initAll()
    le.info(u'CTA策略初始化成功')

    cta.startAll()
    le.info(u'CTA策略启动成功')

    while True:
        can_done2 = Event()
        can_done2.wait(timeout=1)

# ----------------------------------------------------------------------
def runParentProcess():
    """父进程运行函数"""
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_WARN)
    le.addConsoleHandler()
    
    le.info(u'启动CTA策略守护父进程')
    
    DAY_START1 = time(8, 58)         # 日盘上午启动和停止时间
    DAY_END1 = time(10, 17)

    DAY_START2 = time(10, 28)
    DAY_END2 = time(11, 32)

    DAY_START3 = time(13, 28)  # 日盘下午启动和停止时间
    DAY_END3 = time(15, 02)

    NIGHT_START = time(20, 58)      # 夜盘启动和停止时间
    NIGHT_END = time(2, 32)
    
    p = None        # 子进程句柄
    # scheduler = BackgroundScheduler()
    # scheduler = BlockingScheduler()
    
    while True:
        currentTime = datetime.now().time()
        # recording = False   # 实际环境应该是这个
        recording = True    # 用于测试，开盘收盘时间之外也可以执行策略里面

        
        # 判断当前处于的时间段
        if (currentTime >= DAY_START1 and currentTime <= DAY_END1) or (currentTime >= DAY_START2 and currentTime <= DAY_END2) or (currentTime >= DAY_START3 and currentTime <= DAY_END3) or (currentTime >= NIGHT_START) or (currentTime <= NIGHT_END):
            recording = True
        
        # 记录时间则需要启动子进程
        if recording and p is None:
            le.info(u'启动子进程')
            print 'before new'
            p = multiprocessing.Process(target=runChildProcess)
            print 'new mid'
            p.start()
            print 'new'
            le.info(u'子进程启动成功')

        # 非记录时间则退出子进程
        if not recording and p is not None:
            le.info(u'关闭子进程')
            p.terminate()
            p.join()
            p = None
            le.info(u'子进程关闭成功')

        # sleep(5)
        can_done = Event()
        can_done.wait(timeout=5)


if __name__ == '__main__':
    # runChildProcess()

    # 尽管同样实现了无人值守，但强烈建议每天启动时人工检查，为自己的PNL负责
    runParentProcess()