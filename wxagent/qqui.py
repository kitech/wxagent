# web qq simple ui for test

import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtDBus import *

from .qqcom import *

from .ui_qqui import *


class QQWin(QMainWindow):

    def __init__(self, parent=None):
        super(QQWin, self).__init__(parent)
        self.uiw = Ui_MainWindow()
        self.uiw.setupUi(self)

        self.wxses = None
        self.asyncWatchers = {}

        self.sysbus = QDBusConnection.systemBus()
        self.sysiface = QDBusInterface(QQAGENT_SERVICE_NAME, '/io/qtc/qqagent', QQAGENT_IFACE_NAME, self.sysbus)

        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sysbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantqqnum', self.onDBusWantQQNum)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantverify', self.onDBusWantPasswordAndVerifyCode)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logined', self.onDBusLogined)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'loginsuccess', self.onDBusLoginSuccess)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logouted', self.onDBusLogouted)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'newmessage', self.onDBusNewMessage)

        self.uiw.pushButton.clicked.connect(self.onSendQQNum, Qt.QueuedConnection)
        self.uiw.pushButton_2.clicked.connect(self.onSendVerifyInfo, Qt.QueuedConnection)
        self.uiw.pushButton_7.clicked.connect(self.onGetContact, Qt.QueuedConnection)
        self.uiw.pushButton_11.clicked.connect(self.onGetState, Qt.QueuedConnection)
        return

    @pyqtSlot(QDBusMessage)
    def onDBusWantQQNum(self, message):
        qDebug(str(message.arguments()))
        return

    # @param a0=needvfc
    # @param a1=vfcpic
    @pyqtSlot(QDBusMessage)
    def onDBusWantPasswordAndVerifyCode(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusLogined(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusLoginSuccess(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusLogouted(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusNewMessage(self, message):
        qDebug(str(message.arguments()))
        args = message.arguments()
        msglen = args[0]
        msghcc = args[1]

        if True: return
        if self.wxses is None: self.createWXSession()

        for arg in args:
            if type(arg) == int:
                qDebug(str(type(arg)) + ',' + str(arg))
            else:
                qDebug(str(type(arg)) + ',' + str(arg)[0:120])

        hcc64_str = args[1]
        hcc64 = hcc64_str.encode('utf8')
        hcc = QByteArray.fromBase64(hcc64)

        self.saveContent('msgfromdbus.json', hcc)

        wxmsgvec = WXMessageList()
        wxmsgvec.setMessage(hcc)

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)

        # for um in jsobj['AddMsgList']:
        #     tm = 'MT:%s,' % (um['MsgType'])   # , um['Content'])
        #     try:
        #         tm = ':::,MT:%s,%s' % (um['MsgType'], um['Content'])
        #         qDebug(str(tm))
        #     except Exception as ex:
        #         # qDebug('can not show here')
        #         rct = um['Content']
        #         print('::::::::::,MT', um['MsgType'], str(type(rct)), rct)
        #     self.uiw.plainTextEdit.appendPlainText(um['Content'])

        msgs = wxmsgvec.getContent()
        for msg in msgs:
            fromUser = self.wxses.getUserByName(msg.FromUserName)
            toUser = self.wxses.getUserByName(msg.ToUserName)
            qDebug(str(fromUser))
            qDebug(str(toUser))
            fromUser_NickName = ''
            if fromUser is not None: fromUser_NickName = fromUser.NickName
            toUser_NickName = ''
            if toUser is not None: toUser_NickName = toUser.NickName

            content = msg.UnescapedContent
            logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::%s' % \
                     (msg.CreateTime, msg.MsgType, msg.FromUserName, fromUser_NickName,
                      msg.ToUserName, toUser_NickName, msg.MsgId, content)
            self.uiw.plainTextEdit.appendPlainText(logstr)

        return

    def createWXSession(self):
        if self.wxses is not None:
            return

        self.wxses = WXSession()

        # reply = self.iface.call('getinitdata', 123, 'a1', 456)
        reply = self.sysiface.call('getinitdata', 123, 'a1', 456)
        rr = QDBusReply(reply)
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode('utf8')   # to bytes
        data = QByteArray.fromBase64(data64)
        self.wxses.setInitData(data)
        self.saveContent('initdata.json', data)

        # reply = self.iface.call('getcontact', 123, 'a1', 456)
        reply = self.sysiface.call('getcontact', 123, 'a1', 456)
        rr = QDBusReply(reply)
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode('utf8')   # to bytes
        data = QByteArray.fromBase64(data64)
        self.wxses.setContact(data)
        self.saveContent('contact.json', data)

        return

    def getConnState(self):
        reply = self.sysiface.call('connstate', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))

        return rr.value()

    def sendQQNum(self, num):
        reply = self.sysiface.call('inputqqnum', num, 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        return

    def sendPasswordAndVerify(self, password, verify_code):
        reply = self.sysiface.call('inputverify', password, verify_code, 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        return

    def onSendQQNum(self):
        num = self.uiw.lineEdit.text()
        self.sendQQNum(num)
        return

    def onSendVerifyInfo(self):
        password = self.uiw.lineEdit_2.text()
        verify_code = self.uiw.lineEdit_3.text()

        self.sendPasswordAndVerify(password, verify_code)
        return

    def onQRPicGotten(self, qrpic):
        qDebug(str(len(qrpic)))
        fp = QFile("qrpic.jpg")
        fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
        fp.write(qrpic)
        fp.close()

        pix = QPixmap("qrpic.jpg")
        npix = pix.scaled(180, 180)
        self.uiw.label.setPixmap(npix)

        return

    def onStart(self):
        # reply = self.iface.call('islogined', 'a0', 123, 'a1')
        reply = self.sysiface.call('islogined', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        if not rr.isValid():
            qDebug(str(rr.error().message()))
            qDebug(str(rr.error().name()))
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))

        if rr.value() is False:
            # reply = self.iface.call('getqrpic', 123, 'a1', 456)
            reply = self.sysiface.call('getqrpic', 123, 'a1', 456)
            rr = QDBusReply(reply)
            qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
            qrpic64 = rr.value().encode('utf8')   # to bytes
            qrpic = QByteArray.fromBase64(qrpic64)
            self.onQRPicGotten(qrpic)

        return

    def onStop(self):
        # reply = self.iface.call('logout', 'a0', 123, 'a1')
        reply = self.sysiface.call('logout', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        return

    def onRefresh(self):
        # reply = self.iface.call('refresh', 'a0', 123, 'a1')
        reply = self.sysiface.call('refresh', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        return

    def onGetContact(self):

        pcall = self.sysiface.asyncCall('getuserfriends', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone)
        self.asyncWatchers[watcher] = 'getuserfriends'

        pcall = self.sysiface.asyncCall('getgroupnamelist', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone)
        self.asyncWatchers[watcher] = 'getgroupnamelist'

        pcall = self.sysiface.asyncCall('getdiscuslist', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone)
        self.asyncWatchers[watcher] = 'getdiscuslist'

        pcall = self.sysiface.asyncCall('getonlinebuddies', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone)
        self.asyncWatchers[watcher] = 'getgrouponlinebuddies'

        pcall = self.sysiface.asyncCall('getrecentlist', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone)
        self.asyncWatchers[watcher] = 'getrecentlist'

        return

    def onGetContactDone(self, watcher):
        pendReply = QDBusPendingReply(watcher)
        qDebug(str(watcher))
        qDebug(str(pendReply.isValid()))
        if pendReply.isValid():
            hcc = pendReply.argumentAt(0)
            qDebug(str(type(hcc)))
        else:
            hcc = pendReply.argumentAt(0)
            qDebug(str(len(hcc)))
            qDebug(str(hcc))
            return

        message = pendReply.reply()
        args = message.arguments()
        qDebug(str(args))
        extrainfo = self.asyncWatchers[watcher]
        self.saveContent('dr.'+extrainfo+'.json', args[0])

        ######
        hcc = args[0]  # QByteArray
        strhcc = self.hcc2str(hcc)
        hccjs = json.JSONDecoder().decode(strhcc)
        print(extrainfo, ':::', strhcc)

        self.asyncWatchers.pop(watcher)
        return

    def onSyncCheck(self):
        self.wx.syncCheck()
        return

    def onWebSync(self):
        self.wx.webSync()
        return

    def onGetState(self):
        state = self.getConnState()
        qDebug('curr conn state:' + str(state))
        return

    def onGetUrl(self):
        url = self.uiw.lineEdit.text()
        # reply = self.iface.call('geturl', url, 'a0', 123, 'a1')
        reply = self.sysiface.call('geturl', url, 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
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


def main():
    app = QApplication(sys.argv)
    import wxagent.qtutil as qtutil
    qtutil.pyctrl()

    qqw = QQWin()
    qqw.show()

    app.exec_()
    return


if __name__ == '__main__': main()


