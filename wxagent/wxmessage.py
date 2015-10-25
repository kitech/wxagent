
import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *

from .wxcommon import *


class WXUser():
    def __init__(self):
        "docstring"

        self.Uin = 0  # temporary use
        self.UserName = ''
        self.NickName = ''
        self.HeadImgUrl = ''

        self.members = {}  # user name -> WXUser
        return

    # signature1: u.isGroup()
    # signature1: WXUser.isGroup(name)
    def isGroup(p0, p1 = None):
        if type(p0) is WXUser:  # self = p0
            return p0.UserName.startswith('@@')
        return p0.startswith('@@')

    def isMPSub(self):
        return self.HeadImgUrl == ''

    def cname(self):
        if self.UserName in ['filehelper', 'newsapp', 'fmessage']:
            return self.UserName
        if len(self.UserName) < 16:  # maybe a special name
            return self.UserName
        return self.UserName.strip('@')[0:7]


class WXMessage():

    def __init__(self):
        "docstring"

        self.MsgType = 0
        self.MsgId = ''
        self.FromUserName = ''
        self.ToUserName = ''
        self.CreateTime = 0
        self.Content = ''
        self.UnescapedContent = ''

        self.FromUser = None
        self.ToUser = None

        self.jsonContent = {}

        # for file field
        self.FileName = ''
        self.FileSize = 0
        self.MediaId = ''  # for file
        self.Url = ''

        # for voice field
        self.VoiceLength = 0

        return

    def isOffpic(self):
        return False

    def isFileMsg(self):
        return False


class WXMessageList():

    def __init__(self):
        "docstring"
        self.rawMessage = b''  # QByteArray
        self.jsonMessage = {}
        return

    # @param message QByteArray
    def setMessage(self, message):
        self.rawMessage = message
        self.parseMessageList()
        return

    def parseMessageList(self):
        hcc = self.rawMessage

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.jsonMessage = jsobj

        AddMsgCount = jsobj['AddMsgCount']
        ModContactCount = jsobj['ModContactCount']

        return

    def getContent(self):
        jsobj = self.jsonMessage

        msgs = []
        for um in jsobj['AddMsgList']:
            tm = 'MT:%s,' % (um['MsgType'])   # , um['Content'])
            # try:
            #     tm = ':::,MT:%s,%s' % (um['MsgType'], um['Content'])
            #     qDebug(str(tm))
            # except Exception as ex:
            #     # qDebug('can not show here')
            #     rct = um['Content']
            #     print('::::::::::,MT', um['MsgType'], str(type(rct)), rct)

            #######
            msg = self.parseMessageUnit(um)
            msgs.append(msg)

        return msgs

    def parseMessageUnit(self, um):
        msg = WXMessage()
        msg.jsonContent = um

        msg.MsgType = um['MsgType']
        msg.Content = um['Content']
        msg.UnescapedContent = html.unescape(msg.Content)
        msg.MsgId = um['MsgId']
        msg.CreateTime = um['CreateTime']
        msg.ToUserName = um['ToUserName']
        msg.FromUserName = um['FromUserName']

        if msg.MsgType == WXMsgType.MT_X49:
            msg.FileName = um['FileName']
            msg.FileSize = um['FileSize']
            msg.MediaId = um['MediaId']
            msg.Url = um['Url']
        elif msg.MsgType == WXMsgType.MT_VOICE:
            msg.VoiceLength = um['VoiceLength']

        logstr = '[%s][%s] %s => %s @%s:::%s' % \
                 (msg.CreateTime, msg.MsgType, msg.FromUserName, msg.ToUserName, msg.MsgId, msg.UnescapedContent)
        print(logstr)

        return msg

