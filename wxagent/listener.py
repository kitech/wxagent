import os, sys
import json, re
import enum, copy

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *

from .unimessage import PlainMessage
from .botcmd import BotCmder
from .nolib import Nolib


class Listener(QObject):
    # listener角色，控制能够插入的事件点
    ROLE_NONE = 0
    ROLE_CTRL = 1
    ROLE_CHAT = 2

    def __init__(self, toany):
        self.toany = toany
        self.peerRelay = toany.peerRelay
        self.role = self.ROLE_NONE
        return

    def onMessage(self, msg):
        return

    def onRelayGroupMessage(self, room, msg):
        return


class CtrlListener(Listener):
    def __init__(self, toany):
        super(CtrlListener, self).__init__(toany)
        self.role = self.ROLE_CTRL
        return

    def onMessage(self, msg):

        cmd = BotCmder.parseCmd(msg)
        if cmd is False:
            qDebug(('not a valid cmd: %s' % msg[0:120]).encode())
            return

        if cmd[0] == 'help':
            helpmsg = BotCmder.helpMessage()
            self.peerRelay.sendMessage(helpmsg, self.peerRelay.peer_user)

        elif cmd[0] == 'invite':
            if cmd[1] == '':  # 发送所有的好友，注意是真正的已添加的好友，不是在群组里面的。
                nnlst = self.toany.txses.getInviteCompleteList()
                nnlst = list(map(lambda x: '*) ' + x, nnlst))
                self.peerRelay.sendMessage('    '.join(nnlst), self.peerRelay.peer_user)
            else:
                # 查找是否有该好友，
                # 如果有，则创建与该好友的聊天室
                # 如果没有，则查找是否有前相似匹配的
                # 如果有相似匹配的，则提示相似匹配的所有好友
                nnlst = self.toany.txses.getInviteCompleteList(cmd[1])
                nnlen = len(nnlst)
                if nnlen == 0:
                    qDebug(('not found:' + cmd[1]).encode())
                    rpstr = 'no user named: ' + cmd[1]
                    self.peerRelay.sendMessage(rpstr, self.peerRelay.peer_user)
                elif nnlen == 1:
                    qDebug(('exact match found:' + cmd[1] + ',' + str(nnlst[0])).encode())
                    rpstr = 'inviteing %s......' % nnlst[0]
                    self.peerRelay.sendMessage(rpstr, self.peerRelay.peer_user)
                    self.toany.inviteFriendToChat(nnlst[0])
                else:
                    qDebug(('multi match found:' + cmd[1]).encode())
                    nnlst = list(map(lambda x: '*) ' + x, nnlst))
                    self.peerRelay.sendMessage('    '.join(nnlst), self.peerRelay.peer_user)

        elif cmd[0] == 'stats':
            stats = self.toany.getAgentRuntimeStats()
            self.peerRelay.sendMessage(stats, self.peerRelay.peer_user)
        else:
            qDebug('unknown cmd:' + str(cmd))
        return


class RecordListener(Listener):
    def __init__(self, toany):
        super(RecordListener, self).__init__(toany)
        self.role = self.ROLE_CHAT
        return

    def onMessage(self, msg):
        qDebug('recording msg... ' + msg.MsgId)
        return


class HandlerContext:
    def __init__(self, cmd, pmsg, room, txmsg, umsg):
        self.cmd = cmd
        self.pmsg = pmsg
        self.txmsg = txmsg
        self.umsg = umsg
        self.room = room
        return


class LisaListener(Listener):
    def __init__(self, toany):
        super(LisaListener, self).__init__(toany)
        self.role = self.ROLE_CHAT
        self.nol = Nolib()
        self.handlers = {'lisalisa': self.handlerLisalisa,
                         '.help': self.handlerHelp,
                         '.ping': self.handlerPing,
                         '.abbr': self.handlerAbbrev,
                         '.ytran': self.handlerYTran,
                         '.lisa': self.handlerLisaChat}
        return

    def onMessage(self, msg):
        qDebug('lisa is processing msg... ' + msg.MsgId)

        umsg = PlainMessage.fromWXMessage(msg, self.toany.txses)
        tmsg = umsg.dropprefix()

        for cmd in self.handlers.keys():
            if tmsg.startswith(cmd):
                qDebug('matched lisa cmd:' + cmd)
                room = self.toany.findGroupChatByMsg(msg)
                ctx = HandlerContext(cmd, tmsg, room, msg, umsg)
                words = self.handlers[cmd](tmsg, ctx)
                words = self.fmtWords(words, msg, umsg)
                self.peerRelay.sendMessage(words, self.peerRelay.peer_user)
                self.toany.sendMessageToWX(room, words)
                break
        return

    def onRelayGroupMessage(self, room, msg):
        qDebug('lisa is processing relay msg...' + str(room.group_number))

        tmsg = msg
        for cmd in self.handlers.keys():
            if tmsg.startswith(cmd):
                qDebug('matched lisa cmd:' + cmd)
                ctx = HandlerContext(cmd, tmsg, room, None, None)
                words = self.handlers[cmd](msg, ctx)
                words = self.fmtWords(words, msg, None)
                # self.peerRelay.sendMessage(words, self.peerRelay.peer_user)
                self.peerRelay.sendGroupMessage(words, room.group_number)
                self.toany.sendMessageToWX(room, words)
                # 上面的顺序，还是要这样的，否则可能导致wx中消息顺序不对
                break
        return

    def fmtWords(self, words, msg, umsg=None):
        if umsg is None:
            words = "(Lisa) @%s: %s" % (self.toany.txses.me.NickName, words)
        elif umsg.hasprefix():
            dispname = umsg.dispname(self.toany.txses).split('@')[0]
            words = "(Lisa) @%s: %s" % (dispname, words)
        else:
            words = "(Lisa) @%s: %s" % (msg.FromUser.NickName, words)
        return words

    def handlerHelp(self, msg=None, ctx=None):
        words = ' '.join(self.handlers.keys())
        return words

    def handlerLisalisa(self, msg=None, ctx=None):
        words = self.nol.getOne()
        return words

    def handlerLisaChat(self, msg, ctx):
        import hashlib
        h = hashlib.md5()
        h.update(b'memememmememe')
        if ctx.room.FromUser.UserName != self.toany.txses.me.UserName:
            h.update(ctx.room.FromUser.UserName.encode())
        else:
            # should be me
            h.update(self.toany.txses.me.UserName.encode())
        sum = h.hexdigest()
        reqmsg = msg[len(ctx.cmd):].strip()
        # print(12222222222, msg, reqmsg)
        reply = self.nol.tlchat(reqmsg, sum)
        return reply

    def handlerPing(self, msg=None, ctx=None):
        words = 'pong!'
        return words

    # @param msg str
    def handlerAbbrev(self, msg, ctx=None):
        word = msg.strip().split(' ')[1]
        unabbrevs = self.nol.unabbrev(word)
        if unabbrevs is None:
            return 'error occurs'
        return ' '.join(unabbrevs)

    def handlerYTran(self, msg, ctx=None):
        word = msg.strip().split(' ')[1]
        zhres = self.nol.tran('ytran', word)
        return zhres


class ListenerFactory:
    listeners = ['ctrl', 'record', 'lisa']

    def create(name, toany):
        if name == 'ctrl':
            return CtrlListener(toany)
        elif name == 'record':
            return RecordListener(toany)
        elif name == 'lisa':
            return LisaListener(toany)
        return None
