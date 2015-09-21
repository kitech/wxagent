2015.9.21

-  让图片显示在wxaui，保存发送过来的图片 wxagent.py line 383
  
  > ​
  > 
  > ``` 
  >  elif url.startswith('http://emoji.qpic.cn/wx_emoji'):        
  >         qDebug('get the picture url that you saved : '+str(len(hcc)))
  >         self.msgimage = hcc
  >         self.createMsgImage(hcc)
  > ```
  > 
  > line 393 add createMsgImage function
  > 
  > ​
  > 
  > ``` 
  >   def createMsgImage(self, hcc):  
  >     randnum = str(int(time.time()))
  >     self.msgimagename = 'img/mgs_image'+randnum+'.json'
  >     fp = QFile(self.msgimagename)
  >     fp.open(QIODevice.ReadWrite | QIODevice.Truncate)
  >     fp.write(hcc)
  >     fp.close()
  > ```
  > 
  > ​
  
- lwwx.py 解析content的图片 line 123
  
  > ​
  > 
  > ``` 
  >  msgemoji = re.search(r'http://emoji.qpic.cn/\s+', content)      
  >       if msgemoji :
  >             emoji = msgemoji.group()
  >             msgimgurl = re.sub(r'\"','',emoji)
  >             qDebug(msgimgurl)
  >             reply = self.sysiface.call('getmsgimage', msgimgurl)
  >             reply = self.sysiface.call('getmessageimage')
  >             rr = QDBusReply(reply)
  >             if not rr.isValid():
  >                 qDebug(str(rr.error().message()))
  >                 qDebug(str(rr.error().name()))
  >             qDebug(str(len(rr.value())) + ',' + str(type(rr.value())))
  >             self.getImage(rr.value())
  > ```
  > 
  > ​
  
  
  > line 209 add getImage function 
  > 
  > ​
  > 
  > ``` 
  > def getImage(self, msgimagename):
  > qDebug(msgimagename)
  > pix = QPixmap(msgimagename)
  > npix = pix.scaled(180,180)
  > self.uiw.label.setPixmap(npix)
  > 
  > return
  > ```
  > 
  > ​
  
  ​
  
  ​







### 扫描二维码重定向问题

- 扫描二维码之后，发现重定向地址 redirect_url 一个是在wx.qq.com,一个是在wx2.qq.com,直接就定向到了wx2.qq.com的做法不符合我本地测试情况
  
  > 修改了wxagent.py 添加了66-67 line 
  > 
  > ​
  > 
  > ``` 
  > 	self.urlStart = ''     
  >     self.webpushUrlStart = '' 
  > ```
  
- 203-208 line
  
  > ``` 
  >       if nsurl.find('wx.qq.com') > 0 :
  >           self.urlStart = 'https://wx.qq.com'
  >           self.webpushUrlStart = 'https://webpush.weixin.qq.com'
  >       else :
  >       	  self.urlStart = 'https://wx2.qq.com'
  > ```


- getCookie修改 696 line
  
  ​
  
  > ``` 
  >     domain = self.urlStart
  > ```
  > 
  > ​

### 获取不到pass_tickets

- getBaseInfo的时候拿不到pass_tickets 436
  
  > ​
  > 
  > ``` 
  > nsurl = self.urlStart+'/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=en_US&pass_ticket=%s' % \            
  >             (self.nowTime() - 3600 * 24 * 30, self.wxPassTicket)
  > ```
  > 
  > ​