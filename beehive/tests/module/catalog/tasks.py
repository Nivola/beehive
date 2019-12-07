# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.task_v2.manager import configure_task_manager, configure_task_scheduler
from beehive.common.task_v2.canvas import signature
from beehive.common.task_v2.manager import task_manager
from beehive.common.test import runtest, BeehiveTestCase


tests = [
    'test_run_refresh_catalog'
]


class CatalogTaskManagerTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)

        configure_task_manager(self.worker.get('broker'), self.worker.get('result'),
                               task_queue=self.worker.get('queue'))
        configure_task_scheduler(self.worker.get('broker'), self.worker.get('result'),
                                 task_queue=self.worker.get('queue'))

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_run_refresh_catalog(self):
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
        data = {}
        params.update(user)
        params.update(entity)
        params.update(data)
        task = signature('beehive.module.catalog.tasks_v2.refresh_catalog_task', [params], app=task_manager,
                         queue=self.worker.get('queue'))
        res = task.apply_async()
        self.logger.debug('start task: %s' % res)


def run(args):
    runtest(CatalogTaskManagerTestCase, tests, args)


if __name__ == '__main__':
    run({})
