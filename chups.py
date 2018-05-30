#!/usr/bin/env python

from etcdf import Etcd


if __name__ == '__main__':
    p = Etcd('172.16.95.183', 2379)
    
    try:
	chups = p.watch('/python/app1')
	print(chups)
    except Exception as e:
	print(e)
