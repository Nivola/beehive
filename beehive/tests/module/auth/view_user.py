'''
Created on Aug 9, 2017

@author: darkbk
'''
import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase

class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        #self.auth_client = AuthClient()
        self.api_id = u'api'
        self.user = u'admin@local'
        self.user1 = u'camunda@local'
        self.ip = u'158.102.160.234'
        self.pwd = u'testlab'
        self.pwd1 = u'camunda'
        self.baseuri = u'/v1.0/keyauth'
        self.baseuri1 = u'/v1.0/simplehttp'
        self.baseuri2 = u'/v1.0/auth'
        self.credentials = u'%s:%s' % (self.user1, self.pwd1)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_get_roles(self):
        self.call(u'auth', u'/v1.0/auth/roles', u'get', {}, 
                  **self.users[u'admin'])

    def test_get_users(self):
        self.call(u'auth', u'/v1.0/auth/users', u'get', {}, 
                  **self.users[u'admin'])
        
    def test_get_user(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'get', {u'oid':4}, 
                  **self.users[u'admin'])

def test_suite():
    tests = [
        u'test_get_roles',
        u'test_get_users',
        u'test_get_user',
    ]
    return unittest.TestSuite(map(AuthObjectTestCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())        