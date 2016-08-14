import pydbus
from gi.repository import GObject

sysbus = pydbus.SystemBus()

systemd = sysbus.get('io.qtc.wxagent')

def handler1(a, b, c, d, e):
    print(11111, a, b, c, d, e)
    return

# help(sysbus.subscribe)
sysbus.subscribe(iface='io.qtc.wxagent.signals', signal='newmessage', signal_fired=handler1)

GObject.MainLoop().run()
