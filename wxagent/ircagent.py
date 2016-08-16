from PyQt5.QtCore import *
from .baseagent import BaseAgent


class IRCAgent(BaseAgent):
    def __init__(self, parent=None):
        super(IRCAgent, self).__init__(parent)
        return

    def Login(self):
        qDebug('heree')
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    def PushMessage(self):
        return

