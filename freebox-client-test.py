#!/usr/bin/python

from urllib2 import urlopen, Request
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
APP_TOKEN = 'yourtoken'

AUTH_HEADER = 'X-Fbx-App-Auth'

class Session:

	def __init__(self):
		self.api_base_url = self.__get_api_base_url()
		self.app_token = APP_TOKEN
		self.challenge = self.__get_challenge()
		self.password = self.__calculate_password()
		self.session_token = self.__get_session_token()

	def __get_api_base_url(self):
		request = Request(BASEURL + API_BOOTSTRAP)
		response = urlopen(request)
		result = StringIO(response.read())
		j = json.load(result)
		return j['api_base_url']

	def __get_challenge(self):
		# get challenge
		request = Request(BASEURL + self.api_base_url + 'v%d/login/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		response = urlopen(request)
		result = StringIO(response.read())
		j = json.load(result)
		return j['result']['challenge']

	def __calculate_password(self):
		# http://dev.freebox.fr/sdk/os/login/: password = hmac-sha1(app_token, challenge)
		hm = hmac.new(self.app_token, self.challenge, sha1)
		password = hm.hexdigest()
		return password

	# login
	def __get_session_token(self):
		session_token = '{"app_id": "%s", "password": "%s"}' % (APP_ID, self.password)
		request = Request(BASEURL + self.api_base_url + 'v%d/login/session/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		# POST
		response = urlopen(request, session_token)
		result = StringIO(response.read())
		j = json.load(result)
		if j['success']:
			return j['result']['session_token']
		else:
			print("Error in __get_session_token(): %s" % j['msg'])
			return None

	# FIXME
	def logout(self):
		request = Request(BASEURL + self.api_base_url + 'v%d/login/session/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		request.add_header(AUTH_HEADER, self.session_token)
		# force POST to submit session_token (not needed as well)
		response = urlopen(request, self.session_token)
		result = StringIO(response.read())
		j = json.load(result)
		if not j['success']:
			print("Error when logout (%s)" % j['msg'])

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
		request.add_header('Content-type', 'application/json')
		request.add_header(AUTH_HEADER, self.session.session_token)
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

# http://dev.freebox.fr/sdk/os/connection/
class Connection:

	def __init__(self, session):
		self.session = session

	def get_connection_status(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/connection/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		request.add_header(AUTH_HEADER, self.session.session_token)
		response = urlopen(request)
		result = StringIO(response.read())
		j = json.load(result)
		if j['success']:
			return j['result']
		else:
			print("%s" % j['msg'])

class System:

	def __init__(self, session):
		self.session = session

	def get_system_info(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/system/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		request.add_header(AUTH_HEADER, self.session.session_token)
		response = urlopen(request)
		result = StringIO(response.read())
		j = json.load(result)
		if j['success']:
			return j['result']
		else:
			print("%s" % j['msg'])

class Lan():

	def __init__(self, session):
		self.session = session

	def get_lan_info(self):
		request = Request(BASEURL + self.session.api_base_url + 'v%d/lan/browser/pub/' % API_VERSION)
		request.add_header('Content-type', 'application/json')
		request.add_header(AUTH_HEADER, self.session.session_token)
		response = urlopen(request)
		result = StringIO(response.read())
		j = json.load(result)
		if j['success']:
			return j['result']
		else:
			print("%s" % j['msg'])


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
	pp.pprint(lan.get_lan_info())
