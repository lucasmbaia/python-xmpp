#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
import socket
from optparse import OptionParser

import sleekxmpp
import ast
import subprocess
import os

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.xmlstream import ET, StanzaBase, register_stanza_plugin
from sleekxmpp.plugins.xep_0077.stanza import Register
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp.xmlstream.matcher.stanzapath import StanzaPath
from sleekxmpp.xmlstream.matcher.xmlmask import MatchXMLMask
from sleekxmpp import Iq
from etcdf import Etcd
from sleekxmpp.plugins.docker.stanza import Docker
from sleekxmpp.plugins.docker.register import DOCKER

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

class DockerLocal(ElementBase):
	namespace = 'jabber:iq:docker'
	name = 'query'
	plugin_attrib = 'docker'
	interfaces = set(('containers', 'deploy', 'result'))
	sub_interfaces = interfaces
	form_fields = set(('containers', 'deploy', 'result'))
	
class Minion(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password):
		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.chat_minions = 'minions'
		self.range_ports = range(10000, 10100)
		self.add_event_handler("session_start", self.start)
		self.add_event_handler("message", self.message)
		self.add_event_handler("name_pods", self._handler_name_pods)

		register_stanza_plugin(Iq, Containers)
		register_stanza_plugin(Iq, DockerLocal)

		#self.registerHandler(
		#    Callback('Total Containers',
		#							MatchXPath('{%s}iq/{jabber:iq:containers}query' % self.default_ns),
		#	      			self._handler_total_containers))
		
		#self.registerHandler(
		#    Callback('Docker',
		#							MatchXPath('{%s}iq/{jabber:iq:docker}query' % self.default_ns),
		#	      			self._handler_docker))

		#self.registerHandler(
		#    Callback('Docker',
		#							MatchXPath('{%s}iq/{jabber:iq:pods:name}query' % self.default_ns),
		#      				self._handler_name_pods))

	def start(self, event):
		self.send_presence()
		self.get_roster()
		global form

		self.room = 'minions@conference.localhost'
		self.nick = self.boundjid.user

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
					logging.error("Could not create chat room: %s" % e.iq['error']['text'])

					self.disconnect()
			else:
				logging.error("Could not create chat room: %s" % e.iq['error']['text'])

				self.disconnect()
		else:
			self.plugin['xep_0045'].joinMUC(self.room,
																			self.nick)

			logging.info("Chat room %s success created!" % self.room)

		self.add_event_handler("muc::%s::got_online" % self.room, self.muc_online)

	def message(self, msg):
		if msg['type'] in ('chat', 'normal'):
			option = msg['body'].split()[0]

			if option == "deploy":
			  try:
			    response = self.deploy(msg)
			    print(response)
			  except Exception as e:
			    print(unicode(e))
			elif option == "list_ports":
			  try:
			    self.list_ports()
			  except Exception as e:
			    print(e)

		if msg['type'] in ('groupchat', 'normal'):
			print(msg['body'])

	def _handler_name_pods(self, iq):
		if iq['id'] == 'name-pods':
			try:
				names = self._handler_name_containers()
				self.plugin['docker'].response_get_name_pods(ito=iq['from'],
																										ifrom=self.boundjid,
																										success=True,
																										response=','.join(str(s) for s in names))
			except Exception as e:
				self.plugin['docker'].response_get_name_pods(ito=iq['from'],
																										ifrom=self.boundjid,
																										success=False,
																										error=unicode(e))

		if iq['id'] == 'total-pods':
			try:
				total = self._handler_name_containers()
				self.plugin['docker'].response_total_pods(ito=iq['from'],
																									ifrom=self.boundjid,
																									success=True,
																									response=total)
			except Exception as e:
				self.plugin['docker'].response_total_pods(ito=iq['from'],
																									ifrom=self.boundjid,
																									success=False,
																									response=unicode(e))

		if iq['id'] == 'first-deploy':
			print(iq['docker']['name'])
			print(iq['docker']['key'])
			print(iq['docker']['user'])

	def _handler_docker(self, iq):
		response_iq = self.Iq()
		response_iq['id'] = 'containers'
		response_iq['to'] = iq['from']
		response_iq['from'] = self.boundjid

		if iq['id'] == 'containers':
			try:
				names = self._handler_name_containers()
				query = ET.Element('{jabber:iq:docker}query')
				result = ET.Element('containers')
				result.text = ','.join(str(s) for s in names)
				query.append(result)

				response_iq['type'] = 'result'
				response_iq.append(query)
			except Exception as e:
				response_iq['query'] = 'jabber:iq:docker'
				response_iq['type'] = 'error'
				response_iq['error'] = 'cancel'
				response_iq['error']['text'] = unicode(e)

		response_iq.send(now=True)
	
	def _handler_name_containers(self):
		command = ['docker', 'ps', '--format', '"{{.Names}}"']
		
		try:
			response = self.exec_command(command).split('\n')
			return response[:1]
		except Exception as e:
			raise Exception(e)
				
	def _handler_total_containers(self):
		command = ['docker', 'ps']
		count = -1

	  #response_iq = self.Iq()
	  #response_iq['id'] = 'containers'
	  #response_iq['to'] = iq['from']
	  #response_iq['from'] = self.boundjid

		try:
			response = self.exec_command(command).split('\n')
	    
			for infos in response:
				if len(infos.strip()) > 0:
					count += 1

			return count
	    #query = ET.Element('{jabber:iq:containers}query')
	    
	    #result = ET.Element('result')
	    #result.text = unicode(count)

	    #query.append(result)
	    #response_iq['type'] = 'result'
	    #response_iq.append(query)
		except Exception as e:
			raise Exception(e)
	    #response_iq['query'] = 'jabber:iq:containers'
	    #response_iq['type'] = 'error'
	    #response_iq['error'] = 'cancel'
	    #response_iq['error']['text'] = unicode(e)
	 
	  #response_iq.send(now=True)

	def exec_command(self, command):
	  try:
	    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	    (out, err) = process.communicate()

	    if out:
	      return out
	    if err:
	      raise Exception(err.strip())
	  except OSError as e:
	    raise Exception(e)

	def list_ports(self):
	  command = ['docker', 'ps', '--format', '"{{.Ports}}"']
	  ports = []

	  try:
	    docker_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	    (out, err) = docker_process.communicate()

	    if out:
	      response = out.split('\n')

	      for infos in response:
		if len(infos.strip()) > 0:
		  port = infos.split(':')[1].split('->')[0]
		  ports.append(port)

	    if err:
	      raise Exception(err.strip())
	  except OSError as e:
	    raise Exception(e)
	  except:
	    raise Exception(sys.exc_info()[0])

	  return ports

	def deploy(self, msg):
		args = msg['body'].split()
		hostname = args[1]
		endpoint = args[2]
		user_container = args[3]
		port_host = None

		etcd_conn = Etcd('192.168.204.128', 2379)

		try:
			values = ast.literal_eval(etcd_conn.read(endpoint))
		except Exception as e:
			raise Exception(e)

		try:
			ports = self.list_ports()

			print(ports)
			for port in self.range_ports:
				if str(port) not in ports:
					port_host = str(port)
					break

			if port_host is None:
				raise Exception("Not more ports available in host")
		except Exception as e:
			raise Exception(e)

		try:
			command = self.docker_command(hostname, endpoint, user_container, port_host, values)
		except Exception as e:
			raise Exception(e)

		print(command)
		try:
			docker_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			(out, err) = docker_process.communicate()

			if out:
				return out
			if err:
				raise Exception(err.strip())

		except OSError as e:
			raise Exception(e)
	
	def docker_command(self, hostname, endpoint, user_container, port_host, values):
	  command = ['docker', 'run']

	  command.append('--env')
	  command.append('jid=' + user_container + '@localhost')
	  command.append('--env')
	  command.append('etcd_url=192.168.204.128')
	  command.append('--env')
	  command.append('etcd_endpoint=' + endpoint)
	  command.append('--env')
	  command.append('xmpp_url=192.168.204.131')

	  if 'args' in values:
	    for x in values['args']:
	      command.append('--env')
	      command.append(x + '=' + values['args'][x])

	  if 'port_dst' in values:
	    command.append('-p')
	    command.append(port_host + ':' + values['port_dst'])

	  command.append('--name')
	  command.append(hostname)

	  if 'cpus' in values:
	    command.append('--cpus=' + values['cpus'])
	  if 'memory' in values:
	    command.append('--memory=' + values['memory'])
	  if 'image' in values:
	    command.append('-d')
	    command.append(values['image'])
	  else:
	    raise Exception("image is empty")

	  return command
	def muc_online(self, presence):
		if presence['muc']['nick'] != self.nick:
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

	xmpp = Minion('minion@localhost', 'totvs@123')
	xmpp.register_plugin('xep_0030') # Service Discovery
	xmpp.register_plugin('xep_0004') # Data Forms
	xmpp.register_plugin('xep_0059') #
	xmpp.register_plugin('xep_0060') # PubSub
	xmpp.register_plugin('xep_0045') #
	xmpp.register_plugin('xep_0085') #
	xmpp.register_plugin('xep_0071') #
	xmpp.register_plugin('xep_0199') # XMPP Ping
	xmpp.register_plugin('xep_0066') # Out-of-band Data
	xmpp.register_plugin('docker')

	#test_ns = 'http://jabber.org/protocol/chatstates'
	#xmpp['xep_0030'].add_feature(test_ns)

	if xmpp.connect(address=('192.168.204.131', 5222)):
		xmpp.process(block=True)
		print("Done")
	else:
		print("Unable to connect.")

