import sys
from PyQt5.QtCore import *
from .RoundTableServer import *
from .qtutil import pyctrl


def main():
    app = QCoreApplication(sys.argv)
    pyctrl()

    rto = None
    if len(sys.argv) == 2 and sys.argv[1] == 'client':
        qDebug('not impled: {}'.format(sys.argv[1]))
        sys.exit(0)
    else:
        rto = RoundTableServer()

    qDebug('qtloop...{}'.format(rto))
    sys.exit(app.exec_())
    return


if __name__ == '__main__': main()
