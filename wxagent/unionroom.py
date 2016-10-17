from PyQt5.QtCore import *


class UnionRoom:
    def __init__(self):
        self.rooms = {'#channal_name': {
            'ctrl_name1': object,  # ChatRoom
            'ctrl_name2': object,  # ChatRoom
        }}
        self.rooms = {}
        return

    def existChannel(self, chan_name):
        if self.rooms.get(chan_name) is not None:
            return True
        return False

    def existContrl(self, chan_name, ctrl_name):
        if self.existChannel(chan_name):
            if self.rooms.get(chan_name).get(ctrl_name) is not None:
                return True
        return False

    def add(self, chan_name, ctrl_name, room_obj):
        if not self.existChannel(chan_name):
            self.rooms[chan_name] = {ctrl_name: room_obj}
        else:
            self.rooms[chan_name][ctrl_name] = room_obj
        return

    def get(self, chan_name, ctrl_name):
        if not self.existContrl(chan_name, ctrl_name):
            return None
        return self.rooms.get(chan_name).get(ctrl_name)

    def dumpKeys(self, ret=True):
        rooms = {}
        for chan in self.rooms:
            rooms[chan] = {}
            for ctrl in self.rooms[chan]:
                rooms[chan][ctrl] = ''

        if ret:
            return rooms
        else:
            qDebug(str(rooms))
        return
