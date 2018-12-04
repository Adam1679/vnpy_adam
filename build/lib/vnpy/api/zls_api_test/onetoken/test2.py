from websocket import create_connection
import time
WSS_TICK = 'wss://1token.trade/api/v1/ws/tick?gzip=true'
WSS_CANDLE = 'wss://1token.trade/api/v1/ws/candle?gzip=true'
WSS_V2 = 'wss://1token.trade/api/v1/ws/low-freq-quote-v2?gzip=true'
WSS_V3 = 'wss://1token.trade/api/v1/ws/tick-v3?gzip=true'
WSS_ACCOUNT = 'wss://1token.trade/api/v1/ws/trade/huobip/mock-zlsapi'

ws = create_connection(WSS_V2)
t = time.time()
nt = time.time()
while(1):
        if nt - t > 20:
            ws.send({'uri': 'ping'})
            t = nt
        compressData = ws.recv()
        print(compressData)
        # result = api.readData(compressData)
        # print(result)