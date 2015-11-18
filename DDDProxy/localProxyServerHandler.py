#!/usr/bin/env python
# -*- coding: utf-8 -*-
from DDDProxy.socetMessageParser import httpMessageParser
from DDDProxy.domainAnalysis import analysis, domainAnalysisType
from DDDProxy.localServerRemoteConnectManger import localSymmetryConnect,\
	localServerRemoteConnectManger
import json
from DDDProxy.hostParser import parserUrlAddrPort, getDomainName
from os.path import dirname
from DDDProxy.settingConfig import settingConfig
from DDDProxy import domainConfig
from DDDProxy.mime import get_mime_type


class localConnectHandler(localSymmetryConnect):
	def __init__(self, *args, **kwargs):
		localSymmetryConnect.__init__(self, *args, **kwargs)
		self.mode = ""
		self.connectHost = ""

		self.preConnectRecvCache = ""

		self.httpMessageParse = httpMessageParser()
		
	def onRecv(self, data):

		self.preConnectRecvCache += data
		if self.mode == "proxy":
			if self.serverAuthPass and self.preConnectRecvCache:

				if self.connectHost:
					analysis.incrementData(self.address[0], domainAnalysisType.incoming, self.connectHost, len(self.recvCache))
					
				self.sendDataToSymmetryConnect(self.preConnectRecvCache)
				self.preConnectRecvCache = ""
			return
		if self.httpMessageParse.appendData(data):
			method = self.httpMessageParse.method()
			path = self.httpMessageParse.path()
			self.connectName = self.filenoStr() + "	" + method + "	" + path
			if not path.startswith("http://") and method in ["GET", "POST"]:
				path = path.split("?")
				self.onHTTP(self.httpMessageParse.headers,
						method,
						path[0],
						path[1] if len(path) > 1 else "",
						self.httpMessageParse.getBody() if method == "POST" else "")
				self.mode = "http"
			else:
				
				self.mode = "proxy"
				
				connect = localServerRemoteConnectManger.getConnect()
				
				if path.find("status.dddproxy.com")>0:
					try:
						connect = None
						jsonMessage = self.messageParse.getBody()
						jsonBody = json.loads(jsonMessage)
						connectList = localServerRemoteConnectManger.getConnectHost(jsonBody["host"],jsonBody["port"])
						if connectList:
							for _,v in connectList.items():
								connect = v
					except:
						pass
				
				if connect:
					connect.addLocalRealConnect(self)
				else:
					self.close()
				
				self.connectHost = parserUrlAddrPort("https://" + path if method == "CONNECT" else path)[0]
				analysis.incrementData(self.address[0], domainAnalysisType.connect, self.connectHost, 1)
		else:
			pass
# 	def onRemoteConnectRecv(self,connect,data):
# 		self.send(data)
	def onServerAuthPass(self):
		localSymmetryConnect.onServerAuthPass(self)
		"""
		@type connect: remoteServerConnectLocalHander
		"""
		self.connectName = self.symmetryConnectManager.filenoStr() + "	<	" + self.connectName
		self.onRecv("");
		
	def onSend(self, data):
		if self.connectHost:
			analysis.incrementData(self.address[0], domainAnalysisType.outgoing, self.connectHost, len(data))
		if self.mode == "http" and not self.requestSend():
			if self.messageParse.connection() != "keep-alive":
				self.close()
			else:
				self.messageParse.clear()
	
	
	def onHTTP(self, header, method, path, query, post):
# 		log.log(1,self,header,method,path,query,post)
		if method == "POST":
			postJson = json.loads(post)
			opt = postJson["opt"]
			respons = {}

			if(opt == "status"):
				respons = self.server.dumpConnects()
			elif(opt == "serverList"):
				respons["pac"] = "http://" + self.messageParse.getHeader("host") + "/pac"
				respons["list"] = settingConfig.setting(settingConfig.remoteServerList)
			elif opt == "setServerList":
				settingConfig.setting(settingConfig.remoteServerList, postJson["data"])
				respons["status"] = "ok"
# 			elif opt == "testRemoteProxy":
# 				respons["status"] = ""
			elif opt == "domainList":
				
				if "action" in postJson:
					action = postJson["action"]
					domain = postJson["domain"]
					respons={"status":"ok"}
					if action == "delete":
						domainConfig.config.removeDomain(domain)
					elif action == "open":
						domainConfig.config.openDomain(domain)
					elif action == "close":
						domainConfig.config.closeDomain(domain)
					else:
						respons={"status":"no found action"}
				else:
					respons["domainList"] = domainConfig.config.getDomainListWithAnalysis()
			elif opt == "analysisData":
				respons["analysisData"] = analysis.getAnalysisData(
																selectDomain=postJson["domain"],
																startTime=postJson["startTime"],
																todayStartTime=postJson["todayStartTime"]
																)
			elif opt == "addDomain":
				url = postJson["url"]
				host = parserUrlAddrPort(url)[0]
				if host:
					host = getDomainName(host)
				else:
					host = url if getDomainName(url) else ""
				respons["status"] = "ok" if domainConfig.config.addDomain(host) else "error"
			self.reseponse(respons,connection=self.messageParse.connection())
		elif path == "/pac":
			content = self.getFileContent(dirname(__file__) + "/template/pac.js")
			domainList = domainConfig.config.getDomainOpenedList()
			domainListJs = ""
			for domain in domainList:
				domainListJs += "A(\"" + domain + "\")||"
			content = content.replace("{{domainList}}", domainListJs)
			content = content.replace("{{proxy_ddr}}", self.messageParse.getHeader("host"))
			self.reseponse(content,connection=self.messageParse.connection())
		else:
			if path == "/":
				path = "/index.html"
			content = self.getFileContent(dirname(__file__) + "/template" +path)
			if content:
				
				self.reseponse(content,ContentType=get_mime_type(path),connection=self.messageParse.connection())
			else:
				self.reseponse("\"" + path + "\" not found", code=404,connection=self.messageParse.connection())
		

