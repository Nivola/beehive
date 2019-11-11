# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.test import runtest
from beehive.tests.module.scheduler.view import SchedulerAPITestCase

tests_task = [
    'test_ping_task_manager',
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
    # ### 'test_run_concurrent_job_test',
    # 'test_delete_all_tasks',
]

tests_scheduler = [
    'test_create_scheduler_entries',
    'test_get_scheduler_entries',
    'test_get_scheduler_entry',
    'test_delete_scheduler_entry',
]


class TestSchedulerCase(SchedulerAPITestCase):
    validation_active = False

    def setUp(self):
        SchedulerAPITestCase.setUp(self)
        self.module = 'auth'
        self.module_prefix = 'nas'
        self.endpoint_service = 'auth'

    #
    # task manager
    #
    def test_ping_task_manager(self):
        self.get('/v1.0/nas/worker/ping')

    def test_stat_task_manager(self):
        res = self.get('/v1.0/nas/worker/stats')

    def test_report_task_manager(self):
        res = self.get('/v1.0/nas/worker/report')

    def test_queues_task_manager(self):
        res = self.get('/v1.0/nas/worker/queues')

    def test_get_all_tasks(self):
        res = self.get('/v1.0/nas/worker/tasks')

    def test_count_all_tasks(self):
        res = self.get('/v1.0/nas/worker/tasks/count')

    def test_get_task_definitions(self):
        res = self.get('/v1.0/nas/worker/tasks/definitions')

    def test_get_task(self):
        global task_id
        res = self.get('/v1.0/nas/worker/tasks/%s' % task_id)

    def test_get_task_graph(self):
        global task_id
        res = self.get('/v1.0/nas/worker/tasks/%s/graph' % task_id)
        self.logger.info(self.pp.pformat(res))

    def test_delete_all_tasks(self):
        self.delete('/v1.0/nas/worker/tasks')

    def test_delete_task(self):
        global task_id
        self.delete('/v1.0/nas/worker/tasks/%s' % task_id)

    def test_run_job_test(self):
        global task_id
        data = {'x': 2, 'y': 234, 'numbers': [2, 78, 45, 90], 'mul_numbers': []}
        res = self.post('/v1.0/nas/worker/tasks/test', data=data)
        # self.wait_job(res['jobid'], delta=1, accepted_state='SUCCESS')
        task_id = res['jobid']

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        res = self.get('/v1.0/nas/scheduler/entries')
        global schedule_id
        schedule_id = res['schedules'][0]['name']

    def test_get_scheduler_entry(self):
        global schedule_id
        res = self.get('/v1.0/nas/scheduler/entries/%s' % schedule_id)

    def test_create_scheduler_entries(self):
        data = {
            'name': 'celery.backend_cleanup',
            'task': 'celery.backend_cleanup',
            'schedule': {'type': 'crontab',
                         'minute': 2,
                         'hour': '*',
                         'day_of_week': '*',
                         'day_of_month': '*',
                         'month_of_year': '*'},
            'options': {'expires': 60}
        }
        data = {
            'name': 'celery.backend_cleanup',
            'task': 'celery.backend_cleanup',
            'schedule': {'type': 'timedelta',
                         'minutes': 1},
            'options': {'expires': 60}
        }
        self.post('/v1.0/nas/scheduler/entries', data={'schedule': data})

    def test_delete_scheduler_entry(self):
        self.delete('/v1.0/nas/scheduler/entries/%s' % 'celery.backend_cleanup', data='')

    def test_run_concurrent_job_test(self):
        data = {'x': 2, 'y': 234, 'numbers': [2, 78, 45, 90], 'mul_numbers': []}
        uri = '/v1.0/nas/worker/tasks/test'
        max_tasks = 20
        i = 0
        while i < max_tasks:
            job = self.post(uri,  data=data)
            self.logger.debug('Start job: %s' % job)
            i += 1
        # self.wait_job(res['jobid'], delta=1, accepted_state='SUCCESS')
        # task_id = res['jobid']


tests = []
for test_plans in [
    tests_task,
    tests_scheduler
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestSchedulerCase, tests, args)


if __name__ == '__main__':
    run()
