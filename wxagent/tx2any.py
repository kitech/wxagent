# base web tx im protocol client

import os, sys
import json, re
import enum
import time

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

from .imrelayfactory import IMRelayFactory
from .unimessage import *
from .filestore import QiniuFileStore, VnFileStore

# QDBUS_DEBUG


# 基类，xx2any共用的基础逻辑。
class ToxDispatcher(QObject):
    def __init__(self):
        "docstring"

        return

    # @param msg WXMessage
    def send(self, msg):
        return


class Chatroom():
    def __init__(self):
        "docstring"

        self.group_number = -1
        self.peer_number = -1

        # 以收到消息创建聊天群组时的from/to定义
        self.FromUser = None
        self.ToUser = None

        self.title = ''

        self.unsend_queue = []

        self.chat_type = 0  # CHAT_TYPE_NONE
        self.group_sig = None
        self.Gid = 0
        self.ServiceType = 0

        ### fixme some bugs
        self.FromUserName = ''  # case for newsapp/xxx
        return


#
#
#
class TX2Any(QObject):

    def __init__(self, parent=None):
        "docstring"
        super(TX2Any, self).__init__(parent)

        ##### fill at sub class
        self.agent_service = ''
        self.agent_service_path = ''
        self.agent_service_iface = ''
        self.agent_event_path = ''
        self.agent_event_iface = ''
        self.relay_src_pname = ''

        self.txses = None   # XXSession
        self.peerRelay = None  # IMRelay subclass

        # #### state
        self.qrpic = None  # QByteArray
        self.qrfile = ''
        self.need_send_qrfile = False   # 有可能peerRelay还未上线
        self.need_send_notify = False   # 有可能peerRelay还未上线
        self.notify_buffer = []
        self.tx2relay_msg_buffer = []  # 存储未转发到relay的消息

        self.txchatmap = {}  # Uin => Chatroom
        self.relaychatmap = {}  # group_number => Chatroom

        self.asyncWatchers = {}   # watcher => arg0
        self.sysbus = QDBusConnection.systemBus()
        return

    def initDBus(self):
        if len(self.agent_service) == 0: raise 'need set self.agent_service value.'
        if len(self.agent_service_path) == 0: raise 'need set self.agent_service_path value.'

        if qVersion() >= '5.5':
            self.sysiface = QDBusInterface(self.agent_service, self.agent_service_path,
                                           self.agent_service_iface, self.sysbus)
            self.sysiface.setTimeout(50 * 1000)  # shit for get msg pic
        else:
            self.sysiface = QDBusInterface(self.agent_service, self.agent_service_path, '', self.sysbus)

        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantqqnum', self.onDBusWantQQNum)
        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantverify', self.onDBusWantPasswordAndVerifyCode)
        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'newmessage', self.onDBusNewMessage)

        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'beginlogin', self.onDBusBeginLogin)
        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'gotqrcode', self.onDBusGotQRCode)
        # self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'loginsuccess', self.onDBusLoginSuccess)
        service = self.agent_service
        path = self.agent_event_path
        iface = self.agent_event_iface
        self.sysbus.connect(service, path, iface, 'newmessage', self.onDBusNewMessage)
        self.sysbus.connect(service, path, iface, 'beginlogin', self.onDBusBeginLogin)
        self.sysbus.connect(service, path, iface, 'gotqrcode', self.onDBusGotQRCode)
        self.sysbus.connect(service, path, iface, 'loginsuccess', self.onDBusLoginSuccess)
        return

    def initRelay(self):
        from .secfg import relay_type
        if relay_type is None or relay_type == '' or relay_type not in ('xmpp', 'tox'):
            raise 'relay type not set or invalid relay type. see secfg.py.'
        # relay_type = 'xmpp'
        # relay_type = 'tox'
        self.peerRelay = IMRelayFactory.create(relay_type)
        self.peerRelay.src_pname = self.relay_src_pname

        relay = self.peerRelay
        relay.connected.connect(self.onRelayConnected, Qt.QueuedConnection)
        relay.disconnected.connect(self.onRelayDisconnected, Qt.QueuedConnection)
        relay.newMessage.connect(self.onRelayMessage, Qt.QueuedConnection)

        relay.peerConnected.connect(self.onRelayPeerConnected, Qt.QueuedConnection)
        relay.peerDisconnected.connect(self.onRelayPeerDisconnected, Qt.QueuedConnection)
        relay.newGroupMessage.connect(self.onRelayGroupMessage, Qt.QueuedConnection)
        relay.peerEnterGroup.connect(self.onRelayPeerEnterGroup, Qt.QueuedConnection)
        return

    def onRelayConnected(self):
        qDebug('hehee')

        if self.need_send_qrfile is True and self.peerRelay.isPeerConnected(self.peerRelay.peer_user):
            # from .secfg import peer_xmpp_user
            # url = filestore.upload_file(self.qrpic.data())
            url1 = QiniuFileStore.uploadData(self.qrpic.data())
            url2 = VnFileStore.uploadData(self.qrpic.data())
            url = url1 + "\n" + url2
            rc = self.peerRelay.sendMessage('test qrpic url....' + url,
                                            self.peerRelay.peer_user)
            if rc is not False:
                self.need_send_qrfile = False

        if self.need_send_notify is True and self.peerRelay.isPeerConnected(self.peerRelay.peer_user):
            blen = len(self.notify_buffer)
            while len(self.notify_buffer) > 0:
                notify_msg = self.notify_buffer.pop()
                self.peerRelay.sendMessage(notify_msg, self.peerRelay.peer_user)
                qDebug('send buffered notify msg: %s' % blen)
            self.need_send_notify = False

        return

    def onRelayDisconnected(self):
        qDebug('hehee')
        return

    def onRelayPeerConnected(self):
        qDebug('hehee')

        if self.need_send_qrfile is True and self.peerRelay.isPeerConnected(self.peerRelay.peer_user):
            # from .secfg import peer_xmpp_user
            # url = filestore.upload_file(self.qrpic.data())
            url1 = QiniuFileStore.uploadData(self.qrpic.data())
            url2 = VnFileStore.uploadData(self.qrpic.data())
            url = url1 + "\n" + url2
            rc = self.peerRelay.sendMessage('test qrpic url....' + url, self.peerRelay.peer_user)
            if rc is not False:
                self.need_send_qrfile = False

        # TODO 使用dispatch方式发送消息
        if len(self.tx2relay_msg_buffer) > 0 and self.peerRelay.isPeerConnected(self.peerRelay.peer_user):
            blen = len(self.tx2relay_msg_buffer)
            while len(self.tx2relay_msg_buffer) > 0:
                msg = self.tx2relay_msg_buffer.pop()
                self.peerRelay.sendMessage(msg, self.peerRelay.peer_user)
                # ## TODO 如果发送失败，这条消息可就丢失了。
            qDebug('send buffered wx2tox msg: %s' % blen)
        return

    def onRelayPeerDisconnected(self):
        qDebug('hehee')
        return

    def onRelayPeerEnterGroup(self, group_number):
        qDebug(('hehee:' + group_number).encode())

        qDebug(str(self.relaychatmap.keys()).encode())

        groupchat = self.relaychatmap[group_number]
        qDebug('unsend queue: %s ' % len(groupchat.unsend_queue))

        unsends = groupchat.unsend_queue
        groupchat.unsend_queue = []

        idx = 0
        for fmtcc in unsends:
            # assert groupchat is not None
            rc = self.peerRelay.sendGroupMessage(fmtcc, groupchat.group_number)
            if rc is False:
                qDebug('group chat send msg error:%s, %d' % (str(rc), idx))
                # groupchat.unsend_queue.append(fmtcc)  # 也许是这个函数返回值有问题，即使返回错误也可能发送成功。
            idx += 1

        return

    def onRelayMessage(self, msg):
        qDebug('hehee')
        # 汇总消息好友发送过来的消息当作命令处理
        # getqrcode
        # islogined
        # 等待，总之是wxagent支持的命令，

        self.uicmdHandler(msg)
        self.botcmdHandler(msg)
        return

    # @param msg str
    def uicmdHandler(self, msg):
        # maybe impled in subclass 
        return

    def botcmdHandler(self, msg):
        # maybe impled in subclass 
        return

    def onRelayGroupMessage(self, group_number, message):
        qDebug(('hehee' + str(group_number)).encode())
        groupchat = None
        if group_number in self.relaychatmap:
            groupchat = self.relaychatmap[group_number]
        else:
            qDebug('can not find assoc chatroom')
            return

        qDebug('nextline...')
        print('will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.ToUser.NickName))
        if groupchat.FromUser is not None:
            print('or will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.FromUser.NickName))
        else:
            print('or will send wx msg:%s' % (groupchat.FromUserName))

        peer_number = 'jaoijfiwafaewf'
        # TODO 把从各群组来的发给WX端的消息，同步再发送给tox汇总端一份。也就是tox的唯一peer端。
        # TODO 如果是从wx2tox转过去的消息，这里也会再次收到，所以，会向tox汇总端重复发一份了，需要处理。
        try:
            if peer_number == 0: pass  # it myself sent message, omit
            else:
                self.peerRelay.sendMessage(message, self.peerRelay.peer_user)
        except Exception as ex:
            qDebug('send msg error: %s' % str(ex))

        if peer_number == 0:  # it myself sent message, omit
            pass
        else:
            self.sendMessageToWX(groupchat, message)
        return
