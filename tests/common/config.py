'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common.config import ConfigDbManager
from gibboncloudapi.util.data import operation

class ConfigDbManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        db_session = self.open_mysql_session(self.db_uri)
        operation.session = db_session()
        self.manager = ConfigDbManager()
        operation.transaction = 0        
        
    def tearDown(self):
        operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        ConfigDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        ConfigDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()

    def test_property_add1(self):       
        app = 'portal'
        group = 'cloud'
        name = 'prop1'
        value = 'prop1_value'
        res = self.manager.add(app, group, name, value)
        self.assertEqual(res.name, name, 'Error')

    def test_property_add1bis(self):
        with self.assertRaises(TransactionError):
            app = 'portal'
            group = 'cloud'            
            name = 'prop1'
            value = 'prop1_value'
            res = self.manager.add(app, group, name, value)

    def test_property_add2(self):
        app = 'portal'
        group = 'cloud'            
        name = 'prop2'
        value = 'prop2_value'
        res = self.manager.add(app, group, name, value)

    def test_property_get1(self):
        name = 'prop1'
        res = self.manager.get(name=name)
        #self.assertEqual(res.name, name, 'Error')

    def test_property_get2(self):
        with self.assertRaises(QueryError):
            name = 'prop3'
            res = self.manager.get(name=name)
            #self.assertEqual(res, None, 'Error')

    def test_property_get_all(self):
        app = 'portal'
        group = 'cloud'
        res = self.manager.get(app=app, group=group)

    def test_property_update1(self):
        name = 'prop1'
        value = 'prop1_value_update'
        res = self.manager.update(name, value)

    def test_property_update2(self):
        name = 'prop3'
        value = 'prop1_value_update'
        res = self.manager.update(name, value)

    def test_property_delete1(self):
        name1 = 'prop1'
        res = self.manager.delete(name=name1)

    def test_property_delete2(self):
        name2 = 'prop2'
        res = self.manager.delete(name=name2)

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             'test_set_initial_data',
             'test_property_add1',
             'test_property_add1bis',
             'test_property_add2',
             'test_property_get1',
             'test_property_get2',
             'test_property_get_all',
             'test_property_update1',
             'test_property_delete1',
             'test_property_delete2',
            ]
    return unittest.TestSuite(map(ConfigDbManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])