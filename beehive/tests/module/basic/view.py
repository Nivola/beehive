'''
Created on Feb 09, 2018

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase

tests = [  
    # 'test_ping',
    # 'test_info',

    'test_login',
    # 'test_processes',
    # 'test_workers',
    # 'test_configs'
    'test_uwsgi_configs',
    # 'test_reload',
    # 'test_logout',

    # 'test_database_ping',
    # 'test_database_tables',
    # 'test_database_table',
    # 'test_database_table_paging',
    # 'test_database_table_count',
    # 'test_database_table_desc'
]


class BaseTestCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'auth'
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping(self):
        data = ''
        uri = '/v1.0/server/ping/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))

    def test_info(self):
        data = ''
        uri = '/v1.0/server/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_processes(self):
        data = ''
        uri = '/v1.0/server/processes/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_workers(self):
        data = ''
        uri = '/v1.0/server/workers/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_configs(self):
        data = ''
        uri = '/v1.0/server/configs/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))

    def test_uwsgi_configs(self):
        data = ''
        uri = '/v1.0/server/uwsgi/configs/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))

    def test_reload(self):
        data = ''
        uri = '/v1.0/server/reload/'
        res = self.call(self.module, uri, 'PUT', data=data)
        self.logger.debug(self.pp.pformat(res['response']))  

    #
    # database
    #
    def test_database_ping(self):
        data = ''
        uri = '/v1.0/server/db/ping/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_tables(self):
        data = ''
        uri = '/v1.0/server/db/tables/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table(self):
        data = ''
        uri = '/v1.0/server/db/table/resource/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table_paging(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/%s/%s/' % (row, offset)
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))
        
    def test_database_table_count(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/count/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))        
        
    def test_database_table_desc(self):
        data = ''
        row = 10
        offset = 3
        uri = '/v1.0/server/db/table/resource/desc/'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res['response']))        
        

if __name__ == u'__main__':
    runtest(BaseTestCase, tests)