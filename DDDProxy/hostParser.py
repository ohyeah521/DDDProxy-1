import re
from DDDProxy.log import log
from urllib.parse import urlparse

	
def parserUrlAddrPort(path):
	url = urlparse(path)
	hostname = url.netloc
	port = "443" if url.scheme == "https" else "80"
	if hostname.find(':') > 0:
		try:
			addr, port = hostname.split(':')
		except:
			log(3)
			addr = hostname
	else:
		addr = hostname
	port = int(port)
	return (addr, port)

# ^(.*?)\.*([^\.]+)(\.(?:net\.cn|com\.cn|com\.hk|co\.jp|org\.cn|[^\.\d]{2,3}))$
hostMatch = re.compile('^(.*?)\.*([^\.]+)(\.(?:(?:gov|org|com|co|net|edu)\.[a-z]{2,3}|[a-z]{2,3}|google))$')
def getDomainName(host):
	try:
		match = hostMatch.match(host)
		if match:
			hostGroup = match.groups()
			if len(hostGroup) > 2:
				return "%s%s" % (hostGroup[1], hostGroup[2])
	except:
		log(3, host)
	return None
