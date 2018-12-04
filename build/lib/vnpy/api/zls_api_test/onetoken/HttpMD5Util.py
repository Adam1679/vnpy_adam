#!/usr/bin/python
# -*- coding: utf-8 -*-
# 用于进行http请求，以及MD5加密，生成签名的工具类

# import http.client

import time
import json
from urlparse import urlparse
import hmac
import hashlib
import requests

# 填入你的ot_key
ot_key = 'd4ypzCNm-FOXBKDQ4-zsGq3TMK-lLfFlaNm'
# 填入你的ot_secret
ot_secret = 'FEkYfn8Y-C8smdhjD-AIRwne7q-azONOH0A'

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
    # parsed_url = urllib.parse.urlparse(path)
    parsed_url = urlparse(path)
    parsed_path = parsed_url.path

    message = verb + parsed_path + str(nonce) + data_str
    signature = hmac.new(str(secret).encode("utf-8"), str(message).encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    # print('nonce:', nonce)
    # print('parsed_path:', parsed_path)
    # print('data_str:', data_str)
    # print('message:', message)
    return signature


def place_order():
    verb = 'POST'

    # 下单的api前缀如下，具体请查看1token API文档
    url = 'https://onetoken.trade/api/v1/trade'

    # path的具体构成方法请查看1token API文档
    path = '/huobip/zannb/orders'

    nonce = gen_nonce()
    data = {"contract": "huobip/btc.usdt", "price": 1, "bs": "b", "amount": 0.6}
    sig = gen_sign(ot_secret, verb, path, nonce, data)
    headers = gen_headers(nonce, ot_key, sig)
    # server并不要求请求中的data按key排序，只需所发送请求中的data与用来签名的data_str和相同即可，是否排序请按实际情况选择
    resp = requests.post(url + path, headers=headers, data=json.dumps(data, sort_keys=True))
    print(resp.json())


def get_info():
    verb = 'GET'
    url = 'https://onetoken.trade/api/v1/trade'
    path = '/huobip/zannb/info'
    nonce = gen_nonce()
    sig = gen_sign(ot_secret, verb, path, nonce)
    headers = gen_headers(nonce, ot_key, sig)
    resp = requests.get(url + path, headers=headers)
    print(resp.json())


def main():
    place_order()
    get_info()


if __name__ == '__main__':
    main()


