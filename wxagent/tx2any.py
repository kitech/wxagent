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
        self.pendingGroupMessages = {}  # group name => msg

        self.sysbus = QDBusConnection.systemBus()

        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sysbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        #self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logined', self.onDBusLogined)
        #self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logouted', self.onDBusLogouted)

        self.asyncWatchers = {}   # watcher => arg0

        return

    # call from sub class's __init__
    def initBase(self):

        self.initDBus()
        self.initRelay()
        self.startTXBot()
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
        # self.peerRelay.src_pname = 'WQU'
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
            self.peerRelay.sendMessage('test qrpic url....' + url, self.peerRelay.peer_user)
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
            self.peerRelay.sendMessage('test qrpic url....' + url, self.peerRelay.peer_user)
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
        qDebug(b'hehee:' + group_number.encode())

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
        return

    def onRelayGroupMessage(self, group_number, message):
        qDebug(b'hehee' + str(group_number).encode())
        groupchat = None
        if group_number in self.relaychatmap:
            groupchat = self.relaychatmap[group_number]
        else:
            qDebug('can not find assoc chatroom')
            return

        qDebug(('will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.ToUser.NickName)).encode())
        if groupchat.FromUser is not None:
            qDebug(('or will send wx msg:%s,%s' % (groupchat.FromUser.Uin, groupchat.FromUser.NickName)).encode())
        else:
            qDebug(('or will send wx msg:%s' % (groupchat.FromUserName)).encode())

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

    # @param msg str
    def uicmdHandler(self, msg):
        if True: raise 'must impl in sub class'

        if msg[0] != "'":
            qDebug('not a uicmd, normal msg, omit for now.')
            return

        if msg.startswith("'help"):
            friendId = self.peerToxId
            uicmds = ["'help", "'qqnum <num>", "'passwd <pwd[|vfcode]>'", ]
            self.peerRelay.sendMessage("\n".join(uicmds), self.peerRelay.peer_user)
            pass
        elif msg.startswith("'qqnum"):
            qqnum = msg[6:].strip()
            qDebug('the qqnum is:' + str(qqnum))
            self.sendQQNum(qqnum)
            pass
        elif msg.startswith("'passwd"):
            passwd, *vfcode = msg[8:].strip().split('|')
            if len(vfcode) == 0: vfcode.append(4567)
            vfcode = vfcode[0]
            self.sendPasswordAndVerify(passwd, vfcode)
            pass
        else:
            qDebug('unknown uicmd:' + msg[0:120])

        return

    # sub class impl
    def startTXBot(self):
        if True: raise 'must impl in impled'

        # below just sample
        cstate = self.getConnState()
        qDebug('curr conn state:' + str(cstate))

        need_send_notify = False
        notify_msg = ''

        if cstate == CONN_STATE_NONE:
            # do nothing
            qDebug('wait for qqagent bootup...')
            QTimer.singleShot(2345, self.startTXBot)
            pass
        elif cstate == CONN_STATE_WANT_USERNAME:
            need_send_notify = True
            notify_msg = "Input qqnum: ('qqnum <1234567>)"
            pass
        elif cstate == CONN_STATE_WANT_PASSWORD:
            need_send_notify = True
            notify_msg = "Input password: ('passwd <yourpassword>)"
            pass
        elif cstate == CONN_STATE_CONNECTED:
            qDebug('qqagent already logined.')
            self.createWXSession()
            pass
        else:
            qDebug('not possible.')
            pass

        self.startTXBot_extra(need_send_notify, notify_msg)
        return

    def startTXBot_extra(self, need_send_notify, notify_msg):
        if need_send_notify is True:
            # TODO 这里有一个时序问题，有可能self.peerRelay为None，即relay还没有完全启动
            # time.sleep(1)  # hotfix lsself.peerRelay's toxkit is None sometime.
            tkc = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
            if tkc is True:
                self.peerRelay.sendMessage(notify_msg, self.peerRelay.peer_user)
            else:
                self.notify_buffer.append(notify_msg)
                self.need_send_notify = True

        # logined = False
        # if not self.checkWXLogin():
        #     qDebug('wxagent not logined.')
        # else:
        #     logined = True
        #     qDebug('wxagent already logined.')

        # if logined is False:
        #     tkc = False
        #     if self.toxkit is not None:  tkc = self.toxkit.isConnected()
        #     if tkc is True:
        #         friendId = self.peerToxId
        #         self.toxkit.sendMessage(friendId, 'login username:')
        #     else:
        #         self.need_send_request_username = True

        ### 无论是否登陆，启动的都发送一次qrcode文件
        qrpic = self.getQRCode()
        if qrpic is None:
            qDebug('maybe wxagent not run...')
            pass
        else:
            fname = self.genQRCodeSaveFileName()
            self.saveContent(fname, qrpic)

            self.qrpic = qrpic
            self.qrfile = fname

            tkc = False
            tkc = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
            if tkc is True:
                # url = filestore.upload_file(self.qrpic)
                url1 = QiniuFileStore.uploadData(self.qrpic)
                url2 = VnFileStore.uploadData(self.qrpic)
                url = url1 + "\n" + url2
                self.peerRelay.sendMessage('qrcode url:' + url, self.peerRelay.peer_user)
            else:
                self.need_send_qrfile = True

        # if logined is True: self.createWXSession()
        return

    @pyqtSlot(QDBusMessage)
    def onDBusWantQQNum(self, message):
        qDebug(str(message.arguments()))
        self.startTXBot()  # TODO 替换成登陆状态机方法
        return

    # @param a0=needvfc
    # @param a1=vfcpic
    @pyqtSlot(QDBusMessage)
    def onDBusWantPasswordAndVerifyCode(self, message):
        qDebug(str(message.arguments()))

        need_send_notify = False
        notify_msg = ''

        cstate = CONN_STATE_WANT_PASSWORD
        assert(cstate == CONN_STATE_WANT_PASSWORD)

        need_send_notify = True
        notify_msg = "Input password: ('passwd <yourpassword>)"

        if need_send_notify is True:
            tkc = False
            tkc = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
            qDebug(str(tkc))
            if tkc is True:
                self.peerRelay.sendMessage(notify_msg, self.peerRelay.peer_user)
            else:
                self.notify_buffer.append(notify_msg)
                self.need_send_notify = True

        return

    @pyqtSlot(QDBusMessage)
    def onDBusBeginLogin(self, message):
        qDebug(str(message.arguments()))
        # clear smth.
        return

    @pyqtSlot(QDBusMessage)
    def onDBusGotQRCode(self, message):
        qDebug('hereee')
        args = message.arguments()
        # qDebug(str(message.arguments()))
        qrpic64str = args[1]
        qrpic = QByteArray.fromBase64(qrpic64str.encode())

        self.qrpic = qrpic
        fname = self.genQRCodeSaveFileName()
        self.saveContent(fname, qrpic)
        self.qrfile = fname

        tkc = False
        tkc = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
        if tkc is True:
            # url = filestore.upload_file(self.qrpic)
            url1 = QiniuFileStore.uploadData(self.qrpic)
            url2 = VnFileStore.uploadData(self.qrpic)
            url = url1 + "\n" + url2
            self.peerRelay.sendMessage('qrpic url:' + url, self.peerRelay.peer_user)
        else:
            self.need_send_qrfile = True

        return

    @pyqtSlot(QDBusMessage)
    def onDBusLoginSuccess(self, message):
        qDebug(str(message.arguments()))

        self.startTXBot()

        # TODO send success message to UI peer
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

        if self.txses is None: self.createWXSession()

        for arg in args:
            if type(arg) == int:
                qDebug(str(type(arg)) + ',' + str(arg))
            else:
                qDebug(str(type(arg)) + ',' + str(arg)[0:120])

        hcc64_str = args[1]
        hcc64 = hcc64_str.encode()
        hcc = QByteArray.fromBase64(hcc64)

        self.saveContent('qqmsgfromdbus.json', hcc)

        # wxmsgvec = WXMessageList()
        wxmsgvec = self.createMessageList()
        wxmsgvec.setMessage(hcc)

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)

        # temporary send to friend
        # self.toxkit.sendMessage(self.peerToxId, strhcc)

        #############################
        # AddMsgCount = jsobj['AddMsgCount']
        # ModContactCount = jsobj['ModContactCount']

        # grnames = self.wxproto.parseWebSyncNotifyGroups(hcc)
        # self.txses.addGroupNames(grnames)

        # self.txses.parseModContact(jsobj['ModContactList'])

        msgs = wxmsgvec.getContent()
        for msg in msgs:
            fromUser = self.txses.getUserByName(msg.FromUserName)
            toUser = self.txses.getUserByName(msg.ToUserName)
            # qDebug(str(fromUser))
            # qDebug(str(toUser))
            if fromUser is None: qDebug('can not found from user object')
            if toUser is None: qDebug('can not found to user object')
            msg.FromUser = fromUser
            msg.ToUser = toUser

            # hot fix file ack
            # {'value': {'mode': 'send_ack', 'reply_ip': 183597272, 'time': 1444550216, 'type': 101, 'to_uin': 1449732709, 'msg_type': 10, 'session_id': 27932, 'from_uin': 1449732709, 'msg_id': 47636, 'inet_ip': 0, 'msg_id2': 824152}, 'poll_type': 'file_message'}
            if msg.FromUserName == msg.ToUserName:
                qDebug('maybe send_ack msg, but dont known how process it, just omit.')
                continue

            umsg = self.peerRelay.unimsgcls.fromQQMessage(msg, self.txses)
            logstr = umsg.get()
            dlogstr = umsg.dget()
            qDebug(dlogstr.encode())

            self.sendMessageToTox(msg, logstr)

            # this for qq
            if msg.isOffpic():
                qDebug(msg.offpic)
                self.sendShotPicMessageToTox(msg, logstr)
            if msg.isFileMsg():
                qDebug(msg.FileName.encode())
                self.sendFileMessageToTox(msg, logstr)

        return

    def createMessageList(self):
        if True: raise 'must impl in subclass'
        return

    def sendMessageToTox(self, msg, fmtcc):
        fstatus = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
        # qDebug(str(fstatus))
        if fstatus is True:
            try:
                # 把收到的消息发送到汇总tox端
                self.peerRelay.sendMessage(fmtcc, self.peerRelay.peer_user)
            except Exception as ex:
                qDebug(b'tox send msg error: ' + bytes(str(ex), 'utf8'))
            ### dispatch by MsgId
            self.dispatchToToxGroup(msg, fmtcc)
        else:
            # self.tx2relay_msg_buffer.append(msg)
            pass

        return

    def sendShotPicMessageToTox(self, msg, logstr):
        def get_img_reply(data=None):
            if data is None: return
            # url = filestore.upload_file(data)
            url1 = QiniuFileStore.uploadData(data)
            url2 = VnFileStore.uploadData(data)
            url = url1 + "\n" + url2
            umsg = 'pic url: ' + url
            self.sendMessageToTox(msg, umsg)
            return

        self.getMsgImgCallback(msg, get_img_reply)
        return

    def sendFileMessageToTox(self, msg, logstr):
        def get_file_reply(data=None):
            if data is None: return
            if data.data().decode().startswith('{"retcode":102,"errmsg":""}'):
                umsg = 'Get file error: ' + data.data().decode()
                self.sendMessageToTox(msg, umsg)
            else:
                # url = filestore.upload_file(data)
                url1 = QiniuFileStore.uploadData(data)
                url2 = VnFileStore.uploadData(data)
                url = url1 + "\n" + url2
                umsg = 'file url: ' + url
                self.sendMessageToTox(msg, umsg)
            return

        self.getMsgFileCallback(msg, get_file_reply)
        return

    def dispatchToToxGroup(self, msg, fmtcc):
        if True: raise 'must impl in sub class'

        if msg.FromUserName == 'newsapp':
            qDebug('special chat: newsapp')
            self.dispatchNewsappChatToTox(msg, fmtcc)
            pass
        elif msg.ToUserName == 'filehelper' or msg.FromUserName == 'filehelper':
            qDebug('special chat: filehelper')
            self.dispatchFileHelperChatToTox(msg, fmtcc)
            pass
        elif msg.PollType == QQ_PT_SESSION:
            qDebug('qq sess chat')
            self.dispatchQQSessChatToTox(msg, fmtcc)
            pass
        elif msg.FromUser.UserType == UT_GROUP or msg.ToUser.UserType == UT_GROUP:
            # msg.ToUserName.startswith('@@') or msg.FromUserName.startswith('@@'):
            qDebug('wx group chat:')
            # wx group chat
            self.dispatchWXGroupChatToTox(msg, fmtcc)
            pass
        else:
            qDebug('u2u group chat:')
            # user <=> user
            self.dispatchU2UChatToTox(msg, fmtcc)
            pass

        return

    def dispatchNewsappChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        mkey = 'newsapp'
        title = 'newsapp@WQU'

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
            groupchat = self.createChatroom(msg, mkey, title)
            groupchat.unsend_queue.append(fmtcc)

        return

    def dispatchFileHelperChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        if msg.FromUserName == 'filehelper':
            mkey = msg.FromUser.Uin
            title = '%s@WQU' % msg.FromUser.NickName
        else:
            mkey = msg.ToUser.Uin
            title = '%s@WQU' % msg.ToUser.NickName

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
            groupchat = self.createChatroom(msg, mkey, title)
            groupchat.unsend_queue.append(fmtcc)

        return

    def dispatchWXGroupChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        # TODO 这段代码好烂，在外层直接用的变量，到内层又检测是否为None，晕了
        if msg.FromUser.UserType == UT_GROUP:
            if msg.FromUser is None:
                # message pending and try get group info
                qDebug('warning FromUser not found, wxgroup not found:' + msg.FromUserName)
                if msg.FromUserName in self.pendingGroupMessages:
                    self.pendingGroupMessages[msg.FromUserName].append([msg,fmtcc])
                else:
                    self.pendingGroupMessages[msg.ToUserName] = list()
                    self.pendingGroupMessages[msg.ToUserName].append([msg,fmtcc])

                # QTimer.singleShot(1, self.getBatchGroupAll)
                return
            else:
                mkey = msg.FromUser.Uin
                title = '%s@WQU' % msg.FromUser.NickName
                if len(msg.FromUser.NickName) == 0:
                    qDebug('maybe a temp group and without nickname')
                    title = 'TGC%s@WQU' % msg.FromUser.Uin
        else:
            if msg.ToUser is None:
                qDebug('warning ToUser not found, wxgroup not found:' + msg.ToUserName)
                if msg.FromUserName in self.pendingGroupMessages:
                    self.pendingGroupMessages[msg.ToUserName].append([msg,fmtcc])
                else:
                    self.pendingGroupMessages[msg.ToUserName] = list()
                    self.pendingGroupMessages[msg.ToUserName].append([msg,fmtcc])

                # QTimer.singleShot(1, self.getBatchGroupAll)
                return
            else:
                mkey = msg.ToUser.Uin
                title = '%s@WQU' % msg.ToUser.NickName
                if len(msg.ToUser.NickName) == 0:
                    qDebug('maybe a temp group and without nickname')
                    title = 'TGC%s@WQU' % msg.ToUser.Uin

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

    def dispatchWXGroupChatToTox2(self, msg, fmtcc, GroupUser):
        if msg.FromUser is None: msg.FromUser = GroupUser
        elif msg.ToUser is None: msg.ToUser = GroupUser
        else: qDebug('wtf???...')

        self.dispatchWXGroupChatToTox(msg, fmtcc)
        return

    def dispatchQQSessChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        # 如果来源User没有找到，则尝试新请求获取group_sig，则首先获取临时会话的peer用户信息
        # 如果来源User没有找到，则尝试新请求获取好友信息
        to_uin = None
        if msg.FromUser is None:
            to_uin = msg.FromUserName
        elif msg.ToUser is None:
            to_uin = msg.ToUserName
        else:
            pass

        if to_uin is not None:
            pcall = self.sysiface.asyncCall('getfriendinfo', to_uin, 'a0', 123, 'a1')
            watcher = QDBusPendingCallWatcher(pcall)
            watcher.finished.connect(self.onGetFriendInfoDone)
            self.asyncWatchers[watcher] = [msg, fmtcc]
            return

        mkey = msg.ToUser.Uin
        title = '%s@WQU' % msg.ToUser.NickName
        if len(msg.ToUser.NickName) == 0:
            qDebug('maybe a temp group and without nickname')
            title = 'TGC%s@WQU' % msg.ToUser.Uin

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

    def dispatchU2UChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        # 两个用户，正反向通信，使用同一个groupchat，但需要找到它
        if msg.FromUser.Uin == self.txses.me.Uin:
            mkey = msg.ToUser.Uin
            title = '%s@WQU' % msg.ToUser.NickName
        else:
            mkey = msg.FromUser.Uin
            title = '%s@WQU' % msg.FromUser.NickName

        # TODO 可能有一个计算交集的函数吧
        if mkey in self.txchatmap:
            groupchat = self.txchatmap[mkey]

        if groupchat is not None:
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
            groupchat = self.createChatroom(msg, mkey, title)
            groupchat.unsend_queue.append(fmtcc)

        return

    def createChatroom(self, msg, mkey, title):

        group_number = ('%s.%s' % (self.relaychatmap, mkey)).lower()
        group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        groupchat.FromUser = msg.FromUser
        groupchat.ToUser = msg.ToUser
        groupchat.FromUserName = msg.FromUserName
        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat
        groupchat.title = title

        self.createChatroom_set_extra(msg, mkey, title, groupchat)

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat

    def createChatroom_set_extra(self, msg, mkey, title, groupchat):
        if True: raise 'must impl in subclass'
        return

    def sendMessageToWX(self, groupchat, mcc):
        qDebug('here')

        FromUser = groupchat.FromUser
        ToUser = groupchat.ToUser

        if ToUser.UserName == 'filehelper' or FromUser.UserName == 'filehelper':
            qDebug('send special chat: filehelper')
            self.sendFileHelperMessageToWX(groupchat, mcc)
            pass
        elif groupchat.chat_type == CHAT_TYPE_QUN:
            qDebug('send wx group chat:')
            # wx group chat
            self.sendWXGroupChatMessageToWX(groupchat, mcc)
            pass
        elif groupchat.chat_type == CHAT_TYPE_DISCUS:
            qDebug('send wx discus chat:')
            # wx discus chat
            self.sendWXDiscusChatMessageToWX(groupchat, mcc)
            pass
        elif groupchat.chat_type == CHAT_TYPE_SESS:
            qDebug('send wx sess chat:')
            # wx sess chat
            self.sendWXSessionChatMessageToWX(groupchat, mcc)
            pass
        elif groupchat.chat_type == CHAT_TYPE_U2U:
            qDebug('send wx u2u chat:')
            # user <=> user
            self.sendU2UMessageToWX(groupchat, mcc)
            pass
        elif ToUser.UserType == UT_GROUP or FromUser.UserType == UT_GROUP:
            qDebug('send wx group chat:')
            # wx group chat
            self.sendWXGroupChatMessageToWX(groupchat, mcc)
            pass
        elif ToUser.UserType == UT_DISCUS or FromUser.UserType == UT_DISCUS:
            qDebug('send wx discus chat:')
            # wx group chat
            self.sendWXDiscusChatMessageToWX(groupchat, mcc)
            pass
        else:
            qDebug('unknown chat:')
            pass

        # TODO 把从各群组来的发给WX端的消息，再发送给tox汇总端一份。

        if True: return
        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName
        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('sendmessage', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def sendFileHelperMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        qDebug('cc type:, ' + str(type(mcc)))
        qDebug('cc len:, ' + str(len(mcc)))

        try:
            mcc_u8 = mcc.decode('utf8')
            mcc_u16 = mcc_u8.encode('utf16')

            qDebug(mcc_u16)
        except Exception as ex:
            qDebug('str as u8 => u16 error')

        try:
            mcc_u16 = mcc.decode('utf16')
            mcc_u8 = mcc_u16.encode('utf8')

            qDebug(mcc_u8)
        except Exception as ex:
            qDebug('str as u16 => u8 error')

        try:
            qDebug(mcc)
        except Exception as ex:
            qDebug('str as u8 error')

        try:
            bcc = bytes(mcc, 'utf8')
            qDebug(bcc)
        except Exception as ex:
            qDebug('str as bytes u8 error')

        try:
            bcc = bytes(mcc, 'utf8')
            qdebug(bcc)
        except Exception as ex:
            qDebug('str as bytes u8 error')

        # return
        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('sendmessage', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def sendWXGroupChatMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName
        group_code = groupchat.ToUser.Uin

        args = [to_username, from_username, mcc, group_code, 1, 'more', 'even more']
        reply = self.sysiface.call('send_qun_msg', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def sendWXDiscusChatMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        args = [to_username, from_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('send_discus_msg', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def sendWXSessionChatMessageToWX(self, groupchat, mcc):
        def on_dbus_reply(watcher):
            groupchat, mcc = self.asyncWatchers[watcher]

            pendReply = QDBusPendingReply(watcher)
            message = pendReply.reply()
            args = message.arguments()
            qDebug(str(args))

            # #####
            hcc = args[0]  # QByteArray
            strhcc = self.hcc2str(hcc)
            hccjs = json.JSONDecoder().decode(strhcc)
            print('group sig', ':::', strhcc)

            groupchat.group_sig = hccjs['result']['value']

            self.sendWXSessionChatMessageToWX(groupchat, mcc)
            self.asyncWatchers.pop(watcher)
            return

        # get group sig if None
        if groupchat.group_sig is None:
            gid = groupchat.Gid
            tuin = groupchat.FromUser.UserName  # 也有可能是ToUser.UserName
            service_type = groupchat.ServiceType
            pcall = self.sysiface.asyncCall('get_c2cmsg_sig', gid, tuin, service_type, 'a0', 123, 'a1')
            watcher = QDBusPendingCallWatcher(pcall)
            watcher.finished.connect(on_dbus_reply, Qt.QueuedConnection)
            self.asyncWatchers[watcher] = [groupchat, mcc]

        # ##########

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName
        group_sig = groupchat.group_sig

        args = [to_username, from_username, mcc, group_sig, 1, 'more', 'even more']
        reply = self.sysiface.call('send_sess_msg', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def sendU2UMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        args = [to_username, from_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('send_buddy_msg', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        ### TODO send message faild

        return

    def createWXSession(self):
        if True: raise 'must impl in sub class'

        if self.txses is not None:
            return

        self.txses = WXSession()

        reply = self.sysiface.call('getselfinfo', 123, 'a1', 456)
        rr = QDBusReply(reply)
        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode()   # to bytes
        data = QByteArray.fromBase64(data64)
        self.txses.setSelfInfo(data)
        self.saveContent('selfinfo.json', data)

        pcall = self.sysiface.asyncCall('getuserfriends', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone, Qt.QueuedConnection)
        self.asyncWatchers[watcher] = 'getuserfriends'

        pcall = self.sysiface.asyncCall('getgroupnamelist', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone, Qt.QueuedConnection)
        self.asyncWatchers[watcher] = 'getgroupnamelist'

        pcall = self.sysiface.asyncCall('getdiscuslist', 'a0', 123, 'a1')
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.onGetContactDone, Qt.QueuedConnection)
        self.asyncWatchers[watcher] = 'getdiscuslist'

        # pcall = self.sysiface.asyncCall('getonlinebuddies', 'a0', 123, 'a1')
        # watcher = QDBusPendingCallWatcher(pcall)
        # watcher.finished.connect(self.onGetContactDone)
        # self.asyncWatchers[watcher] = 'getgrouponlinebuddies'

        # pcall = self.sysiface.asyncCall('getrecentlist', 'a0', 123, 'a1')
        # watcher = QDBusPendingCallWatcher(pcall)
        # watcher.finished.connect(self.onGetContactDone)
        # self.asyncWatchers[watcher] = 'getrecentlist'

        # reply = self.sysiface.call('getinitdata', 123, 'a1', 456)
        # rr = QDBusReply(reply)
        # # TODO check reply valid

        # qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        # data64 = rr.value().encode('utf8')   # to bytes
        # data = QByteArray.fromBase64(data64)
        # self.txses.setInitData(data)
        # self.saveContent('initdata.json', data)

        # reply = self.sysiface.call('getcontact', 123, 'a1', 456)
        # rr = QDBusReply(reply)

        # # TODO check reply valid
        # qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        # data64 = rr.value().encode('utf8')   # to bytes
        # data = QByteArray.fromBase64(data64)
        # self.txses.setContact(data)
        # self.saveContent('contact.json', data)


        # reply = self.sysiface.call('getgroups', 123, 'a1', 456)
        # rr = QDBusReply(reply)

        # # TODO check reply valid
        # qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        # GroupNames = json.JSONDecoder().decode(rr.value())

        # self.txses.addGroupNames(GroupNames)

        # # QTimer.singleShot(8, self.getBatchContactAll)
        # QTimer.singleShot(8, self.getBatchGroupAll)

        return

    def checkWXLogin(self):
        reply = self.sysiface.call('islogined', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)

        if not rr.isValid(): return False
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        if rr.value() is False:
            return False

        return True

    def getConnState(self):
        if True: raise 'must impl in subclass'
        reply = self.sysiface.call('connstate', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))

        return rr.value()

    def getQRCode(self):
        reply = self.sysiface.call('getqrpic', 123, 'a1', 456)
        rr = QDBusReply(reply)

        if not rr.isValid(): return None

        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        qrpic64 = rr.value().encode('utf8')   # to bytes
        qrpic = QByteArray.fromBase64(qrpic64)

        return qrpic

    def genQRCodeSaveFileName(self):
        now = QDateTime.currentDateTime()
        fname = '/tmp/wxqrcode_%s.jpg' % now.toString('yyyyMMddHHmmsszzz')
        return fname

    def getBaseFileName(self, fname):
        bfname = QFileInfo(fname).fileName()
        return bfname

    # @param cb(data)
    def getMsgImgCallback(self, msg, imgcb=None):

        def on_dbus_reply(watcher):
            qDebug('replyyyyyyyyyyyyyyy')
            pendReply = QDBusPendingReply(watcher)
            qDebug(str(watcher))
            qDebug(str(pendReply.isValid()))
            if pendReply.isValid():
                hcc = pendReply.argumentAt(0)
                qDebug(str(type(hcc)))
            else:
                self.asyncWatchers.pop(watcher)
                if imgcb is not None: imgcb(None)
                return

            message = pendReply.reply()
            args = message.arguments()

            self.asyncWatchers.pop(watcher)
            # send img file to tox client
            if imgcb is not None: imgcb(args[0])

            return

        # 还有可能超时，dbus默认timeout=25，而实现有可能达到45秒。WTF!!!
        args = [msg.offpic, msg.FromUserName]
        offpic_file_path = msg.offpic.replace('/', '%2F')
        args = [offpic_file_path, msg.FromUserName]
        pcall = self.sysiface.asyncCall('get_msg_img', *args) 
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(on_dbus_reply)
        self.asyncWatchers[watcher] = '1'

        return

    def getMsgImgUrl(self, msg):
        args = [msg.MsgId, False]
        return self.syncGetRpc('get_msg_img_url', *args)

    # @param cb(data)
    def getMsgFileCallback(self, msg, imgcb=None):

        def on_dbus_reply(watcher):
            qDebug('replyyyyyyyyyyyyyyy')
            pendReply = QDBusPendingReply(watcher)
            qDebug(str(watcher))
            qDebug(str(pendReply.isValid()))
            if pendReply.isValid():
                hcc = pendReply.argumentAt(0)
                qDebug(str(type(hcc)))
            else:
                self.asyncWatchers.pop(watcher)
                if imgcb is not None: imgcb(None)
                return

            message = pendReply.reply()
            args = message.arguments()

            self.asyncWatchers.pop(watcher)
            # send img file to tox client
            if imgcb is not None: imgcb(args[0])

            return

        # 还有可能超时，dbus默认timeout=25，而实现有可能达到45秒。WTF!!!
        # TODO, msg.FileName maybe need urlencoded
        args = [msg.MsgId, msg.FileName, msg.ToUserName]
        pcall = self.sysiface.asyncCall('get_msg_file', *args) 
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(on_dbus_reply)
        self.asyncWatchers[watcher] = '1'

        return

    # @param hcc QByteArray
    # @return str
    def hcc2str(self, hcc):
        strhcc = ''

        try:
            astr = hcc.data().decode('gkb')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode gbk error:')

        try:
            astr = hcc.data().decode('utf16')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf16 error:')

        try:
            astr = hcc.data().decode('utf8')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
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
