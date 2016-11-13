import logging
import asyncio
import time

from PyQt5.QtCore import *

import socket
import irc.client


class QIRC(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal(str)
    newGroupMessage = pyqtSignal(str, str, str)
    needJoin = pyqtSignal()

    def __init__(self, parent=None):
        irc.client.log.setLevel(logging.DEBUG)
        super(QIRC, self).__init__(parent)
        self.last_ping = time.time()
        return

    def startup(self):
        self._user = 'devnull2'
        self._user = '\_'
        self._user = 'yobot'
        self._peer_user = 'kitech'
        self._channel = '#roundtablex1'
        self._fixchans = ['#archlinux-cn-offtopic', '#linuxba', '#tox-cn123']
        self._fixchans = ['#tox-cn123']
        self._host = 'weber.freenode.net'
        self._port = 8000


        self._client = irc.client.Reactor(on_connect=self.onConnected, on_disconnect=self.onDisconnected)
        self._server = self._client.server()
        r = self._server.connect(self._host, self._port, self._user)
        qDebug(str(self._server.is_connected()))
        self._server.set_keepalive(123.0)
        self._server.set_rate_limit(3)

        self._server.add_global_handler('pubmsg', self.onPublicMessage)
        self._server.add_global_handler('privmsg', self.onPrivateMessage)
        self._server.add_global_handler('error', self.onIRCError)
        for evt in irc.events.protocol:
            if self._server.handlers.get(evt) is None:
                self._server.add_global_handler(evt, self.onIRCEvent)

        self.needJoin.connect(self.rejoin, Qt.QueuedConnection)
        self.needJoin.emit()

        self.loop_timer = QTimer()
        self.loop_timer.timeout.connect(self.iterate, Qt.QueuedConnection)
        self.loop_timer.start(200)

        while False:
            self._client.process_once(timeout=0.05)
        # self._client.process_forever()
        return

    def iterate(self):
        try:
            self._client.process_once(timeout=0)
        except irc.client.ServerNotConnectedError as ex:
            asyncio.get_event_loop().call_soon(self.reconnect)
        return

    def reconnect(self):
        r = self._server.connect(self._host, self._port, self._user)
        return r

    def tryReconnect(self):
        to = self.checkTimeout()
        reconn = False
        if to is True:
            reconn = True
        if self._server.is_connected() is False:
            qDebug('not connected. retry...')
            reconn = True

        if reconn is True:
            self.reconnect()
        return

    # use last_ping_time
    def checkTimeout(self):
        now = time.time()
        if self.last_ping > 1.0:
            delta = now - self.last_ping
            if delta > (260.0 + 12):
                qDebug('maybe connection timeout: {}'.format(delta))
                return True
        return False

    def rejoin(self):
        qDebug('hehrerere')
        jret = self._server.join(self._channel)
        qDebug(str(jret))
        for ch in self._fixchans:
            self._server.join(ch)
        return

    def onConnected(self, sock: socket.socket):
        self.connected.emit()
        return

    def onDisconnected(self, sock: socket.socket):
        qDebug('hehreree')
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
        self.reconnect()
        self.needJoin.emit()
        return

    def onIRCMode(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        qDebug('{}, {}. {}'.format(str(conn), str(evt), str(type(evt))).encode())
        return

    def onIRCEvent(self, conn: irc.client.ServerConnection, evt: irc.client.Event):
        qDebug('{}, {}. {}'.format(str(conn), str(evt), str(type(evt))).encode())
        if evt.type == 'ping' or evt.type == 'pong':
            last_ping = time.time()
            qDebug('last: {}, now: {}, delta: {}, conn: {}'
                   .format(self.last_ping, last_ping,
                           last_ping-self.last_ping, self._server.is_connected()))
            self.last_ping = last_ping
        elif evt.type == 'error':
            qDebug('maybe disconnected')
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
        self.tryReconnect()
        if self._server.is_connected():
            ret = self._server.privmsg(self._peer_user, msg)
            qDebug(str(ret).encode())
        else:
            qDebug('not connected')
        return

    def sendGroupMessage(self, msg, channel):
        self.tryReconnect()
        if self._server.is_connected():
            if self.validName(channel):
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
            qDebug('wtf')
        return True

    def validName(self, name):
        if name[0] != '#': return False
        import re
        # check cjk characters
        mats = re.findall('[\u2E80-\u9FFF]', name)
        return len(mats) == 0
