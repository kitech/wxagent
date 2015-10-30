# web weixin protocol

import os, sys
import json, re
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

from .tx2any import TX2Any, Chatroom


#
#
#
class WX2Tox(TX2Any):

    def __init__(self, parent=None):
        "docstring"
        super(WX2Tox, self).__init__(parent)

        self.agent_service = WXAGENT_SERVICE_NAME
        self.agent_service_path = WXAGENT_SEND_PATH
        self.agent_service_iface = WXAGENT_IFACE_NAME
        self.agent_event_path = WXAGENT_EVENT_BUS_PATH
        self.agent_event_iface = WXAGENT_EVENT_BUS_IFACE
        self.relay_src_pname = 'WXU'

        self.initDBus()
        self.initRelay()
        self.startWXBot()
        return

    def botcmdHandler(self, msg):
        # 汇总消息好友发送过来的消息当作命令处理
        # getqrcode
        # islogined
        # 等待，总之是wxagent支持的命令，

        cmd = BotCmder.parseCmd(msg)
        if cmd is False:
            qDebug('not a cmd: %s' % msg[0:120])
            return

        if cmd[0] == 'help':
            helpmsg = BotCmder.helpMessage()
            self.peerRelay.sendMessage(helpmsg, self.peerRelay.peer_user)
            return

        elif cmd[0] == 'invite':
            if cmd[1] == '':  # 发送所有的好友，注意是真正的已添加的好友，不是在群组里面的。
                nnlst = self.txses.getInviteCompleteList()
                nnlst = list(map(lambda x: '*) ' + x, nnlst))
                self.peerRelay.sendMessage('    '.join(nnlst), self.peerRelay.peer_user)
            else:
                # 查找是否有该好友，
                # 如果有，则创建与该好友的聊天室
                # 如果没有，则查找是否有前相似匹配的
                # 如果有相似匹配的，则提示相似匹配的所有好友
                nnlst = self.txses.getInviteCompleteList(cmd[1])
                nnlen = len(nnlst)
                if nnlen == 0:
                    qDebug(('not found:' + cmd[1]).encode())
                    rpstr = 'no user named: ' + cmd[1]
                    self.peerRelay.sendMessage(rpstr, self.peerRelay.peer_user)
                elif nnlen == 1:
                    qDebug(('exact match found:' + cmd[1] + ',' + str(nnlst[0])).encode())
                    rpstr = 'inviteing %s......' % nnlst[0]
                    self.peerRelay.sendMessage(rpstr, self.peerRelay.peer_user)
                    self.inviteFriendToChat(nnlst[0])
                else:
                    qDebug(('multi match found:' + cmd[1]).encode())
                    nnlst = list(map(lambda x: '*) ' + x, nnlst))
                    self.peerRelay.sendMessage('    '.join(nnlst), self.peerRelay.peer_user)
        else:
            qDebug('unknown cmd:' + str(cmd))

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

        msgs = wxmsgvec.getAddMsgList()
        for msg in msgs:
            fromUser = self.txses.getUserByName(msg.FromUserName)
            toUser = self.txses.getUserByName(msg.ToUserName)
            qDebug(str(fromUser))
            qDebug(str(toUser))

            msg.FromUser = fromUser
            msg.ToUser = toUser

            self.sendMessageToToxByType(msg)

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
                fileurl = msg.Url
                logstr += '> %s' % fileurl
                logstr += '\n\nname: %s' % msg.FileName
            self.sendMessageToTox(msg, logstr)
        elif msg.MsgType == WXMsgType.MT_VOICE:
            logstr += '> voicelen: %s″' % math.floor(msg.VoiceLength / 1000)
            self.sendMessageToTox(msg, logstr)
            self.sendVoiceMessageToTox(msg, logstr)
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
            if self.txses.me.UserName == msg.ToUser.UserName:
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
        # qDebug(mcc.decode())

        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('sendmessage', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        # TODO send message faild

        return

    def sendWXGroupChatMessageToWX(self, groupchat, mcc):

        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName

        args = [to_username, from_username, mcc, 1, 'more', 'even more']
        reply = self.sysiface.call('sendmessage', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

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
        reply = self.sysiface.call('sendmessage', *args)  # 注意把args扩展开

        rr = QDBusReply(reply)
        if rr.isValid():
            qDebug(str(rr.value()) + ',' + str(type(rr.value())))
        else:
            qDebug('rpc call error: %s,%s' % (rr.error().name(), rr.error().message()))

        # TODO send message faild

        return

    def createWXSession(self):
        if self.txses is not None:
            return

        self.txses = WXSession()

        reply = self.sysiface.call('getinitdata', 123, 'a1', 456)
        rr = QDBusReply(reply)
        # TODO check reply valid

        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode()   # to bytes
        data = QByteArray.fromBase64(data64)
        self.txses.processInitData(data)
        self.saveContent('initdata.json', data)

        reply = self.sysiface.call('getcontact', 123, 'a1', 456)
        rr = QDBusReply(reply)

        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode()   # to bytes
        data = QByteArray.fromBase64(data64)
        self.txses.processContactData(data)
        self.saveContent('contact.json', data)

        reply = self.sysiface.call('getgroups', 123, 'a1', 456)
        rr = QDBusReply(reply)

        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        GroupNames = json.JSONDecoder().decode(rr.value())

        self.txses.addGroupNames(GroupNames)

        QTimer.singleShot(8, self.getBatchGroupAll)
        # QTimer.singleShot(8, self.getBatchContactAll)

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

    def getGroupsFromDBus(self):

        reply = self.sysiface.call('getgroups', 123, 'a1', 456)
        rr = QDBusReply(reply)

        # TODO check reply valid
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        GroupNames = json.JSONDecoder().decode(rr.value())

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
        pcall = self.sysiface.asyncCall('getbatchcontact', argjs)
        watcher = QDBusPendingCallWatcher(pcall)
        # watcher.finished.connect(self.onGetBatchContactDone)
        watcher.finished.connect(self.onGetBatchGroupDone)
        self.asyncWatchers[watcher] = arg0
        reqcnt += 1

        qDebug('async reqcnt: ' + str(reqcnt))

        return

    # @param watcher QDBusPengindCallWatcher
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



