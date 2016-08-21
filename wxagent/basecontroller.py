
from PyQt5.QtCore import *


class BaseController(QObject):

    def __init__(self, rt, parent=None):
        super(BaseController, self).__init__(parent)
        self.rt = rt
        return

    def initSession(self):
        return

    def updateSession(self, msgo):
        return
