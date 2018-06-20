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
	logging.info('Send IQ to: %s, from: %s, action: %s, elements: %s' % (ito, ifrom, action, elements))
        
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
                element.text = elements[key]
                query.append(element)

            iq.append(query)
        else:
            iq['query'] = 'jabber:iq:docker'

        iq.append(query)

        return iq.send(now=True, timeout=timeout)

    def _send_response(self, ito=None, ifrom=None, success=None, response=None, error=None, iq_response=None, element=None):
        iq = self.xmpp.Iq()
        iq['id'] = iq_response
        iq['to'] = ito
        iq['from'] = ifrom

        if success:
	    logging.info('Send IQ response to: %s, from: %s, iq: %s, response: %s' % (ito, ifrom, iq_response, response))
            query = ET.Element('{jabber:iq:docker}query')

            if element is not None:
                result = ET.Element(element)
                result.text = response
                query.append(result)

            iq['type'] = 'result'
            iq.append(query)
        else:
	    logging.error('Send IQ response to: %s, from: %s, iq: %s, error: %s' % (ito, ifrom, iq_response, error))
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

	print("CARALHO")
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
        print(success, response, error)
        self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
                            error=error, iq_response=iq_response, element='message')

    def request_load_image(self, path, ito=None, ifrom=None):
	if not path:
	    raise Exception("Path of exec is required")

	return self._send_request(ito=ito, ifrom=ifrom, action='load-image', timeout=120, elements={'path': path})

    def response_load_image(self, iq_response=None, ito=None, ifrom=None, success=None, response=None, error=None):
        self._send_response(ito=ito, ifrom=ifrom, success=success, response=response,
                            error=error, iq_response=iq_response, element='message')

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
