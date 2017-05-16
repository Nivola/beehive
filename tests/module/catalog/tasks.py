'''
Created on Nov 6, 2015

@author: darkbk
'''
import unittest
from tests.test_util import run_test, CloudapiTestCase
from beecell.db.manager import RedisManager
from beehive.common.task.manager import configure_task_manager,\
    configure_task_scheduler
from beehive.module.catalog.tasks import refresh_catalog

class TaskManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        broker = u'redis://10.102.184.51:6379/1'
        configure_task_manager(broker, broker)
        configure_task_scheduler(broker, broker)
        redis_uri = u'redis://10.102.184.51:6379/1'
        self.manager = RedisManager(redis_uri)

    def tearDown(self):
        CloudapiTestCase.tearDown(self)

    def test_run_refresh_catalog(self):
        data = {}
        task = refresh_catalog.delay(u'*', data)
        print task.id, task.status

def test_suite():
    tests = [
        u'test_run_refresh_catalog',
    ]
    return unittest.TestSuite(map(TaskManagerTestCase, tests))

if __name__ == u'__main__':
    run_test([test_suite()])