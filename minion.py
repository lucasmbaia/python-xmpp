#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
import socket
from optparse import OptionParser
import threading
import json
import time

import sleekxmpp
import ast
import subprocess
import os
import Queue
import multiprocessing

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.xmlstream import ET, StanzaBase, register_stanza_plugin
from sleekxmpp.plugins.xep_0077.stanza import Register
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp.xmlstream.matcher.stanzapath import StanzaPath
from sleekxmpp.xmlstream.matcher.xmlmask import MatchXMLMask
from sleekxmpp import Iq
from etcdf import Etcd
from dockerf import DockerCommands
from haproxyf import HAProxy
from events import Channel
from sleekxmpp.plugins.docker.stanza import Docker
from sleekxmpp.plugins.docker.register import DOCKER
from multiprocessing.pool import ThreadPool

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


class Minion(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, etcd_url):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.chat_minions = 'minions'
        self.range_ports = range(10000, 10100)
        self.etcd_url = etcd_url
        self.etcd_port = 2379
        self.hostname = socket.gethostname()
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("name_pods", self._handler_docker)
        self.docker_process = Channel(docker_process=True)
	self.docker_commands = DockerCommands(etcd_url=self.etcd_url, etcd_port=self.etcd_port)
	self.haproxy = HAProxy(etcd_url=self.etcd_url, etcd_port=self.etcd_port)
	self.etcd_conn = Etcd(self.etcd_url, self.etcd_port)
        self.pod_deploy_start = []
        self.container_deploy_start = []
        self.channel_connections = {}
        self.minion_containers = []
        self.retry_deploy_container = {}

    def start(self, event):
        self.send_presence()
        self.get_roster()
        global form

        self.room = 'minions@conference.localhost'
        self.nick = self.boundjid.user

        try:
            room_exist = self.plugin['xep_0030'].get_info(jid=self.room)
        except IqError as e:
            if e.condition == 'item-not-found':
                self.plugin['xep_0045'].joinMUC(self.room,
                                                self.nick,
                                                wait=True)

                form = self.plugin['xep_0045'].getRoomConfig(self.room)
                form.set_values({'muc#roomconfig_persistentroom': 1,
                                 'muc#roomconfig_passwordprotectedroom': 0,
                                 'muc#roomconfig_publicroom': 1,
                                 'muc#roomconfig_roomdesc': 'TESTE!'})

                try:
                    self.plugin['xep_0045'].configureRoom(self.room, form=form)
                    logging.info("Chat room %s success created!" % self.room)
                except IqError as e:
                    logging.error("Could not create chat room: %s" %
                                  e.iq['error']['text'])

                    self.disconnect()
            else:
                logging.error("Could not create chat room: %s" %
                              e.iq['error']['text'])

                self.disconnect()
        else:
            self.plugin['xep_0045'].joinMUC(self.room,
                                            self.nick)

            logging.info("Chat room %s success created!" % self.room)

        self.add_event_handler("muc::%s::got_online" %
                               self.room, self.muc_online)
        containers = self._handler_name_containers()

        if containers is not None:
            self.minion_containers = containers

        print(self.minion_containers)

        self.channel_connections['die'] = Channel(server_process=self.docker_process,
                                                  pod_id='die', target=self._check_container_die)

        self.channel_connections['die'].register(
            self.docker_process.public_address(), self._check_container_die)

        print("PASSOU")

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            option = msg['body'].split()[0]
            print(option)

        if msg['type'] in ('groupchat', 'normal'):
            print(msg['body'])

    def _handler_docker(self, iq):
        print(iq)
        if iq['id'] == 'name-pods':
            try:
                names = self._handler_name_containers()

                if names is None:
                    name = ''

                self.plugin['docker'].response_get_name_pods(ito=iq['from'],
                                                             ifrom=self.boundjid,
                                                             success=True,
                                                             response=','.join(str(s) for s in names))
            except Exception as e:
                self.plugin['docker'].response_get_name_pods(ito=iq['from'],
                                                             ifrom=self.boundjid,
                                                             success=False,
                                                             error=unicode(e))

        if iq['id'] == 'total-pods':
            try:
                total = self._handler_total_containers()
                self.plugin['docker'].response_total_pods(ito=iq['from'],
                                                          ifrom=self.boundjid,
                                                          success=True,
                                                          response=total)
            except Exception as e:
                self.plugin['docker'].response_total_pods(ito=iq['from'],
                                                          ifrom=self.boundjid,
                                                          success=False,
                                                          response=unicode(e))

        if 'first-deploy' in iq['id']:
            pod_name = iq['docker']['user']
            key_etcd = iq['docker']['key']
            application_name = iq['docker']['name']

            try:
                result = self._handler_deploy(iq['from'],
                                              iq['docker']['name'],
                                              iq['docker']['key'],
                                              iq['docker']['user'],
                                              iq['id'])

            except Exception as e:
                self.plugin['docker'].response_first_deploy(ito=iq['from'],
                                                            ifrom=self.boundjid,
                                                            iq_id=iq['id'],
                                                            success=False,
                                                            error=unicode(e))

        if 'action-container' in iq['id']:
            container = iq['docker']['name']
            action = iq['docker']['action']

            if action == "resume":
                action = "unpause"

            try:
                response = self._exec_action_container(action, container)
                self.plugin['docker'].response_action_container(iq_response=iq['id'],
                                                                ito=iq['from'],
                                                                ifrom=self.boundjid,
                                                                success=True,
                                                                response=container)
            except Exception as e:
                self.plugin['docker'].response_action_container(iq_response=iq['id'],
                                                                ito=iq['from'],
                                                                ifrom=self.boundjid,
                                                                success=False,
                                                                error=unicode(e))

        if 'generate-image' in iq['id']:
            path = iq['docker']['path']
            image_name = iq['docker']['name']
            key = iq['docker']['key']

            try:
                response = self._generate_image(
                    path=path, image_name=image_name, key=key, iq_response=iq['id'], ifrom=iq['from'])
            except Exception as e:
                self.plugin['docker'].response_generate_image(iq_response=iq['id'],
                                                              ito=iq['from'],
                                                              ifrom=self.boundjid,
                                                              success=False,
                                                              error=unicode(e))

        if 'load-image' in iq['id']:
            path = iq['docker']['path']

            try:
                response = self._load_image(path=path)

                self.plugin['docker'].response_load_image(iq_response=iq['id'],
                                                          ito=iq['from'],
                                                          ifrom=self.boundjid,
                                                          success=True,
                                                          response=path)
            except Exception as e:
                self.plugin['docker'].response_load_image(iq_response=iq['id'],
                                                          ito=iq['from'],
                                                          ifrom=self.boundjid,
                                                          success=False,
                                                          error=unicode(e))

    def _check_container_die(self, event):
        dic_event = json.loads(event)
        container_name = dic_event['Actor']['Attributes']['name']

        print(container_name)
        if container_name in self.minion_containers:
            if container_name not in self.retry_deploy_container:
                self.retry_deploy_container[container_name] = 0

            if self.retry_deploy_container[container_name] < 3:
                image = dic_event['Actor']['Attributes']['image']
                cn = container_name.split('_app-')

                customer = cn[0]
                application_name = '-'.join(cn[1].split('-')[:-1])

                print(customer, application_name)
                etcd_key = '/' + customer + '/' + application_name

                self._thread_generate_container_die(
                    application_name=application_name, container_name=container_name, etcd_key=etcd_key)
                #self.retry_deploy_container[container_name] += 1
                #tcd = multiprocessing.Process(target=self._thread_generate_container_die, args=(application_name, container_name, etcd_key,))
                #tcd.daemon = True
                # tcd.start()
            else:
                print("JA DEU A PARADA")
                del self.minion_containers[container_name]

    def _thread_generate_container_die(self, application_name, container_name, etcd_key):
        print("foi")
        etcd_conn = Etcd(self.etcd_url, self.etcd_port)
        args = {'container_name': str(container_name), 'application_name': str(
            application_name), 'key': str(etcd_key), 'protocol': {'8080': 'http'}, 'dns': 'lucas.com.br'}

        print(etcd_key)
        try:
            values = ast.literal_eval(etcd_conn.read(etcd_key))
        except Exception as e:
            print(e)
            return

        print(values)
        try:
            command = self.docker_command(
                container_name=str(container_name), values=values)
        except Exception as e:
            print(e)
            return

        print(command, values, self.channel_connections)
        self.container_deploy_start.append(container_name)
        self.channel_connections[container_name] = Channel(server_process=self.docker_process,
                                                           pod_id=container_name,
                                                           pod_args=args)

        self.channel_connections[container_name].register(self.docker_process.public_address(),
                                                          self._generate_container_die)

        try:
            docker_deploy = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = docker_deploy.communicate()

            if err:
                self.channel_connections[container_name].close()
        except OSError as e:
            self.channel_connections[container_name].close()

        # return

    def _generate_container_die(self, event):
        dic_event = json.loads(event)

        if 'status' in dic_event['docker']:
            if 'start' in dic_event['docker']['status']:
                print("PORAAAA", dic_event)
                print("CONTAINER NAME", dic_event['args']['container_name'])
                self.channel_connections[dic_event['args']
                                         ['container_name']].close()

    def _load_image(self, path):
        infos = path.split('/')
        image = infos[len(infos) - 1:][0].split('.')[0]

        try:
            exists = self._handler_exists_image(image)
        except Exception as e:
            raise Exception(e)

        if exists is False:
            try:
                self._handler_load_image(path)
            except Exception as e:
                raise Exception(e)

    def _generate_image(self, path, image_name, key, iq_response, ifrom):
        command = ['docker', 'run', '-t', '-i', '--rm']
        etcd_conn = Etcd(self.etcd_url, self.etcd_port)

        try:
            values = ast.literal_eval(etcd_conn.read(key))
        except Exception as e:
            raise Exception(e)

        if 'args' in values:
            for x in values['args']:
                command.append('--env')
                command.append(x + '=' + values['args'][x])

        if 'ports_dst' in values:
            command.append('-P')
            for x in values['ports_dst']:
                command.append('--expose=' + x)

        command.append('--name')
        command.append(image_name)

        command.append('--cpus=0.1')
        command.append('--memory=15m')
        command.append('-d')
        command.append('alpine')

        self.pod_deploy_start.append(image_name)
        args = {'from': str(ifrom), 'container': str(image_name), 'path': str(
                path), 'from': str(ifrom), 'iq_response': str(iq_response)}
        self.channel_connections[image_name] = Channel(server_process=self.docker_process,
                                                       pod_id=image_name,
                                                       pod_args=args)

        self.channel_connections[image_name].register(
            self.docker_process.public_address(), self._handler_check_generate_image)

        print(command)
        try:
            response = self.exec_command(command)
        except Exception as e:
            self.channel_connections[image_name].close()
            raise Exception(e)

    def _handler_check_generate_image(self, event):
        dic_event = json.loads(event)
        container = None

        print(dic_event)
        if 'container' in dic_event['args']:
            container = dic_event['args']['container']

        def basic_commands(container, path):
            command = ['/usr/bin/sh', 'generate_image.sh',
                       container, path, 'v1', 'hello_world']

            print("GENERATE IMAGE")
            print(command)
            try:
                self.exec_command(command)
            except Exception as e:
                raise Exception(e)

        def check_image(self, args, container):
            if container is not None and container in self.pod_deploy_start:
                try:
                    basic_commands(container, args['path'])
                    self.plugin['docker'].response_generate_image(iq_response=args['iq_response'],
                                                                  ito=args['from'],
                                                                  ifrom=self.boundjid,
                                                                  success=True,
                                                                  response=container)
                except Exception as e:
                    print("ERRO PORRA", e)
                    self.plugin['docker'].response_generate_image(iq_response=args['iq_response'],
                                                                  ito=args['from'],
                                                                  ifrom=self.boundjid,
                                                                  success=False,
                                                                  error=unicode(e))

        if 'status' in dic_event['docker']:
            if dic_event['docker']['status'] == 'start':
                response = threading.Timer(
                    5, check_image, [self, dic_event['args'], container])
                response.daemon = True
                response.start()

            if 'die' in dic_event['docker']['status']:
                if container is not None:
                    if container in self.pod_deploy_start:
                        self.pod_deploy_start.remove(container)

                    self.plugin['docker'].response_generate_image(iq_response=dic_event['args']['iq_response'],
                                                                  ito=dic_event['args']['from'],
                                                                  ifrom=self.boundjid,
                                                                  success=False,
                                                                  error=unicode(e))
                    self.channel_connections[container].close()

    def _exec_action_container(self, action, container):
        command = ['docker', action, container]

        try:
            return self.exec_command(command)
        except Exception as e:
            raise Exception(e)

    def _deploy_container(self, ifrom, application_name, container_name, key_etcd, iq_response):
	args = {'from': str(ifrom), 'application_name': application_name, 'container_name': container_name, 'iq_response': iq_response}

	try:
	    values = ast.literal_eval(self.etcd_conn.read(key_etcd))
	except Exception as e:
	    raise Exception(e)

	args = {'from': str(ifrom), 'application_name': application_name, 'container_name': container_name, 'iq_response': iq_response, 'protocol': values['procotol'], 'dns': args['dns']}

	self.container_deploy_start(container_name)
	self.channel_connections[container_name] = Channel(server_process=self.docker_process,
							pod_id=container_name,
							pod_args=args)

	self.channel_connections[container_name].register(self.docker_process.public_address(), self._check_deploy_container)

	try:
	    self.docker_commands.deploy(container_name=container_name, infos_application=values)
	except Exception as e:
	    self.channel_connections[container_name].close()
	    raise Exception(e)

    def _check_deploy_container(self, event):
	ev = json.dumps(event)
	container_name = None

	if 'pod' in ev['args']:
	    container_name = ev['args']['pod']

	def haproxy(container_name, args):
	    dns = None

	    try:
		address_container = self.docker_commands.address_container(container_name)
	    except Exception as e:
		raise Exception(e)

	    try:
		ports_container = self.docker_commands.ports_container(container_name)
	    except Exception as e:
		raise Exception(e)

	    if 'dns' in args:
		dns = args['dns']

	    try:
		self.haproxy.generate_conf(application_name=args['application_name'], container_name=container_name, ports_container=ports_container, protocol=args['procotol'], address_container=address_container, dns=dns)
	    except Exception as e:
		raise Exception(e)

	def send_response(self, args, container_name):
	    if container_name is not None and container_name in self.container_deploy_start:
		try:
		    haproxy(container_name, args)

		    self.plugin['docker'].response_first_deploy(ito=args['from'],
								ifrom=self.boundjid,
								iq_id=args['iq_response'],
								success=True,
								response='OK')
		except Exception as e:
		    self.plugin['docker'].response_first_deploy(ito=args['from'],
								ifrom=self.boundjid,
								iq_id=args['iq_response'],
								success=False,
								error=unicode(e))

		self.container_deploy_start.remove(container_name)
		self.channel_connections[container_name].close()


	if 'status' in ev['docker']:
	    if 'start' in ev['docker']['status']:
		resp = threading.Timer(10, send_response, [self, ev['args'], container_name])
		resp.daemon = True
		resp.start()

	    if 'die' in ev['docker']['status']:
		if container_name is not None:
		    if container_name in self.container_deploy_start:
			self.container_deploy_start.remove(container_name)

		    self.plugin['docker'].response_first_deploy(ito=ev['args']['from'],
								ifrom=self.boundjid,
								iq_id=ev['args']['iq_response'],
								success=False,
								error='Error to create ' + container_name)
		    self.channel_connections[container_name].close()

    def _handler_deploy(self, ifrom, name, key, user, iq_id):
        ports_service = []
        etcd_conn = Etcd(self.etcd_url, self.etcd_port)

        try:
            values = ast.literal_eval(etcd_conn.read(key))
        except Exception as e:
            raise Exception(e)

        try:
            command = self.docker_command(container_name=user, values=values)
        except Exception as e:
            raise Exception(e)

        self.pod_deploy_start.append(user)
        args = {'from': str(ifrom), 'pod': str(user), 'key': str(key), 'application_name': str(name), 'iq_id': str(iq_id), 'protocol': {'443': 'https', '8080': 'http'}, 'dns': 'lucas.com.br'}
        self.channel_connections[user] = Channel(server_process=self.docker_process,
                                                 pod_id=user,
                                                 pod_args=args)

        self.channel_connections[user].register(
            self.docker_process.public_address(), self._handler_check_deploy)

        print(args)
        print(command)
        try:
            docker_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = docker_process.communicate()

            if out:
                return out
            if err:
                self.channel_connections[user].close()
                raise Exception(err.strip())
        except OSError as e:
            self.channel_connections[user].close()
            raise Exception(e)

    def _handler_check_deploy(self, event):
        # print(event)
        dic_event = json.loads(event)
        pod = None

        if 'pod' in dic_event['args']:
            pod = dic_event['args']['pod']

        def haproxy(container, etcd_url, etcd_port, args):
            ports = {}
            #values = {}
            etcd_conn = Etcd(etcd_url, etcd_port)
            command_address = ['docker', 'inspect', '-f',
                               '"{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"', container]
            command_ports = [
                "docker", "inspect", "--format='{{range $p, $conf := .NetworkSettings.Ports}}{{$p}}:{{(index $conf 0).HostPort}}-{{end}}'", container]

	    print("***************************************HAPROXY**********************************")
            try:
                ip_container = self.exec_command(
                    command_address).strip().replace("'", "").replace('"', '')
            except Exception as e:
                raise Exception(e)

            try:
                ports_container = self.exec_command(
                    command_ports).strip().replace("'", "")
            except Exception as e:
                raise Exception(e)

	    print(ip_container, ports_container)
            if ports_container:
                p = ports_container.split('-')
                p.pop()

                for x in p:
                    aux = x.split('/tcp:')
                    src = aux[0]
                    dst = aux[1]

                    if src in ports:
                        ports[src].append(dst)
                    else:
                        ports[src] = [dst]

	    print(ports)
            key_exists = etcd_conn.key_exists(
                '/haproxy/' + args['application_name'])
            keys = ports.keys()

            print(key_exists)
            print("ARGS: ", args)
            print('/haproxy/' + args['application_name'])

            if key_exists:
                try:
                    values = ast.literal_eval(etcd_conn.read(
                        '/haproxy/' + args['application_name']))

                    print("VALUES: ", values)
                    for key in keys:
                        for x in values['hosts']:
                            if 'portSRC' in x and x['portSRC'] == key:
                                for dst in ports[key]:
				    x['containers'].append({'name': container, 'address': ip_container + ":" + dst})
                                    #x['address'].append(ip_container + ":" + dst)

                except Exception as e:
                    raise Exception(e)
            else:
                values = {'hosts': [], 'dns': args['dns']}

		print("KEYS CARALHO: ", keys)
                for key in keys:
		    print("KEY: ", key)
                    containers = []

                    for dst in ports[key]:
			print("DST: ", dst)
			containers.append({'name': container, 'address': ip_container + ":" + dst})
                        #address.append(ip_container + ":" + dst)

		    print(containers)
                    #values['hosts'].append({'protocol': args['protocol'][key], 'portSRC': key, 'address': address})
                    values['hosts'].append({'protocol': args['protocol'][key], 'portSRC': key, 'containers': containers})

            print(values)
            print(ports)
            print(ip_container)

            try:
                etcd_conn.write(
                    '/haproxy/' + args['application_name'], json.dumps(values))
            except Exception as e:
                raise Exception(e)

            return True

        def send_response(self, args, pod):
            if pod is not None and pod in self.pod_deploy_start:
                try:
                    haproxy(pod, self.etcd_url, self.etcd_port, args)
                    self.plugin['docker'].response_first_deploy(ito=args['from'],
                                                                ifrom=self.boundjid,
                                                                iq_id=args['iq_id'],
                                                                success=True,
                                                                response='OK')
                    self.minion_containers.append(pod)
                except Exception as e:
                    self.plugin['docker'].response_first_deploy(ito=args['from'],
                                                                ifrom=self.boundjid,
                                                                iq_id=args['iq_id'],
                                                                success=False,
                                                                error=unicode(e))

                self.pod_deploy_start.remove(pod)
                self.channel_connections[pod].close()

        if 'status' in dic_event['docker']:
            if 'start' in dic_event['docker']['status']:
                response = threading.Timer(
                    10, send_response, [self, dic_event['args'], pod])
                response.daemon = True
                response.start()

            if 'die' in dic_event['docker']['status']:
                if pod is not None:
                    if pod in self.pod_deploy_start:
                        self.pod_deploy_start.remove(pod)

                    self.plugin['docker'].response_first_deploy(ito=dic_event['args']['from'],
                                                                ifrom=self.boundjid,
                                                                iq_id=dic_event['args']['iq_id'],
                                                                success=False,
                                                                error='Error to create ' + pod)
                    self.channel_connections[pod].close()

    def _handler_exists_image(self, image):
        command = ['docker', 'images', '--format',
                   '"{{.Repository}}:{{.Tag}}"']

        try:
            response = self.exec_command(command)

            if response is not None:
                if image in response:
                    return True

                return False
            else:
                return False
        except Exception as e:
            raise Exception(e)

    def _handler_load_image(self, path):
        command = ['docker', 'load', '--input', path]

        print(command)
        try:
            response = self.exec_command(command)
            print(response)
        except Exception as e:
            raise Exception(e)

    def _handler_name_containers(self):
        command = ['docker', 'ps', '-a', '--format', '"{{.Names}}"']

        try:
            response = self.exec_command(command)

            if response is not None:
                response = response.replace('"', '').split('\n')[:-1]

            return response
        except Exception as e:
            raise Exception(e)

    def _handler_total_containers(self):
        command = ['docker', 'ps']
        count = -1

        print(command)
        try:
            response = self.exec_command(command).split('\n')

            for infos in response:
                if len(infos.strip()) > 0:
                    count += 1

            print(count)
            return str(count)
        except Exception as e:
            raise Exception(e)

    def exec_command(self, command):
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = process.communicate()

            if out:
                return out
            if err:
                raise Exception(err.strip())
        except OSError as e:
            raise Exception(e)

    def list_ports(self):
        command = ['docker', 'ps', '--format', '"{{.Ports}}"']
        ports = []

        try:
            docker_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = docker_process.communicate()

            if out:
                response = out.split('\n')

                for infos in response:
                    if len(infos.strip()) > 0:
                        port = infos.split(':')[1].split('->')[0]
                        ports.append(port)

            if err:
                raise Exception(err.strip())
        except OSError as e:
            raise Exception(e)
        except:
            raise Exception(sys.exc_info()[0])

        return ports

    def docker_command(self, container_name, values):
        command = ['docker', 'run', '--rm']

        if 'args' in values:
            for x in values['args']:
                command.append('--env')
                command.append(x + '=' + values['args'][x])

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
        if 'image' in values:
            command.append('-d')
            command.append(values['image'])
        else:
            raise Exception("image is empty")

        return command

    def muc_online(self, presence):
        if len(presence['muc']['nick'].strip()) > 0:
            if presence['muc']['nick'] != self.nick:
                self.send_message(mto=presence['from'].bare,
                                  mbody="Ola Trouxa, %s %s" % (
                    presence['muc']['role'], presence['muc']['nick']),
                    mtype='groupchat')

    def muc_offline(self, presence):
        if presence['muc']['nick'] != self.nick:
            if presence['muc']['nick'] in self.minions:
                print("Minion Down")
            else:
                print("Application Down")

            print(presence['muc']['nick'])


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

    envs = os.environ.keys()

    if 'etcd_url' not in envs:
        sys.exit('url for etcd is not seated')

    if 'xmpp_url' not in envs:
        sys.exit('url for xmpp is not seated')

    if 'jid' not in envs:
        sys.exit('jid is not seated')

    xmpp = Minion(os.environ['jid'], 'totvs@123', os.environ['etcd_url'])
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0059')
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0045')
    xmpp.register_plugin('xep_0085')
    xmpp.register_plugin('xep_0071')
    xmpp.register_plugin('xep_0199')  # XMPP Ping
    xmpp.register_plugin('xep_0066')  # Out-of-band Data
    xmpp.register_plugin('docker')

    # test_ns = 'http://jabber.org/protocol/chatstates'
    # xmpp['xep_0030'].add_feature(test_ns)

    if xmpp.connect(address=(os.environ['xmpp_url'], 5222)):
        # if xmpp.connect(address=('172.16.95.111', 5222)):
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
