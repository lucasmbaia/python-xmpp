#!/usr/bin/env python

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import base64

def encrypt(data, key):
  if not data:
    raise Exception("data is empty")

  if not key:
    raise Exception("key is empty")

  data_encode = data.encode("utf-8")
  private_key = RSA.importKey(open(key, 'rb').read())
  session_key = get_random_bytes(16)

  cipher_rsa = PKCS1_OAEP.new(private_key)
  enc_session_key = cipher_rsa.encrypt(session_key)

  cipher_aes = AES.new(session_key, AES.MODE_EAX)
  ciphertext, tag = cipher_aes.encrypt_and_digest(data_encode)

  return enc_session_key, cipher_aes.nonce, tag, ciphertext

def decrypt(key, enc_session_key, nonce, tag, ciphertext):
  if not key:
    raise Exception("key is empty")

  if not enc_session_key:
    raise Exception("session key is empty")

  if not nonce:
    raise Exception("nonce is empty")

  if not tag:
    raise Exception("tag is empty")

  if not ciphertext:
    raise Exception("ciphertext is empty")

  public_key = RSA.importKey(open(key, 'rb').read())

  cipher_rsa = PKCS1_OAEP.new(public_key)
  session_key = cipher_rsa.decrypt(enc_session_key)

  cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
  data_decrypt = cipher_aes.decrypt_and_verify(ciphertext, tag)

  return data_decrypt.decode("utf-8")

def encrypt_data(data, key):
  public_key = RSA.importKey(open(key, 'rb').read())
  cipher_rsa = PKCS1_OAEP.new(public_key)

  data_encrypted = cipher_rsa.encrypt(data)
  encoded_data_encrypted = base64.b64encode(data_encrypted)
  return encoded_data_encrypted

def decrypt_data(data, key):
  private_key = RSA.importKey(open(key, 'rb').read())
  cipher_rsa = PKCS1_OAEP.new(private_key)

  decoded_data_encrypted = base64.b64decode(data)
  data_decrypted = cipher_rsa.decrypt(decoded_data_encrypted)

  return data_decrypted

if __name__ == '__main__':
  text = 'Ola Mundo!'

  enc_session_key, nonce, tag, ciphertext = encrypt(text, 'id_rsa.pub')

  data = decrypt('id_rsa', enc_session_key, nonce, tag, ciphertext)

  print(data)

  porra = encrypt_data('123456', 'id_rsa.pub')
  print(porra)
  print(decrypt_data(porra, 'id_rsa'))
  print(decrypt_data('hlzGhMWM0sEdE2Z2MQyjp0E2H7s00TAUOs8yOxWs0B01tGlouJJjvEvFRxKtw6juzn9UrZFGU4gqDMTnNrV1RADqgV8QjufnvHaHhwvOP8paO1irH5Ffcfl7RCr3IoXm2iNjWZO6IDr8P3U8O86XRJ4uFjr7bjZlDWmi+NijG7PZhqy0J9riUS7SWWgzA8ZGDFaSmafOTR0A78llz5cau5y0sL7DNFaPtg5NCm2wzut1xIHP5mU7UO3KUpphrTtoleURwnkXD1a3nEad+Y6K2PAFt43asl5mFGGotNT+wVUPK5thJORee5ixjYt5tutx3za9ALY0JBjE/RSz4LajDA==', 'id_rsa'))
