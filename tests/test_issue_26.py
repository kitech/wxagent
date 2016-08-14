import sys

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

app = QCoreApplication(sys.argv)

sysbus = QDBusConnection.systemBus()

agent_service = 'io.qtc.wxagent'
agent_service_path = '/io/qtc/wxagent'
agent_service_iface = 'io.qtc.wxagent.iface'
sysiface = QDBusInterface(agent_service, agent_service_path,
                          agent_service_iface, sysbus)

service = agent_service
path = '/io/qtc/wxagent/signals'
iface = 'io.qtc.wxagent.signals'

class Handler(QObject):
    def __init__(self, parent=None):
        super(Handler, self).__init__(parent)
        return

    @pyqtSlot(QDBusMessage)
    def onmsg(self, msg):
        return


h = Handler()
print(sysbus)
# bug: blow line will block
# fixed: http://stackoverflow.com/questions/38142809/pyqt-5-6-connecting-to-a-dbus-signal-hangs
if True:
    sysbus.registerObject('/', h)
sysbus.connect('', '', iface, 'newmessage', h.onmsg)
print('runnnnnn')
app.exec_()
