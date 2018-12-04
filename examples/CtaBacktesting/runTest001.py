#!/usr/bin/env python
# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division

# from ctaBacktestingLimit import BacktestingEngine, MINUTE_DB_NAME, OptimizationSetting
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine
HOUR_NAME = 'VnTrader_1Hour_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'

if __name__ == '__main__':

    from cn_wtiStrategy import cn_wtiStrategy

    # db_name = MINUTE_DB_NAME
    db_name = "test"
    # symbol_name = 'OKFT_BTCUSD3M'
    symbol_name = 'dif_price'
    # symbol_name = 'LTC_USD_QUARTER'

    start_date = '20180401'
    end_date = '20181026'
    mode = BacktestingEngine.BAR_MODE
    slippage = 0.0/100  # 滑点
    fee = 0.03/100      # 手续费

    # contract_size = 1   # 合约大小
    price_tick = 0   # 最小价格变动
    # 设置引擎的收益率计算为非复利模式
    engine = BacktestingEngine()
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(mode)
    # 设置引擎的收益率计算为非复利模式
    # engine.setCompoundMode(False)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)
    engine.setEndDate(end_date)

    # 设置产品相关参数
    engine.setSlippage(slippage)
    engine.setRate(fee)
    # engine.setSize(contract_size)
    engine.setPriceTick(price_tick)

    # 设置使用的历史数据库
    engine.setDatabase(db_name, symbol_name)
    d = {'fast_period': 70,
         'slow_period': 64,
         'signal_period': 20,
         'slowMaLength': 27,
         'fastMaLength': 21,
         'contract_size': 100,
         'stop_profit': 1.08}

    engine.initStrategy(cn_wtiStrategy, d)

    engine.runBacktesting()
    engine.showBacktestingResult()





