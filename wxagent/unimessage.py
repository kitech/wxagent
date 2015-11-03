# 把txim的消息转换为要转发的消息格式

import re
import html2text
from PyQt5.QtCore import qDebug

from .wxcommon import *


# should be 27
MAX_LEN_FOR_NEWLINE = ord('Z') - ord('A') + 1 + 1


# 使用fromXXMessage的方式，一个好处是添加新的relay时，方便添加与扩展
# base Uniform Message class
class UniMessage:

    def __init__(self):
        self.content = ''
        self.dcontent = ''
        return

    def get(self):
        return self.content

    def dget(self):
        return self.dcontent

    def fromWXMessage(wxmsg, wxses):
        return

    def fromQQMessage(qqmsg, qqses):
        return

    # filter
    def num2name(self, ses):
        # 对消息做进一步转化，当MsgId==1时，替换消息开关的真实用户名
        # @894e0c4caa27eeef705efaf55235a2a2:<br/>...
        reg = r'^(@[0-9a-f]+):<br/>'
        mats = re.findall(reg, self.content)
        if len(mats) > 0:
            UserName = mats[0]
            UserInfo = ses.getUserInfo(UserName)
            if UserInfo is not None:
                dispRealName = UserInfo.NickName + UserName[0:7]
                self.content = self.content.replace(UserName, dispRealName, 1)
        return self

    # filter
    def dropnl(self):
        self.content = self.content.replace('<br/>', ' ')
        return self

    # filter
    def drophtml(self):
        # self.content = html2text.html2text(self.content)
        h = html2text.HTML2Text()
        self.content = h.handle(self.content)
        return self

    # filter
    def dropstars(self):
        self.content = self.content.replace('**', ' ')
        return self

    # filter
    def strip(self):
        self.content = self.content.strip()
        return self

    # transform
    def nlbylen(self):
        # ●•·
        if len(self.content) < MAX_LEN_FOR_NEWLINE:
            self.content = '  ' + self.content
        else:
            self.content = "\n   •  " + self.content
        return self

    # transform
    def ubb2emoji(self):
        return self

    # transform
    def emoji2ubb(self):
        return self


class PlainMessage(UniMessage):
    def __init__(self):
        super(PlainMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        umsg = PlainMessage()
        msg = wxmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        umsg.drophtml().dropstars().strip()
        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = XmppMessage()
        msg = qqmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        # for eyes
        dispFromUserName = msg.FromUserName
        dispToUserName = msg.ToUserName

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        umsg.drophtml().dropstars().strip()
        return umsg


class ToxMessage(UniMessage):
    def __init__(self):
        super(ToxMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        umsg = XmppMessage()
        msg = wxmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        if msg.MsgType == WXMsgType.MT_TEXT:
            umsg.num2name(wxses).dropnl().dropstars().strip()
        else:
            umsg.num2name(wxses).dropnl().drophtml().dropstars().strip()

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = ToxMessage()
        msg = qqmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        # for eyes
        dispFromUserName = msg.FromUserName
        dispToUserName = msg.ToUserName

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)
        umsg.dconent = logstr

        return umsg


class XmppMessage(UniMessage):
    def __init__(self):
        super(XmppMessage, self).__init__()
        return

    def fromWXMessage(wxmsg, wxses):
        umsg = XmppMessage()
        msg = wxmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        if msg.MsgType == WXMsgType.MT_TEXT:
            umsg.num2name(wxses).dropnl().dropstars().strip()
        else:
            umsg.num2name(wxses).dropnl().drophtml().dropstars().strip()

        # for eyes
        dispFromUserName = msg.FromUserName[0:7]
        dispToUserName = msg.ToUserName[0:7]

        ccmsg = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                 dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)

        umsg.nlbylen()
        return umsg

    def fromQQMessage(qqmsg, qqses):
        umsg = XmppMessage()
        msg = qqmsg
        umsg.content = msg.UnescapedContent
        umsg.dcontent = msg.UnescapedContent

        fromUser = msg.FromUser
        toUser = msg.ToUser

        fromUser_NickName = ''
        if fromUser is not None: fromUser_NickName = fromUser.NickName
        toUser_NickName = ''
        if toUser is not None: toUser_NickName = toUser.NickName

        # for eyes
        dispFromUserName = msg.FromUserName
        dispToUserName = msg.ToUserName

        logstr = '[%s][%s] %s(%s) => %s(%s) @%s:::\n%s' % \
                 (msg.CreateTime, msg.MsgType, dispFromUserName, fromUser_NickName,
                  dispToUserName, toUser_NickName, msg.MsgId, msg.UnescapedContent)
        umsg.dconent = logstr

        umsg.nlbylen()
        return umsg
