wxagent.py 负责wx登陆，保持会话，代理请求，无需UI，可以以服务模式启动。
使用socket服务通信，或者dbus通信，无会话模式。

程序逻辑描述：
wxagent启动后，其行为类似wx2.qq.com，在未登陆时，先获取QRCode图片内容。
并保持pollLogin操作，如果出现QRCode过期响应，则重新获取新的QRCode图片内容。
也就是wxagent未登陆状态，一直保持有效的QRCode图片内容。

关于收消息机制，还是需要wxagent收消息，再广播出来，如果没有程序接收，消息丢失。

wxagent提供的方法：
islogined: sync方法,
getqrpic: sync方法，
refresh: sync方法，
logout: sync方法，
getinitdata: sync方法，
getcontact: sync方法，
;hasmessage: sync方法，
;getmessage: async方法，只读取消息事件。
;readmessage: async方法，设置 消息已读标志，类似客户端上的点击新消息。
dumpinfo: sync方法，
sendmessage: sync方法，
geturl: async方法，


wxagent提供的事件信号：
logined
logouted
newmessage


lwwx.py 负责wx应用协议，消息解析，消息转发，需要一个UI，显示登陆二维码(可临时使用，完成销毁)。
wx2tox.py 负责wx消息与tox好友之间转发。
wxprotocol.py 从代理中抽取出来的部分，可与wxagent.py的大循环无关，随时调用的方法
有可能wxagent.py能更精简一些，而在该处做到更丰富的功能。




