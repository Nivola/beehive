'''
Created on Oct 27, 2014

@author: darkbk
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.module.base import ApiManager, ApiManagerError
from gibboncloudapi.module.auth.mod import AuthModule
from gibboncloudapi.common import AuthDbManager, ConfigDbManager, EventDbManager
from gibboncloudapi.util.data import operation

class ConfigControllerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        # create api manager
        params = {'api_name':'cloudapi',
                  'api_id':'process',
                  'database_uri':self.db_uri,
                  'api_module':['gibboncloudapi.module.config.mod.ConfigModule'],
                  'api_plugin':[],
                  'api_subsystem':'conf'}
        self.manager = ApiManager(params)
        self.manager.configure()
        self.manager.register_modules()
        self.config_module = self.manager.modules['ConfigModule']

        self.perms = [(1, 1, 'admin', 'config', 'Config', '*', 1, '*'),
                      (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, '*'),
                      (1, 1, 'auth', 'role_container', 'RoleContainer', '*', 1, '*'),
                      (1, 1, 'auth', 'user_container', 'UserContainer', '*', 1, '*')]
        operation.perms = self.perms
        
        # create session
        operation.session = self.config_module.get_session()
        operation.user = 'test'
        self.controller = self.config_module.get_controller()
        
    def tearDown(self):
        self.config_module.release_session(operation.session)
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):
        AuthDbManager.create_table(self.db_uri)
        ConfigDbManager.create_table(self.db_uri)
        EventDbManager.create_table(self.db_uri)
            
    def test_remove_table(self):
        AuthDbManager.remove_table(self.db_uri)
        ConfigDbManager.remove_table(self.db_uri)
        EventDbManager.remove_table(self.db_uri)

    def test_set_initial_data(self):
        self.manager.init_object()

    def test_add_config(self):       
        app = 'portal'
        group = 'config_grp'
        name = 'config_name'
        value = 'config_value'
        res = self.controller.add_config(app, group, name, value)
        #self.assertEqual(res.name, name, 'Error')

    def test_add_config_bis(self):
        with self.assertRaises(ApiManagerError):
            app = 'portal'
            group = 'config_grp'
            name = 'config_name'
            value = 'config_value'
            res = self.controller.add_config(app, group, name, value)
            #self.assertEqual(res.name, name, 'Error')
        
    def test_get_config1(self):
        res = self.controller.get_config()
        #self.assertEqual(res.name, name, 'Error')

    def test_get_config2(self):       
        app = 'portal'
        res = self.controller.get_config(app=app)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_config3(self):
        res = self.controller.get_config(name='config_name')
        self.logger.debug(res[0].info())
        #self.assertEqual(res.name, name, 'Error')

    def test_update_config(self):
        conf = self.controller.get_config(name='config_name')[0]
        res = conf.update('config_value2')

    def test_delete_config(self):
        conf = self.controller.get_config(name='config_name')[0]
        res = conf.delete()        

    def test_add_log_config(self):
        app = 'portal'
        name = 'logger1'
        log_name = 'gibbon.cloud'
        log_conf = ('DEBUG', 'log/portal.watch', '%(asctime)s - %(message)s')
        res = self.controller.add_log_config(app, name, log_name, log_conf)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_log_config(self):       
        app = 'portal'
        res = self.controller.get_log_config(app=app)
        self.logger.debug(res[0].info())
        #self.assertEqual(res.name, name, 'Error')

    def test_delete_log_config(self):
        conf = self.controller.get_config(name='logger1')[0]
        res = conf.delete()

    def test_add_auth_config(self):
        auth_type = 'ldap'
        host = 'ad.regione.piemonte.it'
        domain = 'regione.piemonte.it' 
        res = self.controller.add_auth_config(auth_type, host, domain)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_auth_config(self):
        res = self.controller.get_auth_config()
        #self.assertEqual(res.name, name, 'Error')

    def test_delete_auth_config(self):
        conf = self.controller.get_config(name='regione.piemonte.it')[0]
        res = conf.delete()

    '''
    def test_set_queue_config1(self):
        queue_id = 'queue1'
        host = '10.102.86.6'
        port = 5672
        user = 'guest'
        pwd = 'testlab',
        exchange = ('gibbon.event.prod', 'topic')
        routing_key = 'gibbon.event.audit'
        res = self.controller.set_queue_config(queue_id, host, port, user, pwd,
                                            exchange=exchange, 
                                            routing_key=routing_key)
        #self.assertEqual(res.name, name, 'Error')

    def test_set_queue_config2(self):
        queue_id = 'queue2'    
        host = '10.102.86.6'
        port = 5672
        user = 'guest'
        pwd = 'testlab',
        queue = 'queue1'
        routing_key = 'gibbon.event.audit',
        res = self.controller.set_queue_config(queue_id, host, port, user, pwd,
                                            queue=queue, 
                                            routing_key=routing_key)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_queue_config(self):
        res = self.controller.get_queue_config()
        #self.assertEqual(res.name, name, 'Error')

    def test_set_ssh_config(self):       
        id_key = 'id_key'
        priv_key = '-----BEGIN RSA PRIVATE KEY-----\
MIIEowIBAAKCAQEAt7lXVkMbLiXk0NdkOE0bv+F29zHrHWKou+smJ4YzqRy4Cajs\
Xk7GHA4bL+2SUR5JBEmSWndsBOsdOVD3LP5vTub6pF8AyfYRhrjflLdStYBEAeMI\
jPTTC812zr5OHIfcM5PiZJdxqoGU1RVEMJYGDfd4QRQ5fOJs9FFv0isZwBZ2XKQb\
TVLcPNPtvQsBdadLS1IJKKeHT5KyhAi4p6+XlwXCHae0zBZXFuq+hNXJBdymz53T\
6Y+Zg4e0JsuqcjEdgUdKZyW7l+k+MXMJpQYkqSHRehXluVf54cpN5rEdF/2gt9Et\
9mmwS/bV8X4o2mHmhnAClHTOF2wj266SphHO1QIDAQABAoIBAQCX2kEts1mL0xZE\
50KWpmUBO8GwnznNl/YPHFT05h9c77fNhCmZ6VIlbiNageol0fpX6Ndmnr5RcmM9\
NIaYUdR+SrtvkHZ+dzwVNkjWCo/6JIIRbS1sFA87+h7w0qqNOl3u45SDwAja/S+e\
z20FG3r1oE1svOKnLh8P8R+TfrxR3tadF8CaTULfiwFnvY5jt8pCHWEduOQWjBXo\
S3ZMOpzYCzmQTRoiBQYqhgrobiq4Yy/dbJaSq51t9tE6F9k0aCyiD9t8t2bT2/ND\
6d7Np+RVE2pkI9FGXzyNP/cdf9yQKrneFKcTQVtR4+EvY3R6KrMdyYF4uDvGzS22\
xwbzyX0BAoGBAPBmxN6I2mgJDVYMXfh0qlt2QcucLRL2ZVGfkI2OLvZHHm0QsaN7\
Q8EAxdyLx01XDYq9sSs0VmDekmeR2yQYkjdz42XYh5ImUnU4caYoSiLFLrgkRSmU\
lfUCCSEWiVNgmT136bkeDC2+vOBJcfyW3ES7KZWdN8RclBfvlNd8b+5NAoGBAMOl\
Hwfm2S5PT2qSZXkPx5lRYPvSwSW/X01c2DVFgcwPjbgNzJ5E6r6x20g2t4JYDIJW\
rTxQpKJZUk+3MFRinNB0BL2rJkFJC53o3/QH1lmyFObwWKsBjlI/FfVcPXE+rHDR\
qYCHQ7GR4W+SoEmdPrdrB/hHYku1vDxzDcGwrnapAoGAElCyFQY2JZDy/ChLDH/O\
7tLuplWKtZQiGfrfJ3m6qDa44bRQ5FSiz9SAPpJDp+fG91gGZHVDU3QBkXRyTqi0\
kxb4Ly00/vR+ecHIHtGY/FcrfQn+XvGcDyONkIDIC5sjcaRuIRVh9iY++5N85LKV\
q4La4zQsKICpI720CErJuE0CgYBKYLTqWR3J2Eb12hAPtSsJo4F+WwIo6pc9nwVn\
QzR0MpmLFlvq84JW2uDllD+xou2mg3M6keH1AoYjXh5WhmLdcK34uV9CxJVRBB5X\
9L7NvMDrhwX+hQnpRKiBbf7B1bTS8zJAdawLjs0okJK1Sb11F5ChF+pLpBya0pax\
Qw0geQKBgHM58ep4WcIehs+vvC8v0TAzQHQDCGAMpeBU5J4v3pD33cMMa8tFM8Bf\
Y1RJh0wUtYhW7clGQ/Gpb20XJRFK4oDkv9vyhn6xoQX8ehZlrwZvlLMKWQle1Up1\
SApIkx1NR4/nOlLH6X1XQ2nECi3ceZ1RJ3Omx6X+IMSRGWK29/TL\
-----END RSA PRIVATE KEY-----'
        pub_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3uVdWQxsuJeTQ12Q4T\
Ru/4Xb3MesdYqi76yYnhjOpHLgJqOxeTsYcDhsv7ZJRHkkESZJad2wE6x05UPcs/m9O5vqkXwDJ9\
hGGuN+Ut1K1gEQB4wiM9NMLzXbOvk4ch9wzk+Jkl3GqgZTVFUQwlgYN93hBFDl84mz0UW/SKxnAF\
nZcpBtNUtw80+29CwF1p0tLUgkop4dPkrKECLinr5eXBcIdp7TMFlcW6r6E1ckF3KbPndPpj5mDh\
7Qmy6pyMR2BR0pnJbuX6T4xcwmlBiSpIdF6FeW5V/nhyk3msR0X/aC30S32abBL9tXxfijaYeaGc\
AKUdM4XbCPbrpKmEc7V root@ltr9r0mad'
        res = self.controller.set_ssh_config(id_key, priv_key, pub_key)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_ssh_config(self):
        res = self.controller.get_ssh_config()
        #self.assertEqual(res.name, name, 'Error')

    def test_set_uri_config(self):       
        app = 'portal'
        uri_id = 'cludstack_url'
        uri = 'http://10.102.90.209:8080/client/'
        res = self.controller.set_uri_config(app, uri_id, uri)
        #self.assertEqual(res.name, name, 'Error')

    def test_get_uri_config(self):
        app = 'portal'
        res = self.controller.get_uri_config(app=app)
        #self.assertEqual(res.name, name, 'Error')
    '''

def test_suite():
    tests = [#'test_remove_table',
             #'test_create_table',
             #'test_set_initial_data',

             #'test_add_config',
             #'test_add_config_bis',
             #'test_get_config1',
             #'test_get_config2',
             #'test_get_config3',
             #'test_update_config',
             #'test_delete_config',
             
             #'test_add_log_config',
             #'test_get_log_config',
             #'test_delete_log_config',
             
             'test_add_auth_config',
             'test_get_auth_config',
             'test_delete_auth_config',             
             
             #'test_set_queue_config1',
             #'test_set_queue_config2',
             #'test_get_queue_config',
             #'test_set_ssh_config',
             #'test_get_ssh_config',
             #'test_set_uri_config',
             #'test_get_uri_config',
            ]
    return unittest.TestSuite(map(ConfigControllerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])