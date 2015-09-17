ubuntu 12.02 64位


### 软件

	python 3.5 安装  https://www.python.org/downloads/release/python-350/   params : -with-zlib=/usr/include

	qt.run 安装 download.qt.io/official_releases/qt/5.5/5.5.0/qt-opensource-linux-x64-5.5.0-2.run

	sip 安装  http://sourceforge.net/projects/pyqt/files/sip/sip-4.16.9/sip-4.16.9.tar.gz/download

	pyqt5 https://www.riverbankcomputing.com/software/pyqt/download5

	python setuptools 安装 版本自己选择，建议最新的

	toxcore https://github.com/irungentoo/toxcore

		git clone git://github.com/irungentoo/toxcore.git
		cd toxcore
		autoreconf -i
		./configure
		make
		sudo make install

		git clone https://github.com/jedisct1/libsodium/
		cd libsodium
		git checkout tags/1.0.0
		./autogen.sh
		./configure 
		make
		make install
	
	pytox  https://github.com/kitech/PyTox/tree/newapi (相信我，这个作者的解决了https://github.com/aitjcize/PyTox/issues/44 这个问题)

	autoreconf apt-get install dh-autoreconf



###problem：

1.Compression requires the (missing) zlib module

 	1) Of course, you need to install zlib first. and you can find zlib.h in /usr/include

	2) ./configure -with-zlib=/usr/include   make && sudo make install

2.qmake版本不符合， 安装Qt5.5，就可以了复制一份为/usr/bin/qmake

3.pyqt5.5 configure.py 2591-2594 注释掉

4.加入环境变量export PATH=/usr/local/Qt/5.5.0/5.5/gcc/bin:$PATH

5.如果你安装好了,就直接执行 python3.5 configure.py  --qmke /usr/local/bin/qmake --sip /usr/local/bin/sip --verbosse

6. Unable to create the QtCore directory： 安装sip-4.17版本

7.Makefile.am: required file `./README' not found  在toxcore 里面执行ln -s README.md README

8.org.freedesktop.DBus.Error.AccessDenied Connection ":1.158" is not allowed to own the service "io.qtc.wxagent" due to security policies in the configuration file
	cp  /var/www/wxagent/archlinux/wxagent.conf /etc/dbus-1/system.d/wxagent.conf

9. can't find /lib64/libc.so.6 in 12.04 

	cp /lib/x86_64-linux-gnu/lib.so.6 /lib64/

10.: No module named 'PyQt5.QtGui'
		 sudo apt-get install libgl1-mesa-dev


	





	