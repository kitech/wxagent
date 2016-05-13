
import os, sys
import json, re
import enum, time
import requests
import random
import base64


class Nolib:
    burl = 'http://127.0.0.1:5003'
    interval = 30

    def __init__(self):
        self.results = {}
        self.last_fetch_time = -1
        return

    def getPage(self, pageno):
        if time.time() - self.last_fetch_time < self.interval: return

        url = self.burl + '/1.0/nolib.Qiubai/GetPage'
        data = {'Pageno': pageno, 'Result': ''}
        jdata = json.JSONEncoder().encode(data)
        try:
            r = requests.post(url, data=jdata)
        except Exception as ex:
            print(ex)
            return

        resp = json.JSONDecoder().decode(r.text)
        # print(resp)
        if resp['retcode'] == '0':
            res = json.JSONDecoder().decode(resp['Result'])
            for key in res.keys():
                self.results[key] = res[key]
            self.last_fetch_time = time.time()

        return

    def getOne(self):
        self.getPage(1)
        if len(self.results) > 0:
            return random.sample(list(self.results.values()), 1)[0]
        return None

    # @param data str | bytes
    def putFile(self, data):
        s = data.encode() if type(data) == str else data
        s64 = base64.b64encode(s).decode()
        data = {'Data': s64, 'Encoding': 'base64', 'Url': 'about: _blank_', 'Provider': 'any'}
        jdata = json.JSONEncoder().encode(data)

        url = self.burl + '/1.0/nolib.FileStore/PutFile'
        r = requests.post(url, data=jdata)
        resp = json.JSONDecoder().decode(r.text)

        return resp['Url']

    def unabbrev(self, word):
        data = {'Word': word, 'Explains': []}
        jdata = json.JSONEncoder().encode(data)

        url = self.burl + '/1.0/nolib.Abbrev/Unabbrev'
        r = requests.post(url, data=jdata)
        # print(r.status_code, r.headers, r.content, r.json())

        jres = r.json()
        if jres.get('errcode') is not None:
            return None
        return jres.get("Explains")

    def tlchat(self, info, uid):
        data = {'Info': info, 'Userid': uid, 'Loc': '', 'Result': ''}
        jdata = json.JSONEncoder(ensure_ascii=True).encode(data)

        url = self.burl + '/1.0/nolib.Tuling123/GetU'
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        res = requests.post(url, data=jdata, headers=headers)
        print(res.status_code, res.headers, res.content, res.json())

        jres = res.json()
        if jres.get('errcode') is not None:
            return None
        res2 = json.JSONDecoder().decode(jres.get("Result"))

        rcode = res2['code']
        if rcode == 100000:  # 文件
            text = res2['text']
        elif rcode == 200000:  # 链接
            text = res2['text'] + ' ' + res2['url']
        elif rcode == 302000:  # 新闻
            text = res2['text']
            text += ":\n"
            for item in res2['list']:
                text += item['article'] + ': ' + item['detailurl'] + "\n"
        elif rcode == 308000:  # 菜谱
            text = res2['text']
            text += ":\n"
            for item in res2['list']:
                text += item['name'] + ': ' + item['detailurl'] + "\n"
        else:
            text = res2['text']

        return text

    def bmadd(self, bmurl, utype):
        data = {'Id': 0, 'Url': bmurl, 'Type': utype, 'Tags': '', 'Result': ''}
        jdata = json.JSONEncoder().encode(data)

        url = self.burl + '/1.0/nolib.BookMark/BmInsert'
        r = requests.post(url, data=jdata)
        print(r.status_code, r.headers, r.content, r.json())

        jres = r.json()
        if jres.get('errcode') is not None:
            return None
        return jres.get('Result')

    def bmmod(self, bmurl, utype):
        return

    def bmdel(self, bmurl):
        return

    def bmget(self, keywords):
        return

    def tran(self, stype, words):
        data = {'Type': stype, 'Words': words, 'Result': ''}
        jdata = json.JSONEncoder().encode(data)

        url = self.burl + '/1.0/nolib.Fanyi/Translate'
        r = requests.post(url, data=jdata)
        # print(r.status_code, r.headers, r.content, r.json())

        jres = r.json()
        if jres.get('errcode') is not None:
            return None
        return jres.get('Result')

    def couplet(self, rightop):
        data = {'Shanglian': rightop, 'Result': ''}
        jdata = json.JSONEncoder().encode(data)

        url = self.burl + '/1.0/nolib.Couplet/GetCouplet'
        r = requests.post(url, data=jdata)
        print(r.status_code, r.headers, r.content, r.json())

        jres = r.json()
        if jres.get('errcode') is not None:
            return None
        return jres.get('Result')


if __name__ == '__main__':
    nol = Nolib()

    def test_qiubai():
        nol.getPage(1)
        print(time.time(), len(nol.results), nol.results)
        return

    def test_putfile():
        print(nol.putFile('不粉脍塔顶 赤绿 os 这'))
        return

    def test_abbrev():
        words = nol.unabbrev('brm')
        print(words)
        words = nol.unabbrev('aros')
        print(words)
        words = nol.unabbrev('arpa')
        print(words)
        return

    def test_tuling():
        import time
        info = '你好'
        uid = 'iaejfawefewfefaewfewf'
        reply = nol.tlchat(info, uid)
        print(reply)
        for info in ['今天星期几啊', '你叫什么', '谁起的名字', '多大了',
                     '维纳斯是谁', 'aol是什么意思', '这你都知道',
                     '你还知道些什么', '天为什么是蓝的']:
            reply = nol.tlchat(info, uid)
            print(info, reply)
            time.sleep(3)
        return

    def test_tuling2():
        info = '我想看新闻'
        uid = 'iaejfawefewfefaewfewf'
        reply = nol.tlchat(info, uid)
        print(reply)
        return

    def test_bms():
        url = 'http://www.abc.efg.com/' + str(time.time())
        utype = 'link'
        reply = nol.bmadd(url, utype)
        url += str(time.time())
        utype = 'rss'
        reply = nol.bmadd(url, utype)
        return

    def test_tran():
        stype = 'ytran'
        words = 'mock'
        reply = nol.tran(stype, words)
        print(words, "=>", reply)
        words = 'すみません'
        reply = nol.tran(stype, words)
        print(words, "=>", reply)
        words = '编辑'
        reply = nol.tran(stype, words)
        print(words, "=>", reply)
        return

    def test_couplet():
        words = "颠覆三观"
        reply = nol.couplet(words)
        print(words, "=>", reply)
        return

    # test_tran()
    # test_qiubai()
    # test_tuling2()
    # test_bms()
    test_couplet()


if __name__ == '__main__1':
    nol = Nolib()
    print(time.time(), len(nol.results))
    nol.getPage(1)
    print(time.time(), len(nol.results))
    nol.getPage(1)
    print(time.time(), len(nol.results))
    nol.getPage(1)
    print(time.time(), len(nol.results))

    for i in [1, 2, 3]:
        print('------', nol.getOne())
    pass
