from __future__ import unicode_literals

from sleekxmpp.xmlstream import ElementBase, ET

class Docker(ElementBase):
	namespace = 'jabber:iq:docker'
	name = 'query'
	plugin_attrib = 'docker'
	interfaces = set(('pods', 'total', 'names',
										'deploy', 'name', 'key', 'user'))
	sub_interfaces = interfaces
	form_fields = set(('pods', 'total', 'names',
										'deploy', 'name', 'key', 'user'))
