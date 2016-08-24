import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController, Chatroom
from .logiccontroller import LogicController
from .wxcommon import *
from .txmessage import TXMessage

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

    def muc_send_message(self, mto, mbody):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), mto, mbody)

    def muc_number_peers(self, group_number):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number)

    def muc_invite(self, group_number, peer):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), group_number, peer)

    def create_muc2(self, room_ident, title):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rt.funcName(), room_ident, title)


class XmppController(BaseController):
    def __init__(self, rt, parent=None):
        super(XmppController, self).__init__(rt, parent)
        self.relay = XmppRelay()
        self.peerRelay = self.relay
        from .secfg import peer_xmpp_user
        self.relay.peer_user = peer_xmpp_user
        self.initRelay()
        self.relay.xmpp = XmppCallProxy(self)
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(msgo['sender']['channel'])
        from .secfg import peer_xmpp_user
        channel = msgo['sender']['channel']
        self.relay.sendMessage(msgo['params'][0], peer_xmpp_user)
        # self.relay.sendGroupMessage(msgo['params'][0], channel)
        txmsg = TXMessage()
        txmsg.FromUserName = self.peerRelay.self_user
        txmsg.Content = msgo['params'][0]
        self.dispatchGroupChat(channel, txmsg)
        return

    def updateSession(self, msgo):
        qDebug('heree')
        evt = msgo['evt']
        params = msgo['params']
        if evt == 'on_connected': self.relay.on_connected(*params)
        elif evt == 'on_disconnected': self.relay.on_disconnected(*params)
        elif evt == 'on_message': self.relay.on_message(*params)
        elif evt == 'on_muc_message': self.relay.on_muc_message(*params)
        elif evt == 'on_peer_connected': self.relay.on_peer_connected(*params)
        elif evt == 'on_peer_disconnected': self.relay.on_peer_disconnected(*params)
        elif evt == 'on_peer_enter_group': self.relay.on_peer_enter_group(*params)
        else: pass
        return

    def dispatchGroupChat(self, channel, msg):
        groupchat = None
        mkey = channel
        title = '' + channel + channel
        fmtcc = msg.Content

        if mkey in self.txchatmap:
            groupchat = self.txchatmap[mkey]
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.peerRelay.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                self.peerRelay.groupInvite(groupchat.group_number, self.peerRelay.peer_user)
            else:
                self.peerRelay.sendGroupMessage(fmtcc, groupchat.group_number)
        else:
            # TODO 如果是新创建的groupchat，则要等到groupchat可用再发，否则会丢失消息
            groupchat = self.createChatroom(msg, mkey, title)
            groupchat.unsend_queue.append(fmtcc)

        return

    def createChatroom(self, msg, mkey, title):
        group_number = ('WXU.%s' % mkey).lower()
        group_number = mkey
        group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        groupchat.FromUser = msg.FromUser
        groupchat.ToUser = msg.ToUser
        groupchat.FromUserName = msg.FromUserName
        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat
        groupchat.title = title

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat
