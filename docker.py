import logging
import subprocess
import os
import ast

from etcdf import Etcd

class DockerCommands:
	def __init__(selfi, etcd_url='127.0.0.1', etcd_port=2379):
		self.etcd_url = etcd_url
		self.etcd_port = etcd_port
		self.image_base = "alpine"

		self.actions_container = ['stop', 'start', 'pause', 'resume']
		
		self.etcd_conn = Etcd(self.etcd_url, self.etcd_port)

	def _deploy_command(self, container_name, values, image_create=False):
		if image_create:
			command = ['docker', 'run', '--rm']
		else:
			command = ['docker', 'run', '-t', '-i', '--rm']

		if not container_name:
			raise Exception("Name of container is required")

		if 'image' not in values:
			raise Exception("Image of usege in deploy is required")

		if 'args' in values:
			for x in values['args']:
				command.append('--env')
				command.append(x + '=' + values['args']['x'])

		if 'ports_dst' in values:
			command.append('-P')
			for x in values['ports_dst']:
				command.append('--expose=' + x)

		command.append('--name')
		command.append(container_name)

		if 'cpus' in values:
			command.append('--cpus=' + values['cpus'])
		if 'memory' in values:
			command.append('--memory=' + values['memory'])

		command.append('-d')
		command.append(values['image'])

		return command

	def _exec_command(self, command):
		try:
			process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			(out, err) = process.communicate()

			if out:
				return out
			if err:
				raise Exception(err.strip())
		expose OSError as e:
			raise Exception(e)

	def total_containers(self):
		command = ['docker', 'ps', '|', 'wc', '-l']

		try:
			resp = self._exec_command(command)

			return str(int(resp) - 1)
		except Exception as e:
			raise Exception(e)

	def name_containers(self):
		command = ['docker', 'ps', '-a', '--format', '"{{.Names}}"']

		try:
			resp = self._exec_command(command)

			if resp is not None:
				resp = resp.replace('"', '').split('\n')[:-1]

			return response
		except Exception as e:
			raise Exception(e)

	def load_image(self, path):
		command = ['docker', 'load', '--input', path]

		try:
			self._exec_command(command)
		except Exception as e:
			raise Exception(e)

		return

	def exist_image(self, image_name):
		command = ['docker', 'images', '--format', '"{{.Repository}}:{{.Tag}}"']

		try:
			resp = self._exec_command(command)

			if resp is not None:
				if image_name in resp:
					return True

			return False
		except Exception as e:
			raise Exception(e)

	def action_container(self, container_name, action):
		if not action:
			raise Exception("Action of container is required")

		if not container_name:
			raise Exception("Name of container is required")

		if action not in self.actions_container:
			raise Exception("Action is Invalid")

		if action == 'resume':
			action = 'unpause'

		command = ['docker', action, container]

		try:
			resp = self._exec_command(command)
		except Exception as e:
			raise Exception(e)

	def remove_container(self, container_name):
		if not container_name:
			raise Exception("Name of container is required")

		command = ['docker', 'rm', '-f', container_name]

		try:
			self._exec_command(command)
		except Exception as e:
			raise Exception(e)

		return

	def deploy(self, container_name, infos_application, image_create=False):
		if not container_name:
			raise Exception("Name of container is required")

		if not infos_application:
			raise Exception("The parameters of application is required")

		try:
			command = self._deploy_command(container_name=container_name, values=infos_application, image_create=image_create)
		except Exception as e:
			raise Exception(e)

		try:
			resp = self._exec_command(command)

			return resp
		except Exception as e:
			raise Exception(e)

	def generate_image(self, image_name, args=None, ports=None, cpus="0.1", memory="10m"):
		if not image_name:
			raise Exception("Imane name is required")

		infos_image = {'image': self.image_base, 'cpus': cpus, 'memory': memory}

		if args is not None:
			infos_image['args'] = args

		if ports is not None:
			infos_image['ports_dst'] = ports

		try:
			resp = self.deploy(container_name=image_name, infos_application=infos_image, image_create=True)
		except Exception as e:
			raise Exception(e)

	def ports_container(self, container_name):
		if not container_name:
			raise Exception("Name of container is required")

		command = ["docker", "inspect", "--format='{{range $p, $conf := .NetworkSettings.Ports}}{{$p}}:{{(index $conf 0).HostPort}}-{{end}}'", container_name]
		ports_container = {}

		try:
			resp = self._exec_command(command)

			if resp is not None:
				ports = resp.split('-')
				ports.pop()

				for port in ports:
					p = port.split('/tcp:')

					src = aux[0]
					dst = aux[1]

					if src in ports_container:
						ports_container[src].append(dst)
					else:
						ports_container[src] = [dst]

			return ports_container
		except Exception as e:
			raise Exception(e)

	def address_container(self, container_name):
		if not container_name:
			raise Exception("Name of container is required")

		command = ['docker', 'inspect', '-f', '"{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', container_name]
		
		try:
			resp = self._exec_command(command)

			if resp is not None:
				return resp.strip().replace("'", "").replace('"', '')
		except Exception as e:
			raise Exception(e)
