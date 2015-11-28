#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2015年11月18日

@author: dxw
'''
import struct
from DDDProxy.baseServer import sockConnect, socketBufferMaxLenght
import json
import hashlib
from DDDProxy import log



class symmetryConnect(sockConnect):
	"""
	@type remoteConnect: remoteServerConnect
	"""

	optCloseSymmetryConnect = -1

	optSymmetryPing = -2
	optSymmetryPingResponse = -3

	optCloseForceSymmetryConnect = -4

	
	def __init__(self,server):
		sockConnect.__init__(self, server)
		self.symmetryConnectId = 0
		self._symmetryConnectSendPendingCache = []
		self._requestRemove = False
		self.symmetryConnectManager = None
		self.waitSymmetryPingResponse = False
		
		self._symmetryPingLenght = 0
		
#--------


	def pauseSendAndRecv(self):
		return self.waitSymmetryPingResponse

	def onRecv(self, data):
		sockConnect.onRecv(self, data)
		self.sendDataToSymmetryConnect(data)
		
		self._symmetryPingLenght += len(data)
		if(self._symmetryPingLenght>1024*100):
			self._symmetryPingLenght = 0
			self.waitSymmetryPingResponse = True
			self.sendOptToSymmetryConnect(symmetryConnect.optSymmetryPing)
		
	def onClose(self):
		self.sendOptToSymmetryConnect(symmetryConnect.optCloseSymmetryConnect)
		self._requestRemove = True
	
#--------
	def onSymmetryConnectServerClose(self):
		self.close()
	def onSymmetryConnectData(self,data):
		pass
	def onSymmetryConnectOpt(self,opt):
		if opt == symmetryConnect.optCloseSymmetryConnect:
			self.close()
		elif opt == symmetryConnect.optSymmetryPing:
			self.sendOptToSymmetryConnect(symmetryConnect.optSymmetryPingResponse)
		elif opt == symmetryConnect.optSymmetryPingResponse:
			self.waitSymmetryPingResponse = False
		elif opt == symmetryConnect.optCloseForceSymmetryConnect:
			self.shutdown()
			log.log(2,self,"<<< optCloseForceSymmetryConnect, close")
		
	def sendOptToSymmetryConnect(self,opt):
		if self._requestRemove:
			return
		optData = symmetryConnectServerHandler.optChunk(self.symmetryConnectId, opt)
		if type(optData) != str:
			log.log(3,"data not is str")
		self._symmetryConnectSendPendingCache.append(optData)
	def sendDataToSymmetryConnect(self,data):
		if self._requestRemove:
			return
		
			
		if type(data) != str:
			log.log(3,"data not is str")
		for part in symmetryConnectServerHandler.dataChunk(self.symmetryConnectId, data):
			if type(part) != str:
				log.log(3,"part not is str")
			self._symmetryConnectSendPendingCache.append(part)

#--------------- for symmetryConnectServerHandler
	def symmetryConnectSendPending(self):
		return len(self._symmetryConnectSendPendingCache)
	def getSymmetryConnectSendData(self):
		return self._symmetryConnectSendPendingCache.pop(0)
	def requestRemove(self):
		return self._requestRemove
	
class symmetryConnectServerHandler(sockConnect):

	serverToServerJsonMessageConnectId = -1
	
	def __init__(self, server, *args, **kwargs):
		sockConnect.__init__(self, server, *args, **kwargs)
		self.symmetryConnectList = {}
		self._socketMessageBuffer = ""
		self.symmetryConnectIdLoop = 0
		self.symmetryConnectCloseList = []
	
	def getSendPending(self):
		if sockConnect.getSendPending(self) < socketBufferMaxLenght:
			for symmetryConnectId,v in self.symmetryConnectList.items():
				if v.symmetryConnectSendPending():
					self.send(v.getSymmetryConnectSendData())
				elif v.requestRemove():
					self.sendOpt(symmetryConnectId, symmetryConnect.optCloseForceSymmetryConnect)
					self.symmetryConnectCloseList.append(symmetryConnectId)
					del self.symmetryConnectList[symmetryConnectId]
					
		return sockConnect.getSendPending(self)
	def onSend(self, data):
		sockConnect.onSend(self, data)
# 		print "<onSend  ------\n",data,"\n--------->"

# -------------  

	def onServerToServerMessage(self,serverMessage):
		pass

# -------------		
	def onClose(self):
		for _,connect in self.symmetryConnectList.items():
			connect.onSymmetryConnectServerClose()

	@staticmethod
	def optChunk(symmetryConnectId,opt):
		if opt >=0:
			raise Exception("opt must < 0")
		return struct.pack("i", symmetryConnectId)+struct.pack("h", opt) +"\n"

	@staticmethod
	def dataChunk(symmetryConnectId,data):
		l = len(data)
		if l > 32767:  #分块
			yield symmetryConnectServerHandler.dataChunk(symmetryConnectId, data[:32767])
			yield symmetryConnectServerHandler.dataChunk(symmetryConnectId, data[32767:])
		else:
			yield struct.pack("i", symmetryConnectId)+struct.pack("h", l) +data+"\n"
	
	
	_headSize = struct.calcsize("ih")
	def onRecv(self,data):
		sockConnect.onRecv(self, data)
		self._socketMessageBuffer += data
		while True:
			bufferLen = len(self._socketMessageBuffer)
			_headSize = symmetryConnectServerHandler._headSize
			if bufferLen >= _headSize:
				symmetryConnectId,dataSize = struct.unpack("ih",self._socketMessageBuffer[:_headSize])
				if dataSize>=0:
					endIndex = dataSize+_headSize
					if bufferLen > endIndex:
						dataMessage = self._socketMessageBuffer[_headSize:endIndex]
						self._socketMessageBuffer = self._socketMessageBuffer[endIndex+1:]
						self._onRecvData(symmetryConnectId, dataMessage)
					else:
						break
				else:
					self._socketMessageBuffer = self._socketMessageBuffer[_headSize+1:]
					self._onRecvOpt(symmetryConnectId, dataSize)
			else:
				break
	
	def _onRecvData(self,symmetryConnectId,data):
# 		print "<_onRecvData ",symmetryConnectId," ----------\n",data,"\n------------->"
		if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
			try:
				serverMessage = json.loads(data)
				self.onServerToServerMessage(serverMessage)
			except:
				pass
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectData(data)

	def _onRecvOpt(self,symmetryConnectId,opt):
# 		print "<_onRecvOpt ",symmetryConnectId," ------",opt,"--------->"
		if symmetryConnectId == symmetryConnectServerHandler.serverToServerJsonMessageConnectId:
			pass
		else:
			connect = self.getSymmetryConnect(symmetryConnectId)
			if connect:
				connect.onSymmetryConnectOpt(opt)
	def getSymmetryConnect(self,symmetryConnectId):
		if not symmetryConnectId in self.symmetryConnectCloseList:
			return self.symmetryConnectList[symmetryConnectId] if symmetryConnectId in self.symmetryConnectList else None
		return None
# -----------
	def sendOpt(self,symmetryConnectId,opt):
		self.send(self.optChunk(symmetryConnectId, opt))
	def sendData(self,symmetryConnectId,data):
		for d in self.dataChunk(symmetryConnectId, data):
			self.send(d)
	def addSymmetryConnect(self,connect,connectId):
		connect.symmetryConnectId = connectId
		connect.symmetryConnectManager = self
		self.symmetryConnectList[connectId] = connect
		
	def makeSymmetryConnectId(self):
		self.symmetryConnectIdLoop += 1
		return self.symmetryConnectIdLoop

	def authMake(self,auth,timenum):
		return {
			"time":timenum,
			"password":hashlib.md5("%s_%d" % (auth, timenum)).hexdigest()
			}
