'''
Created on Aug 18, 2017

@catalogor: darkbk
'''
import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException,\
    ConflictException

oid = None

tests = [
    'test_add_catalog',
    'test_add_catalog_twice',
    'test_get_catalogs',
    'test_get_catalogs_by_zone',
    'test_get_catalog',
    'test_get_catalog_perms',
    'test_get_catalog_by_name',
    'test_update_catalog',

    'test_add_endpoint',
    'test_add_endpoint_twice',
    'test_get_endpoints',
    'test_filter_endpoints',
    'test_get_endpoint',
    'test_update_endpoint',
    'test_delete_endpoint',

    'test_delete_catalog',
]


class CatalogTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
        
    #
    # catalogs
    #
    def test_add_catalog(self):
        data = {
            'catalog':{
                'name':'beehive', 
                'desc':'beehive catalog',
                'zone':'internal'
            }
        }        
        self.call('auth', '/v1.0/ncs//catalogs', 'post', data=data,
                  **self.users['admin'])
    
    @assert_exception(ConflictException)
    def test_add_catalog_twice(self):
        data = {
            'catalog':{
                'name':'beehive', 
                'desc':'beehive catalog',
                'zone':'internal'  
            }
        }        
        self.call('auth', '/v1.0/ncs//catalogs', 'post', data=data,
                  **self.users['admin'])        
    
    def test_get_catalogs(self):
        res = self.call('auth', '/v1.0/ncs//catalogs', 'get', **self.users['admin'])
        global oid
        oid = res['catalogs'][-1]['id']
        
    def test_get_catalogs_by_zone(self):
        self.call('auth', '/v1.0/ncs//catalogs', 'get',
                  query={'zone':'internal'},
                  **self.users['admin'])   
        
    def test_get_catalog(self):
        global oid
        self.call('auth', '/v1.0/ncs//catalogs/{oid}', 'get',
                  params={'oid':oid},
                  **self.users['admin'])
        
    def test_get_catalog_perms(self):
        global oid
        self.call('auth', '/v1.0/ncs//catalogs/{oid}/perms', 'get',
                  params={'oid':oid},
                  **self.users['admin'])        
        
    def test_get_catalog_by_name(self):
        self.call('auth', '/v1.0/ncs//catalogs/{oid}', 'get',
                  params={'oid':'beehive-internal'},
                  **self.users['admin'])
        
    def test_update_catalog(self):
        data = {
            'catalog':{
                'name':'beehive', 
                'desc':'beehive catalog1',
                'zone':'internal1'  
            }
        }
        self.call('auth', '/v1.0/ncs//catalogs/{oid}', 'put', 
                  params={'oid':'beehive'}, data=data,
                  **self.users['admin'])        

    def test_delete_catalog(self):
        self.call('auth', '/v1.0/ncs//catalogs/{oid}', 'delete', 
                  params={'oid':'beehive'},
                  **self.users['admin'])

    #
    # endpoints
    #
    def test_add_endpoint(self):
        data = {
            'endpoint':{
                'catalog':'beehive',
                'name':'endpoint-prova', 
                'desc':'Authorization endpoint 01', 
                'service':'auth', 
                'uri':'http://localhost:6060/v1.0/auth/', 
                'active':True
            }
        }        
        self.call('auth', '/v1.0/ncs//endpoints', 'post', data=data,
                  **self.users['admin'])

    @assert_exception(ConflictException)
    def test_add_endpoint_twice(self):
        data = {
            'endpoint':{
                'catalog':'beehive',
                'name':'endpoint-prova', 
                'desc':'Authorization endpoint 01', 
                'service':'auth', 
                'uri':'http://localhost:6060/v1.0/auth/', 
                'active':True
            }
        }        
        self.call('auth', '/v1.0/ncs//endpoints', 'post', data=data,
                  **self.users['admin'])        
    
    def test_get_endpoints(self):
        self.call('auth', '/v1.0/ncs//endpoints', 'get', 
                  **self.users['admin'])
        
    def test_filter_endpoints(self):
        self.call('auth', '/v1.0/ncs//endpoints', 'get',
                  query={'service':'auth', 'catalog':'beehive'},
                  **self.users['admin'])        
        
    def test_get_endpoint(self):
        self.call('auth', '/v1.0/ncs//endpoints/{oid}', 'get',
                  params={'oid':'endpoint-prova'}, 
                  **self.users['admin'])
        
    def test_update_endpoint(self):
        data = {
            'endpoint':{
                'name':'endpoint-prova', 
                'desc':'Authorization endpoint 02', 
                'service':'auth', 
                'uri':'http://localhost:6060/v1.0/auth/', 
                'active':True
            }
        }
        self.call('auth', '/v1.0/ncs//endpoints/{oid}', 'put', 
                  params={'oid':'endpoint-prova'}, data=data,
                  **self.users['admin'])        
    
    def test_delete_endpoint(self):
        self.call('auth', '/v1.0/ncs//endpoints/{oid}', 'delete', 
                  params={'oid':'endpoint-prova'},
                  **self.users['admin'])
        
if __name__ == '__main__':
    runtest(CatalogTestCase, tests)  