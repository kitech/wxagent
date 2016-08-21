import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController
from .wxcommon import *

from .toxrelay import ToxRelay


class ToxCallProxy(QObject):
    def __init__(self, ctrl, parent=None):
        super(ToxCallProxy, self).__init__(parent)
        self.ctrl = ctrl
        return

    def friendExists(self, friendId):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), friendId)

    def friendAdd(self, friendId, addMsg):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), friendId, addMsg)

    def sendMessage(self, peer, msg):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), peer, msg)

    def groupchatSendMessage(self, group_number, msg):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number, msg)

    def selfGetConnectionStatus(self):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName())

    def friendGetConnectionStatus(self, peer):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), peer)

    def groupAdd(self):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName())

    def groupchatSetTitle(self, group_number, title):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number, title)

    def groupchatInviteFriend(self, group_number, peer):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number, peer)

    def groupNumberPeers(self, group_number):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number)


class ToxController(BaseController):
    def __init__(self, rt, parent=None):
        super(ToxController, self).__init__(rt, parent)
        self.relay = ToxRelay()
        self.relay.toxkit = ToxCallProxy(self)
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(msgo['sender']['channel'])
        from .secfg import peer_tox_user

        self.relay.sendMessage(msgo['params'][0], peer_tox_user)
        return

    def ifaceForName(self, name):
        name = name.replace('Controller', 'Agent')
        service_name = WXAGENT_SERVICE_NAME + '.' + name
        service_path = WXAGENT_SERVICE_PATH + '/' + name
        service_iface = WXAGENT_SERVICE_IFACE + '.' + name

        iface = QDBusInterface(service_name, service_path,
                               service_iface, self.rt.sysbus)
        return iface

    def remoteCall(self, func, *argv):
        iface = self.ifaceForName(self.__class__.__name__)
        reply = iface.call('rcall', func, *argv)
        rr = QDBusReply(reply)
        if not rr.isValid():
            qDebug('error: {}, {}', rr.error().name(), rr.error().message())
        else:
            ret = json.JSONDecoder().decode(rr.value())
            return rr.value()
        return

    def updateSession(self, msgo):
        qDebug('heree')
        evt = msgo['evt']
        params = msgo['params']
        if evt == 'onToxnetConnectStatus': self.relay.onToxnetConnectStatus(*params)
        elif evt == 'onToxnetFriendStatus': self.relay.onToxnetFriendStatus(*params)
        elif evt == 'onToxnetGroupMessage': self.relay.onToxnetGroupMessage(*params)
        elif evt == 'onToxnetGroupNamelistChanged': self.relay.onToxnetGroupNamelistChanged(*params)
        elif evt == 'onToxnetMessage': self.relay.onToxnetMessage(*params)
        else: pass
        return

