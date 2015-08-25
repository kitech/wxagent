### 微信登陆代理

微信桌面版做的很弱，并且没有Linux版。

虽然在Linux上可以使用微信web版，有时很难在一堆浏览器标签中找到。

像这样的应用，应该有属于自己的程序窗口与桌面空间。


##### 微信登陆代理实现目标

提供后台服务，管理微信登陆会话，负责与服务器通信。

以后台服务的方式运行，占用资源少，并且能够长时间运行，避免了需要经常手机扫描登陆的麻烦。

不过，由于这个代理提供的消息服务不再有认证等安全功能，登陆代理最好安装在安全的机器上，像本机上，或者是内网的私有服务器上。


##### 微信登陆代理原理

提到实现，不免要涉及到微信通信协议，好在已经有人对微信web版协议做了分析，虽然还有不完善的地方，基本上可以实现简单登陆与消息收发功能了。

微信登陆代理根据现有资料，使用PyQt5实现了微信web版协议，通过测试，把相关API更新到了最新的微信的wx2版本。

并且把二维码以dbus服务方式提供出来，这样该服务就不需要有UI的支持了，这也是与现有几个Linux版微信不同的地方。

除了以DBus方式提供API，还可以使用socket方式，可以更灵活了。

微信登陆代理实际上非常像ssh-agent的工作模式，长时间保持住会话，而不受UI交互客户端的启动或者退出状态的影响。



##### 微信登陆代理模块


* 服务端
* 客户端
* dbus服务方法
* dbus总线事件


##### 微信登陆代理提供的服务API

wxagent提供的dbus服务方法： dbus://io.qtc.wxagent


islogined: sync方法, 参数表，无

    返回值：bool

getqrpic: sync方法，参数表，无

    返回值：image/jpeg data, base64 encoded

refresh: sync方法，参数表，无

    返回值：bool

logout: sync方法，参数表，无

    返回值：bool

getinitdata: sync方法，参数表，无

    返回值：json string

getcontact: sync方法，参数表，无

    返回值：json string

sendmessage: sync方法，

    参数表：(from_username str, to_username str, content str, msgtype int)
    返回值：json string
    

dumpinfo: sync方法，参数表，无

geturl: async方法，参数表，(url str)


wxagent提供的dbus事件信号： dbus://io.qtc.wxagent.signals

logined: 参数，bool

logouted: 参数，bool

newmessage: 参数，json string



##### 微信登陆代理程序及客户端

wxagent: 使用PyQt5实现的wxagent后台服务程序。

    cd /path/to/wxagent
    python setup.py install
    /usr/bin/wxagent

wxaui: 使用PyQt5实现的简易wxagent客户端，显示微信登陆二维码，接收消息（消息未分类）。

      /usr/bin/wxaui

wx2tox: 使用PyQt5实现的wxagent客户端，并将收到的消息分类转发到qTox IM客户端，以qTox(toxcore)群形式表示微信聊天会话。

      /usr/bin/wx2tox


##### 微信web版协议

[weixin web protocol.md(v2)](https://github.com/kitech/wxagent/doc/protocolv2.md)

[weixin web protocol.md(v1)](https://github.com/kitech/wxagent/doc/protocol.md)


