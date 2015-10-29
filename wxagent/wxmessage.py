
import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *

from .wxcommon import *

from .txmessage import *


class WXUser(TXUser):

    @staticmethod
    def fromJson(juser):
        user = WXUser()
        user.UserName = juser['UserName']
        user.NickName = juser['NickName']
        if 'HeadImgUrl' in juser: user.HeadImgUrl = juser['HeadImgUrl']

        return user

    def assignTo(self, to):
        f = self
        if len(f.UserName) > 0: to.UserName = f.UserName
        if len(f.NickName) > 0: to.NickName = f.NickName
        if len(f.HeadImgUrl) > 0: to.HeadImgUrl = f.HeadImgUrl
        return


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


# usage: WXMessageList().parse(rawmsg)
class WXMessageList(TXMessageList):

    def __init__(self):
        "docstring"
        self.rawMessage = b''  # QByteArray
        self.jsonMessage = {}

        return

    # @param message QByteArray
    def parseit(self, rawmsg):
        self.rawMessage = rawmsg

        hcc = self.rawMessage
        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.jsonMessage = jsobj

        return self

    def isValid(self):
        if self.jsonMessage['BaseResponse']['Ret'] == 0:
            return True
        return False

    def hasAddMsg(self):
        if self.jsonMessage['AddMsgCount'] > 0:
            return True
        return False

    def hasModContact(self):
        if self.jsonMessage['ModContactCount'] > 0:
            return True
        return False

    def hasDelContact(self):
        if self.jsonMessage['DelContactCount'] > 0:
            return True
        return False

    def hasModChatRoomMember(self):
        if self.jsonMessage['ModChatRoomMemberCount'] > 0:
            return True
        return False

    def getAddMsgList(self):
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
            msg = self._parseMessageUnit(um)
            msgs.append(msg)

        return msgs

    def _parseMessageUnit(self, um):
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

    def getModContactList(self):
        return

    def getDelContactList(self):
        return

    def getModChatRoomMemberList(self):
        return
