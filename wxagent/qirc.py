from PyQt5.QtCore import *

import socket
import irc.client


class QIRC(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QIRC, self).__init__(parent)
        return

    def run(self):
        self._client = irc.client.Reactor(on_connect=self.onConnected, on_disconnect=self.onDisconnected)
        self._server = self._client.server()
        qDebug('hehrere')
        print(self._server)
        r = self._server.connect('weber.freenode.net', 6667, 'devnull')
        qDebug(str(self._server.is_connected()))
        self._server.join('#roundtablex')
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
        self.newMessage.emit(evt.arguments[0])
        return

    def onPrivateMessage(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        print(conn, evt, type(evt))
        self.newMessage.emit(evt.arguments[0])
        return
