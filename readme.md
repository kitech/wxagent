
### 微信 && QQ登陆代理

实现微信 && QQ与其他开放IM协议的互通，并以后台运行方式实现消息的双向转发。

把weixin通过服务端引流出来，实现跨平台的易用的开放的IM客户端，减小原生实现的平台与其他诸多限制。

### 手动执行

    # 启动agent端
    git clone https://github.com/kitech/wxagent.git
    cd wxagent
    sudo cp -v archlinux/txagent.conf /etc/dbus-1/system.d/
    python3 -m wxagent.wxagent

    # 启动转发端，目前支持xmpp协议与toxcore协议
    cp -v wxagent/secfg.py.example wxagent/secfg.py
    vim wxagent/secfg.py
    python3 -m wxagent.wx2any
    

### Documentation
[Proposal想法](https://github.com/kitech/wxagent/blob/master/doc/proposal.md)

[Ubuntu安装](https://github.com/kitech/wxagent/blob/master/doc/build.md)

[ChangeLog](https://github.com/kitech/wxagent/blob/master/doc/changes.md)

[依赖需求包](https://github.com/kitech/wxagent/blob/master/requirements.txt)

