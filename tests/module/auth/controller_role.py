'''
Created on Sep 2, 2013

@author: darkbk

run first scripts/init_coludapi.py configure
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.module.base import ApiManager
from gibboncloudapi.module.auth.model import AuthDbManager
from gibboncloudapi.module.auth.mod import AuthModule
from gibboncloudapi.util.data import operation

# create api manager
params = {'api_name':'cloudapi',
          'api_id':'process',
          'database_uri':CloudapiTestCase.db_uri,
          'api_module':['gibboncloudapi.module.auth.mod.AuthModule'],
          'api_plugin':[],
          'api_subsystem':'auth'}
manager = ApiManager(params)
manager.configure()
manager.register_modules()

class RoleManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        operation.transaction = 0 
        
        self.auth_module = manager.modules['AuthModule']
        
        # create session
        operation.session = self.auth_module.get_session()        

        # caller permissions
        perms = [(1, 1, 'auth', 'objects', 'Objects', '*', 1, '*'),
                 (1, 1, 'auth', 'role', 'Role', '*', 1, '*')]

        operation.perms = perms
        operation.user = ('admin', 'localhost')

        self.controller = self.auth_module.get_controller()
        self.object = self.controller.objects
    
    def tearDown(self):
        self.auth_module.release_session(operation.session)
        CloudapiTestCase.tearDown(self)
    
    def test_create_table(self):
        AuthDbManager.create_table(self.db_uri)
            
    def test_remove_table(self):
        AuthDbManager.remove_table(self.db_uri)

    def test_set_initial_value(self):
        # add actions
        actions = ['*', 'view', 'insert', 'update', 'delete', 'use']
        self.object.add_actions(actions)
        # add object types
        obj_type = [('auth', 'role', 'Role'),
                    ('event', 'role', 'Role'),
                    ('resource', 'container.org.group.vm', 'Vm'),
                    ('resource', 'container.org', 'Org'),
                    ('service', 'VdcService', 'Vdc'),
                    ('service', 'VirtualServerService', 'VirtualServer'),
                    ]
        res = self.object.add_types(obj_type)
        # add objects
        objs = [('resource', 'container.org.group.vm', 'c1.o1.g1.*', ''),
                ('resource', 'container.org.group.vm', 'c1.o1.g1.v1', ''),
                ('resource', 'container.org', 'c1.o2', ''),
                ('service', 'vdcservice', 'ser1', '')]
        res = self.object.add(objs)

    def test_get_all(self):
        self.controller.get_roles()

    def test_get(self):
        self.controller.get_roles(name='role1')

    def test_get_by_permission(self):
        perm = (2, 1, 'resource', 'container.org.group.vm', 'Vm', 'c1.o1.g1.*', 5, 'delete')
        self.controller.get_roles(permission=perm)
    
    def test_add(self):
        name = 'role1'
        description = 'role1'
        res = self.controller.add_role(name, description)

    def test_update(self):
        name = 'role1'
        new_name = 'role2'
        new_description = 'role2_desc'
        role = self.controller.get_roles(name=name)[0]
        role.update(new_name, new_description)

    def test_delete(self):
        name = 'role2'
        role = self.controller.get_roles(name=name)[0]
        res = role.delete()

    def test_get_permissions(self):
        name = 'role1'
        role = self.controller.get_roles(name=name)[0]
        role.get_permissions()

    def test_append_permission(self):
        perms = self.object.get_permission(objid='c1.o1.g1.*')
        role = self.controller.get_roles(name='role1')[0]
        role.append_permissions(perms)

    def test_append_permission_bis(self):
        perms = self.object.get_permission(objid='c1.o1.g1.*')
        role = self.controller.get_roles(name='role1')[0]
        role.append_permissions(perms)

    def test_remove_permission(self):
        perms = self.object.get_permission(objid='c1.o1.g1.*')
        role = self.controller.get_roles(name='role1')[0]
        role.remove_permissions(perms)
        
    def test_can(self):
        pass

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             'test_set_initial_value',
             'test_add',
             'test_get_all',  
             'test_get',
             'test_append_permission',
             'test_append_permission_bis',
             'test_get_permissions',
             'test_get_by_permission',
             'test_remove_permission',
             'test_update',
             'test_delete',          
            ]
    return unittest.TestSuite(map(RoleManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])