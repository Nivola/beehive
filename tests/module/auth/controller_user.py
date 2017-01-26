'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.module.base import ApiManager, ApiManagerError
from gibboncloudapi.module.auth.model import AuthDbManager
from gibbonutil.auth import DatabaseAuth, SystemUser
from gibboncloudapi.module.auth.mod import AuthModule
from gibboncloudapi.util.data import operation
from gibbonutil.simple import transaction_id_generator

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

class UserManagerTestCase(CloudapiTestCase):
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
                 (1, 1, 'auth', 'role', 'Role', '*', 1, '*'),
                 (1, 1, 'auth', 'user', 'User', '*', 1, '*')]
        
        """
        perms = [(1, 1, 'auth', 'role_container', 'ObjectContainer', '*', 1, 'view'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'insert'),
                 (1, 1, 'auth', 'role_container', 'ObjectContainer', '*', 1, 'update'),
                 (1, 1, 'auth', 'role_container', 'ObjectContainer', '*', 1, 'delete')]
        """
        operation.perms = perms
        operation.user = ('admin', 'localhost')

        self.controller = self.auth_module.get_controller()
        self.object = self.controller.objects
        
        # set authentication provider
        db_auth_provider = DatabaseAuth(AuthDbManager, manager.db_manager, SystemUser)
        self.auth_module.set_authentication_providers({'local':db_auth_provider})
        self.authentication_manager = self.auth_module.authentication_manager       
    
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
                    ('auth', 'user', 'User'),
                    ('event', 'user', 'User'),                    
                    ('resource', 'container.org.group.vm', 'Vm'),
                    ('resource', 'container.org', 'Org'),
                    ('service', 'VdcService', 'Vdc'),
                    ('service', 'VirtualServerService', 'VirtualServer'),
                    ]
        res = self.object.add_types(obj_type)
        # add objects
        objs = [('resource', 'container.org.group.vm', 'c1.o1.g1.*', 'bla'),
                ('resource', 'container.org.group.vm', 'c1.o1.g1.v1', 'bla'),
                ('resource', 'container.org.group.vm', 'c1.o1.g1.v2', 'bla'),
                ('resource', 'container.org', 'c1.o2', 'bla'),
                ('service', 'vdcservice', 'ser1', 'bla')]
        res = self.object.add(objs)

        # add roles
        role1 = self.controller.add_role('role1', 'role1')
        role2 = self.controller.add_role('role2', 'role2')

        perms = self.object.get_permission(objid='c1.o2')
        role = self.controller.get_roles(name='role1')[0]
        role.append_permissions(perms)
        
        perms = self.object.get_permission(objid='c1.o1.g1.v1')
        perms.extend(self.object.get_permission(objid='c1.o1.g1.v2'))
        perms.extend(self.object.get_permission(objtype='service'))
        role = self.controller.get_roles(name='role2')[0]
        role.append_permissions(perms)
        
        self.controller.add_guest_role()
        self.controller.add_superadmin_role([])

    def test_login1(self):
        name = 'test1'
        password = 'test'
        domain = 'local'
        ipaddr = '0.0.0.0'
        self.authentication_manager.login(name, password, domain, ipaddr)

    def test_login2(self):
        name = 'admin'
        password = 'admin_01'
        domain = 'clskdom.lab'
        ipaddr = '0.0.0.0'
        self.authentication_manager.login(name, password, domain, ipaddr)

    def test_get_all(self):
        self.controller.get_users()

    def test_get(self):
        name = 'test@local'
        user = self.controller.get_users(name=name)

    def test_get_empty(self):
        with self.assertRaises(ApiManagerError):
            name = 'test1@local'
            self.controller.get_users(name=name)

    def test_get_by_role(self):
        self.controller.get_users(role='role1')
    
    def test_add(self):
        name = 'test@local'
        storetype = 'DBUSER'
        systype = 'USER'
        active = True
        password = 'test'
        description = 'test1'
        self.controller.add_user(name, storetype, systype, active=active, 
                                 password=password, description=description)
        
    def test_add_generic(self):
        name = 'test3@local'
        storetype = 'DBUSER'
        active = True
        password = 'test'
        description = 'test3'
        self.controller.add_generic_user(name, storetype, password=password,
                                         description=description)
        
    def test_add_system(self):
        name = transaction_id_generator()
        usertype = 'DBUSER'
        storetype = 'USER'
        active = True
        password = 'test'
        description = 'system user'
        self.controller.add_system_user(name, password=password, 
                                        description=description)        
        
    def test_update(self):
        name = 'test@local'
        new_name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.update(new_name=new_name)

    def test_delete(self):
        name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.delete()

    def test_append_role1(self):
        name = 'test1@local'
        role_name = 'role1'
        user = self.controller.get_users(name=name)[0]
        user.append_role(role_name)

    def test_append_role2(self):
        name = 'test1@local'
        role_name = 'role2'
        user = self.controller.get_users(name=name)[0]
        user.append_role(role_name)

    def test_append_role2bis(self):
        with self.assertRaises(ApiManagerError):
            name = 'test1@local'
            role_name = 'role2'
            user = self.controller.get_users(name=name)[0]
            user.append_role(role_name)

    def test_remove_role1(self):
        name = 'test1@local'
        role_name = 'role1'
        user = self.controller.get_users(name=name)[0]
        user.remove_role(role_name)

    def test_remove_role2(self):
        name = 'test1@local'
        role_name = 'role2'
        user = self.controller.get_users(name=name)[0]
        user.remove_role(role_name)

    def test_remove_role3(self):
        with self.assertRaises(ApiManagerError):
            name = 'test1@local'
            role_name = 'role3'
            user = self.controller.get_users(name=name)[0]
            user.remove_role(role_name)

    def test_get_roles(self):
        name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.get_roles()

    def test_get_permissions(self):
        name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.get_permissions()

    def test_get_groups(self):
        name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.get_groups()
        
    def test_get_attributes(self):
        name = 'test1@local'
        user = self.controller.get_users(name=name)[0]
        user.get_attribs()     

    def test_can1(self):
        name = 'test1@local'
        action = 'view'
        objtype = 'resource'
        user = self.controller.get_users(name=name)[0]
        user.can(action, objtype)

    def test_can2(self):
        name = 'test1@local'
        action = 'view'
        objtype = 'resource'
        definition = 'container.org.group.vm'
        user = self.controller.get_users(name=name)[0]
        user.can(action, objtype, definition=definition)
        
    def test_can3(self):
        name = 'test1@local'
        action = 'view'
        objtype = 'service'
        user = self.controller.get_users(name=name)[0]
        user.can(action, objtype)

def test_suite():
    tests = ['test_remove_table', 
             'test_create_table',
             'test_set_initial_value',
             'test_add',
             'test_add_generic',
             'test_add_system',
             'test_get_all',    
             'test_get',
             'test_update',
             'test_append_role1',
             'test_append_role2',
             'test_append_role2bis',
             'test_get_roles',
             'test_get_permissions',
             'test_get_groups',
             'test_get_attributes',
             'test_get_by_role',
             'test_login1',
             'test_login2',
             #'test_can1',
             #'test_can2',
             #'test_can3',
             'test_remove_role1',
             'test_remove_role2',
             'test_remove_role3',
             'test_delete',
             #'test_get_empty',         
            ]
    return unittest.TestSuite(map(UserManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])