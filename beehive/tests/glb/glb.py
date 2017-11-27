'''
Created on Jan 12, 2017

@author: darkbk
'''
import time
import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, UnauthorizedException,\
    ConflictException
from beehive.common.apiclient import BeehiveApiClient

uid = None
seckey = None

tests = [
u'test_ping',
u'test_create_keyauth_token',
u'test_validate_token',
#u'test_get_catalog',


#u'test_create_catalog',
#u'test_delete_catalog',

#u'test_get_endpoints',
#u'test_get_endpoint',
#u'test_create_endpoint',
#u'test_delete_endpoint',

u'test_list_resources',    

#u'test_logout',
]

class BeehiveGlbTestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        global uid, seckey
        endpoints = [self.endpoints.get(self.test_config[u'default-endpoint'])]
        user = self.users.get(u'admin')
        self.user_name = user.get(u'user')
        self.pwd = user.get(u'pwd')
        self.ip = user.get(u'ip')
        self.catalog_id = user.get(u'catalog')
        authtype = user.get(u'auth')
        self.client = BeehiveApiClient(endpoints, authtype, self.user_name, 
                                       self.pwd, self.catalog_id)
        #self.client.load_catalog()
        if uid is not None:
            self.client.uid = uid
            self.client.seckey = seckey
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping(self):
        res = self.client.ping(subsystem=u'auth')
        self.logger.info(self.pp.pformat(res))

    def test_create_keyauth_token(self):
        global uid, seckey      
        res = self.client.create_token(api_user=self.user_name, 
                                       api_user_pwd=self.pwd, login_ip=self.ip)
        uid = res[u'access_token']
        seckey = res[u'seckey']
        self.logger.info(self.client.endpoints)

    def test_validate_token(self):
        global uid, seckey
        res = self.client.exist(uid)
        self.logger.info(res)
        
    def test_get_catalog(self):
        res = self.client.get_catalog(self.catalog_id)
        self.logger.info(self.pp.pformat(res))        
        
    #
    # resources
    #
    def test_list_resources(self):
        global uid, seckey
        res = self.client.invoke(u'resource', u'/v1.0/resources', u'get', None)
        self.logger.info(self.pp.pformat(res))
        
if __name__ == u'__main__':
    runtest(BeehiveGlbTestCase, tests)    
    