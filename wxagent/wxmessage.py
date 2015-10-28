
import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *

from .wxcommon import *

from .txmessage import *


class WXMessage(TXMessage):

    def __init__(self):
        "docstring"
        super(WXMessage, self).__init__()

        # for file field
        self.FileName = ''
        self.FileSize = 0
        self.MediaId = ''  # for file
        self.Url = ''

        # for voice field
        self.VoiceLength = 0

        return


class WXMessageList(TXMessageList):

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

