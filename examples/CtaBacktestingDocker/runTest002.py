#!/usr/bin/env python
# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division

from ctaBacktestingDollar import BacktestingEngine, MINUTE_DB_NAME, OptimizationSetting

HOUR_NAME = 'VnTrader_1Hour_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'

if __name__ == '__main__':
    from strategy2MAMult import DoubleMAMultStrategy
    from strategyMACD import MACDStrategy
    from strategy5Day_zls import Day5Strategy

    # db_name = MINUTE_DB_NAME
    db_name = HOUR_NAME
    symbol_name = 'OKFT_BTCUSD3M'
    # symbol_name = 'BTC_USD_QUARTER'
    # symbol_name = 'LTC_USD_QUARTER'

    start_date = '20141229'  # 20141201-20171103, 20171129-20180406
    end_date = '20170426'  #
    mode = BacktestingEngine.BAR_MODE
    slippage = 0.0/100  # 滑点
    fee = 0.03/100      # 手续费
    contract_size = 1   # 合约大小
    price_tick = 0.01   # 最小价格变动

    engine = BacktestingEngine()
    engine.setBacktestingMode(mode)

    # 设置回测用的数据起始日期
    engine.setStartDate(start_date)
    engine.setEndDate(end_date)
    # 设置产品相关参数
    engine.setSlippage(slippage)
    engine.setRate(fee)
    engine.setSize(contract_size)
    engine.setPriceTick(price_tick)

    # 设置使用的历史数据库
    engine.setDatabase(db_name, symbol_name)
    optimize = OptimizationSetting()
    optimize.setOptimizeTarget('capital')

    # # MA
    # optimize.addParameter('fastMaLength', 23, 23, step=1)
    # optimize.addParameter('slowMaLength', 26, 26, step=1)
    # optimize.addParameter('contract_size', 100, 100, step=1)
    # optimize.addParameter('stop_profit', 0.05, 0.45, step=0.005)
    # engine.runParallelOptimization(DoubleMAMultStrategy, optimize)

    # MACD
    # optimize.addParameter('fast_period', 60, 75, step=1)
    # optimize.addParameter('slow_period', 65, 85, step=1)
    # optimize.addParameter('signal_period', 12, 20, step=1)
    # optimize.addParameter('contract_size', 100, 100, step=1)
    # optimize.addParameter('stop_profit', 1.08, 1.08, step=0.005)
    # engine.runParallelOptimization(MACDStrategy, optimize,
    #                                lambda setting: setting['fast_period'] < setting['slow_period'])

    # day5
    optimize.addParameter('fastMaLength', 2, 40, step=1)
    # optimize.addParameter('slowMaLength', 26, 26, step=1)
    optimize.addParameter('contract_size', 100, 100, step=1)
    optimize.addParameter('stop_profit', 1.03, 1.13, step=0.01)
    engine.runParallelOptimization(Day5Strategy, optimize)


    # fast_params = [20]
    # slow_params = [26,27]
    #     # # # 显示回测结果
    # BacktestingEngine.show_result_array_header()
    # for x in itertools.product(fast_params, slow_params):
    #     if x[0] >= x[1]:
    #         continue
    #     # 创建回测引擎
    #     engine = BacktestingEngine()
    #
    #     # 设置引擎的回测模式为K线
    #     engine.setBacktestingMode(mode)
    #
    #     # 设置回测用的数据起始日期
    #     engine.setStartDate(start_date)
    #
    #     # 设置产品相关参数
    #     engine.setSlippage(slippage)
    #     engine.setRate(fee)
    #     engine.setSize(contract_size)
    #     engine.setPriceTick(price_tick)
    #
    #     # 设置使用的历史数据库
    #     engine.setDatabase(db_name, symbol_name)
    #     d = {'fastMaLength': x[0], 'slowMaLength': x[1]}
    #     engine.initStrategy(AtrRsiStrategy, d)
    #     engine.runBacktesting()
    #     engine.show_result_array(*x)
        # engine.showBacktestingResult()

