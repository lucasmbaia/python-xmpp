import ast
import logging
import json
import socket

from etcdf import Etcd


class HAProxy:
    def __init__(self, etcd_url='127.0.0.1', etcd_port=2379):
        self.etcd_conn = Etcd(etcd_url, etcd_port)
        self.key = '/fc-haproxy/'
        self.key_http = {'80': 'app-http', '443': 'app-https'}
        self.appHTTP = 'app-http'
        self.appHTTPS = 'app-https'
        self.app_protocol_http = ['http', 'https']
        self.ports_http = ['80', '443']
	self.hostname = socket.gethostname()

    def generate_conf(self, application_name, container_name, ports_container, protocol, address_container, dns=None):
        logging.info('Generate conf to haproxy with application: %s, container: %s' % (
            application_name, container_name))

        if not application_name:
            raise Exception("Name of application is required")

        if not container_name:
            raise Exception("Name of container is required")

        if not ports_container:
            raise Exception("Ports of container is required")

        if not protocol:
            raise Exception("Protocol of container is required")

        if not address_container:
            raise Exception("Address of container is required")

        keys_ports = ports_container.keys()

        for key in keys_ports:
            if str(key) in self.ports_http:
                etcd_key = self.key + self.key_http[str(key)]

                try:
                    values = self._http_and_https(etcd_key=etcd_key,
                                                  application_name=str(application_name),
                                                  container_name=str(container_name),
                                                  address_container=address_container,
                                                  dns=str(dns),
                                                  ports_container=ports_container[key])

                    self.etcd_conn.write(etcd_key, json.dumps(values))
                except Exception as e:
                    raise Exception(e)

                keys_ports.remove(key)

        if len(keys_ports) > 0:
            try:
                values = self._tcp_and_udp(application_name=application_name,
                                           keys_ports=keys_ports,
                                           container_name=container_name,
                                           address_container=address_container,
                                           dns=dns,
                                           protocol=protocol,
					   ports_container=ports_container)

                self.etcd_conn.write(self.key + application_name, json.dumps(values))
            except Exception as e:
                raise Exception(e)

    def _tcp_and_udp(self, application_name, keys_ports, container_name, address_container, dns, protocol, ports_container):
        key_exists = self.etcd_conn.key_exists(self.key + application_name)

        if key_exists:
            try:
                values = ast.literal_eval(self.etcd_conn.read(self.key + application_name))

                for key in keys_ports:
                    for host in values['hosts']:
                        if 'portSRC' in host and host['portSRC'] == key:
                            for dst in ports_container[key]:
                                host['containers'].append({'name': container_name, 'address': address_container + ':' + dst, 'minion': self.hostname})

            except Exception as e:
                raise Exception(e)
        else:
            values = {'hosts': [], 'dns': dns}

            for key in keys_ports:
                containers = []

                for dst in ports_container[key]:
                    containers.append({'name': container_name, 'address': address_container + ':' + dst, 'minion': self.hostname})

                values['hosts'].append({'protocol': protocol[str(key)], 'portSRC': key, 'containers': containers})

	return values

    def _http_and_https(self, etcd_key, application_name, container_name, address_container, dns, ports_container):
        key_exists = self.etcd_conn.key_exists(etcd_key)

        if key_exists:
            try:
                contains = False
                values = ast.literal_eval(self.etcd_conn.read(etcd_key))

                for host in values['hosts']:
                    if 'name' in host and host['name'] == application_name:
                        contains = True
                        for dst in ports_container:
			    host['containers'].append({'name': container_name, 'address': address_container + ':' + dst, 'minion': self.hostname})

                if contains == False:
                    containers = []

                    for dst in ports_container:
			containers.append({'name': container_name, 'address': address_container + ':' + dst, 'minion': self.hostname})

                    values['hosts'].append({'name': application_name, 'containers': containers, 'dns': dns})

            except Exception as e:
                raise Exception(e)
        else:
            values = {'hosts': []}
            containers = []

            for dst in ports_container:
		containers.append({'name': container_name, 'address': address_container + ':' + dst, 'minion': self.hostname})

	    values['hosts'].append({'name': application_name, 'containers': containers, 'dns': dns, 'minion': self.hostname})

        return values

    def remove_container(self, application_name, container_name, protocol):
        if not application_name:
            raise Exception("Name of application is required")

        if not container_name:
            raise Exception("Name of container is required")

	keys_protocol = protocol.keys()
	keys_etcd = []

	for key in keys_protocol:
	    if str(key) in self.ports_http:
		if self.etcd_conn.key_exists(self.key + self.key_http[str(key)]) == False:
		    raise Exception("Key %s not exists in system haproxy" % self.key_http[str(key)])

		keys_etcd.append(self.key + self.key_http[str(key)])
		keys_protocol.remove(key)

	if len(keys_protocol) > 0:
	    if self.etcd_conn.key_exists(self.key + application_name) == False:
		raise Exception("Key of application %s not exists in system haproxy" % application_name)

	    keys_etcd.append(self.key + application_name)

	for key in keys_etcd:
            try:
		values = ast.literal_eval(self.etcd_conn.read(key))

		if 'hosts' in values:
		    for host in values['hosts']:
			if 'containers' in host:
			    containers = host['containers']

                            for idx, container in enumerate(containers):
	                        if container['name'] == container_name:
	                            containers = containers[:idx] + containers[idx + 1:]
    
	            host['containers'] = containers

		self.etcd_conn.write(key, json.dumps(values))
	    except Exception as e:
		raise Exception(e)

