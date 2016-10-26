from PyQt5.QtCore import *

import socket
import irc.client


class QIRC(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal(str)
    newGroupMessage = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super(QIRC, self).__init__(parent)
        return

    def run(self):
        self._user = 'devnull2'
        self._user = '\_'
        self._user = 'yobot'
        self._peer_user = 'kitech'
        self._channel = '#roundtablex1'
        self._fixchans = ['#archlinux-cn-offtopic', '#linuxba', '#tox-cn123']
        # self._fixchans = ['#tox-cn123']
        self._host = 'weber.freenode.net'
        self._port = 8000

        self._client = irc.client.Reactor(on_connect=self.onConnected, on_disconnect=self.onDisconnected)
        self._server = self._client.server()
        qDebug('hehrere')
        print(self._server)
        r = self._server.connect(self._host, self._port, self._user)
        qDebug(str(self._server.is_connected()))

        self._server.add_global_handler('pubmsg', self.onPublicMessage)
        self._server.add_global_handler('privmsg', self.onPrivateMessage)
        self._server.add_global_handler('error', self.onIRCError)
        for evt in irc.events.protocol:
            if self._server.handlers.get(evt) is None:
                self._server.add_global_handler(evt, self.onIRCEvent)

        jret = self._server.join(self._channel)
        qDebug(str(jret))
        for ch in self._fixchans:
            self._server.join(ch)

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
        sep = '!~' if evt.source.find('!~') != -1 else '!'
        fromuser = evt.source.split(sep)[0]
        fromaddr = evt.source.split(sep)[1]
        self.newGroupMessage.emit(evt.arguments[0], evt.target, fromuser)
        return

    def onPrivateMessage(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        print(conn, evt, type(evt))
        # self.newMessage.emit(evt.arguments[0])
        sep = '!~' if evt.source.find('!~') != -1 else '!'
        fromuser = evt.source.split(sep)[0]
        fromaddr = evt.source.split(sep)[1]
        self.newGroupMessage.emit(evt.arguments[0], evt.target, fromuser)
        return

    def onIRCError(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        qDebug('{}, {}. {}'.format(str(conn), str(evt), str(type(evt))).encode())
        return

    def onIRCMode(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        qDebug('{}, {}. {}'.format(str(conn), str(evt), str(type(evt))).encode())
        return

    def onIRCEvent(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        qDebug('{}, {}. {}'.format(str(conn), str(evt), str(type(evt))).encode())
        return

    def groupAdd(self, channel):
        rc = self._server.join(channel)
        qDebug(str(rc))
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
            if self.invalidName(channel):
                self.groupAdd(channel)
                self.groupInvite(self._peer_user, channel)
                qDebug(str(channel).encode())
                # qDebug(str(msg).encode())
                # ret = self._server.privmsg(self._channel, msg)
                ret = self._server.privmsg(channel, msg)
                qDebug(str(ret).encode())
            else:
                qDebug('Invalid channel name: {}'.format(channel).encode())
                return False
        else:
            qDebug('not connected. retry...')
            r = self._server.connect(self._host, self._port, self._user)
            if self._server.is_connected():
                return self.sendGroupMessage(msg, channel)
            else:
                return False
        return True

    def invalidName(self, name):
        if name[0] != '#': return False
        import re
        # check cjk characters
        mats = re.findall('[\u2E80-\u9FFF]', name)
        return len(mats) == 0
