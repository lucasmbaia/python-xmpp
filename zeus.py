#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
from optparse import OptionParser

import crypt
import sleekxmpp
import uuid

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.stanzabase import ElementBase, ET, JID
from sleekxmpp.xmlstream import ET, StanzaBase, register_stanza_plugin
from sleekxmpp.plugins.xep_0077.stanza import Register
from sleekxmpp.plugins.base import base_plugin
from sleekxmpp import Iq
from etcdf import Etcd
from sleekxmpp.plugins.docker.stanza import Docker
from sleekxmpp.plugins.docker.register import DOCKER


if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


class Containers(ElementBase):
    namespace = 'jabber:iq:containers'
    name = 'query'
    plugin_attrib = 'containers'
    interfaces = set(('total', 'result'))
    sub_interfaces = interfaces
    form_fields = set(('total', 'result'))


class DockerLocal(ElementBase):
    namespace = 'jabber:iq:docker'
    name = 'query'
    plugin_attrib = 'docker'
    interfaces = set(('containers', 'deploy', 'result'))
    sub_interfaces = interfaces
    form_fields = set(('containers', 'deploy', 'result'))


class Register(sleekxmpp.ClientXMPP):
    def __init__(self, domain, jid, password):
        super(Register, self).__init__(jid, password)
        self.register_plugin('xep_0030')
        self.register_plugin('xep_0004')
        self.register_plugin('xep_0066')
        self.register_plugin('xep_0077')
        #self.plugin['xep_0077'].force_registration = True
        self.add_event_handler("session_start", self.start, threaded=True)
        self.add_event_handler("register", self.register, threaded=True)

    def start(self, event):
        self.disconnect(wait=True)

    def run(self):
        self.connect(address=('172.16.95.111', 5222))
        self.process(threaded=True)

    def register(self, iq):
        create = self.Iq()
        create['type'] = 'set'
        create['register']['username'] = self.boundjid.user
        create['register']['password'] = self.password

        try:
            create.send(now=True)
            logging.info("Account created for %s" % self.boundjid)
        except IqError as e:
            logging.error("Could not register account: %s" %
                          e.iq['error']['text'])
        except IqTimeout:
            logging.error("No response from server.")


class Zeus(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.minions = []
        self.jid_minions = []
        self.minions_pods = {}
        self.chat_minions = 'minions'
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("name_pods", self.caralho)

        register_stanza_plugin(Iq, Containers)
        register_stanza_plugin(Iq, DockerLocal)

    def start(self, event):
        self.send_presence()
        self.get_roster()
        global form

        self.room = 'minions@conference.localhost'
        self.nick = self.boundjid.user

        rooms = self.plugin['xep_0030'].get_items(jid='conference.localhost')

        for room in rooms['disco_items']:
            if room['jid'] != self.room:
                self.plugin['xep_0045'].joinMUC(room['jid'],
                                                self.nick)

                self.add_event_handler("muc::%s::got_online" %
                                       room['jid'], self.muc_online)
                self.add_event_handler("muc::%s::got_offline" %
                                       room['jid'], self.muc_offline)
                logging.info("Chat room %s success!" % room['jid'])

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
        self.add_event_handler("muc::%s::got_offline" %
                               self.room, self.muc_offline)

    def message(self, msg):
        print("CHAT")
        if msg['type'] in ('chat', 'normal'):
            option = msg['body'].split()[0]

            if option == "help":
                self.help(msg)
            elif option == "deploy":
                self.first_deploy(msg)
            elif option == "register":
                try:
                    self.register(msg)
                except Exception as e:
                    self.send_message(mto=msg['from'],
                                      mbody=unicode(e),
                                      mtype='chat')

            elif option == "create_room":
                self.create_room(msg)
            else:
                print(option)
                self.send_message(mto=msg['from'],
                                  mbody='Invalid Option',
                                  mtype='chat')

        if msg['type'] in ('groupchat', 'normal'):
            print(msg['body'])

    def help(self, msg):
        custom_msg = self.Message()
        custom_msg[
            'body'] = 'Here&apos;s my .plan for today: 1. Add the following examples to XEP-0071: - ordered and unordered lists - more styles (e.g., indentation) 2. Kick back and relax'
        custom_msg['html'][
            'body'] = '<p>Here&apos;s my .plan for today:</p><ol><li>Add the following examples to XEP-0071:<ul><li>ordered and unordered lists</li><li>more styles (e.g., indentation)</li></ul></li><li>Kick back and relax</li></ol>'

        self.send_message(mto=msg['from'],
                          mbody=custom_msg['body'],
                          mhtml=custom_msg['html'],
                          mtype='chat')

    def get_number_containers(self, to):
        try:
            response = self.plugin['docker'].request_total_pods(
                ito=to, ifrom=self.boundjid)
            return response['docker']['total']
        except IqError as e:
            raise Exception(e.iq['error']['text'])
        except IqTimeout as t:
            raise Exception(t)

    def first_deploy(self, msg):
        if len(self.minions) == 0:
            raise Exception("Not have hosts to start the deploy")

        try:
            hostname, customer, pods, values_etcd = self._get_start_infos(
                msg['body'].split('%'))
        except Exception as e:
            raise Exception(e)

        random = str(uuid.uuid4())
        random = random.upper()
        random = replace("-", "")
        password = random[0:10]
        values_etcd['password'] = crypt.encrypt_data(password, 'id_rsa.pub')

        endpoint = '/' + customer + '/' + hostname

        try:
            etcd_conn.write(endpoint, values_etcd)
        except Exception as e:
            raise Exception(e)

        try:
            self._create_room(hostname)
        except Exception as e:
            raise Exception(e)

        if len(self.minions) == 1:
            for number in range(pods):
                application_name = hostname + "-" + str(number)

                create_user = Register(
                    self.boundjid.domain, application_name + "@" + self.boundjid.domain, password)
                create_user.run()

                try:
                    self.plugin['docker'].request_first_deploy(ito=self.jid_minions[0],
                                                               ifrom=self.boundjid,
                                                               name=hostname,
                                                               key=endpoint,
                                                               user=application_name)
                except IqError as e:
                    raise Exception(e.iq['error']['text'])
                except IqTimeout as t:
                    raise Exception(t)
        else:
            minions_pods = self._pods_containers(pods)

            keys = minions_pods.keys()

            for key in keys:
                for number in range(pods):
                    application_name = hostname + "-" + str(number)

                    create_user = Register(
                        self.boundjid.domain, application_name + "@" + self.boundjid.domain, password)
                    create_user.run()

                    try:
                        self.plugin['docker'].request_first_deploy(ito=minions_pods[key]['minion'],
                                                                   ifrom=self.boundjid,
                                                                   name=hostname,
                                                                   key=endpoint,
                                                                   user=application_name)
                    except IqError as e:
                        raise Exception(e.iq['error']['text'])
                    except IqTimeout as t:
                        raise Exception(t)

    def _pods_containers(self, pods):
        minions_pods = {}
        list_pods = []
        minions_count = {}

        for idx, minion in self.jid_minions:
            try:
                response = self.plugin['docker'].request_total_pods(
                    ito=minion, ifrom=self.boundjid)
                total = int(response['docker']['total'])
                list_pods.append(total)

                if not minions_count:
                    minions_count[idx] = {'total': total, 'minion': minion}
                else:
                    for count in minions_count:
                        if minions_count[count]['total'] == total or minions_count[count]['total'] < total:
                            minions_count[idx] = {
                                'total': total, 'minion': minion}
                        else:
                            minions_count[idx] = minions_count[count]
                            minions_count[count] = {
                                'total': total, 'minion': minion}

            except IqError as e:
                raise Exception(e.iq['error']['text'])
            except IqTimeout as t:
                raise Exception(t)

        check_iquals = all(list_pods[:1] == elem for elem in list_pods)
        total_minions = len(self.jid_minions)

        # if check_iquals:
        for minion in self.jid_minions:
            minions_pods[minion] = pods / total_minions

        if pods % total_minions != 0:
            minions_pods[self.jid_minions[:1]] += pods % total_minions

        # else:
            # if (minions_count.keys()[len(minions_count) - 1]['total'] - minions_count.keys()[0]) > pods:
            #pods_per_minion = pods / (total_minions - 2)

        return minions_pods

    def _get_start_infos(self, values):
        values_etcd = {'pods': 1}
        hostname = None
        customer = None
        pods = 1

        if "--name" not in values:
            raise Exception("Name of application is not informed")

        if "--customer" not in values:
            raise Exception("Name of customer is not informed")

        for value in values:
            if "--cpus" in value:
                values_etcd['cpus'] = value.replace("--cpus=", "").strip()
            if "--memory" in value:
                values_etcd['memory'] = value.replace("--memory=", "").strip()
            if "--args" in value:
                dic = {}
                args = value.strip().replace(
                    "--args[", "").replace("]", "").strip(',')

                for arg in args:
                    x = arg.split(':')
                    dic[x[0]] = x[1]

                values_etcd['args'] = dic
            if "--name" in value:
                hostname = value.replace("--name=", "").strip()
            if "--customer" in value:
                customer = value.replace("--customer=", "").strip()
            if "--pods" in value:
                pods = int(value.replace("--pods=", "").strip())
                values_etcd['pods'] = pods
            if "--port" in value:
                ports = value.strip().replace("--ports=", "").strip().split(',')
                values_etcd['ports_dst'] = ports
	    if "--image" in value:
		values_etcd['image'] = value.replace("--image=", "").strip()

        return hostname, customer, pods, values_etcd

    def deploy(self, msg):
        values_etcd = {'pods': 1}
        hostname = None
        customer = None
        pods = 1
        infos = msg['body'].split('%')

        for value in infos:
            if "--cpus" in value:
                values_etcd['cpus'] = value.replace("--cpus=", "").strip()
            if "--memory" in value:
                values_etcd['memory'] = value.replace("--memory=", "").strip()
            if "--args" in value:
                dic = {}
                args = value.strip().replace(
                    "--args[", "").replace("]", "").split(',')

                for arg in args:
                    x = arg.split(':')
                    dic[x[0]] = x[1]

                values_etcd['args'] = dic
            if "--name" in value:
                hostname = value.replace("--name=", "").strip()
            if "--customer" in value:
                customer = value.replace("--customer=", "").strip()
            if "--pods" in value:
                pods = int(value.replace("--pods=", "").strip())
                values_etcd['pods'] = pods
            if "--port" in value:
                port = value.replace("--port=", "").strip()
                values_etcd['port_dst'] = port

        password = crypt.encrypt_data('123456', 'id_rsa.pub')

        values_etcd['password'] = password
        values_etcd['image'] = 'minion'

        etcd_conn = Etcd('192.168.204.128', 2379)
        print(customer)
        print(hostname)

        endpoint = '/' + customer + '/' + hostname

        try:
            etcd_conn.write(endpoint, values_etcd)
        except Exception as e:
            raise Exception(e)

        self._create_room(hostname)

        # if len(self.jid_minions) == 1:
        print("VERME")

        for number in range(pods):
            print("TOMA NO CU CARALHO")
            print(self.jid_minions[0])
            user = hostname + '-' + str(number)
            create_user = Register(self.boundjid.domain,
                                   user + "@" + self.boundjid.domain, '123456')
            create_user.run()

            self.plugin['docker'].request_first_deploy(ito=self.jid_minions[0],
                                                       ifrom=self.boundjid,
                                                       name=hostname,
                                                       key=endpoint,
                                                       user=user)
            print(msg)

    def register(self, msg):
        args = msg['body'].split()

        if len(args) < 3:
            raise Exception("Number of args is invalid")

        create = Register(self.boundjid.domain,
                          args[1] + "@" + self.boundjid.domain, '123456')
        create.run()

    def create_room(self, msg):
        args = msg['body'].split()
        self._create_room(args[1])

    def _create_room(self, name):
        self.room = name + '@conference.localhost'

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
                                 'muc#roomconfig_roomdesc': 'TESTE!',
                                 'muc#roomconfig_roomname': self.room})

                try:
                    self.plugin['xep_0045'].configureRoom(self.room, form=form)
                    logging.info("Chat room %s success created!" % self.room)
                except IqError as e:
                    logging.error("Could not create chat room: %s" %
                                  e.iq['error']['text'])

            else:
                logging.error("Could not create chat room: %s" %
                              e.iq['error']['text'])

        else:
            self.plugin['xep_0045'].joinMUC(self.room,
                                            self.nick)

            logging.info("Chat room %s success created!" % self.room)

        self.add_event_handler("muc::%s::got_online" %
                               self.room, self.muc_online)
        self.add_event_handler("muc::%s::got_offline" %
                               self.room, self.muc_offline)

    def muc_online(self, presence):
        if len(presence['muc']['nick'].strip()) > 0:
            if presence['muc']['nick'] != self.nick:
                if presence['from'].bare.split('@')[0] == self.chat_minions:
                    self.minions.append(presence['muc']['nick'])
                    self.jid_minions.append(presence['muc']['jid'])

                    try:
                        response = self.plugin['docker'].request_get_name_pods(
                            ito=presence['muc']['jid'], ifrom=self.boundjid)
                        self.minions_pods = response['docker']['name'].split(
                            ',')
                        logging.info("Pods in %s: %s" %
                                     (presence['muc']['jid'], self.minions_pods))
                    except IqError as e:
                        logging.error(
                            "Could not get names of containers: %s" % e.iq['error']['text'])
                    #request_iq = self.Iq()
                    #request_iq['type'] = 'get'
                    #request_iq['id'] = 'containers'
                    #request_iq['to'] = presence['muc']['jid']
                    #request_iq['from'] = self.boundjid
                    #request_iq['query'] = 'jabber:iq:docker'

                    # try:
                    #	response = request_iq.send(now=True)
                    #	self.minions_pods = response['docker']['containers'].split(',')
                    #	logging.info("Pods in %s: %s" % (presence['muc']['jid'], self.minions_pods))
                    # except IqError as e:
                    #	logging.error("Could not get names of containers: %s" % e.iq['error']['text'])

                self.send_message(mto=presence['from'].bare,
                                  mbody="Ola Trouxa, %s %s" % (
                                      presence['muc']['role'], presence['muc']['nick']),
                                  mtype='groupchat')

    def caralho(self, iq):
        print("PORRAAAA")

    def muc_offline(self, presence):
        if presence['muc']['nick'] != self.nick:
            if presence['muc']['nick'] in self.minions:
                self.minions.remove(presence['muc']['nick'])
                self.jid_minions.remove(presence['muc']['jid'])
                del[presence['muc']['jid']]

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

    xmpp = Zeus('zeus@localhost', 'totvs@123')
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
    # xmpp.register_plugin('xep_0077') # In-band Registratio

    #test_ns = 'http://jabber.org/protocol/chatstates'
    # xmpp['xep_0030'].add_feature(test_ns)

    #xmpp['xep_0077'].force_registration = True

    if xmpp.connect(address=('172.16.95.111', 5222)):
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
