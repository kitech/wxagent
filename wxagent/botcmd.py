# bot command handler

import os, sys
import json, re
import enum

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *


class BotCmder(QObject):

    cmds = [
        'help', 'invite', 'stats',
    ]

    cmdpch = '.'

    def __init__(self, parent=None):
        super(BotCmder, self).__init__(parent)
        return

    # @param cmd str
    # @return cmd | False
    def parseCmd(cmdline):
        exp = r"^\.([a-z]+)(.*)"
        mats = re.findall(exp, cmdline)
        qDebug(str(mats).encode())
        if len(mats) == 0: return False

        cmd = mats[0][0]
        if cmd not in BotCmder.cmds: return False

        return mats[0]

    def helpMessage():
        msg = 'valid cmds: .' + ',.'.join(BotCmder.cmds)
        return msg
