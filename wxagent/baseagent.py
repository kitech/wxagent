import sys
import inspect
import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .wxcommon import *


# called service
class AgentService(QObject):
    def __init__(self, agt, parent=None):
        super(AgentService, self).__init__(parent)
        self.agt = agt
        return

    @pyqtSlot(QDBusMessage, result=str)
    def getdummy(self, msg):
        print(msg)
        return 'aaa'

    @pyqtSlot(QDBusMessage, result=str)
    def rcall(self, msg):
        ret = self.agt.onRpcCall(msg.arguments())
        ret = json.JSONEncoder().encode(ret)
        return ret


class BaseAgent(QObject):
    PushMessage = pyqtSignal(str)
    OP = 'op'
    EVT = 'evt'

    def __init__(self, parent=None):
        super(BaseAgent, self).__init__(parent)
        self.sysbus = QDBusConnection.systemBus()
        self.msgsvc = AgentService(self)
        self.agents = []

        self.service_name = WXAGENT_SERVICE_NAME + '.' + self.__class__.__name__
        self.service_path = WXAGENT_SERVICE_PATH + '/' + self.__class__.__name__
        self.service_iface = WXAGENT_SERVICE_IFACE + '.' + self.__class__.__name__
        self.PushMessage.connect(self.onPushMessage, Qt.QueuedConnection)
        self.init_dbus_service()
        self.register_dbus_service()
        self.monitor_message_ring_bus()
        return

    def Login(self):
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    def SendMessageX(self, msg: dict):
        msg['src'] = self.__class__.__name__
        msg['dest'] = ['all'] if msg.get('dest') is None else msg['dest']
        msg['ttl'] = 0 if msg.get('ttl') is None else msg['ttl']
        encmsg = json.JSONEncoder(ensure_ascii=False).encode(msg)
        encmsg = encmsg.replace("\n", '')
        a = self.PushMessage.emit(encmsg)
        qDebug('hereee: {}({})={}'.format(a, str(type(encmsg)), encmsg[0:32]).encode())
        return

    def makeBusMessage(self, op: str, evt: str, *args):
        if op is not None:
            return {'op': op, 'params': args, }
        if evt is not None:
            return {'evt': evt, 'params': args, }
        raise 'wtf'
        return


    ##########
    def init_dbus_service(self):
        sysbus = self.sysbus
        bret = sysbus.registerService(self.service_name)
        if bret is False:
            err = sysbus.lastError()
            qDebug('error: {}, {}'.format(err.name(), err.message()))
            # exit()
        qDebug(str(sysbus.baseService()))
        qDebug(str(sysbus.name()))
        iface = sysbus.interface()
        qDebug(str(sysbus.interface()) + ', ' + str(iface.service()) + ', ' + str(iface.path()))

        return


    def register_dbus_service(self):
        # for test
        # if self.__class__.__name__ == 'RoundTable': return
        sysbus = self.sysbus
        bret = False
        if qVersion() >= '5.5':
            bret = sysbus.registerObject(self.service_path, self.service_iface,
                                         self.msgsvc, QDBusConnection.ExportAllSlots)
        else:
            bret = sysbus.registerObject(self.service_path, self.msgsvc, QDBusConnection.ExportAllSlots)
        qDebug(str(sysbus))
        qDebug(str(bret))
        if bret is False:
            err = sysbus.lastError()
            qDebug('register error:{} {}'.format(err.name(), err.message()))
            exit()

        return

    def monitor_message_ring_bus(self):
        self.agent_event_path = WXAGENT_EVENT_BUS_PATH
        self.agent_event_iface = WXAGENT_EVENT_BUS_IFACE

        # hotfix sysbus.connect hang
        if qVersion() >= '5.6' and qVersion() <= '5.7.9':
            self.sysbus.registerObject('/hotfixidontknowwhy_' + self.__class__.__name__, self)

        # TODO replace with ifaceForName
        if qVersion() >= '5.5':
            self.sysiface = QDBusInterface(self.service_name, self.service_path,
                                           self.service_iface, self.sysbus)
            self.sysiface.setTimeout(50 * 1000)  # shit for get msg pic
        else:
            self.sysiface = QDBusInterface(self.service_name, self.service_path, '', self.sysbus)

        path = self.agent_event_path
        iface = self.agent_event_iface
        bret = self.sysbus.connect('', path, iface, 'PushMessage', self.onDBusNewMessage)
        qDebug('connected server message bus: {}'.format(bret))
        if bret is False:
            err = self.sysbus.lastError()
            print('register error:', err.name(), err.message())
            exit()

        return

    def ifaceForName(self, name):
        service_name = WXAGENT_SERVICE_NAME + '.' + name
        service_path = WXAGENT_SERVICE_PATH + '/' + name
        service_iface = WXAGENT_SERVICE_IFACE + '.' + name

        iface = QDBusInterface(service_name, service_path,
                               service_iface, self.rt.sysbus)
        return iface

    @pyqtSlot(QDBusMessage)
    def onDBusNewMessage(self, msg):
        print(msg, msg.service(), ',', msg.path(), ',', msg.interface(), ',', msg.arguments())
        self.messageHandler(msg)
        return

    def messageHandler(self, msg: QDBusMessage):
        return

    @pyqtSlot(str)
    def onPushMessage(self, msg):
        sder = self.sender()
        clsname = sder.__class__.__name__
        qDebug(('pushing msg to rtbus: {}, {}'.format(clsname, msg[0:56])).encode())

        path = WXAGENT_EVENT_BUS_PATH
        iface = WXAGENT_EVENT_BUS_IFACE
        sigmsg = QDBusMessage.createSignal(path, iface, "PushMessage")

        sigmsg.setArguments([msg, clsname])

        sysbus = self.sysbus
        bret = sysbus.send(sigmsg)
        qDebug(str(bret))

        return

    def onRpcCall(self, msg):
        qDebug(self.__class__.__name__ + ',' + str(msg))
        return

    def funcName(self):
        name0 = inspect.stack()[1][0].f_code.co_name
        name1 = inspect.stack()[1][3]
        name2 = inspect.currentframe().f_code.co_name
        name3 = sys._getframe().f_code.co_name
        if name0 != name1: raise 'wtf, {}, {}'.format(name0, name1)
        return name0


class BaseHandler(BaseAgent):
    def __init__(self, parent=None):
        super(BaseHandler, self).__init__(parent)
        return
