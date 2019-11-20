# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, UnauthorizedException,\
    ConflictException

oid = None

tests = [
    'test_add_role',
    'test_add_role_twice',
    'test_get_roles',
    'test_get_role',
    'test_update_role',
    'test_add_role_perm',
    'test_get_perms_by_role',
    'test_remove_role_perm',
    'test_delete_role',
    
    'test_add_user',
    'test_add_user_twice',
    'test_get_users',
    'test_get_users_by_role',
    'test_get_user',
    'test_get_user_secret',
    'test_get_user_roles',
    'test_add_user_attributes',
    'test_get_user_attributes',
    'test_delete_user_attributes',
    'test_update_user',
    'test_add_user_role',
    'test_get_perms_by_user',
    'test_remove_user_role',
    'test_delete_user',

    'test_add_group',
    'test_add_group_twice',
    'test_get_groups',
    'test_get_group',
    'test_update_group',
    'test_add_group_user',
    'test_get_groups_by_user',
    'test_remove_group_user',
    'test_add_group_role',
    'test_get_groups_by_role',
    'test_get_perms_by_group',
    'test_remove_group_role',
    'test_delete_group',

    'test_get_actions',

    'test_add_type',
    'test_add_type_twice',
    'test_get_types',
    'test_delete_type',

    'test_add_object',
    'test_add_object_twice',
    'test_get_objects',
    'test_get_object',
    'test_get_objects_by_objid',
    'test_delete_object',

    'test_get_perms',
    'test_get_perms_by_type',
    'test_get_perm',

    'test_get_providers',
    'test_get_tokens',
    'test_get_token',
    'test_delete_token',
]


class AuthTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'auth'
        self.module_prefix = 'nas'
        self.endpoint_service = 'auth'
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # domains
    #
    def test_get_providers(self):
        self.get('/v1.0/nas/providers')

    #
    # tokens
    #
    def test_get_tokens(self):
        global oid
        res = self.get('/v1.0/nas/tokens')
        oids = res['tokens']
        if len(oids) > 0:
            oid = oids[0]['token']
    
    def test_get_token(self):
        global oid
        self.get('/v1.0/nas/tokens/{oid}', params={'oid': oid})
        
    def test_delete_token(self):
        global oid
        self.delete('/v1.0/nas/tokens/{oid}', params={'oid': oid})

    #
    # roles
    #
    def test_add_role(self):
        data = {
            'role': {
                'name': 'role_prova',
                'desc': 'role_prova',
                'alias': 'prova'
            }
        }
        self.post('/v1.0/nas/roles', data=data)
    
    @assert_exception(ConflictException)
    def test_add_role_twice(self):
        data = {
            'role': {
                'name': 'role_prova',
                'desc': 'role_prova',
                'alias': 'prova'
            }
        }        
        self.post('/v1.0/nas/roles', data=data)
    
    def test_get_roles(self):
        self.get('/v1.0/nas/roles')
        
    def test_get_role(self):
        self.get('/v1.0/nas/roles', params={'oid': 'role_prova'})
        
    def test_update_role(self):
        data = {
            'role': {
                'name': 'role_prova',
                'desc': 'role_prova1',
            }
        }
        self.put('/v1.0/nas/roles/{oid}', params={'oid': 'role_prova'}, data=data)
        
    def test_add_role_perm(self):
        data = {
            'role': {
                'perms': {
                    'append': [
                        {'subsystem': 'auth', 'type': 'Role', 'objid': '*', 'action': 'view'}]}
            }
        }
        self.put('/v1.0/nas/roles/{oid}', params={'oid': 'role_prova'}, data=data)
        
    def test_get_perms_by_role(self):
        global oid
        self.get('/v1.0/nas/objects/perms', params={'oid': 'role_prova'})

    def test_remove_role_perm(self):
        data = {
            'role': {
                'perms': {
                    'remove': [
                        {'subsystem': 'auth', 'type': 'Role', 'objid': '*', 'action': 'view'}]}
            }
        }
        self.put('/v1.0/nas/roles/{oid}', params={'oid': 'role_prova'}, data=data)
        
    def test_delete_role(self):
        self.delete('/v1.0/nas/roles/{oid}', params={'oid': 'role_prova'})

    #
    # users
    #
    def test_add_user(self):
        data = {
            'user': {
                'name': 'user_prova@local',
                'email': 'user_prova@local',
                'desc': 'user_prova',
                'active': True,
                'expirydate': '2099-12-31',
                'password': 'user_prova',
                'base': True,
            }
        }
        self.post('/v1.0/nas/users', data=data)
    
    @assert_exception(ConflictException)
    def test_add_user_twice(self):
        data = {
            'user': {
                'name': 'user_prova@local',
                'email': 'user_prova@local',
                'desc': 'user_prova',
                'active': True,
                'expirydate': '2019-12-31',
                'password': 'user_prova',
                'base': True
            }
        }       
        self.post('/v1.0/nas/users', data=data)
    
    def test_get_users(self):
        self.get('/v1.0/nas/users', query={'page': 0})

    def test_get_users_by_role(self):
        self.get('/v1.0/nas/users', query={'role': 'Guest'})

    def test_get_user(self):
        self.get('/v1.0/nas/users/{oid}', params={'oid': 'user_prova@local'})

    def test_get_user_secret(self):
        self.get('/v1.0/nas/users/{oid}/secret', params={'oid': 'user_prova@local'})

    def test_get_user_roles(self):
        self.get('/v1.0/nas/roles', params={'oid': 'user_prova@local'})

    def test_add_user_attributes(self):
        data = {
            'user_attribute': {
                'name': 'attr_prova',
                'value': 'attr_prova_value',
                'desc': 'attr_prova_desc'
            }
        }
        self.post('/v1.0/nas/users/{oid}/attributes', params={'oid': 'user_prova@local'}, data=data)
        
    def test_get_user_attributes(self):
        self.get('/v1.0/nas/users/{oid}/attributes', params={'oid': 'user_prova@local'})
          
    def test_delete_user_attributes(self):
        self.delete('/v1.0/nas/users/{oid}/attributes/{aid}', params={'oid': 'user_prova@local', 'aid': 'attr_prova'})

    def test_update_user(self):
        data = {
            'user': {
                'desc': 'user_prova1',
            }
        }
        self.put('/v1.0/nas/users/{oid}', params={'oid': 'user_prova@local'}, data=data)
        
    def test_add_user_role(self):
        data = {
            'user': {
                'roles': {'append': [('Guest', '2019-12-31')]}
            }
        }
        self.put('/v1.0/nas/users/{oid}', params={'oid': 'user_prova@local'}, data=data)
        
    def test_get_perms_by_user(self):
        global oid
        self.get('/v1.0/nas/objects/perms', query={'oid': 'user_prova@local'})
        
    def test_remove_user_role(self):
        data = {
            'user': {
                'roles': {'remove': ['Guest']}
            }
        }        
        self.put('/v1.0/nas/users/{oid}', params={'oid': 'user_prova@local'}, data=data)

    def test_delete_user(self):
        self.delete('/v1.0/nas/users/{oid}', params={'oid': 'user_prova@local'})

    #
    # groups
    #
    def test_add_group(self):
        data = {
            'group': {
                'name': 'grp_prova',
                'desc': 'grp_prova',
                'active': True,
            }
        }
        self.post('/v1.0/nas/groups', data=data)

    @assert_exception(ConflictException)
    def test_add_group_twice(self):
        data = {
            'group': {
                'name': 'grp_prova',
                'desc': 'grp_prova',
                'active': True
            }
        }
        self.post('/v1.0/nas/groups', data=data)

    def test_get_groups(self):
        self.get('/v1.0/nas/groups')

    def test_get_group(self):
        self.get('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'})

    def test_update_group(self):
        data = {
            'group': {
                'name': 'grp_prova',
                'desc': 'grp_prova',
                'active': True,
            }
        }
        self.put('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'}, data=data)
        
    def test_add_group_user(self):
        data = {
            'group': {
                'users': {'append': ['admin@local']}
            }
        }
        self.put('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'}, data=data)

    def test_get_groups_by_user(self):
        self.get('/v1.0/nas/groups', query={'user': 'admin@local'})
        
    def test_remove_group_user(self):
        data = {
            'group': {
                'users': {'remove': ['admin@local']}
            }
        }
        self.put('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'}, data=data)
        
    def test_add_group_role(self):
        data = {
            'group': {
                'roles': {'append': [('ApiSuperAdmin', '2019-12-31')]}
            }
        }
        self.put('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'}, data=data)

    def test_get_groups_by_role(self):
        self.get('/v1.0/nas/groups', query={'role': 'ApiSuperAdmin'})
        
    def test_get_perms_by_group(self):
        self.get('/v1.0/nas/objects/perms', query={'group': 'grp_prova'})
        
    def test_remove_group_role(self):
        data = {
            'group': {
                'roles': {'remove': ['ApiSuperAdmin']}
            }
        }
        self.put('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'}, data=data)

    def test_delete_group(self):
        self.delete('/v1.0/nas/groups/{oid}', params={'oid': 'grp_prova'})

    #
    # actions
    #
    def test_get_actions(self):
        global oid
        self.get('/v1.0/nas/objects/actions')

    #
    # types
    #
    def test_add_type(self):
        global oid
        data = {
            'object_types': [
                {
                    'subsystem': 'prova',
                    'type': 'prova',
                }
            ]
        }
        res = self.post('/v1.0/nas/objects/types', data=data)
        oid = res['ids'][0]

    def test_add_type_twice(self):
        data = {
            'object_types': [
                {
                    'subsystem': 'prova',
                    'type': 'prova',
                }
            ]
        }
        self.post('/v1.0/nas/objects/types', data=data)

    def test_get_types(self):
        self.get('/v1.0/nas/objects/types')

    def test_delete_type(self):
        global oid
        self.delete('/v1.0/nas/objects/types/{oid}', params={'oid': oid})

    #
    # objects and perms
    #
    def test_add_object(self):
        global oid
        data = {
            'objects': [{
                'subsystem': 'auth',
                'type': 'Role',
                'objid': 'prova',
                'desc': 'prova'
            }]
        }
        res = self.post('/v1.0/nas/objects', data=data)
        oid = res['ids'][0]
    
    @assert_exception(ConflictException)
    def test_add_object_twice(self):
        data = {
            'objects': [{
                'subsystem': 'auth',
                'type': 'Role',
                'objid': 'prova',
                'desc': 'prova'
            }]
        }
        self.post('/v1.0/nas/objects', data=data)

    def test_get_objects(self):
        self.get('/v1.0/nas/objects')

    def test_get_objects_by_objid(self):
        global oid
        res = self.get('/v1.0/nas/objects', query={'objid': 'prova'})
        oid = res['objects'][0]['id']

    def test_get_object(self):
        global oid
        self.get('/v1.0/nas/objects/{oid}', params={'oid': oid})

    def test_delete_object(self):
        global oid
        self.delete('/v1.0/nas/objects/{oid}', params={'oid': oid})

    def test_get_perms(self):
        global oid
        res = self.get('/v1.0/nas/objects/perms')
        oids = res['perms']
        if len(oids) > 0:
            oid = oids[0]['id']
            
    def test_get_perms_by_type(self):
        self.get('/v1.0/nas/objects/perms', query={'subsystem': 'auth', 'type': 'Role', 'page': 1})
        
    def test_get_perm(self):
        global oid
        self.get('/v1.0/nas/objects/perms/{oid}', params={'oid': oid})


def run(args):
    runtest(AuthTestCase, tests, args)


if __name__ == '__main__':
    run({})
