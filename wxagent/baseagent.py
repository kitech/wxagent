import json

from PyQt5.QtCore import *


class BaseAgent(QObject):
    PushMessage = pyqtSignal(str)
    OP = 'op'
    EVT = 'evt'

    def __init__(self, parent=None):
        super(BaseAgent, self).__init__(parent)
        return

    def Login(self):
        return

    def Logout(self):
        return

    def RecvMessage(self):
        return

    def SendMessageX(self, msg: dict):
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
