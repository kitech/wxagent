from PyQt5.QtCore import *
from .baseagent import BaseAgent

from .qirc import QIRC


class IRCAgent(BaseAgent):
    def __init__(self, parent=None):
        super(IRCAgent, self).__init__(parent)
        return

    def Login(self):
        qDebug('heree')
        self._irc = QIRC()
        self._irc.connected.connect(self.onIRCConnected, Qt.QueuedConnection)
        self._irc.disconnected.connect(self.onIRCDisconnected, Qt.QueuedConnection)
        self._irc.newMessage.connect(self.onIRCNewMessage, Qt.QueuedConnection)
        self._irc.start()
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    # ######################
    def onIRCConnected(self):
        qDebug('hrerere')
        args = self.makeBusMessage(None, 'connected')
        self.SendMessageX(args)
        return

    def onIRCDisconnected(self):
        qDebug('hrerere')
        args = self.makeBusMessage(None, 'disconnected')
        self.SendMessageX(args)
        return

    def onIRCNewMessage(self, msg):
        qDebug(msg[0:32].encode())
        args = self.makeBusMessage('message', None, msg)
        args['channel'] = 'roundtablex'
        self.SendMessageX(args)
        return
