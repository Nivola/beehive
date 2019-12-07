# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import collections
from functools import wraps
import ujson as json
from logging import getLogger
from celery import Task
from beecell.simple import truncate, import_func
from beehive.common.data import operation
from beehive.common.task_v2.handler import TaskResult

logger = getLogger(__name__)


class TaskError(Exception):
    def __init__(self, value):
        self.value = value
        Exception.__init__(self, value)

    def __repr__(self):
        return 'TaskError: %s' % self.value

    def __str__(self):
        return self.value


class RunTaskError(Exception):
    def __init__(self, value):
        self.value = value
        Exception.__init__(self, value)

    def __repr__(self):
        return 'RunTaskError: %s' % self.value

    def __str__(self):
        return self.value


class BaseTask(Task):
    abstract = True
    inner_type = 'TASK'
    prefix = 'celery-task-shared-'
    prefix_stack = 'celery-task-stack-'
    expire = 3600
    entity_class = None
    controller = None

    _redis = None

    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)

        self.name = self.__class__.__module__ + '.' + self.name

        self.logger = logger
        self.steps = []
        self.task_result = TaskResult()

        self.objid = None
        self.objtype = None
        self.objdef = None
        self.op = None
        self.opid = None
        self.delta = None
        self.user = None
        self.api_id = None

        if self.entity_class is not None:
            self.objtype = self.entity_class.objtype
            self.objdef = self.entity_class.objdef

    @property
    def redis(self):
        if self._redis is None:
            self._redis = self.app.api_manager.redis_taskmanager.conn
        return self._redis

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

        val = self.redis.get(self.prefix + task_id)
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
        if task_id is None:
            task_id = self.request.id

        # get actual data
        current_data = self.get_shared_data()
        current_data.update(data)
        val = json.dumps(current_data)
        self.redis.setex(self.prefix + task_id, self.expire, val)
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
        logger.debug('Pop stack data for job %s: %s' % (task_id, truncate(data)))
        return data

    def push_stack_data(self, data, task_id=None):
        """Set data to shared memory stack. Use this to pass data from different tasks that must ensure synchronization.

        :param task_id: task id
        :param data: stack data
        :return: True
        """
        if task_id is None:
            task_id = self.request.id

        val = json.dumps(data)
        self.redis.lpush(self.prefix_stack + task_id, val)
        logger.debug('Push stack data for job %s: %s' % (task_id, truncate(data)))
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

    def after_return(self, *args, **kwargs):
        """Handler called after the task returns.
        """
        super(BaseTask, self).after_return(*args, **kwargs)
        self.release_session()

    def _setup(self, params):
        """Setup the task context

        :param dict params: task params
        """
        # setup correct user
        try:
            user = params.pop('user', 'task_manager')
            server = params.pop('server', 'localhost')
            identity = params.pop('identity', '')
            api_id = params.pop('api_id', '')
        except Exception:
            self.logger.warning('Can not get request user', exc_info=1)
            user = 'task_manager'
            server = 'localhost'
            identity = ''
            api_id = ''

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

        self.objid = params.pop('objid', None)
        self.op = self.name
        self.opid = self.request.id
        self.delta = 2
        self.user = operation.user
        self.api_id = params.pop('api_id', None)

    def progress(self, step_id, msg=None):
        logger.debug(msg)
        self.task_result.step_progress(self.request.id, step_id, msg=msg)

    #
    # basic task step
    #
    def start_step(self):
        step_id = self.task_result.step_add(self.request.id, 'start_step')
        self.task_result.step_success(self.request.id, step_id, None)

    def end_step(self):
        step_id = self.task_result.step_add(self.request.id, 'end_step')
        self.task_result.step_success(self.request.id, step_id, None)

    #
    # task run
    #
    def run(self, params):
        """The body of the task executed by workers.

        :param dict params: task params
        :param list params.steps: custom task steps. Step can be a python function or a string with the complete path
            of the function
        :return:

        :step: signature example

            def <step_name>(task, params):
                ....
        """
        res = True

        # pre setup
        self._setup(params)

        # open database session
        self.get_session()

        try:
            self.task_result.task_start(self)

            # run start step
            self.start_step()
            # self.task_result.task_update(self.request.id, objid=self.objid)

            # run optional steps
            for step in self.steps:
                if isinstance(step, str):
                    step = import_func(step)

                if not isinstance(step, collections.Callable):
                    raise TaskError('step is not a callable function')

                # step_id = self.task_result.step_add(self.request.id, step.__name__)
                # try:
                #     res = step(self, step_id, params)
                # except Exception as ex:
                #     self.task_result.step_failure(self.request.id, step_id, str(ex))
                #     raise
                # self.task_result.step_success(self.request.id, step_id, res)

                res = step(self, None, params)

            # run optional custom_run
            custom_run = getattr(self, 'custom_run', None)
            if custom_run:
                res = custom_run(params)

            # run end step
            self.end_step()

            self.task_result.task_success(self, str(res))
        except Exception as err:
            self.logger.error(err, exc_info=1)
            self.task_result.task_failure(self, str(err))
            raise
        finally:
            self.release_session()

        return res


def task_step():
    """Use this decorator to log a new task step

    Example::

        @task_step()
        def fn(task, step_id, params, *args, **kwargs):
            ....
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated(task, step_id, params, *args, **kwargs):
            step_id = task.task_result.step_add(task.request.id, fn.__name__)
            try:
                res = fn(task, step_id, params, *args, **kwargs)
            except Exception as ex:
                task.task_result.step_failure(task.request.id, step_id, str(ex))
                raise
            task.task_result.step_success(task.request.id, step_id, res)

            return res
        return decorated
    return wrapper
