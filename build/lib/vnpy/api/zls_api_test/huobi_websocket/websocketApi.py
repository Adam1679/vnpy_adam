# -*- coding: utf-8 -*-

from websocket import create_connection
import gzip
import time
import StringIO


class HuoBiWebsocketApi(object):
    # 订阅 KLine 数据
    def subscribeKLine(self):
        tradeStr = """{"sub": "market.btcusdt.kline.1min","id": "id10"}"""
        return tradeStr


    # 请求 KLine 数据
    def sendKLineRequest(self):
        tradeStr="""{"req": "market.btcusdt.kline.1min","id": "id10", "from": 1513391453, "to": 1513392453}"""
        return tradeStr


    # 订阅 Market Depth 数据
    def subscribeMarketDepth(self):
        tradeStr="""{"sub": "market.btcusdt.depth.step5", "id": "id10"}"""
        return tradeStr


    # 请求 Market Depth 数据
    def sendMarketDepthRequest(self):
        tradeStr="""{"req": "market.ethusdt.depth.step5", "id": "id10"}"""
        return tradeStr


    # 订阅 Trade Detail 数据
    def subscribeTradeDetail(self):
        tradeStr="""{"sub": "market.ethusdt.trade.detail", "id": "id10"}"""
        return tradeStr


    # 请求 Trade Detail 数据
    def sendTradeDetailRequest(self):
        tradeStr="""{"req": "market.btcusdt.trade.detail", "id": "id10"}"""
        return tradeStr


    # 请求MarketDetail数据
    def sendMarketDetailRequest(self):
        tradeStr="""{"req": "market.btcusdt.detail", "id": "id12"}"""
        return tradeStr


if __name__ == '__main__':
    while(1):
        try:
            ws = create_connection("wss://api.huobipro.com/ws")
            break
        except:
            print('connect ws error,retry...')
            time.sleep(5)

    # 调用的函数在这里。
    api = HuoBiWebsocketApi()
    tradeStr = api.sendKLineRequest()

    ws.send(tradeStr)
    while(1):
        compressData = ws.recv()
        # result=gzip.decompress(compressData) #python3用这个方法，python2用下面的三行代码替代
        compressedstream = StringIO.StringIO(compressData)
        gziper = gzip.GzipFile(fileobj=compressedstream)
        result = gziper.read().decode('utf-8')

        if result[:7] == '{"ping"':
            ts=result[8:21]
            pong='{"pong":'+ts+'}'
            ws.send(pong)
            ws.send(tradeStr)
        else:
            print(result)
