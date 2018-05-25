import logging
import ssl

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
								MatchXPath('{%s}iq/{jabber:iq:docker}query' % self.xmpp.default_ns),
								self._handle_name_of_pods))

		register_stanza_plugin(Iq, Docker)

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

		print(iq)
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
	
		print(iq)
		iq.send(now=True)

	def request_first_deploy(self, ito=None, ifrom=None, name=None, key=None, user=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'first-deploy'
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

		return iq.send(now=True)
 
	def response_first_deploy(self, ito=None, ifrom=None, success=None, response=None, error=None):
		iq = self.xmpp.Iq()
		iq['id'] = 'first-deploy'
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
			
		iq.send(now=True)

	def _handle_name_of_pods(self, iq):
		self.xmpp.event('name_pods', iq)
