import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController
from .wxcommon import *

from .xmpprelay import XmppRelay


class XmppCallProxy(QObject):
    def __init__(self, ctrl, parent=None):
        super(XmppCallProxy, self).__init__(parent)
        self.ctrl = ctrl
        return

    def friendExists(self, friendId):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), friendId)

    def send_message(self, mto, mbody):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), mto, mbody)
        return


class XmppController(BaseController):
    def __init__(self, rt, parent=None):
        super(XmppController, self).__init__(rt, parent)
        self.relay = XmppRelay()
        self.relay.xmpp = XmppCallProxy(self)
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(msgo['sender']['channel'])
        from .secfg import peer_xmpp_user

        self.relay.sendMessage(msgo['params'][0], peer_xmpp_user)
        return

    def updateSession(self, msgo):
        qDebug('heree')
        evt = msgo['evt']
        params = msgo['params']
        if evt == 'on_connected': self.relay.on_connected(*params)
        elif evt == 'on_disconnected': self.relay.on_disconnected(*params)
        elif evt == 'on_message': self.relay.on_message(*params)
        elif evt == 'on_muc_message': self.relay.on_muc_message(*params)
        else: pass
        return

