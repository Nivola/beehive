'''
Created on Sep 2, 2013

@author: darkbk
'''
from tests.test_util import run_test, CloudapiTestCase
import json
import unittest
import tests.test_util

uid = None
seckey = None

cat = 5
sid = 16

class CatalogAPITest(CloudapiTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)

        self.api_id = u'api'
        self.baseuri = u'/v1.0/catalog'
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)

    #
    # catalog
    #
    def test_add_catalog(self):
        global uid, seckey
                
        data = {
            u'catalog':{
                u'name':u'beehive', 
                u'desc':u'cloudapi catalog',
                u'zone':u'internal'                        
            }
        }
        uri = u'/v1.0/catalog/'
        res = self.invoke(u'auth',uri, u'POST', data=json.dumps(data))

    def test_get_catalogs(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/catalogs/'
        res = self.invoke(u'auth',uri, 'GET', data=data)
        self.logger.info(self.pp.pformat(res))   

    def test_get_catalog(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/catalog/%s/' % cat
        res = self.invoke(u'auth',uri, 'GET', data=data)
        self.logger.info(self.pp.pformat(res)) 

    def test_get_catalog_by_name(self):
        global uid, seckey
        cat = u'cloudapi'
        data = u''
        uri = u'/v1.0/catalogs/'
        res = self.invoke(u'auth', uri, 'GET', data=data, headers={u'name':cat})
        self.logger.info(self.pp.pformat(res)) 

    def test_update_catalog(self):
        global uid, seckey
        
        data = {
            u'catalog':{
                u'name':u'beehive1', 
                u'desc':u'cloudapi catalog1',
                u'zone':u'internal1'                        
            }
        }
        uri = u'/v1.0/catalog/%s/' % cat
        res = self.invoke(u'auth',uri, u'PUT', data=json.dumps(data))
        
    def test_delete_catalog(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/catalog/%s/' % cat
        res = self.invoke(u'auth',uri, 'DELETE', data=data)           

    # endpoint

    def test_add_endpoint(self):
        global uid, seckey
                
        data = {
            u'endpoint':{
                u'catalog':5,
                u'name':u'auth-01', 
                u'desc':u'Authorization endpoint 01', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/api/auth/', 
                u'enabled':True                   
            }
        }
        uri = u'/v1.0/catalog/endpoint/'
        res = self.invoke(u'auth',uri, u'POST', data=json.dumps(data))

    def test_get_endpoints(self):
        global uid, seckey

        data = u''
        uri = u'/v1.0/catalog/endpoints/'
        res = self.invoke(u'auth',uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
        
    def test_filter_endpoints(self):
        global uid, seckey
        filter = {u'name':u'catalog02'}
        filter = {u'service':u'auth', u'catalog':2}
        data = u''
        uri = u'/v1.0/catalog/endpoints/'
        res = self.invoke(u'auth',uri, u'GET', data=data, headers=filter)
        self.logger.info(self.pp.pformat(res))           

    def test_get_endpoint(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/catalog/endpoint/%s/' % sid
        res = self.invoke(u'auth',uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))

    def test_update_endpoint(self):
        global uid, seckey
        
        data = {
            u'endpoint':{
                #u'catalog':5,
                u'name':u'auth-012', 
                u'desc':u'Authorization endpoint 01', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/api/auth/', 
                u'enabled':False                             
            }
        }
        uri = u'/v1.0/catalog/endpoint/%s/' % (sid)
        res = self.invoke(u'auth',uri, u'PUT', data=json.dumps(data))
        
    def test_delete_endpoint(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/catalog/endpoint/%s/' % (sid)
        res = self.invoke(u'auth',uri, u'DELETE', data=data)         

def test_suite():
    tests = ['test_login',
             #'test_add_catalog',
             #'test_get_catalogs',
             #'test_get_catalog',
             #'test_get_catalog_by_name',
             #'test_update_catalog',
             
             #'test_add_endpoint',
             #u'test_get_endpoints',
             #u'test_filter_endpoints',
             #'test_get_endpoint',
             #'test_update_endpoint',
             #'test_delete_endpoint',
             
             #'test_delete_catalog',
             #'test_logout',
            ]
    #tests = ['test_remove_initial_value', 'test_set_initial_value']   
    return unittest.TestSuite(map(CatalogAPITest, tests))

if __name__ == '__main__':
    run_test(test_suite())
    