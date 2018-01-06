#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author:yuc
# @Date:2018-01-02
# python 2.7.15

import sys
import re,os,json,time
import hashlib,random,base64,binascii,requests
#import crypto
from cookielib import MozillaCookieJar
from bs4 import BeautifulSoup

try:
    from Crypto.Cipher import AES
except:
    sys.modules["Crypto"] = crypto
    from Crypto.Cipher import AES

from netease_api_list import *
from logger_init import init_logging

import traceback

reload(sys)
sys.setdefaultencoding("utf8")

log = init_logging(os.path.basename(__file__))
"""
网易云音乐 加密api相关
收集于git

"""
class NetEaseEncrypt():
    def __init__(self):
        self.modulus = (u"00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7"
                       "b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280"
                       "104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932"
                       "575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b"
                       "3ece0462db0a22b8e7")
        self.nonce = u"0CoJUm6Qyw8W8jud"
        self.pubKey = u"010001"

    #歌曲加密算法
    #基于https://github.com/yanunon/NeteaseCloudMusic脚本实现
    def encrypt_id(self,id):
        magic = bytearray("3go8&$8*3*3h0k(2)2", "u8")
        song_id = bytearray(id, "u8")
        magic_len = len(magic)
        for i, sid in enumerate(song_id):
            song_id[i] = sid ^ magic[i % magic_len]
        m = hashlib.md5(song_id)
        result = m.digest()
        result = base64.b64encode(result)
        result = result.replace(b"/", b"_")
        result = result.replace(b"+", b"-")
        return result.decode("utf-8")

    #登录加密算法
    #基于https://github.com/stkevintan/nw_musicbox脚本实现
    def encrypt_request(self,text):
        text = json.dumps(text)
        #log.debug(text)
        secKey = self.create_secret_key(16)
        encText = self.aes_encrypt(self.aes_encrypt(text, self.nonce), secKey)
        encSecKey = self.rsa_encrypt(secKey, self.pubKey, self.modulus)
        data = {u"params": encText.encode("utf-8"), u"encSecKey": encSecKey.encode("utf-8")}
        return data

    def aes_encrypt(self,text, secKey):
        pad = 16 - len(text) % 16
        text = text + chr(pad) * pad
        encryptor = AES.new(secKey, 2, "0102030405060708")
        ciphertext = encryptor.encrypt(text)
        ciphertext = base64.b64encode(ciphertext).decode("utf-8")
        return ciphertext


    def rsa_encrypt(self,text,pubKey,modulus):
        text = text[::-1]
        rs = pow(int(binascii.hexlify(text), 16), int(pubKey, 16)) % int(modulus, 16)
        return format(rs, "x").zfill(256)

    def create_secret_key(self,size):
        return binascii.hexlify(os.urandom(size))[:16]




class NetEaseSongInfo():
    def __init__(self):
        self.m_encrypt = NetEaseEncrypt()
        self.str_cookie_path = "file_cookie.txt"
        self.default_timeout = 200
        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "music.163.com",
            "Referer": "http://music.163.com/search/",
            "User-Agent":
            #"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36" 
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.cookies = MozillaCookieJar(self.str_cookie_path)
        try:
            self.session.cookies.load()
            cookie = ""
            if os.path.isfile(self.str_cookie_path):
                file_handle = open(self.str_cookie_path, "r")
                cookie = file_handle.read()
                file_handle.close()
            expire_time = re.compile(r"\d{4}-\d{2}-\d{2}").findall(cookie)
            print "expire_time",expire_time
            if expire_time:
                if expire_time[0] < time.strftime("%Y-%m-%d", time.localtime(time.time())):
                    print cookie
                    os.remove(self.str_cookie_path)
        except IOError as e:
            print str(e)
            self.session.cookies.save()

    def http_request(self,
                    method,
                    action,
                    query=None,
                    urlencoded=None,
                    callback=None,
                    timeout=None):
        try:
            if method == "GET":
                url = action if query is None else action + "?" + query
                connection = self.session.get(url,
                                            headers=self.header,
                                            timeout=self.default_timeout)

            elif method == "POST":
                connection = self.session.post(action,
                                            data=query,
                                            headers=self.header,
                                            timeout=self.default_timeout)

            elif method == "Login_POST":
                connection = self.session.post(action,
                                            data=query,
                                            headers=self.header,
                                            timeout=self.default_timeout)
                self.session.cookies.save()
            connection.encoding = "UTF-8"
            strbuf = connection.text
            json_result = json.loads(strbuf)
            return json_result
        except  requests.exceptions.RequestException as e:
            #print traceback.print_exc()
            log.error(str(e))
            return False

    # 登录
    def login(self, username, password):
        pattern = re.compile(r"^0\d{2,3}\d{7,8}$|^1[34578]\d{9}$")
        if pattern.match(username):
            return self.phone_login(username, password)
        action = MUSIC_METEASE_API_LOGIN
        text = {
            "username": username,
            "password": hashlib.md5(password.encode()).hexdigest(),
            "rememberLogin": "true"
        }
        data = self.m_encrypt.encrypt_request(text)
        print data
        try:
            return self.http_request("Login_POST", action, data)
        except Exception as e:
            log.error(e)
            return {"code": 501}

    # 手机登录
    def phone_login(self, username, password):
        action = MUSIC_METEASE_API_LOGIN_PHONE
        text = {
            "phone": username,
            "password": hashlib.md5(password.encode()).hexdigest(),
            "rememberLogin": "true"
        }
        data = self.m_encrypt.encrypt_request(text)
        try:
            return self.http_request("Login_POST", action, data)
        except Exception as e:
            log.error(e)
            return {"code": 501}

    # 每日签到
    # type 为 0即签到
    def daily_signin(self, type):
        action = MUSIC_METEASE_API_SIGN
        text = {"type": type}
        data = self.m_encrypt.encrypt_request(text)
        try:
            return self.http_request("POST", action, data)
        except Exception as e:
            log.error(e)
            return -1

    #获取歌曲下载链接
    def song_detail_link_api_api(self, music_ids, bit_rate=320000): 
        try:
            action = MUSIC_NETEASE_API_SONG_DETAIL_LINK
            self.session.cookies.load()
            csrf = u""
            for cookie in self.session.cookies:
                if cookie.name == "__csrf":
                    csrf = cookie.value
            if csrf == u"":
                log.warning("login null")
            action += csrf
            data = {"ids": music_ids, "br": bit_rate, "csrf_token": csrf}
            json_result = self.http_request("POST",
                                            action,
                                            query=self.m_encrypt.encrypt_request(data),
                                            )
            return json_result["data"]
        except Exception as e:
            log.error(e)
            return []
    
    #获取歌曲详情
    def song_detail(self, music_ids):
        action = MUSIC_NETEASE_API_SONG_DETAIL + "{}".format(music_ids)
        try:
            data = self.http_request("GET", action)
            if data == False:
                log.warning("http_request error.")
                return []
            return data["songs"]
        except Exception as e:
            print traceback.print_exc()
            log.error(e)
            return []

    # 用户歌单列表
    def user_playlist(self, uid, offset=0, limit=100):
        action = MUSIC_NETEASE_API_USER_PLAYLIST+'offset={}&limit={}&uid={}'.format(offset, limit, uid)
        try:
            data = self.http_request('GET', action)
            return data['playlist']
        except Exception as e:
            log.error(e)
            return -1

    # 每日推荐歌单
    #"playlist":歌单列表(list)
    #    "name":歌单名称
    #    "creator":创建者信息
    def user_recommend_playlist(self):
        try:
            action = MUSIC_NETEASE_API_USER_RECOMMEND_PLAYLIST
            self.session.cookies.load()
            csrf = ''
            for cookie in self.session.cookies:
                if cookie.name == '__csrf':
                    csrf = cookie.value
            if csrf == '':
                return False
            action += csrf
            req = {'offset': 0, 'total': True, 'limit': 20, 'csrf_token': csrf}
            page = self.http_request('POST', action,query=self.m_encrypt.encrypt_request(req))
            results = json.loads(page.text)['recommend']
            song_ids = []
            for result in results:
                song_ids.append(result['id'])
            data = map(self.song_detail, song_ids)
            return [d[0] for d in data]
        except Exception as e:
            log.error(e)
            return False

    # 私人FM
    #"data" :歌曲信息(list)
    #   'id': 歌曲ID
    def personal_fm(self):
        try:
            action = MUSIC_NETEASE_API_FM
            self.session.cookies.load()
            data = self.http_request('GET', action)
            return data['data']
        except Exception as e:
            log.error(e)
            return -1


if __name__ == "__main__":
    ne = NetEaseSongInfo()
    #print ne.song_detail([461347998])[0]["bMusic"]
    #listfm = ne.personal_fm()
    #for i in listfm:
    #    print i
    #   print "*"
    #print lo#31080099
    #aa = ne.user_playlist(40109419)
    aa = ne.personal_fm()
    for i in aa:
        print i["id"]
     