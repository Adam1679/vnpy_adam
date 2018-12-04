# encoding: UTF-8

from vnokcoin import *
from OkcoinFutureAPI import OKCoinFuture

# 在OkCoin网站申请这两个Key，分别对应用户名和密码
apiKey = ""
secretKey = "E40A608C6197554BA435A81C9C9F2E07"
okcoinRESTURL = 'www.okex.com'

# 创建API对象
api = OkCoinApi()

# 连接服务器，并等待1秒
api.connect(OKEX_CONTRACT, apiKey, secretKey, True)

sleep(1)

# 测试现货行情API
api.subscribeSpotTicker(SYMBOL_BTC)
# api.subscribeSpotTradeData(SYMBOL_BTC)
# api.subscribeSpotDepth(SYMBOL_BTC, DEPTH_20)
# api.subscribeSpotKline(SYMBOL_BTC, INTERVAL_1M)

# 测试现货交易API
# api.subscribeSpotTrades()
#api.subscribeSpotUserInfo()
# api.spotUserInfo()
# api.spotTrade(symbol, type_, price, amount)
#api.spotCancelOrder(symbol, orderid)
# api.spotOrderInfo(symbol, orderid)

# 测试期货行情API
# api.subscribeFutureTicker(SYMBOL_BCH, FUTURE_EXPIRY_QUARTER)
# api.subscribeFutureTradeData(SYMBOL_BTC, FUTURE_EXPIRY_THIS_WEEK)
# api.subscribeFutureDepth(SYMBOL_BTC, FUTURE_EXPIRY_THIS_WEEK, DEPTH_20)
# api.subscribeFutureKline(SYMBOL_BCH, FUTURE_EXPIRY_THIS_WEEK, INTERVAL_1M)
api.subscribeFutureIndex(SYMBOL_BTC)

# 测试期货交易API

# api.subscribeFutureUserInfo()
# api.subscribeFuturePositions()
# api.futureUserInfo()
# api.login()
# api.subscribeFutureTrades()
# api.futureTrade(symbol, expiry, type_, price, amount, order, leverage)
#api.futureCancelOrder(symbol, expiry, orderid)
#api.futureOrderInfo(symbol, expiry, orderid, status, page, length)


# okcoinFuture = OKCoinFuture(okcoinRESTURL, apiKey, secretKey)
# print (okcoinFuture.future_index('ltc_usd'))
# print (okcoinFuture.future_position('btc_usd', 'quarter'))
# print(api.future_postion('btc_usd'))
# raw_input()

# api.futureTrade('btc_', '1', '5000', 1)
