#!/usr/bin/env python
# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division


# from ctaBacktesting001 import BacktestingEngine, MINUTE_DB_NAME
from ctaBacktestingDollar import BacktestingEngine, MINUTE_DB_NAME
import itertools, copy
# from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME

HOUR_NAME = 'VnTrader_1Hour_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'

if __name__ == '__main__':
    # from strategyAtrRsi import AtrRsiStrategy
    # from strategyAtrRsi002 import AtrRsiStrategy
    # from strategyEA import AtrRsiStrategy
    # from strategyEALimit import AtrRsiStrategy
    from strategyDoubleMATest import DoubleMAStrategy
    # from strategyMACDLimit import AtrRsiStrategy

    db_name = MINUTE_DB_NAME
    # db_name = HOUR_NAME
    # symbol_name = 'OKFT_BTCUSD3M'
    symbol_name = 'BTC_USD_QUARTER'

    start_date = '20171129'  # 20141201
    # end_date = '20170611'
    mode = BacktestingEngine.BAR_MODE
    slippage = 0.0/100  # 滑点
    fee = 0.03/100      # 手续费
    contract_size = 1   # 合约大小
    price_tick = 0.01   # 最小价格变动

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(mode)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)
    # engine.setEndDate(end_date)

    # 设置产品相关参数
    engine.setSlippage(slippage)
    engine.setRate(fee)
    engine.setSize(contract_size)
    engine.setPriceTick(price_tick)

    # 设置使用的历史数据库
    engine.setDatabase(db_name, symbol_name)
    d = {'fastMaLength': 22, 'slowMaLength': 28}
    engine.initStrategy(DoubleMAStrategy, d)

    engine.show_KLine()





