#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
from optparse import OptionParser

import crypt
import sleekxmpp
import uuid
import threading
import os
import ast

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.xmlstream import ET, StanzaBase, register_stanza_plugin
from sleekxmpp.plugins.xep_0077.stanza import Register
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp import Iq
from etcdf import Etcd
from dockerf import DockerCommands
from haproxyf import HAProxy
from sleekxmpp.plugins.docker.stanza import Docker
from sleekxmpp.plugins.docker.register import DOCKER


if sys.version_info < (3, 0):
	reload(sys)
	sys.setdefaultencoding('utf8')
else:
	raw_input = input


class Zeus(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password, etcd_url):
		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.minions = []
		self.jid_minions = []
		self.minions_pods = {}
		self.chat_minions = 'minions'
		self.etcd_url = etcd_url
		self.etcd_port = 2379
		self.containers_per_minion = {}
		self.path_images = os.environ['path_images']
		self.add_event_handler("session_start", self.start)
		self.add_event_handler("message", self.message)
		self.add_event_handler("name_pods", self._handler_deploy)
		self.etcd_conn = Etcd(self.etcd_url, self.etcd_port)
		self.docker_commands = DockerCommands(etcd_url=self.etcd_url, etcd_port=self.etcd_port)
		self.haproxy = HAProxy(etcd_url=self.etcd_url, etcd_port=self.etcd_port)

	def start(self, event):
		self.send_presence()
		self.get_roster()
		global form

		self.room = 'minions@conference.localhost'
		self.nick = self.boundjid.user

		rooms = self.plugin['xep_0030'].get_items(jid='conference.localhost')

		for room in rooms['disco_items']:
			if room['jid'] != self.room:
				self.plugin['xep_0045'].joinMUC(room['jid'],
												self.nick)

				self.add_event_handler("muc::%s::got_online" %
									   room['jid'], self.muc_online)
				self.add_event_handler("muc::%s::got_offline" %
									   room['jid'], self.muc_offline)
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

		self.add_event_handler("muc::%s::got_online" %
							   self.room, self.muc_online)
		self.add_event_handler("muc::%s::got_offline" %
							   self.room, self.muc_offline)

	def message(self, msg):
		logging.info('Chat Message: %s' % msg['body'])

		if msg['type'] in ('chat', 'normal'):
			option = msg['body'].split()[0]

			if option == "help":
				self.help(msg)
			elif option == "deploy":
				thread_deploy = threading.Thread(
					target=self.first_deploy, args=[msg])
				thread_deploy.daemon = True
				thread_deploy.start()
			elif option == "append":
				thread_append = threading.Thread(
					target=self.append_containers, args=[msg])
				thread_append.daemon = True
				thread_append.start()
			elif option == "create_room":
				self.create_room(msg)
			elif option == "container-die":
				thread_container_die = threading.Thread(target=self.container_die, args=[msg])
				thread_container_die.daemon = True
				thread_container_die.start()
			elif option == "stop" or option == "start" or option == "pause" or option == "resume":
				body = msg['body'].split(' ')

				try:
					print("PORRA")
					self.action_container(action=option, container=body[1])
					response = 'Success ' + option + ' ' + body[1]
				except Exception as e:
					response = unicode(e)

				self.send_message(mto=msg['from'],
								  mbody=response,
								  mtype='chat')
			else:
				print(option)
				self.send_message(mto=msg['from'],
								  mbody='Invalid Option',
								  mtype='chat')

		if msg['type'] in ('groupchat', 'normal'):
			print(msg['body'])

	def help(self, msg):
		custom_msg = self.Message()
		custom_msg[
			'body'] = 'Here&apos;s my .plan for today: 1. Add the following examples to XEP-0071: - ordered and unordered lists - more styles (e.g., indentation) 2. Kick back and relax'
		custom_msg['html'][
			'body'] = '<p>Here&apos;s my .plan for today:</p><ol><li>Add the following examples to XEP-0071:<ul><li>ordered and unordered lists</li><li>more styles (e.g., indentation)</li></ul></li><li>Kick back and relax</li></ol>'

		self.send_message(mto=msg['from'],
						  mbody=custom_msg['body'],
						  mhtml=custom_msg['html'],
						  mtype='chat')

	def _handler_deploy(self, iq):
		logging.info('Receive iq request from: %s, iq: %s, args: %s' %
					 (iq['from'], iq['id'], iq['docker']))

		if 'master-first-deploy' in iq['id']:
			args = iq['docker']

			try:
				response = self._deploy_application(
					args=args, iq_response=iq['id'], ifrom=iq['from'])
			except Exception as e:
				self.plugin['docker'].response_master_deploy(iq_response=iq['id'],
															 ito=iq['from'],
															 ifrom=self.boundjid,
															 success=False,
															 error=unicode(e))

		if 'master-append-deploy' in iq['id']:
			args = iq['docker']

			try:
				reponse = self._append_containers(
					args=args, iq_response=iq['id'], ifrom=iq['from'])
			except Exception as e:
				self.plugin['docker'].response_master_append_deploy(iq_response=iq['id'],
																	ito=iq['from'],
																	ifrom=self.boundjid,
																	success=False,
																	error=unicode(e))

	def _deploy_application(self, args, iq_response, ifrom):
		logging.info('Start Deploy Application %s' % (args['application_name']))

		if len(self.minions) == 0:
			raise Exception('Not have hosts to start the deploy')

		image = '{0}_app-{1}/image:v1'.format(args['customer'], args['application_name'])
		ports_and_protocols = args['ports'].strip().split(',')
		protocol = {}
		ports = []

		for x in ports_and_protocols:
			pp = x.split('/')

			ports.append(pp[0])
			protocol[pp[0]] = pp[1]

		values_application = {'cpus': args['cpus'], 'memory': args['memory'], 'ports_dst': ports, 'protocol': protocol, 'image': image, 'total_containers': args['total_containers'], 'dns': args['dns']}

		if 'args' in args:
			values_application['args'] = args['args']

		key_application = '/{0}/{1}'.format(args['customer'], args['application_name'])
		image_name = '{0}_app-{1}'.format(args['customer'], args['application_name'])

		try:
			self.etcd_conn.write(key_application, values_application)
		except Exception as e:
			raise Exception(e)

		# try:
		#	self._create_room(args['application_name'])
		# except Exception as e:
		#	raise Exception(e)

		try:
			self._request_deploy_minion(args=args, image_name=image_name, iq_response=iq_response,
										ifrom=ifrom, key_application=key_application, total_containers=args['total_containers'], first=True)
		except Exception as e:
			raise Exception(e)

	def _append_deploy_application(self, args, iq_response, ifrom):
		logging.info('Start Append Deploy Application %s' %
					 (args['application_name']))

		if len(self.minions) == 0:
			raise Exception('Not have hosts to start the deploy')

		key_application = '/{0}/{1}'.format(
			args['customer'], args['application_name'])

		try:
			values_application = ast.literal_eval(self.etcd_conn.read(key_application))
		except Exception as e:
			raise Exception(e)

		total_containers = values_application['total_containers'] + args['total_containers']
		start_count = values_application['total_containers'] + 1

		try:
			self._request_deploy_minion(args=args, image_name=values_application['image'], iq_response=iq_response, ifrom=ifrom,
										key_application=key_application, total_containers=args['total_containers'], start_count=start_count)
		except Exception as e:
			raise Exception(e)

		values_application['total_containers'] = total_containers

		try:
			self.etcd_conn.write(key_application, values_application)
		except Exception as e:
			raise Exception(e)

	def _request_deploy_minion(self, args, image_name, iq_response, ifrom, key_application, total_containers, first=False, start_count=1):
		if len(self.minions) == 1:
			if first:
				try:
					self._generate_image(path=args['path'], image_name=image_name, key_application=key_application, ito=self.jid_minions[0])
				except Exception as e:
					raise Exception(e)

			for count in range(int(total_containers)):
				container_name = '{0}_app-{1}-{2}'.format(args['customer'], args['application_name'], str(start_count))
				start_count += 1

				thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[self.jid_minions[0], args['application_name'], key_application, container_name, ifrom])
				thread_deploy_minion.daemon = True
				thread_deploy_minion.start()
		else:
			minions_containers = self._pods_containers(int(total_containers))
			iterator = start_count
			keys_minions = minions_containers.keys()

			if first:
				try:
					self._generate_image(
						path=args['path'], image_name=image_name, key_application=key_application, ito=keys_minions[0])
				except Exception as e:
					raise Exception(e)

				for minion in keys_minions[1:]:
					try:
						path = '{0}{1}.tar.gz'.format(
							self.path_images, image_name)
						self._load_image(path=path, ito=minion)
					except Exception as e:
						raise Exception(e)

			def start_deploy(self, minion, total_containers, iterator, key_application, application_name, customer, ifrom):
				for count in range(total_containers):
					container_name = '{0}_app-{1}-{2}'.format(customer, application_name, str(iterator))
					iterator += 1

					thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[minion, application_name, key_application, container_name, ifrom])
					thread_deploy_minion.daemon = True
					thread_deploy_minion.start()

			for minion in keys_minions:
				thread_start_deploy = threading.Thread(target=start_deploy, args=[self, minion, minions_containers[minion], iterator, key_application, args['application_name'], args['customer'], ifrom])
				thread_start_deploy.daemon = True
				thread_start_deploy.start()

				iterator += minions_containers[minion]

	# def _first_deploy(self, args, iq_response, ifrom):
	#    logging.info('Start First Deploy')

	#    if len(self.minions) == 0:
	#        raise Exception('Not have hosts to start the deploy')

	#    image = args['customer'] + '_app-' + args['name'] + '/image:v1'

	#    values_etcd = {'cpus': args['cpus'], 'memory': args['memory'], 'ports_dst': args['ports'].strip(
	#    ).split(','), 'image': image, 'total': args['total']}
	#    key_application = '/' + args['customer'] + '/' + args['name']

	#    etcd_conn = Etcd(self.etcd_url, self.etcd_port)

	#    try:
	#        etcd_conn.write(key_application, values_etcd)
	#    except Exception as e:
	#        raise Exception(e)

	#    try:
	#        self._create_room(args['name'])
	#    except Exception as e:
	#        raise Exception(e)

	#    try:
	#        self._send_deploy_minion(args=args, image=image, iq_response=iq_response,
	#                                 ifrom=ifrom, key_application=key_application, first=True)
	#    except Exception as e:
	#        raise Exception(e)

	def _deploy_container_die(self, application_name, container_name, minion, key_application):
		logging.info('Movie containers die in minion ' % (container_name))

		try:
			values_application = ast.literal_eval(self.etcd_conn.read(key_application))
		except Exception as e:
			raise Exception(e)

		minions_containers = self._pods_containers(1)
		keys_minions = minions_containers.keys()

		try:
			self.plugin['docker'].request_minion_deploy(application_name=application_name,
														container_name=container_name,
														key_application=key_application,
														ito=keys_minions[0],
														ifrom=self.boundjid,
														timeout=120)

			self.containers_per_minion[keys_minions[0]].append(container_name)
		except IqError as e:
			raise Exception(e.iq['error']['text'])
		except IqTimeout as t:
			raise Exception('Timout request')

		#if len(keys_minions) == 1 and keys_minions[0] == minion:
		#	raise Exception('Note have hosts avaliable to depoloy container')


	def _deploy_minion_die(self, containers):
		logging.info('Deploy containers %s die' % (containers))

		minions_containers = self._pods_containers(len(containers))
		keys_minions = minions_containers.keys()
		minion_iterator = 0
		count_containers = 1

		for idx, container_name in enumerate(containers):
			cn = container_name.split('_app-')
			customer = cn[0]
			application_name = '-'.join(cn[1].split('-')[:-1])
			key_application = '/{0}/{1}'.format(customer, application_name)

			if count_containers > minions_containers[keys_minions[minion_iterator]]:
				minion_iterator += 1
				count_containers = 1

			try:
				values_application = ast.literal_eval(self.etcd_conn.read(key_application))
			except Exception as e:
				raise Exception(e)

			try:
				self.haproxy.remove_container(application_name=str(application_name),
											container_name=str(container_name),
											protocol=ast.literal_eval(str(values_application['protocol'])))

				self.plugin['docker'].request_minion_deploy(application_name=application_name,
															container_name=container_name,
															key_application=key_application,
															ito=keys_minions[minion_iterator],
															ifrom=self.boundjid,
															timeout=120)

				count_containers += 1

				containers = containers[:idx] + containers[idx + 1:]
				self.containers_per_minion = containers
			except IqError as e:
				raise Exception(e.iq['error']['text'])
			except IqTimeout as t:
				raise Exception('Timeout request deploy container %s' % (container_name))

		containers = None

	def _append_containers(self, args, iq_response, ifrom):
		print(args)

#    def _send_deploy_minion(self, args, image, iq_response, ifrom, key_application, first):
#        if len(self.minions) == 1:
#            if first:
#                try:
#                    self._generate_image(
#                        path=args['path'], image_name=image, key_application=key_application, ito=self.jid_minions[0])
#                except Exception as e:
#                    raise Exception(e)
#
#            for number in range(int(args['total'])):
#                application_name = args['customer'] + \
#                    '_app-' + args['name'] + '-' + str(number)
#
#                thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[
#                                                        self.jid_minions[0], args['name'], key_application, application_name, ifrom])
#                thread_deploy_minion.daemon = True
#                thread_deploy_minion.start()
#        else:
#            minions_containers = self._pods_containers(int(args['total']))
#            iterator = 0
#            keys_minions = minions_containers.keys()
#
#            if first:
#                try:
#                    self._generate_image(
#                        path=args['path'], image_name=args['name'], key_application=key_application, ito=self.keys_minions[0])
#                except Exception as e:
#                    raise Exception(e)
#
#                for minion in keys_minions[1:]:
#                    try:
#                        self._load_image(
#                            path=self.path_images + args['name'] + '.tar.gz', ito=minion)
#                    except Exception as e:
#                        raise Exception(e)
#
#            def start_deploy(self, minion, number, iterator, key_application, name, ifrom):
#                for n in range(number):
#                    application_name = name + '-' + str(iterator)
#                    iterator += 1
#
#                    thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[
#                                                            minion, name, key_application, application_name, ifrom])
#                    thread_deploy_minion.daemon = True
#                    thread_deploy_minion.start()
#
#            for minion in keys_minions:
#                thread_start_deploy = threading.Thread(target=start_deploy, args=[
#                                                       self, minion, minions_containers[minion], iterator, key_application, args['name'], ifrom])
#                thread_start_deploy.daemon = True
#                thread_start_deploy.start()

	def get_number_containers(self, to):
		try:
			response = self.plugin['docker'].request_total_pods(
				ito=to, ifrom=self.boundjid)
			return response['docker']['total']
		except IqError as e:
			raise Exception(e.iq['error']['text'])
		except IqTimeout as t:
			raise Exception(t)

	def _handler_send_message(self, mto, body):
		self.send_message(mto=mto, mbody=body, mtype='chat')

	def action_container(self, action, container):
		for minion in self.jid_minions:
			try:
				containers = self.plugin['docker'].request_get_name_pods(ito=minion,
																		 ifrom=self.boundjid)

				if container in containers['docker']['name']:
					self.plugin['docker'].request_action_container(container=container,
																   action=action,
																   ito=minion,
																   ifrom=self.boundjid)

					return True
			except IqError as e:
				raise Exception(e.iq['error']['text'])
			except IqTimeout as t:
				raise Exception(t)

		raise Exception("Container " + container + " is not exists")

	def first_deploy(self, msg):
		options = msg['body'].split()

		try:
			application_name, customer, values = self._get_start_infos(options)
		except Exception as e:
			self._handler_send_message(msg['from'], unicode(e))
			return

		values['application_name'] = application_name
		values['customer'] = customer
		values['path'] = '/root/python-xmpp/go/hello_world/hello_world'
		#values['dns'] = 'lucas.com.br'

		print(application_name, customer, values)
		try:
			self._deploy_application(
				args=values, iq_response=None, ifrom=msg['from'])
		except IqError as e:
			self._handler_send_message(
				msg['from'], unicode(e.iq['error']['text']))
		except IqTimeout as t:
			self._handler_send_message(msg['from'], unicode(t))

#        logging.info('Start First Deploy')
#
#        if len(self.minions) == 0:
#            self._handler_send_message(
#                msg['from'], "Not have hosts to start the deploy")
#            return
#
#        try:
#            hostname, customer, pods, values_etcd = self._get_start_infos(
#                msg['body'].split('%'))
#        except Exception as e:
#            self._handler_send_message(msg['from'], unicode(e))
#
#        self._pods_containers(pods)
#
#        etcd_conn = Etcd(self.etcd_url, self.etcd_port)
#        endpoint = '/' + customer + '/' + hostname
#
#        try:
#            etcd_conn.write(endpoint, values_etcd)
#        except Exception as e:
#            self._handler_send_message(msg['from'], unicode(e))
#
#        try:
#            self._create_room(hostname)
#        except Exception as e:
#            self._handler_send_message(msg['from'], unicode(e))
#
#        if len(self.minions) == 1:
#            try:
#                self._generate_image(path='/root/python-xmpp/go/hello_world/hello_world',
#                                     image_name=customer + '_app-' + hostname, key_application=endpoint, ito=self.jid_minions[0])
#            except Exception as e:
#                self._handler_send_message(msg['from'], unicode(e))
#
#            for number in range(pods):
#                application_name = customer + '_app-' + \
#                    hostname + "-" + str(number)
#
#                thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[
#                    self.jid_minions[0], hostname, endpoint, application_name, msg['from']])
#                thread_deploy_minion.daemon = True
#                thread_deploy_minion.start()
#        else:
#            def start_deploy(self, key, number, iterator, endpoint, hostname, ifrom, customer):
#                for n in range(number):
#                    application_name = customer + '_app-' + \
#                        hostname + "-" + str(iterator)
#                    iterator += 1
#
#                    thread_deploy_minion = threading.Thread(target=self._requet_deploy_to_minion,
#                                                            args=[key, hostname, endpoint, application_name, ifrom])
#                    thread_deploy_minion.daemon = True
#                    thread_deploy_minion.start()
#
#            minions_pods = self._pods_containers(pods)
#            iterator = 0
#            keys = minions_pods.keys()
#
#            try:
#                self._generate_image(
#                    path='/root/python-xmpp/go/hello_world/hello_world', image_name=customer + '_app-' + hostname, key_application=endpoint, ito=keys[0])
#            except Exception as e:
#                self._handler_send_message(msg['from'], unicode(e))
#
#            print(keys[1:])
#            for key in keys[1:]:
#                try:
#                    self._load_image(
#                        path=self.path_images + customer + '_app-' + hostname + '.tar.gz', ito=key)
#                except Exception as e:
#                    self._handler_send_message(msg['from'], unicode(e))
#
#            for key in keys:
#                thread_start_deploy = threading.Thread(target=start_deploy,
#                                                       args=[self, key, minions_pods[key], iterator, endpoint, hostname, msg['from'], customer])
#                thread_start_deploy.daemon = True
#                thread_start_deploy.start()
#
#                iterator += minions_pods[key]

	def container_die(self, msg):
		options = msg['body'].split()

		containers = self.containers_per_minion[options[3]]
		for idx, container in enumerate(self.containers_per_minion[options[3]]):
			if container == options[2]:
				containers = containers[:idx] + containers[idx + 1:]

		self.containers_per_minion[options[3]] = containers

		try:
			self._deploy_container_die(application_name=options[1],
									container_name=options[2],
									minion=options[3],
									key_application=options[4])
		except Exception as e:
			logging.error('Error to create container die: %s' % unicode(e))

	def append_containers(self, msg):
		options = msg['body'].split()
		args = {}

		for op in options:
			if "--name" in op:
				args['application_name'] = op.replace("--name=", "").strip()
			if "--customer" in op:
				args['customer'] = op.replace("--customer=", "").strip()
			if "--total" in op:
				args['total_containers'] = int(
					op.replace("--total=", "").strip())

		if 'customer' not in args:
			self._handler_send_message(msg['from'], 'Customer is required')
			return

		if 'application_name' not in args:
			self._handler_send_message(
				msg['from'], 'Name of application is required')
			return

		if 'total_containers' not in args:
			self._handler_send_message(
				msg['from'], 'Total of containers is required')
			return

		try:
			self._append_deploy_application(
				args=args, iq_response=None, ifrom=msg['from'])
		except IqError as e:
			self._handler_send_message(
				msg['from'], unicode(e.iq['error']['text']))
		except IqTimeout as t:
			self._handler_send_message(msg['from'], unicode(t))
#		options = msg['body'].split('%')
#
#		if len(self.minions) == 0:
#			self._handler_send_message(
#				msg['from'], "Not have hosts to start the deploy")
#			return
#
#		for option in options:
#			if 'customer' in option:
#				customer = option.replace('customer=', '').strip()
#			if 'name' in option:
#				name = option.replace('name=', '').strip()
#			if 'number' in option:
#				number_containers = option.replace('number=', '').strip()
#
#		etcd_conn = Etcd(self.etcd_url, self.etcd_port)
#		key_customer = '/' + customer + '/' + name
#
#		if etcd_conn.key_exists(key_customer) is False:
#			self._handler_send_message(
#				msg['from'], 'Application "' + name + '" is not exists')
#			return
#
#		try:
#			values = ast.literal_eval(etcd_conn.read(key_customer))
#		except Exception as e:
#			self._handler_send_message(msg['from'], unicode(e))
#			return
#
#		iterator = values['pods'] + 1
#
#		values['pods'] = values['pods'] + int(number_containers)
#
#		try:
#			etcd_conn.update(key_customer, values)
#		except Exception as e:
#			self._handler_send_message(msg['from'], unicode(e))
#			return
#
#		if len(self.minions) == 1:
#			for number in range(int(number_containers)):
#				application_name = name + '-' + str(iterator)
#				iterator += 1
#
#				thread_deploy_append_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[
#															   self.jid_minions[0], name, key_customer, application_name, msg['from']])
#				thread_deploy_append_minion.daemon = True
#				thread_deploy_append_minion.start()
#		else:
#			def start_deploy(self, key, number, iterator, endpoint, hostname, ifrom):
#				for n in range(number):
#					application_name = hostname + "-" + str(iterator)
#					iterator += 1
#
#					thread_deploy_append_minion = threading.Thread(target=self._requet_deploy_to_minion, args=[
#																   key, hostname, endpoint, application_name, ifrom])
#					thread_deploy_append_minion.daemon = True
#					thread_deploy_append_minion.start()
#
#		minions_pods = self._pods_containers(int(number_containers))
#		keys = minions_pods.keys()
#
#		for key in keys:
#			thread_start_deploy = threading.Thread(target=start_deploy, args=[
#												   self, key, minions_pods[key], iterator, key_customer, name, msg['from']])
#			thread_start_deploy.daemon = True
#			thread_start_deploy.start()
#
#			iterator += minions_pods[key]

	def _generate_image(self, path, image_name, key_application, ito):
		print(path, image_name, key_application, ito)
		try:
			self.plugin['docker'].request_generate_image(path=path,
														 name=image_name,
														 key=key_application,
														 ito=ito,
														 ifrom=self.boundjid)
		except IqError as e:
			raise Exception(e.iq['error']['text'])
		except IqTimeout as t:
			raise Exception("timeout generate image")

	def _load_image(self, path, ito):
		try:
			self.plugin['docker'].request_load_image(path=path,
													 ito=ito,
													 ifrom=self.boundjid)
		except IqError as e:
			raise Exception(e.iq['error']['text'])
		except IqTimeout as t:
			raise Exception("timeout load image")

	def _requet_deploy_to_minion(self, ito, application_name, key_application, container_name, ifrom):
		try:
			self.plugin['docker'].request_minion_deploy(application_name=application_name,
														container_name=container_name,
														key_application=key_application,
														ito=ito,
														ifrom=self.boundjid,
														timeout=120)

			# self.plugin['docker'].request_first_deploy(ito=ito,
			#                                           ifrom=self.boundjid,
			#                                           name=application_name,
			#                                           key=key_application,
			#                                           user=container_name)

			print(ito)
			print(self.containers_per_minion)

			if not bool(self.containers_per_minion):
				self.containers_per_minion[ito] = [container_name]
			else:
				self.containers_per_minion[ito].append(container_name)

			self._handler_send_message(ifrom, 'success deploy container ' + container_name)
		except IqError as e:
			self._handler_send_message(ifrom, e.iq['error']['text'])
		except IqTimeout as t:
			self._handler_send_message(
				ifrom, 'timeout container ' + container_name)

	def _pods_containers(self, pods):
		minions_pods = {}
		list_pods = []
		minions_count = {}
		idx = 0
		check_iquals = True

		for minion in self.jid_minions:
			try:
				response = self.plugin['docker'].request_total_pods(
					ito=minion, ifrom=self.boundjid)

				if len(response['docker']['total'].strip()) > 0:
					total = int(response['docker']['total'])
					list_pods.append(total)
				else:
					list_pods.append(0)

				if not minions_count:
					minions_count[idx] = {'total': total, 'minion': minion}
				else:
					for count in minions_count.keys():
						if minions_count[count]['total'] == total or minions_count[count]['total'] < total:
							minions_count[idx] = {
								'total': total, 'minion': minion}
						else:
							minions_count[idx] = minions_count[count]
							minions_count[count] = {
								'total': total, 'minion': minion}

				idx += 1
			except IqError as e:
				raise Exception(e.iq['error']['text'])
			except IqTimeout as t:
				raise Exception(t)

		if len(list_pods) > 1:
			check_iquals = all(list_pods[:1] == elem for elem in list_pods)

		total_minions = len(self.jid_minions)

		if pods == 1:
			if check_iquals:
				minions_pods[self.jid_minions[0]] = pods
			else:
				minions_pods[minions_count[0]['minion']] = pods
		else:
			if check_iquals:
				for minion in self.jid_minions:
					minions_pods[minion] = pods / total_minions

				if pods % total_minions != 0:
					minions_pods[self.jid_minions[0]] += pods % total_minions
			else:
				for count in range(pods):
					if count > 0 and minions_count[0]['total'] > minions_count[1]['total']:
						for idx in minions_count.keys():
							x = idx + 1
							if x < len(minions_count.keys()) and minions_count[idx]['total'] > minions_count[x]['total']:
								total = minions_count[x]['total']
								minion = minions_count[x]['minion']
								minions_count[x] = {
									'minion': minions_count[idx]['minion'], 'total': minions_count[idx]['total']}
								minions_count[idx] = {
									'minion': minion, 'total': total}

					if minions_count[0]['minion'] not in minions_pods:
						minions_pods[minions_count[0]['minion']] = 1
					else:
						minions_pods[minions_count[0]['minion']] += 1

					minions_count[0]['total'] += 1

		return minions_pods

	def _get_start_infos(self, values):
		options = {'total_containers': 1}
		application_name = None
		customer = None

		for value in values:
			if "--cpus" in value:
				options['cpus'] = value.replace("--cpus=", "").strip()
			if "--memory" in value:
				options['memory'] = value.replace("--memory=", "").strip()
			if "--args" in value:
				dic = {}
				args = value.strip().replace(
					"--args[", "").replace("]", "").split(',')

				for arg in args:
					x = arg.replace('"', '').split(':')
					dic[x[0]] = x[1]

				options['args'] = dic
			if "--name" in value:
				application_name = value.replace("--name=", "").strip()
			if "--customer" in value:
				customer = value.replace("--customer=", "").strip()
			if "--total" in value:
				total_containers = int(value.replace("--total=", "").strip())
				options['total_containers'] = total_containers
			if "--ports" in value:
				options['ports'] = value.strip().replace("--ports=", "")
			if "--dns" in value:
				options['dns'] = value.strip().replace("--dns=", "")

		return application_name, customer, options

	def create_room(self, msg):
		args = msg['body'].split()
		self._create_room(args[1])

	def _create_room(self, name):
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

		self.add_event_handler("muc::%s::got_online" %
							   self.room, self.muc_online)
		self.add_event_handler("muc::%s::got_offline" %
							   self.room, self.muc_offline)

	def muc_online(self, presence):
		if len(presence['muc']['nick'].strip()) > 0:
			if presence['muc']['nick'] != self.nick:
				if presence['from'].bare.split('@')[0] == self.chat_minions:
					self.minions.append(presence['muc']['nick'])
					self.jid_minions.append(presence['muc']['jid'])

					try:
						containers = self.plugin['docker'].request_containers_minion(ito=presence['muc']['jid'],
																					ifrom=self.boundjid)

						if containers['docker']['message']:
							self.containers_per_minion[presence['muc']['jid']] = containers['docker']['message'].split(',')

					except IqError as e:
						logging.error("Could not get names of containers: %s" % e.iq['error']['text'])
					except IqTimeout as t:
						logging.error("Timeout to get names of containers: %s" % t)

				self.send_message(mto=presence['from'].bare,
								mbody="Ola Trouxa, %s %s" % (presence['muc']['role'], presence['muc']['nick']),
								mtype='groupchat')


		print(self.containers_per_minion)

	def muc_offline(self, presence):
		if presence['muc']['nick'] != self.nick:
			if presence['muc']['nick'] in self.minions:
				minion = presence['muc']['jid']
				logging.info('Minion Down %s' % (minion))

				self.minions.remove(presence['muc']['nick'])
				self.jid_minions.remove(presence['muc']['jid'])
				#del[presence['muc']['jid']]

				print(self.containers_per_minion)
				print(self.containers_per_minion[presence['muc']['jid']])
				thread_minion_die = threading.Thread(target=self._deploy_minion_die, args=[self.containers_per_minion[presence['muc']['jid']]])
				thread_minion_die.daemon = True
				thread_minion_die.start()
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

	envs = os.environ.keys()

	if 'etcd_url' not in envs:
		sys.exit('url for etcd is not seated')

	if 'xmpp_url' not in envs:
		sys.exit('url for xmpp is not seated')

	if 'jid' not in envs:
		sys.exit('jid is not seated')

	if 'path_images' not in envs:
		sys.exit('paht of images is not seated')

	print(os.environ['etcd_url'])
	xmpp = Zeus(os.environ['jid'], 'totvs@123', os.environ['etcd_url'])
	xmpp.register_plugin('xep_0030')  # Service Discovery
	xmpp.register_plugin('xep_0004')  # Data Forms
	xmpp.register_plugin('xep_0059')
	xmpp.register_plugin('xep_0060')  # PubSub
	xmpp.register_plugin('xep_0045')
	xmpp.register_plugin('xep_0085')
	xmpp.register_plugin('xep_0071')
	xmpp.register_plugin('xep_0133')
	xmpp.register_plugin('xep_0050')
	xmpp.register_plugin('xep_0199')  # XMPP Ping
	xmpp.register_plugin('xep_0066')  # Out-of-band Data
	xmpp.register_plugin('docker')
	# xmpp.register_plugin('xep_0077') # In-band Registratio

	# test_ns = 'http://jabber.org/protocol/chatstates'
	# xmpp['xep_0030'].add_feature(test_ns)

	# xmpp['xep_0077'].force_registration = True

	if xmpp.connect(address=(os.environ['xmpp_url'], 5222)):
		# if xmpp.connect(address=('192.168.204.131', 5222)):
		xmpp.process(block=True)
		print("Done")
	else:
		print("Unable to connect.")
