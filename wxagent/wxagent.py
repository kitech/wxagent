
# web weixin agent

import os, sys
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

# from dbus.mainloop.pyqt5 import DBusQtMainLoop
# DBusQtMainLoop(set_as_default = True)

SERVICE_NAME = 'io.qtc.wxagent'        

######
class WXMsgType(enum.IntEnum):
    MT_TEXT = 1
    MT_FACE = 2
    MT_SHOT = 3
    MT_VOICE = 34
    MT_X47 = 47  # 像是群内动画表情
    MT_X49 = 49  # 像是服务号消息,像是群内分享，像xml格式
    MT_X51 = 51
    MT_X10000 = 10000  # 系统通知？
    
######
class WXAgent(QObject):
    qrpicGotten = pyqtSignal('QByteArray')

    
    def __init__(self, asvc, parent = None):
        super(WXAgent, self).__init__(parent)

        self.asvc = asvc
        
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
        self.wxinitRawData = b''  # QByteArray
        self.wxinitData = None   # json decoded
        self.wxFriendRawData = b''  # QByteArray
        self.wxFriendData = None  #
        self.wxWebSyncRawData = b''  # QByteArray
        self.wxWebSyncData = None  # 
        self.wxSyncKey = None  # {[]}
        self.syncTimer = None  # QTimer
        
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
        self.wxinitRawData = b''  # QByteArray
        self.wxinitData = None   # json decoded
        self.wxFriendRawData = b''  # QByteArray
        self.wxFriendData = None  #
        self.wxWebSyncRawData = b''  # QByteArray
        self.wxWebSyncData = None  # 
        self.wxSyncKey = None  # {[]}
        self.syncTimer = None  # QTimer

        self.doboot()
        return
    
    def doboot(self):
        url = "https://login.weixin.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx2.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=en_US"
        req = QNetworkRequest(QUrl(url))
        req = self.mkreq(url)
        req.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        
        reply = self.nam.get(req)

        return
    
    def onReply(self, reply):
        self.dumpReply(reply)

        url = reply.url().toString()
        hcc = reply.readAll()
        qDebug('content-length:' + str(len(hcc)))
        
        # statemachine by url and response content
        if url.startswith('https://login.weixin.qq.com/jslogin?'):
            qDebug("qr login code/uuic:" + str(hcc))
            # parse hcc: window.QRLogin.code = 200; window.QRLogin.uuid = "gYmgd1grLg==";
            qrcode = 200
            qruuid = ''
            qruuid = hcc.data().decode('utf8').split('"')[1]
            # qDebug(str(qruuid))
            self.qruuid = qruuid
            
            nsurl = 'https://login.weixin.qq.com/qrcode/4ZYgra8RHw=='
            nsurl = 'https://login.weixin.qq.com/qrcode/%s' % qruuid
            qDebug(str(nsurl))

            nsreq = QNetworkRequest(QUrl(nsurl))
            nsreq = self.mkreq(nsurl)
            nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
            nsreply = self.nam.get(nsreq)
            
        elif url.startswith('https://login.weixin.qq.com/qrcode/'):
            qDebug("qr pic:" + str(len(hcc)))
            self.qrpic = hcc;
            self.qrpicGotten.emit(hcc)

            self.pollLogin()
            
        elif url.startswith('https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?'):
            qDebug("app scaned qrpic:" + str(hcc))
            
            # window.code=408;  # 像是超时
            # window.code=400;  # ??? 难道是会话过期???需要重新获取QR图
            # window.code=201;  # 已扫描，未确认
            # window.code=200;  # 已扫描，已确认登陆
            # parse hcc, format: window.code=201;
            scan_code = hcc.data().decode('utf8').split('=')[1][0:3]

            if scan_code == '408': self.pollLogin()
            elif scan_code == '400':
                qDebug("maybe need rerun doboot()...")
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
                qDebug(nsurl)
                nsreq = QNetworkRequest(QUrl(nsurl))
                nsreq = self.mkreq(nsurl)
                nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
                nsreply = self.nam.get(nsreq)

                pass
            else: qDebug('not impled:' + scan_code)

        elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?'):
            qDebug('got wxuin and wxsid and other important cookie:')
            cookies = reply.header(QNetworkRequest.SetCookieHeader)
            qDebug(str(cookies))
            self.cookies = cookies
            self.wxuin = self.getCookie3('wxuin')
            self.wxsid = self.getCookie3('wxsid')
            qDebug(str(self.wxuin) + ',' + str(self.wxsid))
            
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
        elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?'):
            qDebug('wxinited.:' + str(type(hcc)))
            self.wxinitRawData = hcc
            self.saveContent("baseinfo.json", hcc)
            
            # qDebug(str(hcc.data().decode('utf8')))  # why can not decode?
            # UnicodeEncodeError: 'ascii' codec can't encode characters in position 131-136: ordinal not in range(128)
            strhcc = self.hcc2str(hcc)

            if len(strhcc) > 0:
                jsobj = json.JSONDecoder().decode(strhcc)
                self.wxinitData = jsobj
                self.wxSyncKey = jsobj['SyncKey']
            else:
                qDebug('can not decode hcc base info')


            self.getContact()
            self.syncCheck()
            ########
            
        elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?'):
            qDebug('get contact:' + str(len(hcc)))
            self.wxFriendRawData = hcc
            # parser contact data:

        elif url.startswith('https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?'):
            qDebug('sync check result:' + str(hcc))
            # window.synccheck={retcode:”0”,selector:”0”}
            # selector: 6: 表示有新消息
            # selector: 7: ??? 打开了某项，如群，好友，是一个事件
            # selector: 2: ??? 有新消息
            # selector: 4: ??? 
            # retcode: 1100:???
            # retcode: 1101:??? 会话已退出/结束
            # retcode: 0: 成功

            # parser result:
            
            reg = r'window.synccheck={retcode:"(\d+)",selector:"(\d)"}'
            mats = re.findall(reg, hcc.data().decode('utf8'))
            qDebug(str(mats) + '---' + hcc.data().decode('utf8'))
            retcode = mats[0][0]
            selector = mats[0][1]

            if retcode == '1101':
                qDebug("maybe need rerun doboot()...")
            elif retcode != '0':
                qDebug('error sync check ret code:')
            else:
                if selector == '0':
                    self.syncCheck()
                    pass
                elif selector == '2':
                    self.webSync()
                    pass
                elif selector == '4':  ### TODO,confirm this
                    self.webSync()
                    pass
                elif selector == '7':
                    self.webSync()
                    pass
                else: qDebug('Unknown selctor value:')

        ##############
        elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?'):
            qDebug('web sync result:' + str(len(hcc)))
            self.wxWebSyncRawData = hcc
            self.saveContent('websync.json', hcc)
            self.emitDBusNewMessage(hcc)
            
            # parse web sync result:
            strhcc = self.hcc2str(hcc)

            if len(strhcc) > 0:
                jsobj = json.JSONDecoder().decode(strhcc)
                self.wxWebSyncData = jsobj
                self.wxSyncKey = jsobj['SyncKey']

                ### other process

                ### => synccheck()
                if jsobj['BaseResponse']['Ret'] == 0: self.syncCheck()
                else: qDebug('web sync error:' + str(jsobj['BaseResponse']['Ret'])
                             + ',' + str(jsobj['BaseResponse']['ErrMsg']))
            else:
                qDebug('can not decode hcc base info')

            #######
        elif url.startswith('https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?'):
            qDebug('logouted...')
            QTimer.singleShot(3, self.refresh)

            ########
        else:
            qDebug('unknown requrl:' + str(url))


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
        return

    
    def getBaseInfo(self):
        # TODO: pass_ticket参数
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=1377482058764'
        # v2 url:https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1222669677&lang=en_US&pass_ticket=%252BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%252FZJJXurz79ARX%252FIT
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r='
        qDebug(nsurl)

        post_data = '{"BaseRequest":{"Uin":"%s","Sid":"%s","Skey":"","DeviceID":"%s"}}' % \
                    (self.wxuin, self.wxsid, self.devid)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
            
        # nsreply = self.nam.get(nsreq)  # TODO POST
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))

        return

    def getContact(self):
        
        nsurl = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?r=1377482079876'
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?r='

        post_data = '{}'
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
            
        # nsreply = self.nam.get(nsreq)  # TODO POST
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
        
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
        pass_ticket = self.wxPassTicket.replace('%', '%25')
        nsurl = 'https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18309326978388708085_1377482079946&r=1377482079876&sid=QfLp+Z+FePzvOFoG&uin=2545437902&deviceid=e1615250492&synckey=(见以下说明)&_=1377482079876'
        nsurl = 'https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=&r=&skey=%s&sid=%s&uin=%s&deviceid=e1615250492&synckey=%s&_=' % \
                (skey, self.wxsid, self.wxuin, syncKey)
        # v2 url:https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=1440036883783&skey=%40crypt_3ea2fe08_723d1e1bd7b4171657b58c6d2849b367&sid=9qxNHGgi9VP4%2FTx6&uin=979270107&deviceid=e669767113868147&synckey=1_638162182%7C2_638162328%7C3_638162098%7C11_638162315%7C201_1440036879%7C203_1440034958%7C1000_1440031958&lang=en_US&pass_ticket=%252BEdqKi12tfvM8ZZTdNeh4GLO9LFfwKLQRpqWk8LRYVWFkDE6%252FZJJXurz79ARX%252FIT
        nsurl = 'https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=%s&skey=%s&sid=%s&uin=%s&deviceid=%s&synckey=%s&lang=en_US&pass_ticket=%s' % \
                (self.nowTime(), skey, self.wxsid, self.wxuin, self.devid, syncKey, pass_ticket)

        
        qDebug(nsurl)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        joined_cookies = self.joinCookies()
        # nsreq.setHeader(QNetworkRequest.CookieHeader, QByteArray(joined_cookies.encode('utf8')))
        nsreq.setRawHeader(b'Cookie', joined_cookies.encode('utf8'))
        
        nsreply = self.nam.get(nsreq)
        
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
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' % \
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
        
        return nsreply

    def logout(self):

        skey = self.wxinitData['SKey'].replace('@', '%40')

        # POST
        # https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?redirect=1&type=0&skey=%40crypt_3ea2fe08_3d6fd43e69bbeea4553311ee632760cc
        nsurl = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxlogout?redirect=0&type=0&skey=%s' % \
                (skey)

        post_data = 'sid=%s&uin=%s' % (self.wxsid, self.wxuin)
        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'https://wx2.qq.com/?lang=en_US')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
            
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode('utf8')))
    
        return 

    #
    def requrl(self, url, method, data):
        
        return
    
    # @return str
    def getCookie(self, name):
        ckjar = self.nam.cookieJar()
        domain = 'https://wx2.qq.com'
        cookies = ckjar.cookiesForUrl(QUrl(domain))

        for cookie in cookies:
            tname = cookie.name().data().decode('utf8')
            val = cookie.value().data.decode('utf8')
            qDebug(tname + '=' + val);
            if tname == name:
                return val
        return

    
    def getCookie2(self, name):
        str_cookies = self.cookies.data().decode('utf8')
        for cline in str_cookies.split("\n"):
            for celem in cline.split(";"):
                kv = celem.strip().split('=')
                if (kv[0] == name): return kv[1];
            
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
        qDebug(str(req.url()))
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
            qDebug(astr[0:120].replace("\n", "\\n"))
            strhcc = astr
        except Exception as ex:
            qDebug('decode gbk error:')

        try:
            astr = hcc.data().decode('utf16')
            qDebug(astr[0:120].replace("\n", "\\n"))
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf16 error:')

        try:
            astr = hcc.data().decode('utf8')
            qDebug(astr[0:120].replace("\n", "\\n"))
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf8 error:')

        return strhcc

    # @param name str
    # @param hcc QByteArray
    # @return None
    def saveContent(self, name, hcc):
        # fp = QFile("baseinfo.json")
        fp = QFile(name)
        fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
        # fp.resize(0)
        fp.write(hcc)
        fp.close()
        
        return


    def emitDBusLogined(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "logined")
        sigmsg.setArguments([123])

        sesbus = QDBusConnection.sessionBus()
        bret = sesbus.send(sigmsg)
        qDebug(str(bret))
        return

    def emitDBusLogouted(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', "logouted")
        sigmsg.setArguments([123])

        sesbus = QDBusConnection.sessionBus()
        bret = sesbus.send(sigmsg)
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

        sesbus = QDBusConnection.sessionBus()
        bret = sesbus.send(sigmsg)
        qDebug(str(bret))
        return

    
############
class DelayReplySession():
    def __init__(self):
        self.message = None
        self.netreply = None
        return
    
class WXAgentService(QObject):
    def __init__(self, parent = None):
        super(WXAgentService, self).__init__(parent)

        self.dses = {}  # QNetworkReply => DelayReplySession
        
        self._reply = None
        self.sesbus = QDBusConnection.sessionBus()

        self.wxa = WXAgent(self)
        # self.wxa.reqfinished.connect(self.onNetReply, Qt.QueuedConnection)
        self.wxa.doboot()
        
        return
    

    @pyqtSlot(QDBusMessage, result=bool)
    def islogined(self, message):
        qDebug(str(message.arguments()))
        return self.wxa.logined

    @pyqtSlot(QDBusMessage, result='QString')
    def getqrpic(self, message):
        qrpic = self.wxa.qrpic
        qrpic64 = qrpic.toBase64()

        rstr = qrpic64.data().decode('utf8')
        return rstr

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
        data64 = self.wxa.wxinitRawData.toBase64()
        rstr = data64.data().decode('utf8')
        return rstr


    @pyqtSlot(QDBusMessage, result='QString')
    def getcontact(self, message):
        data64 = self.wxa.wxFriendRawData.toBase64()
        rstr = data64.data().decode('utf8')
        return rstr

    
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

    
    @pyqtSlot(QDBusMessage, result=int)
    def login(self, message):
        # qDebug(str(message))
        qDebug(str(message.arguments()))
        return 456

    @pyqtSlot(QDBusMessage, result=str)
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
        bret = self.sesbus.send(self._reply)
        qDebug(str(bret))

    def onNetReply(self, netreply):
        qDebug(str(netreply))
        
        return
        
##########    
def init_dbus_service(wxasvc):
    sesbus = QDBusConnection.sessionBus()

    bret = sesbus.registerService(SERVICE_NAME)
    qDebug(str(bret))

    bret = sesbus.registerObject("/", wxasvc, QDBusConnection.ExportAllSlots)
    qDebug(str(bret))

    return

def main():    
    app = QCoreApplication(sys.argv)
    import wxagent.qtutil as qtutil
    qtutil.pyctrl()

    wxasvc = WXAgentService()
    init_dbus_service(wxasvc)

    app.exec_()
    return

if __name__ == '__main__': main()



