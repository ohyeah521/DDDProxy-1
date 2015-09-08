#!/usr/bin/env python
# -*- coding: utf-8 -*-
from DDDProxy.server import ServerHandler, baseServer, DDDProxySocketMessage
import DDDProxyConfig
from DDDProxy.socetMessageParser import socetMessageParser
from DDDProxy import hostParser, domainConfig
import re
import socket
import sys
import traceback
import ssl
import time
import math
import struct
import hashlib
import thread
import threading
from DDDProxy.domainConfig import setting, settingConfig
from DDDProxyConfig import mainThreadPool



class proxyServerHandler(ServerHandler):  
	def __init__(self, conn, addr, threadid):
		super(proxyServerHandler, self).__init__(conn, addr, threadid)
		self.source = conn
# 		self.source.settimeout(sendPack.timeout);
		self.method = ""
		self.threadid = threadid
		self.remoteSocket = None
		self.httpMessage = ""
		self.blockHost = DDDProxyConfig.blockHost
		self.hostPort = None
		self.remoteServer = ""
		self.dataCountSend = 0
		self.dataCountRecv = 0
	def info(self):
		return "%s	%s" % (ServerHandler.info(self), self.httpMessage)
	def domainAnalysisAddData(self,dataType,length):
		if not self.hostPort:
			return False
		domainConfig.analysis.incrementData(addr=self.addr, dataType=dataType, hostPort=self.hostPort, message=self.httpMessage, length=length)
		return True
	def sourceToServer(self):
		baseServer.log(1, self.threadid, "}}}}", "<")
		threading.currentThread().name = "worker%s-%s-send"%(self.threadid,self.addr)
		try:
			socetParser = socetMessageParser()
			count = 0
			while self.source != None:
				tmp = self.source.recv(DDDProxyConfig.cacheSize)
				if not tmp:
					break
				baseServer.log(1, "}}}}", tmp)
				length = len(tmp)
				self.dataCountSend += length;
				count += length;
				DDDProxySocketMessage.send(self.remoteSocket, tmp)
				
				#以下数据是为了时统计用
				if socetParser is not None:
					socetParser.putMessage(tmp)
					if socetParser.messageStatus():
						self.httpMessage = socetParser.httpMessage()
						host, port = hostParser.parserUrlAddrPort(self.httpMessage[1] if self.httpMessage[0] != "CONNECT" else "https://" + self.httpMessage[1])
						threading.currentThread().name = "worker%s-%s-%s:%d-send"%(self.threadid,self.addr,host,port)
						self.hostPort = (host, port)
						
						
						#代理host黑名单
						ipAddr = re.match("(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", host)
						foundIp = False
						if ipAddr:
							ipAddr = ipAddr.groups()
							mathIp = "%s.%s.%s" % (ipAddr[0], ipAddr[1], ipAddr[2]);
							for i in self.blockHost:
								if i.startswith(mathIp):
									foundIp = True
									break
						if foundIp or host in self.blockHost:
							baseServer.log(2, self.threadid, "block", host)
							break
						
						baseServer.log(2, self.addr, self.httpMessage)
						self.domainAnalysisAddData("connect", 1)
						socetParser = None
		
				if self.domainAnalysisAddData("incoming", count):
					count = 0
				self.markActive()
		except socket.timeout:
			pass
		except:
			baseServer.log(3, self.threadid, "}}}} error!")
# 		sendPack.end(self.remoteSocket)
		threading.currentThread().name = "worker%s-IDLE-send"%(self.threadid)
		baseServer.log(1, self.threadid, "}}}}", ">")
		self.close()
		
	def serverToSource(self):
		threading.currentThread().name = "worker%s-%s-recv"%(self.threadid,self.addr)
		baseServer.log(1, self.threadid, "-<")
		try:
			count = 0
			for data in DDDProxySocketMessage.recv(self.remoteSocket):
				self.source.send(data)
				self.markActive()
				length = len(data)
				self.dataCountRecv += length
				count += length
				if self.domainAnalysisAddData("outgoing", count):
					count = 0
		except:
			pass
		threading.currentThread().name = "worker%s-IDLE-recv"%(self.threadid)
		baseServer.log(1, self.threadid, "->")
		self.close()
		
	def connRemoteProxyServer(self,host,port,auth):
		self.remoteServer = host
		DDDProxyConfig.fetchRemoteCert(host, port)
		
		self.remoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.remoteSocket = ssl.wrap_socket(self.remoteSocket, ca_certs=DDDProxyConfig.SSLLocalCertPath(host,port),
										 cert_reqs=ssl.CERT_REQUIRED)		
		self.remoteSocket.connect((host,port))
		randomNum = math.floor(time.time())
		self.remoteSocket.send(struct.pack("i", randomNum))
		checkA = hashlib.md5("%s%d" % (auth, randomNum)).hexdigest()
		self.remoteSocket.send(checkA)
		baseServer.log(1, self.threadid, checkA, randomNum)

	def close(self):
		try:
			if self.source:
				self.source.shutdown(0)
		except:
			pass
		self.source = None
		try:
			if self.remoteSocket:
				DDDProxySocketMessage.end(self.remoteSocket)
		except:
			pass
		try:
			if self.remoteSocket:
				self.remoteSocket.shutdown(0)
		except:
			pass
		self.remoteSocket = None
	def AgreeConnIp(self, ipAddr=''):
		if ipAddr.startswith("127.0.0.")  or ipAddr.startswith("10.0.") or ipAddr.startswith("192.168."):
			return True;
		return False;
	def run(self):
		if not self.AgreeConnIp(self.addr):
			baseServer.log(2, self.threadid, "not agree ip %s connect!" % (self.addr))
			return;

		baseServer.log(1, self.threadid, "..... threadid start")
		host,port,auth = setting[settingConfig.remoteServerKey]
		self.connRemoteProxyServer(host,port,auth)
		mark = "[%s,%s]" % (self.addr,self.threadid)
		DDDProxySocketMessage.sendOne(self.remoteSocket,mark )
		baseServer.log(1, self.threadid, "threadid mark")
		
		mainThreadPool.callInThread(self.sourceToServer)
# 		thread.start_new_thread(self.sourceToServer, tuple())
		
		self.serverToSource()
		baseServer.log(1, self.threadid, "!!!!! threadid end")
