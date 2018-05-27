import socket
import threading


class ChannelThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.clients = []
        self.chan_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.chan_sock.bind(('', 0))
        _, self.port = self.chan_sock.getsockname()
        self.chan_sock.listen(5)
        self.daemon = True
        self.start()

    def run(self):
		while True:
			new_client = self.chan_sock.accept()
			print(new_client)
			if not new_client:
				break
			self.clients.append(new_client)

    def sendall(self, msg):
		for client in self.clients:
			client[0].sendall(msg)


class Channel(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.daemon = True
        self.channel_thread = ChannelThread()

    def public_address(self):
        return "tcp://%s:%d" % (socket.gethostname(), self.channel_thread.port)

    def register(self, channel_address, update_callback):
		host, s_port = channel_address.split("//")[-1].split(":")
		print(host, s_port)
		port = int(s_port)
		self.peer_chan_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.peer_chan_sock.connect((host, port))
		self._callback = update_callback
		self.start()

    def deal_with_message(self, msg):
        self._callback(msg)

    def run(self):
		print("MANOO")
		data = ""
		while True:
			new_data = self.peer_chan_sock.recv(1024)
			print(new_data)
			if not new_data:
                # connection reset by peer
				break
			data += new_data
			msgs = data.split("\n\n")
			if msgs[-1]:
				data = msgs.pop()
			for msg in msgs:
				self.deal_with_message(msg)

		print("DEU MERDA")

    def send_value(self, channel_value):
		print("TOMA NO CU")
		self.channel_thread.sendall("%s\n\n" % channel_value)

def pepeca(msg):
	print(msg)

if __name__ == '__main__':
	c1 = Channel()
	process = c1.public_address()

	c2 = Channel()
	c2.register(process, pepeca)

	c1.send_value("PORRA")
