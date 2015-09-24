# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtNetwork import *
from PyQt5.QtDBus import *
from .wxcommon import *
from .wxsession import *
from .wxprotocol import *

class Ui_MainWindow(object):
    MainWindow = ''
    top = 10
    left = 20
    height = 40
    width = 150
    fromuser = None
    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(684, 469)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(20, 10, 84, 33))
        self.pushButton.setObjectName("pushButton")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(20, 100, 201, 201))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(270, 90, 54, 17))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(340, 90, 141, 17))
        self.label_3.setObjectName("label_3")
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(120, 10, 84, 33))
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_3.setGeometry(QtCore.QRect(220, 10, 84, 33))
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_4.setGeometry(QtCore.QRect(320, 10, 84, 33))
        self.pushButton_4.setObjectName("pushButton_4")
        self.pushButton_5 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_5.setGeometry(QtCore.QRect(420, 10, 84, 33))
        self.pushButton_5.setObjectName("pushButton_5")
        self.pushButton_6 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_6.setGeometry(QtCore.QRect(20, 50, 84, 33))
        self.pushButton_6.setObjectName("pushButton_6")
        self.pushButton_10 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_10.setGeometry(QtCore.QRect(580, 400, 80, 40))
        self.pushButton_10.setObjectName('pushButton_10')
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setGeometry(QtCore.QRect(230, 150, 441, 181))
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.pushButton_7 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_7.setGeometry(QtCore.QRect(120, 50, 101, 33))
        self.pushButton_7.setObjectName("pushButton_7")
        self.pushButton_8 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_8.setGeometry(QtCore.QRect(230, 50, 81, 33))
        self.pushButton_8.setObjectName("pushButton_8")
        self.pushButton_9 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_9.setGeometry(QtCore.QRect(230, 50, 81, 33))
        self.pushButton_9.setObjectName("pushButton_9")
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(310, 50, 361, 31))
        self.lineEdit.setObjectName("lineEdit")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 684, 29))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton.setText(_translate("MainWindow", "login"))
        self.label.setText(_translate("MainWindow", "TextLabel"))
        self.pushButton_2.setText(_translate("MainWindow", "logout"))
        self.pushButton_3.setText(_translate("MainWindow", "get contact"))
        self.pushButton_4.setText(_translate("MainWindow", "sync check"))
        self.pushButton_5.setText(_translate("MainWindow", "web sync"))
        self.pushButton_6.setText(_translate("MainWindow", "refresh"))
        self.pushButton_7.setText(_translate("MainWindow", "create session"))
        self.pushButton_8.setText(_translate("MainWindow", "geturl"))


    def addButton(self, fromuser, users):
        self.fromuser = fromuser
        MainWindow = self.MainWindow
        MainWindow.resize(850, 500)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        _translate = QtCore.QCoreApplication.translate
        self.leftFiller = QtWidgets.QWidget()
        for user in users :
            self.pushButton_9 = QtWidgets.QPushButton(self.leftFiller)
            self.pushButton_9.setGeometry(QtCore.QRect(self.left, self.top, self.width, self.height))
            self.top = self.top+self.height
            self.pushButton_9.setObjectName(user['UserName'])
            if user['RemarkName'] == '':
                nickName = re.sub(r'<\w.*>', '', user['NickName'])
                self.pushButton_9.setText(_translate("MainWindow", user['NickName']))
            else :
                self.pushButton_9.setText(_translate("MainWindow", user['RemarkName']))
            self.pushButton_9.released.connect(self.getUserName)

        self.leftFiller.setMinimumSize ( 40, self.top)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self.leftFiller) 
        scroll.setWidgetResizable(True)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(scroll)  
        self.centralwidget.setLayout(vbox)


        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setGeometry(QtCore.QRect(230, 10, 441, 181))
        self.plainTextEdit.setObjectName("plainTextEdit")

        self.plainTextEdit_1 = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_1.setGeometry(QtCore.QRect(230, 200, 441, 181))
        self.plainTextEdit_1.setObjectName("plainTextEdit_1")

        self.pushButton_10 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_10.setGeometry(QtCore.QRect(580, 400, 80, 40))
        self.pushButton_10.setObjectName('pushButton_10')
        self.pushButton_10.setText(_translate("MainWindow", '发送' ))
        self.pushButton_10.released.connect(self.postUserMsg)

        self.pushButton.released.connect(self.postUserMsg)
        MainWindow.setCentralWidget(self.centralwidget)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
     
        return 


    def getUserName(self):
        obj = self.MainWindow.sender()
        self.plainTextEdit_1.appendPlainText('me say to:'+str(obj.objectName())+':')

        return 

    def postUserMsg(self):
        self.sysbus = QDBusConnection.systemBus()
        self.sysiface = QDBusInterface(WXAGENT_SERVICE_NAME, '/io/qtc/wxagent', WXAGENT_IFACE_NAME, self.sysbus)
        from_username =  self.fromuser.UserName
        text = self.plainTextEdit_1.toPlainText()
        paramslist = text.split(':')
        to_username = paramslist[1]
        content = paramslist[2]
        self.sysiface.call('sendmessage', from_username, to_username, content)

        return 
