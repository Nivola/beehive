'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
import gevent
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common import EventDbManager
from gibbonutil.db import TransactionError, QueryError
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen

from gibboncloudapi.common import EventProducer

class EventManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        #db_session = self.open_mysql_session(self.db_uri)
        #operation.session = db_session()
        #self.manager = EventDbManager()
        host = '158.102.160.234'
        port = 5500
        self.client = EventProducer(host, port)     
        
    def tearDown(self):
        #operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        EventDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        EventDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()

    def test_add_event(self):
        event_type = 'cloudstack.org.grp.vm'
        data = {'opid':1, 'op':'test.send', 'params':[], 'response':True}
        source = {'user':'pippo', 'ip':'10.1.1.1'}
        dest = {'app':'cloudapi', 'ip':'10.1.1.2', 'objid':'*//*//*//*'}
        
        self.client.async_send(event_type, data, source, dest)
        self.client.async_send(event_type, data, source, dest)
        self.client.async_send(event_type, data, source, dest)
        self.client.async_send(event_type, data, source, dest)

def test_suite():
    tests = ['test_add_event',
            ]
    return unittest.TestSuite(map(EventManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])