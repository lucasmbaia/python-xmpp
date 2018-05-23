#!/usr/bin/env python

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

from etcdf import Etcd

if __name__ == '__main__':
  p = Etcd('172.16.95.183', 2379)

  try:
    p.write('/lucas/app-teste', {'jid': 'container@localhost', 'password': 'hlzGhMWM0sEdE2Z2MQyjp0E2H7s00TAUOs8yOxWs0B01tGlouJJjvEvFRxKtw6juzn9UrZFGU4gqDMTnNrV1RADqgV8QjufnvHaHhwvOP8paO1irH5Ffcfl7RCr3IoXm2iNjWZO6IDr8P3U8O86XRJ4uFjr7bjZlDWmi+NijG7PZhqy0J9riUS7SWWgzA8ZGDFaSmafOTR0A78llz5cau5y0sL7DNFaPtg5NCm2wzut1xIHP5mU7UO3KUpphrTtoleURwnkXD1a3nEad+Y6K2PAFt43asl5mFGGotNT+wVUPK5thJORee5ixjYt5tutx3za9ALY0JBjE/RSz4LajDA=='})
  except Exception as e:
    print(e)

#  try:
#    val = p.read('/python/app1')
#  except Exception as e:
#    print(e)

#  print(val)

#  try:
#    p.delete('/python/app1')
#  except Exception as e:
#    print(e)

