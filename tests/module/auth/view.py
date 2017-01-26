'''
Created on Sep 2, 2013

@author: darkbk
'''
from tests.test_util import run_test, CloudapiTestCase
import ujson as json
import unittest
from beehive.util.auth import AuthClient
import urllib

uid = None
seckey = None
objid = None

class AuthTestCase(CloudapiTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        self.auth_client = AuthClient()
        self.api_id = u'api'
        self.user = u'admin1@local'
        self.pwd = u'testlab'
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)
        
    def test_get_login_domains(self):
        res = self.invoke('auth','/api/auth/login/domain/', 'GET', 
                                         data='',
                                         headers={'Accept':'json'})     

    def test_refresh(self):
        global uid, seckey
        sign = self.auth_client.sign_request(seckey, '/api/auth/login/refresh/')
        self.invoke('auth','/api/auth/login/refresh/', 'PUT', 
                                   data='',
                                   headers={'Accept':'json',
                                            'uid':uid,
                                            'sign':sign})

    def test_exist_identity(self):
        global uid, seckey
        res = self.invoke('auth','/api/auth/login/%s/' % uid, 'GET', 
                                         data='',
                                         headers={'Accept':'json'})

    # identity
    def test_get_identities(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/identity/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_identity(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/identity/%s/' % uid
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})   

    def test_delete_identity(self):
        global uid, seckey
                
        data = ''
        identity = 'ozIMohWioskVIh9PYyIC'
        uri = '/api/auth/identity/%s/' % identity
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    # objects
    def test_get_objects(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_id(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/%s/' % 22
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_value(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/V:%s/' % ('*').replace('//', '--')
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_value_empty(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/V:aprrrr/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_type(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/T:auth/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_definition(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/D:cloudstack.org.grp.vm/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_object_permissions(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/perm/74/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_object_permissions_with_filter(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/perm/T:resource+D:None+I:529857882_638138605_646335961_*/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_all_permissions(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/perm/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_add_object(self):
        global uid, seckey
        
        # [(objtype, definition, objid), (objtype, definition, objid)]
        data = json.dumps([("resource", "vsphere.dc.dvs.dvp", "529857882//638138605//646335961//*", '')])
        #data = json.dumps([("auth", "role", "1234566//73838", "prova desc")])
        uri = '/api/auth/object/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_objects_by_definition_and_value(self):
        global uid, seckey, objid
                
        data = ''
        uri = '/api/auth/object/D:cloudstack.org.grp.vm/V:%s/' % ('csi//*//*//*')#.replace('//', '--')
        uri = '/api/auth/object/T:auth/D:role/I:%s/' % ('725563892')
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        res = self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})
        objid = res['response'][0][0]

    def test_del_object(self):
        global uid, seckey, objid
        
        data = ''
        uri = '/api/auth/object/%s/' % objid
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_object_types(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/type/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    # type
    def test_add_object_type(self):
        global uid, seckey
        
        data = json.dumps([('resource', 'orchestrator.org.area.prova', 'ProvaClass')])
        uri = '/api/auth/object/type/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_object_type(self):
        global uid, seckey, objid
                
        data = ''
        uri = '/api/auth/object/type/D:orchestrator.org.area.prova/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        res = self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})
        objid = res['response'][0][0]

    def test_del_object_type(self):
        global uid, seckey, objid
        
        data = ''
        uri = '/api/auth/object/type/%s/' % objid
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    # actions
    def test_get_object_actions(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/object/action/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    # users
    def test_get_authentication_domains(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/user/domain/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})    
    
    def test_get_users(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/user/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})
    def test_get_user(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/user/%s/' % 4
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_user2(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/user/portal222/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_users_by_role(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/%s/user/' % 'ApiSuperadmin'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_user_can(self):
        global uid, seckey

        user = 'test1@local'
        action = 'view'
        obj_type = 'cloudapi.orchestrator.org.area.vm'
                        
        data = ''
        uri = '/api/auth/user/%s/can/%s:%s/' % (user, obj_type, action)
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_add_user(self):
        global uid, seckey
        
        data = json.dumps({'username':'prova@local', 
                           'storetype':'DBUSER',
                           'systype':'USER',
                           'active':True, 
                           'password':'prova', 
                           'description':'',
                           'generic':False})       
                 
        uri = '/api/auth/user/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_add_generic_user(self):
        global uid, seckey
        
        data = json.dumps({'username':'prova4@local', 
                           'storetype':'DBUSER',
                           'password':'prova', 
                           'description':'',
                           'generic':True})       
                 
        uri = '/api/auth/user/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_add_system_user(self):
        global uid, seckey
        
        data = json.dumps({'username':'prova2@local',
                           'password':'prova', 
                           'description':'', 
                           'system':True})       
                 
        uri = '/api/auth/user/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_update_user(self):
        global uid, seckey, objid
        
        data = '{"new_name":"prova4@local", "role":{"append":["ApiSuperadmin"], "remove":[]}}'
        uri = '/api/auth/user/%s/' % 'prova4@local'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'PUT', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_del_user(self):
        global uid, seckey, objid
        
        data = ''
        uri = '/api/auth/user/%s/' % 'prova1@local'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_set_user_attrib(self):
        global uid, seckey, objid
        
        data = json.dumps({'name':'test', 'value':'val', 'desc':'desc'})
        uri = '/api/auth/user/%s/attribute/' % 9
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'PUT', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_remove_user_attrib(self):
        global uid, seckey, objid
        
        data = ''
        uri = '/api/auth/user/%s/attribute/%s/' % (9, 'test')
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    # roles
    def test_get_roles(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})
    def test_get_role(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/ApiSuperadmin/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_role2(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/ApiSuperadmin2/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_role3(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/prova_role/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_role4(self):
        global uid, seckey
                
        data = ''
        uri = '/api/auth/role/prova1_role/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_add_role(self):
        global uid, seckey
        
        data = '{"name":"prova_role", "description":"prova_role", "type":"app", "value":["portal"]}'
        uri = '/api/auth/role/'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'POST', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_update_role(self):
        global uid, seckey, objid
        data = json.dumps({"new_name":"prova1_role",
                           "perm":{"append":[
                                             (0, 0, "resource", 
                                              "cloudstack.org", "", 
                                              "*//*", 0, "view")], 
                                   "remove":[]}})       
        
        uri = '/api/auth/role/%s/' % 'prova_role'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'PUT', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_del_role(self):
        global uid, seckey, objid
        
        data = ''
        uri = '/api/auth/role/%s/' % 'c1c6add0-9d30-4852-9303-eabb7beef40c_security_domain_admin'
        sign = self.auth_client.sign_request(seckey, uri)
        sign = sign 
        self.invoke('auth',uri, 'DELETE', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

def test_suite():
    tests = [
             'test_login',
             #'test_get_login_domains',
             #'test_refresh',
             #'test_exist_identity',
             #'test_get_identities',
             #'test_get_identity',
             #'test_delete_identity',
             
             #'test_get_objects',
             #'test_get_objects_by_id',
             #'test_get_objects_by_value',
             #'test_get_objects_by_value_empty',
             #'test_get_objects_by_type',
             
             #'test_get_object_types',
             #'test_get_object_actions',
             #'test_get_object_permissions',
             #'test_get_object_permissions_with_filter',
             #'test_get_all_permissions',
             #'test_add_object',
             #'test_get_objects_by_definition_and_value',
             #'test_del_object',
             #'test_add_object_type',
             #'test_get_object_type',
             #'test_del_object_type',             

             #'test_get_authentication_domains',
             #'test_get_users',
             #'test_get_user',
             #'test_get_user2',
             
             #'test_add_user',
             #'test_add_generic_user',
             #'test_add_system_user',
             #'test_update_user',
             #'test_get_users',
             #'test_del_user',
             #'test_set_user_attrib',
             #'test_remove_user_attrib',
             
             #'test_get_user_can',
             
             #'test_get_roles',
             #'test_get_role',
             #'test_get_role2',
             #'test_add_role',
             #'test_get_role3',
             #'test_update_role',
             #'test_get_users_by_role',
             #'test_get_role4',
             #'test_del_role',             
             'test_logout',
             #'test_remove_initial_value',
            ]
    #tests = ['test_set_initial_value']
    #tests = ['test_remove_initial_value']
    return unittest.TestSuite(map(AuthTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])