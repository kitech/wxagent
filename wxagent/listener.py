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


class LisaListener(Listener):
    def __init__(self, toany):
        super(LisaListener, self).__init__(toany)
        self.role = self.ROLE_CHAT
        self.nol = Nolib()
        self.handlers = {'lisalisa': self.handlerLisalisa,
                         '.help': self.handlerHelp,
                         '.ping': self.handlerPing}
        return

    def onMessage(self, msg):
        qDebug('lisa is processing msg... ' + msg.MsgId)

        umsg = PlainMessage.fromWXMessage(msg, self.toany.txses)
        tmsg = umsg.dropprefix()

        for cmd in self.handlers.keys():
            if tmsg.startswith(cmd):
                qDebug('matched lisa cmd:' + cmd)
                room = self.toany.findGroupChatByMsg(msg)
                words = self.handlers[cmd]()
                words = self.fmtWords(words, umsg, msg)
                self.peerRelay.sendMessage(words, self.peerRelay.peer_user)
                self.toany.sendMessageToWX(room, words)
                break
        return

    def fmtWords(self, words, umsg, msg):
        if umsg.hasprefix():
            dispname = umsg.dispname(self.toany.txses).split('@')[0]
            words = "(Lisa) @%s: %s" % (dispname, words)
        else:
            words = "(Lisa) @%s: %s" % (msg.FromUser.NickName, words)
        return words

    def handlerHelp(self):
        words = ' '.join(self.handlers.keys())
        return words

    def handlerLisalisa(self):
        words = self.nol.getOne()
        return words

    def handlerPing(self):
        words = 'pong!'
        return words


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
