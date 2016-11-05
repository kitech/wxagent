import asyncio
import quamash
import json
import re
import requests
import pyquery

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController, Chatroom
from .wxcommon import *


class CmdController(BaseController):
    def __init__(self, rtab, parent=None):
        super(CmdController, self).__init__(rtab, parent)
        self.ufc = 0
        self.msgos = {}
        self.fetchers = {}
        self.trunner = quamash.QThreadExecutor()
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(str(msgo).encode())

        if msgo.get('context') is None or \
           msgo.get('context').get('content') is None:
            return

        urls = self.extract_urls(msgo['context']['content'])
        qDebug(str(urls))

        self.ufc = self.ufc + 1
        self.msgos[self.ufc] = msgo
        fetcher = UrlFetcher(self.ufc, urls)
        self.fetchers[self.ufc] = fetcher
        loop = asyncio.get_event_loop()
        r = loop.run_in_executor(self.trunner, fetcher.run)
        r.add_done_callback(self.onUrlFetched)
        qDebug('running???')
        return

    def replyGroupMessage(self, msgo):
        return

    def onUrlFetched(self, future):
        seq = future.result()
        fetcher = self.fetchers[seq]
        qDebug(str(fetcher))

        msgo = self.msgos[seq]
        msgo['op'] = 'showtitle'
        msgo['context']['src'] = msgo['src']
        for url in fetcher.resps:
            resp = fetcher.resps[url]
            if resp is None:
                msgo['context']['content'] = '^ Error title'
            else:
                codecs = ['UTF-8', 'GB18030', 'ISO-8859-1']
                for codec in codecs:
                    try:
                        d = pyquery.PyQuery(resp.content.decode(codec))
                        title = d('title').text()
                        qDebug('{} - {}'.format(codec, title).encode())
                        msgo['context']['content'] = title
                        break
                    except:
                        continue
            us = self.extract_urls(msgo['context']['content'])
            if len(us) > 0:
                for u in us:
                    msgo['context']['content'] = msgo['context']['content'].replace(u, 'DDD')
            qDebug(str(msgo).encode())
            self.rtab.SendMessageX(msgo)

        self.fetchers.pop(seq)
        self.msgos.pop(seq)
        return

    def extract_urls(self, text):
        exp = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(exp, text)
        # print(urls)
        return urls


class UrlFetcher():

    def __init__(self, seq, urls):
        self.seq = seq
        self.urls = urls
        self.resps = {}
        return

    # @asyncio.coroutine
    def run(self):
        from requests.packages.urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter
        headers = {'User-Agent': 'yobot/1.0'}
        retries = Retry.from_int(0)
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=retries))
        s.mount('https://', HTTPAdapter(max_retries=retries))
        qDebug(str(self.urls).encode())
        for url in self.urls:
            try:
                resp = s.get(url, headers=headers, timeout=1.2)
                qDebug('{}, {}'.format(resp.status_code, resp.encoding).encode())
                self.resps[url] = resp
            except Exception as ex:
                qDebug(str(ex).encode())
                self.resps[url] = None
        return self.seq
