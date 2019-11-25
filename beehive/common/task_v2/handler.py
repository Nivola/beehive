# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.data import transaction, operation
from beehive.common.model import SchedulerTask, SchedulerState, AbstractDbManager, SchedulerTrace, SchedulerStep
from datetime import datetime
from celery.utils.log import get_task_logger
from celery.signals import task_prerun, task_postrun, task_failure
from traceback import format_tb
import ujson as json


logger = get_task_logger(__name__)


class TaskResult(object):
    def __init__(self):
        self.manager = AbstractDbManager()

    @transaction
    def trace_add(self, task_id, step_id, message, level):
        entity = self.manager.add_entity(SchedulerTrace, task_id, step_id, message, level)
        logger.debug('add new db task trace %s record' % entity)

    @transaction
    def step_add(self, task_id, name):
        entity = self.manager.add_entity(SchedulerStep, task_id, name)
        logger.debug('add new db task step %s record' % entity)

        self.trace_add(task_id, entity.uuid, 'start step', 'INFO')
        return entity.uuid

    @transaction
    def step_success(self, task_id, step_id, result):
        stop_time = datetime.today()
        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, status=SchedulerState.SUCCESS, result=result,
                                            stop_time=stop_time)
        logger.debug('update task step %s record' % entity)

        self.trace_add(task_id, step_id, 'end step with result: %s' % result, 'INFO')

    @transaction
    def step_failure(self, step_id, error):
        stop_time = datetime.today()
        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, status=SchedulerState.FAILURE,
                                            stop_time=stop_time, result=error)
        logger.debug('update task step %s record' % entity)

        self.trace_add(entity.task_id, step_id, 'step error: %s' % error, 'ERROR')

    @transaction
    def task_pending(self, task_id):
        start_time = datetime.today()

        # create task in pending state
        status = SchedulerState.PENDING
        entity = self.manager.add_entity(SchedulerTask, task_id, status, start_time)
        logger.debug('add new db task %s record' % entity)

    @transaction
    def task_prerun(self, **args):
        # store task
        task = args.get('task')
        task_id = args.get('task_id')
        vargs = args.get('args')
        kwargs = args.get('kwargs')

        try:
            vargs = json.dumps(vargs)
        except:
            vargs = ''

        try:
            kwargs = json.dumps(kwargs)
        except:
            kwargs = ''

        # update task in pending state
        status = SchedulerState.STARTED
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, name=task.name, worker=task.request.hostname,
                                            objid=task.objid, objtype=task.objtype, objdef=task.objdef, args=vargs,
                                            kwargs=kwargs, status=status)
        logger.debug('update db task %s record' % entity)

        self.trace_add(task_id, None, 'start task', 'INFO')

    @transaction
    def task_postrun(self, **args):
        task = args.get('task')
        task_id = args.get('task_id')
        status = args.get('state')
        result = args.get('retval')

        # get task stop_time
        stop_time = datetime.today()

        # update task in pending state
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, stop_time=stop_time, status=status,
                                            result=result)
        logger.debug('update db task %s record' % entity)

        self.trace_add(task_id, None, 'end task with result: %s' % result, 'INFO')

    @transaction
    def task_failure(self, **args):
        """Dispatched when a task fails. Sender is the task object executed.

        Provides arguments:
        - task_id: Id of the task.
        - exception: Exception instance raised.
        - args: Positional arguments the task was called with.
        - kwargs: Keyword arguments the task was called with.
        - traceback: Stack trace object.
        - einfo: The billiard.einfo.ExceptionInfo instance.
        """
        task_id = args.get('task_id')
        exception = args.get('exception')
        einfo = args.get('einfo')

        # set status
        status = SchedulerState.FAILURE

        # get exception info
        err = str(exception)
        trace = format_tb(einfo.tb)
        trace.append(err)

        # get task stop_time
        stop_time = datetime.today()

        # update task in pending state
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, stop_time=stop_time, status=status, result=err)
        logger.debug('update db task %s record' % entity)

        self.trace_add(task_id, None, '\n'.join(trace), 'ERROR')

    @transaction
    def task_update(self, task_id, **args):
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, **args)
        logger.debug('update db task %s record' % entity)

        self.trace_add(task_id, None, 'update task', 'INFO')


@task_prerun.connect
def task_prerun(**args):
    try:
        task = args.get('task')
        task.get_session()
        operation.transaction = None
        TaskResult().task_pending(str(task.request.id))
        task.get_session(reopen=True)
        TaskResult().task_prerun(**args)
    except:
        raise
    finally:
        task.release_session()


@task_postrun.connect
def task_postrun(**args):
    try:
        task = args.get('task')
        task.get_session()
        operation.transaction = None
        TaskResult().task_postrun(**args)
    except:
        raise
    finally:
        task.release_session()


@task_failure.connect
def task_failure(**args):
    try:
        task = args.get('task')
        task.get_session()
        operation.transaction = None
        TaskResult().task_failure(**args)
    except:
        raise
    finally:
        task.release_session()
