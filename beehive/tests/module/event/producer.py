'''
Created on Jan 25, 2017

@author: darkbk
'''
from tests.test_util import run_test, CloudapiTestCase
import ujson as json
import unittest
from gibboncloudapi.util.auth import AuthClient
import tests.test_util
from gibboncloudapi.common.event import EventProducerRedis

class EventProducerTestCase(CloudapiTestCase):
    """
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        redis_uri = u'redis://10.102.184.51:6379/0'
        redis_channel = u'beehive.event'
        self.client = EventProducerRedis(redis_uri, redis_channel)
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)
        
    def test_send_event(self):
        event_type = u'syncop'
        objtype = u'test'
        source = {u'user':u'admin',
                  u'ip':u'localhost',
                  u'identity':u'uid'}
        dest = {u'ip':u'localhost',
                u'port':6060,
                u'objid':123, 
                u'objtype':objtype,
                u'objdef':u'test1'}
        data = {u'key':u'value'}
        self.client.send_sync(event_type, data, source, dest)
        
def test_suite():
    tests = [
        u'test_send_event',
    ]
    return unittest.TestSuite(map(EventProducerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])        