'''
Created on Jun 8, 2017

@author: darkbk
'''
'''
import cryptography
import passlib
import time
print passlib.__version__
a = 'prova'
from passlib.hash import sha256_crypt
s = time.time()
pwd = sha256_crypt.encrypt(a)
print time.time() - s
s = time.time()
print sha256_crypt.verify(a, pwd)
print time.time() - s'''

import time
import bcrypt
password = "camunda"
# Hash a password for the first time, with a randomly-generated salt
s = time.time()
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print hashed
print time.time() - s
# Check that an unhashed password matches one that has previously been
hashed = '$2b$12$MetxVQlXia37VF4yotb/SuJqV.RI/QSlDYTdnvLLlcjqEnABtyIgG'
s = time.time()
if bcrypt.checkpw(password, hashed):
    print("It Matches!")
else:
    print("It Does not Match :(")
print time.time() - s