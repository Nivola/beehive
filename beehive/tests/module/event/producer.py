# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

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
        
        redis_uri = 'redis://10.102.184.51:6379/0'
        redis_channel = 'beehive.event'
        self.client = EventProducerRedis(redis_uri, redis_channel)
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)
        
    def test_send_event(self):
        event_type = 'syncop'
        objtype = 'test'
        source = {'user':'admin',
                  'ip':'localhost',
                  'identity':'uid'}
        dest = {'ip':'localhost',
                'port':6060,
                'objid':123, 
                'objtype':objtype,
                'objdef':'test1'}
        data = {'key':'value'}
        self.client.send_sync(event_type, data, source, dest)
        
def test_suite():
    tests = [
        'test_send_event',
    ]
    return unittest.TestSuite(map(EventProducerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])        