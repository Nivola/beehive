'''
Created on Sep 2, 2013

@author: darkbk

run first scripts/init_coludapi.py configure
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.module.base import ApiManager, ApiManagerError
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

class ObjectManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        operation.transaction = 0
        
        self.auth_module = manager.modules['AuthModule']

        # create session
        operation.session = self.auth_module.get_session()
        operation.user = ('admin', 'localhost')

        # caller permissions
        perms = [(1, 1, 'auth', 'objects', 'Objects', '*', 1, '*')]
        
        """perms = [(1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'view'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'insert'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'update'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'delete')]
        """
        operation.perms = perms
        
        # get controller
        controller = self.auth_module.get_controller()
        self.object = controller.objects

    def tearDown(self):
        self.auth_module.release_session(operation.session)
        CloudapiTestCase.tearDown(self)
    
    def test_create_table(self):
        AuthDbManager.create_table(self.db_uri)
        #ConfigDbManager.create_table(self.db_uri)
            
    def test_remove_table(self):
        AuthDbManager.remove_table(self.db_uri)
        #ConfigDbManager.remove_table(self.db_uri)

    def test_set_initial_data(self):    
        self.object.set_initial_data()

    # type
    def test_get_type_all(self):
        res = self.object.get_type()

    def test_get_type(self):
        res = self.object.get_type(objtype='resource')
        res = self.object.get_type(objtype='resource', 
                                   objdef='container.org.group.vm')

    def test_get_type_empty(self):
        with self.assertRaises(ApiManagerError):
            self.object.get_type(objtype='container')

    def test_add_types(self):
        obj_type = [('resource', 'container.org.group.vm', 'Vm'),
                    ('resource', 'container.org', 'Org'),
                    ('service', 'VdcService', 'Vdc'),
                    ('service', 'VirtualServerService', 'VirtualServer'),
                    ]
        res = self.object.add_types(obj_type)
        self.assertEqual(res, True)

    def test_add_types_bis(self):
        obj_type = [('resource', 'container.org.group.vm', 'Vm'),
                    ('resource', 'container.org', 'Org'),
                    ('service', 'VdcService', 'Vdc'),
                    ('service', 'VirtualServerService', 'VirtualServer'),
                    ]
        res = self.object.add_types(obj_type)
        self.assertEqual(res, True)
        
    def test_remove_type(self):
        res = self.object.remove_type(objtype='service')
        res = self.object.remove_type(objtype='resource', 
                                      objdef='container.org.group.vm')
        res = self.object.remove_type(objtype='resource', 
                                      objdef='container.org')
        self.assertEqual(res, True)

    def test_remove_type_bis(self):
        with self.assertRaises(ApiManagerError):
            res = self.object.remove_type(objtype='service')
            res = self.object.remove_type(objtype='resource', 
                                          objdef='container.org.group.vm')
            res = self.object.remove_type(objtype='resource', 
                                          objdef='container.org')
            self.assertEqual(res, True)

    # action
    def test_get_action_all(self):
        res = self.object.get_action()

    def test_get_action(self):
        res = self.object.get_action(value='view')

    def test_add_actions(self):
        actions = ['view', 'use', '*']
        res = self.object.add_actions(actions)

    def test_delete_action1(self):
        res = self.object.remove_action(value='view')

    def test_delete_action2(self):
        res = self.object.remove_action(value='use')

    # object
    def test_get_all(self):
        res = self.object.get()

    def test_get(self):
        res = self.object.get(objid='c1.o2')
        res = self.object.get(objtype='resource')
        res = self.object.get(objtype='service', 
                              objdef='vdcservice', 
                              objid='ser1')

    def test_get_empty(self):
        with self.assertRaises(ApiManagerError):
            res = self.object.get(objtype='conatiner')
        
    def test_add(self):                                              
        objs = [('resource', 'container.org.group.vm', 'c1.o1.g1.*', '*'),
                ('resource', 'container.org.group.vm', 'c1.o1.g1.v1', 'vm1'),
                ('resource', 'container.org', 'c1.o2', 'o2'),
                ('service', 'vdcservice', 'ser1', 'ser1')]
        res = self.object.add(objs)
        self.assertEqual(res, True)

    def test_add_bis(self):
        with self.assertRaises(ApiManagerError):
            objs = [('resource', 'container.org.group.vm', 'c1.o1.g1.*', '*'),
                    ('resource', 'container.org.group.vm', 'c1.o1.g1.v1', 'vm1'),
                    ('resource', 'container.org', 'c1.o2', 'o2'),
                    ('service', 'vdcservice', 'ser1', 'ser1')]
            res = self.object.add(objs)
            self.assertEqual(res, True)

    def test_remove(self):
        res = self.object.remove(objtype='resource')
        res = self.object.remove(objtype='service',
                                 objdef='vdcservice', 
                                 objid='ser1')
        self.assertEqual(res, True)
        
    def test_remove_empty(self):
        with self.assertRaises(ApiManagerError):        
            res = self.object.remove(objtype='resource')
            res = self.object.remove(objtype='service',
                                     objdef='vdcservice', 
                                     objid='ser1')
            self.assertEqual(res, True)

    def test_get_permission_all(self):
        res = self.object.get_permission()

    def test_get_permission(self):
        res = self.object.get_permission(objid='c1.o1.g1.*')
        res = self.object.get_permission(objtype='service')
        res = self.object.get_permission(objdef='container.org')
        res = self.object.get_permission(objid='c1.o1.g1.*', 
                                         objtype='resource', 
                                         objdef='container.org.group.vm')
    
    def test_get_permission_empty(self):
        with self.assertRaises(ApiManagerError):
            res = self.object.get_permission(permission_id=0)

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             #'test_set_initial_value',
             # type
             'test_add_types',
             'test_add_types_bis',
             'test_get_type',
             'test_get_type_empty',
             'test_get_type_all',
             # action
             'test_add_actions',
             'test_get_action_all',
             'test_get_action',
             # object
            'test_add',
            'test_add_bis',
            'test_get_all',
            'test_get',
            'test_get_empty',
             'test_get_permission_all',
             'test_get_permission',
             'test_get_permission_empty',
            'test_remove',
            'test_remove_empty',
             
             'test_delete_action1',
             'test_delete_action2',
             'test_remove_type',
             'test_remove_type_bis',
            ]
    return unittest.TestSuite(map(ObjectManagerTestCase, tests))

if __name__ == '__main__':
    run_test(test_suite())    