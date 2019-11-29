# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import ujson as json
from time import time
from beehive.common.task import BaseTask
from celery.utils.log import get_task_logger
from beehive.common.apimanager import ApiManagerError, ApiObject
from celery.result import AsyncResult, GroupResult
from beehive.common.data import operation
from beehive.common.task.manager import task_manager
from beecell.simple import get_value, import_class, nround, truncate
from celery import chord
from traceback import format_tb
from beehive.common.task.handler import TaskResult, task_local
from gevent import sleep
from functools import wraps
from traceback import format_exc
from billiard.einfo import ExceptionInfo

logger = get_task_logger(__name__)


class JobError(Exception):
    def __init__(self, value, code=0):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return "JobError: %s" % self.value

    def __str__(self):
        return self.value


class JobInvokeApiError(Exception):
    def __init__(self, value, code=0):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return "JobInvokeApiError: %s" % self.value

    def __str__(self):
        return self.value


class AbstractJob(BaseTask):
    abstract = True
    ops = []

    @property
    def controller(self):
        return task_local.controller

    #
    # permissions assignment
    #
    def get_operation_id(self, objdef):
        """
        """
        temp = objdef.split('.')
        ids = ['*' for i in temp]
        return '//'.join(ids)

    def set_operation(self):
        """
        """
        operation.perms = []
        for op in self.ops:
            perm = (
                1,
                1,
                op.objtype,
                op.objdef,
                self.get_operation_id(
                    op.objdef),
                1,
                '*')
            operation.perms.append(perm)
        logger.debug('Set permissions: %s' % operation.perms)

    #
    # shared area
    #
    def get_shared_data(self, job=None):
        """ """
        if job is None:
            job = task_local.opid
        data = BaseTask.get_shared_data(self, job)
        return data

    def set_shared_data(self, data, job=None):
        """ """
        if job is None:
            job = task_local.opid
        data = BaseTask.set_shared_data(self, job, data)
        return data

    def remove_shared_area(self):
        """ """
        return BaseTask.remove_shared_area(self, task_local.opid)

    #
    # shared stack area
    #
    def pop_stack_data(self):
        """Pop item from shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        return BaseTask.pop_stack_data(self, task_local.opid)

    def push_stack_data(self, data):
        """Set data to shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        return BaseTask.push_stack_data(self, task_local.opid, data)

    def remove_stack(self):
        """Remove shared memory stack reference from redis"""
        return BaseTask.remove_stack(self, task_local.opid)

    #
    # varius
    #
    def elapsed(self):
        elapsed = round(time() - task_local.start, 4)
        return elapsed

    def get_entity_class_name(self):
        return task_local.entity_class.__module__ + '.' + \
            task_local.entity_class.__name__

    def get_options(self):
        """Return tupla with some useful options.

        :return:  (class_name, objid, job, job id, start time, time before new query, user, api_id)
        """
        options = (self.get_entity_class_name(), task_local.objid, task_local.op, task_local.opid, None,
                   task_local.delta, task_local.user, task_local.api_id)
        return options

    #
    # task status management
    #
    def send_job_event(self, status, elapsed, ex=None, msg=None):
        """Send job update event

        :param status: jobtask status
        :param ex: exception raised [optional]
        :param elapsed: elapsed time
        :param result: task result. None otherwise task status is SUCCESS [optional]
        :param msg: update message [optional]
        """
        response = [status]
        if ex is not None:
            response.append(str(ex))

        action = task_local.op.split('.')[-1]

        op = '%s.%s' % (self.__module__, self.__name__)
        entity_class = task_local.entity_class
        data = {
            'api_id': task_local.api_id,
            'opid': task_local.opid,
            'op': '%s.%s' % (task_local.entity_class.objdef, op),
            'taskid': self.request.id,
            'task': self.name,
            'params': self.request.args,
            'response': response,
            'elapsed': elapsed,
            'msg': msg
        }

        source = {
            'user': operation.user[0],
            'ip': operation.user[1],
            'identity': operation.user[2]
        }

        dest = {
            'ip': task_local.controller.module.api_manager.server_name,
            'port': task_local.controller.module.api_manager.http_socket,
            'objid': task_local.objid,
            'objtype': entity_class.objtype,
            'objdef': entity_class.objdef,
            'action': action
        }

        # send event
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(ApiObject.ASYNC_OPERATION, data, source, dest)
        except Exception as ex:
            logger.warn('Event can not be published. Event producer is not configured - %s' % ex)

    def update_job(self, params=None, status=None, current_time=None, ex=None, traceback=None, result=None, msg=None,
                   start_time=None):
        """Update job status

        :param params: variables in shared area [optional]
        :param status: job current status [optional]
        :param start_time: job start time [optional]
        :param current_time: current time [optional]
        :param ex: exception raised [optional]
        :param traceback: exception trace [optional]
        :param result: task result. None otherwise task status is SUCCESS [optional]
        :param msg: update message [optional]
        """
        # get actual job
        job = TaskResult.get(task_local.opid)
        if job['status'] is not None and job['status'] == 'FAILURE':
            return None

        params = self.get_shared_data()
        # if job is finished exit to avoid wrong status change
        if params.get('is-finished', False) is True:
            return None

        if 'start-time' not in params.keys():
            params['start-time'] = job.get('start_time')
            self.set_shared_data(params)

        # if status == 'STARTED':
        #     params['start-time'] = time()
        #     self.set_shared_data(params)

        # set result if status is SUCCESS
        retval = None
        if status == 'SUCCESS':
            # set flag for SUCCESS job
            params['is-finished'] = True
            self.set_shared_data(params)

            if 'result' in params:
                retval = params['result']
            # remove shared area
            # self.remove_shared_area()

            # remove stack
            # self.remove_stack()

        # store job data
        msg = None
        counter = int(job.get('counter', 0)) + 1
        TaskResult.store(task_local.opid, status=status, retval=retval, inner_type='JOB', traceback=traceback,
                         stop_time=current_time, msg=msg, counter=counter)
        if status == 'FAILURE':
            logger.error('JOB %s status change to %s' % (task_local.opid, status))
        else:
            logger.info('JOB %s status change to %s' % (task_local.opid, status))


class Job(AbstractJob):
    abstract = True
    inner_type = 'JOB'

    def __init__(self, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)

    @staticmethod
    def create(tasks, *args, **kvargs):
        """Create celery signature with chord, group and chain

        :param tasks: list of celery task
        :return: celery signature
        """
        process = tasks.pop().signature(
            args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
        last_task = None
        for task in tasks:
            if not isinstance(task, list):
                item = task.signature(
                    args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                if last_task is not None:
                    item.link(last_task)
            elif isinstance(task, list) and len(task) > 0:
                item = chord(task, last_task)
            last_task = item
        process.link(last_task)
        return process

    @staticmethod
    def create_job(tasks, *args, **kvargs):
        """Create celery signature with chord, group and chain

        :param tasks: list of celery tasks. Task can be a celery task or a dict like
            {'task':<celery task>, 'args':..}
        :return: celery signature
        """
        tasks.reverse()
        process = tasks.pop().signature(
            args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
        last_task = None
        for task in tasks:
            if not isinstance(task, list):
                if isinstance(task, dict):
                    internal_args = list(args)
                    internal_args.extend(task.get('args'))
                    item = task.get('task').signature(internal_args, immutable=True,
                                                       queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                else:
                    item = task.signature(
                        args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                if last_task is not None:
                    item.link(last_task)
            elif isinstance(task, list) and len(task) > 0:
                subitems = []
                for subtask in task:
                    if isinstance(subtask, dict):
                        internal_args = list(args)
                        internal_args.extend(subtask.get('args'))
                        subitem = subtask.get('task').signature(internal_args, immutable=True,
                                                                 queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                    else:
                        subitem = subtask.get('task').signature(args, immutable=True,
                                                                 queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                    subitems.append(subitem)
                item = chord(subitems, last_task)
            last_task = item
        process.link(last_task)
        return process

    @staticmethod
    def start(inst, tasks, params):
        """Run job

        :param inst: celery task instance
        :param tasks: list of celery task to run. Task can be a celery task or a dict like
            {'task':<celery task>, 'args':..}
        :param params: list of celery task params
        :return: True
        """
        from beehive.common.task.util import end_task, start_task

        ops = inst.get_options()
        inst.set_shared_data(params)
        tasks.insert(0, start_task)
        tasks.append(end_task)
        logger.debug2('Workflow tasks: %s' % tasks)
        process = Job.create_job(tasks, ops)
        process.delay()
        return True

    #
    # handler
    #
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.

        Parameters:

            exc - The exception raised by the task.
            task_id - Unique id of the failed task.
            args - Original arguments for the task that failed.
            kwargs - Original keyword arguments for the task that failed.
            einfo - ExceptionInfo instance, containing the traceback.

        The return value of this handler is ignored.
        """
        err = exc
        BaseTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        trace = format_tb(einfo.tb)
        trace.append(err)
        logger.error('', exc_info=1)
        self.update_job(params={}, status='FAILURE', current_time=time(), ex=err, traceback=trace,
                        result=None, msg=err)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task is to be retried.

        Parameters:

            exc - The exception sent to retry().
            task_id - Unique id of the retried task.
            args - Original arguments for the retried task.
            kwargs - Original keyword arguments for the retried task.
            einfo - ExceptionInfo instance, containing the traceback.

        The return value of this handler is ignored.
        """
        self.update_job(status='FAILURE', current_time=time())


class JobTask(AbstractJob):
    abstract = True
    inner_type = 'JOBTASK'

    #
    # api
    #
    def api_admin_request(self, module, path, method,
                          data='', other_headers=None):
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.app.api_manager.api_client.admin_request(
            module, path, method, data, other_headers, silent=True)

    def api_user_request(self, module, path, method,
                         data='', other_headers=None):
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.app.api_manager.api_client.user_request(
            module, path, method, data, other_headers, silent=True)

    def _query_job(self, module, job_id, attempt):
        """Query remote job status.

        :param module: beehive module
        :param task_id: id of the remote job
        :return: job status. Possible value are: PENDING, PROGRESS, SUCCESS,
                 FAILURE
        """
        prefix = {
            'auth': 'nas',
            'service': 'nws',
            'resource': 'nrs',
            'event': 'nes'
        }

        try:
            uri = '/v1.0/%s/worker/tasks/%s' % (prefix[module], job_id)
            res = self.api_admin_request(
                module, uri, 'GET', '').get(
                'task_instance', {})
            logger.debug('Query job %s: %s' % (job_id, res['status']))
        except ApiManagerError as ex:
            # remote job query fails. Return fake state and wait new query
            res = {'state': 'PROGRESS'}
        return res, attempt

    def invoke_api(self, module, uri, method, data,
                   other_headers=None, link=None):
        """Invoke beehive api.

        :param module: cloudapi module
        :param uri: api uri
        :param method: api method
        :param data: api data
        :param other_headers: extra headers to pass request
        :param link: if not None define resource id to link with the new resource
        :return: api result
        :raise: ApiManagerError
        """
        res = self.api_admin_request(module, uri, method, data, other_headers)
        self.update('PROGRESS', msg='Invoke api %s [%s] in module %s' % (uri, method, module))

        if link is not None:
            # set up link from remote stack to instance
            self.release_session()
            self.get_session()
            resource = self.get_resource(link)
            resource.add_link(
                '%s-link' %
                res['uuid'],
                'relation',
                res['uuid'],
                attributes={})
            # self.release_session()
            self.update('PROGRESS', msg='Setup link between resource %s and resource %s' %
                                         (res['uuid'], resource.oid))
            # self.release_session()

        if method in ['POST', 'PUT', 'DELETE']:
            job_id = res['jobid']
            self.update('PROGRESS', msg='Invoke job %s' % job_id)

            status = 'PENDING'
            attempt = 1
            # after 6 attempt set status to FAILURE and block loop
            while status != 'SUCCESS' and status != 'FAILURE':
                sleep(task_local.delta)
                job = self._query_job(module, job_id, attempt)
                attempt = job[1]
                job = job[0]
                status = job['status']
                self.update('PROGRESS')

            self.update(
                status, msg='Job %s completed with %s' %
                (job_id, status))
            if status == 'FAILURE':
                try:
                    trace = job['traceback'][-1]
                except BaseException:
                    trace = 'Job %s was not found' % job_id
                err = 'Remote job %s error: %s' % (job_id, trace)
                trace = trace
                logger.error(err)
                raise JobInvokeApiError(trace)
            else:
                return job['result']
        else:
            return res

    #
    # invoke remote job
    #
    def wait_for_job_complete(self, task_id):
        """Query celery job and wait until status is not SUCCESS or FAILURE

        **Parameters**:

            * **task_id**: celery task id

        **Return**:

            task results
        """
        try:
            # append job to task jobs list
            self.update('PROGRESS', job=task_id)

            # get celery task
            inner_task = TaskResult.get(task_id)
            start = time()

            # loop until inner_task finish with success or error
            status = inner_task.get('status')
            start_counter = inner_task.get('counter', 0)
            while status != 'SUCCESS' and status != 'FAILURE':
                sleep(task_local.delta)
                inner_task = TaskResult.get(task_id)
                counter = inner_task.get('counter', 0)
                elapsed = time() - start
                # verify job is stalled
                if counter - start_counter == 0 and elapsed > 240:
                    raise JobError('Job %s is stalled' % task_id)

                self.update('PROGRESS', msg='Job %s status %s after %ss' % (task_id, status, elapsed))
                status = inner_task.get('status')

            elapsed = time() - start
            if status == 'FAILURE':
                err = inner_task.get('traceback')[-1]
                logger.error('Job %s error after %ss' % (task_id, elapsed))
                self.update('PROGRESS', msg='Job %s status %s after %ss' % (task_id, status, elapsed))
                raise JobError(err)
            elif status == 'SUCCESS':
                self.update('PROGRESS', msg='Job %s success after %ss' % (task_id, elapsed))
                res = inner_task
            else:
                logger.error('Job %s unknown error after %ss' % (task_id, elapsed))
                self.update('PROGRESS', msg='Job %s status %s after %ss' % (task_id, 'UNKNONWN', elapsed))
                raise JobError('Unknown error')

            return res
        except Exception as ex:
            logger.error(ex)
            raise

    #
    # task status management
    #
    def progress(self, msg):
        """Run a task update and log a message

        :param msg: message to log
        :return:
        """
        self.update('PROGRESS', msg=msg)

    def update(self, status, ex=None, traceback=None, result=None, msg=None, start_time=None, job=None):
        """Update job and jobtask status

        :param status: jobtask status
        :param ex: exception raised [optional]
        :param traceback: exception trace [optional]
        :param result: task result. None otherwise task status is SUCCESS [optional]
        :param msg: update message [optional]
        :param start_time: job task start time [optional]
        :param job: job id to add to tasks jobs list [optional]
        """
        # get variables from shared area
        params = self.get_shared_data()

        # get current time
        current_time = time()

        # log message
        if msg is not None:
            # msg = str(msg)
            if status == 'FAILURE':
                # logger.error(msg, exc_info=1)
                logger.error(msg)
                # msg = 'ERROR: %s' % msg
            else:
                logger.debug(truncate(msg))

        # update jobtask result
        task_id = self.request.id
        jobs = None
        if job is not None:
            jobs = [job]
        TaskResult.store(task_id, status=status, traceback=traceback, retval=result, msg=msg, stop_time=current_time,
                         start_time=start_time, inner_type='JOBTASK', jobs=jobs)

        # get job start time
        job_start_time = params.get('start-time', 0)

        # update job only if job_start_time is not 0. job_start_time=0 if job already finished and shared area is empty
        # don't update job when task status is SUCCESS to avoid async on_success of a task to overwrite job status
        # already written by a following task
        if job_start_time != 0 and status != 'SUCCESS':
            # get elapsed
            elapsed = current_time - float(job_start_time)

            # update job
            self.update_job(current_time=time(), status='PROGRESS')

            # send event
            self.send_job_event(status, elapsed, ex, msg)

    #
    # handler
    #
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.

        Parameters:

            exc - The exception raised by the task.
            task_id - Unique id of the failed task.
            args - Original arguments for the task that failed.
            kwargs - Original keyword arguments for the task that failed.
            einfo - ExceptionInfo instance, containing the traceback.

        The return value of this handler is ignored.
        """
        err = exc
        BaseTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        trace = format_tb(einfo.tb)
        trace.append(err)
        logger.error('', exc_info=1)
        msg = 'ERROR %s:%s %s' % (self.name, task_id, err)
        self.update('FAILURE', ex=err, traceback=trace, result=None, msg=msg)

        # update job
        self.update_job(params={}, status='FAILURE', current_time=time(), ex=err, traceback=trace, result=None,
                        msg=err)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task is to be retried.

        Parameters:

            exc - The exception sent to retry().
            task_id - Unique id of the retried task.
            args - Original arguments for the retried task.
            kwargs - Original keyword arguments for the retried task.
            einfo - ExceptionInfo instance, containing the traceback.

        The return value of this handler is ignored.
        """
        self.update('RETRY')

    def on_success(self, retval, task_id, args, kwargs):
        """Run by the worker if the task executes successfully.

        Parameters:

            retval - The return value of the task.
            task_id - Unique id of the executed task.
            args - Original arguments for the executed task.
            kwargs - Original keyword arguments for the executed task.

        The return value of this handler is ignored.
        """
        self.update('SUCCESS', msg='STOP - %s:%s' % (self.name, task_id))


def job(entity_class=None, name=None, module=None, delta=2):
    """Decorator used for workflow main task.

    Example::

        @job(entity_class=OpenstackSecurityGroup, name='insert', module='ResourceModule', delta=5)
        def func(self, objid, *args, **kwargs):
            pass

    :param entity_class: resource class
    :param name: job name [optional]
    :param op: operation [default=None]
    :param act: action (insert, update, delete, view, use) [default=use]
    :param module: beehive module [optional]
    :param delta: delta time to use when pull remote resource status
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(task, objid, *args, **kwargs):
            # setup correct user
            user_data = args[0]
            try:
                user = user_data.pop('user', 'task_manager')
                server = user_data.pop('server', '127.0.0.1')
                identity = user_data.pop('identity', '')
                api_id = user_data.pop('api_id', '')
            except BaseException:
                logger.warn('Can not get request user', exc_info=1)
                user = 'task_manager'
                server = '127.0.0.1'
                identity = ''
                api_id = ''

            operation.perms = []
            operation.user = (user, server, identity)
            operation.id = api_id
            operation.session = None
            operation.transaction = None
            operation.authorize = False
            operation.cache = False
            operation.encryption_key = task.app.api_manager.app_fernet_key

            if entity_class.module is not None:
                mod = task.app.api_manager.modules[entity_class.module]
                task_local.controller = mod.get_controller()
            elif module is not None:
                mod = task.app.api_manager.modules[module]
                task_local.controller = mod.get_controller()

            task_local.entity_class = entity_class
            task_local.objid = objid
            task_local.op = name
            task_local.opid = task.request.id
            task_local.delta = delta
            task_local.user = operation.user
            task_local.api_id = api_id

            # record PENDING task and set start-time
            ### status = 'STARTED'
            # start_time = time()
            # params = {
            #     'start-time': start_time,
            # }
            # task.set_shared_data(params)
            # task.update_job(status=status, current_time=time())

            # # send event
            ### task.send_job_event(status, 0, ex=None, msg=None)

            res = fn(task, objid, *args, **kwargs)
            task.release_session()
            return res
        return decorated_view
    return wrapper


def job_task(module='', synchronous=True):
    """Decorator used for workflow child task.

    Example::

        @job(module='ResourceModule')
        def func(self, options, *args, **kwargs):
            pass

    :param module: beehive module [optional]
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(task, params, *args, **kwargs):
            entity_class = import_class(params[0])

            if entity_class.module is not None:
                mod = task.app.api_manager.modules[entity_class.module]
                task_local.controller = mod.get_controller()
            elif module is not None:
                mod = task.app.api_manager.modules[module]
                task_local.controller = mod.get_controller()

            task_local.entity_class = entity_class
            task_local.objid = params[1]
            task_local.op = params[2]
            task_local.opid = params[3]
            task_local.delta = params[5]
            task_local.api_id = params[7]

            operation.perms = []
            operation.user = params[6]
            operation.id = params[7]
            operation.session = None
            operation.transaction = None
            operation.authorize = False
            operation.cache = False
            operation.encryption_key = task.app.api_manager.app_fernet_key

            res = None
            # task.update('STARTED', start_time=time(), msg='Start %s:%s' % (task.name, task.request.id))
            task.update('STARTED', msg='START - %s:%s' % (task.name, task.request.id))
            if synchronous:
                try:
                    res = fn(task, params, *args, **kwargs)
                except:
                    raise
                finally:
                    task.release_session()
            else:
                try:
                    res = fn(task, params, *args, **kwargs)
                except Exception as e:
                    msg = 'FAIL - %s:%s caused by %s' % (task.name, task.request.id, e)

                    task.on_failure(e, task.request.id, args, kwargs, ExceptionInfo())
                    logger.error(msg)
                finally:
                    task.release_session()

            return res
        return decorated_view
    return wrapper
