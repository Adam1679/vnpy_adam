# encoding: UTF-8

import multiprocessing
from time import sleep
from datetime import datetime, time

from vnpy.event import EventEngine2
from vnpy.trader.vtEvent import EVENT_LOG
from vnpy.trader.vtEngine import MainEngine, LogEngine
from vnpy.trader.gateway import okcoinGateway
from vnpy.trader.app import dataRecorder

#----------------------------------------------------------------------
def runChildProcess():
    """子进程运行函数"""
    print('-' * 30)

    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    # le.addConsoleHandler()
    le.info(u'启动行情记录运行子进程')
    
    ee = EventEngine2()
    le.info(u'事件引擎创建成功')
    
    me = MainEngine(ee)
    me.addGateway(okcoinGateway)
    me.addApp(dataRecorder)
    le.info(u'主引擎创建成功')

    ee.register(EVENT_LOG, le.processLogEvent)
    le.info(u'注册日志事件监听')

    me.connect('OKEX')
    le.info(u'连接OKEX接口')

    while True:
        sleep(1)

#----------------------------------------------------------------------
def runParentProcess():
    """父进程运行函数"""
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    le.addConsoleHandler()
    le.info(u'启动行情记录守护父进程')
    
    DAY_START = time(8, 57)         # 日盘启动和停止时间
    DAY_END = time(15, 18)
    NIGHT_START = time(20, 57)      # 夜盘启动和停止时间
    NIGHT_END = time(2, 33)
    
    p = None        # 子进程句柄

    while True:
        currentTime = datetime.now().time()
        recording = True

        # # 判断当前处于的时间段
        # if ((currentTime >= DAY_START and currentTime <= DAY_END) or
        #     (currentTime >= NIGHT_START) or
        #     (currentTime <= NIGHT_END)):
        #     recording = True
        #
        # # 过滤周末时间段：周六全天，周五夜盘，周日日盘
        # if ((datetime.today().weekday() == 6) or
        #     (datetime.today().weekday() == 5 and currentTime > NIGHT_END) or
        #     (datetime.today().weekday() == 0 and currentTime < DAY_START)):
        #     recording = False

        # 记录时间则需要启动子进程
        if p is None or not p.is_alive():
            le.info(u'启动子进程')
            p = multiprocessing.Process(target=runChildProcess)
            p.start()
            le.info(u'子进程启动成功')

        # 非记录时间则退出子进程
        # if not recording and p is not None:
        #     le.info(u'关闭子进程')
        #     p.terminate()
        #     p.join()
        #     p = None
        #     le.info(u'子进程关闭成功')

        sleep(5)


if __name__ == '__main__':
    #runChildProcess()
    runParentProcess()
