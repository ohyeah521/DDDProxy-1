<h2>DDDProxy 3.1.0</h2>
私有安全的代理软件


3.X 更改了传输协议与2.x 远程服务不兼容

E-Mail：wdongxv@gmail.com

<h3>主要有以下功能或特点</h3>
*	异步I/O
* 多远程服务器支持(2015.8.8新增)
*	私有的代理软件
*	自动代理配置（原理见：https://en.wikipedia.org/wiki/Proxy_auto-config ）
*	对每个域名下的网站访问次数的统计
*	在一定时间内，每个客户端每小时分别访问哪些网站所用流量的统计
*	pac列表会以统计为标准，将访问次数较多的网站放到最前面来减少客户端的运算
*	远程服务器与本地服务器之间采用SSL加密
*	代理域名列表可备份到Google Drive

<h3>如何运行？</h3>
在远程服务器运行: 
<pre>python remoteServer.py -a [passWord]</pre>
本地服务器运行: 
<pre>python localServer.py</pre>
用浏览器打开：
<pre>http://127.0.0.1:8080/</pre>
这样你就会看到完整的帮助，以及所有的设置

<h3>当然，做为新的开源项目，还有很多事要做的：</h3>
*	pac文件还没有做缓存
*	现在作者是用supervisor来做开机启动，当然也是需要傻瓜一键安装无烦恼自启动功能的
