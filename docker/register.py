import logging
import ssl

from sleekxmpp.stanza import StreamFeatures, Iq
from sleekxmpp.xmlstream import register_stanza_plugin, JID
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.docker import stanza, Docker
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID

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

	def _handle_name_of_pods(self, iq):
		self.xmpp.event('name_pods', iq)
