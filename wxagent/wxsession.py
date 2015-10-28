
import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *

from .wxcommon import *
from .wxmessage import *


class WXSession():

    def __init__(self):
        "docstring"

        self.InitRawData = b''  # QByteArray
        self.InitData = {}

        self.ContactRawData = b''  # QByteArray
        self.ContactData = {}

        self.me = None   # WXUser
        self.Users = {}  # user name => WXUser

        # incomplete information
        self.ICUsers = {}  # user name => WXUser，信息不完全的的用户
        self.ICGroups = {}  # user name = > WXUser, 信息不完全的组

        # ## maybe temporary

        return

    # @param initData QByteArray
    def setInitData(self, initData):
        self.InitRawData = initData
        self.parseInitData()
        return

    def parseInitData(self):
        hcc = self.InitRawData

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n").encode())
        jsobj = json.JSONDecoder().decode(strhcc)
        self.InitData = jsobj

        self._parseInitAboutMe()
        self._parseInitGroups()
        self._parseInitGroupMembers()
        return

    def _parseInitAboutMe(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        uo = self.InitData['User']
        user = WXUser()
        user.UserName = uo['UserName']
        user.NickName = uo['NickName']
        user.HeadImgUrl = uo['HeadImgUrl']

        self.me = user
        return

    def _parseInitGroups(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        # ## InitData中的group都是有info的记录，直接存储在Users中
        cnt = 0
        for user in self.parseUsers(self.InitData['ContactList']):
            self.Users[user.UserName] = user

            if not user.isGroup(): continue
            self.ICGroups[user.UserName] = user
            cnt += 1

        qDebug('got %s groups from init data ' % str(cnt))
        return

    def _parseInitGroupMembers(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        cnt = 0
        # ## InitData中的group都是有info的记录，直接存储在Users中
        for uo in self.InitData['ContactList']:
            user = self.Users[uo['UserName']]
            for mo in self.parseUsers(uo['MemberList']):
                self.ICUsers[mo.UserName] = mo
                user.members[mo.UserName] = mo
                cnt += 1

        qDebug('got %s groups members(not complete) from init data' % str(cnt))
        return

    def _parseInitMPSubs(self):
        mc = self.InitData['Count']
        qDebug(str(mc))

        # ## InitData中的group都是有info的记录，直接存储在Users中
        for uo in self.InitData['MPSubscribeMsgList']:
            user = WXUser()
            user.UserName = uo['UserName']
            user.NickName = uo['NickName']

            self.Users[user.UserName] = user

        return

    # @param contact QByteArray
    def setContact(self, contact):
        self.ContactRawData = contact
        self.parseContact()
        return

    def parseContact(self):
        hcc = self.ContactRawData

        strhcc = hcc.data().decode('utf8')
        qDebug(strhcc[0:120].replace("\n", "\\n").encode())
        jsobj = json.JSONDecoder().decode(strhcc)
        self.ContactData = jsobj

        #######
        upcnt = 0
        newcnt = 0
        totcnt = 0  # total cnt
        for user in self.parseUsers(jsobj['MemberList']):
            if user.UserName in self.ICUsers: self.ICUsers.pop(user.UserName)

            if user.UserName in self.Users:
                self._assignUser(self.Users[user.UserName], user)
                upcnt += 1
            else:
                self.Users[user.UserName] = user
                newcnt += 1
            totcnt += 1

        qDebug('got users, up:%s, new:%s, tot:%s' % (upcnt, newcnt, totcnt))

        return

    # @param contact  jsobj['ModContactList']
    def parseModContact(self, modcontact):
        for contact in modcontact:
            user = self._contactElemToUser(contact)

            # ## 准备下次获取该群组信息
            if user.UserName not in self.Users:
                self.addGroupNames([user.UserName])

            if user.UserName in self.ICGroups: self.ICGroups.pop(user.UserName)

            if user.UserName not in self.Users:
                self.Users[user.UserName] = user
            else:
                self._assignUser(self.Users[user.UserName], user)

            #########
            guser = self.Users[user.UserName]
            # ## 更新群组成员列表
            for subuser in self.parseUsers(contact['MemberList']):
                if subuser.UserName in self.ICUsers: self.ICUsers.pop(subuser.UserName)

                if subuser.UserName not in self.Users:
                    self.Users[subuser.UserName] = subuser
                else:
                    self._assignUser(self.Users[subuser.UserName], subuser)

                # 加入到group的members列表中
                if subuser.UserName not in guser.members:
                    guser.members[subuser.UserName] = subuser

        return

    # TODO
    # @param contact  jsobj['DelContactList']
    def parseDelContact(self, delcontact):

        return

    # TODO
    # @param contact  jsobj['ModChatRoomMemberList']
    def parseModChatRoomMemberList(self, modmembers):

        return

    def _assignUser(self, t, f):
        if len(f.UserName) > 0: t.UserName = f.UserName
        if len(f.NickName) > 0: t.NickName = f.NickName
        if len(f.HeadImgUrl) > 0: t.HeadImgUrl = f.HeadImgUrl
        return

    def _contactElemToUser(self, elem):
        uo = elem

        user = WXUser()
        user.UserName = uo['UserName']
        user.NickName = uo['NickName']
        if 'HeadImgUrl' in uo: user.HeadImgUrl = uo['HeadImgUrl']

        return user

    # @param contact, hccjs['ContactList'] or hccjs['MemberList']
    def parseUsers(self, contact):
        for uo in contact:
            user = self._contactElemToUser(uo)
            yield user

        return

    # @param name str  UserName, like @xxx
    def getUserByName(self, name):
        if WXUser.isGroupName(name): return self.getUserByGroupName(name)

        mc = self.ContactData['MemberCount']
        qDebug(str(mc))

        if name in self.Users: return self.Users[name]
        qDebug("can not find user:" + str(name))
        return None

    # @param name str  UserName, like @@xxx
    def getUserByGroupName(self, name):
        mc = self.InitData['Count']
        qDebug(str(mc))

        if name in self.Users: return self.Users[name]
        qDebug("can not find user:" + str(name))
        return

    # TODO 有可能重名呢？咋办？
    # @param nick str 用户NickName
    # @return WXUser object
    def getUserByNickName(self, nick):
        for tk in self.Users:
            user = self.Users[tk]
            if user.NickName == nick:
                return user
        qDebug(('why not found:' + nick).encode())
        return None

    def addGroupNames(self, GroupNames):
        for name in GroupNames:
            user = WXUser()
            user.UserName = name
            self.ICGroups[name] = user
        return

    def getICGroups(self):
        grnames = []
        gkeys = self.ICGroups.keys()
        for k in gkeys:
            if WXUser.isGroupName(k):
                grnames.append(k)

        return grnames

    def getGroupMembers(self, GroupName):
        if GroupName not in self.Users:
            qDebug('wtf???' + str(GroupName))
            return []

        members = []
        qDebug(str(self.Users[GroupName]))
        for mkey in self.Users[GroupName].members:
            if type(mkey) is int: continue  #
            user = self.Users[GroupName].members[mkey]
            members.append(user.UserName)

        return members

    def getGroupByName(self, GroupName):
        if GroupName not in self.Users:
            qDebug('wtf???' + str(GroupName))
            return None
        return self.Users[GroupName]

    def addGroupUser(self, GroupName, obj):
        user = WXUser()
        user.UserName = obj['UserName']
        user.NickName = obj['NickName']

        if user.UserName not in self.Users:
            self.Users[user.UserName] = user

        # 在这还不能从此拿出，因为这个调用无法保证group中所有member信息都是全面的。
        # if user.UserName in self.ICGroups: self.ICGroups.pop(user.UserName)
        return

    # 不一定是好友的情况
    def getUserInfo(self, UserName):
        if UserName not in self.Users:
            qDebug('wtf???' + str(UserName))
            if UserName not in self.ICUsers:
                qDebug('wtf???' + str(UserName))
                return None
            else:
                return self.ICUsers[UserName]
        else:
            return self.Users[UserName]

    # @param member json's member node
    def addMember(self, member):
        user = WXUser()
        user.UserName = member['UserName']
        user.NickName = member['NickName']

        if user.UserName not in self.Users:
            self.Users[user.UserName] = user

        if user.UserName in self.ICUsers: self.ICUsers.pop(user.UserName)
        return

    # user对象还无NickName的，这种的无法在UI上正常显示NickName
    def checkUncompleteUsers(self):

        cnt = 0
        for uname in self.Users:
            if type(uname) is not str: continue
            user = self.Users[uname]
            if user.NickName == '':
                cnt += 1

        qDebug('uncomplete users cnt/total: %s/%s' % (str(cnt), str(len(self.Users))))
        return

    # TODO 如果NickName重名，应该怎么办呢？
    # @param prefix str
    # @return list of real friend and groups NickName
    def getInviteCompleteList(self, prefix=None):
        jsobj = self.ContactData

        #######
        nnlst = []
        if prefix is not None:
            prefix = prefix.strip()
        for user in self.parseUsers(jsobj['MemberList']):
            if prefix is not None:
                if user.NickName.startswith(prefix):
                    nnlst.append(user.NickName)
            else:
                nnlst.append(user.NickName)

        return nnlst
