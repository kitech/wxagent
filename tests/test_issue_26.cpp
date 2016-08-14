/*
  build:
     moc tests/test_issue_26.cpp > tests/test_issue_26.moc
     g++ ./tests/test_issue_26.cpp -fPIC -lQt5DBus -I /usr/include/qt -I /usr/include/qt/QtDBus
 */

#include <QtCore>
#include <QtDBus>
#include <qdbusutil_p.h>


class Handler : public QObject {
    Q_OBJECT;
public:
    Handler() : QObject(0) {
    }

public slots:
    void onmsg(QDBusMessage m) {
        qDebug()<<"hehhhehhhhhhhhh"<<m;
    }
};

int main(int argc, char **argv) {
    QCoreApplication a(argc, argv);

    auto sysbus = QDBusConnection::systemBus();
    QString service = "io.qtc.wxagent";
    QString path = "/io/qtc/wxagent/signals";
    QString iface = "io.qtc.wxagent.signals";
    // sysbus.registerService(service);

    qDebug()<<sysbus.isConnected();
    Handler* h = new Handler();
    auto ret = sysbus.connect(QString(""), path, iface, "newmessage", h, SLOT(onmsg(QDBusMessage)));
    qDebug()<<ret<<sysbus.lastError()<<sysbus.isConnected();
    ret = sysbus.connect("", "", iface, "newmessage", h, SLOT(onmsg(QDBusMessage)));
    qDebug()<<ret<<sysbus.lastError()<<sysbus.isConnected();

    {
        auto receiver = h;
        auto slot = SLOT(onmsg());
        auto interface = iface;
        QString name = "newmessage";

        if (!receiver || !slot) {
            qDebug()<<"false1";
        }
        if (interface.isEmpty() && name.isEmpty()) {
            qDebug()<<"false2";
        }

        if (!interface.isEmpty() && !QDBusUtil::isValidInterfaceName(interface)) {
            qDebug("QDBusConnection::connect: interface name '%s' is not valid", interface.toLatin1().constData());
        } else {
            qDebug()<<"valid iface:"<<interface;
        }
        if (!service.isEmpty() && !QDBusUtil::isValidBusName(service)) {
            qDebug("QDBusConnection::connect: service name '%s' is not valid", service.toLatin1().constData());
        } else {
            qDebug()<<"valid bus name:"<<service;
        }
        if (!path.isEmpty() && !QDBusUtil::isValidObjectPath(path)) {
            qDebug("QDBusConnection::connect: object path '%s' is not valid", path.toLatin1().constData());
        } else {
            qDebug()<<"valid objpath"<<path;
        }
    }

    qDebug()<<"enter main loop";
    return a.exec();
}

#include "test_issue_26.moc"

