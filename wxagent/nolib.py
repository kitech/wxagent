import os, sys
import json, re
import enum, time
import requests
import random


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


if __name__ == '__main__':
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
