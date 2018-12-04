# encoding:utf8
import time
import json
# import urllib.parse
import hmac
import hashlib
import requests
import urlparse
from vnpy.trader.vtEngine import LogEngine


class OneTokenRestful:
    # 单例对象
    logger = None

    def __init__(self, url, ot_key, ot_secret):
        self.__url = url
        self.__apikey = ot_key
        self.__secretkey = ot_secret


        if not self.logger:
            OneTokenRestful.logger = LogEngine()
            # OKCoinFuture.logger.setLogLevel(OKCoinFuture.logger.LEVEL_INFO)
            # OKCoinFuture.logger.addFileHandler()

    def gen_nonce():
        return str((int(time.time() * 1000000)))

    def gen_headers(nonce, key, sig):
        headers = {
            'Api-Nonce': nonce,
            'Api-Key': key,
            'Api-Signature': sig,
            'Content-Type': 'application/json'
        }
        return headers

    def gen_sign(secret, verb, path, nonce, data=None):
        if data is None:
            data_str = ''
        else:
            assert isinstance(data, dict)
            # server并不要求data_str按key排序，只需此处用来签名的data_str和所发送请求中的data相同即可，是否排序请按实际情况选择
            data_str = json.dumps(data, sort_keys=True)
        parsed_url = urlparse.urlparse(path)
        parsed_path = parsed_url.path

        message = verb + parsed_path + str(nonce) + data_str
        signature = hmac.new(bytes(secret).encode('utf-8'), bytes(message).encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        print('nonce:', nonce)
        print('parsed_path:', parsed_path)
        print('data_str:', data_str)
        print('message:', message)
        return signature

    def place_order():
        verb = 'POST'

        # 下单的api前缀如下，具体请查看1token API文档
        url = 'https://onetoken.trade/api/v1/trade'

        # path的具体构成方法请查看1token API文档
        path = '/huobip/mock-zlsapi/orders'

        nonce = gen_nonce()
        data = {"contract": "huobip/btc.usdt", "price": 1, "bs": "s", "amount": 500}
        sig = gen_sign(ot_secret, verb, path, nonce, data)
        headers = gen_headers(nonce, ot_key, sig)
        # server并不要求请求中的data按key排序，只需所发送请求中的data与用来签名的data_str和相同即可，是否排序请按实际情况选择
        resp = requests.post(url + path, headers=headers, data=json.dumps(data, sort_keys=True))
        print(resp.json())


    def get_info():
        verb = 'GET'
        url = 'https://onetoken.trade/api/v1/trade'
        path = '/huobip/mock-zlsapi/info'
        nonce = gen_nonce()
        sig = gen_sign(ot_secret, verb, path, nonce)
        headers = gen_headers(nonce, ot_key, sig)
        resp = requests.get(url + path, headers=headers)
        print(resp.json())


def main():
    place_order()
    get_info()


if __name__ == '__main__':
    url = 'https://onetoken.trade/api/v1/trade'
    # 填入ot_key
    ot_key = 'e7mACKKa-bPeBlcol-uS3XRB6F-H2PF1Win'
    # 填入ot_secret
    ot_secret = 'QhtFpIZO-pXpadgo9-AAX4UMZz-9i1oXMFh'
    onetoken = OneTokenRestful(url, ot_key, ot_secret)
    onetoken.main()