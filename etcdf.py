#!/usr/bin/env python

import etcd
import ast
import json
import time


class Etcd:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.client = etcd.Client(host=self.address, port=self.port)

    def write(self, endpoint, values):
        if not endpoint:
            raise Exception("Endpoint is empty")

        if not values:
            raise Exception("Value is empty")

        try:
            self.client.write(endpoint, values)
        except Exception as e:
            raise Exception(e)

    def read(self, endpoint):
        if not endpoint:
            raise Exception("Endpoint is empty")

        try:
            values = self.client.read(endpoint).value
        except etcd.EtcdKeyNotFound:
            raise Exception("Key %s not present anymore" % endpoint)

        return values

    def key_exists(self, endpoint):
	if not endpoint:
	    raise Exception("Endpoint is empty")

	try:
	    self.client.read(endpoint)
	except etcd.EtcdKeyNotFound:
	    return False

	return True

    def delete(self, endpoint):
        if not endpoint:
            raise Exception("Endpoint is empty")

        try:
            self.client.delete(endpoint)
        except etcd.EtcdKeyNotFound:
            raise Exception("Key %s not present anymore" % endpoint)

    def update(self, endpoint, replace_value):
		if not endpoint:
			raise Exception("Endpoint is empty")

		if not endpoint:
			raise Exception("Values to replace is empty")
		try:
			response = self.client.read(endpoint)
			response.value = replace_value
			self.client.update(response)
		except Exception as e:
			raise Exception(e)

    def watch(self, endpoint, callback=None):
        if not endpoint:
            raise Exception("Endpoint is empty")

        try:
			print("CARALHO")
			values = self.client.watch(endpoint)
			print(values)
			#callback(values.value)
        except etcd.EtcdKeyNotFound:
			raise Exception("Key %s not present anymore" % endpoint)

if __name__ == '__main__':
	p = Etcd('192.168.204.128', 2379)

	print("TOMA NO SEU CU")
	#d = [{"name": "app", "ips": ["10.10.1.1"], "port": 80}]
	d = {'app': {'ips':['10.10.1.1'], 'portSRC': '80', 'portDST': '8080'}}
	try:
		#p.write('/python/app', {'app': {'ips':['10.10.1.1']}})
		p.write('/python/app', json.dumps(d))
	except Exception as e:
		print(e)

	try:
		val = p.read('/python/app')
	except Exception as e:
		print(e)

	print(val)
	val = ast.literal_eval(val)

	count = 0
	while True:
		val['app' + str(count)] = {'ips':['10.10.1.1'], 'portSRC': '80', 'portDST': '8080'}

		print(json.dumps(val))
		try:
			p.update('/python/app', json.dumps(val))
		except Exception as e:
			print(e)

		print("MEU OVO")
		count += 1
		time.sleep(1)
	
    #val = ast.literal_eval(val)
    #print(val)
    #val.update({'pepeca': 1})
    #print(ast.literal_eval(val))

   # print(val)
    # try:
    #  p.delete('/python/app1')
    # except Exception as e:
    #  print(e)
