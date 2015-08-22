
import os, sys
import json, re
import enum

from PyQt5.QtCore import *


class WXUser():
    def __init__(self):
        "docstring"

        self.Uin = 0
        self.UserName = ''
        self.NickName = ''
        self.HeadImgUrl = ''
        
        return
        
class WXGroup():
    def __init__(self):
        "docstring"

        return

    
class WXMessage():

    def __init__(self):
        "docstring"
        
        self.MsgType = 0
        self.MsgId = ''
        self.FromUserName = ''
        self.ToUserName = ''
        self.CreateTime = 0
        self.Content = ''

        self.FromUser = None
        self.ToUser = None

        self.jsonContent = {}

        return

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
        msg.MsgId = um['MsgId']
        msg.CreateTime = um['CreateTime']
        msg.ToUserName = um['ToUserName']
        msg.FromUserName = um['FromUserName']

        logstr = '[%s][%s] %s => %s @%s:::%s' % \
                 (msg.CreateTime, msg.MsgType, msg.FromUserName, msg.ToUserName, msg.MsgId, msg.Content)
        print(logstr)
        
        return msg

    
class WXSession():

    def __init__(self):
        "docstring"

        self.InitRawData = b''  # QByteArray
        self.InitData = {}

        self.ContactRawData = b''  # QByteArray
        self.ContactData = {}

        return

    # @param initData QByteArray
    def setInitData(self, initData):
        self.InitRawData = initData
        self.parseInitData()
        return

    def parseInitData(self):
        hcc = self.InitRawData
        
        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.InitData = jsobj

        return
    
    # @param contact QByteArray
    def setContact(self, contact):
        self.ContactRawData = contact
        self.parseContact()
        return

    def parseContact(self):
        hcc = self.ContactRawData
        
        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.ContactData = jsobj

        return

    # @param name str  UserName, like @xxx
    def getUserByName(self, name):
        if name.startswith('@@'): return self.getUserByGroupName(name)
        
        mc = self.ContactData['MemberCount']
        qDebug(str(mc))
        for member in self.ContactData['MemberList']:
            tname = member['UserName']
            if tname == name:
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']
                return user

        qDebug("can not find user:" + str(name))
        return None

    # @param name str  UserName, like @@xxx
    def getUserByGroupName(self, name):
        mc = self.InitData['Count']
        qDebug(str(mc))
        for member in self.InitData['ContactList']:
            tname = member['UserName']
            if tname == name:
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']
                return user

        qDebug("can not find user:" + str(name))
        return

    # @param uin int
    def getUserByUin(self, uin):

        mc = self.ContactData['MemberCount']
        qDebug(str(mc))
        for member in self.ContactData['MemberList']:
            tuin = member['Uin']
            if tuin == uin:
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']
                return user

        qDebug("can not find user:" + str(uin))
        return None

        
