# web weixin protocol

import os, sys
import json, re
import html
import enum
import time
import magic
import math

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *


from .imrelayfactory import IMRelayFactory
from .wxcommon import *
from .wxmessage import *
from .wxsession import *
from .unimessage import *
from .botcmd import *
from .filestore import QiniuFileStore, VnFileStore

from .basecontroller import BaseController, Chatroom


#
#
class WechatController(BaseController):

    def __init__(self, rt, parent=None):
        "docstring"
        super(WechatController, self).__init__(rt, parent)

        self.relay_src_pname = 'WXU'

        self.initDBus()
        self.initRelay()
        self.initListener()
        self.startWXBot()
        return

    def replyMessage(self, msgo):
        return

    def botcmdHandler(self, msg):
        # 汇总消息好友发送过来的消息当作命令处理
        # getqrcode
        # islogined
        # 等待，总之是wxagent支持的命令，

        # listener event
        qDebug("emit event...")
        for listener in self.lsnrs:
            if listener.role == listener.ROLE_CTRL:
                listener.onMessage(msg)

        return

    def startWXBot(self):
        logined = False
        if not self.checkWXLogin():
            qDebug('wxagent not logined.')
        else:
            logined = True
            qDebug('wxagent already logined.')

        self.sendQRToRelayPeer()
        if logined is True: self.createWXSession()
        return

    @pyqtSlot(QDBusMessage)
    def onDBusNewMessage(self, message):
        # qDebug(str(message.arguments()))
        args = message.arguments()
        msglen, msghcc, *others = args

        if self.txses is None: self.createWXSession()

        for arg in args:
            if type(arg) == int:
                qDebug(str(type(arg)) + ',' + str(arg))
            else:
                qDebug(str(type(arg)) + ',' + str(arg)[0:120])

        hcc64_str = args[1]
        hcc64 = hcc64_str.encode()
        hcc = QByteArray.fromBase64(hcc64)

        self.saveContent('msgfromdbus.json', hcc)

        wxmsgvec = self.txses.processMessage(hcc)

        def dmUser(UserName):
            u = WXUser()
            u.UserName = UserName
            if UserName in ('newsapp'):
                u.NickName = UserName
            else:
                u.NickName = 'unknown' + UserName[0:7]
            return u

        msgs = wxmsgvec.getAddMsgList()
        for msg in msgs:
            fromUser = self.txses.getUserByName(msg.FromUserName)
            toUser = self.txses.getUserByName(msg.ToUserName)
            qDebug(str(fromUser))
            qDebug(str(toUser))

            msg.FromUser = fromUser
            msg.ToUser = toUser

            # TODO 这种情况怎么处理好呢？
            # 目前只能做到不让程序崩溃掉。
            if msg.FromUser is None:
                msg.FromUser = dmUser(msg.FromUserName)
            if msg.ToUser is None:
                msg.ToUser = dmUser(msg.ToUserName)

            if fromUser is None or toUser is None:
                qDebug(('%s => %s' % (msg.FromUser.NickName, msg.ToUser.NickName)).encode())

            self.sendMessageToToxByType(msg)

        # listener event
        for listener in self.lsnrs:
            if listener.role == listener.ROLE_CHAT:
                for msg in msgs:
                    listener.onMessage(msg)
        return

    def sendMessageToToxByType(self, msg):
        # pmsg = PlainMessage.fromWXMessage(msg, self.txses)
        # logstr = pmsg.content
        # xmsg = XmppMessage.fromWXMessage(msg, self.txses)
        # logstr = xmsg.get()
        umsg = self.peerRelay.unimsgcls.fromWXMessage(msg, self.txses)

        # multimedia 消息处理
        logstr = ''
        if msg.MsgType == WXMsgType.MT_SHOT or msg.MsgType == WXMsgType.MT_X47_CARTOON:
            imgurl = self.getMsgImgUrl(msg)
            logstr += '\n> %s' % imgurl
            self.sendMessageToTox(msg, logstr)
            self.sendShotPicMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_X49_FILE_OR_ARTICLE:
            if len(msg.MediaId) > 0:
                fileurl = self.getMsgFileUrl(msg)
                logstr += '> %s' % fileurl
                logstr += '\n\nname: %s' % msg.FileName
                logstr += '\nsize: %s' % msg.FileSize
            else:
                fileurl = html.unescape(msg.Url)
                logstr += '> %s' % fileurl
                logstr += '\n\nname: %s' % msg.FileName
            self.sendMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_X40:
            logstr = umsg.get()
            self.sendMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_X51:
            logstr = '打开了 ' + umsg.get()
            self.sendMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_VOICE:
            logstr += '> voicelen: %s″' % math.floor(msg.VoiceLength / 1000)
            self.sendMessageToTox(msg, logstr)
            self.sendVoiceMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_X10000:
            logstr = umsg.get()
            self.sendMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_TEXT:
            logstr = umsg.get()
            self.sendMessageToTox(msg, logstr)
        else:
            qDebug('Unknown msg type:' + str(msg.MsgType))
            logstr = 'Unknown -- ' + umsg.get() + ' -- Unknown'
            self.sendMessageToTox(msg, logstr)

        return

    def dispatchToToxGroup(self, msg, fmtcc):
        groupchat = None

        if msg.FromUserName == 'newsapp':
            qDebug('special chat: newsapp')
            self.dispatchNewsappChatToTox(msg, fmtcc)
            pass
        elif msg.ToUserName == 'filehelper' or msg.FromUserName == 'filehelper':
            qDebug('special chat: filehelper')
            self.dispatchFileHelperChatToTox(msg, fmtcc)
            pass
        elif msg.ToUserName.startswith('@@') or msg.FromUserName.startswith('@@'):
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
        title = 'newsapp@WXU'

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
            mkey = msg.FromUser.cname()
            title = '%s@WXU' % msg.FromUser.NickName
        else:
            mkey = msg.ToUser.cname()
            title = '%s@WXU' % msg.ToUser.NickName

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

        if msg.FromUserName.startswith('@@'):
            if msg.FromUser is None:
                # message pending and try get group info
                qDebug('warning FromUser not found, wxgroup not found:' + msg.FromUserName)
                if msg.FromUserName in self.pendingGroupMessages:
                    self.pendingGroupMessages[msg.FromUserName].append([msg, fmtcc])
                else:
                    self.pendingGroupMessages[msg.ToUserName] = list()
                    self.pendingGroupMessages[msg.ToUserName].append([msg, fmtcc])

                self.txses.addGroupNames([msg.FromUserName])
                QTimer.singleShot(1, self.getBatchGroupAll)
                return
            else:
                mkey = msg.FromUser.cname()
                title = '%s@WXU' % msg.FromUser.NickName
                if len(msg.FromUser.NickName) == 0:
                    qDebug('maybe a temp group and without nickname')
                    title = 'TGC%s@WXU' % msg.FromUser.cname()
        else:
            if msg.ToUser is None:
                qDebug('warning ToUser not found, wxgroup not found:' + msg.ToUserName)
                if msg.FromUserName in self.pendingGroupMessages:
                    self.pendingGroupMessages[msg.ToUserName].append([msg, fmtcc])
                else:
                    self.pendingGroupMessages[msg.ToUserName] = list()
                    self.pendingGroupMessages[msg.ToUserName].append([msg, fmtcc])

                self.txses.addGroupNames([msg.ToUserName])
                QTimer.singleShot(1, self.getBatchGroupAll)
                return
            else:
                mkey = msg.ToUser.cname()
                title = '%s@WXU' % msg.ToUser.NickName
                if len(msg.ToUser.NickName) == 0:
                    qDebug('maybe a temp group and without nickname')
                    title = 'TGC%s@WXU' % msg.ToUser.cname()

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

    def dispatchU2UChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        # 两个用户，正反向通信，使用同一个groupchat，但需要找到它
        # 这两个用户一定有一个是自己
        if self.txses.me is not None:
            if self.txses.me.UserName == msg.FromUser.UserName:
                mkey = msg.ToUser.cname()
                title = '%s@WXU' % msg.ToUser.NickName
            elif self.txses.me.UserName == msg.ToUser.UserName:
                mkey = msg.FromUser.cname()
                title = '%s@WXU' % msg.FromUser.NickName
            else:
                # TODO 这么处理好合理吗，是否有更好的处理方式。
                # 有可能是一种通知，并且User为None情况才出现。
                mkey = msg.FromUser.cname()
                title = '%s@WXU' % msg.FromUser.NickName
        else:
            qDebug('wtf???')
            assert(self.txses.me is not None)

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

        group_number = ('WXU.%s' % mkey).lower()
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

    def sendMessageToWX(self, groupchat, mcc):
        qDebug('here')

        FromUser = groupchat.FromUser
        ToUser = groupchat.ToUser

        if ToUser.UserName == 'filehelper' or FromUser.UserName == 'filehelper':
            qDebug('send special chat: filehelper')
            self.sendFileHelperMessageToWX(groupchat, mcc)
            pass
        elif ToUser.UserName.startswith('@@') or FromUser.UserName.startswith('@@'):
            qDebug('send wx group chat:')
            # wx group chat
            self.sendWXGroupChatMessageToWX(groupchat, mcc)
            pass
        else:
            qDebug('send u2u group chat:')
            # user <=> user
            self.sendU2UMessageToWX(groupchat, mcc)
            pass

        # TODO 把从各群组来的发给WX端的消息，再发送给tox汇总端一份。

        if True: return
        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName
        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        retv = self.remoteCall('sendmessage', *args)  # 注意把args扩展开
        # TODO send message faild

        return

    def sendFileHelperMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        qDebug('cc type:, ' + str(type(mcc)))
        qDebug('cc len:, ' + str(len(mcc)))
        # qDebug(mcc.decode())

        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        retv = self.remoteCall('sendmessage', *args)  # 注意把args扩展开
        # TODO send message faild

        return

    def sendWXGroupChatMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        args = [to_username, from_username, mcc, 1, 'more', 'even more']
        retv = self.remoteCall('sendmessage', *args)  # 注意把args扩展开
        # TODO send message faild

        return

    def sendU2UMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        # 一定是发送给对方的消息
        if self.txses.me is not None:
            if self.txses.me.UserName == groupchat.FromUser.UserName:
                from_username = groupchat.FromUser.UserName
                to_username = groupchat.ToUser.UserName
            else:
                from_username = groupchat.ToUser.UserName
                to_username = groupchat.FromUser.UserName
        else:
            qDebug('wtf???')
            assert(self.txses.me is not None)

        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        retv = self.remoteCall('sendmessage', *args)  # 注意把args扩展开
        # TODO send message faild

        return

    def createWXSession(self):
        if self.txses is not None:
            return

        self.txses = WXSession()

        retv = self.remoteCall('getinitdata', 123, 'a1', 456)
        data64 = retv.encode()
        data = QByteArray.fromBase64(data64)
        self.txses.processInitData(data)
        self.saveContent('initdata.json', data)

        retv = self.remoteCall('getcontact', 123, 'a1', 456)
        data64 = retv.encode()
        data = QByteArray.fromBase64(data64)
        self.txses.processContactData(data)
        self.saveContent('contact.json', data)

        retv = self.remoteCall('getgroups', 123, 'a1', 456)
        GroupNames = json.JSONDecoder().decode(retv)

        self.txses.addGroupNames(GroupNames)

        QTimer.singleShot(8, self.getBatchGroupAll)
        # QTimer.singleShot(8, self.getBatchContactAll)

        return

    def checkWXLogin(self):
        retv = self.remoteCall('islogined', 'a0', 123, 'a1')
        if retv is False:
            return retv

        return True

    def getGroupsFromDBus(self):
        retv = self.remoteCall('getgroups', 123, 'a1', 456)
        GroupNames = json.JSONDecoder().decode(retv)

        return GroupNames

    def getBatchGroupAll(self):
        groups2 = self.getGroupsFromDBus()
        self.txses.addGroupNames(groups2)
        groups = self.txses.getICGroups()
        qDebug(str(groups))

        reqcnt = 0
        arg0 = []
        for grname in groups:
             melem = {'UserName': grname, 'ChatRoomId': ''}
             arg0.append(melem)

        argjs = json.JSONEncoder().encode(arg0)
        self.asyncRemoteCall(self.onGetBatchContactDone, 'getbatchcontact', argjs)
        reqcnt += 1

        qDebug('async reqcnt: ' + str(reqcnt))

        return

    # @param watcher QDBusPengindCallWatcher
    def onGetBatchGroupDone(self, retv):
        hccjs = json.JSONDecoder().decode(retv)

        # print(strhcc)
        # self.saveContent('groups.json', hcc)

        memcnt = 0
        for contact in hccjs['ContactList']:
            memcnt += 1
            # print(contact)
            # self.txses.addMember(contact)
            grname = contact['UserName']
            if not WXUser.isGroup(grname): continue

            print('uid=%s,un=%s,nn=%s\n' % (0, contact['UserName'], contact['NickName']))
            self.txses.addGroupUser(grname, contact)
            if grname in self.pendingGroupMessages and len(self.pendingGroupMessages[grname]) > 0:
                while len(self.pendingGroupMessages[grname]) > 0:
                    msgobj = self.pendingGroupMessages[grname].pop()
                    GroupUser = self.txses.getGroupByName(grname)
                    if GroupUser is None:
                        qDebug('still not get msg group info, new?sink?')
                    else:
                        # 是不是能说明，可以把该grname从半完成状态，设置为完成状态呢？
                        self.dispatchWXGroupChatToTox2(msgobj[0], msgobj[1], GroupUser)

        qDebug('got memcnt: %s/%s' % (memcnt, len(self.txses.ICGroups)))

        # flow next
        QTimer.singleShot(32, self.getBatchContactAll)

        return

    def getBatchContactAll(self):

        groups = self.txses.getICGroups()
        qDebug(str(groups))
        reqcnt = 0
        for grname in groups:
            members = self.txses.getGroupMembers(grname)
            qDebug('prepare get group member info: %s, %s' % (grname, len(members)))
            arg0 = []
            for member in members:
                melem = {'UserName': member, 'EncryChatRoomId': grname}
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
                # break
            # break

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

        # qDebug(str(self.txses.getGroups()))
        qDebug('next linee...............')
        # print(strhcc)

        memcnt = 0
        for contact in hccjs['ContactList']:
            memcnt += 1
            # print(contact)
            self.txses.addMember(contact)

        qDebug('got memcnt: %s/%s(left)' % (memcnt, len(self.txses.ICUsers)))
        if len(self.txses.ICUsers) == 0:
            self.txses.checkUncompleteUsers()

        return

    # @param cb(data)
    def getMsgImgCallback(self, msg, imgcb=None):
        args = [msg.MsgId, False]
        self.asyncGetRpc('get_msg_img', args, imgcb)
        return

    def getMsgFileUrl(self, msg):
        file_name = msg.FileName.replace(' ', '+')
        args = [msg.FromUserName, msg.MediaId, file_name, 0]
        return self.syncGetRpc('get_msg_file_url', args)

    # @param cb(data)
    def getMsgVoiceCallback(self, msg, imgcb=None):
        args = [msg.MsgId]
        self.asyncGetRpc('get_msg_voice', args, imgcb)
        return

    # TODO 合并抽象该方法与createChatroom方法
    # @param nick str 好友的NickName
    def inviteFriendToChat(self, nick):

        FromUser = self.txses.me
        ToUser = self.txses.getUserByNickName(nick)
        title = '%s@WXU' % nick
        mkey = ToUser.cname()

        group_number = ('WXU.%s' % mkey).lower()
        group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        groupchat.FromUser = FromUser
        groupchat.ToUser = ToUser
        groupchat.FromUserName = FromUser.UserName
        groupchat.title = title

        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat



