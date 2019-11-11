'''
Created on Feb 09, 2018

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase

tests = [  
    'test_ping',
    'test_info',

    ## 'test_processes',
    ## 'test_workers',
    ## 'test_configs'
    ## 'test_uwsgi_configs',
    ## 'test_reload',
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
        uri = '/v1.0/server/ping'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res))

    def test_info(self):
        data = ''
        uri = '/v1.0/server'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res))
        
    '''def test_processes(self):
        data = ''
        uri = '/v1.0/server/processes'
        res = self.call(self.module, uri, 'GET', data=data, **self.users['admin'])
        self.logger.debug(self.pp.pformat(res))
        
    def test_workers(self):
        data = ''
        uri = '/v1.0/server/workers'
        res = self.call(self.module, uri, 'GET', data=data, **self.users['admin'])
        self.logger.debug(self.pp.pformat(res))
        
    def test_configs(self):
        data = ''
        uri = '/v1.0/server/configs'
        res = self.call(self.module, uri, 'GET', data=data, **self.users['admin'])
        self.logger.debug(self.pp.pformat(res))

    def test_uwsgi_configs(self):
        data = ''
        uri = '/v1.0/server/uwsgi/configs'
        res = self.call(self.module, uri, 'GET', data=data, **self.users['admin'])
        self.logger.debug(self.pp.pformat(res))

    def test_reload(self):
        data = ''
        uri = '/v1.0/server/reload'
        res = self.call(self.module, uri, 'PUT', data=data, **self.users['admin'])
        self.logger.debug(self.pp.pformat(res))'''


if __name__ == '__main__':
    runtest(BaseTestCase, tests)