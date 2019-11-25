# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from logging import getLogger
from beehive.common.task.manager import task_manager
from beehive.common.task_v2 import BaseTask
from beehive.module.scheduler_v2.controller import TaskManager

logger = getLogger(__name__)


def task_step0(task, params):
    """Test task add x and y. Read x and y from shared data. Write mul in shared data.

    :param task: parent celery task
    :param dict params: step params
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
    # task.update('PROGRESS', msg='add %s' % data)
    return res


def task_step1(task, params):
    """Test job sum numbers.

    :param task: parent celery task
    :param dict params: step params
    """
    numbers = params.get('numbers')
    res = sum(numbers)

    # save data. Shared data must be re-kept before save modification because
    # concurrent tasks can change its content during task elaboration
    data = task.get_shared_data()
    data['res'] = res
    task.set_shared_data(data)
    # self.update('PROGRESS', msg='sum %s' % numbers)
    task.logger.debug('sum numbers %s: %s' % (numbers, res))
    return res


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
            task_step0,
            task_step1
        ]


task_manager.tasks.register(TestTask())

# @task_manager.task(bind=True, base=BaseTask)
# def test_task(self, params):
#     """Test task
#
#     :param objid: objid. Ex. 110//2222//334//*
#     :param x: x
#     :param y: y
#     :param numbers: numbers
#     :param error: error
#     :param suberror: suberror
#     """
#     # ops = self.get_options()
#     # self.set_shared_data(params)
#
#     # g1 = []
#     # for i in range(0, len(params['numbers'])):
#     #     g1.append(jobtest_task3.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
#     # if params['error'] is True:
#     #     g1.append(test_raise.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
#     #
#     # g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
#
#     steps = [
#         task_step0,
#         task_step1
#     ]
#     params['steps'] = steps
#
#     return True




