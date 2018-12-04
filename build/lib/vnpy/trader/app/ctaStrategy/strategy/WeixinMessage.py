# encoding: UTF-8

import requests
from restclient import GET, POST
import json
import threading
import time


class WeixinMessage(object):
    expires_time = 0
    access_token = None

    def __init__(self):
        self.allusers = {'aaron': 'o5iF2091TiNQfN8ay9fnrh7Sph-4',
                         'caodong': 'o5iF205DG3XmCwg35EcsPcsWIIE4',
                         'mading': 'o5iF201sKFZqSBVhVTI2MSSbFI7Q',
                         'zls': 'o5iF208bxdRKegjdaQBDO99zdLfU',
                         'Maohen': 'o5iF202mupZoENDsAOH7EkQRSVlw'}
        # self.allusers = {'zls': 'o5iF208bxdRKegjdaQBDO99zdLfU'}

        self.APPID = "wxe10cd37e052f3539"
        self.APPSECRET = "0556260b2d4b4705e7f20f7a092d3c84"

    def usersto(self, users = None):
        if users == None:
            # return self.allusers['aaron']
            return self.allusers['zls']

        elif users == "All":
            return ','.join(set(self.allusers.values()))
        else:
            if isinstance(users,list):
                usersinfo = []
                for user in users:
                    usersinfo.append(self.allusers[user])
                # return ','.join(set(usersinfo))
                return usersinfo
            else:
                print("'users' must be a list!")
                return

    # def json_post_data_generator(self, content='Hi!你好！',users = None):
    #     msg_content = {}
    #     msg_content['content'] = content
    #     post_data = {}
    #     post_data['text'] = msg_content
    #     post_data['touser'] = "%s" % self.usersto(users)
    #     # post_data['touser'] = self.usersto(users)
    #     post_data['toparty'] = ''
    #     post_data['msgtype'] = 'text'
    #     post_data['agentid'] = '9'
    #     post_data['safe'] = '0'
    #     #由于字典格式不能被识别，需要转换成json然后在作post请求
    #     #注：如果要发送的消息内容有中文的话，第三个参数一定要设为False
    #     return json.dumps(post_data,False,False)

    def strategy_notification(self, touser=None, gateway='交易所', name='测试名称', contract='测试合约', detail='无内容'):
        msg_content = {}
        msg_content['gateway_name'] = {'value': gateway, 'color': '#173177'}
        msg_content['name'] = {'value': name, 'color': '#173177'}
        msg_content['contract'] = {'value': contract, 'color': '#173177'}
        msg_content['detail'] = {'value': detail, 'color': '#173177'}
        post_data = {}
        post_data['data'] = msg_content
        post_data['touser'] = touser
        post_data['template_id'] = 'ZModF76ywtLyYMKJxh4sy494blZ1ZFfM_305XBhoKDs'

        # return json.dumps(post_data, False, False)
        return post_data

    def get_token_info(self):
        r = GET("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s" % (self.APPID, self.APPSECRET))
        js = json.loads(r)
        if "errcode" not in js:
            access_token = js["access_token"]
            expires_in = js["expires_in"]
        else:
            print("Can not get the access_token")
            print(js)
            return '', None
        return access_token, expires_in

    def send(self, gateway='gateway', name='测试名称', contract='测试合约', detail='无内容', users=None):
        if self.__class__.expires_time < time.time():
            access_token, expires_in = self.get_token_info()
            self.__class__.expires_time = time.time() + expires_in - 200
            self.__class__.access_token = access_token
        post_url_freshing = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=%s' % self.__class__.access_token

        usersinfo = []
        if users is None:
            usersinfo.append(self.allusers['aaron'])
        # elif users == "All":
        #     return ','.join(set(self.allusers.values()))
        else:
            if isinstance(users, list):
                for user in users:
                    usersinfo.append(self.allusers[user])

        for user in usersinfo:
            post_data = self.strategy_notification(touser=user, gateway=gateway, name=name, contract=contract,
                                                   detail=detail)
            # print(post_data)
            result = POST(post_url_freshing, params=post_data, async=False,
                          headers={'Content-Type': 'application/json', 'charset': 'utf-8'})
            # print(result)
            # result = r.json()



    # 原油交易策略的发送信息
    def send2(self, gateway='None', name='None', contract='None', detail='无内容', users=None):
        if self.__class__.expires_time < time.time():
            access_token, expires_in = self.get_token_info()
            self.__class__.expires_time = time.time() + expires_in - 200
            self.__class__.access_token = access_token
        post_url_freshing = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=%s' % self.__class__.access_token
        usersinfo = []
        if users is None:
            usersinfo.append(self.allusers['zls'])
        # elif users == "All":
        #     return ','.join(set(self.allusers.values()))
        else:
            if isinstance(users, list):
                for user in users:
                    usersinfo.append(self.allusers[user])

        for user in usersinfo:
            post_data = self.strategy_notification(touser=user, gateway=gateway, name=name, contract=contract,
                                                   detail=detail)
            # print(post_data)
            result = POST(post_url_freshing, params=post_data, async=False,
                          headers={'Content-Type': 'application/json', 'charset': 'utf-8'})

if __name__ == '__main__':
    user_list=['zls']
    user_list2 = ['aaron', 'caodong', 'mading', 'zls', 'Maohen']
    weixin = WeixinMessage()
    # msg = '帐号：public\n密码：V6!@U$Me'
    # weixin.send2(gateway='ctp&ib', name='原油价差套利', contract='上海油&美油', detail=msg, users=user_list)
    msg = '当前价差：9.73616156541  下线：9.92470778416'
    weixin.send2(gateway='ctp&ib', name='原油价差套利', contract='做多上海油&做空美油', detail=msg, users=user_list2)