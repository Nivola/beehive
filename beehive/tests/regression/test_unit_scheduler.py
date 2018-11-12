"""
Created on Feb 09, 2018

@author: darkbk

Use this test_unit to test openstack entities
"""
from beehive.common.test import runtest
from beehive.tests.module.auth.view import AuthTestCase
from beehive.tests.module.event.view import EventTestCase
from beehive.tests.module.basic.view import BaseTestCase
from beehive.tests.module.catalog.view import CatalogTestCase
from beehive.tests.module.scheduler.view import SchedulerAPITestCase

tests_scheduler = [
    u'test_ping_task_manager',
    u'test_stat_task_manager',
    u'test_report_task_manager',
    u'test_queues_task_manager',
    u'test_get_all_tasks',
    u'test_count_all_tasks',
    u'test_get_task_definitions',
    u'test_run_job_test',
    u'test_get_task',
    u'test_get_task_graph',
    u'test_delete_task',
    u'test_run_job_test',
    u'test_delete_all_tasks',
    u'test_create_scheduler_entries',
    u'test_get_scheduler_entries',
    u'test_get_scheduler_entry',
    u'test_delete_scheduler_entry',
]


class TestCase(SchedulerAPITestCase):
    validation_active = False

    def setUp(self):
        SchedulerAPITestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'


tests = []
for test_plans in [
    tests_scheduler
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
