# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.test import runtest, BeehiveTestCase

task_id = '4dc35bd0-5494-4f54-8f52-4e8e0b3fc752'
schedule_id = None

tests = [
    # 'test_ping_task_manager',
    # 'test_stat_task_manager',
    # 'test_report_task_manager',
    # 'test_queues_task_manager',
    # 'test_get_task_definitions',
    # 
    'test_run_test_task',
    # 'test_get_all_tasks',
    # 'test_get_task',
    # 'test_get_task_status',
    # 'test_get_task_trace',
    # 'test_get_task_graph',
    # 'test_delete_task',
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
        self.endpoint_service = 'auth'

    def tearDown(self):
        BeehiveTestCase.tearDown(self)
        
    #
    # task manager
    #
    def test_ping_task_manager(self):
        self.get('/v2.0/nas/worker/ping')

    def test_stat_task_manager(self):
        self.get('/v2.0/nas/worker/stats')

    def test_report_task_manager(self):
        self.get('/v2.0/nas/worker/report')

    def test_queues_task_manager(self):
        self.get('/v2.0/nas/worker/queues')

    def test_get_all_tasks(self):
        res = self.get('/v2.0/nas/worker/tasks', query={'elapsed': 3600})
        global task_id
        task_id = res['task_instances'][0]['uuid']

    def test_get_task_definitions(self):
        self.get('/v2.0/nas/worker/tasks/definitions')

    def test_get_task(self):
        global task_id
        self.get('/v2.0/nas/worker/tasks/%s' % task_id)

    def test_get_task_status(self):
        global task_id
        self.get('/v2.0/nas/worker/tasks/%s/status' % task_id)

    def test_get_task_trace(self):
        global task_id
        self.get('/v2.0/nas/worker/tasks/%s/trace' % task_id)

    # def test_get_task_graph(self):
    #     global task_id
    #     self.get('/v2.0/nas/worker/tasks/%s/graph' % task_id)
    #
    # def test_delete_all_tasks(self):
    #     self.delete('/v2.0/nas/worker/tasks')
    #
    # def test_delete_task(self):
    #     global task_id
    #     self.delete('/v2.0/nas/worker/tasks/%s' % task_id)
    #
    def test_run_test_task(self):
        global task_id
        data = {'x': 2, 'y': 234, 'numbers': [2, 78, 45, 90], 'mul_numbers': []}
        res = self.post('/v2.0/nas/worker/tasks/test', data=data)
        self.logger.debug(res)

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        res = self.get('/v2.0/nas/scheduler/entries')
        global schedule_id
        schedule_id = res['schedules'][0]['name']

    def test_get_scheduler_entry(self):
        global schedule_id
        self.get('/v2.0/nas/scheduler/entries/%s' % schedule_id)

    def test_create_scheduler_entries(self):
        data = {
            'name': 'celery.backend_cleanup',
            'task': 'celery.backend_cleanup',
            'schedule': {
                'type': 'crontab',
                'minute': 2,
                'hour': '*',
                'day_of_week': '*',
                'day_of_month': '*',
                'month_of_year': '*'
            },
            'options': {'expires': 60}
        }
        # data = {
        #     'name': 'celery.backend_cleanup',
        #     'task': 'celery.backend_cleanup',
        #     'schedule': {
        #         'type': 'timedelta',
        #         'minutes': 1
        #     },
        #     'options': {'expires': 60}
        # }
        self.post('/v2.0/nas/scheduler/entries', data={'schedule': data})

    def test_delete_scheduler_entry(self):
        self.delete('/v2.0/nas/scheduler/entries/%s' % 'celery.backend_cleanup')


def run(args):
    runtest(SchedulerAPITestCase, tests, args)


if __name__ == '__main__':
    run({})
