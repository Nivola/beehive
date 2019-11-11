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
    'test_add_role',
    'test_add_role_twice',
    'test_get_roles',
    'test_get_role',
    'test_update_role',
    'test_add_role_perm',
    'test_get_perms_by_role',
    'test_remove_role_perm',
    'test_delete_role',

    'test_add_user',
    'test_add_user_twice',
    'test_get_users',
    'test_get_users_by_role',
    'test_get_user',
    'test_get_user_secret',
    'test_get_user_roles',
    'test_add_user_attributes',
    'test_get_user_attributes',
    'test_delete_user_attributes',
    'test_update_user',
    'test_add_user_role',
    'test_get_perms_by_user',
    'test_remove_user_role',
    'test_delete_user',

    'test_add_group',
    'test_add_group_twice',
    'test_get_groups',
    'test_get_group',
    'test_update_group',
    'test_add_group_user',
    'test_get_groups_by_user',
    'test_remove_group_user',
    'test_add_group_role',
    'test_get_groups_by_role',
    'test_get_perms_by_group',
    'test_remove_group_role',
    'test_delete_group',

    'test_get_actions',

    'test_add_type',
    'test_add_type_twice',
    'test_get_types',
    'test_delete_type',

    'test_add_object',
    'test_add_object_twice',
    'test_get_objects',
    'test_get_object',
    'test_delete_object',

    'test_get_perms',
    'test_get_perms_by_type',
    'test_get_perm',

    'test_get_providers',
    'test_get_tokens',
    'test_get_token',
    'test_delete_token',
]


class TestCase(AuthTestCase):
    validation_active = False

    def setUp(self):
        AuthTestCase.setUp(self)
        self.module = 'auth'
        self.module_prefix = 'nas'
        self.endpoint_service = 'auth'


tests = []
for test_plans in [
    tests_auth
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == '__main__':
    run()
