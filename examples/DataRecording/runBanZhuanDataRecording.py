# encoding: UTF-8

import multiprocessing
from time import sleep
from datetime import datetime, time

from vnpy.event import EventEngine2
from vnpy.trader.vtEvent import EVENT_LOG
from vnpy.trader.vtEngine import MainEngine, LogEngine
from vnpy.trader.gateway import ctpGateway,oandaGateway
from vnpy.trader.app import dataRecorder


# ----------------------------------------------------------------------
def runChildProcess():
    """子进程运行函数"""
    print('-' * 30)

    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    le.addConsoleHandler()
    le.info(u'启动行情记录运行子进程')

    ee = EventEngine2()
    le.info(u'事件引擎创建成功')

    me = MainEngine(ee)

    me.addGateway(ctpGateway)
    me.addGateway(oandaGateway)

    me.addApp(dataRecorder)
    le.info(u'主引擎创建成功')

    ee.register(EVENT_LOG, le.processLogEvent)
    le.info(u'注册日志事件监听')

    me.connect('CTP')
    le.info(u'连接OKEX接口')

    me.connect('OANDA')
    le.info(u'连接OKEX接口')

    while True:
        sleep(1)


# ----------------------------------------------------------------------
def runParentProcess():
    """父进程运行函数"""
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    le.addConsoleHandler()
    le.info(u'启动行情记录守护父进程')

    # DAY_START = time(8, 57)  # 日盘启动和停止时间
    # DAY_END = time(15, 18)
    # NIGHT_START = time(20, 57)  # 夜盘启动和停止时间
    # NIGHT_END = time(2, 33)

    p = None  # 子进程句柄



    while True:
        # currentTime = datetime.now().time()
        recording = isTimeAllTrading()

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
        if not recording and p is not None:
            le.info(u'关闭子进程')
            p.terminate()
            p.join()
            p = None
            le.info(u'子进程关闭成功')

        sleep(5)


r = redis.Redis(host=redisHost, port=6379, db=8)
def isTimeAllTrading():
    t = datetime.datetime.now().strftime('%Y-%m-%d')
    date = int(datetime.datetime.now().strftime('%Y%m%d'))
    hour = int(datetime.datetime.now().strftime('%H'))
    minu = int(datetime.datetime.now().strftime('%M'))
    # 判断今天是否是交易日
    rdate = r.get('date')
    rflag = r.get('isTrading')
    if rdate and int(rdate) == date:
        flag = int(rflag)
    else:
        self.usdcnyRate()
        a = ts.trade_cal()
        flag = int(a[a.calendarDate == t].isOpen)
        r.set('date',date)
        r.set('isTrading',flag)
    if flag:
        # 判断现在是否是交易时间
        if hour in [9,14,21,22,23,0,1]:
            return True
        elif hour in [11,2]:
            if minu<30:
                return True
        elif hour == 10:
            if minu<15 or minu>30:
                return True
        elif hour == 13:
            if minu>30:
                return True
    return False


if __name__ == '__main__':
    # runChildProcess()
    runParentProcess()
