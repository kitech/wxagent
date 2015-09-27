网页微信客户端封包大全
-----------------------

2015-09-21  微信故障，网页版API拿不到Uin，不知道是永久的还是暂时的？
看来是更新客户端了，Uin一直是0了，不变了。

> http://www.langyeweb.com/Program/70.html

网页版微信功能只有一个：聊天。根据 ***Copyright (C) 狼夜***我这两天研究发现，
网页版微信可以脱离手机微信，也就是手机微信退出、手机关机，都不影响网页端微信的
在线以及聊天，关于如何使用加好友、朋友圈、摇一摇功能，我有个思路就是抓手机封包 
@Icenowy 在微博上有抓手机包的计划 然后使用，不过这个想法因为时间问题没有去实践，
希望大家能研究出来的话在本页面留一个链接，十分感谢！

以下是Post/Get的封包大全，如果能看懂这个，基本上你就可以做出来了。


## 获取uuid

https://login.weixin.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_=1388994062250

这一步中，需要从cookie获取这三个值，wxuin, wxsid, webwx\_data\_ticket

需要在response中获取这一个值，pass\_ticket

## 获取二维码

https://login.weixin.qq.com/qrcode/{$uuid}?t=webwx


## 等待扫描Get

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=1&_=1388975894359

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=1&_=1388975873359

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=1&_=1388975883859


### 扫描了（但还没有确认）-返回

window.code=201;

### 扫描了并确认-返回

window.code=200;

### 未扫描返回空

window.code=408

###  等待扫描超时，qrpic失效 -返回

window.code=400

这时需要从头开始，重新执行流程。

## 扫描之后-第一次请求成功

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatreport?type=1&r=1388975895453

{"BaseRequest":{"Uin":0,"Sid":0},"Count":1,"List":[{"Type":1,"Text":"/cgi-bin/mmwebwx-bin/login, First Request Success, uuid: 454d958c7f6243"}]}


## 扫描之后-第二次请求开始

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatreport?type=1&r=1388975895453

{"BaseRequest":{"Uin":0,"Sid":0},"Count":1,"List":[{"Type":1,"Text":"/cgi-bin/mmwebwx-bin/login, Second Request Start, uuid: 454d958c7f6243"}]}


## 等待确认Get

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=0&_=1388975895453

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=0&_=1388975900953

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=0&_=1388975906453

https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?uuid=454d958c7f6243&tip=0&_=1388975911953


### 手机确认-返回

window.code=200;

window.redirect_uri="https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=03f725a8039d418ab79c69b6ffbd771b&lang=zh_CN&scan=1388975896";


### 未确认返回空


## get 登陆获取Cookie

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=03f725a8039d418ab79c69b6ffbd771b&lang=zh_CN&scan=1388975896&fun=new


## WX2新协议
https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=b03aa3dfbe8d4130981ddf771137ae7b&lang=zh_CN&scan=1419126125&fun=old


## 设置Cookie 返回一个状态


## post 第二次请求成功

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatreport?type=1&r=1388976086218

{"BaseRequest":{"Uin":0,"Sid":0},"Count":1,"List":[{"Type":1,"Text":"/cgi-bin/mmwebwx-bin/login, Second Request Success, uuid: 454d958c7f6243, time: 190765ms"}]}


## post 表示登陆成功-返回重要的数据SKey

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=1388976086484

DeviceID 是e + 随机数
> http://www.tanhao.me/talk/1466.html

{"BaseRequest":{"Uin":"750366800","Sid":"e75TXbI7TnKUevmI","Skey":"","DeviceID":"e519062714508114"}}


## post 应该是向服务器端提供的一次验证-返回SyncKey

> http://freezingsky.iteye.com/blog/2055502

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=e75TXbI7TnKUevmI&r=1388976086734

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI"},"SyncKey":{"Count":4,"List":[{"Key":1,"Val":620916854},{"Key":2,"Val":620917961},{"Key":3,"Val":620917948},{"Key":1000,"Val":1388967977}]},"rr":1388976086734}


## post 可能是获取当前会话列表

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?r=1388976086734

{}


## post 可能是在手机上显示的提示信息

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatusnotify?r=1388976086750

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI","Skey":"","DeviceID":"e519062714508114"},"Code":3,"FromUserName":"langyeie","ToUserName":"langyeie","ClientMsgId":"1388976086750"}


## get 获取头像图片

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?seq=1388335457&username=langyeie


## get 同理可以获取其他微信好友的头像

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?seq=620917759&username=wxid_xx3mtgeux5511


## post 更改什么状态？标记已读？

应该是获取wx群成员信息。在webwxinit正确返回后，逐个获取每个wx群的成员联系人信息。

参数：Count 最大50,如果一个群组人超过50,则需要分多次获取。

https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxbatchgetcontact?type=ex&r=1440473919872&lang=en_US&pass_ticket=kKWVrvi2aw98Z8sXfzwncDWxWZZQgVZERel61bswt0bLI5z3Xo3Vz8l5UmrLWOXq

{"BaseRequest":{"Uin":979270107,"Sid":"u/kOgmTvxB4z+JXa","Skey":"@crypt_3ea2fe08_3e4ced233d812cc841a3fab5b3f1ca8b"
,"DeviceID":"e636182931708129"},"Count":6,"List":[{"UserName":"@1502b925d9437c23efb37032f659df57","EncryChatRoomId"
:"@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"},{"UserName":"@f36e87e70ab243ad6c77286351dda159"
,"EncryChatRoomId":"@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"},{"UserName"
:"@59c5871ee15417771ce99dc6cd99727dfdd4e698aef8ff0ca36c333ff44c4202","EncryChatRoomId":"@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"
},{"UserName":"@904b8cc29872a83fb6bde6c4776b711a","EncryChatRoomId":"@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"
},{"UserName":"@da0af1a08aad98d3acd9a6a3164389b36c494d865900d39c50ef480d29cc8296","EncryChatRoomId":"
@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"},{"UserName":"@fffed55b50bb48f9f62d751bac389545be5bf40996ac493959e9404a1652617f"
,"EncryChatRoomId":"@@77d919fac8bb4cd3b4cb56f12b1512c0d3ac1b8884e97d558096ddb7b87aa2b9"}]}



## 聊天室头像

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetheadimg?seq=620917806&username=3445229833chatroom@


## get 监听会话

https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18308660551080269895_1388975862078&r=1388976091937&sid=e75TXbI7TnKUevmI&uin=750366800&deviceid=e519062714508114&synckey=1_620916854%7C2_620917963%7C3_620917948%7C11_1388976090%7C1000_1388967977&_=1388976091937

https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18308660551080269895_1388975862078&r=1388976119062&sid=e75TXbI7TnKUevmI&uin=750366800&deviceid=e519062714508114&synckey=1_620916854%7C2_620917963%7C3_620917948%7C11_1388976090%7C1000_1388967977&_=1388976119078

https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18308660551080269895_1388975862078&r=1388976173375&sid=e75TXbI7TnKUevmI&uin=750366800&deviceid=e519062714508114&synckey=1_620916854%7C2_620917963%7C3_620917948%7C11_1388976090%7C1000_1388967977&_=1388976173390

https://webpush.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?callback=jQuery18308660551080269895_1388975862078&r=1388976146265&sid=e75TXbI7TnKUevmI&uin=750366800&deviceid=e519062714508114&synckey=1_620916854%7C2_620917963%7C3_620917948%7C11_1388976090%7C1000_1388967977&_=1388976146265


### 正常返回结果

window.synccheck={retcode:"0",selector:"0"}


### 有消息返回结果

window.synccheck={retcode:"0",selector:"6"}


### 发送消息返回结果

window.synccheck={retcode:"0",selector:"2"}


### 朋友圈有动态

window.synccheck={retcode:"0",selector:"4"}


## 获取消息-post-设置Cookie

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=e75TXbI7TnKUevmI&r=1388977398062

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI"},"SyncKey":{"Count":5,"List":[{"Key":1,"Val":620916854},{"Key":2,"Val":620917978},{"Key":3,"Val":620917975},{"Key":201,"Val":1388977392},{"Key":1000,"Val":1388967977}]},"rr":1388977398062}

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=e75TXbI7TnKUevmI&r=1388977583250

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI"},"SyncKey":{"Count":5,"List":[{"Key":1,"Val":620916854},{"Key":2,"Val":620917980},{"Key":3,"Val":620917975},{"Key":201,"Val":1388977400},{"Key":1000,"Val":1388967977}]},"rr":1388977583250}

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=e75TXbI7TnKUevmI&r=1388977660750

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI"},"SyncKey":{"Count":5,"List":[{"Key":1,"Val":620916854},{"Key":2,"Val":620917982},{"Key":3,"Val":620917975},{"Key":201,"Val":1388977585},{"Key":1000,"Val":1388967977}]},"rr":1388977660750}

## post 发送消息

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?sid=e75TXbI7TnKUevmI&r=1388977830140

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI","Skey":"D6EBA5FA425CAE258F24E75CF51F2E1B4EEA9C5338BE456C","DeviceID":"e519062714508114"},"Msg":{"FromUserName":"langyeie","ToUserName":"pp80000","Type":1,"Content":"55","ClientMsgId":1388977830140,"LocalID":1388977830140}}

https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=e75TXbI7TnKUevmI&r=1388977830390

{"BaseRequest":{"Uin":750366800,"Sid":"e75TXbI7TnKUevmI"},"SyncKey":{"Count":5,"List":[{"Key":1,"Val":620916854},{"Key":2,"Val":620917986},{"Key":3,"Val":620917975},{"Key":201,"Val":1388977776},{"Key":1000,"Val":1388967977}]},"rr":1388977830390}


## get 有消息来，响铃

https://res.wx.qq.com/zh_CN/htmledition/swf/msg17ced3.mp3


## 获取消息中的图片

缩略图：
https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg?type=slave&MsgID={MsgID值}&skey=%40{skey值}
原图：
https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg?MsgID={MsgID值}&skey=%40{skey值}

另外， 如果在微信中收藏的图片地址为cdnurl：


'emoji fromusername = wxid_72ihdogv8ya621 tousername = wang1058056871 type=1 idbuffer=media:0_0 md5=63d404516886152038c15e22113d06c0 len = 19870 productid= androidmd5=63d404516886152038c15e22113d06c0 androidlen=19870 s60v3md5 = 63d404516886152038c15e22113d06c0 s60v3len=19870 s60v5md5 = 63d404516886152038c15e22113d06c0 s60v5len=19870 cdnurl = http://emoji.qpic.cn/wx_emoji/OlaTef8nbNwrx2yCBBaaictrcFZGbrDbEPFB96n3Rve8hjj0xCFpcyQ/ '

/cgi-bin/mmwebwx-bin/webwxgetvideo?type=flv&msgid={MsgID值}&skey={SKey值}

/cgi-bin/mmwebwx-bin/webwxgetvideo?fun=download&msgid={MsgID值}&skey={SKey值}


## 获取语音

GET
https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetvoice?msgid=6104830929818611751&skey=@crypt_3ea2fe08_7782b85e3ba92163e53c8712a8187c32

返回：

Content-Type:audio/mp3


## 获取文件
https://file2.wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetmedia?sender=@9430feec6b3e2f13b011fcf1968fceeef11f67a0fefe49da80e00383199cbfbd&mediaid=@crypt_736e9b43_13a6c54428ab1cb061e55a957428df3700b128f2fc3b9718888da4e50c1422fbf97dc9fa344ce35f23b8feb46ae3d48602788e9eb5e787c8473c74bf5802e7f511f0c33090ff4593a33aa3397b1c3b6042ef9f965b31a43b5a96c905de612ec6b2b2ba6b935433c2711eca9c6eaa4c948cb764461ca2fb6b902aa1d306130bff57d90e070f1c2414107649aa09e212d43cb1aa8a40c48a85cd8581882f48af19c4e08409ca383bdcfd2d7bd4b2b5a99e888b116b7e3c7722007f78a3d5ed56fd942f6c0ff8f3f097457d5fdbef8efd88&filename=sbt.jar&fromuser=979270107&pass_ticket=SFxRYgzBDZXnDHyeS78pMJ8pQoifrwoSM%252BINCvLRrddKWIHY4I6dDgPRXCyLQeGK&webwx_data_ticket=AQar6r1A65dHjs1mh6%2FQYyeW

这个url是可以不需要cookie，直接在客户端下载的。但是不知道是否有有效期。

weixin限制文件大小25M以内。

还有一种文件，消息类型同样为49，但是这种消息不包含MediaId，而是有Url字段，是一个普通HTML文档链接。

这种不再需要获取真实文件URL地址操作。这种类型消息，一般是订阅号推送的新闻文章。

