# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte
from __future__ import annotations
import collections

from beecell.db.manager import RedisManager

try:
    import collections.Callable
except ImportError:
    collections.Callable = collections.abc.Callable  # compatibility fix for python >= 3.10

from copy import deepcopy
from functools import wraps
from typing import Any, Callable, List, Dict, Union
from uuid import uuid4

import ujson as json
from logging import getLogger
from billiard.exceptions import TimeLimitExceeded, WorkerLostError, Terminated
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from beecell.types.type_class import dynamic_import
from beecell.types.type_string import truncate
from beecell.password import obscure_data
from beecell.simple import import_func
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import operation
from beehive.common.audit import Audit, initAudit, localAudit
from beehive.common.task_v2.canvas import signature
from beehive.common.task_v2.handler import TaskResult
from celery.utils.saferepr import saferepr
from celery.app.amqp import AMQP
from beecell.simple import jsonDumps

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beehive.common.apimanager import ApiObject

logger = getLogger(__name__)


class TaskError(Exception):
    def __init__(self, value, *arg, **kw):
        self.value = value
        super(Exception, self).__init__(self.value, *arg, **kw)

    def __repr__(self):
        return "TaskError: %s" % self.value

    def __str__(self):
        return "%s" % self.value


class RunTaskError(Exception):
    def __init__(self, value, *arg, **kw):
        self.value = value
        super(Exception, self).__init__(self.value, *arg, **kw)

    def __repr__(self):
        return "RunTaskError: %s" % self.value

    def __str__(self):
        return self.value


# class BaseTaskRequest(Request):
#     def on_timeout(self, soft, timeout):
#         super(BaseTaskRequest, self).on_timeout(soft, timeout)
#         if not soft:
#            logger.warning(
#                'A hard timeout was enforced for task %s',
#                self.task.name
#            )
#         if soft:
#             self.task.task_result.task_failure(self, 'Soft time limit exceeded')
#             self.task.failure({}, 'Soft time limit exceeded')
#             raise TaskError('Soft time limit exceeded')
#         except TimeLimitExceeded:
#             self.task_result.task_failure(self, 'Time limit exceeded')
#             self.failure(params, 'Time limit exceeded')
#             raise TaskError('Time limit exceeded')


class BaseTask(Task):
    """Base beehive celery task class

    :param args: positional arg
    :param kwargs: key value arg
    """

    abstract = True
    inner_type = "TASK"
    prefix = "celery-task-shared-"
    prefix_stack = "celery-task-stack-"
    expire = 3600
    entity_class = None
    controller = None
    _redis = None
    _data: dict = None

    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)

        self.name = self.__class__.__module__ + "." + self.name

        self.logger = logger
        self.steps = []
        self.task_result = TaskResult(self)
        self.audit: Audit = None

        self.objid = None
        self.objtype = None
        self.objdef = None
        self.op = None
        self.opid = None
        self.delta = None
        self.user = None
        self.api_id = None
        self.current_step_id = None
        self.current_step_name = None

        if self.entity_class is not None:
            self.objtype = self.entity_class.objtype
            self.objdef = self.entity_class.objdef

    @property
    def redis(self):
        if self._redis is None:
            self._redis = self.app.api_manager.redis_taskmanager.conn
        return self._redis

    def set_data(self, key: str, value: Any):
        """
        set local data as opposed to set_shared_data
        """
        if self._data is None:
            self._data = {}
        self._data[key] = value

    def get_data(self, key: str, defaultvalue: Any = None) -> Any:
        """
        get local data as opposed to get_shared_data
        """
        if self._data is None:
            return None
        return self._data.get(key, defaultvalue)

    #
    # stdout
    #
    def get_key_stdout(self):
        return self.prefix + self.api_id + "stdout"

    def set_stdout_data(self, data):
        """Set stdout to shared memory area. Use this to pass stdout from different tasks/steps.

        :param task_id: task id
        :param data: data to store
        :return: True
        """
        val = jsonDumps(data)
        redisManager: RedisManager = self.redis
        redisManager.setex(self.get_key_stdout(), self.expire, val)
        return True

    def get_stdout_data(self):
        """Get stdout from shared memory area.

        :return: stdout
        """
        val = self.redis.get(self.get_key_stdout())
        if val is not None:
            data = json.loads(val)
        else:
            data = {}
        return data

    def remove_stdout_data(self):
        """Remove stdout from shared memory area reference from redis"""
        redisManager: RedisManager = self.redis
        redisManager.delete_key(self.get_key_stdout())

    #
    # shared area
    #
    def get_shared_data(self, task_id=None):
        """Get data from shared memory area. Use this to pass data from different tasks. Shared area could not ensure
        synchronization.

        :param task_id: task id
        :return: shared data
        """
        if task_id is None:
            task_id = self.request.id

        val = self.redis.get(self.prefix + self.api_id)
        if val is not None:
            data = json.loads(val)
        else:
            data = {}
        return data

    def set_shared_data(self, data, task_id=None):
        """Set data to shared memory area. Use this to pass data from different tasks. Shared area could not ensure
        synchronization.

        :param task_id: task id
        :param data: data to store
        :return: True
        """
        # if task_id is None:
        #     task_id = self.request.id

        # get actual data
        # current_data = self.get_shared_data()
        # current_data.update(data)
        val = jsonDumps(data)
        self.redis.setex(self.prefix + self.api_id, self.expire, val)
        return True

    def remove_shared_area(self, task_id=None):
        """Remove shared memory area reference from redis

        :param task_id: task id
        :return: shared data
        """
        if task_id is None:
            task_id = self.request.id

        keys = self.redis.keys(self.prefix + task_id)
        res = self.redis.delete(*keys)
        return res

    #
    # shared stack area
    #
    def pop_stack_data(self, task_id=None):
        """Pop item from shared memory stack. Use this to pass data from different tasks that must ensure
        synchronization.

        :param task_id: task id
        :return: stack data
        """
        if task_id is None:
            task_id = self.request.id

        data = None
        val = self.redis.lpop(self.prefix_stack + task_id)
        if val is not None:
            data = json.loads(val)
        logger.debug("Pop stack data for job %s: %s" % (task_id, truncate(data)))
        return data

    def push_stack_data(self, data, task_id=None):
        """Set data to shared memory stack. Use this to pass data from different tasks that must ensure synchronization.

        :param task_id: task id
        :param data: stack data
        :return: True
        """
        if task_id is None:
            task_id = self.request.id

        val = jsonDumps(data)
        self.redis.lpush(self.prefix_stack + task_id, val)
        logger.debug("Push stack data for job %s: %s" % (task_id, truncate(data)))
        return True

    def remove_stack(self, task_id=None):
        """Remove shared memory stack reference from redis

        :param task_id: task id
        :return: stack data
        """
        if task_id is None:
            task_id = self.request.id

        keys = self.redis.keys(self.prefix_stack + task_id)
        res = self.redis.delete(*keys)
        return res

    #
    # db session
    #
    def get_session(self, reopen=False):
        """Open a new sqlalchemy session

        :param reopen: if True close first the previous session
        """
        if reopen is True:
            self.app.api_manager.release_session()
        self.app.api_manager.get_session()

    def flush_session(self):
        """Flush the current sqlalchemy session"""
        self.app.api_manager.flush_session()

    def release_session(self):
        """Release the current sqlalchemy session"""
        self.app.api_manager.release_session()

    # def after_return(self, *args, **kwargs):
    #     """Handler called after the task returns.
    #     """
    #     super(BaseTask, self).after_return(*args, **kwargs)
    #     self.release_session()

    def _setup(self, params):
        """Setup the task context

        :param dict params: task params
        """
        operation.authorize = False

        printed_params = deepcopy(params)
        self.logger.debug("get input params: %s" % obscure_data(printed_params))
        if isinstance(params, dict):
            sync = params.get("sync", False)
        else:
            sync = False

        if sync is True:
            # self.request.id = self.request['kwargs'].pop('task_id')
            self.request.update(id=self.request.kwargs.pop("task_id"))
            self.parent = params.pop("parent_task")
            self.hostname = params.pop("hostname")
            self.argsrepr = jsonDumps(self.request.args)
            # self.argsrepr = saferepr(self.request.args, AMQP.argsrepr_maxsize)
            self.kwargsrepr = saferepr(self.request.kwargs, AMQP.kwargsrepr_maxsize)
        else:
            self.parent = None
            self.hostname = self.request.hostname
            self.argsrepr = jsonDumps(self.request.args)
            # self.argsrepr = self.request.argsrepr
            if hasattr(self.request, "kwargsrepr"):
                self.kwargsrepr = self.request.kwargsrepr
            else:
                self.kwargsrepr = ""

        # setup correct user
        try:
            user = params.pop("user", "task_manager")
            server = params.pop("server", "localhost")
            identity = params.pop("identity", "")
            api_id = params.pop("api_id", "")
        except Exception:
            self.logger.warning("Can not get request user", exc_info=True)
            user = "task_manager"
            server = "localhost"
            identity = ""
            api_id = ""

        if sync is False:
            operation.perms = []
            operation.user = (user, server, identity)
            operation.id = api_id
            operation.session = None
            operation.transaction = None
            operation.authorize = False
            operation.cache = False
            operation.encryption_key = self.app.api_manager.app_fernet_key

        if self.entity_class is not None and self.entity_class.module is not None:
            mod = self.app.api_manager.modules[self.entity_class.module]
            self.controller = mod.get_controller()

        self.objid = params.get("objid", None)
        self.op = self.name
        self.opid = self.request.id
        self.delta = 2
        self.user = user
        self.api_id = api_id

        self.logger.debug("completed params setup")
        try:
            self.audit = initAudit(
                objdef=self.objdef,
                objid=self.objid,
                api_method=self.name,
                req_method="task",
                request_id=api_id,
                user=user,
                subsystem=self.app.api_manager.app_subsytem,
            )
        except Exception as ex:
            logger.error(ex)
        return params

    def progress(self, step_id=None, msg=None):
        """Update progress task step status

        :param step_id: step id
        :param msg: progress message
        """
        if step_id is None and self.current_step_id is not None:
            step_id = self.current_step_id
        self.task_result.step_progress(self.request.id, step_id, msg=msg)

    def failure(self, params, error):
        self.audit.state = 500
        self.audit.send_audit(self.app.api_manager.elasticsearch, error=error, data=params)
        pass

    #
    # api call
    #
    def invoke_api(self, subsystem, uri, method, data=""):
        try:
            if self.controller.api_client is not None:
                res = self.controller.api_client.admin_request(subsystem, uri, method, data=data)
                return res
            else:
                self.logger.warning("Api client is not configured")
                return None
        except ApiManagerError as ex:
            raise TaskError(ex.value)

    def wait_task(self, subsystem, prefix, taskid, timeout=60, delta=3, maxtime=600, trace=None):
        try:
            if self.controller.api_client is not None:
                self.controller.api_client.admin_wait_task(
                    subsystem,
                    prefix,
                    taskid,
                    timeout=timeout,
                    delta=delta,
                    maxtime=maxtime,
                    trace=trace,
                )
            else:
                self.logger.warning("Api client is not configured")
        except ApiManagerError as ex:
            raise TaskError(ex.value)

    #
    # basic task step
    #
    def start_step(self):
        """Start step"""
        step_id = self.task_result.step_add(self.request.id, "start_step")
        self.task_result.step_success(self.request.id, step_id, None)

    def end_step(self):
        """End step"""
        step_id = self.task_result.step_add(self.request.id, "end_step")
        self.task_result.step_success(self.request.id, step_id, None)

    #
    # task run
    #
    def __import_step(self, step):
        components = step.split(".")
        self.logger.debug("import step %s" % step)
        # step passed as function
        try:
            mod = __import__(".".join(components[:-1]), globals(), locals(), [components[-1]], 0)
            step_func = getattr(mod, components[-1], None)

        # step passed as class method
        except Exception:
            mod = __import__(".".join(components[:-2]), globals(), locals(), [components[-2]], 0)
            step_class = getattr(mod, components[-2], None)
            step_func = getattr(step_class, components[-1], None)

        return step_func

    def run(self, params, *args, **kvargs):
        """The body of the task executed by workers.

        :param dict params: task params
        :return: task result
        """
        res = True

        # pre setup
        params = self._setup(params)

        # get sync
        sync = params.get("sync", False)

        # open database session
        if sync is False:
            self.get_session()

        try:
            self.task_result.task_start(self)

            # run start step
            self.start_step()

            # run workflow steps
            for step in self.steps:
                if isinstance(step, str):
                    step = import_func(step)

                if not isinstance(step, collections.Callable):
                    raise TaskError("step is not a callable function")

                res, params = step(self, None, params)

                # set result of the executed step in the params of the following step
                params["last_step_response"] = res

            # run optional steps
            steps = params.pop("steps", [])
            # self.logger.debug("+++++ run - steps: %s" % steps)
            for step in steps:
                if isinstance(step, dict):
                    # logger.debug('+++++ run dict - step[step]: %s' % step['step'])
                    step_func = self.__import_step(step["step"])

                    # logger.debug('+++++ run dict - BEFORE - step_func: %s' % step_func)
                    res, params = step_func(self, None, params, *step["args"])
                    # logger.debug('+++++ run dict - AFTER - step_func: %s' % step_func)
                else:
                    # logger.debug('+++++ run else - __import_step - step: %s' % step)
                    step_func = self.__import_step(step)
                    # logger.debug('+++++ run else - BEFORE - step_func: %s' % step_func)
                    res, params = step_func(self, None, params)
                    # logger.debug('+++++ run else - AFTER - step_func: %s' % step_func)

                # set result of the executed step in the params of the following step
                params["last_step_response"] = res

            # run optional custom_run
            custom_run = getattr(self, "custom_run", None)
            if custom_run is not None:
                res, params = custom_run(params)

            # run end step
            self.audit.state = 200
            self.audit.send_audit(self.app.api_manager.elasticsearch, data=params)

            self.task_result.task_success(self, str(res))
        except SoftTimeLimitExceeded:
            self.task_result.task_failure(self, "Soft time limit exceeded")
            self.failure(params, "Soft time limit exceeded")
            raise TaskError("Soft time limit exceeded")
        except TimeLimitExceeded:
            self.task_result.task_failure(self, "Time limit exceeded")
            self.failure(params, "Time limit exceeded")
            raise TaskError("Time limit exceeded")
        except WorkerLostError:
            self.task_result.task_failure(self, "The worker processing a job has exited prematurely")
            self.failure(params, "The worker processing a job has exited prematurely")
            raise TaskError("The worker processing a job has exited prematurely")
        except Terminated:
            self.task_result.task_failure(self, "The worker processing a job has been terminated by user request")
            self.failure(
                params,
                "The worker processing a job has been terminated by user request",
            )
            raise TaskError("The worker processing a job has been terminated by user request")
        except ApiManagerError as err:
            self.task_result.task_failure(self, str(err.value))
            self.failure(params, str(err.value))
            raise TaskError(str(err.value))
        except TaskError as err:
            self.task_result.task_failure(self, str(err.value))
            self.failure(params, str(err.value))
            raise
        except Exception as err:
            # self.logger.error(err, exc_info=True)
            msg = str(err)
            self.task_result.task_failure(self, msg)
            self.failure(params, msg)
            raise TaskError(msg)
        finally:
            if sync is False:
                self.release_session()
        return res


def task_step():
    """Use this decorator to log a new task step

    Example::

        @task_step()
        def fn(task, step_id, params, *args, **kwargs):
            ....
            return res, params
    """

    def wrapper(fn):
        @wraps(fn)
        def decorated(task, dummystep_id, params, *args, **kwargs):
            step_id = task.task_result.step_add(task.request.id, fn.__name__)
            task.progress(step_id, msg="get params: %s" % params)
            try:
                task.current_step_id = step_id
                task.current_step_name = fn.__name__
                # logger.debug("+++++ decorated - task.current_step_id: %s" % (task.current_step_id))
                # logger.debug("+++++ decorated - task.current_step_name: %s" % (task.current_step_name))
                res, params = fn(task, step_id, params, *args, **kwargs)
            except SoftTimeLimitExceeded:
                task.task_result.step_failure(task.request.id, step_id, "Soft time limit exceeded")
                raise
            except TaskError as ex:
                task.task_result.step_failure(task.request.id, step_id, str(ex))
                raise
            except Exception as ex:
                task.task_result.step_failure(task.request.id, step_id, str(ex))
                raise
            task.task_result.step_success(task.request.id, step_id, res)

            return res, params

        return decorated

    return wrapper


def create_task_class(TaskClass, fn, task_entity_class, task_alias):
    class InternalTask(TaskClass):
        name = task_alias
        entity_class = task_entity_class

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.steps = [InternalTask.main_step]

        @staticmethod
        @task_step()
        def main_step(task, step_id, params, *args, **kvargs):
            """internal step used to run async method.

            :param task: parent celery task
            :param str step_id: step id
            :param dict params: step params
            :return: res, params
            """
            entity_id = params.get("entity_id", None)
            entity = task.controller.get_entity_for_task(task.entity_class, entity_id)
            res = fn(entity, params)
            task.progress(step_id, msg="run async method %s: %s" % (fn.__name__, res))
            return res, params

    name = "".join(t.capitalize() for t in task_alias.split("_"))
    task_class_name = "%s%s" % (task_entity_class.__name__, name)
    logger.warn(task_class_name)
    InternalTaskClass = type(task_class_name, (InternalTask,), {"__module__": task_entity_class.__module__})

    return InternalTaskClass


def run_async(action="use", TaskClass=BaseTask, alias=None):
    """Use this decorator to transform a class method in static and run ad celery task

    Example::

        @run_async(action='use')
        def fn(task, step_id, params, *args, **kwargs):
            ....
            return res, params
    """

    def wrapper(fn):
        @wraps(fn)
        def run_async_decorated(*args, **kwargs):
            register = kwargs.pop("register", False)
            sync = kwargs.pop("sync", False)
            task_entity_class = kwargs.pop("entity_class", None)
            task_alias = alias if alias is not None else fn.__name__

            args = list(args)
            # sync = False
            # if len(args) > 1:
            #     sync = args[1].pop('sync', False)

            logger.debug("##### run_async args: %s" % args)
            logger.debug("##### run_async kwargs: %s" % kwargs)
            logger.debug("##### run_async register: %s" % register)
            logger.debug("##### run_async task_entity_class: %s" % task_entity_class)
            logger.debug("##### run_async task_alias: %s" % task_alias)
            logger.debug("##### run_async sync status: %s" % sync)

            # register task in celery
            if register is True:
                from beehive.common.task_v2.manager import task_manager

                # module = __import__(task_entity_class.__module__)
                # import sys
                # module = sys.modules[task_entity_class.__module__]
                # # module = dynamic_import(task_entity_class.__module__)
                # logger.warn(module)
                # task_class_name = '%sTask%s' % (task_entity_class.__name__, fn.__name__)
                # logger.warn(task_class_name)
                # setattr(module, task_class_name, create_task_class(TaskClass, fn, task_entity_class))
                InternalTaskClass = create_task_class(TaskClass, fn, task_entity_class, task_alias)
                task_manager.tasks.register(InternalTaskClass())

            # run method as sync
            elif sync is True:
                logger.debug("########## start sync %s" % fn.__name__)
                # args = list(args)
                inst = args.pop(0)
                params = args.pop(0)
                params["sync"] = True
                res = fn(inst, params)
                logger.debug("run sync method %s: %s" % (fn.__name__, res))
                logger.debug("########## end sync %s" % fn.__name__)
                return res

            # send task request to celery
            else:
                # args = list(args)
                inst = args.pop(0)
                params = {}
                if len(args) > 0:
                    params = args.pop(0)
                controller = inst.controller

                # verify permissions
                objid = inst.objid
                if action == "insert":
                    objid = "//".join(inst.objid.split("//")[0:-1])
                controller.check_authorization(inst.objtype, inst.objdef, objid, action)

                params.update(inst.get_user())
                params["objid"] = str(uuid4())
                params["alias"] = task_alias
                params["entity_id"] = inst.oid
                task_name = "%s.%s" % (inst.__class__.__module__, task_alias)
                # task_name = 'beehive.common.task_v2.%s' % fn.__name__
                task = signature(
                    task_name,
                    [params],
                    app=inst.task_manager,
                    queue=inst.celery_broker_queue,
                )
                task_obj = task.apply_async()
                return {"taskid": task_obj.id}, 201

        return run_async_decorated

    return wrapper


def prepare_or_run_task(entity: ApiObject, task: str, params: dict, sync=False):
    """Prepare a task using a simple function or run an async task using a celery task

    :param entity: ApiObject instance that run task
    :param task: name of task to run. Name must contain the full python path
    :param params: task params
    :param sync: if True run a sync task
    :return:
    """
    params["sync"] = sync
    # logger.info("+++++ prepare_or_run_task - sync: %s" % sync)
    if sync is True:
        user = {
            "user": operation.user[0],
            "server": operation.user[1],
            "identity": operation.user[2],
            "api_id": operation.id,
        }
        new_params = deepcopy(params)
        new_params.update(user)
        task = signature(task, [], app=entity.task_manager)
        return {"task": task, "uuid": entity.uuid, "params": new_params}, 200
    else:
        # logger.info("+++++ prepare_or_run_task - task: %s" % task)
        task = signature(task, [params], app=entity.task_manager, queue=entity.celery_broker_queue)
        task = task.apply_async()
        logger.info("run async task %s" % task.id)
        return {"taskid": task.id, "uuid": entity.uuid}, 202


def run_sync_task(prepared_sync_task, parent_task: BaseTask, parent_step: str, custom_task_id: str = None):
    """Run a sync task using a simple function

    :param prepared_sync_task: result from prepare_or_run_task
    :param parent_task: parent task instance
    :param parent_step: parent step
    :param custom_task_id: str(uuid4()) or None. used when you want a custom id for the new task

    :return:
    """
    logger.info("start sync task %s" % prepared_sync_task["task"])
    prepared_sync_task["params"]["hostname"] = parent_task.hostname
    prepared_sync_task["params"]["parent_task"] = parent_task.request.id + ":" + parent_step
    prepared_sync_task["params"]["user"] = operation.user[0]
    prepared_sync_task["params"]["server"] = operation.user[1]
    prepared_sync_task["params"]["identity"] = operation.user[2]
    prepared_sync_task["params"]["api_id"] = operation.id
    prepared_sync_task["params"]["objid"] = parent_task.objid
    # res = prepared_sync_task['task'].type(prepared_sync_task['params'])
    res = prepared_sync_task["task"].apply(task_id=custom_task_id, args=[prepared_sync_task["params"]], throw=True)
    logger.info("complete sync task %s : %s " % (prepared_sync_task["task"], res))
    return res.result
