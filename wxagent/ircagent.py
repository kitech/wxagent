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

    # override
    def onRpcCall(self, argv):
        qDebug('hereeeee: {}'.format(argv).encode()[0:78])

        func = argv[0]
        ret = None

        if func == 'friendExists':
            ret = self.toxkit.friendExists(argv[1])
        elif func == 'sendMessage':
            ret = self._irc.sendMessage(argv[1])
        elif func == 'sendGroupMessage':
            ret = self._irc.sendGroupMessage(argv[1], argv[2])
        else:
            qDebug('not supported now: {}'.format(func))

        return ret

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
        args = self.setCtxChannel(args, self._irc._channel)
        self.SendMessageX(args)
        return
