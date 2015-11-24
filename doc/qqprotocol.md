# w.qq协议整理

web QQ现在只有文字消息功能了。

接收图片消息与接收文件功能已挂，而且像是官方停止了相应服务。

web QQ端无法发送讨论组消息，只能接收。

2015-09-26  web QQ 变化，1、恢复了接收图片功能。2、官方去掉了密码登陆方式，只保留了二维码登陆方式。

2015-09-30  web QQ 像强制禁止密码登陆方式，总是返回“登录失败，请稍后再试。”

### 登陆

w.qq与桌面版本qq不能同时登陆。是按照设备来区分的，并不是真正的允许一个产品线登陆一个。

#### 二维码方式，获取二维码
GET
https://ssl.ptlogin2.qq.com/ptqrshow?appid=501004106&e=0&l=M&s=5&d=72&v=4&t=0.704464654205367

#### poll二维码登陆状态

是个是长poll还是定时方式呢？webqq实现方式好像调用很频繁？

Web QQ渣竟然使用的是定时轮循的方式，非长轮循，这么渣，很可能以后还会改, 

GET
https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1&login2qq=1&aid=501004106&u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1%26webqq_type%3D10&ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=0-2-234799&mibao_css=m_webqq&t=1&g=1&js_type=0&js_ver=10135&login_sig=&pt_randsalt=0

返回值：

ptuiCB('66','0','','0','二维码未失效。(668993644)', '');

ptuiCB('65','0','','0','二维码已失效。(687867386)', '');

ptuiCB('67','0','','0','二维码认证中。(1476407059)', '');

ptuiCB('0','0','http://ptlogin4.web2.qq.com/check_sig?pttype=1&uin=1449732709&service=ptqrlogin&nodirect=0&ptsigx=f8e9bead7b555c24827306627b025455c049216faeb9b620db93d01dfb55f8695eb3b2bd03866e5ba5bc576159da655296977b9d3cfe42a0a61325abd93c18e4&s_url=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1&f_url=&ptlang=2052&ptredirect=100&aid=501004106&daid=164&j_later=0&low_login_hour=0&regmaster=0&pt_login_type=3&pt_aid=0&pt_aaid=16&pt_light=0&pt_3rd_aid=0','0','登录成功！', 'abcyatsen1');


登陆成功后，获取cookie: ptwebqq

登陆成功后，获取内容项: check\_sig\_url

其他：

qrcode失效时间，大概120秒，2分钟。


### 消息

w.qq的假多点登陆，在执行channel/poll2时，哪个是最近一次poll的，哪个能收到消息，否则另外一个会收到消息。

w.qq与手机qq能够保证都收到消息，但是手机上发送的消息不会再同步到另一终端上，虽然对方能够收到。

##### 事件类型，poll_type

* message
* group_message
* discu_message  (这是想要省一个字符，并不是我拼错误，shit)
* sess_message
* kick_message
* buddies\_status_change
* input_notify
* file_message
* tips

###### 消息类型，msg_type

*
*
* 

##### 设置参数：
enable_https: 1|0，默认0不开启https。

不过也还是部分API支持https。好像是在d.web2.qq.com域名上的可以。

##### 返回错误号汇总
{"retcode":100101}  这是二进制？
{"retcode":100006,"errmsg":""}
{"retcode":100003}
{"retcode":100001}  群编号有问题
{"retcode":100000}
{"retcode":122,"errmsg":"wrong web client3"}
{"retcode":121,"errmsg":""}  ReLinkFailure
{"retcode":120,"errmsg":""}  ReLinkFailure
{"retcode":116}
{"retcode":114}
{"retcode":110}  已经下线
{"retcode":109}  已经下线
{"retcode":108,"errmsg":""}
{"retcode":103,"errmsg":""}  掉线
{"retcode":102,"errmsg":""}  正常连接、没有消息。
{"retcode":101,"errmsg":""}
{"retcode":100,"errmsg":""}  NotReLogin
{"retcode":60,"errmsg":""}
{"retcode":50,"errmsg":""}
{"retcode":0}

##### long poll

poll超时为60秒，但有时为120秒。
使用telnet d.web2.qq.com 443，1分钟被服务器关闭。

POST
https://d.web2.qq.com/channel/poll2?


返回值：

{"retcode":102,"errmsg":""}  poll 正常超时，再次poll即可。

{"retcode":103,"t":""} 登录异常，可能只能刷新重新登陆了

{"retcode":121,"t":""}  掉线




##### 被迫下载
您的帐号在另一地点登录，您已被迫下线。如有疑问，请登录 safe.qq.com 了解更多。

这是poll2的返回值的一种情况。

    {"retcode":0,"result":[{"poll_type":"kick_message","value":{"msg_id":53125,"from_uin":10000,"to_uin":1449732709,"msg_id2":53126,"msg_type":48,"reply_ip":0,"show_reason":1,"reason":"\u60A8\u7684\u5E10\u53F7\u5728\u53E6\u4E00\u5730\u70B9\u767B\u5F55\uFF0C\u60A8\u5DF2\u88AB\u8FEB\u4E0B\u7EBF\u3002\u5982\u6709\u7591\u95EE\uFF0C\u8BF7\u767B\u5F55 safe.qq.com \u4E86\u89E3\u66F4\u591A\u3002"}}]}


##### 定时下线

web QQ在2-3天会自动cookie失效一次，所以默认无法实现永久在线。

参考这个讨论，也许可以定时刷新一下现有的登陆cookie，实现永久在线的功能。

https://github.com/sjdy521/Mojo-Webqq/issues/7#issuecomment-149608429


##### 发送好友消息
POST https://d.web2.qq.com/channel/send_buddy_msg2?

返回值：
{"retcode":0,"result":"ok"}

##### 发送群消息
POST https://d.web2.qq.com/channel/send_qun_msg2?

返回值：
{"retcode":0,"result":"ok"}
116, ???

##### 发送讨论组消
POST https://d.web2.qq.com/channel/send_discu_msg2?

返回值：
{"retcode":0,"result":"ok"}


##### 发送临时会话消息
POST https://d.web2.qq.com/channel/send_sess_msg2?

返回值：
{"retcode":0,"result":"ok"}


##### 获取图片

GET
http://w.qq.com/d/channel/get_offpic2?file_path=%2F4c7d819b-4235-466c-9915-c7e0dcd0cceb&f_uin=2300061779&clientid=53999199&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133392e372e31363400005c3f00000006026e0400bf2533b56d0000000a4071353561464b52766e6d00000028eb50c56972b2f7fc3830f65bca9ea3c2b9aba4f6343346cb78e00acc3328f497d35f653d3cf607f4

错误信息：

200 OK, {"retcode":103,"errmsg":""}

在正确获取数据时，这个请求应该会http 302响应，

GET
http://103.7.29.36:80/?ver=2173&rkey=edea46b6f7f03c43b367815b383e85bc276fe87305ceaf738f2996b182f24f8c6545820a1b9ad7420836810b746567e78995c6af1707a4864cdd4d0537f2f447

注：这个图片服务器太烂，一般要10-20秒响应，还有可能达到45秒。

##### 同意并获取文件

GET
http://d.web2.qq.com/channel/get_file2?lcid=20868&guid=qt.png&to=2300061779&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133392e372e31363400005c3f00000006026e0400bf2533b56d0000000a4071353561464b52766e6d000000284b286bf4fcbdbba4b1cfe3734176d3c2f449f427f3524b3a4d5c4f79d3dd067f4e4410349ae11544&count=1&time=1444491764548&clientid=53999199

错误信息：

200 OK, {"retcode":102,"errmsg":""}  接收文件"qt.png"超时，文件传输失败。

在正确获取数据时，这个请求应该会302响应，

GET
http://file1.web.qq.com/v2/3040028095/2300061779/20868/1075/33946/0/0/1/f/16970/qt.png?psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133392e372e31363400005c3f00000006026e0400bf2533b56d0000000a4071353561464b52766e6d000000284b286bf4fcbdbba4b1cfe3734176d3c2f449f427f3524b3a4d5c4f79d3dd067f4e4410349ae11544

注，如果手机端登陆了该账号，则web 端QQ不会收到接收文件请求。

即使手机没登陆，这个文件接口也非常不稳定，经常响应超时。

是因为这变态的把file1.web.qq.com域名指向了1.1.1.1。

##### 拒绝接收文件

http://d.web2.qq.com/channel/refuse_file2?to=2300061779&lcid=20868&psessionid=8368046764001d636f6e6e7365727665725f77656271714031302e3133392e372e31363400005c3f00000006026e0400bf2533b56d0000000a4071353561464b52766e6d000000284b286bf4fcbdbba4b1cfe3734176d3c2f449f427f3524b3a4d5c4f79d3dd067f4e4410349ae11544&clientid=53999199&t=1444491833302

{"retcode":0,"result":"ok"}


##### 获取好友列表

POST
http://s.web2.qq.com/api/get_user_friends2

返回值：
{"retcode":6}  错误，账号被锁定了?可是重新登陆再调用也没有问题啊？
别人是在自动加好友时出现的问题，超过15个之后就失败了,返回{ retcode :6}
这个错误很少见啊，找不到是什么原因。

正确:
{"retcode":0,"result":{"friends":[{"flag":0,"uin":2318067912,"categories":0}],"marknames":[],"categories":[{"index":1,"sort":1,"name":"朋友"},{"index":2,"sort":2,"name":"家人"},{"index":3,"sort":3,"name":"同學"}],"vipinfo":[{"vip_level":0,"u":2318067912,"is_vip":0}],"info":[{"face":105,"flag":285213184,50"nick":"YAT-SEN","uin":2318067912}]}}


### 参考：

https://github.com/xhan/qqbot/blob/master/protocol.md

https://github.com/zeruniverse/GnomeQQ/blob/master/PROTOCOL.md

https://github.com/Yinzo/SmartQQBot

