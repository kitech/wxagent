# base relay class

from abc import ABCMeta,abstractmethod

from PyQt5.QtCore import *


class IMRelay(QThread):

    __metaclass__ = ABCMeta

    # 不同的relay，可能有不同的参数，如何统一一下呢。
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal('QString')   # just the message
    peerConnected = pyqtSignal('QString')   # peer identifier
    peerDisconnected = pyqtSignal('QString')  # peer identifier
    peerEnterGroup = pyqtSignal('QString')  # group identifier
    newGroupMessage = pyqtSignal('QString', 'QString')  # group identifier, msg

    def __init__(self, parent=None):
        super(IMRelay, self).__init__(parent)
        self.src_pname = 'WXU.or.WQU'  # src proto name
        return

    # @return True|False
    @abstractmethod
    def sendMessage(self, msg, peer):
        return

    # @return True|False
    @abstractmethod
    def sendGroupMessage(self, msg, peer):
        return

    # @return True|False
    @abstractmethod
    def sendFileMessage(self, msg, peer):
        return

    # @return True|False
    @abstractmethod
    def sendVoiceMessage(self, msg, peer):
        return

    # @return True|False
    @abstractmethod
    def sendImageMessage(self, msg, peer):
        return

    @abstractmethod
    def disconnectIt(self):
        return

    @abstractmethod
    def isConnected(self):
        return

    @abstractmethod
    def isPeerConnected(self, peer):
        return

    @abstractmethod
    def createChatroom(self, key, title):
        return

    @abstractmethod
    def groupInvite(self, group_number, peer):
        return

    @abstractmethod
    def groupNumberPeers(self, group_number):
        return
