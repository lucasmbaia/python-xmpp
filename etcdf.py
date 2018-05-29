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

    def update(self, endpoint, append_values=None, add_values=None):
	if not endpoint:
	    raize Exception("Endpoint is empty")

	try:
	    response = self.client.read(endpoint)
	except Exception as e:
	    raise Exception(e)

	values = ast.literal_eval(response.value)

	if append_values is not None:

if __name__ == '__main__':
    p = Etcd('172.16.95.183', 2379)

    try:
        p.write('/python/app1', {'string': 'test', 'number': 3})
    except Exception as e:
        print(e)

    try:
        val = p.read('/python/app1')
    except Exception as e:
        print(e)

    val = ast.literal_eval(val)
    print(val)
    val.update({'pepeca': 1})
    #print(ast.literal_eval(val))

    print(val)
    # try:
    #  p.delete('/python/app1')
    # except Exception as e:
    #  print(e)
