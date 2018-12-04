# encoding: utf-8

from vnhuobi import *

#----------------------------------------------------------------------
def testTrade():
    """测试交易"""
    accessKey = '5adf1926-1c334fbf-13736665-63ff7'
    secretKey = 'ea50c334-29f364bc-f5e74eba-20253'
    
    # 创建API对象并初始化
    api = TradeApi()
    api.DEBUG = True
    api.init(accessKey, secretKey)
    
    # 查询账户，测试通过
    api.getAccountInfo()
    
    # 查询委托，测试通过
    #api.getOrders()
    
    # 买入，测试通过
    #api.buy(7100, 0.0095)
    
    # 卖出，测试通过
    #api.sell(7120, 0.0095)
    
    # 撤单，测试通过
    #api.cancelOrder(3915047376L)
    
    # 查询杠杆额度，测试通过
    #api.getLoanAvailable()
    
    # 查询杠杆列表，测试通过
    #api.getLoans()
 
    # 阻塞
    input()    


#----------------------------------------------------------------------
def testData():
    """测试行情接口"""
    api = HuoBiMarketApi()

    # 连接服务器，并等待1秒
    api.connect(True)
    api.subscribeTick('btcusdt')
    api.subscribeKLine('btcusdt')
    sleep(1)

    # 订阅成交推送，测试通过
    #api.subscribeTick(SYMBOL_BTCCNY)
    
    # 订阅报价推送，测试通过
    #api.subscribeQuote(SYMBOL_BTCCNY)

    # 订阅深度推送，测试通过
    #api.subscribeDepth(SYMBOL_BTCCNY, 1)

    #查询K线数据，测试通过
    data = api.getKline(SYMBOL_BTCCNY, PERIOD_1MIN, 100)


    print(data)

    # input()
    
    
if __name__ == '__main__':
    # testTrade()
    
    testData()
