# web weixin protocol

import os, sys
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtDBus import *



from wxagent.qtoxkit import *
from wxagent.wxsession import *

SERVICE_NAME = 'io.qtc.wxagent'
# QDBUS_DEBUG

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

        ##以收到消息创建聊天群组时的from/to定义
        self.FromUser = None
        self.ToUser = None
        
        self.title = ''
        
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

        ##### state
        self.qrpic = None  # QByteArray
        self.qrfile = ''
        self.need_send_qrfile = False   # 有可能toxkit还未上线
        self.wx2tox_msg_buffer = []  # 存储未转发到tox的消息
        self.tox2wx_msg_buffer = []

        self.wxchatmap = {}  # Uin => Chatroom
        self.toxchatmap = {}  # group_number => Chatroom
        
        
        #####
        self.sesbus = QDBusConnection.sessionBus()
        self.iface = QDBusInterface(SERVICE_NAME, '/', '', self.sesbus)

        #                                   path   iface    name
        # sigmsg = QDBusMessage.createSignal("/", 'signals', "logined")
        # connect(service, path, interface, name, QObject * receiver, const char * slot)
        # self.sesbus.connect(SERVICE_NAME, "/", 'signals', 'logined', self.onDBusLogined)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logined', self.onDBusLogined)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'logouted', self.onDBusLogouted)
        self.sesbus.connect(SERVICE_NAME, "/io/qtc/wxagent/signals", 'io.qtc.wxagent.signals', 'newmessage', self.onDBusNewMessage)

        self.initToxnet()
        self.startWXBot()
        return

    
    def initToxnet(self):
        ident = 'wx2tox'
        self.toxkit = QToxKit(ident, True)
        self.toxkit.connectChanged.connect(self.onToxnetConnectStatus, Qt.QueuedConnection)
        self.toxkit.newMessage.connect(self.onToxnetMessage, Qt.QueuedConnection)
        self.toxkit.friendConnectionStatus.connect(self.onToxnetFriendStatus, Qt.QueuedConnection)
        self.toxkit.fileChunkRequest.connect(self.onToxnetFileChunkReuqest, Qt.QueuedConnection)
        self.toxkit.fileRecvControl.connect(self.onToxnetFileRecvControl, Qt.QueuedConnection)
        self.toxkit.newGroupMessage.connect(self.onToxnetGroupMessage, Qt.QueuedConnection)
        return

    
    def onToxnetConnectStatus(self, status):
        qDebug(str(status))
        friendId = self.peerToxId
        fexists = self.toxkit.friendExists(friendId)
        qDebug(str(fexists))

        famsg = 'from wx2tox...'
        if not fexists:
            friend_number = self.toxkit.friendAdd(friendId, famsg)
            qDebug(str(friend_number))
        else:
            # rc = self.toxkit.friendDelete(friendId)
            # qDebug(str(rc))
            try:
                friend_number = self.toxkit.friendAddNorequest(friendId)
                qDebug(str(friend_number))
            except Exception as ex:
                pass
            #self.toxkit.friendAddNorequest(friendId)
            pass
                
        return

    def onToxnetMessage(self, friendId, msgtype, msg):
        qDebug(friendId + ':' + str(msgtype) + '=' + str(len(msg)))
        return

    def onToxnetFriendStatus(self, friendId, status):
        qDebug(friendId + ':' + str(status))

        if status > 0 and self.need_send_qrfile is True:
            file_number = self.toxkit.fileSend(self.peerToxId, len(self.qrpic), self.getBaseFileName(self.qrfile))
            if file_number == pow(2,32):
                qDebug('send file error')
            else:
                self.need_send_qrfile = False


        if status > 0 and len(self.wx2tox_msg_buffer) > 0:
            blen = len(self.wx2tox_msg_buffer)
            while len(self.wx2tox_msg_buffer) > 0:
                msg = self.wx2tox_msg_buffer.pop()
                mid = self.toxkit.sendMessage(self.peerToxId, msg)
                ### TODO 如果发送失败，这条消息可就丢失了。
            qDebug('send buffered wx2tox msg: %s' % blen)

        return

    def onToxnetFileChunkReuqest(self, friendId, file_number, position, length):
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
        print('or will send wx msg:%s,%s' % (groupchat.FromUser.Uin, groupchat.FromUser.NickName))

        if peer_number == 0:  # it myself sent message, omit
            pass
        else:
            self.sendMessageToWX(groupchat, message)
        return
    
    def startWXBot(self):
        if not self.checkWXLogin():
            qDebug('wxagent not logined.')
        else:
            qDebug('wxagent already logined.')
            
        ### 无论是否登陆，启动的都发送一次qrcode文件
        qrpic = self.getQRCode()
        fname = self.genQRCodeSaveFileName()
        self.saveContent(fname, qrpic)
        tkc = False
        if self.toxkit is not None:  tkc = self.toxkit.isConnected()
        if tkc is True:
            friendId = self.peerToxId
            fsize = len(qrpic)
            self.toxkit.fileSend(friendId, fsize, self.getBaseFileName(fname))
        else:
            self.qrpic = qrpic
            self.qrfile = fname
            self.need_send_qrfile = True
                
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

        self.saveContent('msgfromdbus.json', hcc)

        wxmsgvec = WXMessageList()
        wxmsgvec.setMessage(hcc)
        

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)

        AddMsgCount = jsobj['AddMsgCount']
        ModContactCount = jsobj['ModContactCount']

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
            logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::%s' % \
                     (msg.CreateTime, msg.MsgType, msg.FromUserName, fromUser_NickName,
                      msg.ToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

            self.sendMessageToTox(msg, logstr)
            
        return


    def sendMessageToTox(self, msg, fmtcc):
        fstatus = self.toxkit.friendGetConnectionStatus(self.peerToxId)
        if fstatus > 0:
            mid = self.toxkit.sendMessage(self.peerToxId, fmtcc)
            ### dispatch by MsgId
            self.dispatchToTox(msg, fmtcc)
        else:
            # self.wx2tox_msg_buffer.append(msg)
            pass

            
        return

    
    def dispatchToTox(self, msg, fmtcc):
        groupchat = None

        if msg.ToUserName == 'filehelper' or msg.FromUserName == 'filehelper':
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
        #         groupchat.title = '%s@WXU' % msg.ToUser.NickName
        #     else:
        #         groupchat.title = '%s@WXU' % msg.FromUser.NickName
                
        #     rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
        #     rc = self.toxkit.groupchatIniteFriend(group_number, self.peerToxId)
        #     if rc != 0: qDebug('invite error')

        # # assert groupchat is not None
        # rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
        # if rc != 0: qDebug('group chat send msg error')
        
        return

    def dispatchFileHelperChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''
        
        if msg.FromUserName == 'filehelper':
            mkey = msg.FromUser.Uin
            title = '%s@WXU' % msg.FromUser.NickName
        else:
            mkey = msg.ToUser.Uin
            title = '%s@WXU' % msg.ToUser.NickName

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
        else:
            group_number = self.toxkit.groupchatAdd()
            groupchat = Chatroom()
            groupchat.group_number = group_number
            groupchat.FromUser = msg.FromUser
            groupchat.ToUser = msg.ToUser
            self.wxchatmap[mkey] = groupchat
            self.toxchatmap[group_number] = groupchat
            groupchat.title = title
                
            rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
            rc = self.toxkit.groupchatIniteFriend(group_number, self.peerToxId)
            if rc != 0: qDebug('invite error')

        # assert groupchat is not None
        rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
        if rc != 0: qDebug('group chat send msg error')
        
        return

    def dispatchWXGroupChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        if msg.FromUserName.startswith('@@'):
            mkey = msg.FromUser.Uin
            title = '%s@WXU' % msg.FromUser.NickName
        else:
            mkey = msg.ToUser.Uin
            title = '%s@WXU' % msg.ToUser.NickName

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
        else:
            group_number = self.toxkit.groupchatAdd()
            groupchat = Chatroom()
            groupchat.group_number = group_number
            groupchat.FromUser = msg.FromUser
            groupchat.ToUser = msg.ToUser
            self.wxchatmap[mkey] = groupchat
            self.toxchatmap[group_number] = groupchat
            groupchat.title = title
                
            rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
            rc = self.toxkit.groupchatIniteFriend(group_number, self.peerToxId)
            if rc != 0: qDebug('invite error')

        # assert groupchat is not None
        rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
        if rc != 0: qDebug('group chat send msg error')

        return
    
    def dispatchU2UChatToTox(self, msg, fmtcc):
        groupchat = None
        mkey = None
        title = ''

        mkey = '%s&%s' %(msg.FromUser.Uin, msg.ToUser.Uin)
        title = '%s@WXU' % msg.FromUser.NickName

        if mkey in self.wxchatmap:
            groupchat = self.wxchatmap[mkey]
        else:
            group_number = self.toxkit.groupchatAdd()
            groupchat = Chatroom()
            groupchat.group_number = group_number
            groupchat.FromUser = msg.FromUser
            groupchat.ToUser = msg.ToUser
            self.wxchatmap[mkey] = groupchat
            self.toxchatmap[group_number] = groupchat
            groupchat.title = title
                
            rc = self.toxkit.groupchatSetTitle(group_number, groupchat.title)
            rc = self.toxkit.groupchatIniteFriend(group_number, self.peerToxId)
            if rc != 0: qDebug('invite error')

        # assert groupchat is not None
        rc = self.toxkit.groupchatSendMessage(groupchat.group_number, fmtcc)
        if rc != 0: qDebug('group chat send msg error')

        return

    
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

        
        if True: return
        from_username = groupchat.FromUser.UserName
        to_username = groupchat.ToUser.UserName
        args = [from_username, to_username, mcc, 1, 'more', 'even more']
        reply = self.iface.call('sendmessage', *args)  # 注意把args扩展开

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
        reply = self.iface.call('sendmessage', *args)  # 注意把args扩展开

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
        
        args = [to_username, from_username, mcc, 1, 'more', 'even more']
        reply = self.iface.call('sendmessage', *args)  # 注意把args扩展开

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
        reply = self.iface.call('sendmessage', *args)  # 注意把args扩展开

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

        reply = self.iface.call('getinitdata', 123, 'a1', 456)
        rr = QDBusReply(reply)
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode('utf8')   # to bytes
        data = QByteArray.fromBase64(data64)
        self.wxses.setInitData(data)
        self.saveContent('initdata.json', data)
        
        reply = self.iface.call('getcontact', 123, 'a1', 456)
        rr = QDBusReply(reply)
        qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
        data64 = rr.value().encode('utf8')   # to bytes
        data = QByteArray.fromBase64(data64)
        self.wxses.setContact(data)
        self.saveContent('contact.json', data)
        
        return

    def checkWXLogin(self):
        reply = self.iface.call('islogined', 'a0', 123, 'a1')
        qDebug(str(reply))
        rr = QDBusReply(reply)
        # TODO check rr.isValid()
        qDebug(str(rr.value()) + ',' + str(type(rr.value())))

        if rr.value() is False:
            return False
        
        return True

    def getQRCode(self):
        reply = self.iface.call('getqrpic', 123, 'a1', 456)
        rr = QDBusReply(reply)
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
        
    
def main():
    app = QApplication(sys.argv)
    import wxagent.qtutil as qtutil
    qtutil.pyctrl()

    w2t = WX2Tox()

    app.exec_()
    return


if __name__ == '__main__': main()



