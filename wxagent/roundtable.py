import json

from PyQt5.QtCore import *
from .baseagent import BaseAgent
from .toxcontroller import ToxController
from .wechatcontroller import WechatController
from .xmppcontroller import XmppController
from .irccontroller import IRCController
from .cmdcontroller import CmdController
from .unionroom import UnionRoom


# TODO should be based on BaseHandler?
class RoundTable(BaseAgent):
    def __init__(self, parent=None):
        super(RoundTable, self).__init__(parent)
        self.protocols = {}
        self.ctrls = {}
        self.rules = {}
        self.unichats = UnionRoom()
        return

    def Login(self):
        self.ctrls['ToxAgent'] = ToxController(self)
        self.ctrls['WechatAgent'] = WechatController(self)
        self.ctrls['XmppAgent'] = XmppController(self)
        self.ctrls['IRCAgent'] = IRCController(self)
        self.ctrls['CmdAgent'] = CmdController(self)

        for ctrl in self.ctrls:
            self.ctrls[ctrl].initSession()

        return

    def messageHandler(self, msg):
        qDebug('herhere')
        print(msg, msg.service(), ',', msg.path(), ',', msg.interface(), ',')
        qDebug(str(msg.arguments())[0:66].encode())
        msgo = json.JSONDecoder().decode(msg.arguments()[0])

        if msgo.get(self.OP) is not None:
            filtered = False
            if msgo['src'] == 'IRCAgent':
                msgo = self.ctrls['IRCAgent'].fillContext(msgo)
                self.ctrls['IRCAgent'].fillChatroom(msgo)
            elif msgo['src'] == 'XmppAgent':
                msgo = self.ctrls['XmppAgent'].fillContext(msgo)
                self.ctrls['XmppAgent'].fillChatroom(msgo)
            elif msgo['src'] == 'ToxAgent':
                msgo = self.ctrls['ToxAgent'].fillContext(msgo)
                self.ctrls['ToxAgent'].fillChatroom(msgo)
                filtered = self.ctrls['ToxAgent'].filterMessage(msgo)
            elif msgo['src'] == 'WechatAgent':
                msgo = self.ctrls['WechatAgent'].fillContext(msgo)
                self.ctrls['WechatAgent'].fillChatroom(msgo)
            else:
                qDebug('unsupported agent:' + msgo['src'])

            if filtered:
                qDebug('filtered: {} from {}'.format(filtered, msgo['src']))
            else:
                self.processOperator(msgo)
        elif msgo.get(self.EVT) is not None:
            self.processEvent(msgo)
        else:
            raise 'wtf'
        return

    def processOperator(self, msgo):
        if msgo['src'] == 'IRCAgent':
            self.processOperatorIRC(msgo)
        elif msgo['src'] == 'WechatAgent':
            self.processOperatorWechat(msgo)
        elif msgo['src'] == 'XmppAgent':
            self.processOperatorXmpp(msgo)
        elif msgo['src'] == 'ToxAgent':
            self.processOperatorTox(msgo)
        elif msgo['src'] == 'RoundTable':
            self.processOperatorRoundTable(msgo)
        else:
            qDebug('not supported agent: ' + msgo['src'])

        self.processCommand(msgo)
        return

    def processOperatorIRC(self, msgo):
        rules = ['ToxAgent', 'WechatAgent', 'XmppAgent']
        rules = ['ToxAgent', 'WechatAgent']
        rules = ['ToxAgent']
        remsg = 're: ' + msgo['params'][0]
        args = self.makeBusMessage('reply', None, remsg)
        args['context'] = msgo['context']

        for rule in rules:
            args['dest'] = [rule]
            if self.ctrls.get(rule) is not None:
                self.ctrls[rule].replyMessage(args)

        return

    def processOperatorWechat(self, msgo):
        rules = ['ToxAgent', 'XmppAgent', 'IRCAgent']
        rules = ['ToxAgent']
        remsg = 're: ' + msgo['params'][1]
        args = self.makeBusMessage('reply', None, remsg)
        args['context'] = msgo['context']

        for rule in rules:
            args['dest'] = [rule]
            if self.ctrls.get(rule) is not None:
                self.ctrls[rule].replyMessage(args)

        return

    def processOperatorXmpp(self, msgo):
        rules = ['ToxAgent', 'WechatAgent', 'IRCAgent']
        remsg = 're: ' + msgo['params'][1]
        args = self.makeBusMessage('reply', None, remsg)
        args['context'] = msgo['context']

        for rule in rules:
            args['dest'] = [rule]
            if self.ctrls.get(rule) is not None:
                self.ctrls[rule].replyMessage(args)

        return

    def processOperatorTox(self, msgo):
        rules = ['IRCAgent', 'WechatAgent', 'XmppAgent']
        rules = ['IRCAgent', 'XmppAgent']
        rules = ['IRCAgent']
        qDebug(str(msgo['params']).encode())
        remsg = 're: ' + msgo['params'][2]
        args = self.makeBusMessage('reply', None, remsg)
        args['context'] = msgo['context']

        for rule in rules:
            args['dest'] = [rule]
            if self.ctrls.get(rule) is not None:
                self.ctrls[rule].replyMessage(args)

        return

    def processOperatorRoundTable(self, msgo):
        if msgo['op'] == 'showpiclink':
            remsg = msgo['params'][0]
            args = self.makeBusMessage('reply', None, remsg)
            args['context'] = msgo['context']
            self.ctrls['ToxAgent'].replyMessage(args)
            # self.ctrls['XmppAgent'].replyMessage(args)
            return

        if msgo['op'] == 'notinfo':
            remsg = msgo['params'][0]
            args = self.makeBusMessage('reply', None, remsg)
            args['context'] = msgo['context']
            self.ctrls['ToxAgent'].replyMessage(args)
            # self.ctrls['XmppAgent'].replyMessage(args)
            return

        if msgo['op'] == 'showtitle':
            qDebug('hereeee')
            qDebug(str(msgo).encode())
            if msgo['context']['content'] == '':
                return
            msgo['src'] = msgo['context']['src']
            if msgo['src'] == 'IRCAgent':
                self.processOperatorIRC(msgo)
                self.ctrls[msgo['src']].replyMessage(msgo)
            elif msgo['src'] == 'XmppAgent':
                self.processOperatorXmpp(msgo)
            elif msgo['src'] == 'ToxAgent':
                self.processOperatorTox(msgo)
                self.ctrls[msgo['src']].replyMessage(msgo)
            # elif msgo['src'] == 'RoundTable':
            #    self.processOperatorRoundTable(msgo)
            else:
                qDebug('not supported agent: ' + msgo['src'])
            return

        return

    def processCommand(self, msgo):
        self.ctrls['CmdAgent'].replyMessage(msgo)
        return

    def processEvent(self, msgo):
        if self.ctrls.get(msgo['src']) is not None:
            self.ctrls.get(msgo['src']).updateSession(msgo)

        return
