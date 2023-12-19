# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import gevent.monkey

gevent.monkey.patch_all()

from beehive.common.task_v2.manager import (
    configure_task_manager,
    configure_task_scheduler,
)
from beehive.common.task_v2.canvas import signature
from beehive.common.task_v2.manager import task_manager
from beehive.common.test import runtest, BeehiveTestCase


tests = [
    "test_disable_expired_users",
    "test_remove_expired_roles_from_users",
]


class CatalogTaskManagerTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)

        configure_task_manager(
            self.worker.get("broker"),
            self.worker.get("result"),
            task_queue=self.worker.get("queue"),
        )
        configure_task_scheduler(
            self.worker.get("broker"),
            self.worker.get("result"),
            task_queue=self.worker.get("queue"),
        )
        self.logger.info("end setup")

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_disable_expired_users(self):
        params = {}
        user = {
            "user": "user1",
            "server": "server1",
            "identity": "identity1",
            "api_id": "apiid1",
        }
        entity = {"objid": "objid1"}
        data = {}
        self.logger.info("AAA passo 1")
        params.update(user)
        self.logger.info("AAA passo 2")
        params.update(entity)
        self.logger.info("AAA passo 3")
        params.update(data)
        self.logger.info("AAA passo 4")
        task = signature(
            "beehive.module.auth.tasks_v2.disable_expired_users_task",
            [params],
            app=task_manager,
            queue=self.worker.get("queue"),
        )
        self.logger.info("AAA passo 5")
        res = task.apply_async()
        self.logger.info("AAA passo 6")
        self.logger.debug("start task: %s" % res)

    def test_remove_expired_roles_from_users(self):
        params = {}
        user = {
            "user": "user1",
            "server": "server1",
            "identity": "identity1",
            "api_id": "apiid1",
        }
        entity = {"objid": "objid1"}
        data = {}
        params.update(user)
        params.update(entity)
        params.update(data)
        task = signature(
            "beehive.module.auth.tasks_v2.remove_expired_roles_from_users_task",
            [params],
            app=task_manager,
            queue=self.worker.get("queue"),
        )
        res = task.apply_async()
        self.logger.debug("start task: %s" % res)


def run(args):
    runtest(CatalogTaskManagerTestCase, tests, args)


if __name__ == "__main__":
    run({})
