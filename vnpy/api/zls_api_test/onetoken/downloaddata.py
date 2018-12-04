# -*-encoding:utf8-*-

import pandas as pd
import json
import urllib
import requests
import dateutil
import datetime
import time

class DownloadData(object):
    def __init__(self):
        pass

    def read_data(self, file_path):
        data = pd.read_json(file_path, lines=True, compression='gzip', orient='records')
        return data

    def request_stream(self, url, file_path):
        data = requests.get(url, stream=True)
        with open(file_path, 'ab+') as f:
            for chunk in data.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        f.close()

    def get_contract(self, date):
        """   date的例子：'2018-01-02'   """
        url = 'http://alihz-net-0.qbtrade.org/contracts?date='+date
        print url
        data = requests.get(url, stream=True)
        contracts_str = ''
        for chunk in data.iter_content(chunk_size=1024):
            contracts_str += chunk
        contracts = (json.loads(contracts_str))
        return contracts




if __name__ == '__main__':
    pd.set_option('display.expand_frame_repr', False)
    # pd.set_option('max_colwidth', 1000)

    dd = DownloadData()
<<<<<<< HEAD:vnpy/api/zls_api_test/onetoken/downloaddata.py
    file_path = 'huobip_btc_usdt'

    # for i in range(20):
    #     i = str(i)
    #     if len(i) == 1:
    #         i = '0' + i
        # request_url = 'http://alihz-net-0.qbtrade.org/hist-ticks?date=2018-09-' + i + '&contract=okex/btc.usdt'
        # file_path = './'+request_url.split('=')[2].replace('/', '-') + '_' + request_url.split('=')[1].split('&')[0]+'.json.gz'

    request_url = 'https://onetoken.trade/api/v1/quote/candles?contract=huobip/btc.usdt&since=2018-07-01T00:00:00Z&until=2018-07-02T23:59:59Z&duration=1m'
    # 下载数据
    dd.request_stream(request_url, file_path)
=======
    file_path = 'okef_eth_usd_q.json.gz'
    UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    startDatetime = datetime.datetime(2018, 7, 15)
    while startDatetime < datetime.datetime(2018, 10, 15):
        start = datetime.datetime.strftime(startDatetime, UTC_FORMAT)
        end = datetime.datetime.strftime(startDatetime+datetime.timedelta(1), UTC_FORMAT)

        request_url = 'https://1token.trade/api/v1/quote/candles?contract=okef/eth.usd.q&since='+start+'&until='+end+'&duration=5m'
        # 下载数据
        dd.request_stream(request_url, file_path)

        print(start)
        startDatetime += datetime.timedelta(1)

        time.sleep(2)
>>>>>>> 4c6f0537e25f1029e78564ef3235d7c39171032f:vnpy/api/zls_api_test/1token/downloaddata.py

    # # 读取数据
    # data = dd.read_data(file_path)
    # data['time'] = pd.to_datetime(data['time'])+datetime.timedelta(hours=8)
    # data = data[data['time'] >= pd.datetime(2018, 9, 1, hour=0, minute=0)]

    # # 查询某天有数据的交易所的交易对
    # date = datetime.datetime(2017, 1, 1)
    # for i in range(580):
    #     str_date = date.strftime('%Y-%m-%d')
    #     data = dd.get_contract(str_date)
    #     date += datetime.timedelta(days=1)
    #     print data, '\n', len(data)
    #     time.sleep(1)

