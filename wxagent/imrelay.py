# base relay class

from abc import ABCMeta,abstractmethod

from PyQt5.QtCore import *


class IMRelay(QObject):

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
        supert(self, IMRelay).__init__(parent)

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