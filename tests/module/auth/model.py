'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
from tests.test_util import BeehiveTestCase
from beehive.common.data import operation
from beehive.common.model.authorization import AuthDbManager
from beecell.db import QueryError, TransactionError
from beecell.simple import id_gen
from beehive.common.test import runtest

class AuthManagerTestCase(BeehiveTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        db_session = self.open_mysql_session(self.db_uri)
        operation.session = db_session()
        self.manager = AuthDbManager()
        operation.transaction = 0
        
    def tearDown(self):
        operation.session.close()
        BeehiveTestCase.tearDown(self)

    def test_create_table(self):       
        AuthDbManager.create_table(self.db_uri)
            
    def test_remove_table(self):       
        AuthDbManager.remove_table(self.db_uri)     

    def test_set_initial_data(self):       
        self.manager.set_initial_data()

    def test_get_object_type_all(self):
        res = self.manager.get_object_type()
        #self.assertEqual(res.name, name, 'Error')

    def test_get_object_type(self):
        res = self.manager.get_object_type(objtype='resource')
        res = self.manager.get_object_type(objtype='resource', objdef='container.org.group.vm')
        #self.assertEqual(res.name, name, 'Error')

    def test_get_type_empty(self):
        with self.assertRaises(QueryError):
            self.manager.get_object_type(objtype='container')

    def test_add_object_types(self):
        obj_type = [['resource', 'container.org.group.vm', 'Vm'],
                    ['resource', 'container.org', 'Org'],
                    ['service', 'vdcservice', 'Vdc'],
                    ['service', 'VirtualServerService', 'VirtualServer'],
                    ]
        res = self.manager.add_object_types(obj_type)
        #self.assertEqual(res, True)
        
    def test_remove_object_type(self):
        res = self.manager.remove_object_type(objtype='service')
        res = self.manager.remove_object_type(objtype='resource', objdef='container.org.group.vm')
        res = self.manager.remove_object_type(objtype='resource', objdef='container.org')
        self.assertEqual(res, True)

    def test_get_object_action_all(self):
        res = self.manager.get_object_action()

    def test_get_object_action(self):
        res = self.manager.get_object_action(value='use')

    def test_add_object_actions(self):
        items = ['*', 'view', 'insert', 'update', 'delete', 'use']
        res = self.manager.add_object_actions(items)

    def test_remove_object_action(self):
        for item in ['*', 'view', 'insert', 'update', 'delete', 'use']:
            res = self.manager.remove_object_action(value=item)

    def test_add_object(self):
        obj_type1 = self.manager.get_object_type(objtype='resource', 
                                                objdef='container.org.group.vm')[0]
        obj_type2 = self.manager.get_object_type(objtype='resource', 
                                                objdef='container.org')[0]
        obj_type3 = self.manager.get_object_type(objtype='service', 
                                                objdef='vdcservice')[0]                                                
        objs = [(obj_type1, 'c1.o1.g1.*', 'bla'),
                (obj_type1, 'c1.o1.g1.v1', 'bla'),
                (obj_type2, 'c1.o2', 'bla'),
                (obj_type3, 'ser1', 'bla')]
        actions = self.manager.get_object_action()
        res = self.manager.add_object(objs, actions)
        #self.assertEqual(res, True)
        
    def test_add_object_bis(self):
        with self.assertRaises(TransactionError):
            obj_type1 = self.manager.get_object_type(objtype='resource', 
                                                     objdef='container.org.group.vm')[0]
            obj_type2 = self.manager.get_object_type(objtype='resource', 
                                                     objdef='container.org')[0]
            objs = [(obj_type1, 'c1.o1.g1.*'),
                    (obj_type1, 'c1.o1.g1.v1'),
                    (obj_type2, 'c1.o2')]
            actions = self.manager.get_object_action()
            res = self.manager.add_object(objs, actions)
            self.assertEqual(res, True)

    def test_get_object_all(self):
        res = self.manager.get_object()
        self.logger.debug(res)
        
    def test_get_object(self):
        res = self.manager.get_object(objid='c1.o2')
        
        obj_type1 = self.manager.get_object_type(objtype='resource', 
                                                 objdef='container.org.group.vm')[0]
        res = self.manager.get_object(objtype=obj_type1)

        res = self.manager.get_object(objid='c1.o1.g1.*', objtype=obj_type1)

    def test_get_object_empty(self):
        with self.assertRaises(QueryError):
            res = self.manager.get_object(objid='c1.o1.g1.*.l')

    def test_remove_object(self):
        res = self.manager.remove_object(objid='c1.o1.g1.*')
        res = self.manager.remove_object()

    def test_remove_object_empty(self):
        with self.assertRaises(TransactionError):
            res = self.manager.remove_object(objid='c1.o1.g1.*')

    def test_get_permission_all(self):
        res = self.manager.get_permission_by_id()

    def test_get_permission(self):
        res = self.manager.get_permission_by_object(objid='c1.o1.g1.*')
        res = self.manager.get_permission_by_object(objtype='service')
        res = self.manager.get_permission_by_object(objdef='container.org')
        res = self.manager.get_permission_by_object(objid='c1.o1.g1.*', 
                                                    objtype='resource', 
                                                    objdef='container.org.group.vm')
    
    def test_get_permission_empty(self):
        with self.assertRaises(QueryError):
            res = self.manager.get_permission_by_id(permission_id=0)

    # role
    def test_add_role(self):
        objid = id_gen()
        name = 'role1'
        description = 'role1'
        res = self.manager.add_role(objid, name, description)
        #self.assertEqual(res, True)
        
    def test_add_role_bis(self):
        objid = id_gen()
        name = 'role1'
        description = 'role1'
        with self.assertRaises(TransactionError):
            self.manager.add_role(objid, name, description)

    def test_get_role(self):
        name = 'role1'
        res = self.manager.get_role(name=name)

    def test_get_role_permission(self):
        name = 'role2'
        res = self.manager.get_role_permissions(name)

    def test_update_role(self):
        name = 'role1'
        new_name = 'role2'
        new_description = 'role2_desc'
        res = self.manager.update_role(name=name, new_name=new_name, 
                                       new_description=new_description, )
        self.assertEqual(res, True)

    def test_remove_role(self):
        res = self.manager.remove_role(name='role2')
        self.assertEqual(res, True)

    def test_append_role_permission(self):
        role = self.manager.get_role(name='role2')[0]
        perms1 = self.manager.get_permission_by_object(objid='c1.o1.g1.*')
        perms2 = self.manager.get_permission_by_object(objtype='service')
        res = self.manager.append_role_permissions(role, perms1)
        res = self.manager.append_role_permissions(role, perms2)
        self.assertEqual(res, True)
        
    def test_remove_role_permission(self):
        role = self.manager.get_role(name='role2')[0]
        perms1 = self.manager.get_permission_by_object(objid='c1.o1.g1.*')
        perms2 = self.manager.get_permission_by_object(objtype='service') 
        res = self.manager.remove_role_permission(role, perms1)
        res = self.manager.remove_role_permission(role, perms2)
        self.assertEqual(res, True)        
        
    def test_get_permission_roles(self):
        perms2 = self.manager.get_permission_by_object(objtype='service')[0]
        res = self.manager.get_permission_roles(perms2)

    # user
    def test_add_user(self):
        objid = id_gen()
        name = 'user1'
        user_type = 'user'
        roles = [self.manager.get_role(name='role2')[0]]
        active = True
        password = 'mypass'
        res = self.manager.add_user(objid, name, roles, 
                                    active=active, password=password)
        #self.assertEqual(res, True)

    def test_get_user(self):
        res = self.manager.get_user(name='user1')

    def test_get_user_roles(self):
        user, total = self.manager.get_user(name='admin@local')
        #print user[0].role[0].expiry_date
        res, total = self.manager.get_user_roles_with_expiry(user[0])
        print res[0]

    def test_get_role_users(self):
        role, total = self.manager.get_role(name='ApiSuperadmin')
        res = self.manager.get_role_users(role[0])
        print res

    def test_get_user_permissions(self):
        user = self.manager.get_user(name='user1')[0]
        res = self.manager.get_user_permissions(user)

    def test_get_user_permissions2(self):
        user = self.manager.get_user(name='user2')[0]
        res = self.manager.get_user_permissions(user)

    def test_verify_user_password(self):
        password = 'mypass'
        user = self.manager.get_user(name='user1')[0]
        res = self.manager.verify_user_password(user, password)
        self.assertEqual(res, True)

    def test_verify_user_password_bad(self):
        password = 'mypass1'
        user = self.manager.get_user(name='user1')[0]
        res = self.manager.verify_user_password(user, password)
        self.assertEqual(res, False)

    def test_update_user(self):
        name = 'user1'
        res = self.manager.update_user(name=name, new_name='user2', 
                                       new_description='user2_desc', 
                                       new_active=False, new_password='mypass2')
        self.assertEqual(res, True)

    def test_append_user_role(self):
        user = self.manager.get_user(name='user1')[0]
        if self.manager.add_role(id_gen(), 'role3', 'role3_desc'):
            role = self.manager.get_role(name='role3')[0]
        #self.manager.append_role_permission(role, 3, 6)
        res = self.manager.append_user_role(user, role)
        self.assertEqual(res, True)

    def test_append_user_role_bis(self):
        with self.assertRaises(TransactionError):
            user = self.manager.get_user(name='user1')[0]
            role = self.manager.get_role(name='role3')[0]
            res = self.manager.append_user_role(user, role)

    def test_remove_user_role(self):
        user = self.manager.get_user(name='user1')[0]
        role = self.manager.get_role(name='role3')[0]
        res = self.manager.remove_user_role(user, role)
        res = self.manager.remove_role(name='role3')
        self.assertEqual(res, True)

    def test_remove_user(self):
        res = self.manager.remove_user(username='user2')
        self.assertEqual(res, True)

    def test_set_attribute(self):
        user = self.manager.get_user(name='user2')[0]
        res = self.manager.set_user_attribute(user, 'attr1', 'value1', '')
        #self.assertEqual(res, True)

    def test_set_attribute_bis(self):
        user = self.manager.get_user(name='user2')[0]
        res = self.manager.set_user_attribute(user, 'attr1', 'value2', '')
        #self.assertEqual(res, True)

    def test_get_attribute(self):
        user = self.manager.get_user(name='user2')[0]
        self.logger.debug(user.attrib)
        #self.assertEqual(res, True)

    def test_remove_attribute(self):
        user = self.manager.get_user(name='user2')[0]
        res = self.manager.remove_user_attribute(user, 'attr1')
        self.assertEqual(res, True)        
    
    # group
    def test_add_group(self):
        name = 'group1'
        description = ''
        user_type = 'group'
        roles = [self.manager.get_role(name='role2')[0]]
        members = [self.manager.get_user(name='user2')[0]]
        active = True
        password = 'mypass'
        res = self.manager.add_group(id_gen(), name, description, members, roles)
        #self.assertEqual(res, True)

    def test_get_group(self):
        res = self.manager.get_group(name='group1')
        self.logger.debug(res)

    def test_get_group_roles(self):
        group = self.manager.get_group(name='group1')[0]
        res = self.manager.get_group_roles(group)

    def test_get_role_groups(self):
        role = self.manager.get_role(name='role2')[0]
        res = self.manager.get_role_groups(role)

    def test_get_group_members(self):
        group = self.manager.get_group(name='group1')[0]
        res = self.manager.get_group_members(group)

    def test_get_user_groups(self):
        user = self.manager.get_user(name='user2')[0]
        res = self.manager.get_user_groups(user)

    def test_get_group_permissions(self):
        group = self.manager.get_group(name='group1')[0]
        res = self.manager.get_group_permissions(group)

    def test_update_group(self):
        name = 'group1'
        new_name = 'group2'
        new_description = 'group2'
        res = self.manager.update_group(name=name, new_name=new_name, 
                                        new_description=new_description)
        self.assertEqual(res, True)

    def test_append_group_role(self):
        group = self.manager.get_group('group1')[0]
        if self.manager.add_role(id_gen(), 'role4', 'role4_desc'):
            role = self.manager.get_role(name='role4')[0]
        res = self.manager.append_group_role(group, role)
        self.assertEqual(res, True)

    def test_append_group_role_bis(self):
        with self.assertRaises(TransactionError):
            group = self.manager.get_group(name='group1')[0]
            role = self.manager.get_role(name='role4')[0]
            res = self.manager.append_group_role(group, role)
            self.assertEqual(res, False)

    def test_remove_group_role(self):
        group = self.manager.get_group(name='group1')[0]
        role = self.manager.get_role(name='role4')[0]
        res = self.manager.remove_group_role(group, role)
        res = self.manager.remove_role(name='role4')
        self.assertEqual(res, True)

    def test_append_group_member(self):
        group = self.manager.get_group(name='group1')[0]
        if self.manager.add_user(id_gen(), 'user3', [], active=True, 
                                 password='', description=''):
            user = self.manager.get_user(name='user3')[0]
        res = self.manager.append_group_member(group, user)
        self.assertEqual(res, True)

    def test_append_group_member_bis(self):
        with self.assertRaises(TransactionError):
            group = self.manager.get_group(name='group1')[0]
            user = self.manager.get_user(name='user3')[0]
            res = self.manager.append_group_member(group, user)
            self.assertEqual(res, False)

    def test_remove_group_member(self):
        group = self.manager.get_group(name='group1')[0]
        user = self.manager.get_user(name='user3')[0]
        res = self.manager.remove_group_memeber(group, user)
        res = self.manager.remove_user(username='user3')
        self.assertEqual(res, True)

    def test_remove_group(self):
        res = self.manager.remove_group(name='group2')
        self.assertEqual(res, True)

def test_suite():
    tests = [
        ##'test_remove_table',
        ##'test_create_table',
        ##'test_set_initial_data',
        # system object type
        ##'test_add_object_types',
        ##'test_get_object_type',
        ##'test_get_object_type_all',
        ##'test_get_type_empty',
        
        # system object action
        ##'test_get_object_action',             
        ##'test_add_object_actions',
        ##'test_get_object_action_all',
        
        # system object
        ##'test_add_object',
        ##'test_add_object_bis',
        ##'test_get_object_all',
        ##'test_get_object',
        ##'test_get_object_empty',
        
        # system object permission
        ##'test_get_permission_all',
        ##'test_get_permission',
        ##'test_get_permission_empty',          
        
        # role
        ##'test_add_role',
        #'test_add_role_bis',
        #'test_get_role',
        #'test_update_role',
        #'test_append_role_permission',
        #'test_append_role_permission',
        #'test_get_role_permission',
        #'test_get_permission_roles',
        
        # user
        #'test_add_user',
        #'test_get_user',
        #'test_get_user_roles',
        'test_get_role_users',
        #'test_get_user_permissions',
        #'test_verify_user_password',
        #'test_verify_user_password_bad',
        #'test_append_user_role',
        #'test_append_user_role_bis',
        'test_get_user_roles',
        #'test_remove_user_role',
        #'test_update_user',
        #'test_set_attribute',
        #'test_set_attribute_bis',
        #'test_get_attribute',             
        #'test_remove_attribute',
        
        # group
        #'test_add_group',
        #'test_get_group',
        #'test_get_group_roles',
        #'test_get_role_groups',
        #'test_get_group_members',
        #'test_get_user_groups',
        #'test_get_group_permissions',
        #'test_append_group_role',
        #'test_append_group_role_bis',
        #'test_append_group_member',
        #'test_append_group_member_bis',          
        #'test_get_group_roles',
        #'test_get_group_members',
        #'test_get_user_groups',
        #'test_get_user_permissions2',
        #'test_get_group_permissions',           
        #'test_remove_group_role',
        #'test_remove_group_member',
        #'test_update_group',
        
        # delete all
        #'test_remove_group',
        #'test_remove_user',
        #'test_remove_role_permission',
        #'test_remove_role',
        #'test_remove_object',
        #'test_remove_object_empty',
        #'test_remove_object_action',             
        #'test_remove_object_type',
    ]
    return unittest.TestSuite(map(AuthManagerTestCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())
    