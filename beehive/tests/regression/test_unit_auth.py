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


tests_auth = [
    u'test_add_role',
    u'test_add_role_twice',
    u'test_get_roles',
    u'test_get_role',
    u'test_update_role',
    u'test_add_role_perm',
    u'test_get_perms_by_role',
    u'test_remove_role_perm',
    u'test_delete_role',

    u'test_add_user',
    u'test_add_user_twice',
    u'test_get_users',
    u'test_get_users_by_role',
    u'test_get_user',
    u'test_get_user_secret',
    u'test_get_user_roles',
    u'test_add_user_attributes',
    u'test_get_user_attributes',
    u'test_delete_user_attributes',
    u'test_update_user',
    u'test_add_user_role',
    u'test_get_perms_by_user',
    u'test_remove_user_role',
    u'test_delete_user',

    u'test_add_group',
    u'test_add_group_twice',
    u'test_get_groups',
    u'test_get_group',
    u'test_update_group',
    u'test_add_group_user',
    u'test_get_groups_by_user',
    u'test_remove_group_user',
    u'test_add_group_role',
    u'test_get_groups_by_role',
    u'test_get_perms_by_group',
    u'test_remove_group_role',
    u'test_delete_group',

    u'test_get_actions',

    u'test_add_type',
    u'test_add_type_twice',
    u'test_get_types',
    u'test_delete_type',

    u'test_add_object',
    u'test_add_object_twice',
    u'test_get_objects',
    u'test_get_object',
    u'test_delete_object',

    u'test_get_perms',
    u'test_get_perms_by_type',
    u'test_get_perm',

    u'test_get_providers',
    u'test_get_tokens',
    u'test_get_token',
    u'test_delete_token',
]


class TestCase(AuthTestCase):
    validation_active = False

    def setUp(self):
        AuthTestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'
        self.endpoint_service = u'auth'


tests = []
for test_plans in [
    tests_auth
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
