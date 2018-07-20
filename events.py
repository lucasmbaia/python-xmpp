import subprocess
import sys
import os
import signal
import json
import socket
import threading
import time
import logging

from optparse import OptionParser


class SocketThread(threading.Thread):
	def __init__(self, docker_process=False, pod_id=None):
		threading.Thread.__init__(self)

		self.pods_id = {}
		self.pod_id = None
		self.pod_args = {}
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind(('', 0))
		self.sock.listen(100)
		self.daemon = True
		self.start()

		if docker_process:
			docker_thread = threading.Thread(target=self._docker_events)
			docker_thread.start()

	def run(self):
		try:
			while True:
				connection = self.sock.accept()[0]
				if not connection:
					break

				if self.pod_id is not None:
					self.pods_id[self.pod_id] = {
						'connection': connection, 'args': self.pod_args}
		finally:
			connection.close()

	def _docker_events(self):
		command = ['docker', 'events', '--format', '{{json .}}']

		try:
			docker_events = subprocess.Popen(
				command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

			while True:
				event = docker_events.stdout.readline()
				if docker_events.poll() is not None:
					break
				if event:
					self._event(event)

			rc = docker_events.poll()
			return rc
		except OSError as e:
			return unicode(e)
		# except (KeyboardInterrupt):
			# os.killpg(os.getpgid(docker_events.pid), signal.SIGTERM)

	def _event(self, event):
		dic_event = json.loads(event)

		if 'Actor' in dic_event:
			if 'Attributes' in dic_event['Actor']:
				if 'name' in dic_event['Actor']['Attributes']:
					pod_name = dic_event['Actor']['Attributes']['name']

					if pod_name in self.pods_id:
						args = self.pods_id[pod_name]['args']
						ev = json.dumps({'docker': dic_event, 'args': args})
						self.pods_id[pod_name]['connection'].sendall(ev)

		if 'status' in dic_event:
			if dic_event['status'] == 'die':
				if 'die' in self.pods_id:
					self.pods_id['die']['connection'].sendall(event)

	def public_address(self):
		return [socket.gethostname(), self.sock.getsockname()[1]]

	def register_pods(self, name=None, args=None):
		self.pod_id = name
		self.pod_args = args

	def unregister_pods(self, name):
		if name in self.pods_id:
			self.pods_id[name]['connection'].close()
			del self.pods_id[name]


class Channel(threading.Thread):
	def __init__(self, docker_process=False, server_process=None, pod_id=None, pod_args=None, group=None, target=None):
		threading.Thread.__init__(self)

		self.pod_id = pod_id
		self.pod_args = pod_args
		self.server_process = server_process
		self.daemon = True
		self.response = None
		self.channel_thread = SocketThread(docker_process=docker_process)
		self._return = None

	def public_address(self):
		return self.channel_thread.public_address()

	def register(self, server_address, callback):
		self.peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_process.channel_thread.register_pods(name=self.pod_id, args=self.pod_args)
		self.peer_sock.connect((server_address[0], server_address[1]))
		self._callback = callback
		self.start()

	def run(self):
		#if self._Thread__target is not None:
		#	self._return = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)

		try:
			while True:
				data = self.peer_sock.recv(1024)
				if not data:
					break

				self.response = self._callback(data)

				if self.response:
					self._return = self.response
					break
		except Exception as e:
			self._return = e
			self.server_process.channel_thread.unregister_pods(self.pod_id)
			self.peer_sock.close()
		finally:
			self.server_process.channel_thread.unregister_pods(self.pod_id)
			self.peer_sock.close()

	#def join(self):
	#	threading.Thread.join(self)
	#	return self._return

	def close(self):
		self.response = True
		self.server_process.channel_thread.unregister_pods(self.pod_id)
		self.peer_sock.close()

# def events(callback):
#	comand = ['docker', 'events', '--format', '{{json .}}']

#	try:
#		docker_events = subprocess.Popen(comand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

#		while True:
#			event = docker_events.stdout.readline()
#			if docker_events.poll() is not None:
#				break
#			if event:
#				print(event)

#		rc = docker_events.poll()
#		return rc
#	except OSError as e:
#		return unicode(e)
#	except (KeyboardInterrupt):
#		os.killpg(os.getpgid(docker_events.pid), signal.SIGTERM)


# def check_from(event):
#    print("PORRA")
#    print(event)


# def pod_die(event):
#    print(event)

#    return True

#def docker_event(event):
#	print(event)

#	raise Exception("chups")
	#return True

if __name__ == '__main__':
	optp = OptionParser()

	optp.add_option('-q', '--quiet', help='set logging to ERROR',
					action='store_const', dest='loglevel',
					const=logging.ERROR, default=logging.INFO)

	optp.add_option('-d', '--debug', help='set logging to DEBUG',
					action='store_const', dest='loglevel',
					const=logging.DEBUG, default=logging.INFO)

	optp.add_option('-v', '--verbose', help='set logging to COMM',
					action='store_const', dest='loglevel',
					const=5, default=logging.INFO)

	opts, args = optp.parse_args()
	logging.basicConfig(level=opts.loglevel,
						format='%(levelname)-8s %(message)s')

#	docker_process = Channel(docker_process=True)

#	die = Channel(server_process=docker_process, pod_id='die')
#	die.register(docker_process.public_address(), docker_event)
#	print(die.join())

	# s = Channel(docker_process=True)

	# die_process = Channel(server_process=s,
	#                      pod_id='die')

	# die_process.register(s.public_address(), pod_die)

	# s2 = Channel(server_process=s,
	#             pod_id='minion-python')

	# s2.register(s.public_address(), check_from)
