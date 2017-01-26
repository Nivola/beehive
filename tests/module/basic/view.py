'''
Created on Sep 2, 2013

@author: darkbk
'''
import ujson as json
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.util.auth import AuthClient
import tests.test_util

class BaseTestCase(CloudapiTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        self.auth_client = AuthClient()
        self.module = 'monitor'
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)

    def test_ping(self):
        data = ''
        res = self.invoke(self.module, '/v1.0/server/ping/', 'GET', 
                                    data=json.dumps(data),
                                    headers={'Accept':'json'})
        self.logger.debug(self.pp.pformat(res['response']))

    def test_info(self):
        data = ''
        res = self.invoke(self.module, '/v1.0/server/', 'GET', 
                                    data=json.dumps(data),
                                    headers={'Accept':'json'})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_processes(self):
        data = ''
        uri = '/v1.0/server/processes/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_workers(self):
        data = ''
        uri = '/v1.0/server/workers/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_configs(self):
        data = ''
        uri = '/v1.0/server/configs/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))

    def test_uwsgi_configs(self):
        data = ''
        uri = '/v1.0/server/uwsgi/configs/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))

    def test_reload(self):
        data = ''
        uri = '/v1.0/server/reload/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'PUT', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))  

    #
    # database
    #
    def test_database_ping(self):
        data = ''
        uri = '/v1.0/server/db/ping/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_tables(self):
        data = ''
        uri = '/v1.0/server/db/tables/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table(self):
        data = ''
        uri = '/v1.0/server/db/table/resource/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table_paging(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/%s/%s/' % (row, offset)
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table_count(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/count/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))        
        
    def test_database_table_desc(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/desc/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke(self.module, uri, 'GET', 
                          data=data,
                          headers={'Accept':'json',
                                   'uid':tests.test_util.uid,
                                   'sign':sign})
        self.logger.debug(self.pp.pformat(res['response']))        
        
def test_suite():
    tests = [#'test_ping',
             #'test_info',
             
             'test_login',
             #'test_processes',
             #'test_workers',
             #'test_configs'
             'test_uwsgi_configs',
             #'test_reload',
             #'test_logout',
             
             #'test_database_ping',
             #'test_database_tables',
             #'test_database_table',
             #'test_database_table_paging',
             #'test_database_table_count',
             #'test_database_table_desc'
            ]
    return unittest.TestSuite(map(BaseTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])