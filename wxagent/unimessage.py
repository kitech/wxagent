# 把txim的消息转换为要转发的消息格式

import re
from PyQt5.QtCore import *


# 使用fromXXMessage的方式，一个好处是添加新的relay时，方便添加与扩展
# base Uniform Message class
class UniMessage:

    def __init__(self):
        self.content = ''
        self.dconent = ''
        return

    def get(self):
        return self.content

    def dget(self):
        return self.dconent

    def fromWXMessage(wxmsg, wxses):
        return

    def fromQQMessage(qqmsg, qqses):
        return


class PlainMessage(UniMessage):
    def __init__(self):
        super(PlainMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        pmsg = PlainMessage()

        msg = wxmsg

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        content = msg.UnescapedContent

        # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
        # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
        reg = r'^(@[0-9a-f]+):<br/>'
        mats = re.findall(reg, content)
        if len(mats) > 0:
            UserName = mats[0]
            UserInfo = wxses.getUserInfo(UserName)
            if UserInfo is not None:
                dispRealName = UserInfo.NickName + UserName[0:7]
                content = content.replace(UserName, dispRealName, 1)

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)
        pmsg.content = ccmsg
        return pmsg

    def fromQQMessage(qqmsg, qqses):
        xmsg = XmppMessage()
        msg = qqmsg

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        content = msg.UnescapedContent

        # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
        # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
        reg = r'^(@[0-9a-f]+):<br/>'
        mats = re.findall(reg, content)
        if len(mats) > 0:
            qDebug(str(mats).encode())
            UserName = mats[0]
            UserInfo = qqses.getUserInfo(UserName)
            qDebug(str(UserInfo).encode())
            if UserInfo is not None:
                dispRealName = UserInfo.NickName + UserName
                content = content.replace(UserName, dispRealName, 1)

        # for eyes
        dispFromUserName = msg.FromUserName
        dispToUserName = msg.ToUserName

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, content)
        xmsg.dconent = logstr

        # ●••·
        ccmsg = "" + content
        xmsg.content = ccmsg
        return xmsg


class ToxMessage(UniMessage):
    def __init__(self):
        super(ToxMessage, self).__init__()
        return

    def fromWXMessage(wxmsg):
        tmsg = ToxMessage()

        msg = wxmsg
        ccmsg = msg.UnescapedContent
        tmsg.content = ccmsg
        return tmsg


class XmppMessage(UniMessage):
    def __init__(self):
        super(XmppMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        xmsg = XmppMessage()
        msg = wxmsg

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        content = msg.UnescapedContent

        # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
        # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
        reg = r'^(@[0-9a-f]+):<br/>'
        mats = re.findall(reg, content)
        if len(mats) > 0:
            UserName = mats[0]
            UserInfo = wxses.getUserInfo(UserName)
            if UserInfo is not None:
                dispRealName = UserInfo.NickName + UserName[0:7]
                content = content.replace(UserName, dispRealName, 1)

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        # 这个格式，类似QQ，用户名信息独占一行，消息新起一行，行首空几个格。
        ccmsg = "\n        " + content

        xmsg.content = ccmsg
        return xmsg

    def fromQQMessage(qqmsg, qqses):
        xmsg = XmppMessage()
        msg = qqmsg

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        content = msg.UnescapedContent

        # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
        # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
        reg = r'^(@[0-9a-f]+):<br/>'
        mats = re.findall(reg, content)
        if len(mats) > 0:
            qDebug(str(mats).encode())
            UserName = mats[0]
            UserInfo = qqses.getUserInfo(UserName)
            qDebug(str(UserInfo).encode())
            if UserInfo is not None:
                dispRealName = UserInfo.NickName + UserName
                content = content.replace(UserName, dispRealName, 1)

        # for eyes
        dispFromUserName = msg.FromUserName
        dispToUserName = msg.ToUserName

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, content)
        xmsg.dconent = logstr

        # ●•·
        ccmsg = "\n   •   " + content
        if len(content) < 27: ccmsg = '  ' + content
        xmsg.content = ccmsg
        return xmsg
