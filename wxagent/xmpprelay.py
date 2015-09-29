# toxcore protocol IM relay class

from PyQt5.QtCore import *

from .imrelay import IMRelay


class XmppRelay(IMRelay):

    def __init__(self, parent=None):
        supert(self, XmppRelay).__init__(parent)
