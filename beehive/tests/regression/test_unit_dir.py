# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.test import runtest
from beehive.tests.module.auth.view import AuthTestCase
from beehive.tests.module.event.view import EventTestCase
from beehive.tests.module.basic.view import BaseTestCase
from beehive.tests.module.catalog.view import CatalogTestCase
from beehive.tests.module.scheduler.view import SchedulerAPITestCase

tests_dir = [
    u'test_add_catalog',
    u'test_add_catalog_twice',
    u'test_get_catalogs',
    u'test_get_catalogs_by_zone',
    u'test_get_catalog',
    u'test_get_catalog_perms',
    u'test_get_catalog_by_name',
    u'test_update_catalog',

    u'test_add_endpoint',
    u'test_add_endpoint_twice',
    u'test_get_endpoints',
    u'test_filter_endpoints',
    u'test_get_endpoint',
    u'test_update_endpoint',
    u'test_delete_endpoint',

    u'test_delete_catalog',
]


class TestCase(CatalogTestCase):
    validation_active = False

    def setUp(self):
        CatalogTestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'
        self.endpoint_service = u'auth'


tests = []
for test_plans in [
    tests_dir
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
