#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
from optparse import OptionParser

import crypt
import sleekxmpp

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.xmlstream import ET, StanzaBase, register_stanza_plugin
from sleekxmpp.plugins.xep_0077.stanza import Register
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp import Iq
from etcdf import Etcd

if sys.version_info < (3, 0):
        reload(sys)
        sys.setdefaultencoding('utf8')
else:
        raw_input = input

class Containers(ElementBase):
  namespace = 'jabber:iq:containers'
  name = 'query'
  plugin_attrib = 'containers'
  interfaces = set(('total', 'result'))
  sub_interfaces = interfaces
  form_fields = set(('total', 'result'))

class Register(sleekxmpp.ClientXMPP):
	def __init__(self, domain, jid, password):
		super(Register, self).__init__(jid, password)
		self.register_plugin('xep_0030')
		self.register_plugin('xep_0004')
		self.register_plugin('xep_0066')
		self.register_plugin('xep_0077')
		self.add_event_handler("session_start", self.start, threaded=True)
		self.add_event_handler("register", self.register, threaded=True)

	def start(self, event):
		self.disconnect(wait=True)

	def run(self):
		self.connect(address=('172.16.95.111', 5222))
		self.process(threaded=True)

	def register(self, iq):
		create = self.Iq()
		create['type'] = 'set'
		create['register']['username'] = self.boundjid.user
		create['register']['password'] = self.password

		try:
			create.send(now=True)
                        logging.info("Account created for %s!" % self.boundjid)
                except IqError as e:
                        logging.error("Could not register account: %s" %
                                        e.iq['error']['text'])
                except IqTimeout:
                        logging.error("No response from server.")

class Zeus(sleekxmpp.ClientXMPP):
        def __init__(self, jid, password):
                sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.minions = []
		self.jid_minions = []
		self.chat_minions = 'minions'
                self.add_event_handler("session_start", self.start)
                self.add_event_handler("message", self.message)

		register_stanza_plugin(Iq, Containers)

        def start(self, event):
                self.send_presence()
                self.get_roster()
		global form

		self.room = 'minions@conference.localhost'
		self.nick = 'zeus'

		rooms = self.plugin['xep_0030'].get_items(jid='conference.localhost')

		for room in rooms['disco_items']:
			if room['jid'] != self.room:
				self.plugin['xep_0045'].joinMUC(room['jid'],
								self.nick)

				self.add_event_handler("muc::%s::got_online" % room['jid'], self.muc_online)
				self.add_event_handler("muc::%s::got_offline" % room['jid'], self.muc_offline)
                        	logging.info("Chat room %s success!" % room['jid'])

		try:
			room_exist = self.plugin['xep_0030'].get_info(jid=self.room)
		except IqError as e:
			if e.condition == 'item-not-found':
				self.plugin['xep_0045'].joinMUC(self.room,
								self.nick,
								wait=True)

				form = self.plugin['xep_0045'].getRoomConfig(self.room)
				form.set_values({'muc#roomconfig_persistentroom': 1,
					 	 'muc#roomconfig_passwordprotectedroom': 0,
				 		 'muc#roomconfig_publicroom': 1,
				 		 'muc#roomconfig_roomdesc': 'TESTE!'})

                		try:
                        		self.plugin['xep_0045'].configureRoom(self.room, form=form)
                        		logging.info("Chat room %s success created!" % self.room)
                		except IqError as e:
                        		logging.error("Could not create chat room: %s" %
                                        	e.iq['error']['text'])

					self.disconnect()
			else:
                        	logging.error("Could not create chat room: %s" %
                                        e.iq['error']['text'])

				self.disconnect()
		else:
			self.plugin['xep_0045'].joinMUC(self.room,
							self.nick)

                        logging.info("Chat room %s success created!" % self.room)

		self.add_event_handler("muc::%s::got_online" % self.room, self.muc_online)
		self.add_event_handler("muc::%s::got_offline" % self.room, self.muc_offline)

        def message(self, msg):
                print("CHAT")
                if msg['type'] in ('chat', 'normal'):
                        option = msg['body'].split()[0]

                        if option == "help":
                                self.help(msg)
			elif option == "deploy":
			  self.deploy(msg)
                        elif option == "register":
				try:
                                	self.register(msg)
				except Exception as e:
                                	self.send_message(mto=msg['from'],
                                                	mbody=unicode(e),
                                                	mtype='chat')

                        elif option == "create_room":
                                self.create_room(msg)
			elif option == "teste_iq":
			  #self.teste_iq()
                        else:
                                print(option)
                                self.send_message(mto=msg['from'],
                                                mbody='Invalid Option',
                                                mtype='chat')

		if msg['type'] in ('groupchat', 'normal'):
			print(msg['body'])

        def help(self, msg):
                custom_msg = self.Message()
                custom_msg['body'] = 'Here&apos;s my .plan for today: 1. Add the following examples to XEP-0071: - ordered and unordered lists - more styles (e.g., indentation) 2. Kick back and relax'
                custom_msg['html']['body'] = '<p>Here&apos;s my .plan for today:</p><ol><li>Add the following examples to XEP-0071:<ul><li>ordered and unordered lists</li><li>more styles (e.g., indentation)</li></ul></li><li>Kick back and relax</li></ol>'

                self.send_message(mto=msg['from'],
                                mbody=custom_msg['body'],
                                mhtml=custom_msg['html'],
                                mtype='chat')

	def get_number_containers(self, to):
	  request_iq = self.Iq()
	  request_iq['type'] = 'get'
	  request_iq['id'] = 'containers'
	  #request_iq['to'] = self.porra[0]
	  request_iq['to'] = to
	  request_iq['from'] = self.boundjid
	  request_iq['query'] = 'jabber:iq:containers'

	  try:
	    response = request_iq.send(now=True)
	    return response['containers']['result']
	  except Exception as e:
	    raise Exception(e)

	def deploy(self, msg):
	  values_etcd = {'pods': 1}
	  hostname = None
	  customer = None
	  pods = 1
	  infos = msg['body'].split('%')

	  for value in infos:
	    if "--cpus" in value:
	      values_etcd['cpus'] = value.replace("--cpus=", "").strip()
	    if "--memory" in value:
	      values_etcd['memory'] = value.replace("--memory=", "").strip()
	    if "--args" in value:
	      dic = {}
	      args = value.strip().replace("--args[", "").replace("]", "").split(',')

	      for arg in args:
		x = arg.split(':')
		dic[x[0]] = x[1]

	      values_etcd['args'] = dic
	    if "--name" in value:
	      hostname = value.replace("--name=", "").strip()
	    if "--customer" in value:
	      customer = value.replace("--customer=", "").strip()
	    if "--pods" in value:
	      pods = int(value.replace("--pods=", "").strip())
	      values_etcd['pods'] = pods
	    if "--port" in value:
	      port = value.replace("--port=", "").strip()
	      values_etcd['port_dst'] = port
	  
	  password = crypt.encrypt_data('123456', 'id_rsa.pub')

	  values_etcd['password'] = password
	  values_etcd['image'] = 'minion'

	  etcd_conn = Etcd('127.0.0.1', 2379)
	  endpoint = '/' + customer + '/' + hostname

	  try:
	    etcd_conn.write(endpoint, values_etcd)
	  except Exception as e:
	    raise Exception(e)

	  _create_room(self, hostname)

	  if len(self.jid_minions) == 1:
	    for number in range(pods):
	      user = hostname + '-' + str(number)
	      create_user = Register(self.boundjid.domain, user + "@" + self.boundjid.domain, '123456')
	      create.run()

	      msg = 'deploy ' + hostname + ' ' + endpoint
	      self.send_message(mto=self.minions[0] + '@' + self.boundjid.domain,
				mbody=msg,
				mtype='chat')
	      print(msg)
	  
        def register(self, msg):
                args = msg['body'].split()

		if len(args) < 3:
			raise Exception("Number of args is invalid")

		create = Register(self.boundjid.domain, args[1] + "@" + self.boundjid.domain, '123456')
		create.run()

	def create_room(self, msg):
	  args = msg['body'].split()

	  _create_room(self, args[1])
	    
        def _create_room(self, name):
                #args = msg['body'].split()
		self.room = name + '@conference.localhost'

		try:
			room_exist = self.plugin['xep_0030'].get_info(jid=self.room)
		except IqError as e:
			if e.condition == 'item-not-found':
				self.plugin['xep_0045'].joinMUC(self.room,
								self.nick,
								wait=True)

				form = self.plugin['xep_0045'].getRoomConfig(self.room)
				form.set_values({'muc#roomconfig_persistentroom': 1,
					 	 'muc#roomconfig_passwordprotectedroom': 0,
				 		 'muc#roomconfig_publicroom': 1,
				 		 'muc#roomconfig_roomdesc': 'TESTE!',
				 		 'muc#roomconfig_roomname': self.room})

                		try:
                        		self.plugin['xep_0045'].configureRoom(self.room, form=form)
                        		logging.info("Chat room %s success created!" % self.room)
                		except IqError as e:
                        		logging.error("Could not create chat room: %s" %
                                        	e.iq['error']['text'])

			else:
                        	logging.error("Could not create chat room: %s" %
                                        e.iq['error']['text'])

		else:
			self.plugin['xep_0045'].joinMUC(self.room,
							self.nick)

                        logging.info("Chat room %s success created!" % self.room)

		self.add_event_handler("muc::%s::got_online" % self.room, self.muc_online)
		self.add_event_handler("muc::%s::got_offline" % self.room, self.muc_offline)
			
	def muc_online(self, presence):
		if presence['muc']['nick'] != self.nick:
			if presence['from'].bare.split('@')[0] == self.chat_minions:
				self.minions.append(presence['muc']['nick'])
				self.jid_minions.append(presence['muc']['jid'])

			self.send_message(mto=presence['from'].bare,
					  mbody="Ola Trouxa, %s %s" % (presence['muc']['role'], presence['muc']['nick']),
					  mtype='groupchat')

	def muc_offline(self, presence):
		if presence['muc']['nick'] != self.nick:
			if presence['muc']['nick'] in self.minions:
				print("Minion Down")
			else:
				print("Application Down")

			print(presence['muc']['nick'])

if __name__ == '__main__':
	optp = OptionParser()

	optp.add_option('-q', '--quiet', help='set logging to ERROR',
			action='store_const', dest='loglevel',
			const=logging.ERROR, default=logging.INFO)

	optp.add_option('-d', '--debug', help='set logging to DEBUG',
			action='store_const', dest='loglevel',
			const=logging.DEBUG, default=logging.INFO)

	optp.add_option('-v', '--verbose', help='set logging to COMM',
			action='store_const', dest='loglevel',
			const=5, default=logging.INFO)

	opts, args = optp.parse_args()
	logging.basicConfig(level=opts.loglevel,
				format='%(levelname)-8s %(message)s')

        xmpp = Zeus('luquitas@localhost', 'totvs@123')
        xmpp.register_plugin('xep_0030') # Service Discovery
        xmpp.register_plugin('xep_0004') # Data Forms
        xmpp.register_plugin('xep_0059') #
        xmpp.register_plugin('xep_0060') # PubSub
        xmpp.register_plugin('xep_0045') #
        xmpp.register_plugin('xep_0085') #
        xmpp.register_plugin('xep_0071') #
        xmpp.register_plugin('xep_0199') # XMPP Ping
        xmpp.register_plugin('xep_0066') # Out-of-band Data
        #xmpp.register_plugin('xep_0077') # In-band Registratio

        #test_ns = 'http://jabber.org/protocol/chatstates'
        #xmpp['xep_0030'].add_feature(test_ns)

        #xmpp['xep_0077'].force_registration = True

        if xmpp.connect(address=('172.16.95.111', 5222)):
                xmpp.process(block=True)
                print("Done")
        else:
                print("Unable to connect.")

