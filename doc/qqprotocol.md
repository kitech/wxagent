# w.qq协议整理

web QQ现在只有文字消息功能了。

接收图片消息与接收文件功能已挂，而且像是官方停止了相应服务。

web QQ端无法发送讨论组消息，只能接收。

2015-09-26  web QQ 变化，1、恢复了接收图片功能。2、官方去掉了密码登陆方式，只保留了二维码登陆方式。

2015-09-30  web QQ 像强制禁止密码登陆方式，总是返回“登录失败，请稍后再试。”

### 登陆

w.qq与桌面版本qq不能同时登陆。是按照设备来区分的，并不是真正的允许一个产品线登陆一个。


### 消息

w.qq的假多点登陆，在执行channel/poll2时，哪个是最近一次poll的，哪个能收到消息，否则另外一个会收到消息。

w.qq与手机qq能够保证都收到消息，但是手机上发送的消息不会再同步到另一终端上，虽然对方能够收到。

##### 事件类型，poll_type

* message
* group_message
* discu_message  (这是想要省一个字符，并不是我拼错误，shit)
* sess_message
* kick_message
* buddies_status_change
* input_notify
* file_message
* tips

###### 消息类型，msg_type

*
*
* 

##### 被迫下载
您的帐号在另一地点登录，您已被迫下线。如有疑问，请登录 safe.qq.com 了解更多。

    {"retcode":0,"result":[{"poll_type":"kick_message","value":{"msg_id":53125,"from_uin":10000,"to_uin":1449732709,"msg_id2":53126,"msg_type":48,"reply_ip":0,"show_reason":1,"reason":"\u60A8\u7684\u5E10\u53F7\u5728\u53E6\u4E00\u5730\u70B9\u767B\u5F55\uFF0C\u60A8\u5DF2\u88AB\u8FEB\u4E0B\u7EBF\u3002\u5982\u6709\u7591\u95EE\uFF0C\u8BF7\u767B\u5F55 safe.qq.com \u4E86\u89E3\u66F4\u591A\u3002"}}]}



### 参考：

https://github.com/xhan/qqbot/blob/master/protocol.md
https://github.com/zeruniverse/GnomeQQ/blob/master/PROTOCOL.md

