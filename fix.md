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