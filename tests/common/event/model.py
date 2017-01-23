'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
import datetime
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common import EventDbManager
from gibbonutil.db import TransactionError, QueryError
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen

class EventDbManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        db_session = self.open_mysql_session(self.db_uri)
        operation.session = db_session()
        self.manager = EventDbManager()
        operation.transaction = 0        
        
    def tearDown(self):
        operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        EventDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        EventDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()

    def test_add_event(self):
        eventid = id_gen()  
        etype = 'cloudstack.org.grp.vm'
        objid = '*//*//*//*'
        creation = datetime.datetime.utcnow()
        data = {u'opid':1, u'op':u'test.send', u'params':[], u'response':True}
        source = {u'user':u'pippo', u'ip':u'10.1.1.1'}
        dest = {u'app':u'cloudapi', u'ip':u'10.1.1.2'} 
        res = self.manager.add(eventid, etype, objid, creation, data, source, dest)
        
    def test_get_event(self):
        res = self.manager.gets()

    def test_get_event_types(self):
        res = self.manager.get_types()
        print res

def test_suite():
    tests = [#'test_remove_table',
             #'test_create_table',
             #'test_set_initial_data',
             #'test_add_event',
             #'test_get_event',
             'test_get_event_types',
            ]
    return unittest.TestSuite(map(EventDbManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])