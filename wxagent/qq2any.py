# web qq protocol

import os, sys
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

import wxagent.filestore as filestore
from .imrelayfactory import IMRelayFactory
from .qqcom import *
from .qqsession import *
from .wxprotocol import *

# QDBUS_DEBUG


class ToxDispatcher(QObject):
    def __init__(self):
        "docstring"

        return

    # @param msg WXMessage
    def send(self, msg):
        return


CHAT_TYPE_NONE = 0
CHAT_TYPE_U2U = 1
CHAT_TYPE_QUN = 2
CHAT_TYPE_DISCUS = 3
CHAT_TYPE_SESS = 4


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

        self.chat_type = CHAT_TYPE_NONE
        self.group_sig = None
        self.Gid = 0
        self.ServiceType = 0

        ### fix some bugs
        self.FromUserName = ''  # case for newsapp/xxx
        return


#
#
#
class WX2Tox(QObject):

    def __init__(self, parent = None):
        "docstring"
        super(WX2Tox, self).__init__(parent)

        self.wxses = None
        self.toxkit = None
        self.peerToxId = '398C8161D038FD328A573FFAA0F5FAAF7FFDE5E8B4350E7D15E6AFD0B993FC529FA90C343627'

        self.peerRelay = None


        # #### state
        self.qrpic = None  # QByteArray
        self.qrfile = ''
        self.need_send_qrfile = False   # 有可能toxkit还未上线
        self.need_send_notify = False   # 有可能toxkit还未上线
        self.notify_buffer = []
        self.wx2tox_msg_buffer = []  # 存储未转发到tox的消息
        self.tox2wx_msg_buffer = []

        self.wxchatmap = {}  # Uin => Chatroom
        self.toxchatmap = {}  # group_number => Chatroom
        self.wxproto = WXProtocol()
        self.pendingGroupMessages = {}  # group name => msg

        #####
        self.sysbus = QDBusConnection.systemBus()
        self.sysiface = QDBusInterface(QQAGENT_SERVICE_NAME, '/io/qtc/qqagent', QQAGENT_IFACE_NAME, self.sysbus)

        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sysbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        #self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logined', self.onDBusLogined)
        #self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'logouted', self.onDBusLogouted)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantqqnum', self.onDBusWantQQNum)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'wantverify', self.onDBusWantPasswordAndVerifyCode)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'newmessage', self.onDBusNewMessage)

        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'beginlogin', self.onDBusBeginLogin)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'gotqrcode', self.onDBusGotQRCode)
        self.sysbus.connect(QQAGENT_SERVICE_NAME, "/io/qtc/qqagent/signals", 'io.qtc.qqagent.signals', 'loginsuccess', self.onDBusLoginSuccess)

        self.asyncWatchers = {}   # watcher => arg0

        self.initRelay()
        # self.initToxnet()
        self.startWXBot()
        return

    def initRelay(self):
        self.peerRelay = IMRelayFactory.create('xmpp')

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

        if self.need_send_qrfile is True:
            # from .secfg import peer_xmpp_user
            url = filestore.upload_file(self.qrpic.data())
            self.peerRelay.sendMessage('test qrpic url....' + url,
                                       self.peerRelay.peer_user)
            self.need_send_qrfile = False

        if self.need_send_notify is True:
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
        # TODO 使用dispatch方式发送消息
        if len(self.wx2tox_msg_buffer) > 0:
            blen = len(self.wx2tox_msg_buffer)
            while len(self.wx2tox_msg_buffer) > 0:
                msg = self.wx2tox_msg_buffer.pop()
                self.peerRelay.sendMessage(msg, self.peerRelay.peer_user)
                # ## TODO 如果发送失败，这条消息可就丢失了。
            qDebug('send buffered wx2tox msg: %s' % blen)
        return

    def onRelayPeerDisconnected(self):
        qDebug('hehee')
        return

    def onRelayPeerEnterGroup(self):
        qDebug('hehee')
        return

    def onRelayMessage(self, msg):
        qDebug('hehee')
        # 汇总消息好友发送过来的消息当作命令处理
        # getqrcode
        # islogined
        # 等待，总之是wxagent支持的命令，

        self.uicmdHandler(msg)
        return

    def onRelayGroupMessage(self):
        qDebug('hehee')
        return

    def onToxnetConnectStatus(self, status):
        qDebug(str(status))
        friendId = self.peerToxId
        fexists = self.toxkit.friendExists(friendId)
        qDebug(str(fexists))

        famsg = 'from qq2tox...'
        if not fexists:
            friend_number = self.toxkit.friendAdd(friendId, famsg)
            qDebug(str(friend_number))
        else:
            # rc = self.toxkit.friendDelete(friendId)
            # qDebug(str(rc))
            try:
                True
                # friend_number = self.toxkit.friendAddNorequest(friendId)
                # qDebug(str(friend_number))
            except Exception as ex:
                pass
            # self.toxkit.friendAddNorequest(friendId)
            pass

        return

    def onToxnetMessage(self, friendId, msgtype, msg):
        qDebug(friendId + ':' + str(msgtype) + '=' + str(len(msg)))

        # 汇总消息好友发送过来的消息当作命令处理
        # getqrcode
        # islogined
        # 等待，总之是wxagent支持的命令，

        self.uicmdHandler(msg)

        return

    def onToxnetFriendStatus(self, friendId, status):
        qDebug(friendId + ':' + str(status))

        if status > 0 and self.need_send_notify is True:
            blen = len(self.notify_buffer)
            while len(self.notify_buffer) > 0:
                notify_msg = self.notify_buffer.pop()
                self.toxkit.sendMessage(self.peerToxId, notify_msg)
                qDebug('send buffered notify msg: %s' % blen)
            self.need_send_notify = False

        if status > 0 and len(self.wx2tox_msg_buffer) > 0:
            blen = len(self.wx2tox_msg_buffer)
            while len(self.wx2tox_msg_buffer) > 0:
                msg = self.wx2tox_msg_buffer.pop()
                mid = self.toxkit.sendMessage(self.peerToxId, msg)
                # ## TODO 如果发送失败，这条消息可就丢失了。
            qDebug('send buffered wx2tox msg: %s' % blen)

        return

    def onToxnetFileChunkReuqest(self, friendId, file_number, position, length):
        if qrand() % 7 == 1:
            qDebug('fn=%s,pos=%s,len=%s' % (file_number, position, length))

        if position >= len(self.qrpic):
            qDebug('warning exceed file size: finished.')
            # self.toxkit.fileControl(friendId, file_number, 2)  # CANCEL
            return

        chunk = self.qrpic[position:(position + length)]
        self.toxkit.fileSendChunk(friendId, file_number, position, chunk)
        return

    def onToxnetFileRecvControl(self, friendId, file_number, control):
        qDebug('fn=%s,ctl=%s,' % (file_number, control))

        return

    def onToxnetGroupMessage(self, group_number, peer_number, message):
        qDebug('nextline...')
        print('gn=%s,pn=%s,mlen=%s,mp=%s' % (group_number, peer_number, len(message), message[0:27]))

        groupchat = None
        if group_number in self.toxchatmap:
            groupchat = self.toxchatmap[group_number]
        else:
            qDebug('can not find assoc chatroom')
            return

        qDebug('nextline...')
        print('will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.ToUser.NickName))
        if groupchat.FromUser is not None:
            print('or will send wx msg:%s,%s' % (groupchat.FromUser.Uin, groupchat.FromUser.NickName))
        else:
            print('or will send wx msg:%s' % (groupchat.FromUserName))

        if peer_number == 0:  # it myself sent message, omit
            pass
        else:
            self.sendMessageToWX(groupchat, message)

        # TODO 把从各群组来的发给WX端的消息，同步再发送给tox汇总端一份。也就是tox的唯一peer端。
        # TODO 如果是从wx2tox转过去的消息，这里也会再次收到，所以，会向tox汇总端重复发一份了，需要处理。
        try:
            if peer_number == 0: pass  # it myself sent message, omit
            else: mid = self.toxkit.sendMessage(self.peerToxId, message)
        except Exception as ex:
            qDebug('send msg error: %s' % str(ex))

        return

    def onToxnetGroupNamelistChanged(self, group_number, peer_number, change):
        qDebug(str(change))

        # TODO group number count == 2
        number_peers = self.toxkit.groupNumberPeers(group_number)
        if number_peers == 0:
            qDebug('why 0?')
        elif number_peers == 1:
            qDebug('myself added')
        elif number_peers == 2:
            qDebug('toxpeer added')
        else:
            qDebug('wtf?')

        qDebug('np: %d' % number_peers)
        if number_peers != 2: return

        groupchat = self.toxchatmap[group_number]
        qDebug('unsend queue: %s ' % len(groupchat.unsend_queue))

        unsends = groupchat.unsend_queue
        groupchat.unsend_queue = []

        idx = 0
        for fmtcc in unsends:
            # assert groupchat is not None
            rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
            if rc != 0:
                qDebug('group chat send msg error:%s, %d' % (str(rc), idx))
                # groupchat.unsend_queue.append(fmtcc)  # 也许是这个函数返回值有问题，即使返回错误也可能发送成功。
            idx += 1

        return

    # @param msg str
    def uicmdHandler(self, msg):

        if msg[0] != "'":
            qDebug('not a uicmd, normal msg, omit for now.')
            return

        if msg.startswith("'help"):
            friendId = self.peerToxId
            uicmds = ["'help", "'qqnum <num>", "'passwd <pwd[|vfcode]>'", ]
            self.toxkit.sendMessage(friendId, "\n".join(uicmds))
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

    def startWXBot(self):

        cstate = self.getConnState()
        qDebug('curr conn state:' + str(cstate))

        need_send_notify = False
        notify_msg = ''

        if cstate == CONN_STATE_NONE:
            # do nothing
            qDebug('wait for qqagent bootup...')
            QTimer.singleShot(2345, self.startWXBot)
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

        if need_send_notify is True:
            tkc = self.peerRelay.isConnected()
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
            tkc = self.peerRelay.isConnected()
            if tkc is True:
                url = filestore.upload_file(self.qrpic)
                self.peerRelay.sendMessage('qrcode url:' + url,
                                           self.peerRelay.peer_user)
            else:
                self.need_send_qrfile = True

        # if logined is True: self.createWXSession()
        return

    @pyqtSlot(QDBusMessage)
    def onDBusWantQQNum(self, message):
        qDebug(str(message.arguments()))
        self.startWXBot()  # TODO 替换成登陆状态机方法
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
            tkc = self.peerRelay.isConnected()
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
        tkc = self.peerRelay.isConnected()
        if tkc is True:
            url = filestore.upload_file(self.qrpic)
            self.peerRelay.sendMessage('qrpic url:' + url,
                                       self.peerRelay.peer_user)
        else:
            self.need_send_qrfile = True

        return

    @pyqtSlot(QDBusMessage)
    def onDBusLoginSuccess(self, message):
        qDebug(str(message.arguments()))

        self.startWXBot()

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

        if self.wxses is None: self.createWXSession()

        for arg in args:
            if type(arg) == int:
                qDebug(str(type(arg)) + ',' + str(arg))
            else:
                qDebug(str(type(arg)) + ',' + str(arg)[0:120])

        hcc64_str = args[1]
        hcc64 = hcc64_str.encode('utf8')
        hcc = QByteArray.fromBase64(hcc64)

        self.saveContent('qqmsgfromdbus.json', hcc)

        wxmsgvec = WXMessageList()
        wxmsgvec.setMessage(hcc)

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)

        # temporary send to friend
        # self.toxkit.sendMessage(self.peerToxId, strhcc)

        #############################
        # AddMsgCount = jsobj['AddMsgCount']
        # ModContactCount = jsobj['ModContactCount']

        # grnames = self.wxproto.parseWebSyncNotifyGroups(hcc)
        # self.wxses.addGroupNames(grnames)

        # self.wxses.parseModContact(jsobj['ModContactList'])

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

            msg.FromUser = fromUser
            msg.ToUser = toUser
            content = msg.UnescapedContent

            # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
            # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
            reg = r'^(@[0-9a-f]+):<br/>'
            mats = re.findall(reg, content)
            if len(mats) > 0:
                qDebug(str(mats).encode())
                UserName = mats[0]
                UserInfo = self.wxses.getUserInfo(UserName)
                qDebug(str(UserInfo).encode())
                if UserInfo is not None:
                    dispRealName = UserInfo.NickName + UserName
                    content = content.replace(UserName, dispRealName, 1)

            # for eyes
            dispFromUserName = msg.FromUserName
            dispToUserName = msg.ToUserName

            logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                     (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                      dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

            logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                     (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                      dispToUserName, toUser_NickName, msg.MsgId, content)

            self.sendMessageToTox(msg, logstr)

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
            # self.wx2tox_msg_buffer.append(msg)
            pass

        return

    def dispatchToToxGroup(self, msg, fmtcc):

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

        # if msg.FromUser.Uin in self.wxchatmap:
        #     groupchat = self.wxchatmap[msg.FromUser.Uin]
        # else:
        #     group_number = self.toxkit.groupchatAdd()
        #     groupchat = Chatroom()
        #     groupchat.group_number = group_number
        #     groupchat.FromUser = msg.FromUser
        #     groupchat.ToUser = msg.ToUser
        #     self.wxchatmap[msg.FromUser.Uin] = groupchat
        #     self.toxchatmap[group_number] = groupchat
        #     if msg.ToUser.UserName == 'filehelper':
        #         groupchat.title = '%s@WQU' % msg.ToUser.NickName
        #     else:
        #         groupchat.title = '%s@WQU' % msg.FromUser.NickName

        #     rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
        #     rc = self.toxkit.groupchatInviteFriend(group_number, self.peerToxId)
        #     if rc != 0: qDebug('invite error')

        # # assert groupchat is not None
        # rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
        # if rc != 0: qDebug('group chat send msg error')

        return

    def dispatchNewsappChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        mkey = 'newsapp'
        title = 'newsapp@WQU'

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.toxkit.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                rc = self.toxkit.groupchatInviteFriend(groupchat.group_number, self.peerToxId)
            else:
                rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
                if rc != 0: qDebug('group chat send msg error')
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

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.toxkit.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                rc = self.toxkit.groupchatInviteFriend(groupchat.group_number, self.peerToxId)
            else:
                rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
                if rc != 0: qDebug('group chat send msg error:%s' % str(rc))
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

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.toxkit.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                rc = self.toxkit.groupchatInviteFriend(groupchat.group_number, self.peerToxId)
            else:
                rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
                if rc != 0: qDebug('group chat send msg error: %s' % str(rc))
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

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.toxkit.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                rc = self.toxkit.groupchatInviteFriend(groupchat.group_number, self.peerToxId)
            else:
                rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
                if rc != 0: qDebug('group chat send msg error: %s' % str(rc))
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
        if msg.FromUser.Uin == self.wxses.me.Uin:
            mkey = msg.ToUser.Uin
            title = '%s@WQU' % msg.ToUser.NickName
        else:
            mkey = msg.FromUser.Uin
            title = '%s@WQU' % msg.FromUser.NickName

        # TODO 可能有一个计算交集的函数吧
        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]

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

        group_number = ('WXU.%s' % mkey).lower()
        group_number = self.peerRelay.createChatroom(mkey, title).lower()
        groupchat = Chatroom()
        groupchat.group_number = group_number
        groupchat.FromUser = msg.FromUser
        groupchat.ToUser = msg.ToUser
        groupchat.FromUserName = msg.FromUserName
        self.wxchatmap[mkey] = groupchat
        self.toxchatmap[group_number] = groupchat
        groupchat.title = title

        if msg.PollType == QQ_PT_DISCUS:
            groupchat.chat_type = CHAT_TYPE_DISCUS
        elif msg.PollType == QQ_PT_QUN:
            groupchat.chat_type = CHAT_TYPE_QUN
        elif msg.PollType == QQ_PT_SESSION:
            groupchat.chat_type = CHAT_TYPE_SESS 
        elif msg.PollType == QQ_PT_USER:
            groupchat.chat_type = CHAT_TYPE_U2U
        else:
            qDebug('undefined behavior')

        groupchat.Gid = msg.Gid
        groupchat.ServiceType = msg.ServiceType

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        # rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
        # rc = self.toxkit.groupchatInviteFriend(group_number, self.peerToxId)
        # if rc != 0: qDebug('invite error')

        return groupchat

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
        if self.wxses is not None:
            return

        self.wxses = WXSession()

        reply = self.sysiface.call('getselfinfo', 123, 'a1', 456)
        rr = QDBusReply(reply)
        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode()   # to bytes
        data = QByteArray.fromBase64(data64)
        self.wxses.setSelfInfo(data)
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
        # self.wxses.setInitData(data)
        # self.saveContent('initdata.json', data)

        # reply = self.sysiface.call('getcontact', 123, 'a1', 456)
        # rr = QDBusReply(reply)

        # # TODO check reply valid
        # qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        # data64 = rr.value().encode('utf8')   # to bytes
        # data = QByteArray.fromBase64(data64)
        # self.wxses.setContact(data)
        # self.saveContent('contact.json', data)


        # reply = self.sysiface.call('getgroups', 123, 'a1', 456)
        # rr = QDBusReply(reply)

        # # TODO check reply valid
        # qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        # GroupNames = json.JSONDecoder().decode(rr.value())

        # self.wxses.addGroupNames(GroupNames)

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

    def getGroupsFromDBus(self):

        reply = self.sysiface.call('getgroups', 123, 'a1', 456)
        rr = QDBusReply(reply)

        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        GroupNames = json.JSONDecoder().decode(rr.value())

        return GroupNames

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


        if extrainfo == 'getuserfriends':
            self.wxses.setUserFriends(hcc)

        if extrainfo == 'getgroupnamelist':
            self.wxses.setGroupList(hcc)
            for um in hccjs['result']['gnamelist']:
                gcode = um['code']
                gname = um['name']
                qDebug('get group detail...' + str(um))
                pcall = self.sysiface.asyncCall('get_group_detail', gcode, 'a0', 123, 'a1')
                twatcher = QDBusPendingCallWatcher(pcall)
                twatcher.finished.connect(self.onGetGroupOrDiscusDetailDone, Qt.QueuedConnection)
                self.asyncWatchers[twatcher] = 'get_group_detail'
                qDebug('get group detail...' + str(um) + str(twatcher))

        if extrainfo == 'getdiscuslist':
            self.wxses.setDiscusList(hcc)
            for um in hccjs['result']['dnamelist']:
                did = um['did']
                dname = um['name']
                qDebug('get discus detail...' + str(um))
                pcall = self.sysiface.asyncCall('get_discus_detail', did, 'a0', 123, 'a1')
                twatcher = QDBusPendingCallWatcher(pcall)
                twatcher.finished.connect(self.onGetGroupOrDiscusDetailDone, Qt.QueuedConnection)
                self.asyncWatchers[twatcher] = 'get_discus_detail'
                qDebug('get discus detail...' + str(um) + str(twatcher))

        self.asyncWatchers.pop(watcher)
        return

    # TODO delay dbus 请求响应合并处理
    def onGetGroupOrDiscusDetailDone(self, watcher):
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

        if extrainfo == 'get_group_detail':
            qDebug('gooooooooot')
            self.wxses.setGroupDetail(hcc)
            pass

        if extrainfo == 'get_discus_detail':
            qDebug('gooooooooot')
            self.wxses.setDiscusDetail(hcc)
            pass

        self.asyncWatchers.pop(watcher)
        return

    def getBatchGroupAll(self):
        groups2 = self.getGroupsFromDBus()
        self.wxses.addGroupNames(groups2)
        groups = self.wxses.getICGroups()
        qDebug(str(groups))

        reqcnt = 0
        arg0 = []
        for grname in groups:
             melem = {'UserName': grname, 'ChatRoomId': ''}
             arg0.append(melem)

        argjs = json.JSONEncoder().encode(arg0)
        pcall = self.sysiface.asyncCall('getbatchcontact', argjs)
        watcher = QDBusPendingCallWatcher(pcall)
        # watcher.finished.connect(self.onGetBatchContactDone)
        watcher.finished.connect(self.onGetBatchGroupDone)
        self.asyncWatchers[watcher] = arg0
        reqcnt += 1

        qDebug('async reqcnt: ' + str(reqcnt))

        return

    # @param message QDBusPengindCallWatcher
    def onGetBatchGroupDone(self, watcher):
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
        # qDebug(str(len(args)))

        hcc = args[0]  # QByteArray
        strhcc = self.hcc2str(hcc)
        hccjs = json.JSONDecoder().decode(strhcc)

        # print(strhcc)

        memcnt = 0
        for contact in hccjs['ContactList']:
            memcnt += 1
            # print(contact)
            # self.wxses.addMember(contact)
            grname = contact['UserName']
            if not WXUser.isGroup(grname): continue

            print('uid=%s,un=%s,nn=%s\n' % (contact['Uin'], contact['UserName'], contact['NickName']))
            self.wxses.addGroupUser(grname, contact)
            if grname in self.pendingGroupMessages and len(self.pendingGroupMessages[grname]) > 0:
                while len(self.pendingGroupMessages[grname]) > 0:
                    msgobj = self.pendingGroupMessages[grname].pop()
                    GroupUser = self.wxses.getGroupByName(grname)
                    self.dispatchWXGroupChatToTox2(msgobj[0], msgobj[1], GroupUser)

        qDebug('got memcnt: %s/%s' % (memcnt, len(self.wxses.ICGroups)))

        ### flow next
        # QTimer.singleShot(12, self.getBatchContactAll)

        return

    def getBatchContactAll(self):

        groups = self.wxses.getICGroups()
        qDebug(str(groups))
        reqcnt = 0
        for grname in groups:
            members = self.wxses.getGroupMembers(grname)
            arg0 = []
            for member in members:
                melem = {'UserName': member, 'EncryChatRoomId': group.UserName}
                arg0.append(melem)

            cntpertime = 50
            while len(arg0) > 0:
                subarg = arg0[0:cntpertime]
                subargjs = json.JSONEncoder().encode(subarg)
                pcall = self.sysiface.asyncCall('getbatchcontact', subargjs)
                watcher = QDBusPendingCallWatcher(pcall)
                watcher.finished.connect(self.onGetBatchContactDone)
                self.asyncWatchers[watcher] = subarg
                arg0 = arg0[cntpertime:]
                reqcnt += 1
                break
            break

        qDebug('async reqcnt: ' + str(reqcnt))

        return

    # @param message QDBusPengindCallWatcher
    def onGetBatchContactDone(self, watcher):
        pendReply = QDBusPendingReply(watcher)
        qDebug(str(watcher))
        qDebug(str(pendReply.isValid()))
        if pendReply.isValid():
            hcc = pendReply.argumentAt(0)
            qDebug(str(type(hcc)))
        else:
            return

        message = pendReply.reply()
        args = message.arguments()
        # qDebug(str(len(args)))

        hcc = args[0]  # QByteArray
        strhcc = self.hcc2str(hcc)
        hccjs = json.JSONDecoder().decode(strhcc)

        # qDebug(str(self.wxses.getGroups()))
        print(strhcc)

        memcnt = 0
        for contact in hccjs['ContactList']:
            memcnt += 1
            # print(contact)
            self.wxses.addMember(contact)

        qDebug('got memcnt: %s/%s' % (memcnt, len(self.wxses.ICUsers)))
        return

    def onGetFriendInfoDone(self, watcher):
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
        msg, fmtcc = self.asyncWatchers[watcher]

        ######
        hcc = args[0]  # QByteArray
        strhcc = self.hcc2str(hcc)
        hccjs = json.JSONDecoder().decode(strhcc)
        print(':::', strhcc)

        self.wxses.addFriendInfo(hcc)
        if msg.FromUser is None:
            msg.FromUser = self.wxses.getUserByName(msg.FromUserName)
        elif msg.ToUser is None:
            msg.ToUser = self.wxses.getUserByName(msg.ToUserName)
        else:
            pass

        assert(msg.FromUser is not None)
        assert(msg.ToUser is not None)

        self.dispatchQQSessChatToTox(msg, fmtcc)

        self.asyncWatchers.pop(watcher)
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


# hot fix
g_w2t = None


def on_app_about_close():
    qDebug('hereee')
    global g_w2t

    g_w2t.peerRelay.disconnectIt()
    return


def main():
    app = QCoreApplication(sys.argv)
    import wxagent.qtutil as qtutil
    qtutil.pyctrl()

    w2t = WX2Tox()
    global g_w2t
    g_w2t = w2t

    app.aboutToQuit.connect(on_app_about_close)

    app.exec_()
    return


if __name__ == '__main__': main()
