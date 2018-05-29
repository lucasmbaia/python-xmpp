import sys
import sleekxmpp

from sleekxmpp.exceptions import IqError, IqTimeout

class RegisterAccount(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
	sleekxmpp.ClientXMPP.__init__(self, jid, password)
	self.add_event_handler("session_start", self.start, threaded=True)
	self.add_event_handler("failed_auth", self.failed_auth)

    def start(self, event):
	self.send_presence()
	self.get_roster()
	self.disconnect()

    def failed_auth(self, event):
	self.register(self)

    def register(self):
	create = self.Iq()
	create['type'] = 'set'
	create['register']['username'] = self.boundjid.user
	create['register']['password'] = self.password

	try:
	    create.send(now=True)
	except IqError as e:
	    sys.exit(e.iq['error']['text'])
	    self.disconnect()
	except IqTimeout as t:
	    sys.exit(t)
	    self.disconnect()

if __name__ == '__main__':
    args = sys.argv

    if len(args) < 4:
	sys.exit("number of arguments is invalid")

    xmpp = RegisterAccount(args[2], args[3])
    xmpp.register_plugin('xep_0030')
    xmpp.register_plugin('xep_0004')
    xmpp.register_plugin('xep_0066')
    xmpp.register_plugin('xep_0077')
    xmpp.register_plugin('xep_0133')

    xmpp['xep_0077'].force_registration = True

    if xmpp.connect(address=(str(args[1]), 5222)):
	xmpp.process(block=True)
    else:
	sys.exit("error to connect xmpp server")
