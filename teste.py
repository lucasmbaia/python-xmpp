#!/usr/bin/env python

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

from etcdf import Etcd

if __name__ == '__main__':
  #private = RSA.importKey('id_rsa')
  data = 'Ola Mundo'.encode("utf-8")

  key = open('id_rsa', 'rb').read()
  private = RSA.importKey(key)
  session_key = get_random_bytes(16)

  cipher_rsa = PKCS1_OAEP.new(private)
  enc_session_key = cipher_rsa.encrypt(session_key)

  cipher_aes = AES.new(session_key, AES.MODE_EAX)
  ciphertext, tag = cipher_aes.encrypt_and_digest(data)

  print(ciphertext, tag)
  print(private.publickey().exportKey())

  public_key = RSA.importKey(open('id_rsa.pub', 'rb').read())

  pepeca = PKCS1_OAEP.new(public_key)
  session_key = cipher_rsa.decrypt(enc_session_key)

  cipher_des = AES.new(session_key, AES.MODE_EAX, cipher_aes.nonce)
  datad = cipher_des.decrypt_and_verify(ciphertext, tag)
  print(datad.decode("utf-8"))
#  p = Etcd('127.0.0.1', 2379)

#  try:
#    p.write('/python/app1', {'string': 'test', 'number': 3})
#  except Exception as e:
#    print(e)

#  try:
#    val = p.read('/python/app1')
#  except Exception as e:
#    print(e)

#  print(val)

#  try:
#    p.delete('/python/app1')
#  except Exception as e:
#    print(e)

