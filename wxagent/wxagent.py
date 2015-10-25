# web weixin agent

import os, sys
import json, re
import time

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

from .wxcommon import *
from .wxsession import *
from .wxprotocol import *

# from dbus.mainloop.pyqt5 import DBusQtMainLoop
# DBusQtMainLoop(set_as_default = True)


######
class WXAgent(QObject):
    qrpicGotten = pyqtSignal('QByteArray')
    asyncRequestDone = pyqtSignal(int, 'QByteArray')

    def __init__(self, asvc, parent=None):
        super(WXAgent, self).__init__(parent)

        self.asvc = asvc

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.onReply, Qt.QueuedConnection)

        self.wxses = None

        self.logined = False
        self.qruuid = ''
        self.devid = 'e669767113868187'
        self.qrpic = b''   # QByteArray
        self.userAvatar = b''  # QByteArray
        self.rediect_url = ''
        self.cookies = []  # [QNetworkCookie]
        self.wxPassTicket = ''
        self.wxDataTicket = ''
        self.wxinitRawData = b''  # QByteArray
        self.wxinitData = None   # json decoded
        self.wxFriendRawData = b''  # QByteArray
        self.wxFriendData = None  #
        self.wxWebSyncRawData = b''  # QByteArray
        self.wxWebSyncData = None  # 
        self.wxSyncKey = None  # {[]}
        self.syncTimer = None  # QTimer
        self.clientMsgIdBase = qrand()

        self.wxproto = WXProtocol()
        self.wxGroupUserNames = {}  # 来自websync:AddMsgList:StatusNotifyUserName，以@@开头的

        self.asyncQueueIdBase = qrand()
        self.asyncQueue = {} # {reply => id}
        self.refresh_count = 0
        self.urlStart = ''
        self.webpushUrlStart = ''
        self.msgimage= b''   # QByteArray
        self.msgimagename = ''  #str 

        self.retry_times_before_refresh = 0

        return

    def refresh(self):
        oldname = self.nam
        oldname.finished.disconnect()
        self.nam = None

        qDebug('see this...')

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.onReply, Qt.QueuedConnection)

        self.logined = False
        self.qruuid = ''
        self.devid = 'e669767113868187'
        self.qrpic = b''   # QByteArray
        self.userAvatar = b''  # QByteArray
        self.rediect_url = ''
        self.cookies = []  # [QNetworkCookie]
        self.wxPassTicket = ''
        self.wxDataTicket = ''
        self.wxinitRawData = b''  # QByteArray
        self.wxinitData = None   # json decoded
        self.wxFriendRawData = b''  # QByteArray
        self.wxFriendData = None  #
        self.wxWebSyncRawData = b''  # QByteArray
        self.wxWebSyncData = None  #
        self.wxSyncKey = None  # {[]}
        self.syncTimer = None  # QTimer

        self.asyncQueueIdBase = qrand()
        self.asyncQueue = {}  # {reply => id}

        self.retry_times_before_refresh = 0

        self.doboot()
        self.refresh_count += 1
        return

    def doboot(self):

        self.emitDBusBeginLogin()

        url = "https://login.weixin.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx2.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=en_US"
        req = QNetworkRequest(QUrl(url))
        req = self.mkreq(url)
        req.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')

        qDebug('requesting: ' + url)
        reply = self.nam.get(req)
        reply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def onReply(self, reply):
        self.dumpReply(reply)

        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        error_no = reply.error()

        url = reply.url().toString()
        hcc = reply.readAll()
        qDebug('content-length:' + str(len(hcc)) + ',' + str(status_code) + ',' + str(error_no))

        # TODO 考虑添加个retry_times_before_refresh
        if status_code is None and error_no in [99, 8]:
            qDebug('maybe temporary network offline.' + str(error_no))
            # QTimer.singleShot(123, self.webSync)
            # QTimer.singleShot(123, self.refresh)
            # return

        # statemachine by url and response content
        if url.startswith('https://login.weixin.qq.com/jslogin?'):
            qDebug("qr login code/uuic:" + str(hcc))

            if status_code is None and error_no == QNetworkReply.TimeoutError:
                qDebug('timeout:')
                self.doboot()
                return

            self.saveContent('jslogin.html', hcc, reply)

            # parse hcc: window.QRLogin.code = 200; window.QRLogin.uuid = "gYmgd1grLg==";
            qrcode = 200
            qruuid = ''
            qruuid = hcc.data().decode('utf8').split('"')[1]
            # qDebug(str(qruuid))
            self.qruuid = qruuid

            self.requestQRCode()
            # nsurl = 'https://login.weixin.qq.com/qrcode/4ZYgra8RHw=='
            # nsurl = 'https://login.weixin.qq.com/qrcode/%s' % qruuid
            # qDebug(str(nsurl))

            # nsreq = QNetworkRequest(QUrl(nsurl))
            # nsreq = self.mkreq(nsurl)
            # nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
            # nsreply = self.nam.get(nsreq)

        #####
        elif url.startswith('https://login.weixin.qq.com/qrcode/'):
            qDebug("qr pic:" + str(len(hcc)))

            if status_code is None and error_no == QNetworkReply.TimeoutError:
                qDebug('timeout:')
                self.requestQRCode()
                return

            self.qrpic = hcc
            self.qrpicGotten.emit(hcc)

            self.emitDBusGotQRCode()

            self.pollLogin()

        ######
        elif url.startswith('https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?'):
            qDebug("app scaned qrpic:" + str(hcc))

            # window.code=408;  # 像是超时
            # window.code=400;  # ??? 难道是会话过期???需要重新获取QR图（已确认，在浏览器中，收到400后刷新了https://wx2.qq.com/
            # window.code=201;  # 已扫描，未确认
            # window.code=200;  # 已扫描，已确认登陆
            # parse hcc, format: window.code=201;
            scan_code = hcc.data().decode('utf8').split('=')[1][0:3]

            if scan_code == '408': self.pollLogin()
            elif scan_code == '400':
                qDebug("maybe need rerun refresh()...")
                self.refresh()
            elif scan_code == '201':
                self.pollLogin()
                pass
            elif scan_code == '200':  # 扫描确认完成，登陆成功
                # emit logined
                self.logined = True
                self.emitDBusLogined()

                # parser redirect url:
                redir_url = hcc.data().decode('utf8').split('"')[1]
                self.redirect_url = redir_url

                nsurl = redir_url
                if nsurl.find('wx.qq.com') > 0:
                    self.urlStart = 'https://wx.qq.com'
                    self.webpushUrlStart = 'https://webpush.weixin.qq.com'
                else:
                    self.urlStart = 'https://wx2.qq.com'
                    self.webpushUrlStart = 'https://webpush2.weixin.qq.com'
                qDebug(nsurl)
                qDebug(self.urlStart)
                qDebug(self.webpushUrlStart)
                nsreq = QNetworkRequest(QUrl(nsurl))
                nsreq = self.mkreq(nsurl)
                nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
                nsreply = self.nam.get(nsreq)
                nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

                pass
            else: qDebug('not impled:' + scan_code)

        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxnewloginpage?'):
            qDebug('got wxuin and wxsid and other important cookie:')
            cookies = reply.header(QNetworkRequest.SetCookieHeader)
            qDebug(str(cookies))
            self.cookies = cookies
            self.wxuin = self.getCookie3('wxuin')
            self.wxsid = self.getCookie3('wxsid')
            self.wxDataTicket = self.getCookie3('webwx_data_ticket')
            qDebug(str(self.wxuin) + ', ' + str(self.wxsid) + ', ' + str(self.wxDataTicket))

            # parse content: SKey,pass_ticket
            # <error><ret>0</ret><message>OK</message><skey>@crypt_3ea2fe08_723d1e1bd7b4171657b58c6d2849b367</skey><wxsid>9qxNHGgi9VP4/Tx6</wxsid><wxuin>979270107</wxuin><pass_ticket>%2BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%2FZJJXurz79ARX%2FIT</pass_ticket><isgrayscale>1</isgrayscale></error>
            qDebug('parsing: ' + str(hcc))
            reg = r'<pass_ticket>(.+)</pass_ticket>'
            mats = re.findall(reg, hcc.data().decode('utf8'))
            qDebug(str(mats))
            # pass_ticket = mats[0][0]
            pass_ticket = mats[0]    ### 为什么又变成一维的了呢？
            self.wxPassTicket = pass_ticket
            qDebug(pass_ticket)

            self.getBaseInfo()

        #############
        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxinit?'):
            qDebug('wxinited.:' + str(type(hcc)))
            self.wxinitRawData = hcc
            self.saveContent("baseinfo.json", hcc, reply)

            # qDebug(str(hcc.data().decode('utf8')))  # why can not decode?
            # UnicodeEncodeError: 'ascii' codec can't encode characters in position 131-136: ordinal not in range(128)
            strhcc = self.hcc2str(hcc)

            if len(strhcc) > 0:
                jsobj = json.JSONDecoder().decode(strhcc)
                self.wxinitData = jsobj
                self.wxSyncKey = jsobj['SyncKey']

                retcode = jsobj['BaseResponse']['Ret']
                # retcode: 1205: ???
            else:
                qDebug('can not decode hcc base info')

            self.getContact()
            self.syncCheck()
            ########

        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxgetcontact?'):
            qDebug('get contact:' + str(len(hcc)))
            self.wxFriendRawData = hcc
            # parser contact data:

            self.emitDBusLoginSuccess()

            #########
        #elif url.startswith('https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?'):
        elif url.startswith(self.webpushUrlStart+'/cgi-bin/mmwebwx-bin/synccheck?'):
            qDebug('sync check result:' + str(hcc))

            if status_code is None and error_no in [99]:  # QNetworkReply.UnknownNetworkError
                if self.retry_times_before_refresh > 3:
                    qDebug('really need refresh')
                    self.retry_times_before_refresh = 0
                    QTimer.singleShot(456, self.refresh)
                else:
                    self.retry_times_before_refresh += 1
                    QTimer.singleShot(12340, self.syncCheck)
                return
            else:
                if self.retry_times_before_refresh > 0:
                    qDebug('retry before refresh useful, ' + str(self.retry_times_before_refresh))
                    self.retry_times_before_refresh = 0  # reset zero

            # window.synccheck={retcode:”0”,selector:”0”}
            # selector: 6: 表示有新消息
            # selector: 7: ??? 打开了某项，如群，好友，是一个事件
            # selector: 2: ??? 有新消息
            # selector: 4: ???
            # retcode: 1100:???
            # retcode: 1101:??? 会话已退出/结束
            # retcode: 1102: 用户在手机端主动退出
            # retcode: 1205: ???
            # retcode: 0: 成功

            # parser result:

            reg = r'window.synccheck={retcode:"(-?\d+)",selector:"(\d)"}'
            mats = re.findall(reg, hcc.data().decode('utf8'))
            qDebug(str(mats) + '---' + hcc.data().decode('utf8'))
            retcode = mats[0][0]
            selector = mats[0][1]

            if retcode == '-1':
                qDebug('wtf???...')
                QTimer.singleShot(3000, self.logout)
            elif retcode == '1100':
                qDebug("maybe need reget SyncKey, rerun getBaseInfo() ..." + str(retcode))
            elif retcode == '1101':
                qDebug("maybe need rerun refresh()..." + str(retcode))
                qDebug("\n\n\n\n\n\n\n")
                QTimer.singleShot(5000, self.refresh)
            elif retcode != '0':
                qDebug('error sync check ret code:')
            else:
                if selector == '0':
                    self.syncCheck()
                    pass
                elif selector == '2':
                    self.webSync()
                    pass
                elif selector == '4':  # TODO,confirm this，像是群成员列表有变化
                    self.webSync()
                    pass
                elif selector == '6':  # TODO,confirm this
                    self.webSync()
                    pass
                elif selector == '7':
                    self.webSync()
                    pass
                else: qDebug('Unknown selctor value:')

        ##############
        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxsync?'):
            qDebug('web sync result:' + str(len(hcc)) + str(status_code))

            # TODO check no reply case and rerun synccheck.
            if status_code == '' and l:
                qDebug('maybe need rerun synccheck')

            self.wxWebSyncRawData = hcc
            self.saveContent('websync.json', hcc, reply)
            self.emitDBusNewMessage(hcc)

            # parse web sync result:
            strhcc = self.hcc2str(hcc)

            if len(strhcc) > 0:
                jsobj = json.JSONDecoder().decode(strhcc)
                self.wxWebSyncData = jsobj
                self.wxSyncKey = jsobj['SyncKey']

                ### other process
                grnames = self.wxproto.parseWebSyncNotifyGroups(hcc)
                for grname in grnames: self.wxGroupUserNames[grname] = 1
                qDebug(str(grnames))

                ### => synccheck()
                if jsobj['BaseResponse']['Ret'] == 0: self.syncCheck()
                else: qDebug('web sync error:' + str(jsobj['BaseResponse']['Ret'])
                             + ',' + str(jsobj['BaseResponse']['ErrMsg']))
            else:
                qDebug('can not decode hcc base info')

            #######
        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxlogout?'):
            qDebug('logouted...')
            QTimer.singleShot(3, self.refresh)

            ########
        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxsendmsg?'):
            qDebug('sendmsg...')
            self.saveContent('sendmsg.json', hcc, reply)

            ########
        #elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?'):
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?'):
            qDebug('getbatchcontact done...')
            self.saveContent('getbatchcontact.json', hcc, reply)

            if reply in self.asyncQueue:
                reqno = self.asyncQueue.pop(reply)
                self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxgetmsgimg?'):
            if reply in self.asyncQueue:
                reqno = self.asyncQueue.pop(reply)
                self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith(self.urlStart+'/cgi-bin/mmwebwx-bin/webwxgetvoice?'):
            if reply in self.asyncQueue:
                reqno = self.asyncQueue.pop(reply)
                self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://emoji.qpic.cn/wx_emoji'):
            qDebug('get the picture url that you saved : ' + str(len(hcc)))
            self.msgimage = hcc
            self.createMsgImage(hcc)
        else:
            qDebug('unknown requrl:' + str(url))
            self.saveContent('wxunknown_requrl.json', hcc, reply)

        return

    def createMsgImage(self, hcc):
        randnum = str(int(time.time()))
        self.msgimagename = 'img/mgs_image' + randnum + '.json'
        fp = QFile(self.msgimagename)
        fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
        fp.write(hcc)
        fp.close()

    def onReplyError(self, errcode):
        qDebug('reply error:' + str(errcode))
        reply = self.sender()
        url = reply.url().toString()
        qDebug('url: ' + url)

        return

    def requestQRCode(self):
        nsurl = 'https://login.weixin.qq.com/qrcode/4ZYgra8RHw=='
        nsurl = 'https://login.weixin.qq.com/qrcode/%s' % self.qruuid
        qDebug(str(nsurl))

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def pollLogin(self):
        ###
        nsurl = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=4eDUw9zdPg==&tip=0&r=-1166218796'
        # v2 url: https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=gfNC8TeiPg==&tip=1&r=-1222670084&lang=en_US
        nsurl = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=1&r=%s&lang=en_US' % \
                (self.qruuid, self.nowTime())
        qDebug(nsurl)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def getBaseInfo(self):
        # TODO: pass_ticket参数
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=1377482058764'
        # v2 url:https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1222669677&lang=en_US&pass_ticket=%252BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%252FZJJXurz79ARX%252FIT
        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=en_US&pass_ticket=' % \
        #        (self.nowTime() - 3600 * 24 * 30)
        #nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=en_US&pass_ticket=' % \
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=en_US&pass_ticket=%s' % \
                (self.nowTime() - 3600 * 24 * 30, self.wxPassTicket)
        qDebug(nsurl)

        post_data = '{"BaseRequest":{"Uin":"%s","Sid":"%s","Skey":"","DeviceID":"%s"}}' % \
                    (self.wxuin, self.wxsid, self.devid)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        # nsreply = self.nam.get(nsreq)  # TODO POST
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def getContact(self):

        nsurl = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?r=1377482079876'
        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?r='
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxgetcontact?r='

        post_data = '{}'
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        # nsreply = self.nam.get(nsreq)  # TODO POST
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def syncCheck(self):
        ### make syncKey: format: 1_124125|2_452346345|3_65476547|1000_5643635
        syncKey = []
        for k in self.wxSyncKey['List']:
            elem = '%s_%s' % (k['Key'], k['Val'])
            syncKey.append(elem)

        # |需要URL编码成%7C
        syncKey = '%7C'.join(syncKey)   # [] => str''

        skey = self.wxinitData['SKey'].replace('@', '%40')
        self.skey = skey
        pass_ticket = self.wxPassTicket.replace('%', '%25')
        nsurl = 'https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18309326978388708085_1377482079946&r=1377482079876&sid=QfLp+Z+FePzvOFoG&uin=2545437902&deviceid=e1615250492&synckey=(见以下说明)&_=1377482079876'
        #nsurl = 'https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=&r=&skey=%s&sid=%s&uin=%s&deviceid=e1615250492&synckey=%s&_=' % \
        #        (skey, self.wxsid, self.wxuin, syncKey)
        nsurl = self.webpushUrlStart+'/cgi-bin/mmwebwx-bin/synccheck?callback=&r=&skey=%s&sid=%s&uin=%s&deviceid=e1615250492&synckey=%s&_=' % \
                (skey, self.wxsid, self.wxuin, syncKey)
        # v2 url:https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=1440036883783&skey=%40crypt_3ea2fe08_723d1e1bd7b4171657b58c6d2849b367&sid=9qxNHGgi9VP4%2FTx6&uin=979270107&deviceid=e669767113868147&synckey=1_638162182%7C2_638162328%7C3_638162098%7C11_638162315%7C201_1440036879%7C203_1440034958%7C1000_1440031958&lang=en_US&pass_ticket=%252BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%252FZJJXurz79ARX%252FIT
        nsurl = self.webpushUrlStart+'/cgi-bin/mmwebwx-bin/synccheck?r=%s&skey=%s&sid=%s&uin=%s&deviceid=%s&synckey=%s&lang=en_US&pass_ticket=%s' % \
                (self.nowTime(), skey, self.wxsid, self.wxuin, self.devid, syncKey, pass_ticket)


        qDebug(nsurl)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        joined_cookies = self.joinCookies()
        # nsreq.setHeader(QNetworkRequest.CookieHeader, QByteArray(joined_cookies.encode('utf8')))
        nsreq.setRawHeader(b'Cookie', joined_cookies.encode('utf8'))

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def webSync(self):
        syncKey = []
        for k in self.wxSyncKey['List']:
            elem = '%s_%s' % (k['Key'], k['Val'])
            syncKey.append(elem)

        # |需要URL编码成%7C
        syncKey = '%7C'.join(syncKey)   # [] => str''

        skey = self.wxinitData['SKey'].replace('@', '%40')

        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=9qxNHGgi9VP4/Tx6&skey=@crypt_3ea2fe08_723d1e1bd7b4171657b58c6d2849b367&lang=en_US&pass_ticket=%252BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%252FZJJXurz79ARX%252FIT'
        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' % \
                #(self.wxsid, skey, self.wxPassTicket)
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' % \
                (self.wxsid, skey, self.wxPassTicket)

        # {"BaseRequest":{"Uin":979270107,"Sid":"9qxNHGgi9VP4/Tx6","Skey":"@crypt_3ea2fe08_723d1e1bd7b4171657b58c6d2849b367","DeviceID":"e740613595349714"},"SyncKey":{"Count":7,"List":[{"Key":1,"Val":638162182},{"Key":2,"Val":638162328},{"Key":3,"Val":638162098},{"Key":11,"Val":638162315},{"Key":201,"Val":1440036879},{"Key":203,"Val":1440034958},{"Key":1000,"Val":1440031958}]},"rr":-1222840202}
        post_data = 'BaseRequest":{"Uin":%s,"Sid":"%s","Skey":"%s","DeviceID":"%s"},"SyncKey":%s,"rr":%s}'
        post_data_obj = {
            "BaseRequest": {
                "Uin": self.wxuin,
                "Sid": self.wxsid,
                "Skey": self.wxinitData['SKey'],
                "DeviceID": self.devid,
            },
            "SyncKey": self.wxSyncKey,
            "rr": self.nowTime(),
        }
        post_data = json.JSONEncoder().encode(post_data_obj)
        qDebug(str(post_data))
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return nsreply

    def logout(self):

        skey = self.wxinitData['SKey'].replace('@', '%40')

        # POST
        # https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?redirect=1&type=0&skey=%40crypt_3ea2fe08_3d6fd43e69bbeea4553311ee632760cc
        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?redirect=0&type=0&skey=%s' % \
        #        (skey)
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxlogout?redirect=0&type=0&skey=%s' % \
                (skey)

        post_data = 'sid=%s&uin=%s' % (self.wxsid, self.wxuin)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    # @param from_username str
    # @param to_username str
    # @param msg_type int
    # @param content str
    def sendmessage(self, from_username, to_username, content, msg_type=1):

        # url v1:
        # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?sid=QfLp+Z+FePzvOFoG&r=1377482079876
        # https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=en_US&pass_ticket=DJhcRApklCEqLxypM8VNWrEaWiVfk40Neuvl7VQQGDDRHit9EWDo6cWQyIqiKiP7
        # {"BaseRequest":{"Uin":979270107,"Sid":"oLSQVNxibkhFyvwS",
        # "Skey":"@crypt_3ea2fe08_509243cc2f67b21740bbd5c204aebdeb","DeviceID":"e869252818170935"},
        # "Msg":{"Type":1,"Content":"ccc",
        # "FromUserName":"@0f71eb337572192a18ccf8ee3622e535a5c2e641ddd9534ae6ecf431045da76c",
        # "ToUserName":"filehelper","LocalID":"14403062501420476","ClientMsgId":"14403062501420476"}}
        # 1440307117517
        # 1440307117517.2507 == QDateTime.toMSecsSinceEpoch().strcat(autoinc)
        # 14403062501420476 == QDateTime.toMSecsSinceEpoch().strcat(autoinc)

        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=en_US&pass_ticket=%s' % \
        #        (self.wxPassTicket)
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=en_US&pass_ticket=%s' % \
                (self.wxPassTicket)

        clientMsgId = self.nextClientMsgId()

        post_data_obj = {
            "BaseRequest": {
                "Uin": self.wxuin,
                "Sid": self.wxsid,
                "Skey": self.wxinitData['SKey'],
                "DeviceID": self.devid,
            },
            "Msg": {
                "Type": msg_type,
                "Content": content,
                "FromUserName": from_username,
                "ToUserName": to_username,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId,
            },
        }

        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    #
    def requrl(self, url, method='GET', data=''):
        nsurl = url

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return nsreply

    ####
    def geticon(self, username):
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?seq=&username=@3d9f8af0b17ab22745f776b94fe3530f'
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?seq=&username=wxid_xx3mtgeux5511'
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?seq=&username=kitech'
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxgeticon?seq=&username=coder_zj'

        return

    # @param members List json format in string
    def getbatchcontact(self, members):
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?type=ex&r=1440473919872&lang=en_US&pass_ticket=kKWVrvi2aw98Z8sXfzwncDWxWZZQgVZERel61bswt0bLI5z3Xo3Vz8l5UmrLWOXq'
        #nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?type=ex&r=%s&lang=en_US&pass_ticket=%s' % \
        #        (self.nowTime(), self.wxPassTicket)
        nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?type=ex&r=%s&lang=en_US&pass_ticket=%s' % \
                (self.nowTime(), self.wxPassTicket)



        members_list = json.JSONDecoder().decode(members)
        post_data_obj = {
            "BaseRequest": {
                "Uin": self.wxuin,
                "Sid": self.wxsid,
                "Skey": self.wxinitData['SKey'],
                "DeviceID": self.devid,
            },
            "Count": len(members_list),
            "List": members_list,
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8')[0:120])

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    def getMsgImg(self, msgid, thumb=True):

        skey = self.wxinitData['SKey'].replace('@', '%40')
        tyarg = 'type=slave&' if thumb is True else ''

        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg?type=slave&MsgID={MsgID值}&skey=%40{skey值}'
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg?%sMsgID=%s&skey=%s' % \
                (tyarg, msgid, skey)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    def getMsgImgUrl(self, msgid, thumb=True):
        skey = self.wxinitData['SKey'].replace('@', '%40')
        tyarg = 'type=slave&' if thumb is True else ''

        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg?%sMsgID=%s&skey=%s' % \
                (tyarg, msgid, skey)
        return nsurl

    def getMsgFileUrl(self, sender_name, media_id, file_name, from_uin):
        # sender_name = ''
        # media_id = ''
        # file_name = ''
        # from_uin = 0
        # file_name = urllib.parse.quote_plus(file_name)   # 对中文不太友好
        file_name = file_name.replace(' ', '+')  # 这种可能存在bug
        pass_ticket = self.wxPassTicket
        data_ticket = self.wxDataTicket
        nsurl = 'https://file2.wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetmedia?sender=%s&mediaid=%s&filename=%s&fromuser=%s&pass_ticket=%s&webwx_data_ticket=%s'  % \
                (sender_name, media_id, file_name, from_uin, pass_ticket, data_ticket)
        return nsurl

    def getMsgVoice(self, msgid):

        skey = self.wxinitData['SKey'].replace('@', '%40')

        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetvoice?msgid=%s&skey=%s' % \
                (msgid, skey)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    def nextClientMsgId(self):
        now = QDateTime.currentDateTime()
        self.clientMsgIdBase = self.clientMsgIdBase + 1
        clientMsgId = '%s%4d' % (now.toMSecsSinceEpoch(), self.clientMsgIdBase % 10000)
        return clientMsgId

    # @return str
    def getCookie(self, name):
        ckjar = self.nam.cookieJar()
        #domain = 'https://wx2.qq.com'
        domain = self.urlStart
        cookies = ckjar.cookiesForUrl(QUrl(domain))

        for cookie in cookies:
            tname = cookie.name().data().decode('utf8')
            val = cookie.value().data.decode('utf8')
            qDebug(tname + '=' + val)
            if tname == name:
                return val
        return

    def getCookie2(self, name):
        str_cookies = self.cookies.data().decode('utf8')
        for cline in str_cookies.split("\n"):
            for celem in cline.split(";"):
                kv = celem.strip().split('=')
                if (kv[0] == name): return kv[1]

        return

    def getCookie3(self, name):
        for c in self.cookies:
            tname = c.name().data().decode('utf8')
            tvalue = c.value().data().decode('utf8')
            if tname == name: return tvalue
        return

    def joinCookies(self):
        joined = ''
        for c in self.cookies:
            tname = c.name().data().decode('utf8')
            tvalue = c.value().data().decode('utf8')
            joined = joined + '%s=%s; ' % (tname, tvalue)

        return joined

    def nowTime(self):
        # return QDateTime.currentDateTime().toTime_t()
        import time
        return int(time.time())

    def mkreq(self, url):
        req = QNetworkRequest(QUrl(url))
        self.setUserAgent(req)
        self.setReferer(req)
        return req

    def setUserAgent(self, req):
        ua = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36'
        req.setRawHeader(b'User-Agent', ua)
        return

    def setReferer(self, req):
        req.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        return

    def dumpReply(self, reply):
        qDebug("\ngggggggg===========")
        qDebug(str(reply))
        req = reply.request()
        qDebug(str(req.url()).encode())
        stcode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        qDebug(str(stcode))
        cookies = reply.header(QNetworkRequest.SetCookieHeader)
        qDebug(str(cookies))

        hdrlst = reply.rawHeaderList()
        for hdr in hdrlst:
            hdrval = reply.rawHeader(hdr)
            qDebug(str(hdr) + '=' + str(hdrval))

        # hcc = reply.readAll()
        # qDebug(str(hcc))

        return

    # @param hcc QByteArray
    # @return str
    def hcc2str(self, hcc):
        strhcc = ''

        try:
            astr = hcc.data().decode('gkb')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode gbk error:')

        try:
            astr = hcc.data().decode('utf16')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf16 error:')

        try:
            astr = hcc.data().decode('utf8')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf8 error:')

        return strhcc

    # @param name str
    # @param hcc QByteArray
    # @return None
    def saveContent(self, name, hcc, reply):
        # fp = QFile("baseinfo.json")
        fp = QFile(name)
        fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
        # fp.resize(0)

        # write reply info
        reqinfo = b''
        req = reply.request()
        # qDebug(str(req.url()))
        reqinfo += req.url().toString().encode() + b"\n"
        stcode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        # qDebug(str(stcode))
        reqinfo += b'status code:' + str(stcode).encode() + b"\n"
        cookies = reply.header(QNetworkRequest.SetCookieHeader)
        # qDebug(str(cookies))

        hdrlst = reply.rawHeaderList()
        for hdr in hdrlst:
            hdrval = reply.rawHeader(hdr)
            # qDebug(str(hdr) + '=' + str(hdrval))
            reqinfo += hdr + b'=' + hdrval + b"\n"

        reqinfo += b"\n\n"
        fp.write(reqinfo)

        fp.write(hcc)
        fp.close()

        return

    # begin dbus signals
    def emitDBusBeginLogin(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "beginlogin")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusGotQRCode(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "gotqrcode")

        qrpic64 = self.qrpic.toBase64()
        qrpic64str = qrpic64.data().decode()
        sigmsg.setArguments([123, qrpic64str])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusLoginSuccess(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "loginsuccess")

        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusLogined(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "logined")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))
        return

    def emitDBusLogouted(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "logouted")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))
        return

    # @param hcc QByteArray
    def emitDBusNewMessage(self, hcc):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "newmessage")
        # sigmsg.setArguments([123, 456])
        hcc64 = hcc.toBase64()
        hcc64_str = hcc64.data().decode('utf8')
        qDebug(str(len(hcc)) + ',' + str(len(hcc64_str)))
        sigmsg.setArguments([len(hcc), hcc64_str, len(hcc)])
        # sigmsg.setArguments([123, 'abcnewmessagessssssssss'])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))
        return


############
class DelayReplySession():
    def __init__(self):
        self.message = None
        self.netreply = None
        self.busreply = None
        return


class WXAgentService(QObject):
    def __init__(self, parent=None):
        super(WXAgentService, self).__init__(parent)

        self.dses = {}  # reqno => DelayReplySession

        self._reply = None
        self.sysbus = QDBusConnection.systemBus()

        self.wxa = WXAgent(self)
        # self.wxa.reqfinished.connect(self.onNetReply, Qt.QueuedConnection)
        self.wxa.asyncRequestDone.connect(self.onDelayedReply, Qt.QueuedConnection)
        self.wxa.doboot()

        return

    @pyqtSlot(QDBusMessage, result=bool)
    def islogined(self, message):
        qDebug(str(message.arguments()))
        return self.wxa.logined

    @pyqtSlot(QDBusMessage, result='QString')
    def getqrpic(self, message):
        qrpic = QByteArray(self.wxa.qrpic)
        qrpic64 = qrpic.toBase64()

        rstr = qrpic64.data().decode('utf8')
        return rstr

    # TODO all network should be async
    @pyqtSlot(QDBusMessage, result='QString')
    def getmsgimage(self, message):
        imgurls = message.arguments()
        imgurl = imgurls[0]
        #imgurl = 'http://emoji.qpic.cn/wx_emoji/OlaTef8nbNwrx2yCBBaaictrcFZGbrDbEPFB96n3Rve8hjj0xCFpcyQ/'
        qDebug(str(imgurl))
        nsreq = QNetworkRequest(QUrl(imgurl))
        nsreq = self.wxa.mkreq(imgurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreply = self.wxa.nam.get(nsreq)
        nsreply.error.connect(self.wxa.onReplyError, Qt.QueuedConnection)
        return

    @pyqtSlot(QDBusMessage, result=str)
    def getmessageimage(self, message):
        qDebug(str(len(self.wxa.msgimage)))
        return  self.wxa.msgimagename

    @pyqtSlot(QDBusMessage, result=bool)
    def refresh(self, message):
        self.wxa.refresh()
        return True

    @pyqtSlot(QDBusMessage, result=bool)
    def logout(self, message):
        self.wxa.logout()
        return True

    # assert logined
    @pyqtSlot(QDBusMessage, result='QString')
    def getinitdata(self, message):
        if type(self.wxa.wxinitRawData) == bytes:  # we need QByteArray
            qDebug('maybe not inited.')
            return ''

        data64 = self.wxa.wxinitRawData.toBase64()
        rstr = data64.data().decode('utf8')
        return rstr

    @pyqtSlot(QDBusMessage, result='QString')
    def getcontact(self, message):
        if type(self.wxa.wxFriendRawData) == bytes: # we need QByteArray
            qDebug('maybe not inited.')
            return ''

        data64 = self.wxa.wxFriendRawData.toBase64()
        rstr = data64.data().decode('utf8')
        return rstr

    @pyqtSlot(QDBusMessage, result='QString')
    def getgroups(self, message):
        groups = json.JSONEncoder().encode(self.wxa.wxGroupUserNames)
        rstr = groups
        return rstr

    # @param from_username str
    # @param to_username str
    # @param content str, need utf8 encoded(but now seem utf16)
    # @param msg_type int optional
    @pyqtSlot(QDBusMessage, result=bool)
    def sendmessage(self, message):
        args = message.arguments()
        qDebug(json.dumps(args) )
        from_username = args[0]
        to_username = args[1]
        qDebug('cc type: ' + str(type(args[2])))
        content = args[2]

        msg_type = 1
        if len(args) > 3: msg_type = int(args[3])
        # TODO msg_type check
        # TODO content length check

        self.wxa.sendmessage(from_username, to_username, content, msg_type)
        return True

    # @calltype: async
    @pyqtSlot(QDBusMessage, result='QString')
    def getbatchcontact(self, message):
        args = message.arguments()
        members = args[0]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getbatchcontact(members)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    # @calltype: async
    @pyqtSlot(QDBusMessage, result=bool)
    def get_url(self, message):
        args = message.arguments()
        url = args[0]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.requrl(url)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    # @calltype: async
    # @param msgid str
    # @param thumb bool
    @pyqtSlot(QDBusMessage, result='QString')
    def get_msg_img(self, message):
        args = message.arguments()
        msgid = args[0]
        thumb = args[1] if len(args) > 1 else True

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getMsgImg(msgid, thumb)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    # @calltype: sync
    @pyqtSlot(QDBusMessage, result=str)
    def get_msg_img_url(self, message):
        args = message.arguments()
        msgid = args[0]
        thumb = args[1] if len(args) > 1 else True

        r = self.wxa.getMsgImgUrl(msgid, thumb)

        return r

    # @calltype: sync
    @pyqtSlot(QDBusMessage, result=str)
    def get_msg_file_url(self, message):
        args = message.arguments()
        sender_name = args[0]
        media_id = args[1]
        file_name = args[2]
        from_uin = args[3]

        r = self.wxa.getMsgFileUrl(sender_name, media_id, file_name, from_uin)

        return r

    # @calltype: async
    # @param msgid str
    @pyqtSlot(QDBusMessage, result='QString')
    def get_msg_voice(self, message):
        args = message.arguments()
        msgid = args[0]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getMsgVoice(msgid)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    def onDelayedReply(self, reqno, hcc):
        qDebug(str(reqno))

        if reqno not in self.dses: return

        s = self.dses.pop(reqno)
        s.busreply.setArguments([hcc])

        self.sysbus.send(s.busreply)

        return

    # @pyqtSlot(QDBusMessage, result=bool)
    # def hasmessage(self, message):
    #     # qDebug(str(message))
    #     qDebug(str(message.arguments()))
    #     return False

    # @pyqtSlot(QDBusMessage, result='QString')
    # def readmessage(self, message):
    #     # qDebug(str(message))
    #     qDebug(str(message.arguments()))
    #     message.setDelayedReply(True)

    #     netreply = self.wxa.webSync()
    #     drses = DelayReplySession()
    #     drses.message = message
    #     drses.busreply = message.createReply()
    #     drses.netreply = netreply

    #     return "not impossible see this."

    # @pyqtSlot(QDBusMessage, result=int)
    def login(self, message):
        # qDebug(str(message))
        qDebug(str(message.arguments()))
        return 456

    # @pyqtSlot(QDBusMessage, result=str)
    def islogined_t(self, message):
        # qDebug(str(message))
        qDebug(str(message.arguments()))

        message.setDelayedReply(True)
        dreply = message.createReply("789")
        self._reply = dreply

        QTimer.singleShot(5000, self.tshot)
        # dreply.setDelayedReply(False)
        # sesbus = QDBusConnection.sessionBus()
        # bret = sesbus.send(dreply)
        # qDebug(str(bret) + ',' + str(message.isDelayedReply()))
        # qDebug(str(bret) + ',' + str(dreply.isDelayedReply()))
        return "123"

    def tshot(self):
        bret = self.sysbus.send(self._reply)
        qDebug(str(bret))


##########
def init_dbus_service():
    sysbus = QDBusConnection.systemBus()
    bret = sysbus.registerService(WXAGENT_SERVICE_NAME)
    if bret is False:
        err = sysbus.lastError()
        print(err.name(), err.message())
        exit()
    qDebug(str(sysbus.name()))
    iface = sysbus.interface()
    qDebug(str(sysbus.interface()) + str(iface.service()) + str(iface.path()))

    return


def register_dbus_service(wxasvc):

    sysbus = QDBusConnection.systemBus()
    # bret = sysbus.registerObject("/io/qtc/wxagent", wxasvc, QDBusConnection.ExportAllSlots)
    bret = False
    if qVersion() >= '5.5':
        bret = sysbus.registerObject("/io/qtc/wxagent", WXAGENT_IFACE_NAME, wxasvc, QDBusConnection.ExportAllSlots)
    else:
        bret = sysbus.registerObject("/io/qtc/wxagent", wxasvc, QDBusConnection.ExportAllSlots)
    qDebug(str(sysbus))
    if bret is False:
        err = sysbus.lastError()
        print(err.name(), err.message())
        exit()

    return


def main():
    app = QCoreApplication(sys.argv)
    import wxagent.qtutil as qtutil
    qtutil.pyctrl()

    init_dbus_service()
    wxasvc = WXAgentService()
    register_dbus_service(wxasvc)

    app.exec_()
    return


if __name__ == '__main__': main()
