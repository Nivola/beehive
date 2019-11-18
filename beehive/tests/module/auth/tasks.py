# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import unittest
from beehive.common.task.manager import configure_task_manager,\
    configure_task_scheduler
from beehive.module.auth.tasks import disable_expired_users,\
    remove_expired_roles_from_users
from beehive.common.test import runtest, BeehiveTestCase

tests = [
    'test_disable_expired_users',
    # 'test_remove_expired_roles_from_users',
]


class AuthTaskTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'auth'
        self.module_prefix = 'nas'
        self.endpoint_service = 'auth'

        configure_task_manager(self.broker, self.broker)
        configure_task_scheduler(self.broker, self.broker)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_disable_expired_users(self):
        data = {}
        task = disable_expired_users.delay('*', data)
        
    def test_remove_expired_roles_from_users(self):
        data = {}
        task = remove_expired_roles_from_users.delay('*', data)


if __name__ == '__main__':
    runtest(AuthTaskTestCase, tests)
