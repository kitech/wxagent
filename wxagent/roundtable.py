import json

from PyQt5.QtCore import *
from .baseagent import BaseAgent
from .toxcontroller import ToxController

# TODO should be based on BaseHandler?
class RoundTable(BaseAgent):
    def __init__(self, parent=None):
        super(RoundTable, self).__init__(parent)
        self.protocols = {}
        self.ctrls = {}
        self.rules = {}
        return

    def Login(self):
        self.ctrls['ToxAgent'] = ToxController(self)

        for ctrl in self.ctrls:
            self.ctrls[ctrl].initSession()

        return

    def messageHandler(self, msg):
        qDebug('herhere')
        print(msg, msg.service(), ',', msg.path(), ',', msg.interface(), ',', msg.arguments())
        msgo = json.JSONDecoder().decode(msg.arguments()[0])
        if msgo.get(self.OP) is not None:
            self.processOperator(msgo)
        elif msgo.get(self.EVT) is not None:
            self.processEvent(msgo)
        else:
            raise 'wtf'
        return

    def processOperator(self, msgo):
        if msgo['src'] == 'IRCAgent':
            self.processOperatorIRC(msgo)
        return

    def processOperatorIRC(self, msgo):
        rules = ['ToxAgent', 'WXAgent', 'XmppAgent']
        remsg = 're: ' + msgo['params'][0]
        args = self.makeBusMessage('reply', None, remsg)
        # args['dest'] = ['ToxAgent', 'WXAgent', 'XmppAgent']
        args['sender'] = msgo
        # self.SendMessageX(args)

        for rule in rules:
            args['dest'] = [rule]
            if self.ctrls.get(rule) is not None:
                self.ctrls[rule].replyMessage(args)

        return

    def processEvent(self, msgo):
        if self.ctrls.get(msgo['src']) is not None:
            self.ctrls.get(msgo['src']).updateSession(msgo)

        return
