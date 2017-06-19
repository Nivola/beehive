'''
Created on Nov 6, 2015

@author: darkbk
'''
import unittest
from tests.test_util import BeehiveTestCase
from beehive.common.task.manager import configure_task_manager,\
    configure_task_scheduler
from beehive.module.catalog.tasks import refresh_catalog
from beehive.module.auth.tasks import disable_expired_users,\
    remove_expired_roles_from_users
from beehive.common.test import runtest

class AuthTaskManagerTestCase(BeehiveTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        configure_task_manager(self.broker, self.broker)
        configure_task_scheduler(self.broker, self.broker)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_disable_expired_users(self):
        data = {}
        task = disable_expired_users.delay(u'*', data)
        print task.id, task.status
        
    def test_remove_expired_roles_from_users(self):
        data = {}
        task = remove_expired_roles_from_users.delay(u'*', data)
        print task.id, task.status        

def test_suite():
    tests = [
        #u'test_disable_expired_users',
        u'test_remove_expired_roles_from_users',
    ]
    return unittest.TestSuite(map(AuthTaskManagerTestCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())