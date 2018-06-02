#!/usr/bin/env python

from etcdf import Etcd

def watch(values):
	print(values)

if __name__ == '__main__':
    p = Etcd('192.168.75.128', 2379)
    
    try:
		chups = p.watch('/python/app')
    except Exception as e:
		print(e)
