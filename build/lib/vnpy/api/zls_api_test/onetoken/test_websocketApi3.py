# -*- coding: utf-8 -*-
from websocketApi3 import onetokenWebsocketApi
import time
from multiprocessing import Pool, Process
import threading

ACCOUNT_NAME = "huobip/mock-adamzzz"
SECRET = 'tRJs6HQP-cnpMnEB7-T9xRGOGM-TOusHtG7'
API_KEY = '9rsmJL65-ztLxddIV-H1a2c1xw-gcwWTFOM'

if __name__ == "__main__":
    # 获取数据

    t = time.time()
    api = onetokenWebsocketApi()
    api.login(account=ACCOUNT_NAME,
              apiKey=API_KEY,
              secretKey=SECRET)

    # -----------websocket 测试-----------
    api.ws_connect(data_type='tick')
    # api.ws_connect(data_type='bar')
    time.sleep(5)
    api.send_ping(api.ws_dict['tick'])
    api.subscribeTick(contract='huobip/btc.usdt')  # work!
    # api.subscribeKline(contract='huobip/btc.usdt', duration='1m')  # work!
    # api3.subscribeZhubi(contract='huobip/btc.usdt') # work!
    # api.subscribeTick_v3(contract='huobip/btc.usdt') # not work
    # api.subscribeLowFreqQuote(contract=["okex/btc.usdt"]) # work!
    # api.subscribeAccount()
    # -----------restful 测试-----------
    # api.startReq()
    # api.qryAccount() # ok
    # api.sendOrder("huobip/btc.usdt", amount=100, direction="b", price=30) # ok
    # api.qryOrder(contract="huobip/btc.usdt") # ok
    # api.cancelOrder(client_oid=u"xxx2") # ok
    # api.cancelAll(contract="huobip/btc.usdt") # ok
    # api.qryTransaction(contract="huobip/btc.usdt") # ok
    # time.sleep(2)
    # api.close()