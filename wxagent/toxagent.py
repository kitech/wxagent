from PyQt5.QtCore import *
from .baseagent import BaseAgent


class ToxAgent(BaseAgent):
    def __init__(self, parent=None):
        super(ToxAgent, self).__init__(parent)
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

