### some qt utils

#from PyQt5 import QtCore
#from PyQt5.QtCore import QThread, QDateTime
from PyQt5.QtCore import *

def mygettid():
    ### simple gettid like C's syscall(__NR_gettid)
    import ctypes
    import platform

    syscalls = {
        'i386':   224,   # unistd_32.h: #define __NR_gettid 224
        'x86_64': 186,   # unistd_64.h: #define __NR_gettid 186
    }
    libcs = {
        'i386': '/lib/libc.so.6',
        'x86_64': '/lib64/libc.so.6',
    }
    # libc = ctypes.CDLL("/lib/libc.so.6")
    libc = ctypes.CDLL(libcs[platform.machine()])
    # tid = ctypes.CDLL('libc.so.6').syscall(224)
    return libc.syscall(syscalls[platform.machine()])

### in msgh: 0 <PyQt5.QtCore.QMessageLogContext object at 0x7fff84192358> aaaaaaaaa
def qt_debug_handler(tp, ctx, msg):
    #print("in msgh:", tp, ctx, msg)
    #print(ctx.function, ctx.file, ctx.line)

    tid = QThread.currentThreadId()  ### voidstr type
    tid = mygettid()
    tid = str(tid)
    
    now = QDateTime.currentDateTime()
    tmstr = now.toString("yyyy-MM-dd hh:mm:ss")

    fn = ''
    try:
        if ctx.file is None: # for qt internal msg
            fn = 'qtinternal'
        else:
            fn = ctx.file.encode('utf-8')
            fnl = ctx.file.split('/')
            fn = fnl[len(fnl)-1]
    except:
        fn = 'errfh'

    line = ctx.line
    function = None
    try:
        if type(ctx.function) == str: function = ctx.function
        elif type(ctx.function) == bytes: function = ctx.function.decode('utf8')
        else: function = ctx.function
    except:
        print(b'EEE:' + bytes(ctx.function, 'utf8'))

    if ctx.function == None: function = 'qtinternal'
    
    flog = "[" + tmstr + "] T(" + tid + ") " + fn + ":" + str(line) + " " + function \
        + " -- " + msg
    print(flog)

#usage
# qInstallMessageHandler(qt_debug_handler)


###
### TODO improve qDebug() function
### 多参数类型的qDebug
### 并且能够用上qt的 debug handler
### 不过这样不能正确获取调用栈信息了，还是不能用啊。
def qxDebug(*args):
    s = ''
    for arg in args:
        s += str(arg) + ' '
    qDebug(s)

#####
import sys, time
import signal
# from PyQt5.QtWidgets import qApp
from PyQt5.QtCore import QCoreApplication

### 必须与qt的timeout同时才能生效。
def sigint_handler(a0, a1):
    qApp = QCoreApplication.instance()
    print("SIGINT catched:", a0, a1, qApp)
    qApp.quit()
    sys.exit(0)

def pytimeout():
    time.sleep(0.0000001)

ctrl_timer = None
def pyctrl():
    qInstallMessageHandler(qt_debug_handler)
    qApp = QCoreApplication.instance()
    ctrl_timer = QTimer(qApp)
    ctrl_timer.timeout.connect(pytimeout)
    ctrl_timer.start(100)
    
    signal.signal(signal.SIGINT, sigint_handler)
    
