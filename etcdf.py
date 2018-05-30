#!/usr/bin/env python

import etcd
import ast


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
	    update = self.client.update(response)
	except Exception as e:
	    raise Exception(e)

    def watch(self, endpoint):
        if not endpoint:
            raise Exception("Endpoint is empty")

        try:
            values = self.client.watch(endpoint, timeout=0)
        except etcd.EtcdKeyNotFound:
            raise Exception("Key %s not present anymore" % endpoint)

        return values.value

if __name__ == '__main__':
    p = Etcd('172.16.95.183', 2379)

    try:
	p.write('/python/app1', {'app': {'ips':['10.10.1.1']}})
    except Exception as e:
        print(e)

    try:
        val = p.read('/python/app1')
    except Exception as e:
        print(e)

    val = ast.literal_eval(val)
    val['app']['ips'].append('10.10.1.2')

    try:
	p.update('/python/app1', val)
    except Exception as e:
	print(e)
    #val = ast.literal_eval(val)
    #print(val)
    #val.update({'pepeca': 1})
    #print(ast.literal_eval(val))

   # print(val)
    # try:
    #  p.delete('/python/app1')
    # except Exception as e:
    #  print(e)
