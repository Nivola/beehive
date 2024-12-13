# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.test import BeehiveTestCase, runtest
from beehive.common.task.manager import configure_task_manager, configure_task_scheduler
from beehive.module.scheduler.tasks import jobtest

tests = ["test_run_jobtest"]


class TaskTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)

        configure_task_manager(self.broker, self.broker)
        configure_task_scheduler(self.broker, self.broker)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_run_jobtest(self):
        data = {"x": 2, "y": 234, "numbers": [2, 78, 45, 90]}
        task = jobtest.delay("123", **data)


def run(args):
    runtest(TaskTestCase, tests, args)


if __name__ == "__main__":
    run({})
