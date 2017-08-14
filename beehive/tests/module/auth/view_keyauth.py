'''
Created on Aug 9, 2017

@author: darkbk
'''
import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase

tests = [
    u'test_create_token',
    u'test_create_token_no_user',
    u'test_create_token_no_pwd',
    u'test_create_token_no_ip',
]

class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # keyauth token
    #
    def test_create_token(self):
        data = {u'user':self.users[u'admin'][u'user'], 
                u'password':self.users[u'admin'][u'pwd'], 
                u'login-ip':self.users[u'admin'][u'ip']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)

    def test_create_token_no_user(self):
        data = {u'password':self.users[u'admin'][u'pwd']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
        
    def test_create_token_no_pwd(self):
        data = {u'user':self.users[u'admin'][u'user']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)        
        
    def test_create_token_no_ip(self):
        data = {u'user':self.users[u'admin'][u'user'], 
                u'password':self.users[u'admin'][u'pwd']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
     

if __name__ == u'__main__':
    runtest(AuthObjectTestCase, tests)      