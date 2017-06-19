'''
Created on Sep 2, 2013

@author: darkbk
'''
from tests.test_util import run_test, CloudapiTestCase
import unittest
import datetime
from gibboncloudapi.module.base import ApiManager
from gibboncloudapi.module.event.model import EventDbManager
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen

pid = None
pid = 836485998

class EventControllerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        operation.transaction = 0
        
        # create api manager
        params = {'api_name':'cloudapi',
                  'api_id':'process',
                  'database_uri':self.db_uri,
                  'api_module':['gibboncloudapi.module.event.mod.EventModule'],
                  'api_plugin':[],
                  'api_subsystem':'auth'}
        self.manager = ApiManager(params)
        self.manager.configure()
        self.manager.register_modules()
        self.event_module = self.manager.modules['EventModule']      

        # caller permissions
        perms = [(1, 1, 'event', 'property', 'ConfigEvent', '*', 1, '*'),
                 (1, 1, 'event', 'user', 'ConfigEvent', 'prova@local', 1, '*')]
        #perms = []
        
        """perms = [(1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'view'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'insert'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'update'),
                 (1, 1, 'auth', 'object_container', 'ObjectContainer', '*', 1, 'delete')]
        """
        operation.perms = perms
        operation.user = ('admin', 0)
        
        # create session
        operation.session = self.event_module.get_session()
        self.controller = self.event_module.get_controller()
    
    def tearDown(self):
        self.event_module.release_session(operation.session)
        CloudapiTestCase.tearDown(self)
    
    def test_create_table(self):
        EventDbManager.create_table(self.db_uri)
            
    def test_remove_table(self):
        EventDbManager.remove_table(self.db_uri)

    def test_set_initial_data(self):    
        self.manager.init_object()

    def test_get_events(self):
        res = self.controller.get_events(datefrom=datetime.datetime(2015, 3, 9, 15, 23, 00),
                                         dateto=datetime.datetime(2015, 3, 9, 15, 23, 56))
        #res = self.controller.get_events(dateto=datetime.datetime(2015, 3, 9, 15, 23, 56))
        #res = self.controller.get_events(etype='property')
        #res = self.controller.get_events(oid=896161038)
        #res = self.controller.get_events(source='admin@local')
        #res = self.controller.get_events(data='provaRole')
        
        for i in res:
            print i

def test_suite():
    tests = [#'test_remove_table',
             #'test_create_table',
             #'test_set_initial_data',
             'test_get_events',
            ]
    return unittest.TestSuite(map(EventControllerTestCase, tests))

if __name__ == '__main__':
    run_test(test_suite())    