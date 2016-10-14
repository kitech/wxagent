# xmpp protocol IM relay class

import os, sys
import json, re
import logging
from collections import defaultdict

from PyQt5.QtCore import *

import sleekxmpp

from .imrelay import IMRelay
from .unimessage import XmppMessage


class XmppRelay(IMRelay):

    def __init__(self, parent=None):
        super(XmppRelay, self).__init__(parent)

        self.unimsgcls = XmppMessage
        self.src_pname = ''

        self.self_user = ''
        self.peer_user = ''
        self.nick_name = ''

        self.xmpp = None  # XmppCallProxy

        return

    # abstract method implemention
    # @return True|False
    def sendMessage(self, msg, peer):
        rc = self.xmpp.send_message(mto=peer, mbody=msg)
        qDebug(str(rc))
        return True

    # @return True|False
    def sendGroupMessage(self, msg, peer):
        rc = self.xmpp.muc_send_message(peer, msg)
        qDebug(str(rc))
        return rc

    # @return True|False
    def sendFileMessage(self, msg, peer):
        return

    # @return True|False
    def sendVoiceMessage(self, msg, peer):
        return

    # @return True|False
    def sendImageMessage(self, msg, peer):
        return

    def disconnectIt(self):
        self.xmpp.disconnect()
        return

    def isConnected(self):
        # st = self.xmpp.state.current_state
        # qDebug(str(st))
        return self.is_connected

    def isPeerConnected(self, peer):
        # qDebug(str(self.fixstatus))
        return self.fixstatus[peer]

    def createChatroom(self, room_key, title):
        room_ident = '%s.%s' % (self.src_pname, room_key)
        room_ident = '%s.%s' % (self.src_pname, self._roomify_name(title))
        qDebug(self.src_pname.encode())
        qDebug(self._roomify_name(title).encode())
        qDebug(room_ident.encode())
        room_ident = room_key
        self.xmpp.create_muc2(room_ident, title)
        return room_ident.lower()

    def groupInvite(self, group_number, peer):
        self.xmpp.muc_invite(group_number, peer)
        return

    def groupNumberPeers(self, group_number):
        return self.xmpp.muc_number_peers(group_number)

    def on_connected(self, what=None):
        qDebug('hreere:' + str(what))
        # self.is_connected = True
        # self.connected.emit()
        return

    def on_connection_failed(self):
        qDebug('hreere')
        self.is_connected = False
        self.disconnected.emit()
        return

    def on_disconnected(self, what=None):
        qDebug('hreere:' + str(what))
        self.is_connected = False
        self.disconnected.emit()
        return

    def on_peer_connected(self, peer):
        qDebug('hereee:' + str(peer))
        self.peerConnected.emit(peer)
        return

    def on_peer_disconnected(self, peer):
        qDebug('hereee:' + str(peer))
        self.peerDisconnected.emit(peer)
        return

    def on_peer_enter_group(self, peer):
        qDebug('hereee:' + str(peer))
        self.peerEnterGroup.emit(peer)
        return

    def on_session_start(self, event):
        qDebug('hhere:' + str(event))

        self.xmpp.send_presence()
        self.xmpp.get_roster()

        # self.xmpp.plugin['xep_0045'].joinMUC('yatest0@conference.xmpp.jp', 'yatbot0inmuc')
        # self.create_muc('yatest1')
        return

    def on_message(self, msg):
        qDebug(b'hhere:' + str(msg).encode())

        if msg['type'] in ('chat', 'normal'):
            # msg.reply("Thanks for sending 000\n%(body)s" % msg).send()
            # self.xmpp.send_message(mto=msg['from'], mbody='Thanks 国为 for sending:\n%s' % msg['body'])
            self.newMessage.emit(msg['body'])
        elif msg['type'] in ('groupchat'):
            mto = msg['from'].bare
            # print(msg['from'], "\n")
            # qDebug(mto)

            if msg['from'].resource == self.peer_jid.split('@')[0]:
                mgroup = msg['from'].user
                mbody = msg['body']
                self.newGroupMessage.emit(mgroup, mbody)
            else:  # myself send
                pass

            if msg['from'] != 'yatest1@conference.xmpp.jp/yatbot0inmuc' and \
               msg['from'] != 'yatest0@conference.xmpp.jp/yatbot0inmuc':
                pass
                # self.xmpp.send_message(mto=mto, mbody='Thanks 国为 for sending:\n%s' % msg['body'],
                #                       mtype='groupchat')
            else:
                pass

        # import traceback
        # traceback.print_stack()
        # qDebug('done msg...')
        return

    def on_muc_message(self, msg):
        # qDebug(b'hhere:' + str(msg).encode())

        #if msg['mucnick'] != self.nick and self.nick in msg['body']:
        #   qDebug('want reply.......')
            # self.send_message(mto=msg['from'].bare,
            #                  mbody="I heard that, %s." % msg['mucnick'],
            #                  mtype='groupchat')
        #    pass

        return

    def on_groupchat_invite(self, inv):
        qDebug(b'hreree:' + str(inv).encode())

        if inv['from'].bare == self.xmpp.boundjid:
            pass  # from myself
        else:
            room = inv['from'].bare
            muc_nick = self.nick_name
            self.plugin_muc.joinMUC(room, muc_nick)
            # self.groupInvite.emit(room)
        return

    def on_groupchat_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def on_muc_room_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def on_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())

        # qDebug(str(self.xmpp.roster))
        qDebug(str(self.xmpp.client_roster).encode())
        # qDebug(str(self.xmpp.client_roster['yatseni@xmpp.jp'].resources).encode())
        qDebug(str(self.xmpp.client_roster[self.peer_user].resources).encode())

        def check_self_presence(presence):
            if presence['to'] == presence['from']:
                return True
            return False

        def check_peer_presence(presence):
            if presence['from'].bare == self.peer_user:
                return True
            return False

        if check_self_presence(presence):
            self.is_connected = True
            self.connected.emit()
            return

        # peer user presence
        if check_peer_presence(presence):
            if presence['type'] == 'unavailable':
                for room in self.fixrooms:
                    if self.peer_user in self.fixrooms[room]:
                        self.fixrooms[room].remove(self.peer_user)
                self.fixstatus[self.peer_user] = False
                self.peerDisconnected.emit(self.peer_user)
            else:
                for room in self.fixrooms:
                    if self.peer_user not in self.fixrooms[room]:
                        # self.fixrooms[room].append(self.peer_user)
                        pass  # 这个地方不能再添加，对方掉线情况，需要使用invite才行。
                self.fixstatus[self.peer_user] = True
                self.peerConnected.emit(self.peer_user)
            return

        # 以下是关于room的presence处理
        room_jid = presence['from'].bare
        peer_jid = ''

        exp = r'jid="([^/]+)/\d+"'
        mats = re.findall(exp, str(presence))
        print(mats)
        if len(mats) == 0:
            # now care presence
            return

        # muc presence
        peer_jid = mats[0]
        if presence['type'] == 'unavailable':
            if peer_jid in self.fixrooms[room_jid]:
                self.fixrooms[room_jid].remove(peer_jid)
        else:
            onum = len(self.fixrooms[room_jid])
            if peer_jid not in self.fixrooms[room_jid]:
                self.fixrooms[room_jid].append(peer_jid)
            nnum = len(self.fixrooms[room_jid])
            if nnum == 2 and self.peer_user in self.fixrooms[room_jid]:
                user = presence['from'].user
                self.peerEnterGroup.emit(user)

        qDebug(str(self.fixrooms).encode())
        return

    def on_presence_avaliable(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def create_muc(self, name):
        muc_name = '%s@%s' % (name, self.xmpp_conference_host)
        muc_nick = self.nick_name
        self.plugin_muc.joinMUC(muc_name, muc_nick)
        print(self.plugin_muc.rooms)
        return

    # TODO 检测聊天室是否已经存在，是否是自己创建的
    def create_muc2(self, room_jid, nick_name):
        muc_name = '%s@%s' % (room_jid, self.xmpp_conference_host)
        muc_nick = nick_name
        self.xmpp.add_event_handler('muc::%s::presence' % muc_name, self.on_muc_room_presence)
        qDebug((muc_name + ',,,' + muc_nick).encode())
        self.plugin_muc.joinMUC(muc_name, muc_nick)
        self.plugin_muc.setAffiliation(muc_name, jid=self.peer_user)
        print(self.plugin_muc.rooms, muc_name, self.xmpp.boundjid.bare)
        qDebug(str(self.plugin_muc.jidInRoom(muc_name, self.xmpp.boundjid.bare)))
        nowtm = QDateTime.currentDateTime()
        muc_subject = 'Chat with %s@%s since %s' \
                      % (nick_name, room_jid, nowtm.toString('H:m:ss M/d/yy'))
        # 设置聊天室主题
        self.xmpp.send_message(mto=muc_name, mbody=None,
                               msubject=muc_subject, mtype='groupchat')
        return

    def muc_invite(self, room_name, peer_jid):
        qDebug('heree')
        room_jid = '%s@%s' % (room_name, self.xmpp_conference_host)
        reason = 'hello come here:' + room_jid
        self.plugin_muc.invite(room_jid, peer_jid, reason=reason)  # , mfrom=mfrom)
        return

    def muc_number_peers(self, room_jid):
        muc_name = '%s@%s' % (room_jid.lower(), self.xmpp_conference_host)
        qDebug((muc_name + str(self.fixrooms)).encode())
        # room_obj = self.plugin_muc.rooms[muc_name]
        room_obj = self.fixrooms[muc_name]
        qDebug(str(room_obj) + '==len==' + str(len(room_obj)))
        for e in self.fixrooms:
            qDebug(str(e).encode())
        # qDebug(str(room_obj) + str(self.plugin_muc.rooms.keys()))
        # for room_name in self.plugin_muc.rooms:
        #    room_obj = self.plugin_muc.rooms[room_name]
        #    print(room_obj)
        return len(room_obj)

    def muc_send_message(self, room_name, msg):
        mto = '%s@%s' % (room_name, self.xmpp_conference_host)
        mbody = msg
        mtype = 'groupchat'
        qDebug(mto.encode())
        self.xmpp.send_message(mto=mto, mbody=mbody, mtype=mtype)
        return

    def send_message(self, peer_jid, msg):
        mto = peer_jid
        mbody = msg
        mtype = 'chat'
        self.xmpp.send_message(mto=mto, mbody=mbody, mtype=mtype)
        return

    # 把oname中的特殊字符转换为xmpp支持conference名
    # 主要思路是把特殊的符号过滤掉，手动替换为*
    # '"@&  => ****+
    def _roomify_name(self, oname):
        nname = ''
        for ch in oname:
            nch = ch
            if ch in ("'", '"', '@', '&'):
                nch = '*'
            elif ch in (' '):
                nch = '+'
            elif ch in ('#'):
                nch = '.'
            elif ch in ('<', '>', '(', ')'):
                nch = '.'
            elif ch in ('，'):  # 全角标点
                nch = ','
            elif ch in ('。'):
                nch = '.'
            nname += nch
        return nname


if __name__ == '__main__':
    pass
