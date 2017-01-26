'''
Created on Nov 6, 2015

@author: darkbk
'''
import time
import unittest
import gevent
from tests.test_util import run_test, CloudapiTestCase
from celery import chain, chord, group, signature

from gibboncloudapi.module.scheduler.manager import task_manager, configure_task_manager, configure_task_scheduler
from gibboncloudapi.module.scheduler.manager import task_scheduler
from beecell.db.manager import RedisManager
from gibboncloudapi.module.scheduler.tasks import test, jobtest, jobtest2
from celery.result import GroupResult

class TaskManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        broker = 'redis://10.102.160.12:6379/1'
        configure_task_manager(broker, broker)
        configure_task_scheduler(broker, broker)
        redis_uri = '10.102.160.12;6379;1'
        self.manager = RedisManager(redis_uri)
        self._prefix = "celery-schedule"    
    
    def tearDown(self):
        CloudapiTestCase.tearDown(self)
    
    def test_get_scheduler_tasks(self):
        i = task_manager.control.inspect()
        s = task_scheduler.control.inspect()
        from celery.result import AsyncResult
        data = AsyncResult('7ca7e07-7fa5-4a7a-8a9f-78dedbaeeb99', 
                           app=task_manager)

        if data.failed() is True:
            print data.id, data.traceback
        elif data.ready() is True:
            print data.id, data.result
        else:
            print data.task_id, data.status
        
        print i.query_task('7ca7e07-7fa5-4a7a-8a9f-78dedbaeeb99')
        
        print s.ping()
        
        '''
        print i.registered()
        print i.active()
        print i.scheduled()
        print s.scheduled()
        print i.reserved()
        print i.revoked()
        print i.active_queues()
        print s.active_queues()
        '''   
        '''
        print task_manager.control.ping(timeout=0.5)
        print i.registered()
        print i.active()
        print i.scheduled()
        print i.reserved()
        print i.revoked()
        print i.stats()
        print i.report()
        print i.active_queues()
        '''
        #print i.memdump()
        #print i.memsample()
        #print i.objgraph()
        #print i.registered_tasks()
        #print i.query_task()
        # Discard all waiting tasks.
        #i.purge()
        # Tell all (or specific) workers to revoke a task by id.
        #i.revoke(task_id)
        # Tell all (or specific) workers to set time limits for a task by type.
        #i.time_limit(task_name)
        
        #print self.manager.delete(pattern='celery-task-meta*')
        
        #print len(self.manager.conn.keys('celery-task-meta*'))
        #keys = self.manager.inspect(pattern='celery-task-meta*', debug=False)
        #for key in keys:
        #    key = key[0].lstrip('celery-task-meta-')
        #print keys
        #print self.manager.query(keys)
        #print self.manager.conn.object('IDLETIME', 'celery-task-meta-c0cc4d5c-d2c7-489c-8d3b-ec07db2e559a')
            #print key        
        '''from celery.result import AsyncResult
        self.manager = RedisManager(self.redis_uri)
        keys = self.manager.inspect(pattern='celery-task-meta*', debug=False)
        for key in keys:
            key = key[0].lstrip('celery-task-meta-')
            res = AsyncResult(key)
            backend
            print res.get()    '''
    
    def test_task(self):
        '''Celery will automatically retry sending messages in the event of 
        connection failure, and retry behavior can be configured - like how
        often to retry, or a maximum number of retries - or disabled all 
        together. To disable retry you can set the retry execution option 
        to False
        '''
        from datetime import datetime, timedelta
        tomorrow = datetime.utcnow() + timedelta(seconds=120)
        task = test.apply_async(retry=False, countdown=0)
        '''print task.id, task.status
        while task.state == 'PENDING' or task.state == 'STARTED':
            time.sleep(2)
            print task.id, task.status
            
        if task.failed() is True:
            print task.id, task.traceback
        elif task.ready() is True:
            print task.id, task.result
        else:
            print task.task_id, task.status'''

    def test_test_workflow(self):
        '''Celery will automatically retry sending messages in the event of 
        connection failure, and retry behavior can be configured - like how
        often to retry, or a maximum number of retries - or disabled all 
        together. To disable retry you can set the retry execution option 
        to False
        '''
        from datetime import datetime, timedelta
        tomorrow = datetime.utcnow() + timedelta(seconds=120)
        task = test_workflow.apply_async(('proc1', 1, 2))
        print task.id, task.status
        while task.state == 'PENDING' or task.state == 'STARTED':
            time.sleep(2)
            print task.id, task.status
            
        if task.failed() is True:
            print task.id, task.traceback
        elif task.ready() is True:
            print task.id, task.result
        else:
            print task.task_id, task.status
        
    def test_run_task(self):
        from gibboncloudapi.module.service.tasks import add_service_day_usage
        from gibboncloudapi.module.service.tasks import add_service_week_usage
        from gibboncloudapi.module.service.tasks import add_service_month_usage
        from gibboncloudapi.module.service.tasks import add_service_year_usage
        task = add_service_day_usage.apply_async((21,))
        task = add_service_week_usage.apply_async((21,))
        task = add_service_month_usage.apply_async((21,))
        task = add_service_year_usage.apply_async((21,))
        
    def test_run_test(self):
        task = test.delay()
        print task.id, task.status        
        
    def test_run_jobtest(self):
        data = {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]}
        task = jobtest.delay('123', data)
        print task.id, task.status
    
    def test_run_jobtest2(self):
        data = {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]}
        task = jobtest2.delay('123', data)
        print task.id, task.status        

    def _query_task_graph_item(self, task_id):
        from celery.result import AsyncResult
        res = AsyncResult(task_id, app=task_manager)
        #print list(res.collect())
        resp = {u'status':res.state,
                u'result':None, 
                u'traceback':None,
                u'children':[], 
                u'id':task_id,
                u'timestamp':None,
                u'type':None,
                u'name':None, 
                u'args':None}
        
        print "1 - %s - %s" % (res.result[0], res.result[5])
        # get children
        if res.children is not None:
            print "2 - %s" % res.children
            for c in res.children:
                if isinstance(c, GroupResult):
                    for c1 in c.children:
                        sub = self._query_task_graph_item(c1.task_id)
                        resp[u'children'].append(sub)
                else:
                    sub = self._query_task_graph_item(c.task_id)
                    resp[u'children'].append(sub)                    
        
        result = res.info
        try: name = result[0]
        except: name = None                    
        try: args = result[1]
        except: args = None
        try: timestamp = result[2]
        except: timestamp = None
        try: elapsed = result[3]
        except: elapsed = None
        try: tasktype = result[4]
        except: tasktype = None                    
        try: result = result[5]
        except: result = None
        
        resp[u'name'] = name
        resp[u'args'] = args
        resp[u'timestamp'] = timestamp
        resp[u'elapsed'] = elapsed
        resp[u'type'] = tasktype        
        
        if res.state == 'ERROR':
            resp[u'traceback'] = res.traceback
        elif res.ready() is True:
            resp[u'result'] = result
            
        return resp
    
    def test_query(self):
        #self._query_task_graph_item('5c86ee4e-14b0-4fc3-8bde-4b7d0a47cab0')
        from celery.result import AsyncResult
        res = AsyncResult('825adcc1-1d9a-46f3-9db4-d999880dbab7', app=task_manager)
        print res.result

def test_suite():
    tests = [
             #'test_task',
             #'test_test_workflow',
             #'test_get_scheduler_tasks',
             #'test_run_task',
             #'test_run_test',
             #'test_run_jobtest',
             'test_run_jobtest2',
             #'test_query',
            ]
    return unittest.TestSuite(map(TaskManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])