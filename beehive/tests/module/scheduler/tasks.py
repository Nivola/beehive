'''
Created on Nov 6, 2015

@author: darkbk
'''
from beehive.common.test import BeehiveTestCase, runtest
from beehive.common.task.manager import configure_task_manager,\
    configure_task_scheduler
from beehive.module.scheduler.tasks import jobtest, jobtest2
    
tests = [
u'test_run_jobtest',
#u'test_run_jobtest2',
]

class TaskTestCase(BeehiveTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        configure_task_manager(self.broker, self.broker)
        configure_task_scheduler(self.broker, self.broker)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_run_jobtest(self):
        data = {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90]}
        task = jobtest.delay(u'123', **data)
        print task.id, task.status
    
    def test_run_jobtest2(self):
        data = {u'suberror':False}
        task = jobtest2.delay(u'123', **data)
        print task.id, task.status

if __name__ == u'__main__':
    runtest(TaskTestCase, tests)