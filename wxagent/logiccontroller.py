# web weixin protocol

import os, sys
import json, re
import html
import enum
import time
import magic
import math

from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *


from .imrelayfactory import IMRelayFactory
from .wxcommon import *
from .wxmessage import *
from .wxsession import *
from .unimessage import *
from .botcmd import *
from .filestore import QiniuFileStore, VnFileStore

from .basecontroller import BaseController, Chatroom


#
#
class LogicController(BaseController):

    def __init__(self, rt, parent=None):
        "docstring"
        super(LogicController, self).__init__(rt, parent)

        self.relay_src_pname = self.__class__.__name__

        return


