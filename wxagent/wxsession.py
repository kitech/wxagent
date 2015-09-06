
import os, sys
import json, re
import enum
import html

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
        self.me = None  # WXUser

        self.members = {}  # user name -> WXUser
        
        return

    # @param member json's member node
    def addMember(self, member):
        user = WXUser()
        user.Uin = member['Uin']
        user.UserName = member['UserName']
        user.NickName = member['NickName']

        self.members[user.UserName] = user
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
        self.UnescapedContent = ''

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
        msg.UnescapedContent = html.unescape(msg.Content)
        msg.MsgId = um['MsgId']
        msg.CreateTime = um['CreateTime']
        msg.ToUserName = um['ToUserName']
        msg.FromUserName = um['FromUserName']

        logstr = '[%s][%s] %s => %s @%s:::%s' % \
                 (msg.CreateTime, msg.MsgType, msg.FromUserName, msg.ToUserName, msg.MsgId, msg.UnescapedContent)
        print(logstr)
        
        return msg

    
class WXSession():

    def __init__(self):
        "docstring"

        self.InitRawData = b''  # QByteArray
        self.InitData = {}

        self.ContactRawData = b''  # QByteArray
        self.ContactData = {}

        self.me = None   # WXUser
        self.Groups = {}  # group name => WXGroup
        self.Members = {}  # user name => WXUser

        ### maybe temporary
        self.InitGroups = {}  #
        self.OtherGroups = {}  # group name => 1
        
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

        self._parseInitGroups()
        return

    def _parseInitGroups(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        for member in self.InitData['ContactList']:
            tname = member['UserName']
            if tname.startswith('@@'):
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']

                self.InitGroups[tname] = user
            
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
        groups = []
        for member in self.InitData['ContactList']:
            tname = member['UserName']
            groups.append([member['UserName'],member['NickName']])
            if tname == name:
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']
                return user

        qDebug("can not find user:" + str(name))
        print(str(groups))
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


    def addGroupNames(self, GroupNames):
        for name in GroupNames:
            self.OtherGroups[name] = 1
        return
    
    def getInitGroups(self):
        grnames = []
        for gr in self.InitGroups:
            user = self.InitGroups[gr]
            grnames.append(gr)
        return grnames

    def getAllGroups(self):
        grnames = self.getInitGroups()
        for name in self.OtherGroups:
            if name not in grnames:
                grnames.append(name)
        return grnames

    # 返回InitData中以@@开关的项
    def getGroups(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        grnames = []
        for member in self.InitData['ContactList']:
            tname = member['UserName']
            if tname.startswith('@@'):
                user = WXUser()
                user.Uin = member['Uin']
                user.UserName = member['UserName']
                user.NickName = member['NickName']
                user.HeadImgUrl = member['HeadImgUrl']
                group = WXGroup()
                group.me = user
                self.Groups[user.UserName] = group
                grnames.append(user.UserName)
                
        return grnames
    
    def getGroupMembers(self, GroupName):
        if GroupName not in self.Groups:
            qDebug('wtf???' + str(GroupName))
            return None

        members = []
        for contact in self.InitData['ContactList']:
            tname = contact['UserName']
            if tname == GroupName:
                mc = contact['MemberCount']
                qDebug(str(mc))
                for member in contact['MemberList']:
                    members.append(member['UserName'])
                break

        return members

    def getGroupByName(self, GroupName):
        if GroupName not in self.Groups:
            qDebug('wtf???' + str(GroupName))
            return None
        return self.Groups[GroupName]

    def addGroupUser(self, GroupName, obj):
        user = WXUser()
        user.Uin = obj['Uin']
        user.UserName = obj['UserName']
        user.NickName = obj['NickName']

        self.Groups[GroupName] = user
        return

    # 不一定是好友的情况
    def getUserInfo(self, UserName):
        if UserName not in self.Members:
            qDebug('wtf???' + str(UserName))
            return None
        return self.Members[UserName]

    # 不一定是好友的情况
    def getUserInfo_dep(self, UserName):
        for group in self.Groups:
            if UserName in group.members:
                return group.members[UserName]
        qDebug('user not found:' + UserName)
        return None

    # @param member json's member node
    def addMember(self, member):
        user = WXUser()
        user.Uin = member['Uin']
        user.UserName = member['UserName']
        user.NickName = member['NickName']

        self.Members[user.UserName] = user
        return
