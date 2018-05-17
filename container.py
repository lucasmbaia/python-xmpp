#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import getpass
import socket
from optparse import OptionParser

import sleekxmpp
import ast
import subprocess
import os
import crypt

from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp import Iq
from etcdf import Etcd

if sys.version_info < (3, 0):
  reload(sys)
  sys.setdefaultencoding('utf8')
else:
  raw_input = input

class ClientDocker(sleekxmpp.ClientXMPP):
  def __init__(self, jid, password, room):
    sleekxmpp.ClientXMPP.__init__(self, jid, password)
    self.room = room + '@conference.localhost'
    self.nick = self.boundjid.user
    self.add_event_handler("session_start", self.start)

  def start(self, event):
    self.send_presence()
    self.get_roster()
    
    try:
      room_exist = self.plugin['xep_0030'].get_info(jid=self.room)
    except IqError as e:
      logging.error("Could not create chat room: %s" % e.iq['error']['text'])
      self.disconnect()
    else:
      self.plugin['xep_0045'].joinMUC(self.room,
				      self.nick)

      logging.info("Chat room %s success!" % self.room)

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

  etcd_envs = {'etcd_url': '127.0.0.1', 'etcd_port': 2379}
  envs = os.environ.keys()

  if 'etcd_endpoint' not in envs:
    sys.exit('endpoint for etcd is not informed')

  if 'xmpp_url' not in envs:
    sys.exit('host of xmpp is not informed')

  if 'jid' not in envs:
    sys.exit('jid is not informed')

  if 'etcd_url' in envs:
    etcd_envs['etcd_url'] = os.environ['etcd_url']

  if 'etcd_port' in envs:
    etcd_envs['etcd_port'] = os.environ['etcd_port']

  etcd_connection = Etcd(etcd_envs['etcd_url'], etcd_envs['etcd_port'])

  try:
    values_etcd = ast.literal_eval(etcd_connection.read(os.environ['etcd_endpoint']))
  except Exception as e:
    sys.exit(unicode(e))

  password = crypt.decrypt_data(values_etcd['password'], 'id_rsa')
  endpoint = os.environ['etcd_endpoint'].split('/')

  xmpp = ClientDocker(os.environ['jid'], password, endpoint[len(endpoint) - 1])
  xmpp.register_plugin('xep_0030') #Service Discovery
  xmpp.register_plugin('xep_0004')
  xmpp.register_plugin('xep_0059')
  xmpp.register_plugin('xep_0060')
  xmpp.register_plugin('xep_0199')
  xmpp.register_plugin('xep_0066')
  xmpp.register_plugin('xep_0045')

  if xmpp.connect(address=(os.environ['xmpp_url'], 5222)):
    xmpp.process(block=True)
  else:
    print("Unable to connect.")
