'''
Created on Feb 09, 2018

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
import ujson as json

uid = None
seckey = None
task_id = 'd124ef29-7c57-423e-b6d9-b72d519d7600'
schedule_id = None

tests = [
    # 'test_ping_task_manager',
    # 'test_stat_task_manager',
    # 'test_report_task_manager',
    # 'test_queues_task_manager',
    # 'test_get_all_tasks',
    # 'test_count_all_tasks',
    # 'test_get_task_definitions',
    # 'test_run_job_test',
    # 'test_get_task',
    # 'test_get_task_graph',
    # 'test_delete_task',
    # 'test_run_job_test',
    # 'test_delete_all_tasks',
    #
    # 'test_create_scheduler_entries',
    # 'test_get_scheduler_entries',
    # 'test_get_scheduler_entry',
    # 'test_delete_scheduler_entry',
]


class SchedulerAPITestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'auth'
        self.module_prefix = 'nas'
        
    #
    # task manager
    #
    def test_ping_task_manager(self):
        data = ''
        uri = '/v1.0/nas/worker/ping'
        
        self.call(self.module, uri, 'get', data=data, **self.users['admin'])

    def test_stat_task_manager(self):
        data = ''
        uri = '/v1.0/nas/worker/stats'
        
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_report_task_manager(self):
        data = ''
        uri = '/v1.0/nas/worker/report'
        
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_queues_task_manager(self):
        data = ''
        uri = '/v1.0/nas/worker/queues'

        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_all_tasks(self):
        data = ''
        uri = '/v1.0/nas/worker/tasks'
        
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_count_all_tasks(self):
        data = ''
        uri = '/v1.0/nas/worker/tasks/count'

        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task_definitions(self):
        data = ''
        uri = '/v1.0/nas/worker/tasks/definitions'
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))

    def test_get_task(self):
        data = ''
        global task_id
        uri = '/v1.0/nas/worker/tasks/%s' % task_id
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_get_task_graph(self):
        global task_id
        data = ''
        uri = '/v1.0/nas/worker/tasks/%s/graph' % task_id
        
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        self.logger.info(self.pp.pformat(res))
        
    def test_delete_all_tasks(self):
        data = ''
        uri = '/v1.0/nas/worker/tasks'
        
        self.call(self.module, uri, 'delete', data=data, **self.users['admin'])
        
    def test_delete_task(self):
        global task_id
        data = ''
        uri = '/v1.0/nas/worker/tasks/%s' % task_id
        
        self.call(self.module, uri, 'delete', data=data, **self.users['admin'])
        
    def test_run_job_test(self):
        global task_id
        data = {'x': 2, 'y': 234, 'numbers': [2, 78, 45, 90], 'mul_numbers':[]}
        uri = '/v1.0/nas/worker/tasks/test'
        res = self.call(self.module, uri, 'post', data=data, **self.users['admin'])
        self.wait_job(res['jobid'], delta=1, accepted_state='SUCCESS')
        task_id = res['jobid']

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        data = ''
        uri = '/v1.0/nas/scheduler/entries'
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])
        global schedule_id
        schedule_id = res['schedules'][0]['name']

    def test_get_scheduler_entry(self):
        global schedule_id
        data = ''
        uri = '/v1.0/nas/scheduler/entries/%s' % schedule_id
        res = self.call(self.module, uri, 'get', data=data, **self.users['admin'])

    def test_create_scheduler_entries(self):
        data = {
            'name':'celery.backend_cleanup',
            'task': 'celery.backend_cleanup',
            'schedule': {'type':'crontab',
                        'minute':2,
                        'hour':'*',
                        'day_of_week':'*',
                        'day_of_month':'*',
                        'month_of_year':'*'},
            'options': {'expires': 60}
        }
        data = {
            'name':'celery.backend_cleanup',
            'task': 'celery.backend_cleanup',
            'schedule': {'type':'timedelta',
                        'minutes':1},
            'options': {'expires': 60}
        }
        uri = '/v1.0/nas/scheduler/entries'
        self.call(self.module, uri, 'post', data={'schedule':data}, **self.users['admin'])

    def test_delete_scheduler_entry(self):
        uri = '/v1.0/nas/scheduler/entries/%s' % 'celery.backend_cleanup'
        self.call(self.module, uri, 'delete', data='', **self.users['admin'])


if __name__ == '__main__':
    runtest(SchedulerAPITestCase, tests)
