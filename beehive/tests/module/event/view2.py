'''
Created on Sep 2, 2013

@author: darkbk
'''
import ujson as json
import unittest
from gibboncloudapi.util.auth import AuthClient
import tests.test_util
from beehive.common.test import BeehiveTestCase, runtest

jobid = None
pid = 836485998
tid = 134604261

class EventAPITestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        self.auth_client = AuthClient()
        self.api_id = 'api'
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
        
    # events
    def test_get_events(self):
               
        data = ''
        
        #res = self.controller.get_events(datefrom=datetime.datetime(2015, 3, 9, 15, 23, 00),
        #                                 dateto=datetime.datetime(2015, 3, 9, 15, 23, 56))
        #res = self.controller.get_events(dateto=datetime.datetime(2015, 3, 9, 15, 23, 56))
        #res = self.controller.get_events(etype='property')
        #res = self.controller.get_events(oid=896161038)
        #res = self.controller.get_events(source='admin@local')
        #res = self.controller.get_events(data='provaRole')        
        
        #uri = '/api/event/%s/' % 'property++++'
        #uri = '/api/event/%s/' % '+provaRole+++'
        #uri = '/api/event/%s/' % '+++25-05-15-09-28-52+'
        uri = '/v1.0/event/%s/' % '+admin+++'
        uri = '/v1.0/events/'
        query = 'objdef=tenant.cloud_domain.security_domain.environment.security_policy&objid=2b2a01db-a44a-498e-8547-7182bad66fa2//229c88e4-04a0-4f5f-ac59-086568ffe31e//17d5e7f2-ee8b-4a7a-b34e-a6ebb3320b73//5c05c848-f21f-41f1-808b-328fd2b21002%'
        res = self.invoke('core', uri, 'GET', data='', filter=query)
        self.logger.info(self.pp.pformat(res))

    def test_get_events_by_page(self):
        buri = '/v1.0/events/'
        uri = '%s?page=2&size=5' % buri
        sign = self.auth_client.sign_request(tests.test_util.seckey, buri)
        res = self.invoke('core', uri, 'GET', data='')
        self.logger.info(self.pp.pformat(res['response']))

    def test_get_event(self):
        data = ''
        uri = '/v1.0/event/%s/' % u'0ad68a18-3390-4fcf-ad9f-8779974d07c2'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke('core', uri, 'GET', data='')
        self.logger.info(self.pp.pformat(res['response']))

    def test_get_event_types(self):
        data = ''
        uri = '/v1.0/event/types/'
        sign = self.auth_client.sign_request(tests.test_util.seckey, uri)
        res = self.invoke('core', uri, 'GET', data='')
        self.logger.info(self.pp.pformat(res['response']))

def test_suite():
    tests = ['test_login',
             'test_get_events',
             #'test_get_events_by_page',
             #'test_get_event',
             #'test_get_event_types',
             'test_logout',
            ]
    #tests = ['test_remove_initial_value', 'test_set_initial_value']   
    return unittest.TestSuite(map(EventAPITestCase, tests))

if __name__ == '__main__':
    runtest([test_suite()])