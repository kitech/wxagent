
from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .wxcommon import *


# called service
class RoundTableService(QObject):
    def __init__(self, parent=None):
        super(RoundTableService, self).__init__(parent)
        return

    @pyqtSlot(QDBusMessage, result=str)
    def getdummy(self, msg):
        print(msg)
        return 'aaa'


class RoundTableServer(QObject):
    def __init__(self, parent=None):
        super(RoundTableServer, self).__init__(parent)
        self.sysbus = QDBusConnection.systemBus()
        self.msgsvc = RoundTableService()
        self.agents = []

        self.init_dbus_service()
        self.register_dbus_service()
        self.monitor_message_ring_bus()

        self.loginAllProtocols()
        return

    ##########
    def init_dbus_service(self):
        sysbus = self.sysbus
        bret = sysbus.registerService(WXAGENT_SERVICE_NAME)
        if bret is False:
            err = sysbus.lastError()
            qDebug('error: {}, {}'.format(err.name(), err.message()))
            exit()
        qDebug(str(sysbus.name()))
        iface = sysbus.interface()
        qDebug(str(sysbus.interface()) + ', ' + str(iface.service()) + ', ' + str(iface.path()))

        return


    def register_dbus_service(self):
        sysbus = self.sysbus
        bret = False
        if qVersion() >= '5.5':
            bret = sysbus.registerObject(WXAGENT_SEND_PATH, WXAGENT_IFACE_NAME,
                                         self.msgsvc, QDBusConnection.ExportAllSlots)
        else:
            bret = sysbus.registerObject(WXAGENT_SEND_PATH, self.msgsvc, QDBusConnection.ExportAllSlots)
        qDebug(str(sysbus))
        qDebug(str(bret))
        if bret is False:
            err = sysbus.lastError()
            qDebug('register error:{} {}'.format(err.name(), err.message()))
            exit()

        return

    def monitor_message_ring_bus(self):
        self.agent_service = WXAGENT_SERVICE_NAME
        self.agent_service_path = WXAGENT_SEND_PATH
        self.agent_service_iface = WXAGENT_IFACE_NAME
        self.agent_event_path = WXAGENT_EVENT_BUS_PATH_SERVER
        self.agent_event_iface = WXAGENT_EVENT_BUS_IFACE_SERVER

        # hotfix sysbus.connect hang
        if qVersion() >= '5.6' and qVersion() <= '5.7.9':
            self.sysbus.registerObject('/hotfixidontknowwhy', self)

        if qVersion() >= '5.5':
            self.sysiface = QDBusInterface(self.agent_service, self.agent_service_path,
                                           self.agent_service_iface, self.sysbus)
            self.sysiface.setTimeout(50 * 1000)  # shit for get msg pic
        else:
            self.sysiface = QDBusInterface(self.agent_service, self.agent_service_path, '', self.sysbus)

        service = self.agent_service
        path = self.agent_event_path
        iface = self.agent_event_iface
        bret = self.sysbus.connect(service, path, iface, 'newmessage', self.onDBusNewMessage)
        qDebug('connected server message bus: {}'.format(bret))
        if bret is False:
            err = self.sysbus.lastError()
            print('register error:', err.name(), err.message())
            exit()

        return

    @pyqtSlot(QDBusMessage)
    def onDBusNewMessage(self, msg):
        print(msg)
        return

    def loginAllProtocols(self):
        from .wxagent import WXAgent
        from .ircagent import IRCAgent
        from .toxagent import ToxAgent
        # from .xmppagent import XmppAgent
        # from .slackagent import SlackAgent

        agts = self.agents
        agts.append(WXAgent())
        agts.append(IRCAgent())
        agts.append(ToxAgent())

        for agt in agts:
            agt.PushMessage.connect(self.onPushMessage, Qt.QueuedConnection)
            agt.Login()

        return

    @pyqtSlot(str)
    def onPushMessage(self, msg):
        sder = self.sender()
        clsname = sder.__class__.__name__
        qDebug(('pushing msg to rtbus: {}, {}'.format(clsname, msg[0:32])).encode())

        sigmsg = QDBusMessage.createSignal(WXAGENT_EVENT_BUS_PATH_CLIENT, WXAGENT_EVENT_BUS_IFACE_CLIENT, "PushMessage")

        sigmsg.setArguments([msg, clsname])

        sysbus = self.sysbus
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return
