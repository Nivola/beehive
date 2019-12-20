# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import traceback

from beehive.common.data import transaction, operation, query
from beehive.common.model import SchedulerTask, SchedulerState, AbstractDbManager, SchedulerTrace, SchedulerStep
from datetime import datetime
from celery.utils.log import get_task_logger
from celery.signals import task_prerun


logger = get_task_logger(__name__)


class TaskResult(object):
    """Utility class used to manage task, step and trace in database"""
    def __init__(self):
        self.manager = AbstractDbManager()

    @transaction
    def trace_add(self, task_id, step_id, message, level):
        """Add a task trace

        :param task_id: task id
        :param step_id: step id
        :param message: trace message
        :param level: trace level
        :return:
        """
        entity = self.manager.add_entity(SchedulerTrace, task_id, step_id, message, level)
        logger.debug2('add new db task trace %s record' % entity)

    @transaction
    def step_add(self, task_id, name):
        """Add a step

        :param task_id: task id
        :param name: step name
        :return:
        """
        entity = self.manager.add_entity(SchedulerStep, task_id, name)
        logger.debug2('add new db task step %s record' % entity)
        logger.info('add new step %s: %s' % (name, entity.uuid))
        self.trace_add(task_id, entity.uuid, 'start step', 'INFO')
        return entity.uuid

    @transaction
    def step_progress(self, task_id, step_id, msg=None):
        """Update a step

        :param task_id: task id
        :param step_id: step id
        :param msg: progress message
        :return:
        """
        run_time = datetime.today()
        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, run_time=run_time)
        logger.debug2('update task step %s record' % entity)

        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, run_time=run_time)
        logger.debug2('update db task %s record' % entity)

        logger.info('step %s progress' % step_id)

        if msg is not None:
            self.trace_add(task_id, step_id, msg, 'INFO')

    @transaction
    def step_success(self, task_id, step_id, result):
        """Update a step with success

        :param task_id: task id
        :param step_id: step id
        :param result: step result
        :return:
        """
        stop_time = datetime.today()
        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, status=SchedulerState.SUCCESS, result=result,
                                            stop_time=stop_time, run_time=stop_time)
        logger.debug2('update task step %s record' % entity)
        logger.info('step %s success' % step_id)
        self.trace_add(task_id, step_id, 'end step with result: %s' % result, 'INFO')

    @transaction
    def step_failure(self, task_id, step_id, error):
        """Update a step with failure

        :param task_id: task id
        :param step_id: step id
        :param error: step error
        :return:
        """
        stop_time = datetime.today()
        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, status=SchedulerState.FAILURE,
                                            stop_time=stop_time, result=error)
        logger.debug2('update task step %s record' % entity)
        logger.info('step %s error: %s' % (step_id, error))
        self.trace_add(task_id, step_id, 'step error: %s' % error, 'ERROR')

    @query
    def task_exists(self, task_id):
        """Check task exists

        :param task_id: task id
        :return:
        """
        entity = self.manager.exist_entity(SchedulerTask, task_id)
        if entity is True:
            logger.error('task %s already exists' % task_id)
            raise Exception('task %s already exists' % task_id)

    @transaction
    def task_prerun(self, **args):
        """Dispatched when a task pre run.

        :param args.task: celery task
        :param args.task_id: celery task id
        """
        task = args.get('task')
        task_id = args.get('task_id')

        start_time = datetime.today()

        self.task_exists(task_id)

        # create task in pending state
        status = SchedulerState.PENDING
        entity = self.manager.add_entity(SchedulerTask, task_id, task.name, status, start_time)
        logger.debug2('add new db task %s record' % entity)
        logger.info('send new task')

    @transaction
    def task_start(self, task):
        """Dispatched when a task start.

        :param task: celery task
        """
        task_id = task.request.id
        vargs = task.request.argsrepr
        kwargs = task.request.kwargsrepr

        entity = self.manager.get_entity(SchedulerTask, task_id)
        if entity.status != SchedulerState.PENDING:
            raise Exception('task %s is not in PENDING status' % task_id)

        # update task in pending state
        status = SchedulerState.STARTED
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, name=task.name, worker=task.request.hostname,
                                            objid=task.objid, objtype=task.objtype, objdef=task.objdef, args=vargs,
                                            kwargs=kwargs, status=status)
        logger.debug2('update db task %s record' % entity)
        logger.info('start task')
        self.trace_add(task_id, None, 'start task', 'INFO')

    @transaction
    def task_success(self, task, result):
        """Dispatched when a task success.

        :param task: celery task
        :param result: task result
        """
        task_id = task.request.id

        # set status
        status = SchedulerState.SUCCESS

        # get task stop_time
        stop_time = datetime.today()

        # update task in pending state
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, stop_time=stop_time, run_time=stop_time,
                                            status=status, result=result)
        logger.debug2('update db task %s record' % entity)
        logger.info('task finished')
        self.trace_add(task_id, None, 'end task with result: %s' % result, 'INFO')

    @transaction
    def task_failure(self, task, err):
        """Dispatched when a task fails.

        :param task: celery task
        :param err: error message
        """
        task_id = task.request.id

        # set status
        status = SchedulerState.FAILURE

        # get exception info
        trace = traceback.format_exc()

        # get task stop_time
        stop_time = datetime.today()

        # update task in pending state
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, stop_time=stop_time, run_time=stop_time,
                                            status=status, result=err)
        logger.debug('update db task %s record' % entity)
        logger.info('task failed: %s' % trace)

        self.trace_add(task_id, None, trace, 'ERROR')

    @transaction
    def task_update(self, task_id, **args):
        """Update a task

        :param task_id: task id
        :param args: key value args
        :return:
        """
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, **args)
        logger.debug2('update db task %s record' % entity)

        self.trace_add(task_id, None, 'update task', 'INFO')


@task_prerun.connect
def task_prerun(**args):
    task = args.get('task')
    task.get_session()
    operation.transaction = None
    TaskResult().task_prerun(**args)
    task.release_session()


# @task_postrun.connect
# def task_postrun(**args):
#     task = args.get('task')
#     task.get_session()
#     operation.transaction = None
#     TaskResult().task_postrun(**args)


# @task_failure.connect
# def task_failure(**args):
#     operation.transaction = None
#     TaskResult().task_failure(**args)
