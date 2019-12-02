# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.test import BeehiveTestCase, runtest
from beehive.common.task_v2.manager import configure_task_manager, configure_task_scheduler
from beehive.common.task_v2.canvas import signature
from beehive.common.task_v2.manager import task_manager
    
tests = [
    'test_run_test_task'
]


class TaskTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)

        configure_task_manager(self.worker.get('broker'), self.worker.get('result'),
                               task_queue=self.worker.get('queue'))
        configure_task_scheduler(self.worker.get('broker'), self.worker.get('result'),
                                 task_queue=self.worker.get('queue'))

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_run_test_task(self):
        params = {}
        user = {
            'user': 'user1',
            'server': 'server1',
            'identity': 'identity1',
            'api_id': 'apiid1'
        }
        entity = {
            'objid': 'objid1'
        }
        data = {
            'x': 2,
            'y': 234,
            'numbers': [2, 78, 45, 90]
        }
        params.update(user)
        params.update(entity)
        params.update(data)
        task = signature('beehive.module.scheduler_v2.tasks.test_task', [params], app=task_manager,
                         queue=self.worker.get('queue'))
        res = task.apply_async()
        self.logger.debug('start task: %s' % res)


def run(args):
    runtest(TaskTestCase, tests, args)


if __name__ == '__main__':
    run({})
