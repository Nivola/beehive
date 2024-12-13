# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from logging import getLogger
from time import sleep
from beehive.common.task_v2.manager import task_manager
from beehive.common.task_v2 import (
    BaseTask,
    task_step,
    prepare_or_run_task,
    run_sync_task,
)
from beehive.module.scheduler_v2.controller import TaskManager

logger = getLogger(__name__)


class TestTask(BaseTask):
    name = "test_task"
    entity_class = TaskManager

    """Test task

    :param objid: objid. Ex. 110//2222//334//*
    :param x: x
    :param y: y
    :param numbers: numbers
    :param error: error
    :param suberror: suberror
    """

    def __init__(self, *args, **kwargs):
        super(TestTask, self).__init__(*args, **kwargs)

        self.steps = [TestTask.task_step0, TestTask.task_step1, TestTask.task_step2]

    @staticmethod
    @task_step()
    def task_step0(task, step_id, params, *args, **kvargs):
        """Test step add x and y. Read x and y from shared data. Write mul in shared data.

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: res, params
        """
        x = params["x"]
        y = params["y"]
        res = x + y

        # save data. Shared data must be re-kept before save modification because
        # concurrent tasks can change its content during task elaboration
        data = task.get_shared_data()
        data["mul"] = res
        task.set_shared_data(data)
        task.logger.debug("mul x=%s and y=%s: %s" % (x, y, res))
        task.progress(step_id, msg="add %s" % data)
        return res, params

    @staticmethod
    @task_step()
    def task_step1(task, step_id, params, *args, **kvargs):
        """Test step sum numbers.

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        :return: res, params
        """
        numbers = params.get("numbers")
        res = sum(numbers)

        # save data. Shared data must be re-kept before save modification because
        # concurrent tasks can change its content during task elaboration
        data = task.get_shared_data()
        data["res"] = res
        task.set_shared_data(data)
        task.progress(step_id, msg="sum %s" % numbers)
        task.logger.debug("sum numbers %s: %s" % (numbers, res))
        return res, params

    @staticmethod
    @task_step()
    def task_step2(task, step_id, params, *args, **kvargs):
        """Test step run a sync task

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        :return: res, params
        """
        # user = {
        #     'user': operation.user[0],
        #     'server': operation.user[1],
        #     'identity': operation.user[2],
        #     'api_id': operation.id
        # }
        # new_params = deepcopy(params)
        # new_params.update(user)
        prepared_task, code = prepare_or_run_task(
            TaskManager(task.controller),
            "beehive.module.scheduler_v2.tasks.test2_task",
            params,
            sync=True,
        )
        task.progress(step_id, msg="task_step2 - prepared_task: %s" % (prepared_task))
        task.logger.debug("task_step2 - prepared_task: %s" % (prepared_task))

        res = run_sync_task(prepared_task, task, step_id)
        task.progress(step_id, msg="task_step2 - res: %s" % (res))
        task.logger.debug("task_step2 - res: %s" % (res))

        return res, params

    def failure(self, params, error):
        self.logger.warning("task %s failed", self.request.id)


class Test2Task(BaseTask):
    name = "test2_task"
    entity_class = TaskManager

    """Test task

    :param objid: objid. Ex. 110//2222//334//*
    :param x: x
    :param y: y
    :param numbers: numbers
    :param error: error
    :param suberror: suberror
    """

    def __init__(self, *args, **kwargs):
        super(Test2Task, self).__init__(*args, **kwargs)

        self.steps = [Test2Task.task_step0, Test2Task.task_step1]

    @staticmethod
    @task_step()
    def task_step0(task, step_id, params, *args, **kvargs):
        """Test step sleep a little

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: res, params
        """
        sleep(2)
        res = True
        task.progress(step_id, msg="step wait a little")
        return res, params

    @staticmethod
    @task_step()
    def task_step1(task, step_id, params, *args, **kvargs):
        """Test step invoke async api

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: res, params
        """
        # lancio il test3 (test_inline_task) che termina e NON ricursivamente il task/test
        uri = "/v2.0/nas/worker/tasks/test3"
        data = {"x": 2, "y": 234, "numbers": [2, 78, 45, 90], "mul_numbers": []}
        res = task.invoke_api("auth", uri, "post", data=data)
        if res is not None:
            taskid = res.get("taskid")
            task.wait_task("auth", "nas", taskid, timeout=60, delta=3, maxtime=600, trace=None)
            task.progress(step_id, msg="invoke an api from a task")
            return res.get("result", None), params
        return None, params

    def failure(self, params, error):
        self.logger.warning("task %s failed", self.request.id)


class ScheduledActionTask(BaseTask):
    name = "scheduled_action_task"
    entity_class = TaskManager

    def __init__(self, *args, **kwargs):
        """Use this task to schedule an action

        :param args:
        :param kwargs:
        """
        super(ScheduledActionTask, self).__init__(*args, **kwargs)

        self.steps = []

    @staticmethod
    @task_step()
    def remove_schedule_step(task, step_id, params, *args, **kvargs):
        """Remove schedule

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """
        schedule_name = params.get("schedule_name")
        task.controller.remove_schedule(schedule_name)
        task.progress(step_id, msg="remove schedule %s" % schedule_name)
        return True, params

    @staticmethod
    @task_step()
    def task_step(task, step_id, params, *args, **kvargs):
        """Test step

        :param task: parent celery task
        :param str step_id: step id
        :param dict params: step params
        :return: True, params
        """
        task.progress(step_id, msg="simple test step")
        return True, params


task_manager.tasks.register(TestTask())
task_manager.tasks.register(Test2Task())
task_manager.tasks.register(ScheduledActionTask())
