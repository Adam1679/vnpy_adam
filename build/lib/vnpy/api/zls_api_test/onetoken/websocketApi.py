# -*- coding: utf-8 -*-

from websocket import create_connection
import gzip
import time
import StringIO
import json
import hmac
import hashlib


WSS_TICK = 'wss://onetoken.trade/api/v1/ws/tick?gzip=true'
WSS_CANDLE = 'wss://onetoken.trade/api/v1/ws/candle?gzip=true'
WSS_V2 = 'wss://onetoken.trade/api/v1/ws/low-freq-quote-v2?gzip=true'
WSS_V3 = 'wss://onetoken.trade/api/v1/ws/tick-v3?gzip=true'
WSS_ACCOUNT = 'wss://onetoken.trade/api/v1/ws/trade/huobip/mock-zlsapi'
# 例子：wss://onetoken.trade/api/v1/ws/trade/huobip/ot-user1


class onetokenWebsocketApi(object):
    def readData(self, compressData):
        # result=gzip.decompress(compressData) #python3用这个方法，python2用下面的三行代码替代
        compressedstream = StringIO.StringIO(compressData)
        gziper = gzip.GzipFile(fileobj=compressedstream)
        result = gziper.read().decode('utf-8')
        return json.loads(result)

    # ------------------WSS_TICK:实时tick、逐笔交易数据接口-------------------
    # -------------------WSS_V3:实时tick-v3行情 （Alpha）--------------------
    def auth(self):
        """支持同时订阅不同交易所的不同合约，首先需要发送auth进行认证"""
        tradeStr = """
        {
        "uri":"auth"
        }
        """
        return tradeStr

    def ping(self):
        """所有接口支持心跳方式检测服务器是否在线，心跳时长为30秒。若客户端超过30秒未发送心跳包，服务端会返回丢失心跳的通知，。"""
        tradeStr = """
        {
        "uri":"ping"
        }
        """
        return tradeStr

    def subscribeTick(self, contract):
        """
        订阅tick数据, 如果需要请求多个tick， 可以在同一个websocket里面发送多个subscribe-single-tick-verbose的请求, 每个请求带着多个不同的contract
        {
        "uri": "subscribe-single-tick-verbose",
        "contract": contract
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "subscribe-single-tick-verbose"
        tradeStr['contract'] = contract
        return json.dumps(tradeStr)

    def unsubscribeTick(self, contract):
        """
        逐笔与tick数据支持订阅后退订
        {
        "uri": "unsubscribe-single-tick-verbose",
        "contract": "bitfinex/btc.usd"
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "unsubscribe-single-tick-verbose"
        tradeStr['contract'] = contract
        return json.dumps(tradeStr)

    def subscribeZhubi(self, contract):
        """
        订阅逐笔数据, 如果需要请求多个contract的逐笔数据， 可以在同一个websocket里面发送多个subscribe-single-zhubi-verbose的请求, 每个请求带着多个不同的contract
        tradeStr = {
        "uri": "subscribe-single-zhubi-verbose",
        "contract": "bitfinex/btc.usd"
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "subscribe-single-zhubi-verbose"
        tradeStr['contract'] = contract
        return json.dumps(tradeStr)

    def unsubscribeZhubi(self, contract):
        """
        逐笔与tick数据支持订阅后退订
        {
        "uri": "unsubscribe-single-zhubi-verbose",
        "contract": "bitfinex/btc.usd"
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "unsubscribe-single-zhubi-verbose"
        tradeStr['contract'] = contract
        return json.dumps(tradeStr)

    # -----------------WSS_CANDLE:实时candle数据接口-------------------------
    def subscribeKline(self, contract, duration):
        """
        支持不同时长：1m,5m,15m,30m,1h,2h,4h,6h,1d,1w。
        支持同一连接订阅多个合约
        {
        "contract":"huobip/btc.usdt",
        "duration": "1m"
        }
        """
        tradeStr = {}
        tradeStr['contract'] = contract
        tradeStr['duration'] = duration
        return json.dumps(tradeStr)

    # ----------------------WSS_V2:24小时涨跌幅数据接口-----------------------
    def subscribeLowFreqQuote(self, contract):
        """
        推送各个合约的当前价格以及24小时涨跌幅。
        支持同时订阅不同交易所的不同合约
        每个请求可以带着1个的contracts,例子:["huobip/btc.usdt"]
        每个请求可以带着多个不同的contracts,例子:["huobip/btc.usdt", "huobip/ht.usdt"]
        {
        "uri": "batch-subscribe",
        "contracts": ["huobip/btc.usdt", "huobip/ht.usdt"]
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "batch-subscribe"
        tradeStr['contracts'] = contract
        return json.dumps(tradeStr)

    def unsubscribeLowFreqQuote(self, contract):
        """
        支持订阅后退订
        {
        "uri":"batch-unsubscribe",
        "contracts":["huobip/btc.usdt", "huobip/ht.usdt"]
        }
        """
        tradeStr = {}
        tradeStr['uri'] = "batch-unsubscribe"
        tradeStr['contract'] = contract
        return json.dumps(tradeStr)

    # ----------------------WSS_V4:账户信息订阅-----------------------
    def qryAccount(self):
        # TODO: 未完成,查询账户信息
        tradeStr = {}
        verb = 'GET'
        nonce = 0
        path = '/huobip/mock-zlsapi'
        data = ''
        secret = 'FEkYfn8Y-C8smdhjD-AIRwne7q-azONOH0A'
        api_key = 'd4ypzCNm-FOXBKDQ4-zsGq3TMK-lLfFlaNm'
        message = verb + path + str(nonce) + data
        signature = hmac.new(bytes(secret.encode('utf8')), bytes(message.encode('utf8')), digestmod=hashlib.sha256).hexdigest()
        tradeStr['Api-Nonce'] = nonce
        tradeStr['Api-Key'] = api_key
        tradeStr['Api-Signature'] = signature
        return json.dumps(tradeStr)

# TEST
if __name__ == '__main__':
    while(1):
        try:
            # ws = create_connection(WSS_TICK)
            # ws = create_connection(WSS_V2)
            ws = create_connection(WSS_ACCOUNT)
            break
        except:
            print('connect ws error,retry...')
            time.sleep(5)

    # 调用的函数在这里。
    api = onetokenWebsocketApi()
    tradeStr = api.auth()  # step 1:发送认证
    tradeStr2 = api.subscribeTick('huobip/btc.usdt')  # 查询tick
    tradeStr3 = api.subscribeZhubi('huobip/ht.usdt')  # 查询逐笔
    tradeStr4 = api.subscribeLowFreqQuote(["huobip/btc.usdt", "huobip/ht.usdt"])
    tradeStr5 = api.qryAccount()  # 查询账户信息

    ws.send(tradeStr)
    t = time.time()
    ws.send(tradeStr2)


    while(1):
        nt = time.time()
        if nt - t > 20:
            ws.send(api.ping())
            t = nt
        compressData = ws.recv()
        # print(compressData)
        result = api.readData(compressData)
        print(result)

        # if result[:7] == '{"ping"':
        #     ts=result[8:21]
        #     pong='{"pong":'+ts+'}'
        #     ws.send(pong)
        #     ws.send(tradeStr)
        # else:
        #     print(result)

