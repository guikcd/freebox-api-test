#!/usr/bin/python

import sys
from urllib2 import urlopen, Request, HTTPError
from StringIO import StringIO
import simplejson as json

# challenge password
from hashlib import sha1
import hmac

from time import time

BASEURL = 'http://mafreebox.freebox.fr'
API_BOOTSTRAP = '/api_version'
API_VERSION = 1

APP_ID = 'org.iroqwa.freebox_stats'
TOKEN_FILE = 'token'

AUTH_HEADER = 'X-Fbx-App-Auth'
USER_AGENT = APP_ID

class Session:

	def __init__(self):
		self.api_base_url = self.__get_api_base_url()
		self.app_token = self.__get_token()
		self.challenge = self.__get_challenge()
		self.password = self.__calculate_password()
		self.session_token = self.__get_session_token()

	def __get_token(self):
		token_file = open(TOKEN_FILE, 'r')
		read_data = token_file.readlines()[0].rstrip('\n')
		token_file.close()
		return read_data

	def __get_api_base_url(self):
		request = Request(BASEURL + API_BOOTSTRAP)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			return j['api_base_url']
		except Exception, e:
			print("Unexcepted error when connecting to %s: %s" % \
					(request.get_full_url(), e))
			sys.exit(e)

	def __get_challenge(self):
		request = Request(BASEURL + self.api_base_url + 'v%d/login/' % API_VERSION)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			return j['result']['challenge']
		except Exception, e:
			j = json.loads(e.readlines()[0])
			print("Problem in get_challenge(): %s (%s)" % (j['msg'], j['error_code']))
			sys.exit(e)

	def __calculate_password(self):
		# http://dev.freebox.fr/sdk/os/login/: password = hmac-sha1(app_token, challenge)
		myhmac = hmac.new(self.app_token, self.challenge, sha1)
		password = myhmac.hexdigest()
		return password

	# login
	def __get_session_token(self):
		session_token = '''
						{
							"app_id": "%s",
							"password": "%s"
						}
						''' \
								% (APP_ID, self.password)
		request = Request(BASEURL + self.api_base_url + 'v%d/login/session/' % API_VERSION)
		request.add_header('User-Agent', USER_AGENT)
		# POST
		try:
			response = urlopen(request, session_token)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				return j['result']['session_token']
			else:
				print("Error in __get_session_token(): %s" % j['msg'])
				return None
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get session token: %s (%s)" % (j['msg'], j['error_code']))
			sys.exit(e)

	def logout(self):
		request = Request(BASEURL + self.api_base_url + 'v%d/login/logout/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			# force POST
			response = urlopen(request, "")
			result = StringIO(response.read())
			j = json.load(result)
			if not j['success']:
				print("Error when logout (%s)" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable logout: %s (%s)" % (j['msg'], j['error_code']))
			sys.exit(e)

class RRDFetch:
	def __init__(self, session):
		self.session = session
		self.date_start = int(time()-300)
		self.date_end = int(time())
		self.precision = 1

	# http://dev.freebox.fr/sdk/os/rrd/#post--api-v1-rrs-
	def get_rrd(self, db, field):
		stats = '''{
					"db": "%s",
					"date_start": "%d",
					"date_end": "%d",
					"fields": [ "%s" ],
					"precision": %d
				 }''' % (db, self.date_start, self.date_end, field, self.precision)
		request = Request(BASEURL + self.session.api_base_url + 'v%d/rrd/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			# POST
			response = urlopen(request, stats)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				#print("success %s" % j['result']['data'])
				last_index = len(j['result']['data']) - 1
				return j['result']['data'][last_index][field]
			else:
				print("Problem in get_rrd(): %s" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get connection status : %s (%s)" % (j['msg'], j['error_code'] ))
			sys.exit(e)

# http://dev.freebox.fr/sdk/os/connection/
class Connection:

	def __init__(self, session):
		self.session = session

	def get_connection_status(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/connection/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				return j['result']
			else:
				print("%s" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get connection status : %s (%s)" % (j['msg'], j['error_code'] ))
			sys.exit(e)

class System:

	def __init__(self, session):
		self.session = session

	def get_system_info(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/system/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				return j['result']
			else:
				print("%s" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get system info : %s (%s)" % (j['msg'], j['error_code'] ))
			sys.exit(e)

class Lan():

	def __init__(self, session):
		self.session = session

	def get_lan_info(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/lan/browser/pub/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				return j['result']
			else:
				print("%s" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get lan info : %s (%s)" % (j['msg'], j['error_code'] ))
			sys.exit(e)

class Igd():

	def __init__(self, session):
		self.session = session

	def get_redirections(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/upnpigd/redir/' % API_VERSION)
		request.add_header(AUTH_HEADER, self.session.session_token)
		request.add_header('User-Agent', USER_AGENT)
		try:
			response = urlopen(request)
			result = StringIO(response.read())
			j = json.load(result)
			if j['success']:
				return j['result']
			else:
				print("%s" % j['msg'])
		except HTTPError, e:
			j = json.loads(e.readlines()[0])
			print("Unable to get igd redirections : %s (%s)" % (j['msg'], j['error_code'] ))
			sys.exit(e)

if __name__ == "__main__":
	session = Session()
	#rrdfetch = RRDFetch(session)
	#print(rrdfetch.get_rrd('net', 'rate_up'))
	#print(rrdfetch.get_rrd('net', 'rate_down'))
	#connection = Connection(session)
	#connection_status = connection.get_connection_status()
	#print(connection_status['rate_down'], connection_status['rate_up'])
	#system = System(session)
	#print(system.get_system_info())
	lan = Lan(session)
	import pprint
	pp = pprint.PrettyPrinter()
	infos = lan.get_lan_info()
	#pp.pprint(infos)
	for info in infos:
		if info['active'] is True:
			print(info)
			print(info['names'], info['l3connectivities'][0]['addr'])
			print("###############################################")
	igd = Igd(session)
	redirections = igd.get_redirections()
	#pp.pprint(redirections)
	for redirection in redirections:
		if redirection['int_ip'] not in '192.168.0.249':
			print(redirection['desc'], redirection['int_ip'])
	session.logout()
