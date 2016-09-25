import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController, Chatroom
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

    def groupchatAdd(self):
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
        self.peerRelay = self.relay
        self.initRelay()
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(str(msgo['sender']['channel']))
        from .secfg import peer_tox_user

        self.relay.sendMessage(msgo['params'][0], peer_tox_user)
        self.replyGroupMessage(msgo)
        return

    def replyGroupMessage(self, msgo):
        groupchat = None
        mkey = None
        title = ''

        mkey = msgo['sender']['channel']
        title = "It's title: " + msgo['sender']['channel']
        fmtcc = msgo['params'][0]

        if mkey in self.txchatmap:
            groupchat = self.txchatmap[mkey]

        if groupchat is not None:
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.peerRelay.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                # reinvite peer into group
                self.peerRelay.groupInvite(groupchat.group_number, self.peerRelay.peer_user)
            else:
                self.peerRelay.sendGroupMessage(fmtcc, groupchat.group_number)
        else:
            groupchat = self.createChatroom(msgo, mkey, title)
            groupchat.unsend_queue.append(fmtcc)
            qDebug('groupchat not exists, create it:' + mkey)

        return

    def createChatroom(self, msgo, mkey, title):

        group_number = ('WXU.%s' % mkey).lower()
        group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        # groupchat.FromUser = msg.FromUser
        # groupchat.ToUser = msg.ToUser
        # groupchat.FromUserName = msg.FromUserName
        groupchat.msgo = msgo
        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat
        groupchat.title = title

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat

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

