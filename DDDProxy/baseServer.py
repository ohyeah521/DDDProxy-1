# -*- coding: UTF-8 -*-
'''
Created on 2015年9月3日

@author: dxw
'''
import logging
import socket
import sys
import time
import traceback
import select
import signal
import ssl

debuglevel = 2

class sockConnect(object):
	"""
	@type sock: _socketobject
	"""
	
	_filenoLoop = 0
	
	def __init__(self,server):
		self.server = server
		self.info = {
					"startTime":time.time(),
					"send":0,
					"recv":0
					}
		self.sock = None
		self.address = (None,None)
		self.dataSendList = []
		sockConnect._filenoLoop+=1
		self._fileno = sockConnect._filenoLoop
		self.connectName = ""
		
		socket.setdefaulttimeout(10)
	def __str__(self, *args, **kwargs):
		return "["+str(self.fileno())+"]"+(self.connectName if self.connectName else  str(self.address))
	def connect(self,sock,address):
		"""
		@param address: 仅记录
		"""
		self.address = address
		self.sock = sock
		sock.setblocking(False)
		self.server.addSockConnect(self)
	def connectWithAddress(self,address):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			addr = (socket.gethostbyname(address[0]),address[1])
			s.connect(addr)
			s.setblocking(False)
			self.connect(s, address)
			return True
		except:
			baseServer.log(3,address)
			self.server.addCallback(self.onClose)
		return False
	def _setConnect(self,sock,address):
		"""
		@type sock: _socketobject
		"""
		self.sock = sock
		self.address = address
		self.onConnected()
	def fileno(self):
		return self._fileno
	def send(self,data):
		if data and len(data)>1024:
			self.dataSendList.append(data[:1024])
			self.send(data[1024:])
		else:
			self.dataSendList.append(data)
	def onConnected(self):
		pass
	def onRecv(self,data):
		self.info["recv"] += len(data)
		
	def onSend(self,data):
		self.info["send"] += len(data)
		l = self.sock.send(data)
	def onClose(self):
		pass
	def close(self):
		self.send(None)
class baseServer():
	def __init__(self,handler):
		self.handler = handler

		self.socketList = {}
		self.serverList = []

		self.callbackList = []
		
	def addCallback(self,cb, *args, **kwargs):
		self.callbackList.append((cb,0,args,kwargs))
		
	def addListen(self,port,host=""):
# 		self.server = bind_sockets(port=self.port, address=self.host) 
		
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
		server.bind((host, port))
		server.listen(1024)
		server.setblocking(0)

		self.serverList.append(server)
	def addSockListen(self,sock):
		sock.setblocking(False)
		self.serverList.append(sock)
		
	def addSockConnect(self,connect):
		if not connect.sock in self.socketList:
			self.socketList[connect.sock] = connect
			baseServer.log(2,connect,">	connect")
	
	def handleNewConnect(self,sock,address):
		handler = self.handler(server=self)
		self.socketList[sock] = handler
		handler._setConnect(sock, address)
		baseServer.log(2,handler,"*	connect")

	@staticmethod
	def log(level, *args, **kwargs):
		if level < debuglevel:
			return
		
		data = "	".join(str(i) for i in args)
		if level==3:
			data += "	"+str(sys.exc_info())
			data += "	"+str(traceback.format_exc())
		
		data = time.strftime("%y-%B-%d %H:%M:%S:	")+ data
		if level<2:
			print data+""
		else:
			logging.log([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR][level], data)
	def start(self):
		
		while True:
			rlist = self.serverList + self.socketList.keys()
			wlist = []
			for connect in self.socketList.values():
				if len(connect.dataSendList)>0:
					wlist.append(connect.sock)
			readable,writable,exceptional = select.select(rlist, wlist, rlist,1)
			for sock in readable:
				if sock in self.serverList:
					self.onConnect(sock)
				else:
					self.onData(sock)
			for sock in writable:
				self.onSend(sock)
			for sock in exceptional:
				self.onExcept(sock)
				
			cblist = self.callbackList
			self.callbackList = []
			while len(cblist):
				cbobj = cblist.pop(0)
				cbobj[0](*cbobj[2],**cbobj[3])
				
	def onConnect(self,sock):
		connect,address = sock.accept()
		connect.setblocking(0)
		self.handleNewConnect(connect,address)
	def onSend(self,sock):
		if sock in self.socketList:
			connect = self.socketList[sock]
			data = connect.dataSendList.pop(0)
			if data:
				try:
					connect.onSend(data)
					return
				except:
					baseServer.log(3)
			sock.close()
			self.onExcept(sock)
			
	def onData(self,sock):
		data = None
		
		try:
			data = sock.recv(1024)
		except ssl.SSLError as e:
			if isinstance(e, ssl.SSLWantReadError):
				return
			else:
				baseServer.log(3)
		except:
			baseServer.log(3)
		
		
		if isinstance(sock, ssl.SSLSocket):
			while 1:
				data_left = sock.pending()
				if data_left:
					data += sock.recv(data_left)
				else:
					break
		
		if data:
			if sock in self.socketList:
				handler = self.socketList[sock]
				handler.onRecv(data)
		else:
			self.onExcept(sock)
	def onExcept(self,sock):
		if sock in self.socketList:
			handler = self.socketList[sock]
			baseServer.log(2,handler,"<	close")
			del self.socketList[sock]
			handler.onClose()
			
if __name__ == "__main__":
	server = baseServer(handler=sockConnect)
	server.addListen(port=8888)
	server.start()
