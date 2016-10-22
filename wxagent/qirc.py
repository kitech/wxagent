from PyQt5.QtCore import *

import socket
import irc.client


class QIRC(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal(str)
    newGroupMessage = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super(QIRC, self).__init__(parent)
        return

    def run(self):
        self._user = 'devnull2'
        self._peer_user = 'kitech'
        self._channel = '#roundtablex1'
        self._host = 'weber.freenode.net'
        self._port = 8000

        self._client = irc.client.Reactor(on_connect=self.onConnected, on_disconnect=self.onDisconnected)
        self._server = self._client.server()
        qDebug('hehrere')
        print(self._server)
        r = self._server.connect(self._host, self._port, self._user)
        qDebug(str(self._server.is_connected()))
        jret = self._server.join(self._channel)
        qDebug(str(jret))
        self._server.add_global_handler('pubmsg', self.onPublicMessage)
        self._server.add_global_handler('privmsg', self.onPrivateMessage)

        while True:
            self._client.process_once(timeout=0.05)
        # self._client.process_forever()
        return

    def onConnected(self, sock: socket.socket):
        self.connected.emit()
        return

    def onDisconnected(self, sock: socket.socket):
        self.disconnected.emit()
        return

    def onPublicMessage(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        print(conn, evt, type(evt))
        # self.newMessage.emit(evt.arguments[0])
        self.newGroupMessage.emit(evt.arguments[0], evt.target)
        return

    def onPrivateMessage(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        print(conn, evt, type(evt))
        # self.newMessage.emit(evt.arguments[0])
        self.newGroupMessage.emit(evt.arguments[0], evt.target)
        return

    def groupAdd(self, channel):
        self._server.join(channel)
        return

    def groupInvite(self, nick, channel):
        ret = self._server.invite(nick, channel)
        # qDebug(str(ret).encode())
        # lst = self._server.list()
        # qDebug(str(lst).encode())
        return

    def sendMessage(self, msg):
        if self._server.is_connected():
            ret = self._server.privmsg(self._peer_user, msg)
            qDebug(str(ret).encode())
        else:
            qDebug('not connected')
        return

    def sendGroupMessage(self, msg, channel):
        if self._server.is_connected():
            self.groupAdd(channel)
            self.groupInvite(self._peer_user, channel)
            qDebug(str(channel).encode())
            # qDebug(str(msg).encode())
            # ret = self._server.privmsg(self._channel, msg)
            ret = self._server.privmsg(channel, msg)
            qDebug(str(ret).encode())
        else:
            qDebug('not connected')
        return
