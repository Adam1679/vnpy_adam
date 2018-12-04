# -*- coding: utf-8 -*-

import websocket
import gzip
import time
import StringIO
import json
import zlib
import json
from threading import Thread
from urlparse import urlparse
import hmac
import hashlib
import requests
import os
import warnings
from Queue import Queue, Empty

SECRET = 'tRJs6HQP-cnpMnEB7-T9xRGOGM-TOusHtG7'
API_KEY = '9rsmJL65-ztLxddIV-H1a2c1xw-gcwWTFOM'
ACCOUNT_NAME = "huobip/mock-adamzzz"

class onetokenWebsocketApi(object):
    params_dict = {
        'Account': {'info': ['获取账户信息'],
                    "withdraws": ['获取提币记录', '请求提币', '取消提币']},
        'Order': {'orders': ['查询订单信息','创建订单','修改订单，只有BITMEX交易所支持','取消订单，最多支持同时取消9个订单'],
                  'orders/all': ['取消所有符合条件的订单'],
                  'trans': ['获取最近成交记录']}
    }

    WSS_TICK = 'wss://1token.trade/api/v1/ws/tick?gzip=true'  # tick数据，返回gzip
    WSS_CANDLE = 'wss://1token.trade/api/v1/ws/candle?gzip=true'  # bar数据，支持 1m,5m,15m,30m,1h,2h,4h,6h,1d,1w
    WSS_V2 = 'wss://1token.trade/api/v1/ws/low-freq-quote-v2?gzip=true'  # 24小时涨跌幅
    WSS_V3 = 'wss://1token.trade/api/v1/ws/tick-v3?gzip=true'
    WSS_ACCOUNT = 'wss://1token.trade/api/v1/ws/trade'
    RES_URL = "https://1token.trade/api/v1/"

    def __init__(self):
        """Constructor"""
        self.apiKey = ''  # 用户名
        self.secretKey = ''  # 密码
        self.host = ''  # 服务器地址
        self.currency = ''  # 货币类型（usd或者cny）
        self.ws = None  # websocket应用对象
        self.thread = {}  # 工作线程
        self.ping_thread = {} # ping的线程
        self.rec_thread = {} # 获取数据的线程
        self.accounts = []
        self.exchange = ''
        self.account_name = ''
        self.account_symbol = ''
        self.reqID = 0
        self.reqQueue = Queue()  # 请求队列
        self.reqThread = Thread(target=self.processQueue)
        self.orderDict = {}
        self.ws_dict = {'bar': None,
                        'tick': None,
                        'info': None}
        self.host_dict = {'bar': self.WSS_CANDLE,
                     'tick': self.WSS_TICK,
                     'info': self.WSS_ACCOUNT}

    def readData(self, compressData):
        # result=gzip.decompress(compressData) #python3用这个方法，python2用下面的三行代码替代
        compressedstream = StringIO.StringIO(compressData)
        gziper = gzip.GzipFile(fileobj=compressedstream)
        result = gziper.read().decode('utf-8')
        return json.loads(result)

    def startReq(self):
        self.active = True
        self.reqThread.start()

    def generateSign(self, secret, verb, url, nonce, data_str=None):
        if data_str is None:
            data_str = ''

        parsed_url = urlparse(url)
        path = parsed_url.path

        # print "Computing HMAC: %s" % verb + path + str(nonce) + data
        message = os.path.join(verb, path) + str(nonce) + data_str
        # print(message)

        signature = hmac.new(bytes(secret).encode('utf8'),
                             bytes(message).encode('utf8'), digestmod=hashlib.sha256).hexdigest()
        return signature

    def gen_headers(self, nonce, key, sig):
        headers = {
            'Api-Nonce': str(nonce),
            'Api-Key': key,
            'Api-Signature': sig,
            'Content-Type': 'application/json'
        }
        return headers

    def gen_nonce(self):
        return str((int(time.time() * 1000000)))

    def auth(self, ws, **kwargs):
        """支持同时订阅不同交易所的不同合约，首先需要发送auth进行认证"""
        tradeStr = {
        "uri": "auth"
        }
        tradeStr.update(kwargs)
        params = json.dumps(tradeStr)
        ws.send(params)

    def login(self, account, apiKey, secretKey):
        self.account_symbol = account
        self.exchange, self.account_name = account.split("/")
        self.apiKey = apiKey
        self.secretKey = secretKey

    def processQueue(self):
        """处理请求队列中的请求"""
        while self.active:
            try:
                req = self.reqQueue.get(block=True, timeout=1)  # 获取请求的阻塞为一秒
                callback = req['callback']
                reqID = req['reqID']
                r = callback(req['params'], reqID)
            except Empty:
                pass

    # -----------------Restful:下单------------------------
    def sendOrder(self, symbol, price, amount, direction, client_oid=None, options=None):
        """
        :param symbol: contract
        :param price:
        :param amount:
        :param direction: 'long' or 'short'
        :param client_oid: 由用户指定或者由OneToken随机生成，用于追踪订单信息。
        :param options:
            e.g :
            {
              "contract": "string",
              "bs": "b",
              "price": 0,
              "amount": 0,
              "client_oid": "string",
              "options": {
                "additionalProp1": "string",
                "additionalProp2": "string",
                "additionalProp3": "string"
              }
            }
        :return:
        {
            "exchange_oid": "string", # 由交易所生成，用于追踪订单信息。
            "client_oid": "string"
        }
        sample: {u'client_oid': u'xxx2', u'exchange_oid': u'huobip/btc.usdt-sfazm8495l0h7mmk4yq97wmp6zo'}
        """
        params = dict()

        self.reqID += 1
        params['contract'] = symbol
        params['price'] = price
        params['amount'] = abs(amount)
        params['bs'] = direction
        if client_oid is not None:
            params['client_oid'] = client_oid
        if options is not None:
            params['options'] = options
        data = {'reqID': self.reqID, 'callback': self.onSendOrder, 'params': params}
        self.reqQueue.put(data)

    def onSendOrder(self, params, reqID):
        r = self.sendTradingRequest(data=params,
                                       path="%s/%s/orders" % (self.exchange, self.account_name),
                                       verb="POST"
                                       )
        orderID = r['exchange_oid']
        self.orderDict[reqID] = orderID
        print(r)
        return r

    # ----------------- Restful:撤单,撤所有 ------------------------
    def cancelAll(self, contract=None):
        """
        :param contract: 类似于binance/btc.usdt。对于部分交易所，如果不输入此参数可以撤销所有交易对的订单，根据交易所实际情况而定。
        :return: sample
        {u'status': u'success'}
        """
        self.reqID += 1
        if contract is not None:
            params = {'contract': contract}
        else:
            params = None
        data = {'reqID': self.reqID, 'callback': self.onCancelAll, 'params': params}
        self.reqQueue.put(data)

    def onCancelAll(self, params, reqID=None):
        r = self.sendTradingRequest(params=params,
                                path="%s/%s/orders/all" % (self.exchange, self.account_name),
                                verb="DELETE"
                                )
        print(r)

    # ----------------- Restful:撤单 ------------------------
    def cancelOrder(self, client_oid=None, exchange_oid=None):
        """
        :param client_oid: 用户定义的订单号，最多支持9个订单号，用逗号分隔。
        :param exchange_oid: 交易所生成的订单号，最多支持9个订单号，用逗号分隔。
        :return:
        [{u'exchange_oid': u'huobip/btc.usdt-sfazm8495l0h7mmk4yq97wmp6zo'}]
        """
        params = {}
        self.reqID += 1
        if client_oid is None and exchange_oid is None:
            raise ValueError("至少输入一个参数")

        if client_oid is not None:
            params['client_oid'] = client_oid
        if exchange_oid is not None:
            params['exchange_oid'] = exchange_oid

        data = {'reqID': self.reqID, 'callback': self.onCancelOrder, 'params': params}
        self.reqQueue.put(data)

    def onCancelOrder(self, params, reqID=None):
        r = self.sendTradingRequest(params=params,
                                path="%s/%s/orders" % (self.exchange, self.account_name),
                                verb="DELETE"
                                )
        print(r)

    # ----------------- Restful:查询订单 ------------------------
    def qryOrder(self, contract=None, client_oid=None, exchange_oid=None, status=None):
        """
        :param contract: e.g "binance/btc.usdt"
        :param status: available values : waiting, pending, withdrawing, withdrawn, dealt, part-deal-pending,
                        part-deal-withdrawn, part-deal-withdrawing, error-order, active, end
        :param client_oid: 用户定义的订单号，最多支持9个订单号，用逗号分隔。
        :param exchange_oid: 交易所生成的订单号，最多支持9个订单号，用逗号分隔。
        :return:
            e.g
            [
              {
                "account": "string",
                "average_dealt_price": 0,
                "bs": "string",
                "client_oid": "string",
                "comment": "string",
                "commission": 0,
                "contract": "string",
                "dealt_amount": 0,
                "entrust_amount": 0,
                "entrust_price": 0,
                "entrust_time": "string",
                "exchange_oid": "string",
                "last_dealt_amount": 0,
                "canceled_time": "string",
                "closed_time": "string",
                "ots_closed_time": "string",
                "last_update": "string",
                "exchange_update": "string",
                "options": {},
                "status": "waiting",
                "tags": {}
              }
            ]
        """
        params = dict()
        self.reqID += 1
        if contract is not None:
            params['contract'] = contract
        if client_oid is not None:
            params['client_oid'] = client_oid
        if exchange_oid is not None:
            params['exchange_oid'] = exchange_oid

        data = {'reqID': self.reqID, 'callback': self.onQryOrder, 'params': params}
        self.reqQueue.put(data)

    def onQryOrder(self, params, reqID=None):
        r = self.sendTradingRequest(params=params,
                                       path="%s/%s/orders" % (self.exchange, self.account_name),
                                       verb="GET")
        print(r)

    # ----------------- Restful:查询成交信息 ------------------------
    def qryTransaction(self, contract=None, count=None):
        """
        :param contract: 建议填写。但是对于部分交易所，此项不填可以返回所有成交。
        :param count: 返回成交记录的条数
        :return:
        """

        params = {}
        self.reqID += 1
        if contract is not None:
            params['contract'] = contract
        else:
            warnings.showwarning(":param contract: 建议填写。但是对于部分交易所，此项不填可以返回所有成交。")

        if count is not None:
            params['count'] = count

        data = {'reqID': self.reqID,
                'callback': self.onQryTransaction,
                'params': params}
        self.reqQueue.put(data)

    def onQryTransaction(self, params, reqID=None):
        r = self.sendTradingRequest(params=params,
                                       verb='GET',
                                       path="%s/%s/trans" % (self.exchange, self.account_name))
        print(r)

    def sendTradingRequest(self,
                           path,
                           verb,
                           params=None,
                           data=None
                           ):
        """
        :param verb: "POST" or "GET" or "DELETE"
        :param path: 根据具体的操作进行构造{exchange}/{account}/orders e.g '/huobip/zannb/orders'
        :param nonce: 时间戳
        :param data: 具体的操作信息 e.g data = {"contract": "huobip/btc.usdt", "price": 1, "bs": "b", "amount": 0.6}
        :return:
        """
        if params is not None and len(params)==0:
            params = None
        if data is not None and len(data)==0:
            data = None
        nonce = self.gen_nonce()
        data_str = json.dumps(data, sort_keys=True) if data is not None else ""
        sig = self.generateSign(self.secretKey, verb, path, nonce, data_str)
        headers = self.gen_headers(nonce, self.apiKey, sig)
        # server并不要求请求中的data按key排序，只需所发送请求中的data与用来签名的data_str和相同即可，是否排序请按实际情况选择
        if verb == "POST":
            resp = requests.post(os.path.join(self.RES_URL, "trade", path), headers=headers, data=data_str, params=params)
        elif verb == "GET":
            resp = requests.get(os.path.join(self.RES_URL, "trade", path), headers=headers, data=data_str, params=params)
        elif verb == 'DELETE':
            resp = requests.delete(os.path.join(self.RES_URL, "trade", path), headers=headers, data=data_str, params=params)
        else:
            pass
        return resp.json()

    def qryAccount(self):
        """
        {
          "balance": 4362.166242423991,                 # 总资产 = 现金 + 虚拟货币市值
          "cash": 0.0,                                  # 现金（根据人民币汇率计算）
          "market_value": 4362.166242423991,            # 货币市值
          "market_value_detail": {                      # 每个币种的市值
            "btc": 0.0,
            "usdt": 0.0,
            "eth": 4362.166242423991
          },
          "position": [{                                # 货币持仓，默认包含btc，usdt或法币
              "total_amount": 1.0,                      # 总数
              "contract": "eth",                        # 币种
              "market_value": 4362.166242423991,        # 市值
              "available": 0.97,                        # 可用数量
              "frozen": 0.03,                           # 冻结数量
              "type": "spot"                            # 类型，spot表示现货持仓
            },
            {
              "total_amount": 0.0,
              "contract": "usdt",
              "market_value": 0.0,
              "available": 0.0,
              "frozen": 0.0,
              "type": "spot",
              "value_cny": 0.0
            },
            {
              "total_amount": 0.0,
              "contract": "btc",
              "market_value": 0.0,
              "available": 0.0,
              "frozen": 0.0,
              "type": "spot"
            }
          ]
        }
        sample:
        {u'market_value_detail': {u'usdt': 0.0, u'eth': 281424.5021877569, u'btc': 360121.62614054297},
         u'market_value': 641546.1283282998,
         u'balance': 865561.1346905641,
         u'cash': 224015.00636226428,
         u'position': [
                       {u'available': 8.0698, u'market_value': 360121.62614054297, u'total_amount': 8.0798, u'frozen': 0.01, u'contract': u'btc', u'extra_info': {}, u'type': u'spot', u'value_cny': 360121.62614054297},
                       {u'available': 32667.309774, u'market_value': 0.0, u'total_amount': 32667.309774, u'frozen': 0.0, u'contract': u'usdt', u'extra_info': {}, u'type': u'spot', u'value_cny': 224015.00636226428},
                       {u'available': 197.39999999999998, u'market_value': 281424.5021877569, u'total_amount': 199.99999999999997, u'frozen': 2.6000000000000005, u'contract': u'eth', u'extra_info': {}, u'type': u'spot', u'value_cny': 281424.5021877569}
                       ]
         }
         """
        return self.sendTradingRequest(
                                verb="GET",
                                path="%s/%s/info" % (self.exchange, self.account_name)
        )

    def ws_connect(self, data_type, **options):
        """连接服务器"""
        headers = None
        host = self.host_dict[data_type]
        if data_type == "info":
            verb = 'GET'
            nonce = self.gen_nonce()
            secret = self.secretKey
            path = "/ws/%s" % self.account_name
            api_key = self.apiKey
            signature = self.generateSign(secret, verb, path, nonce, data_str=None)

            headers = self.gen_headers(nonce, api_key, signature)

        self.ws_dict[data_type] = OneTokenWebSocket(host,
                                                     header=headers,
                                                     on_message=onMessage,
                                                     on_error=onError,
                                                     on_close=onClose,
                                                     on_open=onOpen
                                                     )

        self.ws_dict[data_type].data_type = data_type
        self.thread[data_type] = Thread(target=self.ws_dict[data_type].run_forever, kwargs={'ping_interval': 10})
        self.thread[data_type].start()

    def reconnect(self, data_type):
        """重新连接"""
        pass

    def close(self):
        """关闭接口"""
        for k in self.thread.keys():
            if self.thread[k] and self.thread[k].isAlive():
                self.ws[k].close()
                self.thread[k].join()
                self.ping_thread[k].join()

        if self.reqThread and self.reqThread.isAlive():
            self.active = False
            self.reqThread

    def send_ping(self, ws):
        """所有接口支持心跳方式检测服务器是否在线，心跳时长为30秒。若客户端超过30秒未发送心跳包，服务端会返回丢失心跳的通知，。"""
        tradeStr = {"uri": "ping"}
        params = json.dumps(tradeStr)
        ws.send(params)
        print("s")


    # -----------------WSS_TICK:实时TICK数据接口-------------------------
    def subscribeTick(self, contract):
        """
        订阅tick数据, 如果需要请求多个tick， 可以在同一个websocket里面发送多个subscribe-single-tick-verbose的请求, 每个请求带着多个不同的contract

        //Websocket Client request
        {
            "uri": "subscribe-single-tick-verbose",
            "contract": "bitfinex/btc.usd"
        }

        //Websocket Server response
        {
            "uri":"single-tick-verbose",
            "data":
            {
                 "asks":
                 [
                     {"price": 9218.5, "volume": 1.7371},
                     ...
                 ],
                 "bids":
                 [
                     {"price": 9218.4, "volume": 0.81871728},
                     ...
                 ],
                 "contract": "bitfinex/btc.usd",
                 "last": 9219.3,  // 最新成交价
                 "time": "2018-05-03T16:16:41.630400+08:00",  // 1token的系统时间 ISO 格式 带时区
                 "exchange_time": "2018-05-03T16:16:41.450400+08:00",  // 交易所给的时间 ISO 格式 带时区
                 "amount": 16592.4,  //成交额 (CNY)
                 "volume": 0.3   // 成交量
           }
        }
        """
        if self.ws_dict['tick'] is None:
            self.ws_connect(data_type='tick')

        self.auth(self.ws_dict['tick'])
        self.sendMarketDataRequest(ws=self.ws_dict['tick'], contract=contract, uri="subscribe-single-tick-verbose")
    # # -----------------WSS_v3:实时TICK数据接口-------------------------
    # def subscribeTick_v3(self, contract):
    #     """
    #     推送v3格式的tick行情，每隔30秒服务器会推送snapshot，在此间隔内发送diff，客户端可以通过计算snapshot+diff得出当前行情。
    #     在diff类型的数据中，如bids或者asks中存在[x,y=0]的情况，则删除上个snapshot中bids或asks价格为x的行情，否则更新此行情。
    #     """
    #     self.ws_connect(self.WSS_V3, self.apiKey, self.secretKey)
    #     self.auth(self.ws_dict['tick'])
    #     self.sendMarketDataRequest(contract, self.ws_dict['tick'])

    # -----------------WSS_TICK:实时ZHUBI数据接口-------------------------
    def subscribeZhubi(self, contract):
        """
        订阅逐笔数据, 如果需要请求多个contract的逐笔数据， 可以在同一个websocket里面发送多个subscribe-single-zhubi-verbose的请求, 每个请求带着多个不同的contract
        tradeStr = {
        "uri": "subscribe-single-zhubi-verbose",
        "contract": "bitfinex/btc.usd"
        }
        return:
        {u'data': [{u'exchange_time': u'2018-10-29T07:28:45.293000+00:00', u'price': 6499.4, u'bs': u's', u'contract': u'huobip/btc.usdt', u'amount': 0.1154, u'time': u'2018-10-29T15:28:45.866691+08:00'}], u'uri': u'single-zhubi-verbose'}
        """
        if self.ws_dict['tick'] is None:
            self.ws_connect(data_type='zhubi')

        self.auth(self.ws_dict['zhubi'])
        self.sendMarketDataRequest(self.ws_dict['zhubi'], contract, uri="subscribe-single-zhubi-verbose")

    # -----------------WSS_CANDLE:实时candle数据接口-------------------------
    def subscribeKline(self, contract, duration):
        """
        支持不同时长：duration=1m,5m,15m,30m,1h,2h,4h,6h,1d,1w。
        支持同一连接订阅多个合约

        //Websocket Client request
        {
            "contract":"huobip/btc.usdt",
            "duration": "1m"
        }

        //Websocket Server response
        {
            "amount": 16592.4, //成交量
            "close": 9220.11,
            "high": 9221,
            "low": 9220.07,
            "open": 9220.07,
            "volume": 0.3, //成交额
            "contract": "huobip/btc.usdt",
            "duration": "1m",
            "time": "2018-05-03T07:30:00Z" // 时间戳 isoformat
        }
        """
        if self.ws_dict['bar'] is None:
            self.ws_connect(data_type='bar')

        self.auth(self.ws_dict['bar'])
        self.sendMarketDataRequest(self.ws_dict['bar'], contract, duration=duration)

    # # ----------------------WSS_V2:24小时涨跌幅数据接口-----------------------
    # def subscribeLowFreqQuote(self, contract):
    #     """
    #     推送各个合约的当前价格以及24小时涨跌幅。
    #     支持同时订阅不同交易所的不同合约
    #     每个请求可以带着1个的contracts,例子:["huobip/btc.usdt"]
    #     每个请求可以带着多个不同的contracts,例子:["huobip/btc.usdt", "huobip/ht.usdt"]
    #
    #     //Websocket Client request
    #     {
    #         "uri":"batch-subscribe",
    #         "contracts":["huobip/btc.usdt", "huobip/ht.usdt"]
    #     }
    #
    #     //Websocket Server response
    #     {
    #         "uri":"batch-subscribe",
    #         "code":"success"
    #     }
    #
    #     //Websocket Server response
    #     {
    #         "uri":"low-freq-quote",
    #         "data":
    #         [
    #             {
    #                 "contract":"huobip/btc.usdt",
    #                 "rise":3.345103,
    #                 "price":6152.32,
    #                 "price_s":"6152.32"         //根据交易所的min_change format的字符串
    #             },
    #             {
    #                 "contract":"huobip/ht.usdt",
    #                 "rise":-0.539916,
    #                 "price":3.7027,
    #                 "price_s":"3.7027"
    #             }
    #         ]
    #     }
    #     """
    #     self.ws_connect(self.WSS_V2, self.apiKey, self.secretKey)
    #     self.sendMarketDataRequest(contract, uri="batch-subscribe")

    # ----------------------WSS_V4:账户信息订阅-----------------------
    def subscribeAccount(self):
        """ account name 必须为{exchange}/{account}的类型, 不支持模拟账户"""
        host = os.path.join(self.WSS_ACCOUNT, account)
        self.ws_connect(data_type="info")
        self.ws['info'].send(json.dumps({"uri": "sub-info"}))

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
        params = json.dumps(tradeStr)
        self.ws.send(params)

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

    def sendMarketDataRequest(self, ws, contract, **kwargs):
        tradeStr = {}
        if isinstance(contract, str):
            tradeStr['contract'] = contract
        elif isinstance(contract, list):
            tradeStr['contracts'] = contract
        tradeStr.update(kwargs)
        params = json.dumps(tradeStr)
        try:
            ws.send(params)
        except websocket.WebSocketConnectionClosedException:
            pass

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

def onMessage(ws, evt):
    """信息推送"""
    if ws.data_type == "tick" or ws.data_type == "bar":
        evt = readData(evt)
    print(evt)

def onError(ws, evt):
    """错误推送"""
    print('onError')
    print(evt)

def onClose(ws):
    """接口断开"""
    print('onClose')

def onOpen(ws):
    """接口打开"""
    pass

def readData(compressData):
    # result=gzip.decompress(compressData) #python3用这个方法，python2用下面的三行代码替代
    compressedstream = StringIO.StringIO(compressData)
    gziper = gzip.GzipFile(fileobj=compressedstream)
    result = gziper.read().decode('utf-8')
    return json.loads(result)

class OneTokenWebSocket(websocket.WebSocketApp):
    def _send_ping(self, interval, event):
        while not event.wait(interval):
            self.last_ping_tm = time.time()
            if self.sock:
                try:
                    tradeStr = {"uri": "ping"}
                    params = json.dumps(tradeStr)
                    self.sock.ping(payload=params)
                except Exception as ex:
                    warnings.warning("send_ping routine terminated: {}".format(ex))
                    break