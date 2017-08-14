'''
Created on Aug 9, 2017

@author: darkbk
'''
import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase

tests = [
    u'test_get_users',
    u'test_get_users_401',    
    u'test_get_user',
    
    #u'test_add_group',
    u'test_get_groups',
    #u'test_get_groups_by_user',
    #u'test_get_groups_by_role',
    #u'test_get_group',
    #u'test_get_group_perms',
    #u'test_update_group',
    #u'test_add_group_user',
    #u'test_remove_group_user',
    #u'test_add_group_role',
    #u'test_remove_group_role',    
    #u'test_del_group',
]

class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # users
    #
    def test_get_users(self):
        self.call(u'auth', u'/v1.0/auth/users', u'get', {}, 
                  **self.users[u'admin'])
        
    def test_get_users_401(self):
        self.call(u'auth', u'/v1.0/auth/users', u'get', {})        
        
    def test_get_user(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'get', {u'oid':4}, 
                  **self.users[u'admin'])
    
    #
    # groups
    #
    def test_add_group(self):
        self.call(u'auth', u'/v1.0/auth/groups', u'post', {}, 
                  **self.users[u'admin'])    
    
    def test_get_groups(self):
        self.call(u'auth', u'/v1.0/auth/groups', u'get', {}, 
                  **self.users[u'admin'])
        
    def test_get_group(self):
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'get', {u'oid':4}, 
                  **self.users[u'admin'])        

if __name__ == u'__main__':
    runtest(AuthObjectTestCase, tests)      