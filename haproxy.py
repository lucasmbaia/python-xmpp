import ast
import json

from etcdf import Etcd

class HAProxy:
	def __init__(self, etcd_url='127.0.0.1', etcd_port=2379):
		self.etcd_conn = Etcd(etcd_url, etcd_port)
		self.key = '/fc-haproxy/'

	def generate_conf(self, application_name, container_name, ports_container, protocol, address_container, dns=None)
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
		key_exists = self.etcd_conn.key_exists(self.key + application_name)

		if key_exists:
			try:
				values = ast.literal_eval(self.etcd_conn.read(self.key + application_name))

				for key in keys_ports:
					for host in values['hosts']:
						if 'portSRC' in host and host['portSRC'] == key:
							for dst in ports_container:
								host['address'].append(address_container + ':' + dst)

			except Exception as e:
				raise Exception(e)
		else:
			values = {'hosts': [], 'dns': dns}

			for key in keys_ports:
				address = []

				for dst in ports_container[key]:
					address.append(address_container + ':' + dst)

				values['hosts'].append({'protocol': protocol, 'portSRC': key, 'address': address_container})

		try:
			self.etcd_conn.write(self.key + application_name, json.dumps(values))

	def remove_container(self, application_name, container_name):
		if not application_name:
			raise Exception("Name of application is required")

		if not container_name:
			raise Exception("Name of container is required")

		key_exists = self.etcd_conn.key_exists(self.key + application_name)

		if key_exists:
			try:
				values = ast.literal_eval(self.etcd_conn.read(self.key + application_name))
		else:
			raise Exception("Key of application %s not exists in system haproxy" % application_name) 
