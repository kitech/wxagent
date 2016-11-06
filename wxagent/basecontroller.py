# base web tx im protocol client

import os, sys
import json, re
import enum
import time
import asyncio

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

from .imrelayfactory import IMRelayFactory
from .unimessage import *
from .filestore import QiniuFileStore, VnFileStore
from .txcom import *
from .listener import ListenerFactory
# QDBUS_DEBUG


class Chatroom():
    def __init__(self):
        "docstring"

        self.group_number = -1
        self.peer_number = -1

        self.msgo = None

        # 以收到消息创建聊天群组时的from/to定义
        self.FromUser = None
        self.ToUser = None

        self.title = ''

        self.unsend_queue = []

        self.chat_type = CHAT_TYPE_NONE
        self.group_sig = None
        self.Gid = 0
        self.ServiceType = 0

        # fixme some bugs
        self.FromUserName = ''  # case for newsapp/xxx
        return

    def toJson(self):
        return


class BaseController0(QObject):
    def __init__(self, rtab, parent=None):
        "docstring"
        super(BaseController0, self).__init__(parent)
        self.rtab = rtab
        return

    def initSession(self):
        return

    def updateSession(self, msgo):
        return

    def ifaceForName(self, name):
        name = name.replace('Controller', 'Agent')
        service_name = WXAGENT_SERVICE_NAME + '.' + name
        service_path = WXAGENT_SERVICE_PATH + '/' + name
        service_iface = WXAGENT_SERVICE_IFACE + '.' + name

        iface = QDBusInterface(service_name, service_path,
                               service_iface, self.rtab.sysbus)
        return iface

    def remoteCall(self, func, *argv):
        iface = self.ifaceForName(self.__class__.__name__)
        reply = iface.call('rcall', func, *argv)
        rr = QDBusReply(reply)
        if not rr.isValid():
            qDebug('error: {}, {}' .format(rr.error().name(), rr.error().message()))
        else:
            ret = json.JSONDecoder().decode(rr.value())
            return ret
        return

    def asyncRemoteCall(self, cbfunc, func, *argv):
        iface = self.ifaceForName(self.__class__.__name__)
        pcall = iface.asyncCall('getbatchcontact', *argv)
        watcher = QDBusPendingCallWatcher(pcall)
        watcher.finished.connect(self.asyncRemoteCallDone)
        self.asyncWatchers[watcher] = [cbfunc, func, argv]
        return

    def asyncRemoteCallDone(self, watcher):
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

        retv = json.JSONDecoder().decode(args[0])
        cbfunc, func, argv = self.asyncWatchers[watcher]
        self.asyncWatchers.pop(watcher)
        cbfunc(retv)
        return


class BaseController(BaseController0):

    def __init__(self, rt, parent=None):
        "docstring"
        super(BaseController, self).__init__(rt, parent)

        ##### fill at sub class
        self.relay_src_pname = ''

        self.txses = None   # XXSession
        self.peerRelay = None  # IMRelay subclass
        self.lsnrs = []  # XXXListener

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

        self.asyncWatchers = {}   # watcher => arg0
        self.sysbus = QDBusConnection.systemBus()
        return

    def initDBus(self):
        return

    def initRelay(self):
        # from .secfg import relay_type
        # if relay_type is None or relay_type == '' or relay_type not in ('xmpp', 'tox'):
        #    raise 'relay type not set or invalid relay type. see secfg.py.'
        # relay_type = 'xmpp'
        # relay_type = 'tox'
        # self.peerRelay = IMRelayFactory.create(relay_type)
        # self.peerRelay.src_pname = self.relay_src_pname
        self.peerRelay.src_name = self.__class__.__name__

        relay = self.peerRelay
        relay.connected.connect(self.onRelayConnected, Qt.QueuedConnection)
        relay.disconnected.connect(self.onRelayDisconnected, Qt.QueuedConnection)
        relay.newMessage.connect(self.onRelayMessage, Qt.QueuedConnection)

        relay.peerConnected.connect(self.onRelayPeerConnected, Qt.QueuedConnection)
        relay.peerDisconnected.connect(self.onRelayPeerDisconnected, Qt.QueuedConnection)
        relay.newGroupMessage.connect(self.onRelayGroupMessage, Qt.QueuedConnection)
        relay.peerEnterGroup.connect(self.onRelayPeerEnterGroup, Qt.QueuedConnection)
        return

    def initListener(self):
        from .secfg import listeners
        for listener in listeners:
            lo = ListenerFactory.create(listener, self)
            self.lsnrs.append(lo)
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
            if rc is not False: self.need_send_qrfile = False

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
            if rc is not False: self.need_send_qrfile = False

        # TODO 使用dispatch方式发送消息
        if len(self.tx2relay_msg_buffer) > 0 and self.peerRelay.isPeerConnected(self.peerRelay.peer_user):
            blen = len(self.tx2relay_msg_buffer)
            while len(self.tx2relay_msg_buffer) > 0:
                msg = self.tx2relay_msg_buffer.pop()
                # self.peerRelay.sendMessage(msg, self.peerRelay.peer_user)
                self.sendMessageToToxByType(msg)
                # ## TODO 如果发送失败，这条消息可就丢失了。
            qDebug('send buffered wx2tox msg: %s' % blen)
        return

    def onRelayPeerDisconnected(self):
        qDebug('hehee')
        return

    def onRelayPeerEnterGroup(self, group_number):
        qDebug(('hehee:' + group_number).encode())
        qDebug(str(self.rtab.unichats.dumpKeys(ret=True)).encode())
        qDebug(str(self.relaychatmap.keys()).encode())

        if self.relaychatmap.get(group_number) is None:
            qDebug('not exist: {}'.format(group_number))
            return

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

        return

    def onRelayGroupMessage(self, group_number, message):
        qDebug(('hehee:' + str(group_number)).encode())
        groupchat = None
        if group_number in self.relaychatmap:
            groupchat = self.relaychatmap[group_number]
        else:
            qDebug('can not find assoc chatroom')
            return

        qDebug((json.JSONEncoder().encode(groupchat.__dict__)).encode())
        qDebug(('will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.ToUser.NickName)).encode())
        if groupchat.FromUser is not None:
            qDebug(('or will send wx msg:%s,%s' % (groupchat.ToUser.Uin, groupchat.FromUser.NickName)).encode())
        else:
            qDebug(('or will send wx msg:%s' % (groupchat.FromUserName)).encode())

        peer_number = 'magicxxxjaoijfiwafaewf'
        # TODO 把从各群组来的发给WX端的消息，同步再发送给tox汇总端一份。也就是tox的唯一peer端。
        # TODO 如果是从wx2tox转过去的消息，这里也会再次收到，所以，会向tox汇总端重复发一份了，需要处理。
        try:
            if peer_number == 0: pass  # it myself sent message, omit
            else:
                if groupchat.FromUserName == self.txses.me.UserName:
                    newmsg = '⇧(To: %s) %s' % (groupchat.ToUser.NickName, message)
                else:
                    newmsg = '⇧(To: %s) %s' % (groupchat.FromUser.NickName, message)
                ret = self.peerRelay.sendMessage(newmsg, self.peerRelay.peer_user)
        except Exception as ex:
            qDebug('send msg error: %s' % str(ex))

        if peer_number == 0: pass  # it myself sent message, omit
        else:
            ret = self.sendMessageToWX(groupchat, message)
            if ret: pass

            # listener event
            for listener in self.lsnrs:
                if listener.role == listener.ROLE_CHAT:
                    listener.onRelayGroupMessage(groupchat, message)

        return

    def sendQRToRelayPeer(self, qrpic64str=None):
        # 无论是否登陆，启动的都发送一次qrcode文件
        if qrpic64str is None:
            qrpic64str = self.getQRCode()
        if qrpic64str is not None:
            qrpic = QByteArray.fromBase64(qrpic64str)
        else: qrpic = None
        if qrpic is None:
            qDebug('maybe wechat agent not run...')
        elif len(qrpic) == 0:
            qDebug('maybe wechat agent not bootstrap...')
        else:
            fname = self.genQRCodeSaveFileName()
            self.saveContent(fname, qrpic)

            self.qrpic = qrpic
            self.qrfile = fname

            tkc = False
            # tkc = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
            tkc = True
            if tkc is True:
                # url = filestore.upload_file(self.qrpic)
                url1 = QiniuFileStore.uploadData(self.qrpic)
                url2 = VnFileStore.uploadData(self.qrpic)
                url = url1 + "\n" + url2
                # self.peerRelay.sendMessage('qrcode url:' + url, self.peerRelay.peer_user)
                args = self.rtab.makeBusMessage('showpiclink', None, 'qrcode url:' + url)
                self.rtab.SendMessageX(args)
            else:
                self.need_send_qrfile = True
        return

    def onDBusBeginLogin2(self):
        qDebug('hehrhe')
        return

    def onDBusGotQRCode2(self, qrpic64str):
        self.sendQRToRelayPeer(qrpic64str)
        return

    def onDBusLoginSuccess(self):
        loop = asyncio.get_event_loop()
        loop.call_soon(self.startWXBot)

        args = self.rtab.makeBusMessage('notinfo', None, 'login success')
        self.rtab.SendMessageX(args)
        # send success message to UI peer
        return

    def onDBusLogined(self):
        qDebug('hehreere')
        args = self.rtab.makeBusMessage('notinfo', None, 'log in')
        self.rtab.SendMessageX(args)
        # send success message to UI peer
        return

    def onDBusLogouted(self):
        qDebug('hehreere')
        args = self.rtab.makeBusMessage('notinfo', None, 'log out')
        self.rtab.SendMessageX(args)
        # send success message to UI peer
        return

    # def onDBusNewMessage(self, message)

    # @param msg TXMessage
    def sendMessageToToxByType(self, msg):
        raise 'must impled in subclass'
        return

    def sendMessageToTox(self, msg, fmtcc):
        fstatus = self.peerRelay.isPeerConnected(self.peerRelay.peer_user)
        if fstatus is True:
            if msg.FromUserName == self.txses.me.UserName:
                newcc = '⇩(From: %s) %s' % (msg.ToUser.NickName, fmtcc)
            else:
                newcc = '⇩(From: %s) %s' % (msg.FromUser.NickName, fmtcc)

            try:
                # 把收到的消息发送到汇总tox端
                ret = self.peerRelay.sendMessage(newcc, self.peerRelay.peer_user)
            except Exception as ex:
                qDebug('tox send msg error: ' + str(ex))

            # dispatch by ChatType
            ret = self.dispatchToToxGroup(msg, fmtcc)
            if ret: pass
        else:
            # self.tx2relay_msg_buffer.append(msg)
            pass

        return

    # wx and qq both use
    def sendShotPicMessageToTox(self, msg, logstr):
        umsg = self.peerRelay.unimsgcls.fromWXMessage(msg, self.txses)

        def get_img_reply(data=None):
            if data is None: return
            # url = filestore.upload_file(data)
            url1 = QiniuFileStore.uploadData(data)
            url2 = VnFileStore.uploadData(data)
            url = url1 + "\n" + url2
            urmsg = '%s: pic url: %s' % (umsg.dispname(self.txses), url)
            self.sendMessageToTox(msg, urmsg)
            return

        self.getMsgImgCallback(msg, get_img_reply)
        return

    # wx use now
    def sendVoiceMessageToTox(self, msg, logstr):
        umsg = self.peerRelay.unimsgcls.fromWXMessage(msg, self.txses)

        def get_voice_reply(data=None):
            if data is None: return
            # url = filestore.upload_file(data)
            url1 = QiniuFileStore.uploadData(data)
            url2 = VnFileStore.uploadData(data)
            url = url1 + "\n" + url2
            urmsg = '%s: voice url: %s' % (umsg.dispname(self.txses), url)
            self.sendMessageToTox(msg, urmsg)
            return

        self.getMsgVoiceCallback(msg, get_voice_reply)
        return

    # qq use now，也许wx也会用到。
    def sendFileMessageToTox(self, msg, logstr):
        def get_file_reply(data=None):
            if data is None: return
            # fix qq protocol error return
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

    # def dispatchToToxGroup(self, msg, fmtcc):
    # def dispatchNewsappChatToTox(self, msg, fmtcc):
    # def dispatchFileHelperChatToTox(self, msg, fmtcc):
    # def dispatchWXGroupChatToTox(self, msg, fmtcc):
    #    需要一个公共的判断用户是否是群组的方法TXUser.isGroup()
    # def dispatchU2UChatToTox(self, msg, fmtcc):
    # def dispatchxxxChatToTox(self, msg, fmtcc):

    # def createChatroom(self, msg, mkey, title):
    #    需要统一判断chatroom类型的方法

    # def fillChatroom(self, msgo, mkey=None, title=None, group_number=None):
    #    需要统一判断chatroom类型的方法

    # def sendMessageToWX(self, groupchat, mcc):
    #    这个方法好像不抽像不出来

    # def sendxxxMessageToWX(self, groupchat, mcc):
    #    从reply 敵得到的消息，发回给wx/qq端

    # def createWXSession(self):
    #    目前抽象不出来，需要把取初始化数据分离出来

    # def checkWXLogin(self):
    #    需要和getconnstate想办法合并统一一下
    # def getConnState(self):

    def getQRCode(self):
        retv = self.peerRelay.getqrpic(123, 'a1', 456)
        if retv is not None:
            qrpic64 = retv.encode()   # to bytes
            return qrpic64
        return None

    def genQRCodeSaveFileName(self):
        now = QDateTime.currentDateTime()
        fname = '/tmp/wxqrcode_%s.jpg' % now.toString('yyyyMMddHHmmsszzz')
        return fname

    # @param data QByteArray | bytes
    def genMsgImgSaveFileName(self, data):
        now = QDateTime.currentDateTime()

        m = magic.open(magic.MAGIC_MIME_TYPE)
        m.load()
        mty = m.buffer(data.data()) if type(data) == QByteArray else m.buffer(data)
        m.close()

        suffix = mty.split('/')[1]
        suffix = 'jpg' if suffix == 'jpeg' else suffix
        suffix = 'bmp' if suffix == 'x-ms-bmp' else suffix

        fname = '/tmp/wxpic_%s.%s' % (now.toString('yyyyMMddHHmmsszzz'), suffix)
        return fname

    def getBaseFileName(self, fname):
        bfname = QFileInfo(fname).fileName()
        return bfname

    # def group/friend info methods...

    # def getMsgImgCallback(self, msg, imgcb=None):
    #    需要统一处理图片源地址信息

    def getMsgImgUrl(self, msg):
        args = [msg.MsgId, False]
        return self.syncGetRpc('get_msg_img_url', args)

    # def getMsgFileUrl(self, msg):
    # def getMsgFileCallback(self, msg, imgcb=None):
    # @param cb(data)
    # def getMsgVoiceCallback(self, msg, imgcb=None):

    def getAgentRuntimeStats(self):
        args = []
        return self.syncGetRpc('get_stats', args)

    # @param name str
    # @param args list
    # @param return None | mixed
    def syncGetRpc(self, name, args):
        reply = self.sysiface.call(name, *args)
        rr = QDBusReply(reply)

        # TODO check reply valid
        qDebug(name + ':' + str(len(rr.value())) + ',' + str(type(rr.value())))
        if rr.isValid():
            return rr.value()
        return None

    def asyncGetRpc(self, name, args, callback):
        pcall = self.sysiface.asyncCall(name, *args)
        watcher = QDBusPendingCallWatcher(pcall)
        # watcher.finished.connect(callback)
        watcher.finished.connect(self.onAsyncGetRpcFinished)
        self.asyncWatchers[watcher] = callback
        return

    def onAsyncGetRpcFinished(self, watcher):
        qDebug('replyyyyyyyyyyyyyyy')
        pendReply = QDBusPendingReply(watcher)
        qDebug(str(watcher))
        qDebug(str(pendReply.isValid()))
        if pendReply.isValid():
            hcc = pendReply.argumentAt(0)
            qDebug(str(type(hcc)))
        else:
            callback = self.asyncWatchers.pop(watcher)
            if callback is not None: callback(None)
            return

        message = pendReply.reply()
        args = message.arguments()

        callback = self.asyncWatchers.pop(watcher)
        # send img file to tox client
        if callback is not None: callback(args[0])

        return

    # listener 需要知道发送以哪个room
    def findGroupChatByMsg(self, msg):
        for mkey in self.txchatmap:
            room = self.txchatmap[mkey]
            if room.FromUser.UserName == msg.FromUser.UserName and \
               room.ToUser.UserName == msg.ToUser.UserName:
                return room

            if room.ToUser.UserName == msg.FromUser.UserName and \
               room.FromUser.UserName == msg.ToUser.UserName:
                return room
        raise Exception('wtf')
        return None

    # @param hcc QByteArray
    # @return str
    def hcc2str(self, hcc):
        strhcc = ''

        astr = hcc.data().decode()
        qDebug(astr[0:120].replace("\n", "\\n").encode())
        strhcc = astr

        return strhcc

    # @param name str
    # @param hcc QByteArray
    # @return None
    def saveContent(self, name, hcc):
        fp = QFile(name)
        fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
        fp.write(hcc)
        fp.close()
        return
