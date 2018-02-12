'''
Created on Feb 09, 2018

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
import ujson as json

uid = None
seckey = None
task_id = 'd124ef29-7c57-423e-b6d9-b72d519d7600'

tests = [
    'test_ping_task_manager',
    'test_stat_task_manager',
    'test_report_task_manager',
    'test_queues_task_manager',
    'test_get_all_tasks',
    'test_count_all_tasks',
    'test_get_task_definitions',
    # 'test_run_job_test',
    # 'test_get_task',
    # 'test_get_task_graph',
    # 'test_delete_task',
    # 'test_run_job_test',
    # 'test_delete_all_tasks',
    
    # 'test_get_scheduler_entries',
    # 'test_create_scheduler_entries',
    # 'test_delete_scheduler_entry',
]


class SchedulerAPITestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = u'resource'
        
    #
    # task manager
    #
    def test_ping_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/worker/ping'
        
        self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])

    def test_stat_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/worker/stats'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_report_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/worker/report'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_queues_task_manager(self):
        global uid, seckey

        data = u''
        uri = u'/v1.0/worker/queues'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_all_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/worker/tasks'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_count_all_tasks(self):
        global uid, seckey

        data = u''
        uri = u'/v1.0/worker/tasks/count'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task_definitions(self):
        global uid, seckey

        data = u''
        uri = u'/v1.0/worker/tasks/definitions'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task(self):
        global uid, seckey
                
        data = u''
        task_id = u'6d21c46a-d1bc-4435-9d26-5d75881f6cb1'
        uri = u'/v1.0/worker/task/%s' % task_id
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_get_task_graph(self):
        global uid, seckey, task_id
        data = u''
        task_id = '89c29e6f-82e6-4a0e-8041-da1230edb7e0'
        uri = u'/v1.0/worker/task/%s/graph' % task_id
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_delete_all_tasks(self):
        global uid, seckey
        data = u''
        uri = u'/v1.0/worker/tasks'
        
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])
        
    def test_delete_task(self):
        global uid, seckey
        oid = ''
        data = u''
        uri = u'/v1.0/worker/task/%s' % oid
        
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])
        
    def test_run_job_test(self):
        global uid, seckey, task_id
        data = json.dumps({u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]} )
        uri = u'/v1.0/worker/task/jobtest'
        res = self.call(self.module, uri, u'POST', data=data, **self.users[u'admin'])
        self.wait_job(res[u'jobid'], delta=1, accepted_state=u'SUCCESS')

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/scheduler/entries'
        
        res = self.invoke('monitor', uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.debug(self.pp.pformat(res))

    def test_create_scheduler_entries(self):
        global uid, seckey
                
        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'crontab',
                                        'minute':2,
                                        'hour':'*',
                                        'day_of_week':'*',
                                        'day_of_month':'*',
                                        'month_of_year':'*'},
                           'options': {'expires': 60}})
        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'timedelta',
                                        'minutes':1},
                           'options': {'expires': 60}})
        
        data = json.dumps({'name':'services_usage',
                           'task': 'tasks.add_services_instant_usage',
                           'schedule': {'type':'timedelta',
                                        'minutes':30},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_day',
                           'task': 'tasks.add_services_day_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_week',
                           'task': 'tasks.add_services_week_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'day_of_week':1},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_month',
                           'task': 'tasks.add_services_month_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'day_of_month':1},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_year',
                           'task': 'tasks.add_services_year_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'month_of_year':1},
                           'options': {'expires': 86400}})

        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'timedelta',
                                        'minutes':1},
                           'options': {'expires': 60}})

        uri = u'/v1.0/scheduler/entry'
        
        self.call(self.module, uri, u'POST', data=data, **self.users[u'admin'])

    def test_delete_scheduler_entry(self):
        global uid, seckey
                
        data = json.dumps({'name':'discover_openstack_01'})
        uri = u'/v1.0/scheduler/entry'
        
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])


if __name__ == u'__main__':
    runtest(SchedulerAPITestCase, tests)