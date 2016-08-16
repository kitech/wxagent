from PyQt5.QtCore import *


class BaseAgent(QObject):

    def __init__(self, parent=None):
        super(BaseAgent, self).__init__(parent)
        return

    def Login(self):
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    def PushMessage(self):
        return

