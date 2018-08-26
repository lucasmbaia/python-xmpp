import logging
import ssl

import logging
from sleekxmpp.stanza import StreamFeatures, Iq
from sleekxmpp.xmlstream import register_stanza_plugin, JID
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.docker import stanza, Docker
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.exceptions import IqError, IqTimeout


class DOCKER(BasePlugin):
	name = 'docker'
	description = 'Util of Docker'
	stanza = stanza
	dependencies = set(['xep_0030', 'xep_0004'])

	def plugin_init(self):
		self.xep = 'docker'

		self.xmpp.registerHandler(
			Callback('Docker',
					 MatchXPath('{%s}iq/{jabber:iq:docker}query' %
								self.xmpp.default_ns),
					 self._handle_name_of_pods))

		register_stanza_plugin(Iq, Docker)

	def _send_request(self, ito=None, ifrom=None, action=None, timeout=None, elements=None):
		logging.info('Send IQ to: %s, from: %s, action: %s, elements: %s' % (
			ito, ifrom, action, elements))

		iq = self.xmpp.Iq()

		if action is not None:
			iq['id'] = action + '-' + iq['id']

		iq['type'] = 'get'
		iq['to'] = ito
		iq['from'] = ifrom

		if elements is not None:
			query = ET.Element('{jabber:iq:docker}query')

			for key in elements.keys():
				element = ET.Element(key)
				element.text = str(elements[key])

				query.append(element)

			iq.append(query)
		else:
			iq['query'] = 'jabber:iq:docker'

		return iq.send(now=True, timeout=timeout)

	def _send_response(self, ito=None, ifrom=None, success=None, response=None, error=None, iq_response=None, element=None):
		iq = self.xmpp.Iq()
		iq['id'] = iq_response
		iq['to'] = ito
		iq['from'] = ifrom

		if success:
			logging.info('Send IQ response to: %s, from: %s, iq: %s, response: %s' % (
				ito, ifrom, iq_response, response))
			query = ET.Element('{jabber:iq:docker}query')

			if element is not None:
				result = ET.Element(element)
				result.text = response
				query.append(result)

			iq['type'] = 'result'
			iq.append(query)
		else:
			logging.error('Send IQ response to: %s, from: %s, iq: %s, error: %s' % (
				ito, ifrom, iq_response, error))
			iq['query'] = 'jabber:iq:docker'
			iq['type'] = 'error'
			iq['error'] = 'cancel'
			iq['error']['text'] = unicode(error)

		iq.send(now=True)

	def request_action_container(self, container, action, ito=None, ifrom=None):
		if not container:
			raise Exception("Container name is required")

		if not action:
			raise Exception("Container action is required")

		return self._send_request(ito=ito, ifrom=ifrom, action='action-container', elements={'name': container, 'action': action})

	def response_action_container(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def request_generate_image(self, path, name, key, ito=None, ifrom=None):
		if not path:
			raise Exception("Path of exec is required")

		if not name:
			raise Exception("Name of image is required")

		if not key:
			raise Exception("Key of etcd is required")

		return self._send_request(ito=ito, ifrom=ifrom, action='generate-image', timeout=120, elements={'path': path, 'name': name, 'key': key})

	def response_generate_image(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def request_load_image(self, path, ito=None, ifrom=None):
		if not path:
			raise Exception("Path of exec is required")

		return self._send_request(ito=ito, ifrom=ifrom, action='load-image', timeout=120, elements={'path': path})

	def response_load_image(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def resquet_master_deploy(self, customer, application_name, total_containers, ports, cpus, memory, path, ito, ifrom, args=None, timeout=None):
		if not customer:
			raise Exception("Customer of application is required")

		if not application_name:
			raise Exception("Name of application is required")

		if not total_containers:
			raise Exception("Total of containers is required")

		if not cpus:
			raise Exception("Total of cpus is required")

		if not memory:
			raise Exception("Total of memory is required")

		if not ports:
			raise Exception("Ports of application is required")

		if not path:
			raise Exception(
				"Path where contains the code of application is required")

		elements = {'customer': customer, 'application_name': application_name,
					'total_containers': total_containers, 'cpus': cpus, 'memory': memory, 'ports': ports, 'path': path}

		if args is not None:
			elements['args'] = args

		return self._send_request(ito=ito, ifrom=ifrom, action='master-first-deploy', timeout=timeout, elements=elements)

	def response_master_deploy(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def request_master_append_deploy(self, customer, application_name, total_containers, ito, ifrom, timeout=None):
		if not customer:
			raise Exception("Customer of application is required")

		if not application_name:
			raise Exception("Name of application is required")

		if not total_containers:
			raise Exception("Total of containers is required")

		elements = {'customer': customer, 'application_name': application_name,
					'total_containers': total_containers}

		return self._send_request(ito=ito, ifrom=ifrom, action='master-append-deploy', timeout=timeout, elements=elements)

	def response_master_append_deploy(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def request_minion_deploy(self, application_name, container_name, key_application, ito, ifrom, timeout=None):
		if not application_name:
			raise Exception("Name of application is required")

		if not container_name:
			raise Exception("Name of container is required")

		if not key_application:
			raise Exception("Name of etcd's key is required")

		elements = {'application_name': application_name,
					'container_name': container_name, 'key_application': key_application}

		return self._send_request(ito=ito, ifrom=ifrom, action='deploy-container', timeout=timeout, elements=elements)

	def response_minion_deploy(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
							error=error, iq_response=iq_response, element='message')

	def request_containers_minion(self, ito, ifrom, timeout=None):
		return self._send_request(ito=ito, ifrom=ifrom, action='name-containers', timeout=timeout, elements=None)

	def response_containers_minion(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
		self._send_response(ito=ito, ifrom=ifrom, success=success, response=response, error=error, iq_response=iq_response, element='message')

	def request_get_name_pods(self, ito=None, ifrom=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'name-pods'
		iq['type'] = 'get'
		iq['to'] = ito
		iq['from'] = ifrom
		iq['query'] = 'jabber:iq:docker'

		return iq.send(now=True)

	def response_get_name_pods(self, ito=None, ifrom=None, success=None, response=None, error=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'name-pods'
		iq['to'] = ito
		iq['from'] = ifrom

		if success:
			query = ET.Element('{jabber:iq:docker}query')
			result = ET.Element('name')
			result.text = response
			query.append(result)

			iq['type'] = 'result'
			iq.append(query)
		else:
			iq['query'] = 'jabber:iq:docker'
			iq['type'] = 'error'
			iq['error'] = 'cancel'
			iq['error']['text'] = unicode(error)

		iq.send(now=True)

	def request_total_pods(self, ito=None, ifrom=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'total-pods'
		iq['type'] = 'get'
		iq['to'] = ito
		iq['from'] = ifrom
		iq['query'] = 'jabber:iq:docker'

		return iq.send(now=True)

	def response_total_pods(self, ito=None, ifrom=None, success=None, response=None, error=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'total-pods'
		iq['to'] = ito
		iq['from'] = ifrom

		if success:
			query = ET.Element('{jabber:iq:docker}query')
			result = ET.Element('total')
			result.text = response
			query.append(result)

			iq['type'] = 'result'
			iq.append(query)
		else:
			iq['query'] = 'jabber:iq:docker'
			iq['type'] = 'error'
			iq['error'] = 'cancel'
			iq['error']['text'] = unicode(error)

		iq.send(now=True)

	def request_first_deploy(self, ito=None, ifrom=None, name=None, key=None, user=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'first-deploy-' + iq['id']
		iq['type'] = 'get'
		iq['to'] = ito
		iq['from'] = ifrom

		query = ET.Element('{jabber:iq:docker}query')
		req_name = ET.Element('name')
		req_name.text = name
		req_key = ET.Element('key')
		req_key.text = key
		req_user = ET.Element('user')
		req_user.text = user

		query.append(req_name)
		query.append(req_key)
		query.append(req_user)

		iq.append(query)

		return iq.send(now=True, timeout=120)

	def response_first_deploy(self, ito=None, ifrom=None, iq_id=None, success=None, response=None, error=None):
		iq = self.xmpp.Iq()
		iq['id'] = iq_id
		iq['to'] = ito
		iq['from'] = ifrom

		if success:
			query = ET.Element('{jabber:iq:docker}query')
			result = ET.Element('deploy')
			result.text = response
			query.append(result)

			iq['type'] = 'result'
			iq.append(query)
		else:
			iq['query'] = 'jabber:iq:docker'
			iq['type'] = 'error'
			iq['error'] = 'cancel'
			iq['error']['text'] = unicode(error)

		print(iq)
		iq.send(now=True)

	def _handle_name_of_pods(self, iq):
		self.xmpp.event('name_pods', iq)
