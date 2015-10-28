
import os, sys
import json, re
import enum
import html

from PyQt5.QtCore import *
from .qqcom import *

from .txmessage import *


class QQMessage(TXMessage):

    def __init__(self):
        "docstring"
        super(QQMessage, self).__init__()

        # for qq group mess
        self.PollType = QQ_PT_NONE
        self.Gid = 0
        self.ServiceType = 0

        self.offpic = None

        # for qq recv file
        self.FileName = ''
        self.FileType = ''
        self.FileMode = ''
        self.FileCancelType = 0
        return

    def isOffpic(self):
        return self.offpic is not None

    def isFileMsg(self):
        return self.PollType == QQ_PT_FILE and self.FileMode == 'recv'


class QQMessageList(TXMessageList):

    def __init__(self):
        "docstring"
        super(QQMessageList, self).__init__()

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

        return

    def getContent(self):
        jsobj = self.jsonMessage

        msgs = []
        for um in jsobj['result']:
            tm = 'MT:%s,' % (um['poll_type'])   # , um['Content'])
            mpt = self.pollTypeToConst(um['poll_type'])

            # TODO 暂时忽略处理的消息类型
            omit_poll_types = ['kick_message', 'input_notify',
                               'buddies_status_change', 'tips', 'shake_message']
            if um['poll_type'] in omit_poll_types:
                qDebug(tm)
                continue

            #######
            msg = self.parseMessageUnit(um)
            msgs.append(msg)

        return msgs

    # group_message:
    # {'value': {'msg_id2': 39870,
    # 'to_uin': 1449732709, 'group_code': 566854938,
    # 'send_uin': 1769524962, 'msg_type': 43,
    # 'content': [['font', {'size': 11, 'name': 'Tahoma', 'color': '000000', 'style': [0, 0, 0]}], 'vvv '],
    # 'reply_ip': 176884841, 'time': 1441451443, 'from_uin': 2905310716, 'seq': 2086,
    # 'msg_id': 4970, 'info_seq': 143094421}, 'poll_type': 'group_message'}
    def parseMessageUnit(self, um):
        msg = QQMessage()
        msg.jsonContent = um

        qDebug('here')
        print(um)

        umval = um['value']
        msg.MsgType = umval['msg_type'] if 'msg_type' in umval else 0

        if 'content' in um['value']:
            clen = len(um['value']['content'])
            msg.Content = um['value']['content'][clen-1]   # 最后一个
            mfont, *mcontents = um['value']['content']  # hoho, got from cookbook
            # TODO mface => bbcode
            newmcontents = ''
            for mc in mcontents:
                if type(mc) is not str: newmcontents += str(mc)
                else: newmcontents += mc
                if type(mc) is not str and 'offpic' in mc: msg.offpic = mc[1]['file_path']

            msg.Content = newmcontents
            msg.UnescapedContent = html.unescape(msg.Content)

        msg.MsgId = um['value']['msg_id']
        msg.CreateTime = um['value']['time']
        msg.ToUserName = str(um['value']['to_uin'])
        msg.FromUserName = str(um['value']['from_uin'])

        # poll type
        msg.PollType = self.pollTypeToConst(um['poll_type'])
        if msg.PollType == QQ_PT_SESSION:
            msg.Gid = str(um['value']['id'])   # 是所有的消息都有这项吗？
            msg.ServiceType = str(um['value']['service_type'])
        elif msg.PollType == QQ_PT_FILE:
            msg.FileName = umval['name'] if 'name' in umval else ''
            msg.FileType = umval['type']
            msg.FileMode = umval['mode']
            msg.FileCancelType = umval['cancel_type'] if 'cancel_type' in umval else 0
        elif msg.PollType == QQ_PT_USER:
            pass

        logstr = '[%s][%s] %s => %s @%s:::%s' % \
                 (msg.CreateTime, msg.MsgType, msg.FromUserName, msg.ToUserName, msg.MsgId, msg.UnescapedContent)
        # print(logstr)

        return msg

    # @param ty str
    def pollTypeToConst(self, pty):
        if pty == 'sess_message': return QQ_PT_SESSION
        elif pty == 'discu_message': return QQ_PT_DISCUS
        elif pty == 'qun_message': return QQ_PT_QUN
        elif pty == 'user_message': return QQ_PT_USER
        elif pty == 'message': return QQ_PT_USER
        elif pty == 'kick_message': return QQ_PT_KICK
        elif pty == 'buddies_status_change': return QQ_PT_STATUS
        elif pty == 'input_notify': return QQ_PT_INPUT_NOTIFY
        elif pty == 'tips': return QQ_PT_TIPS
        elif pty == 'file_message': return QQ_PT_FILE
        elif pty == 'shake_message': return QQ_PT_SHAKE
        elif pty == 'av_request': return QQ_PT_AV_REQUEST
        elif pty == 'av_refuse': return QQ_PT_AV_REFUSE
        else:
            qDebug('unknown poll type:' + pty)
            return QQ_PT_NONE


class WXSession():

    def __init__(self):
        "docstring"

        self.SelfRawInfo = b''  # QByteArray
        self.SelfInfo = {}
        self.InitRawData = b''  # QByteArray
        self.InitData = {}

        self.ContactRawData = b''  # QByteArray
        self.ContactData = {}

        self.me = None   # QQUser
        self.Users = {}  # user name => QQUser

        # incomplete information
        self.ICUsers = {}  # user name => QQUser，信息不完全的的用户
        self.ICGroups = {}  # user name = > QQUser, 信息不完全的组

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

        self._parseInitAboutMe()
        self._parseInitGroups()
        self._parseInitGroupMembers()
        return

    def setSelfInfo(self, info):
        self.SelfRawInfo = info

        hcc = self.SelfRawInfo
        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.SelfInfo = jsobj

        self._parseInitAboutMe()
        return

    def _parseInitAboutMe(self):

        uo = self.SelfInfo['result']
        user = QQUser()
        user.Uin = uo['uin']
        user.UserName = str(uo['uin'])
        user.NickName = uo['nick']
        user.HeadImgUrl = uo['face']
        user.UserType = USER_TYPE_USER

        self.me = user
        self.Users[user.Uin] = user
        self.Users[user.UserName] = user

        return

    def setUserFriends(self, friends):
        self.rawFriends = friends

        self._parseUserFriends()
        return

    def _parseUserFriends(self):
        hcc = self.rawFriends

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.friendsData = jsobj

        for user in self.parseUsers(jsobj['result']['info']):
            qDebug('got friend:' + str(user.NickName))
            if user.Uin in self.ICUsers: self.ICUsers.pop(user.Uin)
            if user.UserName in self.ICUsers: self.ICUsers.pop(user.UserName)

            if user.UserName in self.Users:
                self._assignUser(self.Users[user.UserName], user)
                self.Users[user.Uin] = self.Users[user.UserName]
            else:
                self.Users[user.UserName] = user
                self.Users[user.Uin] = user

        return

    def _assignUser(self, t, f):
        if f.Uin > 0: t.Uin = f.Uin
        if len(f.UserName) > 0: t.UserName = f.UserName
        if len(f.NickName) > 0: t.NickName = f.NickName
        if len(f.HeadImgUrl) > 0: t.HeadImgUrl = f.HeadImgUrl
        t.UserType = f.UserType

        return

    def _contactElemToUser(self, elem):
        uo = elem

        user = QQUser()
        if 'uin' in uo: user.Uin = uo['uin']
        else: print('warning contact has not Uin: %s:%s' % (uo['nick'][0:8], uo['nick']))
        user.UserName = str(uo['uin'])
        user.NickName = uo['nick']
        user.UserType = USER_TYPE_USER
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
        # TODO 对QQ来说，这是不必须的判断，也判断不出来
        if QQUser.isGroup(name): return self.getUserByGroupName(name)

        mc = len(self.friendsData['result']['info'])
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

    # @param uin int
    def getUserByUin(self, uin):
        if uin in self.Users: return self.Users[uin]
        qDebug("can not find user:" + str(uin))
        return None

    def setGroupList(self, glist):
        self.GroupRawList = glist

        self._parseGroupList()
        return

    def _parseGroupList(self):
        hcc = self.GroupRawList

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n").encode())
        jsobj = json.JSONDecoder().decode(strhcc)
        self.GroupList = jsobj

        for grp in jsobj['result']['gnamelist']:
            user = QQUser()
            user.Uin = grp['code']
            user.UserName = str(grp['gid'])
            user.NickName = grp['name']
            user.UserType = USER_TYPE_GROUP
            qDebug(b'got group:' + str(user.NickName).encode())

            self.Users[user.Uin] = user
            self.Users[user.UserName] = user

        return

    def setDiscusList(self, dlist):
        self.DiscusRawList = dlist

        self._parseDiscusList()
        return

    def _parseDiscusList(self):
        hcc = self.DiscusRawList

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n").encode())
        jsobj = json.JSONDecoder().decode(strhcc)
        self.GroupList = jsobj

        for grp in jsobj['result']['dnamelist']:
            user = QQUser()
            user.Uin = grp['did']
            user.UserName = str(grp['did'])
            user.NickName = grp['name']
            user.UserType = USER_TYPE_DISCUS
            qDebug(b'got discus:' + str(user.NickName).encode())

            self.Users[user.Uin] = user
            self.Users[user.UserName] = user

        return

    def setGroupDetail(self, info):
        hcc = info

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n").encode())
        jsobj = json.JSONDecoder().decode(strhcc)
        self.GroupList = jsobj

        for um in jsobj['result']['minfo']:
            user = QQUser()
            user.Uin = um['uin']
            user.UserName = str(um['uin'])
            user.NickName = um['nick']
            user.UserType = USER_TYPE_USER
            qDebug('got user:' + str(user.NickName))

            if user.Uin not in self.Users:
                qDebug('new user:' + str(user.NickName))
                self.Users[user.Uin] = user
                self.Users[user.UserName] = user
            else:
                qDebug('already exist user:' + str(user.NickName))

        return

    def setDiscusDetail(self, info):
        hcc = info

        strhcc = hcc.data().decode()
        qDebug(strhcc[0:120].replace("\n", "\\n"))
        jsobj = json.JSONDecoder().decode(strhcc)
        self.GroupList = jsobj

        for um in jsobj['result']['mem_info']:
            user = QQUser()
            user.Uin = um['uin']
            user.UserName = str(um['uin'])
            user.NickName = um['nick']
            user.UserType = USER_TYPE_USER
            qDebug('got user:' + str(user.NickName))

            if user.Uin not in self.Users:
                qDebug('new user:' + str(user.NickName))
                self.Users[user.Uin] = user
                self.Users[user.UserName] = user
            else:
                qDebug('already exist user:' + str(user.NickName))

        return

    def addGroupNames(self, GroupNames):
        for name in GroupNames:
            user = QQUser()
            user.UserName = name
            user.UserType = USER_TYPE_GROUP
            self.ICGroups[name] = user
        return

    def getICGroups(self):
        grnames = []
        gkeys = self.ICGroups.keys()
        for k in gkeys:
            if QQUser.isGroup(k):
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
        user = QQUser()
        user.Uin = obj['Uin']
        user.UserName = obj['UserName']
        user.NickName = obj['NickName']
        user.UserType = USER_TYPE_GROUP

        if user.Uin not in self.Users:
            self.Users[user.Uin] = user
            self.Users[user.UserName] = user

        if user.UserName in self.ICGroups: self.ICGroups.pop(user.UserName)
        if user.Uin in self.ICGroups: self.ICGroups.pop(user.Uin)
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
        user = QQUser()
        user.Uin = member['Uin']
        user.UserName = member['UserName']
        user.NickName = member['NickName']
        user.UserType = USER_TYPE_USER

        if user.Uin not in self.Users:
            self.Users[user.UserName] = user
            self.Users[user.Uin] = user

        if user.UserName in self.ICUsers: self.ICUsers.pop(user.UserName)
        if user.Uin in self.ICUsers: self.ICUsers.pop(user.Uin)
        return

    # @param info QByteArray
    def addFriendInfo(self, info):
        hcc = info
        strhcc = self.hcc2str(hcc)
        hccjs = json.JSONDecoder().decode(strhcc)

        res = hccjs['result']
        user = QQUser()
        user.Uin = res['tuin']
        user.UserName = str(res['tuin'])
        user.NickName = res['nick']
        user.HeadImgUrl = res['face']
        user.UserType = USER_TYPE_USER

        self.Users[user.Uin] = user
        self.Users[user.UserName] = user

        return user

    # @param hcc QByteArray
    # @return str
    def hcc2str(self, hcc):
        strhcc = ''

        try:
            astr = hcc.data().decode('gkb')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode gbk error:')

        try:
            astr = hcc.data().decode('utf16')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf16 error:')

        try:
            astr = hcc.data().decode('utf8')
            qDebug(astr[0:120].replace("\n", "\\n").encode())
            strhcc = astr
        except Exception as ex:
            qDebug('decode utf8 error:')

        return strhcc
