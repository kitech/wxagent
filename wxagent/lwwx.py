# web weixin protocol

import os, sys
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtDBus import *

SERVICE_NAME = 'io.qtc.wxagent'
# QDBUS_DEBUG

from wxagent.ui_mainwindow import *
class QRWin(QMainWindow):
    def __init__(self, parent = None):
        super(QRWin, self).__init__(parent)        
        self.uiw = Ui_MainWindow()
        self.uiw.setupUi(self)

        self.sesbus = QDBusConnection.sessionBus()
        self.iface = QDBusInterface(SERVICE_NAME, '/', '', self.sesbus)

        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sesbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logined', self.onDBusLogined)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logouted', self.onDBusLogouted)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'newmessage', self.onDBusNewMessage)
        
        # self.wx.qrpicGotten.connect(self.onQRPicGotten, Qt.QueuedConnection)
        self.uiw.pushButton.clicked.connect(self.onStart, Qt.QueuedConnection)
        self.uiw.pushButton_2.clicked.connect(self.onStop, Qt.QueuedConnection)
        self.uiw.pushButton_3.clicked.connect(self.onGetContact, Qt.QueuedConnection)
        self.uiw.pushButton_4.clicked.connect(self.onSyncCheck, Qt.QueuedConnection)
        self.uiw.pushButton_5.clicked.connect(self.onWebSync, Qt.QueuedConnection)
        self.uiw.pushButton_6.clicked.connect(self.onRefresh, Qt.QueuedConnection)
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
        
        for arg in args:
            if type(arg) == int:
                qDebug(str(type(arg)) + ',' + str(arg))
            else:
                qDebug(str(type(arg)) + ',' + str(arg)[0:120])

        hcc64_str = args[1]
        hcc64 = hcc64_str.encode('utf8')
        hcc = QByteArray.fromBase64(hcc64)

        self.saveContent('msgfromdbus.json', hcc)

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)

        AddMsgCount = jsobj['AddMsgCount']
        ModContactCount = jsobj['ModContactCount']

        for um in jsobj['AddMsgList']:
            tm = 'MT:%s,' % (um['MsgType'])   # , um['Content'])
            try:
                tm = ':::,MT:%s,%s' % (um['MsgType'], um['Content'])
                qDebug(str(tm))
            except Exception as ex:
                # qDebug('can not show here')
                rct = um['Content']
                print('::::::::::,MT', um['MsgType'], str(type(rct)), rct)
            self.uiw.plainTextEdit.appendPlainText(um['Content'])
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
        reply = self.iface.call('islogined', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))

        if rr.value() is False:
            reply = self.iface.call('getqrpic', 123, 'a1', 456)
            rr = QDBusReply(reply)
            qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
            qrpic64 = rr.value().encode('utf8')   # to bytes
            qrpic = QByteArray.fromBase64(qrpic64)
            self.onQRPicGotten(qrpic)
            
        
        return
    def onStop(self):
        reply = self.iface.call('logout', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        return

    def onRefresh(self):
        reply = self.iface.call('refresh', 'a0', 123, 'a1')
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


