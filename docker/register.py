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

		print(self.xmpp.default_ns)
		self.xmpp.registerHandler(
			Callback('Name of Pods',
								MatchXPath('{%s}iq/{jabber:iq:pods:name}query' % self.xmpp.default_ns),
								self._handle_name_of_pods))

		register_stanza_plugin(Iq, Docker)

	def request_get_name_pods(self, ito=None, ifrom=None):
		print(ito, ifrom)
		iq = self.xmpp.Iq()
		iq['type'] = 'get'
		iq['to'] = ito
		iq['from'] = ifrom
		iq['query'] = 'jabber:iq:pods:name'

		return iq.send(now=True)

	def response_get_name_pods(self, ito=None, ifrom=None, sucess=None, response=None, error=None):
		iq = self.xmpp.Iq()
		iq['to'] = ito
		iq['from'] = ifrom

		if sucess:
			query = ET.Element('{jabber:iq:pods:name}query')
			result = ET.Element('pods')
			result.text = response
			query.append(result)

			iq['type'] = 'result'
			iq.append(query)
		else:
			iq['query'] = 'jabber:iq:pods:name'
			iq['type'] = 'error'
			iq['error'] = 'cancel'
			iq['error']['text'] = unicode(error)
			
		iq.send(now=True)

	def _handle_name_of_pods(self, iq):
		print("CARALHO")
		self.xmpp.event('name_pods', iq)
