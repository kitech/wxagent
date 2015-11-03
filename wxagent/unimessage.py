# 把txim的消息转换为要转发的消息格式

import re
import html2text
from PyQt5.QtCore import qDebug

# should be 27
MAX_LEN_FOR_NEWLINE = ord('Z') - ord('A') + 1 + 1


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
        umsg = PlainMessage()

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
        umsg.content = ccmsg
        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = XmppMessage()
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
        umsg.dconent = logstr

        # ●••·
        ccmsg = "" + content
        umsg.content = ccmsg
        return umsg


class ToxMessage(UniMessage):
    def __init__(self):
        super(ToxMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        umsg = XmppMessage()
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

        #
        content = content.replace('<br/>', ' ')
        content = html2text.html2text(content)
        content = content.replace('**', ' ')
        content = content.strip()

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        ccmsg = content
        umsg.content = ccmsg
        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = ToxMessage()
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
        umsg.dconent = logstr

        ccmsg = content
        umsg.content = ccmsg
        return umsg


class XmppMessage(UniMessage):
    def __init__(self):
        super(XmppMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        umsg = XmppMessage()
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

        #
        content = content.replace('<br/>', ' ')
        content = html2text.html2text(content)
        content = content.replace('**', ' ')
        content = content.strip()

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        # ●•·
        ccmsg = "\n   •  " + content
        if len(content) < MAX_LEN_FOR_NEWLINE: ccmsg = '  ' + content
        umsg.content = ccmsg
        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = XmppMessage()
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
        umsg.dconent = logstr

        # ●•·
        ccmsg = "\n   •  " + content
        if len(content) < MAX_LEN_FOR_NEWLINE: ccmsg = '  ' + content
        umsg.content = ccmsg
        return umsg
