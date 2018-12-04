# encoding: UTF-8
from vnpy.trader.app.ctaStrategy.WeixinMessage import WeixinMessage
from vnpy.trader.app.ctaStrategy.ctaEngine import CtaEngine
from vnpy.trader.vtEngine import MainEngine, LogEngine
from vnpy.event import EventEngine2
import sys
user_list = ['aaron','aaron']
weixin = WeixinMessage()

volume=100
msg_str='做多'
price=999.99

result = weixin.send('1ok', '001 double ma', 'BTC1', '%s%s张, $%s' % (msg_str, volume, price), user_list)
print(result)
