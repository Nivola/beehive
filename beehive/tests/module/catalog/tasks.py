# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import unittest
from beehive.common.task.manager import configure_task_manager,\
    configure_task_scheduler
from beehive.module.catalog.tasks import refresh_catalog
from beehive.common.test import runtest, BeehiveTestCase


class CatalogTaskManagerTestCase(BeehiveTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        configure_task_manager(self.broker, self.broker)
        configure_task_scheduler(self.broker, self.broker)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_run_refresh_catalog(self):
        data = {}
        task = refresh_catalog.delay('*', data)


def test_suite():
    tests = [
        'test_run_refresh_catalog',
    ]
    return unittest.TestSuite(map(CatalogTaskManagerTestCase, tests))

if __name__ == '__main__':
    runtest(test_suite())