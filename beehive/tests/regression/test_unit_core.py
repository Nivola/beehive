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

tests_base = [
    'test_ping',
    'test_info',
]

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

    u'test_get_domains',
    u'test_get_tokens',
    u'test_get_token',
    u'test_delete_token',
]

tests_catalog = [
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

tests_event = [
    u'test_get_event_types',
    u'test_get_event_entities',
    u'test_get_events',
]

tests_scheduler = [
    'test_ping_task_manager',
    # 'test_stat_task_manager',
    # 'test_report_task_manager',
    # 'test_queues_task_manager',
    # 'test_get_all_tasks',
    # 'test_count_all_tasks',
    # 'test_get_task_definitions',
    # 'test_run_job_test',
    # 'test_get_task',
    # 'test_get_task_graph',
    # 'test_delete_task',
    # 'test_run_job_test',
    # 'test_delete_all_tasks',
    # 'test_create_scheduler_entries',
    # 'test_get_scheduler_entries',
    # 'test_get_scheduler_entry',
    # 'test_delete_scheduler_entry',
]


class CoreTestCase(BaseTestCase, AuthTestCase, EventTestCase, CatalogTestCase, SchedulerAPITestCase):
    pass


if __name__ == u'__main__':
    for tests in [
        # tests_base,
        # tests_auth,
        # tests_catalog,
        # tests_event,
        tests_scheduler
    ]:
        runtest(CoreTestCase, tests)
