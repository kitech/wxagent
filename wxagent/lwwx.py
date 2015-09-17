# web weixin protocol

import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtDBus import *

# QDBUS_DEBUG

from .wxcommon import *
from .wxsession import *

from .ui_mainwindow import *
class QRWin(QMainWindow):
    def __init__(self, parent = None):
        super(QRWin, self).__init__(parent)        
        self.uiw = Ui_MainWindow()
        self.uiw.setupUi(self)

        self.wxses = None

        self.sysbus = QDBusConnection.systemBus()
        self.sysiface = QDBusInterface(WXAGENT_SERVICE_NAME, '/io/qtc/wxagent', WXAGENT_IFACE_NAME, self.sysbus)
        
        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sysbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        self.sysbus.connect(WXAGENT_SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logined', self.onDBusLogined)
        self.sysbus.connect(WXAGENT_SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logouted', self.onDBusLogouted)
        self.sysbus.connect(WXAGENT_SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'newmessage', self.onDBusNewMessage)
        
        # self.wx.qrpicGotten.connect(self.onQRPicGotten, Qt.QueuedConnection)
        self.uiw.pushButton.clicked.connect(self.onStart, Qt.QueuedConnection)
        self.uiw.pushButton_2.clicked.connect(self.onStop, Qt.QueuedConnection)
        self.uiw.pushButton_3.clicked.connect(self.onGetContact, Qt.QueuedConnection)
        self.uiw.pushButton_4.clicked.connect(self.onSyncCheck, Qt.QueuedConnection)
        self.uiw.pushButton_5.clicked.connect(self.onWebSync, Qt.QueuedConnection)
        self.uiw.pushButton_6.clicked.connect(self.onRefresh, Qt.QueuedConnection)
        self.uiw.pushButton_7.clicked.connect(self.createWXSession, Qt.QueuedConnection)
        self.uiw.pushButton_8.clicked.connect(self.onGetUrl, Qt.QueuedConnection)
        return

    @pyqtSlot(QDBusMessage)
    def onDBusLogined(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusLogouted(self, message):
        qDebug(str(message.arguments()))
        return

    @pyqtSlot(QDBusMessage)
    def onDBusNewMessage(self, message):
        # qDebug(str(message.arguments()))
        args = message.arguments()
        msglen = args[0]
        msghcc = args[1]

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

        AddMsgCount = jsobj['AddMsgCount']
        ModContactCount = jsobj['ModContactCount']

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
            #reply = self.iface.call('getqrpic', 123, 'a1', 456)
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
        self.wx.getContact()
        return
    def onSyncCheck(self):
        self.wx.syncCheck()
        return
    def onWebSync(self):
        self.wx.webSync()
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

    qrw = QRWin()
    qrw.show()

    app.exec_()
    return


if __name__ == '__main__': main()


