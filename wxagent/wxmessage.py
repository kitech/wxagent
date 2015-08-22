
import os, sys
import json, re
import enum

from PyQt5.QtCore import *


class WXMessage():

    def __init__(self):
        "docstring"

        self.rawMessage = ''
        
        self.MsgType = 0
        self.MsgId = ''
        self.FromUserName = ''
        self.ToUserName = ''
        self.CreateTime = 0

        return

    
        
