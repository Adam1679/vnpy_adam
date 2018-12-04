# encoding: utf-8
# v20-RESTApi网址：http://developer.oanda.com/rest-live-v20/introduction/

from vnoanda import OandaApiV3

    
if __name__ == '__main__':
    token = '343988942537a1c63f34c9080f1e092b-777783dfc0e16311438991381f420300'
    accountId = '101-011-8526730-001'
    
    api = OandaApiV3()
    # api.DEBUG = False 默认False
    
    api.init('practice', token, accountId)

    # api.sendOrder({'order': {
    #     'units': -1000,  # 传参是美油units数量,待优化
    #     'instrument': 'USD_CNH',
    #     'timeInForce': 'FOK',
    #     'type': 'MARKET',
    #     'positionFill': 'DEFAULT'
    # }})

    # 获取交易合约列表，通过
    # api.getInstruments({'accountId': accountId})


    # 获取价格，通过
    a = api.getPrices({'instruments': 'USD_CNH'})
    # a = api.getPrices({'instruments': 'BCO_USD'})
    # a = api.getPrices({'instruments': 'WTICO_USD'})
    print '+'*30,'a','+'*30,'\n',a
    
    # 获取历史数据，失败
    # api.getPriceHisory({'instrument': 'WTICO_USD',
    #                     'granularity': 'D',
    #                     'candleFormat': 'midpoint',
    #                     'count': '50'})
    
    # 查询用户的所有账户，通过
    # api.getAccounts()

    # 查询账户信息，通过
    # api.getAccountInfo()
    
    # 查询委托数据，通过
    # api.getOrders({'instruments': 'WTICO_USD'})

    # ----------------------------------------------------------------------
    # 发送委托，通过
    # api.sendOrder({'order': {
    #                'units': "33",
    #                'instrument': 'WTICO_USD',
    #                'timeInForce': 'FOK',
    #                'type': 'MARKET',
    #                'positionFill': 'DEFAULT'
    #                }})

    # 查询委托数据，通过
    # api.getOrderInfo('8')
    
    # 修改委托，通过
    # api.modifyOrder({'units': '10000',
    #                'side': 'buy',
    #                'type': 'market'}, '123')
    
    # 撤销委托，通过
    #api.cancelOrder('123')
    
    # 查询所有持仓，通过
    # a = api.getTrades({'instrument': 'WTICO_USD'})
    # b = api.getTrades({'instrument': 'BCO_USD'})
    # print a,b
    # api.getTrades({'instrument': 'USD_CNH'})


    # 查询持仓数据，通过
    # api.getTradeInfo('8')
    
    # 修改持仓，通过
    #api.modifyTrade({'trailingStop': '150'}, '10125150909')    
    
    # 平仓，通过(50是需要平的单位数，30是说明单编号即：tradeID)
    # body = {
    #     "units": "50"
    # }
    # api.closeTrade(params= body,optional='30/close')
    
    # 查询汇总持仓，通过-----------若根据仓位判断策略可以用这一个
    # api.getPositions()
    
    # 查询汇总持仓细节，通过
    #api.getPositionInfo('EUR_USD')
    
    # 平仓汇总持仓，通过
    #api.closePosition('EUR_USD')
    
    # 查询账户资金变动，通过
    #api.getTransactions({})
    
    # 查询资金变动信息，通过
    #api.getTransactionInfo('10135713982')
    
    # 查询账户变动历史，部分通过，某些情况下可能触发JSONDecodeError
    #api.getAccountHistory()
    
    # 查询财经日历，通过
    #api.getCalendar({'period': '604800'})
    
    # 查询历史持仓比，通过
    #api.getPositionRatios({'instrument': 'EUR_USD',
                           #'period': '604800'})
    
    # 查询历史价差，通过
    #api.getSpreads({'instrument': 'EUR_USD',
                    #'period': '604800'})
    
    # 查询交易商持仓，通过
    #api.getCommitments({'instrument': 'EUR_USD'})
    
    # 查询订单簿，通过
    #api.getOrderbook({'instrument': 'EUR_USD',
                      #'period': '604800'})
    
    # 查询Autochartist，失败，OANDA服务器报错
    #api.getAutochartist({'instrument': 'EUR_USD'})
    
    # 阻塞
    input()
