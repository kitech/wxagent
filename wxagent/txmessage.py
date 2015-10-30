from .txcom import *


# user classes
class TXUser():
    def __init__(self):
        "docstring"

        self.Uin = 0  # temporary use
        self.UserName = ''  # qqnum/@abcdef123
        self.NickName = ''

        self.UserType = USER_TYPE_UNKNOWN  # USER_TYPE_*
        self.members = {}  # user name -> TXUser
        self.HeadImgUrl = ''

        return

    # 支持作为实例方法与类方法两种方式
    # signature1: u.isGroup()
    # signature2: TXUser.isGroup(name)
    def isGroup(self):
        if type(self) is str:
            return TXUser.isGroupName(self)

        if self.UserType == USER_TYPE_GROUP:
            return True
        if self.UserName.startswith('@@'):
            return True

        return False

    # forwx
    @staticmethod
    def isGroupName(name):
        return name.startswith('@@')

    # forqq
    def isDiscus(self):
        return self.UserType == USER_TYPE_DISCUS

    # forwx
    def isMPSub(self):
        return self.HeadImgUrl == ''

    # forwx
    def cname(self):
        if self.UserName in ['filehelper', 'newsapp', 'fmessage']:
            return self.UserName
        if len(self.UserName) < 16:  # maybe a special name
            return self.UserName
        return self.UserName.strip('@')[0:7]


class QQUser(TXUser): pass


# message classes
class TXMessage():

    def __init__(self):
        "docstring"
        self.MsgType = 0
        self.MsgId = ''
        self.FromUserName = ''  # is uin
        self.ToUserName = ''  # is uin
        self.CreateTime = 0
        self.Content = ''
        self.UnescapedContent = ''

        self.FromUser = None
        self.ToUser = None

        self.jsonContent = {}

        return

    def isOffpic(self):
        return False

    def isFileMsg(self):
        return False


class TXMessageList():

    def __init__(self):
        "docstring"
        return
