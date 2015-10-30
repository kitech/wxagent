from PyQt5.QtCore import *


# XXAgent基类，实现共有的抽象功能
class TXAgent(QObject):

    def __init__(self, parent=None):
        super(TXAgent, self).__init__(parent)

        # reconnect state
        self.reconnect_total_times = 0
        self.reconnect_start_time = QDateTime()
        self.reconnect_last_time = QDateTime()
        self.reconnect_retry_times = 0
        # self.reconnect_slot = None

        self.RECONN_WAIT_TIMEOUT = 4567
        self.RECONN_MAX_RETRY_TIMES = 8

        self.queue_shot_timers = {}  # QTimer => [slot, extra]
        return

    # 在reconnect策略允许的范围内
    def canReconnect(self):
        if self.reconnect_retry_times <= self.RECONN_MAX_RETRY_TIMES:
            return True
        return False

    def inReconnect(self):
        if self.reconnect_retry_times > 0:
            return True
        return False

    def tryReconnect(self, slot):
        self.queueShot(self.RECONN_WAIT_TIMEOUT, self._tryReconnectImpl, slot)
        return

    def _tryReconnectImpl(self, slot):
        if not self.canReconnect():
            qDebug('wtf???')
            return False

        # 累计状态改变
        if self.reconnect_retry_times == 0:
            self.reconnect_start_time = QDateTime.currentDateTime()
        self.reconnect_last_time = QDateTime.currentDateTime()
        self.reconnect_total_times += 1
        self.reconnect_retry_times += 1

        oldname = self.nam
        self.nam = None
        oldname.finished.disconnect()

        qDebug('see this reconnect...')

        # self.acj = AgentCookieJar()
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.onReply, Qt.QueuedConnection)
        self.nam.setCookieJar(self.acj)

        # self.queueShot(1234, slot)
        QTimer.singleShot(1234, slot)
        # QTimer.singleShot(1234, self.eventPoll)
        return

    def finishReconnect(self):
        if not self.inReconnect():
            qDebug('wtf???')
            return

        qDebug('reconn state: retry:%s, time=%s' %
               (self.reconnect_retry_times,
                self.reconnect_start_time.msecsTo(self.reconnect_last_time)))
        self.reconnect_retry_times = 0
        self.reconnect_start_time = QDateTime()
        self.reconnect_last_time = QDateTime()
        return

    def queueShot(self, msec, slot, extra):
        tmer = QTimer()
        tmer.setInterval(msec)
        tmer.setSingleShot(True)

        tmer.timeout.connect(self.onQueueShotTimeout, Qt.QueuedConnection)
        self.queue_shot_timers[tmer] = [slot, extra]
        tmer.start()

        return

    def onQueueShotTimeout(self):
        tmer = self.sender()
        slot, extra = self.queue_shot_timers.pop(tmer)
        slot(extra)
        return
