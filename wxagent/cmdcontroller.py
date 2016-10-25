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
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(str(msgo).encode())

        if msgo.get('context') is None or \
           msgo.get('context').get('content') is None:
            return

        urls = self.extract_urls(msgo['context']['content'])
        for url in urls:
            print(url)
            self.ufc += 1
            self.msgos[self.ufc] = msgo
            self.fetchers[self.ufc] = UrlFetcher(self.ufc, url)
            self.fetchers[self.ufc].fetched.connect(self.onUrlFetched, Qt.QueuedConnection)
            self.fetchers[self.ufc].start()
        return

    def replyGroupMessage(self, msgo):
        return

    def onUrlFetched(self, seq):
        fetcher = self.fetchers[seq]
        qDebug(str(fetcher))

        d = pyquery.PyQuery(fetcher.resp.content.decode())
        title = d('title').text()
        qDebug(title.encode())

        msgo = self.msgos[seq]
        msgo['op'] = 'showtitle'
        msgo['context']['content'] = title
        msgo['context']['src'] = msgo['src']
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


class UrlFetcher(QThread):
    fetched = pyqtSignal(int)

    def __init__(self, seq, url):
        super(UrlFetcher, self).__init__()
        self.seq = seq
        self.url = url
        self.resp = None
        return

    def run(self):
        headers = {'User-Agent': 'yobot/1.0'}
        self.resp = requests.get(self.url, headers=headers)
        # self.resp = requests.get(self.url)
        resp = self.resp
        print(resp.status_code, resp.encoding)
        self.fetched.emit(self.seq)
        return

