# toxcore protocol IM relay class

from PyQt5.QtCore import *

from .imrelay import IMRelay


class ToxRelay(IMRelay):

    def __init__(self, parent=None):
        super(ToxRelay, self).__init__(parent)
