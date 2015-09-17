

# web weixin protocol

import os, sys
import json, re
import enum

from PyQt5.QtCore import *


class WXProtocol(QObject):
    def __init__(self):
        "docstring"

        return

    
    def parseWebSyncNotifyGroups(self, hcc):
        strhcc = hcc.data().decode()
        hccjs = json.JSONDecoder().decode(strhcc)

        grnames = {}

        for msg in hccjs['AddMsgList']:
            StatusNotifyCode = msg['StatusNotifyCode']
            qDebug(str(StatusNotifyCode))
            StatusNotifyUserName = msg['StatusNotifyUserName']
            segs = StatusNotifyUserName.split(',')
            for seg in segs:
                if seg.startswith('@@'):
                    grnames[seg] = 1

        for msg in hccjs['ModContactList']:
            name = msg['UserName']
            if name.startswith('@@'):
                grnames[name] = 1
        
        return grnames

    
