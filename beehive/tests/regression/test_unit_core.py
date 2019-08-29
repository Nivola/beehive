# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.test import runtest
from beehive.tests.module.auth.view import AuthTestCase
from beehive.tests.module.event.view import EventTestCase
from beehive.tests.module.basic.view import BaseTestCase
from beehive.tests.module.catalog.view import CatalogTestCase
from beehive.tests.module.scheduler.view import SchedulerAPITestCase

tests_base = [
    u'test_ping',
    u'test_info',
]


class TestCase(BaseTestCase):
    validation_active = False

    def setUp(self):
        BaseTestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'
        self.endpoint_service = u'auth'


tests = []
for test_plans in [
    tests_base
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
