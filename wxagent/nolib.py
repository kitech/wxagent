
import os, sys
import json, re
import enum, time
import requests
import random
import base64


class Nolib:
    burl = 'http://127.0.0.1:5002'
    interval = 30

    def __init__(self):
        self.results = {}
        self.last_fetch_time = -1
        return

    def getPage(self, pageno):
        if time.time() - self.last_fetch_time < self.interval: return

        url = self.burl + '/1.0/nolib.Qiubai/GetPage'
        data = {'Pageno': pageno, 'Pesult': ''}
        jdata = json.JSONEncoder().encode(data)

        r = requests.post(url, data=jdata)

        resp = json.JSONDecoder().decode(r.text)
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


if __name__ == '__main__':
    nol = Nolib()
    # print(nol.putFile('不粉脍塔顶 赤绿 os 这'))
    words = nol.unabbrev('brm')
    print(words)
    words = nol.unabbrev('aros')
    print(words)
    words = nol.unabbrev('arpa')
    print(words)


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
