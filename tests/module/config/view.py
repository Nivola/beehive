'''
Created on Sep 2, 2013

@author: darkbk
'''
import json
import unittest
from tests.test_util import run_test, CloudapiTestCase

uid = None
seckey = None

class ConfigAPITestCase(CloudapiTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        self.api_id = 'api'
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)

    def test_login(self):
        data = {'user':'admin@local', 'password':'testlab', 'login_ip':'172.16.0.15'}
        res = self.send_auth_api_request('/api/auth/login', 'POST', 
                                    data=json.dumps(data),
                                    headers={'Accept':'json'})
        global uid, seckey
        res = res['response']
        uid = res['uid']
        seckey = res['seckey']

    def test_logout(self):
        global uid, seckey
        sign = self.auth_client.sign_request(seckey, '/api/auth/logout')
        self.send_auth_api_request('/api/auth/logout', 'POST', 
                              data='',
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_get_config(self):
        global uid, seckey
                
        data = ''
        uri = '/api/config/cloudapi/'
        sign = self.auth_client.sign_request(seckey, uri)
        self.send_api_request(uri, 'GET', 
                              data=data,
                              headers={'Accept':'json',
                                       'uid':uid,
                                       'sign':sign})

    def test_reload_config(self):
        params = {}
        base_url = "http://172.16.0.2:5000/api/config/reload"
        res = self.http_client(base_url, params)
        res_dict = json.loads(res)
        self.logger.debug(self.pp.pformat(res_dict))
        self.assertEqual(res_dict['status'], 'ok')

def test_suite():
    tests = [#'test_set_initial_value',
             'test_login',
             'test_get_config',       
             'test_logout',
             #'test_remove_initial_value',
            ]
    #tests = ['test_remove_initial_value', 'test_set_initial_value']   
    return unittest.TestSuite(map(ConfigAPITestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])