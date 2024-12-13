# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import ApiObject
from beehive.common.data import transaction, operation, query
from beehive.common.model import (
    SchedulerTask,
    SchedulerState,
    AbstractDbManager,
    SchedulerTrace,
    SchedulerStep,
)
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from celery.signals import task_prerun


logger = get_task_logger(__name__)


class TaskResult(object):
    """Utility class used to manage task, step and trace in database"""

    def __init__(self, task):
        self.manager = AbstractDbManager()

        self.task = task

        self.stop_time = 0
        self.start_time = 0

    def elapsed(self):
        if isinstance(self.start_time, datetime) and isinstance(self.stop_time, datetime):
            return round(
                (self.stop_time - self.start_time) / timedelta(microseconds=1) / 1000000,
                3,
            )
        return 0

    def send_event(self, op, status, elapsed, ex=None):
        """Send event

        :param status: jobtask status
        :param ex: exception raised [optional]
        :param elapsed: elapsed time
        :param result: task result. None otherwise task status is SUCCESS [optional]
        :param msg: update message [optional]
        """
        response = [status, ""]
        if ex is not None:
            response = [status, str(ex)]

        action = self.task.op.split(".")[-1]

        entity_class = self.task.entity_class
        data = {
            "opid": self.task.opid,
            "op": op,
            "api_id": self.task.api_id,
            "args": [],
            "kwargs": "",  # self.task.request.args,
            "response": response,
            "elapsed": elapsed,
        }

        source = {
            "user": operation.user[0],
            "ip": operation.user[1],
            "identity": operation.user[2],
        }

        dest = {
            "ip": self.task.controller.module.api_manager.server_name,
            "port": self.task.controller.module.api_manager.http_socket,
            "pod": self.task.controller.module.api_manager.app_k8s_pod,
            "objid": self.task.objid,
            "objtype": entity_class.objtype,
            "objdef": entity_class.objdef,
            "action": action,
        }

        # send event
        try:
            client = self.task.controller.module.api_manager.event_producer
            client.send(ApiObject.ASYNC_OPERATION, data, source, dest)
        except Exception as ex:
            logger.warning("Event can not be published. Event producer is not configured - %s" % ex)

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
        # logger.debug2('add new db task trace %s record' % entity)

    @transaction
    def step_add(self, task_id, name):
        """Add a step

        :param task_id: task id
        :param name: step name
        :return:
        """
        entity = self.manager.add_entity(SchedulerStep, task_id, name)
        logger.debug2("add new db task step %s record" % entity)
        logger.info("add new step %s.%s" % (name, entity.uuid))
        self.trace_add(task_id, entity.uuid, "start step", "INFO")
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
        step = self.manager.get_entity(SchedulerStep, step_id)

        entity = self.manager.update_entity(SchedulerStep, uuid=step_id, run_time=run_time)
        logger.debug2("update task step %s record" % entity)

        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, run_time=run_time)
        logger.debug2("update db task %s record" % entity)

        logger.info("step %s.%s progress: %s" % (step.name, step_id, msg))

        if msg is not None:
            self.trace_add(task_id, step_id, msg, "INFO")

    @transaction
    def step_success(self, task_id, step_id, result):
        """Update a step with success

        :param task_id: task id
        :param step_id: step id
        :param result: step result
        :return:
        """
        stop_time = datetime.today()
        self.stop_time = stop_time
        entity = self.manager.get_entity(SchedulerStep, step_id)
        entity_id = self.manager.update_entity(
            SchedulerStep,
            uuid=step_id,
            status=SchedulerState.SUCCESS,
            result=result,
            stop_time=stop_time,
            run_time=stop_time,
        )
        logger.debug2("update task step %s record" % entity_id)
        logger.info("step %s.%s success" % (entity.name, step_id))
        self.trace_add(task_id, step_id, "end step with result: %s" % result, "INFO")
        step_name = entity.name
        self.send_event(step_name, "STEP", self.elapsed(), ex=None)

    @transaction
    def step_failure(self, task_id, step_id, error):
        """Update a step with failure

        :param task_id: task id
        :param step_id: step id
        :param error: step error
        :return:
        """
        stop_time = datetime.today()
        self.stop_time = stop_time
        entity = self.manager.get_entity(SchedulerStep, step_id)
        entity_id = self.manager.update_entity(
            SchedulerStep,
            uuid=step_id,
            status=SchedulerState.FAILURE,
            stop_time=stop_time,
            result=False,
        )
        logger.debug2("update task step %s record" % entity_id)
        logger.error("step %s.%s error: %s" % (entity.name, step_id, error), exc_info=True)
        self.trace_add(task_id, step_id, "step error: %s" % error, "ERROR")
        step_name = entity.name
        self.send_event(step_name, "STEP", self.elapsed(), ex=error)

    @query
    def task_exists(self, task_id):
        """Check task exists

        :param task_id: task id
        :return:
        """
        entity = self.manager.exist_entity(SchedulerTask, task_id)
        if entity is True:
            logger.warning("task %s already exists" % task_id)
            return True
        return False
        # raise Exception('task %s already exists' % task_id)

    @transaction
    def task_prerun(self, **args):
        """Dispatched when a task pre run.

        :param args.task: celery task
        :param args.task_id: celery task id
        """
        task = args.get("task")
        task_id = args.get("task_id")

        start_time = datetime.today()
        self.start_time = start_time

        exists = self.task_exists(task_id)

        # create task in pending state
        if exists is False:
            status = SchedulerState.PENDING
            entity = self.manager.add_entity(SchedulerTask, task_id, task.name, status, start_time)
            logger.debug2("add new db task %s record" % entity)
            logger.info("send new task")
        # update already created task
        else:
            status = SchedulerState.PENDING
            entity = self.manager.update_entity(
                SchedulerTask,
                uuid=task_id,
                name=task.name,
                status=status,
                start_time=start_time,
            )
            logger.debug2("update db task %s record" % entity)

    @transaction
    def task_start(self, task):
        """Dispatched when a task start.

        :param task: celery task
        """
        task_id = task.request.id
        vargs = task.argsrepr
        kwargs = task.kwargsrepr
        entity = self.manager.get_entity(SchedulerTask, task_id)
        if entity.status != SchedulerState.PENDING:
            raise Exception("task %s is not in PENDING status" % task_id)

        self.start_time = entity.start_time

        # update task in pending state
        status = SchedulerState.STARTED
        entity = self.manager.update_entity(
            SchedulerTask,
            uuid=task_id,
            name=task.name,
            worker=task.hostname,
            objid=task.objid,
            objtype=task.objtype,
            objdef=task.objdef,
            args=vargs,
            kwargs=kwargs,
            status=status,
            api_id=task.api_id,
            parent=task.parent,
        )
        logger.debug2("update db task %s record" % entity)
        logger.info("start task")
        self.trace_add(task_id, None, "start task", "INFO")
        self.send_event(self.task.name, "STARTED", 0, ex=None)

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
        self.stop_time = stop_time

        # update task in pending state
        entity = self.manager.update_entity(
            SchedulerTask,
            uuid=task_id,
            stop_time=stop_time,
            run_time=stop_time,
            status=status,
            result=result,
        )
        logger.debug2("update db task %s record" % entity)
        logger.info("task finished")
        self.trace_add(task_id, None, "end task with result: %s" % result, "INFO")
        self.send_event(self.task.name, "SUCCESS", self.elapsed(), ex=None)

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
        # trace = traceback.format_exc()

        # get task stop_time
        stop_time = datetime.today()
        self.stop_time = stop_time

        # update task in pending state
        entity = self.manager.update_entity(
            SchedulerTask,
            uuid=task_id,
            stop_time=stop_time,
            run_time=stop_time,
            status=status,
            result=False,
        )
        logger.debug("update db task %s record" % entity)
        # logger.error('task failed: %s' % trace)

        # self.trace_add(task_id, None, trace, 'ERROR')
        self.send_event(self.task.name, "FAILURE", self.elapsed(), ex=err)

    @transaction
    def task_update(self, task_id, **args):
        """Update a task

        :param task_id: task id
        :param args: key value args
        :return:
        """
        entity = self.manager.update_entity(SchedulerTask, uuid=task_id, **args)
        logger.debug2("update db task %s record" % entity)

        self.trace_add(task_id, None, "update task", "INFO")


@task_prerun.connect
def task_prerun(**args):
    task = args.get("task")
    task_id = args.get("task_id")
    args["kwargs"]["task_id"] = task_id

    if getattr(task, "get_session", None):
        open_new_session = True
        if getattr(operation, "session", None) is not None:
            open_new_session = False
        if open_new_session is True:
            task.get_session()
        operation.transaction = None
        TaskResult(None).task_prerun(**args)
        if open_new_session is True:
            task.release_session()
