'''
Created on Sep 2, 2013

@author: darkbk
'''
import json
import unittest
import tests.test_util
from beehive.common.test import runtest, BeehiveTestCase

seckey = None
objid = None

obj = 31813

class AuthTestCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        #self.auth_client = AuthClient()
        self.api_id = u'api'
        self.user = u'admin@local'
        self.user1 = u'camunda@local'
        self.ip = u'158.102.160.234'
        self.pwd = u'testlab'
        self.pwd1 = u'camunda'
        self.baseuri = u'/v1.0/keyauth'
        self.baseuri1 = u'/v1.0/simplehttp'
        self.baseuri2 = u'/v1.0/auth'
        self.credentials = u'%s:%s' % (self.user1, self.pwd1)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
    
    #
    # simplehttp
    #
    def test_get_simple_http_login_domains(self):
        uri = u'%s/login/domains/' % self.baseuri1
        res = self.invoke_no_sign(u'auth', uri, u'GET', data='')
        self.logger.info(json.dumps(res, indent=4))
        
    def test_get_simple_http_users(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'name'}
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter,
                          auth_method=u'simplehttp', 
                          credentials=self.credentials)
        self.logger.info(json.dumps(res, indent=4))
    
    #
    # keyauth
    #
    def test_get_login_domains(self):
        uri = u'%s/login/domains/' % self.baseuri
        res = self.invoke_no_sign(u'auth', uri, u'GET', data='')
        self.logger.info(json.dumps(res, indent=4))   

    def test_refresh(self):
        uri = u'%s/login/refresh/' % self.baseuri
        res = self.invoke(u'auth', uri, u'PUT', data='')
        self.logger.info(json.dumps(res, indent=4))

    def test_exist_identity(self):
        uri = u'%s/login/%s/' % (self.baseuri, tests.test_util.uid)
        res = self.invoke(u'auth', uri, u'GET', data='')
        self.logger.info(json.dumps(res, indent=4))

    #
    # identity
    #
    def test_get_identities(self):      
        data = ''
        uri = u'%s/identities/' % self.baseuri2
        res = self.invoke(u'auth', uri, u'GET', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_identity(self):
        data = ''
        uri = u'%s/identities/%s/' % (self.baseuri2, tests.test_util.uid)
        res = self.invoke(u'auth', uri, u'GET', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_delete_identity(self):
        data = ''
        identity = u'9sglCzsNTUECVYkC5YDZ'
        uri = u'%s/identities/%s/' % (self.baseuri2, identity)
        res = self.invoke(u'auth', uri, u'DELETE', data=data)
        self.logger.info(json.dumps(res, indent=4))
        
    #
    # objects
    #
    def test_get_objects(self):
        uri = u'/v1.0/auth/objects/'
        ofilter = {u'page':0, u'size':20, u'order':u'ASC', u'field':u'type'}
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_objects_by_id(self):
        uri = u'/v1.0/auth/objects/%s/' % 31600
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_objects_by_objid(self):
        uri = u'/v1.0/auth/objects/'
        ofilter = {u'objid':u'754aee5c9ba528024e40//ccc524e70ba5c7372592//*'}
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_objects_by_subsystem(self):
        uri = u'/v1.0/auth/objects/'
        ofilter = {u'subsystem':u'auth'}
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_objects_by_type(self):
        uri = u'/v1.0/auth/objects/'
        ofilter = {u'type':u'openstack'}
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_objects_by_type_and_objid(self):
        uri = u'/v1.0/auth/objects/'
        ofilter = {u'type':u'Role', u'objid':u'prova'}
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_add_object(self):
        global obj
        data = {
            u'objects':[
                {
                    u'subsystem':u'auth', 
                    u'type':u'Role', 
                    u'objid':u'prova', 
                    u'desc':u'prova'        
                }
            ]
        }
        uri = u'/v1.0/auth/objects/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))
        obj = res[u'objects'][0][u'id']

    def test_del_object(self):
        global obj
        uri = u'/v1.0/auth/objects/%s/' % obj
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    #
    # object permissions
    #
    def test_get_object_permissions(self):
        ofilter = {u'page':0, u'size':20, u'order':u'ASC', u'field':u'type',
                   u'subsystem':u'resource', u'type':u'Container.CustomResource'}
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))       
    
    def test_get_object_permission(self):
        uri = u'/v1.0/auth/objects/perms/%s/' % 31747
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_object_permissions_with_filter(self):
        ofilter = {u'order':u'ASC', u'field':u'subsystem'}
        ofilter = {u'objid':u'a3ac12fa3e9a72b75a39//fa4e5d2ab9505468748d//d15630aeddcb982d425d'}
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4)) 

    #
    # object type
    #
    def test_get_object_types(self):
        uri = u'/v1.0/auth/objects/types/'
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))
    
    def test_filter_object_types(self):
        ofilter = {u'order':u'ASC', u'field':u'type', 
                   u'subsystem':u'resource'}
        uri = u'/v1.0/auth/objects/types/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))    
    
    def test_add_object_type(self):
        data = {
            u'object-types':[
                {
                    u'subsystem':u'prova',
                    u'type':u'prova',
                }
            ]
        }
        uri = u'/v1.0/auth/objects/types/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_del_object_type(self):
        uri = u'/v1.0/auth/objects/types/%s/' % 883
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    #
    # actions
    #
    def test_get_object_actions(self):
        uri = u'/v1.0/auth/objects/actions/'
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))
    
    #
    # users
    #
    def test_get_users(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'name'}
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))
        
    def test_get_user(self):
        uri = u'/v1.0/auth/users/%s/' % 31
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_user_perms(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'id',
                   u'user':31}
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))
        
    def test_get_user_roles(self):
        ofilter = {u'user':u'prova5@local'}
        uri = u'/v1.0/auth/roles/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))
        
    def test_get_user_groups(self):
        ofilter = {u'user':u'admin@local'}
        uri = u'/v1.0/auth/groups/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_user_attribs(self):
        uri = u'/v1.0/auth/users/%s/attributes/' % u'prova5@local'
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_user_can(self):
        user = 'test1@local'
        action = 'view'
        obj_type = 'cloudapi.orchestrator.org.area.vm'

        uri = u'/v1.0/auth/users/%s/can/%s:%s/' % (user, obj_type, action)
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_add_user(self):
        data = {
            u'user':{
                u'name':u'prova5@local', 
                u'storetype':u'DBUSER',
                u'systype':u'USER',
                u'active':True, 
                u'password':u'prova', 
                u'desc':''
            }
        } 
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_add_generic_user(self):
        data = {
            u'user':{
                u'name':u'prova53@local', 
                u'storetype':u'DBUSER',
                u'password':u'prova', 
                u'desc':u'',
                u'generic':True}
        }
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_add_system_user(self):
        data = {
            u'user':{
                u'name':u'prova54@local',
                u'password':u'prova', 
                u'description':u'', 
                u'system':True
            }
        }
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_update_user(self):
        data = {
            u'user':{
                u'desc':u'prova',
                u'roles':{
                    u'append':[], 
                    u'remove':[u'ApiSuperAdmin']
                }
            }
        }
        uri = u'/v1.0/auth/users/%s/' % u'prova5@local'
        res = self.invoke(u'auth', uri, u'PUT', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_del_user(self):
        uri = u'/v1.0/auth/users/%s/' % u'prova53@local'
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_set_user_attrib(self):
        data = {
            u'user-attribute':{
                u'name':u'test',
                u'value':u'test1',
                u'desc':u'test2'
            }
        }
        uri = u'/v1.0/auth/users/%s/attributes/' % u'prova5@local'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_remove_user_attrib(self):
        uri = u'/v1.0/auth/users/%s/attributes/%s/' % (u'prova5@local', u'test')
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    #
    # roles
    #
    def test_get_roles(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'objid'}
        uri = u'/v1.0/auth/roles/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_role(self):
        uri = u'/v1.0/auth/roles/%s/' % u'prova1_role'
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_role_perms(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'id', 
                   u'role':u'ApiSuperadmin'}
        uri = u'/v1.0/auth/objects/perms/' 
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))     

    def test_get_role_users(self):
        ofilter = {u'role':u'ApiSuperadmin'}
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_role_groups(self):
        ofilter = {u'role':u'ApiSuperadmin'}
        uri = u'/v1.0/auth/groups/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_add_role(self):
        data = {
            u'role':{
                u'name':u'prova_role', 
                u'desc':u'prova_role'
            }
        }
        uri = u'/v1.0/auth/roles/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_update_role(self):
        data = {
            u'role':{
                u'name':u'prova1_role', 
                u'desc':u'prova1_role',
                u'perms':{
                    u'append':[
                        (0, 0, u'resource', u'Openstack.Domain', u'*//*', 0, u'view')
                    ], 
                    u'remove':[
                        #(0, 0, u'resource', u'Openstack.Domain', u'*//*', 0, u'view')
                    ]
                }              
            }
        }        
        uri = u'/v1.0/auth/roles/%s/' % u'prova1_role'
        res = self.invoke(u'auth', uri, u'PUT', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_del_role(self):
        data = ''
        uri = u'/v1.0/auth/roles/%s/' % u'prova1_role'
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    #
    # groups
    #
    def test_get_groups(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'objid'}
        uri = u'/v1.0/auth/groups/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_group(self):
        uri = u'/v1.0/auth/groups/%s/' % u'prova_group'
        res = self.invoke(u'auth', uri, u'GET', data=u'')
        self.logger.info(json.dumps(res, indent=4))

    def test_get_group_perms(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'id',
                   u'group':u'prova1_group'}
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_group_roles(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'id',
                   u'group':u'prova_group'}
        uri = u'/v1.0/auth/roles/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_get_group_users(self):
        ofilter = {u'page':0, u'size':5, u'order':u'ASC', u'field':u'id',
                   u'group':u'prova_group'}        
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'GET', data=u'', filter=ofilter)
        self.logger.info(json.dumps(res, indent=4))

    def test_add_group(self):
        data = {
            u'group':{
                u'name':u'prova_group', 
                u'desc':u'prova_group'
            }
        }
        uri = u'/v1.0/auth/groups/'
        res = self.invoke(u'auth', uri, u'POST', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_update_group(self):
        data = {
            u'group':{
                u'name':u'prova_group', 
                u'desc':u'prova1_group',
                u'users':{
                    u'append':[
                        u'admin@local'
                    ], 
                    u'remove':[
                        
                    ]
                },
                u'roles':{
                    u'append':[
                        u'ApiSuperAdmin'
                    ], 
                    u'remove':[
                        
                    ]
                },                                
            }
        }        
        uri = u'/v1.0/auth/groups/%s/' % u'prova_group'
        res = self.invoke(u'auth', uri, u'PUT', data=data)
        self.logger.info(json.dumps(res, indent=4))

    def test_del_group(self):
        uri = u'/v1.0/auth/groups/%s/' % u'prova_group'
        res = self.invoke(u'auth', uri, u'DELETE', data=u'')
        self.logger.info(json.dumps(res, indent=4))

def test_suite():
    tests = [
        #'test_get_simple_http_login_domains',
        #'test_simple_http_login',
        #'test_get_simple_http_users',
        
        #'test_get_login_domains',
        'test_login',
        
        #'test_refresh',
        #'test_exist_identity',
        'test_get_identities',
        #'test_get_identity',
        #'test_delete_identity',
        
        #'test_get_objects',
        #'test_get_objects_by_id',
        #'test_get_objects_by_objid',
        #'test_get_objects_by_subsystem',
        #'test_get_objects_by_type',
        #'test_get_objects_by_type_and_objid',        
        #'test_add_object',
        #'test_del_object',
        
        #'test_get_object_permissions',        
        #'test_get_object_permission',
        #'test_get_object_permissions_with_filter',
        
        #'test_get_object_types',
        #'test_filter_object_types',        
        #'test_add_object_type',
        #'test_del_object_type',
        
        #'test_get_object_actions',
        
        #'test_get_roles',
        #'test_get_role',
        #'test_get_role_perms',
        #'test_get_role_users',
        #'test_get_role_groups'
        #'test_add_role',
        #'test_update_role',
        #'test_del_role',
        
        #'test_get_groups',
        #'test_get_group',
        #'test_get_group_perms',
        #'test_get_group_roles',
        #'test_get_group_users',
        #'test_add_group',
        #'test_update_group',
        #'test_del_group',          
           
        #'test_get_users',
        #'test_get_user',
        #####'test_get_user_can', 
        #'test_get_user_perms',
        #'test_get_user_roles',
        #'test_get_user_groups',
        #'test_get_user_attribs',
        #'test_add_user',
        #'test_add_generic_user',
        #'test_add_system_user',
        #'test_update_user',
        #'test_del_user',
        #'test_set_user_attrib',
        #'test_remove_user_attrib',
           
        #'test_logout',
    ]
    return unittest.TestSuite(map(AuthTestCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())
    