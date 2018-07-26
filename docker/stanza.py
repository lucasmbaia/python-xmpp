from __future__ import unicode_literals

from sleekxmpp.xmlstream import ElementBase, ET


class Docker(ElementBase):
    namespace = 'jabber:iq:docker'
    name = 'query'
    plugin_attrib = 'docker'
    interfaces = set(('name', 'total', 'action', 'message', 'request', 'key_application',
                      'deploy', 'name', 'key', 'user', 'path', 'container_name', 'etcd_key', 'dns'
                      'customer', 'application_name', 'total_containers', 'cpus', 'memory', 'ports'))
    sub_interfaces = interfaces
    form_fields = set(('name', 'total', 'action', 'message', 'request', 'key_application',
                       'deploy', 'name', 'key', 'user', 'path', 'container_name', 'etcd_key', 'dns'
                       'customer', 'application_name', 'total_containers', 'cpus', 'memory', 'ports'))
