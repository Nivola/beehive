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


tests_event = [
    u'test_get_event_types',
    u'test_get_event_entities',
    u'test_get_events',
]


class TestCase(EventTestCase):
    validation_active = False

    def setUp(self):
        EventTestCase.setUp(self)
        self.module = u'event'
        self.module_prefix = u'nes'


tests = []
for test_plans in [
    tests_event
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
