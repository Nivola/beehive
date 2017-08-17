'''
Created on Aug 9, 2017

@author: darkbk
'''
import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, UnauthorizedException,\
    ConflictException

oid = None

tests = [
#     u'test_get_domains',
#     u'test_get_tokens',
#     u'test_get_token',
#     u'test_delete_token',
    
#     u'test_add_role',
#     u'test_add_role_twice',
#     u'test_get_roles',
#     u'test_get_roles_by_user',
#     u'test_get_role',
#     u'test_update_role',
#     u'test_add_role_perm',
#     u'test_get_perms_by_role',
#     u'test_remove_role_perm',
#     u'test_delete_role',    
    
    u'test_add_user',
    u'test_add_user_twice',
    u'test_get_users',
    u'test_get_users_by_role',
    u'test_get_user',
    u'test_add_user_attributes',
    u'test_get_user_attributes',    
    u'test_delete_user_attributes',
    u'test_update_user',
    u'test_add_user_role',
    u'test_get_perms_by_user',
    u'test_remove_user_role',
    u'test_delete_user',
    
#     u'test_add_group',
#     u'test_add_group_twice',
#     u'test_get_groups',
#     u'test_get_group',
#     u'test_update_group',
#     u'test_add_group_user',
#     u'test_get_groups_by_user',    
#     u'test_remove_group_user',
#     u'test_add_group_role',
#     u'test_get_groups_by_role',
#     u'test_get_perms_by_group',
#     u'test_remove_group_role',    
#     u'test_delete_group',
    
#     u'test_get_actions',
# 
#     u'test_add_type',
#     u'test_add_type_twice',
#     u'test_get_types',
#     u'test_delete_type',
# 
#     u'test_add_object',
#     u'test_add_object_twice',
#     u'test_get_objects',
#     u'test_get_object',
#     u'test_delete_object',
# 
#     u'test_get_perms',
#     u'test_get_perms_by_type',
# 
#     u'test_get_perms_by_user',
#     
#     u'test_get_perm',
]

class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # domains
    #
    def test_get_domains(self):
        self.call(u'auth', u'/v1.0/auth/domains', u'get')

    #
    # tokens
    #
    def test_get_tokens(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/tokens', u'get', 
                        **self.users[u'admin'])
        oids = res[u'tokens']
        if len(oids) > 0:
            oid = oids[0][u'token']
    
    def test_get_token(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/tokens/{oid}', u'get', 
                  params={u'oid':oid},
                  **self.users[u'admin'])
        
    def test_delete_token(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/tokens/{oid}', u'delete', 
                  params={u'oid':oid},
                  **self.users[u'admin'])         

    #
    # roles
    #
    def test_add_role(self):
        data = {
            u'role':{
                u'name':u'role_prova',
                u'desc':u'role_prova',
                u'active':True,
                #u'expiry-date':u'2099-12-31T'
            }
        }        
        self.call(u'auth', u'/v1.0/auth/roles', u'post', data=data,
                  **self.users[u'admin'])
    
    @assert_exception(BadRequestException)
    def test_add_role_twice(self):
        data = {
            u'role':{
                u'name':u'role_prova',
                u'desc':u'role_prova',
            }
        }        
        self.call(u'auth', u'/v1.0/auth/roles', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_roles(self):
        self.call(u'auth', u'/v1.0/auth/roles', u'get', 
                  **self.users[u'admin'])
        
    def test_get_roles_by_user(self):
        self.call(u'auth', u'/v1.0/auth/roles', u'get',
                  query={u'user':4},
                  **self.users[u'admin'])        
        
    def test_get_role(self):
        self.call(u'auth', u'/v1.0/auth/roles/{oid}', u'get',
                  params={u'oid':4}, 
                  **self.users[u'admin'])
        
    def test_update_role(self):
        data = {
            u'role':{
                u'name':u'role_prova',
                u'desc':u'role_prova1',
            }
        }
        self.call(u'auth', u'/v1.0/auth/roles/{oid}', u'put', 
                  params={u'oid':u'role_prova'}, data=data,
                  **self.users[u'admin'])        
        
    def test_add_role_perm(self):
        data = {
            u'role':{
                u'perms':{u'append':[4]}
            }
        }
        self.call(u'auth', u'/v1.0/auth/roles/{oid}', u'put',
                  params={u'oid':u'role_prova'}, data=data,
                  **self.users[u'admin'])
        
    def test_get_perms_by_role(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/objects/perms', u'get',
                        query={u'role':u'role_prova'},
                        **self.users[u'admin'])        
        
    def test_remove_role_perm(self):
        data = {
            u'role':{
                u'perms':{u'remove':[4]}
            }
        }        
        self.call(u'auth', u'/v1.0/auth/roles/{oid}', u'put',
                  params={u'oid':u'role_prova'}, data=data,
                  **self.users[u'admin'])     
        
    def test_delete_role(self):
        self.call(u'auth', u'/v1.0/auth/roles/{oid}', u'delete', 
                  params={u'oid':u'role_prova'},
                  **self.users[u'admin'])  

    #
    # users
    #
    def test_add_user(self):
        data = {
            u'user':{
                u'name':u'user_prova@local',
                u'desc':u'user_prova',
                u'active':True,
                u'expiry-date':u'2099-12-31',
                u'password':u'user_prova',
                u'base':True
            }
        }        
        self.call(u'auth', u'/v1.0/auth/users', u'post', data=data,
                  **self.users[u'admin'])
    
    @assert_exception(BadRequestException)
    def test_add_user_twice(self):
        data = {
            u'user':{
                u'name':u'user_prova@local',
                u'desc':u'user_prova',
                u'active':True,
                u'expiry-date':u'2099-12-31',
                u'password':u'user_prova',
                u'base':True
            }
        }       
        self.call(u'auth', u'/v1.0/auth/users', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_users(self):
        self.call(u'auth', u'/v1.0/auth/users', u'get', 
                  **self.users[u'admin'])
        
    def test_get_users_by_role(self):
        self.call(u'auth', u'/v1.0/auth/users', u'get',
                  query={u'role':4},
                  **self.users[u'admin'])        
        
    def test_get_user(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'get',
                  params={u'oid':u'user_prova@local'}, 
                  **self.users[u'admin'])
        
    def test_add_user_attributes(self):
        data = {
            u'user-attribute':{
                u'name':u'attr_prova',
                u'value':u'attr_prova_value',
                u'desc':u'attr_prova_desc'
            }
        }
        self.call(u'auth', u'/v1.0/auth/users/{oid}/attributes', u'post',
                  params={u'oid':u'user_prova@local'}, data=data,
                  **self.users[u'admin'])
        
    def test_get_user_attributes(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}/attributes', u'get',
                  params={u'oid':u'user_prova@local'}, 
                  **self.users[u'admin'])
          
    def test_delete_user_attributes(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}/attributes/{aid}', u'delete',
                  params={u'oid':u'user_prova@local', u'aid':u'attr_prova'},
                  **self.users[u'admin'])
    
    def test_update_user(self):
        data = {
            u'user':{
                u'desc':u'user_prova1',
            }
        }
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'put', 
                  params={u'oid':u'user_prova@local'}, data=data,
                  **self.users[u'admin'])        
        
    def test_add_user_role(self):
        data = {
            u'user':{
                u'roles':{u'append':[(u'4', u'2099-12-31')]}
            }
        }
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'put',
                  params={u'oid':u'user_prova@local'}, data=data,
                  **self.users[u'admin'])
        
    def test_get_perms_by_user(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/objects/perms', u'get',
                        query={u'user':u'user_prova@local'},
                        **self.users[u'admin'])        
        
    def test_remove_user_role(self):
        data = {
            u'user':{
                u'roles':{u'remove':[u'4']}
            }
        }        
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'put',
                  params={u'oid':u'user_prova@local'}, data=data,
                  **self.users[u'admin'])     
        
    def test_delete_user(self):
        self.call(u'auth', u'/v1.0/auth/users/{oid}', u'delete', 
                  params={u'oid':u'user_prova@local'},
                  **self.users[u'admin'])  
    
    #
    # groups
    #
    def test_add_group(self):
        data = {
            u'group':{
                u'name':u'grp_prova',
                u'desc':u'grp_prova',
                u'active':True,
                #u'expiry-date':u'2099-12-31'
            }
        }        
        self.call(u'auth', u'/v1.0/auth/groups', u'post', data=data,
                  **self.users[u'admin'])
    
    @assert_exception(BadRequestException)
    def test_add_group_twice(self):
        data = {
            u'group':{
                u'name':u'grp_prova',
                u'desc':u'grp_prova',
                u'active':True
            }
        }        
        self.call(u'auth', u'/v1.0/auth/groups', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_groups(self):
        self.call(u'auth', u'/v1.0/auth/groups', u'get', 
                  **self.users[u'admin'])
        
    def test_get_group(self):
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'get',
                  params={u'oid':u'grp_prova'}, 
                  **self.users[u'admin'])
        
    def test_update_group(self):
        data = {
            u'group':{
                u'name':u'grp_prova',
                u'desc':u'grp_prova',
                u'active':True,
                #u'expiry-date':u'2099-12-31T'
            }
        }
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'put', 
                  params={u'oid':u'grp_prova'}, data=data,
                  **self.users[u'admin'])        
        
    def test_add_group_user(self):
        data = {
            u'group':{
                u'users':{u'append':[u'admin@local']}
            }
        }
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'put',
                  params={u'oid':u'grp_prova'}, data=data,
                  **self.users[u'admin'])

    def test_get_groups_by_user(self):
        self.call(u'auth', u'/v1.0/auth/groups', u'get',
                  query={u'user':u'admin@local'}, 
                  **self.users[u'admin'])
        
    def test_remove_group_user(self):
        data = {
            u'group':{
                u'users':{u'remove':[u'admin@local']}
            }
        }        
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'put',
                  params={u'oid':u'grp_prova'}, data=data,
                  **self.users[u'admin'])     
        
    def test_add_group_role(self):
        data = {
            u'group':{
                u'roles':{u'append':[u'Guest']}
            }
        }
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'put',
                  params={u'oid':u'grp_prova'}, data=data,
                  **self.users[u'admin'])

    def test_get_groups_by_role(self):
        self.call(u'auth', u'/v1.0/auth/groups', u'get',
                  query={u'role':u'Guest'}, 
                  **self.users[u'admin'])
        
    def test_get_perms_by_group(self):
        self.call(u'auth', u'/v1.0/auth/objects/perms', u'get',
                        query={u'group':u'grp_prova'},
                        **self.users[u'admin'])        
        
    def test_remove_group_role(self):
        data = {
            u'group':{
                u'roles':{u'remove':[u'Guest']}
            }
        }        
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'put',
                  params={u'oid':u'grp_prova'}, data=data,
                  **self.users[u'admin'])
        
    def test_delete_group(self):
        self.call(u'auth', u'/v1.0/auth/groups/{oid}', u'delete', 
                  params={u'oid':u'grp_prova'},
                  **self.users[u'admin'])  

    #
    # actions
    #
    def test_get_actions(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/objects/actions', u'get', 
                  **self.users[u'admin'])

    #
    # types
    #
    def test_add_type(self):
        global oid
        data = {
            u'object-types':[
                {
                    u'subsystem':u'prova',
                    u'type':u'prova',
                }
            ]
        }        
        res = self.call(u'auth', u'/v1.0/auth/objects/types', u'post', data=data,
                  **self.users[u'admin'])
        oid = res[u'ids'][0]
    
    @assert_exception(BadRequestException)
    def test_add_type_twice(self):
        data = {
            u'object-types':[
                {
                    u'subsystem':u'prova',
                    u'type':u'prova',
                }
            ]
        }        
        self.call(u'auth', u'/v1.0/auth/objects/types', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_types(self):
        res = self.call(u'auth', u'/v1.0/auth/objects/types', u'get', 
                  **self.users[u'admin'])

    def test_delete_type(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/objects/types/{oid}', u'delete', 
                  params={u'oid':oid},
                  **self.users[u'admin']) 

    #
    # objects
    #
    def test_add_object(self):
        global oid
        data = {
            u'objects':[{
                u'subsystem':u'auth', 
                u'type':u'Role', 
                u'objid':u'prova', 
                u'desc':u'prova'        
            }]
        }        
        res = self.call(u'auth', u'/v1.0/auth/objects', u'post', data=data,
                  **self.users[u'admin'])
        oid = res[u'id']
    
    @assert_exception(ConflictException)
    def test_add_object_twice(self):
        data = {
            u'objects':[{
                u'subsystem':u'auth', 
                u'type':u'Role', 
                u'objid':u'prova', 
                u'desc':u'prova'        
            }]
        }        
        self.call(u'auth', u'/v1.0/auth/objects', u'post', data=data,
                  **self.users[u'admin'])        
    
    def test_get_objects(self):
        self.call(u'auth', u'/v1.0/auth/objects', u'get', 
                  **self.users[u'admin'])
        
    def test_get_object(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/objects/{oid}', u'get',
                  params={u'oid':oid}, 
                  **self.users[u'admin'])

    def test_delete_object(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/objects/{oid}', u'delete', 
                  params={u'oid':oid},
                  **self.users[u'admin'])
        
    #
    # perms
    #
    def test_get_perms(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/objects/perms', u'get', 
                  **self.users[u'admin'])
        oids = res[u'perms']
        if len(oids) > 0:
            oid = oids[0][u'oid']
            
    def test_get_perms_by_type(self):
        global oid
        res = self.call(u'auth', u'/v1.0/auth/objects/perms', u'get',
                        query={u'subsystem':u'auth', u'type':u'Role', u'page':1},
                        **self.users[u'admin'])
        
    def test_get_perm(self):
        global oid
        self.call(u'auth', u'/v1.0/auth/objects/perms/{oid}', u'get',
                  params={u'oid':oid}, 
                  **self.users[u'admin'])    

if __name__ == u'__main__':
    runtest(AuthObjectTestCase, tests)      