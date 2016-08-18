from PyQt5.QtCore import *


class BaseAgent(QObject):
    PushMessage = pyqtSignal(str)

    def __init__(self, parent=None):
        super(BaseAgent, self).__init__(parent)
        return

    def Login(self):
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    def SendMessageX(self):
        return

