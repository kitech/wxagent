# w.qq Linux login agent daemon

import os, sys, time
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

from .qqcom import *
from .wxprotocol import *
from .txagent import TXAgent, AgentCookieJar, AgentStats


######
class QQAgent(TXAgent):
    qrpicGotten = pyqtSignal('QByteArray')
    asyncRequestDone = pyqtSignal(int, 'QByteArray')

    def __init__(self, asvc, parent=None):
        super(QQAgent, self).__init__(parent)

        self.asvc = asvc
        self.asts = AgentStats()

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.onReply, Qt.QueuedConnection)
        self.acj = AgentCookieJar()
        self.nam.setCookieJar(self.acj)

        self.connState = CONN_STATE_NONE
        self.logined = False
        self.appid = "501004106"
        self.qruuid = ''
        self.devid = 'e669767113868187'
        self.qrpic = b''   # QByteArray
        self.userAvatar = b''  # QByteArray
        self.cookies = []  # [QNetworkCookie]
        self.syncTimer = None  # QTimer
        self.clientMsgIdBase = qrand()
        self.clientid = 53999199

        self.wxproto = WXProtocol()

        self.asyncQueueIdBase = qrand()
        self.asyncQueue = {}  # {reply => id}
        self.refresh_count = 0

        return

    def refresh(self):
        oldname = self.nam
        oldname.finished.disconnect()
        self.nam = None

        qDebug('see this...')

        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.onReply, Qt.QueuedConnection)
        self.acj = AgentCookieJar()
        self.nam.setCookieJar(self.acj)

        self.connState = CONN_STATE_NONE
        self.logined = False
        self.appid = "501004106"
        self.qruuid = ''
        self.devid = 'e669767113868187'
        self.qrpic = b''   # QByteArray
        self.userAvatar = b''  # QByteArray
        self.cookies = []  # [QNetworkCookie]
        self.syncTimer = None  # QTimer

        self.asyncQueueIdBase = qrand()
        self.asyncQueue = {}  # {reply => id}

        self.login_sig = ''
        self.doboot()

        self.refresh_count += 1
        return

    def doboot(self):

        self.emitDBusBeginLogin()

        url = "https://ui.ptlogin2.qq.com/cgi-bin/login" + \
              "?daid=164&target=self&style=5&mibao_css=m_webqq&appid=" + "501004106" + \
              "&enable_qlogin=0&no_verifyimg=1&s_url=http://w.qq.com/" + \
              "proxy.html?f_url=loginerroralert&strong_login=1&login_state=10"

        req = self.mkreq(url)
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
        self.updateCookies(reply)

        if status_code is None and error_no in [99]:
            qDebug('maybe logout for timeout.')

        # statemachine by url and response content
        if url.startswith('https://ui.ptlogin2.qq.com/cgi-bin/login?'):

            self.connState = CONN_STATE_WANT_USERNAME
            # self.emitDBusWantQQNum()
            # self.checkNeedVerify()

            self.requestQRCode()
            ########
        elif url.startswith('https://ssl.ptlogin2.qq.com/check?'):

            # parse result
            strhcc = self.hcc2str(hcc)

            exp = r"ptui_checkVC\('(\d)','([^']+)','([^']+)','([^']+)','(\d)'\);"
            mats = re.findall(exp, strhcc)
            qDebug(str(mats))
            self.verify_need = mats[0][0]
            self.verify_code = mats[0][1]
            self.verify_salt = mats[0][2]
            self.verify_verify = mats[0][3]
            self.verify_rand_salt = mats[0][4]

            qDebug('Verify salt:' + self.verify_salt)
            if self.verify_need == '0':
                qDebug('Verify code:' + self.verify_code)
                cookies = reply.rawHeader(b'Set-Cookie')
                qDebug(cookies)

                self.verify_session = ''
                self.verify_drvs = ''
                for ckline in cookies.data().decode().split("\n"):
                    if ckline.startswith('ptvfsession='):
                        self.verify_session = ckline.split(';')[0].split('=')[1]
                    elif ckline.startswith('ptdrvs='):
                        self.verify_drvs = ckline.split(';')[0].split('=')[1]

                qDebug('session:'+self.verify_session)
                qDebug('drvs:'+self.verify_drvs)

                # self.doJSLogin()
                self.connState = CONN_STATE_WANT_PASSWORD
                self.emitDBusWantVerify()
            elif self.verify_need == '1':
                qDebug('We need verify code image: %s' % vc)
                self.getVerifyImage()
            else: qDebug('wtf???')
            ########
        elif url.startswith('https://ssl.captcha.qq.com/getimage?'):
            self.verify_code_pic = hcc
            self.saveContent('vfpic.jpg', hcc)

            # ## get the verify_session
            cookies = reply.rawHeader(b'Set-Cookie')
            qDebug(cookies)

            self.verify_session = ''
            self.verify_drvs = ''
            for ckline in cookies.data().decode().split("\n"):
                if ckline.startswith('ptvfsession='):
                    self.verify_session = ckline.split(';')[0].split('=')[1]
                elif ckline.startswith('ptdrvs='):
                    self.verify_drvs = ckline.split(';')[0].split('=')[1]

            qDebug('session:'+self.verify_session)
            qDebug('drvs:'+self.verify_drvs)

            self.connState = CONN_STATE_WANT_PASSWORD
            self.emitDBusWantVerify()
            ########
        elif url.startswith('https://ssl.ptlogin2.qq.com/login?'):
            qDebug('login stage 1 done.')

            # parse result:
            # ptuiCB('71','0','','0','您的帐号由于异常禁止登录，请联系客服。(2009081021)', 'QQNUMBER');
            # ptuiCB('0','0','http://ptlogin4.web2.qq.com/check_sig?...','0','登录成功！', 'yatsen1');
            # ptuiCB('4','2','','0','页面过期，请重试。(2776629272)', '');
            # errcode:71/0

            qDebug(hcc)
            strhcc = self.hcc2str(hcc)
            exp = r"ptuiCB\('(\d+)','([^']+)','([^']+)','([^']+)','([^']+)', '([^']+)'\);"
            mats = re.findall(exp, strhcc)
            errcode = int(mats[0][0])
            self.check_sig_url = mats[0][2]
            errmsg = mats[0][4]
            self.nickname = mats[0][5]

            if errcode != 0: qDebug(errmsg.encode())
            errcodes = [0, 2, 3, 4, 5, 6, 7, 8, 71, 10005]
            if errcode not in errcodes: qdebug('unkown new errcode:' + str(errcode))

            self.ptwebqq = self.getCookie4(reply.rawHeader(b'Set-Cookie'), 'ptwebqq')
            qDebug(self.ptwebqq)

            if errcode == 0:  # OK
                qDebug(hcc[0:120])
                self.loginCheckSig()
                pass
            elif errcode == 2:  # server busy, try agin
                pass
            elif errcode == 3:  # wrong password
                pass
            elif errcode == 4:  # wrong verify code
                qDebug('expired wait for password and verify code, refresh...')
                QTimer.singleShot(1, self.refresh)
                pass
            elif errcode == 5:  # verify faild
                pass
            elif errcode == 6 or errcode == 71: # You may need to try login again
                pass
            elif errcode == 7:  # Wrong input
                pass
            elif errcode == 8:  # Too many logins on this IP. Please try again
                pass
            elif errcode == 10005:  # need bar code
                pass
            else: pass
            ########
        elif url.startswith('http://ptlogin4.web2.qq.com/check_sig?'):
            qDebug('login check sig done.')
            # qDebug(hcc[0:120])

            # parse result:
            ### now do what，再验证一次是否登陆成功了
            self.loginGetVerifyWebQQ()

            ########
        elif url.startswith('https://ssl.ptlogin2.qq.com/ptqrshow?'):
            qDebug('get qr code done')

            self.qrpic = hcc

            self.qrsig = self.getCookie4(reply.rawHeader(b'Set-Cookie'), 'qrsig')
            qDebug(self.qrsig)

            self.qrpicGotten.emit(hcc)
            self.emitDBusGotQRCode()

            self.qrpic_show_begin_time = QDateTime.currentDateTime()
            self.pollLogin()
            ########
        elif url.startswith('https://ssl.ptlogin2.qq.com/ptqrlogin?'):
            qDebug('poll qr login...')
            qDebug(hcc)

            strhcc = self.hcc2str(hcc)
            # parse content
            # ptuiCB('66','0','','0','二维码未失效。(1451238424)', '');
            exp = r"ptuiCB\('(\d+)','(\d+)','(.*)','(\d+)','(.+)', '(.*)'\);"
            mats = re.findall(exp, strhcc)
            qDebug(str(mats).encode())

            ptcode = mats[0][0]

            if ptcode == '66':
                QTimer.singleShot(2345, self.pollLogin)
            elif ptcode == '67':
                QTimer.singleShot(2345, self.pollLogin)
            elif ptcode == '65':
                self.qrpic_show_expire_time = QDateTime.currentDateTime()
                qDebug(str(self.qrpic_show_begin_time.secsTo(self.qrpic_show_expire_time)))
                QTimer.singleShot(567, self.requestQRCode)
                pass
            elif ptcode == '0':
                self.ptwebqq = self.getCookie4(reply.rawHeader(b'Set-Cookie'), 'ptwebqq')
                qDebug('ptwebqq:' + self.ptwebqq)
                self.check_sig_url = mats[0][2]
                self.loginCheckSig()
                pass
            ########
        elif url.startswith('http://s.web2.qq.com/api/getvfwebqq?'):
            qDebug('getvfwebqq done')
            qDebug(hcc[0:120])

            ### get current state's vfwebqq
            strhcc = self.hcc2str(hcc)
            jshcc = json.JSONDecoder().decode(strhcc)
            self.newvfwebqq = jshcc['result']['vfwebqq']

            ### set online status, the last login stage
            self.loginSetOnline()

            ########
        elif url.startswith('http://d.web2.qq.com/channel/login2?'):
            qDebug('login set online status done')
            qDebug(hcc)

            ### parse result
            strhcc = self.hcc2str(hcc)
            jshcc = json.JSONDecoder().decode(strhcc)
            self.vfwebqq = jshcc['result']['vfwebqq']
            self.psessionid = jshcc['result']['psessionid']

            # self.logined = True
            self.requestSelfInfo()
            # self.connState = CONN_STATE_CONNECTED
            # self.emitDBusLoginSuccess()

            # ## now do what?
            self.eventPoll()

            ########
        elif url.startswith('http://d.web2.qq.com/channel/poll2?'):
            qDebug('msgpoll2 done.')
            qDebug(hcc)

            if status_code is None and error_no == 99:
                # 尝试重新建立新连接， 使用当前的会话信息再次发起请求
                # QTimer.singleShot(5678, self.tryReconnect)
                if self.canReconnect(): self.tryReconnect(self.eventPoll)
                return
            else:
                if self.inReconnect(): self.finishReconnect()

            if status_code == 502:
                qDebug('server unavliable...')
                self.eventPoll()
                return

            # parse result
            strhcc = self.hcc2str(hcc)
            jshcc = json.JSONDecoder().decode(strhcc)

            # retcode: 0/102/103/109/116/120/121
            retcode = int(jshcc['retcode'])

            if retcode == 0:
                self.emitDBusNewMessage(hcc)
                self.eventPoll()
                pass
            elif retcode == 102:
                self.eventPoll()
            elif retcode == 109:
                # 有消息了
                self.emitDBusNewMessage(hcc)
                pass
            elif retcode == 116:
                # {"retcode":116,"p":"3cbe693781c61e1e2766749cf46eb157f65a7bc156697804"}
                # 0a02035ddd71535708feb92acc1832e99fe9968426853187e81688d298d87bfa

                # refresh self.ptwebqq for later poll
                strhcc = self.hcc2str(hcc)
                jshcc = json.JSONDecoder().decode(strhcc)
                self.ptwebqq = jshcc['p']
                qDebug(self.ptwebqq)

                self.eventPoll()
            elif retcode in [103]:
                qDebug('login exception, refresh...')
                QTimer.singleShot(123, self.refresh)
                pass
            elif retcode in [120, 121]:
                qDebug('relink not impled')
                pass
            elif retcode == -30:
                qDebug('not impled')
                pass
            else: qDebug('unknown retcode.')

            ########
        elif url.startswith('http://s.web2.qq.com/api/get_self_info2?'):
            self.selfRawData = hcc
            qDebug('this is myself')

            # parse me
            strhcc = self.hcc2str(hcc)
            jshcc = json.JSONDecoder().decode(strhcc)

            self.username = jshcc['result']['uin']

            self.logined = True
            self.connState = CONN_STATE_CONNECTED
            self.emitDBusLoginSuccess()

            ########
        elif url.startswith('http://s.web2.qq.com/api/get_user_friends2?'):
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://s.web2.qq.com/api/get_group_name_list_mask2?'):
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            pass
            ########
        elif url.startswith('http://s.web2.qq.com/api/get_discus_list?'):
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            pass
            ########
        elif url.startswith('http://d.web2.qq.com/channel/get_online_buddies2?'):
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            pass
            ########
        elif url.startswith('http://d.web2.qq.com/channel/get_recent_list2?'):
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            pass
            ########
        elif url.startswith('http://d.web2.qq.com/channel/get_c2cmsg_sig2?'):
            qDebug(hcc)
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://s.web2.qq.com/api/get_group_info_ext2?'):
            qDebug(hcc)
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://d.web2.qq.com/channel/get_discu_info?'):
            qDebug(hcc)
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://s.web2.qq.com/api/get_friend_uin2?'):
            qDebug(hcc)
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://w.qq.com/d/channel/get_offpic2?'):
            qDebug(hcc)
            if (reply.hasRawHeader(b'Location')):
                redir = reply.rawHeader(b'Location').data().decode()
                # requrl: http://103.7.28.186:80/?ver=2173&rkey=a57579bda0d936f34129xxxxxxxxxxxx
                nsurl = redir
                nsreq = self.mkreq(nsurl)
                nsreply = self.nam.get(nsreq)

                reqno = self.asyncQueue[reply]
                self.asyncQueue.pop(reply)
                self.asyncQueue[nsreply] = reqno
            else:
                reqno = self.asyncQueue[reply]
                self.asyncQueue.pop(reply)
                self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://103.7.28.186:80/?ver=') and '&rkey=' in url:
            # 获取图片内容返回
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://103.7.29.36:80/?ver=') and '&rkey=' in url:
            # 获取图片内容返回
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://d.web2.qq.com/channel/get_file2?'):
            qDebug(hcc)
            if (reply.hasRawHeader(b'Location')):
                redir = reply.rawHeader(b'Location').data().decode()
                # requrl: http://file1.web.qq.com/v2/3040028095/2300061779/20868/1075/33946/0/0/1/f/16970/qt.png?psessionid=
                nsurl = redir
                nsreq = self.mkreq(nsurl)
                nsreply = self.nam.get(nsreq)

                reqno = self.asyncQueue[reply]
                self.asyncQueue.pop(reply)
                self.asyncQueue[nsreply] = reqno
            else:
                reqno = self.asyncQueue[reply]
                self.asyncQueue.pop(reply)
                self.asyncRequestDone.emit(reqno, hcc)
            ########
        elif url.startswith('http://file1.web.qq.com/v2/'):
            # 获取文件内容返回
            reqno = self.asyncQueue[reply]
            self.asyncQueue.pop(reply)
            self.asyncRequestDone.emit(reqno, hcc)
            ########
        else:
            qDebug('unknown requrl:' + str(url))
            qDebug(hcc[0:120])
            self.saveContent('qqunknown_requrl.json', hcc)

        return

    def onReplyError(self, errcode):
        qDebug('reply error:' + str(errcode))
        reply = self.sender()
        url = reply.url().toString()
        qDebug('url: ' + url)

        return

    def checkNeedVerify(self):
        import random
        self.username = '1449732709'
        self.appid = "501004106"

        nsurl = ('https://ssl.ptlogin2.qq.com' + \
                "/check?pt_tea=1&uin=%s&appid=" + "501004106" + "&" + \
                "js_ver=" + "10120" + "&js_type=0&login_sig=%s&pt_tea=1&u1=http://" + \
                "w.qq.com/proxy.html&r=%s") % \
                (self.username, '', str(random.random()))
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def getVerifyImage(self):
        import random
        nsurl = ('https://ssl.captcha.qq.com' +
                 "/getimage?aid=" + self.appid + "&uin=%s&r=%s&cap_cd=%s") % \
                 (self.username, random.randome(), self.verify_code)
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    # @return str
    def JSVerifyCalc(self, password, verify_salt, verify_code):
        import subprocess
        outstr = ''
        cmd = ['wxagent/qqjsverify.py', 'jsverify', password, verify_salt, verify_code]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        outstr, errstr = process.communicate()
        print(outstr)
        exp = r'resp:(.+)'
        mats = re.findall(exp, outstr.decode())
        return mats[0].lstrip()

    def JSInfoHash(self, uin, ptwebqq):
        import subprocess
        outstr = ''
        cmd = ['wxagent/qqjsverify.py', 'infohash', uin, ptwebqq]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        outstr, errstr = process.communicate()
        print(outstr)
        exp = r'resphash:(.+)'
        mats = re.findall(exp, outstr.decode())
        return mats[0].lstrip()

    # @return str
    def JSVerifyCalcInline(self, password, verify_salt, verify_code):
        import execjs
        jsrts = execjs.available_runtimes()
        jsrt = execjs.get('Node') if 'Node' in jsrts else None

        hash_js_file = os.path.dirname(os.path.realpath(__file__)) + '/encrypt.js'
        hash_js_fp = open(hash_js_file, "r")

        full_js = hash_js_fp.read()
        ctx = jsrt.compile(full_js)
        val = ctx.call('encryption', password, verify_salt, verify_code)
        return val

    def JSInfoHashInline(self, uin, ptwebqq):
        import execjs
        jsrts = execjs.available_runtimes()
        jsrt = execjs.get('Node') if 'Node' in jsrts else None

        hash_js_file = os.path.dirname(os.path.realpath(__file__)) + '/encrypt.js'
        hash_js_file = os.path.dirname(os.path.realpath(__file__)) + '/hash.js'
        hash_js_fp = open(hash_js_file, "r")

        full_js = hash_js_fp.read()
        ctx = jsrt.compile(full_js)
        val = ctx.call('P2', uin, ptwebqq)
        return val

    def getInfoHash(self, uin, ptwebqq):
        try:
            if self.info_hash is not None: return self.info_hash
        except Exception as ex:
            type(ex)
            pass

        uin = str(uin)
        # self.info_hash = self.JSInfoHash(uin, ptwebqq)
        self.info_hash = self.JSInfoHashInline(uin, ptwebqq)
        return self.info_hash

    def doJSLogin(self):

        use_verify_code = ''
        self.p = ''
        if self.verify_need == '1':
            use_verify_code = self.input_verify_code
        else:
            use_verify_code = self.verify_code
        p2 = self.JSVerifyCalc(self.password, self.verify_salt, use_verify_code)
        p22 = self.JSVerifyCalc(self.password, self.verify_salt, use_verify_code)
        qDebug(p2 + ',,,' + p22)
        p3 = self.JSVerifyCalcInline(self.password, self.verify_salt, use_verify_code)
        p32 = self.JSVerifyCalcInline(self.password, self.verify_salt, use_verify_code)
        qDebug(p3 + ',,,' + p32)
        self.p = p2

        # http%%3A%%2F%%2Fw.qq.com%%2Fproxy.html%%3Flogin2qq%%3D1%%26webqq_type%%3D10
        # http://w.qq.com/proxy.html?login2qq=1&webqq_type=10
        nsurl = ("https://ssl.ptlogin2.qq.com/login?" 
                 "u=%s"
                 "&p=%s"
                 "&verifycode=%s"
                 "&webqq_type=%s"
                 "&remember_uin=1"
                 "&aid=" + self.appid + "&login2qq=1"
                 '&u1=http%%3A%%2F%%2Fw.qq.com%%2Fproxy.html%%3Flogin2qq%%3D1%%26webqq_type%%3D10'
                 "&h=1"
                 "&ptredirect=0"
                 "&ptlang=2052"
                 "&daid=164"
                 "&from_ui=1"
                 "&pttype=1"
                 "&dumy="
                 "&fp=loginerroralert"
                 # "&action=0-0-5111"
                 "&mibao_css=m_webqq"
                 "&t=1"
                 "&g=1"
                 "&js_type=0"
                 "&js_ver=" + "10120" +  "&login_sig="
                 "&pt_uistyle=5"
                 "&pt_randsalt=%s"
                 "&pt_vcode_v1=0"
                 "&pt_verifysession_v1=%s") % \
                 (self.username, self.p, use_verify_code, 10, 0, self.verify_session)
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def requestQRCode(self):
        import random
        nsurl = 'https://ssl.ptlogin2.qq.com/ptqrshow?appid=501004106&e=0&l=M&s=5&d=72&v=4&t=0.704464654205367'
        nsurl = 'https://ssl.ptlogin2.qq.com/ptqrshow?appid=%s&e=0&l=M&s=5&d=72&v=4&t=%s' % \
                (self.appid, str(random.random()))
        qDebug(nsurl)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def pollLogin(self):
        nsurl = 'https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1&login2qq=1&aid=501004106&u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1%26webqq_type%3D10&ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=0-2-234799&mibao_css=m_webqq&t=1&g=1&js_type=0&js_ver=10135&login_sig=&pt_randsalt=0'
        nsurl = 'https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1&login2qq=1&aid=%s&u1=http://w.qq.com/proxy.html?login2qq=1&webqq_type=10&ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=0-2-234799&mibao_css=m_webqq&t=1&g=1&js_type=0&js_ver=10135&login_sig=&pt_randsalt=0' % \
                (self.appid)
        qDebug(nsurl)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def loginCheckSig(self):

        nsurl = 'http://ptlogin4.web2.qq.com/check_sig?pttype=1&uin=1449732709&service=login&nodirect=0&ptsigx=a68ecae444b83ef...'
        nsurl = self.check_sig_url
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def loginGetVerifyWebQQ(self):

        nsurl = 'http://s.web2.qq.com/api/getvfwebqq?ptwebqq=' + self.ptwebqq + '&clientid=53999199&psessionid=&t=1424324701030'
        nsurl = 'http://s.web2.qq.com/api/getvfwebqq?ptwebqq=%s&clientid=53999199&psessionid=&t=1424324701030' % \
                (self.ptwebqq)
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def loginSetOnline(self):
        nsurl = 'http://d.web2.qq.com/channel/login2?'
        qDebug(str(nsurl))

        post_data_obj = {
            "ptwebqq": self.ptwebqq,
            "clientid": 53999199,
            "psessionid":"",
            "status":"online",
            "passwd_sig": "",
        }
        post_data = json.JSONEncoder().encode(post_data_obj)
        qDebug(str(post_data))
        ### fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        return

    def eventPoll(self):
        nsurl = 'http://d.web2.qq.com/channel/poll2?'
        qDebug(str(nsurl))

        # r:{"ptwebqq":"acc30a5f77fc58b24694864bad33e45be4c28fa09b70f53c4e52aac5cf550179",
        # "clientid":53999199,
        # "psessionid":"8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e3834000035ed0000093c026e0400652a69566d0000000a4049424563327a334b656d0000002862508788b5fcbafaea2b3bee6dc94dee9aafb652c4b2f98145147331d68940605b5c364081533b79",
        # "key":""}
        post_data_obj = {
            "ptwebqq": self.ptwebqq,
            "clientid": 53999199,
            "psessionid": self.psessionid,
            "key": "",
        }
        post_data = json.JSONEncoder().encode(post_data_obj)
        qDebug(str(post_data))
        ### fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def requestSelfInfo(self):
        nsurl = 'http://s.web2.qq.com/api/get_self_info2?t=1441356850625'
        qDebug(str(nsurl))

        nsreq = self.mkreq(nsurl)
        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

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
    def getUserFriends(self):
        nsurl = 'http://s.web2.qq.com/api/get_user_friends2?'

        # r:{"vfwebqq":"e5f60d054feb0611e7aadff20252903bf85a636d896c3659986dbef12b5d64cb6c1b4607f545baa5",
        # "hash":"5F130B2A0B65592E"}
        post_data_obj = {
            'vfwebqq': self.newvfwebqq,
            'hash': self.getInfoHash(self.username, self.ptwebqq),
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        qDebug(self.ptwebqq)
        qDebug(self.vfwebqq)
        qDebug(self.newvfwebqq)
        # ## fix shit qq post data format
        post_data = 'r=' + post_data
        qDebug(bytes(post_data, 'utf8'))

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getGroupNameList(self):
        nsurl = 'http://s.web2.qq.com/api/get_group_name_list_mask2?'

        # r:{"vfwebqq":"e5f60d054feb0611e7aadff20252903bf85a636d896c3659986dbef12b5d64cb6c1b4607f545baa5",
        # "hash":"5F130B2A0B65592E"}
        post_data_obj = {
            'vfwebqq': self.newvfwebqq,
            'hash': self.getInfoHash(self.username, self.ptwebqq),
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        qDebug(self.ptwebqq)
        qDebug(self.vfwebqq)
        qDebug(self.newvfwebqq)
        # ## fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1')
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getDiscusList(self):

        nowt = self.nowTime()
        nsurl = 'http://s.web2.qq.com/api/get_discus_list?clientid=53999199&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e3834000035ed0000093c026e0400652a69566d0000000a4049424563327a334b656d00000028a8089c4ac5252c52af2dfb8c2389ab2437388f1ffaa095cc7755fcdbdc57407ca6216a0936714e33&vfwebqq=db89a0549f8cc718984e67947c05392cb4b3973c1bf90fb52a7c9c56b4000c37c7a0d022865e6361&t=1441377742655'
        nsurl = 'http://s.web2.qq.com/api/get_discus_list?clientid=%s&psessionid=%s&vfwebqq=%s&t=%s' % \
                (self.clientid, self.psessionid, self.newvfwebqq, nowt)

        post_data_obj = {
            'clientid': self.clientid,
            'psessionid': self.psessionid,
            'vfwebqq': self.newvfwebqq,
            't': nowt,
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getGroupOnlineBuddies(self):

        nowt = self.nowTime()
        nowt = str(time.time()).split('.')[0]
        nsurl = 'http://d.web2.qq.com/channel/get_online_buddies2?vfwebqq=db89a0549f8cc718984e67947c05392cb4b3973c1bf90fb52a7c9c56b4000c37c7a0d022865e6361&clientid=53999199&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e3834000035ed0000093c026e0400652a69566d0000000a4049424563327a334b656d00000028a8089c4ac5252c52af2dfb8c2389ab2437388f1ffaa095cc7755fcdbdc57407ca6216a0936714e33&t=1441377742795'
        nsurl = 'http://d.web2.qq.com/channel/get_online_buddies2?vfwebqq=%s&clientid=%s&psessionid=%s&t=%s' % \
                (self.newvfwebqq, self.clientid, self.psessionid, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getRecentList(self):

        nowt = self.nowTime()
        nsurl = 'http://d.web2.qq.com/channel/get_recent_list2?'

        post_data_obj = {
            'clientid': self.clientid,
            'psessionid': self.psessionid,
            'vfwebqq': self.newvfwebqq,
            't': nowt,
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        # ## fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getFaceIcon(self, uin):
        nsurl = 'http://face1.web.qq.com/cgi/svr/face/getface?cache=1&type=1&f=40&uin=4157863681&t=1441377742&vfwebqq=db89a0549f8cc718984e67947c05392cb4b3973c1bf90fb52a7c9c56b4000c37c7a0d022865e6361'
        nsurl = 'http://face1.web.qq.com/cgi/svr/face/getface?cache=1&type=1&f=40&uin=%s&t=%s&vfwebqq=%s' % \
                (uin, self.nowTime(), self.newvfwebqq)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setRawHeader(b'Referer', b'http://w.qq.com/')

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getC2CMsgSig(self, gid, to_uin, service_type):

        nowt = self.nowTime()
        nsurl = 'http://d.web2.qq.com/channel/get_c2cmsg_sig2?'
        nsurl = 'http://d.web2.qq.com/channel/get_c2cmsg_sig2?id=%s&to_uin=%s&clientid=%s&psessionid=%s&service_type=%s&t=%s'  %   \
                (gid, to_uin, self.clientid, self.psessionid, service_type, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getFriendDetail(self, to_uin):

        nowt = self.nowTime()
        nsurl = 'http://s.web2.qq.com/api/get_friend_uin2?tuin=%s&verifysession=&type=1&code=&vfwebqq=%s&t=%s' % \
                (to_uin, self.vfwebqq, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getGroupDetail(self, gcode):

        nowt = self.nowTime()
        nsurl = 'http://s.web2.qq.com/api/get_group_info_ext2?gcode=4243921733&vfwebqq=dcc18f7455d4ad57b64c7d779d4b74236465ece6675577496de0cf324d0d32e5cf6766be76294965&t=1442025939396'
        nsurl = 'http://s.web2.qq.com/api/get_group_info_ext2?gcode=%s&cb=undefined&vfwebqq=%s&t=%s' % \
                (gcode, self.vfwebqq, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    ####
    def getDiscusDetail(self, did):

        nowt = self.nowTime()
        nsurl = 'http://d.web2.qq.com/channel/get_discu_info?did=1011664478&vfwebqq=dcc18f7455d4ad57b64c7d779d4b74236465ece6675577496de0cf324d0d32e5cf6766be76294965&clientid=53999199&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e38340000439900000bde026e0400652a69566d0000000a406451553469573966496d000000282922098baee4e49b40c72a4dc53f80bb9fc5ded0e5b2d31ccace2448a66aa5ae4fd7a1e28b9163fa&t=1442025992605'
        nsurl = 'http://d.web2.qq.com/channel/get_discu_info?did=%s&clientid=%s&psessionid=%s&t=%s' % \
                (did, self.clientid, self.psessionid, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)
        reqno = self.nextReqno()
        self.asyncQueue[nsreply] = reqno
        return reqno

    #####
    def sendBuddyMessage(self, from_username, to_username, content):
        nsurl = 'http://d.web2.qq.com/channel/send_buddy_msg2?'

        fullcc = [content, ["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]]
        jscontent = json.JSONEncoder().encode(fullcc)
        jsfont = '["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]'

        # r:{"to":1769524962,
        # "content":"[\"ddddddddddddd\",
        #[\"font\",{\"name\":\"宋体\",\"size\":10,\"style\":[0,0,0],\"color\":\"000000\"}]]",
        # "face":591,"clientid":53999199,
        # "msg_id":77290005,
        # "psessionid":"8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e383400000f0100000995026e0400652a69566d0000000a407736617265753743546d0000002843dd80f60835be7c14f5f48ea1c1824823a9756206765ece2ed2610877279952e2b4c2eaf7694714"}

        # {"to": "1769524962",
        # "psessionid": "8368046764001d636f6e6e7365727665725f77656271714031302e3133332e34312e383400007a3e00000994026e0400652a69566d0000000a407736617265753743546d00000028a90c2a60852694ae6b6152fa2e51495dfd3d3d9019c1a295341a16a36566b2f191fa9d000569f472",
        # "content": "rrrrrrrrrqqqqqqqqqqq",
        # "msg_id": "14414456161217714",
        # "clientid": 53999199}
        post_data_obj = {
            'to': int(to_username),
            'content': jscontent,

            'face': 591,
            'msg_id': int(self.nextClientMsgId()),
            'clientid': self.clientid,
            'psessionid': self.psessionid,
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        ### fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def sendQunMessage(self, from_username, to_username, content):
        nsurl = 'http://d.web2.qq.com/channel/send_qun_msg2?'

        fullcc = [content, ["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]]
        jscontent = json.JSONEncoder().encode(fullcc)
        jsfont = '["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]'

        post_data_obj = {
            'group_uin': int(to_username),
            'content': jscontent,

            'msg_id': int(self.nextClientMsgId()),
            'clientid': self.clientid,
            'psessionid': self.psessionid,
        }

        # ## has_cface??? what's this???
        if False:
            post_data_obj['group_code'] = ''
            post_data_obj['key'] = ''
            post_data_obj['sig'] = ''

        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        # ## fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def sendSessionMessage(self, from_username, to_username, content, group_sig):
        nsurl = 'http://d.web2.qq.com/channel/send_sess_msg2?'

        fullcc = [content, ["font", {"name": "宋体", "size": 10, "style": [0, 0, 0], "color": "000000"}]]
        jscontent = json.JSONEncoder().encode(fullcc)
        # jsfont = '["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]'

        post_data_obj = {
            'to': int(to_username),
            'group_sig': group_sig,
            'service_type': 0,  # any else?, or 1 if group type is discus

            'content': jscontent,

            'msg_id': self.nextClientMsgId(),
            'clientid': self.clientid,
            'psessionid': self.psessionid,
        }
        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        # ## fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def sendDiscusMessage(self, from_username, to_username, content):
        nsurl = 'http://d.web2.qq.com/channel/send_discu_msg2?'

        fullcc = [content, ["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]]
        jscontent = json.JSONEncoder().encode(fullcc)
        jsfont = '["font",{"name":"宋体","size":10,"style":[0,0,0],"color":"000000"}]'

        post_data_obj = {
            'did': int(to_username),
            'content': jscontent,

            'msg_id': int(self.nextClientMsgId()),
            'clientid': self.clientid,
            'psessionid': self.psessionid,
        }

        # ## what???
        if False:
            post_data_obj['key'] = ''
            post_data_obj['sig'] = ''

        post_data = json.JSONEncoder(ensure_ascii=False).encode(post_data_obj)
        qDebug(bytes(post_data, 'utf8'))
        # ## fix shit qq post data format
        post_data = 'r=' + post_data

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)
        nsreq.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        nsreply = self.nam.post(nsreq, QByteArray(post_data.encode()))
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        return

    def getMsgImg(self, file_path, f_uin):
        # 目前一直响应"302"，可能是cookie不对，和浏览器上发送的cookie不一样
        # 少了verifysession=，p_skey=
        # 还真是cookie的问题，使用P3P，jsonp like方式让不同域名共享cookie解决。
        # file_path = ''
        # f_uin = ''
        psessionid = ''
        psessionid = self.psessionid
        nsurl = 'http://w.qq.com/d/channel/get_offpic2?file_path=%s&f_uin=%s&clientid=53999199&psessionid=%s' % \
                (file_path, f_uin, psessionid)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    def getMsgImgUrl(self, file_path, f_uin):
        # file_path = ''
        # f_uin = ''
        psessionid = ''
        psessionid = self.psessionid
        nsurl = 'http://w.qq.com/d/channel/get_offpic2?file_path=%s&f_uin=%s&clientid=53999199&psessionid=%s' \
                (file_path, f_uin, psessionid)
        return nsurl

    def getMsgFileUrl(self, lcid, guid, to_uin):
        # lcid = '20868'
        # guid = ''
        # to_uin = ''
        psessionid = self.psessionid
        nowt = self.nowTime()
        nsurl = 'http://d.web2.qq.com/channel/get_file2?lcid=20868&guid=%s&to=%s&psessionid=%s&count=1&time=%s&clientid=53999199' % \
                (lcid, guid, to_uin, psessionid, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    def getMsgFile(self, lcid, guid, to_uin):
        # lcid = 20868
        # guid = ''
        # to_uin = ''
        psessionid = self.psessionid
        nowt = self.nowTime()
        nsurl = 'http://d.web2.qq.com/channel/get_file2?lcid=%s&guid=%s&to=%s&psessionid=%s&count=1&time=%s&clientid=53999199' % \
                (lcid, guid, to_uin, psessionid, nowt)

        nsreq = QNetworkRequest(QUrl(nsurl))
        nsreq = self.mkreq(nsurl)

        nsreply = self.nam.get(nsreq)
        nsreply.error.connect(self.onReplyError, Qt.QueuedConnection)

        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        self.asyncQueue[nsreply] = reqno
        return reqno

    ###############
    def nextClientMsgId(self):
        now = QDateTime.currentDateTime()
        self.clientMsgIdBase = self.clientMsgIdBase + 1
        clientMsgId = '%s%4d' % (now.toMSecsSinceEpoch(), self.clientMsgIdBase % 10000)
        return clientMsgId

    def nextReqno(self):
        self.asyncQueueIdBase = self.asyncQueueIdBase + 1
        reqno = self.asyncQueueIdBase
        return reqno

    # 把所有reply的所有cookie都记录下来
    def updateCookies(self, reply):
        ckjar = self.nam.cookieJar()
        qDebug(str(ckjar))

        all_cookies = ckjar.xallCookies()

        for ck in all_cookies:
            doms = ('.w.qq.com', '.qq.com', '.web2.qq.com', '.d.web2.qq.com',
                    '.web.qq.com', '.s.web2.qq.com')

            nck = QNetworkCookie(ck)
            nck.setDomain('.w.qq.com')
            bret1 = ckjar.insertCookie(nck)

            nck = QNetworkCookie(ck)
            nck.setDomain('.qq.com')
            bret2 = ckjar.insertCookie(nck)

            nck = QNetworkCookie(ck)
            nck.setDomain('.web2.qq.com')
            bret3 = ckjar.insertCookie(nck)

            nck = QNetworkCookie(ck)
            nck.setDomain('.d.web2.qq.com')
            bret4 = ckjar.insertCookie(nck)

            nck = QNetworkCookie(ck)
            nck.setDomain('s.web.qq.com')
            bret5 = ckjar.insertCookie(nck)

            nck = QNetworkCookie(ck)
            nck.setDomain('.web.qq.com')
            bret6 = ckjar.insertCookie(nck)

            # qDebug(str(bret1) + str(bret2) + str(bret3))

        return

    # @return str
    def getCookie(self, name):
        ckjar = self.nam.cookieJar()
        domain = 'https://wx2.qq.com'
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

    # @param setcookie QByteArray
    def getCookie4(self, setcookie, name):
        str_cookies = setcookie.data().decode()
        for cline in str_cookies.split("\n"):
            qDebug(cline)
            for celem in cline.split(";"):
                kv = celem.strip().split('=')
                qDebug(str(kv))
                if (kv[0] == name): return kv[1];

        return

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
        ua = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36'
        req.setRawHeader(b'User-Agent', ua)
        return

    def setReferer(self, req):
        req.setRawHeader(b'Referer', b'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1')
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

        astr = hcc.data().decode('utf8')
        qDebug(astr[0:120].replace("\n", "\\n").encode())
        strhcc = astr

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

    def emitDBusWantQQNum(self):
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "wantqqnum")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusWantVerify(self):
        need = self.verify_need
        vcpic = 'dddddddd'

        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "wantverify")
        sigmsg.setArguments([need, vcpic, 123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusBeginLogin(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "beginlogin")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusGotQRCode(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "gotqrcode")

        qrpic64 = self.qrpic.toBase64()
        qrpic64str = qrpic64.data().decode()
        sigmsg.setArguments([123, qrpic64str])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusLoginSuccess(self):
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "loginsuccess")

        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def emitDBusLogined(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "logined")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))
        return

    def emitDBusLogouted(self):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "logouted")
        sigmsg.setArguments([123])

        sysbus = QDBusConnection.systemBus()
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))
        return

    # @param hcc QByteArray
    def emitDBusNewMessage(self, hcc):
        # sigmsg = QDBusMessage.createSignal("/", SERVICE_NAME, "logined")
        sigmsg = QDBusMessage.createSignal("/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', "newmessage")
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


class QQAgentService(QObject):
    def __init__(self, parent=None):
        super(QQAgentService, self).__init__(parent)

        self.dses = {}  # reqno => DelayReplySession

        self._reply = None
        self.sysbus = QDBusConnection.systemBus()

        self.wxa = QQAgent(self)
        # self.wxa.reqfinished.connect(self.onNetReply, Qt.QueuedConnection)
        self.wxa.asyncRequestDone.connect(self.onDelayedReply, Qt.QueuedConnection)
        self.wxa.doboot()

        return

    @pyqtSlot(QDBusMessage, result=bool)
    def islogined(self, message):
        qDebug(str(message.arguments()))
        return self.wxa.logined

    @pyqtSlot(QDBusMessage, result=int)
    def connstate(self, message):
        qDebug(str(message.arguments()))
        return self.wxa.connState

    @pyqtSlot(QDBusMessage, result=bool)
    def inputqqnum(self, message):
        qDebug(str(message.arguments()))
        args = message.arguments()
        num = args[0]

        self.wxa.username = num
        self.wxa.checkNeedVerify()
        return True

    @pyqtSlot(QDBusMessage, result=bool)
    def inputverify(self, message):
        qDebug(str(message.arguments()))
        args = message.arguments()
        password = args[0]
        verify_code = args[1]

        self.wxa.password = password
        self.wxa.input_verify_code = verify_code
        self.wxa.doJSLogin()
        return True

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
    def getselfinfo(self, message):
        if type(self.wxa.selfRawData) == bytes:  # we need QByteArray
            qDebug('maybe not inited.')
            return ''

        data64 = self.wxa.selfRawData.toBase64()
        rstr = data64.data().decode()
        return rstr

    # assert logined
    @pyqtSlot(QDBusMessage, result='QString')
    def getinitdata(self, message):
        if type(self.wxa.wxinitRawData) == bytes:  # we need QByteArray
            qDebug('maybe not inited.')
            return ''

        data64 = self.wxa.wxinitRawData.toBase64()
        rstr = data64.data().decode('utf8')
        return rstr

    # TODO 延迟响应请求抽象汇总。
    @pyqtSlot(QDBusMessage, result='QString')
    def getuserfriends(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getUserFriends()
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def getgroupnamelist(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True);
        s.busreply = s.message.createReply()

        reqno = self.wxa.getGroupNameList()
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def getdiscuslist(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getDiscusList()
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def getonlinebuddies(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True);
        s.busreply = s.message.createReply()

        reqno = self.wxa.getGroupOnlineBuddies()
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def getrecentlist(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True);
        s.busreply = s.message.createReply()

        reqno = self.wxa.getRecentList()
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def get_c2cmsg_sig(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        gid = args[0]
        to_uin = args[1]
        service_type = args[2]

        reqno = self.wxa.getC2CMsgSig(gid, to_uin, service_type)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def get_group_detail(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        gcode = args[0]
        # gcode = '753943144'

        reqno = self.wxa.getGroupDetail(gcode)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def get_discus_detail(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        did = args[0]
        # did = '3330059290'

        reqno = self.wxa.getDiscusDetail(did)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result='QString')
    def getfriendinfo(self, message):
        args = message.arguments()

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        to_uin = args[0]
        # to_uin = '3040028095'

        reqno = self.wxa.getFriendDetail(to_uin)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    @pyqtSlot(QDBusMessage, result=bool)
    def send_buddy_msg(self, message):
        args = message.arguments()

        from_username = args[0]
        to_username = args[1]
        qDebug('cc type: ' + str(type(args[2])))
        content = args[2]

        reqno = self.wxa.sendBuddyMessage(from_username, to_username, content)
        return True

    @pyqtSlot(QDBusMessage, result=bool)
    def send_qun_msg(self, message):
        args = message.arguments()

        from_username = args[0]
        to_username = args[1]
        qDebug('cc type: ' + str(type(args[2])))
        content = args[2]

        reqno = self.wxa.sendQunMessage(from_username, to_username, content)
        return True

    @pyqtSlot(QDBusMessage, result=bool)
    def send_sess_msg(self, message):
        args = message.arguments()

        from_username = args[0]
        to_username = args[1]
        qDebug('cc type: ' + str(type(args[2])))
        content = args[2]
        group_sig = args[3]

        reqno = self.wxa.sendSessionMessage(from_username, to_username, content, group_sig)
        return True

    @pyqtSlot(QDBusMessage, result=bool)
    def send_discus_msg(self, message):
        args = message.arguments()

        from_username = args[0]
        to_username = args[1]
        qDebug('cc type: ' + str(type(args[2])))
        content = args[2]

        reqno = self.wxa.sendDiscusMessage(from_username, to_username, content)
        return True

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

    # @calltype: async
    @pyqtSlot(QDBusMessage, result=bool)
    def geturl(self, message):
        args = message.arguments()
        url = args[0]

        r = self.wxa.requrl(url)

        return True

    # @calltype: async
    # @param msgid str
    # @param thumb bool
    @pyqtSlot(QDBusMessage, result='QString')
    def get_msg_img(self, message):
        args = message.arguments()
        file_path = args[0]
        f_uin = args[1]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getMsgImg(file_path, f_uin)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    # @calltype: sync
    @pyqtSlot(QDBusMessage, result=str)
    def get_msg_img_url(self, message):
        args = message.arguments()
        file_path = args[0]
        f_uin = args[1]

        r = self.wxa.getMsgImgUrl(file_path, f_uin)

        return r

    # @calltype: async
    @pyqtSlot(QDBusMessage, result=str)
    def get_msg_file(self, message):
        args = message.arguments()
        lcid = args[0]
        guid = args[1]
        to_uin = args[2]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getMsgFile(lcid, guid, to_uin)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    # @calltype: async
    @pyqtSlot(QDBusMessage, result=str)
    def get_msg_file_url(self, message):
        args = message.arguments()
        lcid = args[0]
        guid = args[1]
        to_uin = args[2]

        s = DelayReplySession()
        s.message = message
        s.message.setDelayedReply(True)
        s.busreply = s.message.createReply()

        reqno = self.wxa.getMsgFileUrl(lcid, guid, to_uin)
        s.netreply = reqno

        self.dses[reqno] = s
        return 'can not see this.'

    def onDelayedReply(self, reqno, hcc):
        qDebug(str(reqno))

        if reqno not in self.dses:
            qDebug('warning: reqno not found')
            return

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
    bret = sysbus.registerService(QQAGENT_SERVICE_NAME)
    if bret is False:
        err = sysbus.lastError()
        print(err.name(), err.message())
        exit()
    qDebug(str(sysbus.name()))
    iface = sysbus.interface()
    qDebug(str(sysbus.interface()) + str(iface.service()) + str(iface.path()))

    return


def register_dbus_service(asvc):

    sysbus = QDBusConnection.systemBus()
    bret = False
    if qVersion() >= '5.5':
        bret = sysbus.registerObject("/io/qtc/qqagent", QQAGENT_IFACE_NAME, asvc, QDBusConnection.ExportAllSlots)
    else:
        bret = sysbus.registerObject("/io/qtc/qqagent", asvc, QDBusConnection.ExportAllSlots)
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
    asvc = QQAgentService()
    register_dbus_service(asvc)

    app.exec_()
    return


if __name__ == '__main__': main()
