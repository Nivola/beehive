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
#u'test_create_keyauth_token',
#u'test_ping_subsystem',
#u'test_ping_endpoint',

#u'test_exist',
#u'test_load_catalog',

#u'test_get_catalogs',
u'test_get_catalog',
#u'test_create_catalog',
#u'test_delete_catalog',

#u'test_get_endpoints',
#u'test_get_endpoint',
#u'test_create_endpoint',
#u'test_delete_endpoint',

#u'test_list_resources',    

#u'test_logout',
]

class BeehiveApiClientTestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        global uid, seckey
        endpoints = [self.endpoints.get(self.test_config[u'default-endpoint'])]
        user = self.users.get(u'test3')
        self.user_name = user.get(u'user')
        self.pwd = user.get(u'pwd')
        self.ip = user.get(u'ip')
        self.catalog_id = user.get(u'catalog')
        authtype = user.get(u'auth')
        self.client = BeehiveApiClient(endpoints, authtype, self.user_name, self.pwd, None, self.catalog_id)
        if uid is not None:
            self.client.uid = uid
            self.client.seckey = seckey
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping_subsystem(self):
        self.client.load_catalog()
        res = self.client.ping(subsystem=u'auth')
        self.logger.info(self.pp.pformat(res))
        
    def test_ping_endpoint(self):
        res = self.client.ping(endpoint={u'proto':u'http',
                                         u'host':u'10.102.184.69',
                                         u'port':6060})
        self.logger.info(self.pp.pformat(res))

    def test_create_keyauth_token(self):
        global uid, seckey      
        res = self.client.create_token(api_user=self.user_name, 
                                       api_user_pwd=self.pwd, login_ip=self.ip)
        uid = res[u'access_token']
        seckey = res[u'seckey']
        self.logger.info(self.client.endpoints)

    def test_exist(self):
        global uid, seckey
        res = self.client.exist(uid)
        self.logger.info(res)
        
    def test_load_catalog(self):
        global uid, seckey
        res = self.client.load_catalog()
        self.logger.info(res)        
        
    #
    # catalogs
    #        
    def test_get_catalogs(self):
        global uid, seckey
        for i in range(1, 20):
            time.sleep(2)
            res = self.client.get_catalogs()
            print ''
            print self.client.endpoints['auth']
        self.logger.info(self.pp.pformat(res))
        
    def test_get_catalog(self):
        global uid, seckey
        res = self.client.get_catalog(self.catalog_id)
        self.logger.info(self.pp.pformat(res))        

    def test_create_catalog(self):
        res = self.client.create_catalog(u'prova', u'internal')
        self.logger.info(self.pp.pformat(res))
        
    def test_delete_catalog(self):
        catalog_id = 7
        res = self.client.delete_catalog(catalog_id) 

    #
    # endpoints
    #
    def test_get_endpoints(self):
        global uid, seckey
        res = self.client.get_endpoints()
        self.logger.info(self.pp.pformat(res))
        
    def test_get_endpoint(self):
        global uid, seckey
        res = self.client.get_endpoint(17)
        self.logger.info(self.pp.pformat(res))        

    def test_create_endpoint(self):
        name = u'prova'
        service = u'auth'
        uri = u'http://localhost:5000'
        res = self.client.create_endpoint(2, name, service, uri)
        self.logger.info(self.pp.pformat(res))
        
    def test_delete_endpoint(self):
        endpoint_id = 17
        res = self.client.delete_endpoint(endpoint_id)
        
    #
    # resources
    #
    def test_list_resources(self):
        global uid, seckey
        res = self.client.invoke(u'resource1', u'/v1.0/resources/', u'get', u'')
        #self.logger.info(self.pp.pformat(res))
        
if __name__ == u'__main__':
    runtest(BeehiveApiClientTestCase, tests)    
    