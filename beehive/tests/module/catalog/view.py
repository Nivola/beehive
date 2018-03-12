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
    u'test_add_catalog',
    u'test_add_catalog_twice',
    u'test_get_catalogs',
    u'test_get_catalogs_by_zone',
    u'test_get_catalog',
    u'test_get_catalog_perms',
    u'test_get_catalog_by_name',
    u'test_update_catalog',

    u'test_add_endpoint',
    u'test_add_endpoint_twice',
    u'test_get_endpoints',
    u'test_filter_endpoints',
    u'test_get_endpoint',
    u'test_update_endpoint',
    u'test_delete_endpoint',

    u'test_delete_catalog',
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
            u'catalog':{
                u'name':u'beehive', 
                u'desc':u'beehive catalog',
                u'zone':u'internal'
            }
        }        
        self.call(u'auth', u'/v1.0/ncs//catalogs', u'post', data=data,
                  **self.users[u'admin'])
    
    @assert_exception(ConflictException)
    def test_add_catalog_twice(self):
        data = {
            u'catalog':{
                u'name':u'beehive', 
                u'desc':u'beehive catalog',
                u'zone':u'internal'  
            }
        }        
        self.call(u'auth', u'/v1.0/ncs//catalogs', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_catalogs(self):
        res = self.call(u'auth', u'/v1.0/ncs//catalogs', u'get', **self.users[u'admin'])
        global oid
        oid = res[u'catalogs'][-1][u'id']
        
    def test_get_catalogs_by_zone(self):
        self.call(u'auth', u'/v1.0/ncs//catalogs', u'get',
                  query={u'zone':u'internal'},
                  **self.users[u'admin'])   
        
    def test_get_catalog(self):
        global oid
        self.call(u'auth', u'/v1.0/ncs//catalogs/{oid}', u'get',
                  params={u'oid':oid},
                  **self.users[u'admin'])
        
    def test_get_catalog_perms(self):
        global oid
        self.call(u'auth', u'/v1.0/ncs//catalogs/{oid}/perms', u'get',
                  params={u'oid':oid},
                  **self.users[u'admin'])        
        
    def test_get_catalog_by_name(self):
        self.call(u'auth', u'/v1.0/ncs//catalogs/{oid}', u'get',
                  params={u'oid':u'beehive-internal'},
                  **self.users[u'admin'])
        
    def test_update_catalog(self):
        data = {
            u'catalog':{
                u'name':u'beehive', 
                u'desc':u'beehive catalog1',
                u'zone':u'internal1'  
            }
        }
        self.call(u'auth', u'/v1.0/ncs//catalogs/{oid}', u'put', 
                  params={u'oid':u'beehive'}, data=data,
                  **self.users[u'admin'])        

    def test_delete_catalog(self):
        self.call(u'auth', u'/v1.0/ncs//catalogs/{oid}', u'delete', 
                  params={u'oid':u'beehive'},
                  **self.users[u'admin'])

    #
    # endpoints
    #
    def test_add_endpoint(self):
        data = {
            u'endpoint':{
                u'catalog':u'beehive',
                u'name':u'endpoint-prova', 
                u'desc':u'Authorization endpoint 01', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/v1.0/auth/', 
                u'active':True
            }
        }        
        self.call(u'auth', u'/v1.0/ncs//endpoints', u'post', data=data,
                  **self.users[u'admin'])

    @assert_exception(ConflictException)
    def test_add_endpoint_twice(self):
        data = {
            u'endpoint':{
                u'catalog':u'beehive',
                u'name':u'endpoint-prova', 
                u'desc':u'Authorization endpoint 01', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/v1.0/auth/', 
                u'active':True
            }
        }        
        self.call(u'auth', u'/v1.0/ncs//endpoints', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_endpoints(self):
        self.call(u'auth', u'/v1.0/ncs//endpoints', u'get', 
                  **self.users[u'admin'])
        
    def test_filter_endpoints(self):
        self.call(u'auth', u'/v1.0/ncs//endpoints', u'get',
                  query={u'service':u'auth', u'catalog':u'beehive'},
                  **self.users[u'admin'])        
        
    def test_get_endpoint(self):
        self.call(u'auth', u'/v1.0/ncs//endpoints/{oid}', u'get',
                  params={u'oid':u'endpoint-prova'}, 
                  **self.users[u'admin'])
        
    def test_update_endpoint(self):
        data = {
            u'endpoint':{
                u'name':u'endpoint-prova', 
                u'desc':u'Authorization endpoint 02', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/v1.0/auth/', 
                u'active':True
            }
        }
        self.call(u'auth', u'/v1.0/ncs//endpoints/{oid}', u'put', 
                  params={u'oid':u'endpoint-prova'}, data=data,
                  **self.users[u'admin'])        
    
    def test_delete_endpoint(self):
        self.call(u'auth', u'/v1.0/ncs//endpoints/{oid}', u'delete', 
                  params={u'oid':u'endpoint-prova'},
                  **self.users[u'admin'])
        
if __name__ == u'__main__':
    runtest(CatalogTestCase, tests)  