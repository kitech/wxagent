import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController
from .wxcommon import *

from .imrelay import IMRelay


class IRCCallProxy(QObject):
    def __init__(self, ctrl, parent=None):
        super(IRCCallProxy, self).__init__(parent)
        self.ctrl = ctrl
        return

    def friendExists(self, friendId):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), friendId)

    def sendMessage(self, msg):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), msg)
        return

    def sendGroupMessage(self, msg, group):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), msg, group)
        return


class IRCController(BaseController):
    def __init__(self, rt, parent=None):
        super(IRCController, self).__init__(rt, parent)
        self.relay = IRCRelay()
        self.relay.xmpp = IRCCallProxy(self)
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(str(msgo['context']['channel']))
        # from .secfg import peer_xmpp_user

        msg = 'hehehheeeee'
        msg = str(msgo)
        self.relay.sendGroupMessage(msg, 'grouppppp')
        # self.relay.sendMessage(msgo['params'][0], peer_xmpp_user)
        return

    def updateSession(self, msgo):
        qDebug('heree')
        evt = msgo['evt']
        params = msgo['params']
        if evt == 'onIRCConnected': self.relay.onIRCConnected()
        elif evt == 'onIRCDisconnected': self.relay.onIRCDisconnected()
        elif evt == 'onIRCNewMessage': self.relay.onIRCNewMessage(*params)
        else: pass
        return

    def fillContext(self, msgo):
        msgtxt = str(msgo)
        qDebug(msgtxt.encode())
        # msgo['context'] = {
        #    'channel': msgo['channel'],
        # }
        return msgo


class IRCRelay(IMRelay):
    def __init__(self, parent=None):
        super(IRCRelay, self).__init__(parent)
        return

    # ######################
    def onIRCConnected(self):
        qDebug('hrerere')
        return

    def onIRCDisconnected(self):
        qDebug('hrerere')
        return

    def onIRCNewMessage(self, msg):
        qDebug(msg[0:32].encode())
        return

    def sendMessage(self, msg):
        self.xmpp.sendMessage(msg)
        return

    def sendGroupMessage(self, msg, group):
        self.xmpp.sendGroupMessage(msg, group)
        return
