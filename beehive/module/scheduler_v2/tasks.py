# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from logging import getLogger
from beehive.common.task_v2.manager import task_manager
from beehive.common.task_v2 import BaseTask, task_step
from beehive.module.scheduler_v2.controller import TaskManager

logger = getLogger(__name__)


class TestTask(BaseTask):
    name = 'test_task'
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

        self.steps = [
            TestTask.task_step0,
            TestTask.task_step1
        ]

    @staticmethod
    @task_step()
    def task_step0(task, step_id, params, *args, **kvargs):
        """Test task add x and y. Read x and y from shared data. Write mul in shared data.

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        """
        x = params['x']
        y = params['y']
        res = x + y

        # save data. Shared data must be re-kept before save modification because
        # concurrent tasks can change its content during task elaboration
        data = task.get_shared_data()
        data['mul'] = res
        task.set_shared_data(data)
        task.logger.debug('mul x=%s and y=%s: %s' % (x, y, res))
        task.progress(step_id, msg='add %s' % data)
        return res

    @staticmethod
    @task_step()
    def task_step1(task, step_id, params, *args, **kvargs):
        """Test job sum numbers.

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        """
        numbers = params.get('numbers')
        res = sum(numbers)

        # save data. Shared data must be re-kept before save modification because
        # concurrent tasks can change its content during task elaboration
        data = task.get_shared_data()
        data['res'] = res
        task.set_shared_data(data)
        task.progress(step_id, msg='sum %s' % numbers)
        task.logger.debug('sum numbers %s: %s' % (numbers, res))
        return res


task_manager.tasks.register(TestTask())
