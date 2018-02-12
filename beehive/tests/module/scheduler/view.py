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
        self.module = u'auth'
        
    #
    # task manager
    #
    def test_ping_task_manager(self):
        data = u''
        uri = u'/v1.0/worker/ping'
        
        self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])

    def test_stat_task_manager(self):
        data = u''
        uri = u'/v1.0/worker/stats'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_report_task_manager(self):
        data = u''
        uri = u'/v1.0/worker/report'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_queues_task_manager(self):
        data = u''
        uri = u'/v1.0/worker/queues'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_all_tasks(self):
        data = u''
        uri = u'/v1.0/worker/tasks'
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_count_all_tasks(self):
        data = u''
        uri = u'/v1.0/worker/tasks/count'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task_definitions(self):
        data = u''
        uri = u'/v1.0/worker/tasks/definitions'
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task(self):
        data = u''
        global task_id
        uri = u'/v1.0/worker/tasks/%s' % task_id
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_get_task_graph(self):
        global task_id
        data = u''
        uri = u'/v1.0/worker/tasks/%s/graph' % task_id
        
        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_delete_all_tasks(self):
        data = u''
        uri = u'/v1.0/worker/tasks'
        
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])
        
    def test_delete_task(self):
        global task_id
        data = u''
        uri = u'/v1.0/worker/tasks/%s' % task_id
        
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])
        
    def test_run_job_test(self):
        global task_id
        data = {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]}
        uri = u'/v1.0/worker/tasks/test'
        res = self.call(self.module, uri, u'POST', data=data, **self.users[u'admin'])
        self.wait_job(res[u'jobid'], delta=1, accepted_state=u'SUCCESS')
        task_id = res[u'jobid']

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        data = u''
        uri = u'/v1.0/scheduler/entries'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])

    def test_get_scheduler_entries(self):
        data = u''
        uri = u'/v1.0/scheduler/entries'

        res = self.call(self.module, uri, u'GET', data=data, **self.users[u'admin'])

    def test_create_scheduler_entries(self):
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
        uri = u'/v1.0/scheduler/entries'
        self.call(self.module, uri, u'POST', data=data, **self.users[u'admin'])

    def test_delete_scheduler_entry(self):
        data = json.dumps({'name':'discover_openstack_01'})
        uri = u'/v1.0/scheduler/entries'
        self.call(self.module, uri, u'DELETE', data=data, **self.users[u'admin'])


if __name__ == u'__main__':
    runtest(SchedulerAPITestCase, tests)