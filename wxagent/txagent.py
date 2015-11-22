from PyQt5.QtCore import *
from PyQt5.QtNetwork import *


class AgentStats:
    def __init__(self):
        self.refresh_count = 0
        return


# 带获取所有cookie扩展功能的定制类
class AgentCookieJar(QNetworkCookieJar):
    def __init__(self, parent=None):
        super(AgentCookieJar, self).__init__(parent)

    def xallCookies(self):
        return self.allCookies()


# XXAgent基类，实现共有的抽象功能
class TXAgent(QObject):

    def __init__(self, parent=None):
        super(TXAgent, self).__init__(parent)

        self.acj = AgentCookieJar()
        self.nam = QNetworkAccessManager()
        # regradless network, QNetworkSession leave away
        self.nam.setConfiguration(QNetworkConfiguration())

        # reconnect state
        self.reconnect_total_times = 0
        self.reconnect_start_time = QDateTime()
        self.reconnect_last_time = QDateTime()
        self.reconnect_retry_times = 0
        # self.reconnect_slot = None

        self.RECONN_WAIT_TIMEOUT = 4567
        self.RECONN_MAX_RETRY_TIMES = 8

        self.queue_shot_timers = {}  # QTimer => [slot, extra]

        # test some
        # self.testNcm()
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

    def testNcm(self):
        def onAdded(cfg):
            qDebug('ncm added:' + cfg.name())
            return

        def onChanged(cfg):
            qDebug('ncm changed:' + cfg.name())
            return

        def onRemoved(cfg):
            qDebug('ncm removed:' + cfg.name())
            return

        def onOnlineStateChanged(online):
            qDebug('ncm online:' + str(online))
            return

        def onUpdateCompleted():
            qDebug('ncm update completed')
            return

        # QNetworkConfigurationManager会检测好多网络信息啊
        # 比如哪些无线网络可用，哪些无线网络不可用，都能显示出来，但这样也更耗资源。

        self.ncm = QNetworkConfigurationManager()
        self.ncm.configurationAdded.connect(onAdded)
        self.ncm.configurationChanged.connect(onChanged)
        self.ncm.configurationRemoved.connect(onRemoved)
        # 这个触发了一个bug哈，https://bugreports.qt.io/browse/QTBUG-49048
        # 不过应该fix了，看到代码加了个if (session) { the warning }，fix链接在上面bug链接中有。
        self.ncm.onlineStateChanged.connect(onOnlineStateChanged)
        self.ncm.updateCompleted.connect(onUpdateCompleted)
        return
