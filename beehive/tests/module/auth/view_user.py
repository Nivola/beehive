'''
Created on Aug 9, 2017

@author: darkbk
'''
import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase

seckey = None
objid = None

obj = 31813

class AuthObjectTestCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance.
    """
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

def test_suite():
    tests = [
        u'test_login',
        #u'test_logout',
    ]
    return unittest.TestSuite(map(AuthObjectTestCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())        