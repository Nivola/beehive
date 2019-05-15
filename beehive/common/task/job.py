"""
Created on May 12, 2017

@author: darkbk
"""
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
        self.value = str(value)
        Exception.__init__(self, value, code)
        
    def __repr__(self):
        return "JobError: %s" % self.value

    def __str__(self):
        return self.value


class JobInvokeApiError(Exception):
    def __init__(self, value, code=0):
        self.code = code
        self.value = str(value)
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
        temp = objdef.split(u'.')
        ids = [u'*' for i in temp]
        return u'//'.join(ids)
    
    def set_operation(self):
        """
        """        
        operation.perms = []
        for op in self.ops:
            perm = (1, 1, op.objtype, op.objdef, self.get_operation_id(op.objdef), 1, u'*')
            operation.perms.append(perm)
        logger.debug(u'Set permissions: %s' % operation.perms)     

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
        return task_local.entity_class.__module__ + u'.' + \
               task_local.entity_class.__name__    
    
    def get_options(self):
        """Return tupla with some useful options.
        
        :return:  (class_name, objid, job, job id, start time, 
                   time before new query, user) 
        """
        options = (self.get_entity_class_name(), task_local.objid, 
                   task_local.op, task_local.opid, None, 
                   task_local.delta, task_local.user)
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

        action = task_local.op.split(u'.')[-1]
        op = task_local.op
        op = op.replace(u'.%s' % action, u'')
        entity_class = task_local.entity_class
        data={
            u'opid': task_local.opid,
            u'op': u'%s.%s' % (task_local.entity_class.objdef, op),
            u'taskid': self.request.id,
            u'task': self.name,
            u'params': self.request.args,
            u'response': response,
            u'elapsed': elapsed,
            u'msg': str(msg)
        }
        
        source = {
            u'user': operation.user[0],
            u'ip': operation.user[1],
            u'identity': operation.user[2]
        }
        
        dest = {
            u'ip': task_local.controller.module.api_manager.server_name,
            u'port': task_local.controller.module.api_manager.http_socket,
            u'objid': task_local.objid,
            u'objtype': entity_class.objtype,
            u'objdef': entity_class.objdef,
            u'action': action
        }      
        
        # send event
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(ApiObject.ASYNC_OPERATION, data, source, dest)
        except Exception as ex:
            logger.warn(u'Event can not be published. Event producer is not configured - %s' % ex)
    
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
        if job[u'status'] is not None and job[u'status'] == u'FAILURE':
            return None

        params = self.get_shared_data()
        # if job is finished exit to avoid wrong status change
        if params.get(u'is-finished', False) is True:
            return None

        if u'start-time' not in params.keys():
            params[u'start-time'] = job.get(u'start_time')
            self.set_shared_data(params)

        # set result if status is SUCCESS
        retval = None
        if status == u'SUCCESS':
            # set flag for SUCCESS job
            params[u'is-finished'] = True
            self.set_shared_data(params)

            if u'result' in params:
                retval = params[u'result']
            # remove shared area
            # self.remove_shared_area()
            
            # remove stack
            # self.remove_stack()

        # store job data
        msg = None
        counter = int(job.get(u'counter', 0)) + 1
        TaskResult.store(task_local.opid, status=status, retval=retval, inner_type=u'JOB', traceback=traceback,
                         stop_time=current_time, msg=msg, counter=counter)
        if status == u'FAILURE':
            logger.error(u'JOB %s status change to %s' % (task_local.opid, status))
        else:         
            logger.info(u'JOB %s status change to %s' % (task_local.opid, status))


class Job(AbstractJob):
    abstract = True
    inner_type = u'JOB'

    def __init__(self, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)

    @staticmethod
    def create(tasks, *args, **kvargs):
        """Create celery signature with chord, group and chain

        :param tasks: list of celery task
        :return: celery signature
        """
        process = tasks.pop().signature(args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
        last_task = None
        for task in tasks:
            if not isinstance(task, list):
                item = task.signature(args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
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
            {u'task':<celery task>, u'args':..}
        :return: celery signature
        """
        tasks.reverse()
        process = tasks.pop().signature(args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
        last_task = None
        for task in tasks:
            if not isinstance(task, list):
                if isinstance(task, dict):
                    internal_args = list(args)
                    internal_args.extend(task.get(u'args'))
                    item = task.get(u'task').signature(internal_args, immutable=True,
                                                       queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                else:
                    item = task.signature(args, immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                if last_task is not None:
                    item.link(last_task)
            elif isinstance(task, list) and len(task) > 0:
                subitems = []
                for subtask in task:
                    if isinstance(subtask, dict):
                        internal_args = list(args)
                        internal_args.extend(subtask.get(u'args'))
                        subitem = subtask.get(u'task').signature(internal_args, immutable=True,
                                                                 queue=task_manager.conf.TASK_DEFAULT_QUEUE)
                    else:
                        subitem = subtask.get(u'task').signature(args, immutable=True,
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
            {u'task':<celery task>, u'args':..}
        :param params: list of celery task params
        :return: True
        """
        from beehive.common.task.util import end_task, start_task

        ops = inst.get_options()
        inst.set_shared_data(params)
        tasks.insert(0, start_task)
        tasks.append(end_task)
        logger.debug2(u'Workflow tasks: %s' % tasks)
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
        err = str(exc)
        BaseTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        trace = format_tb(einfo.tb)
        trace.append(err)
        logger.error(u'', exc_info=1)
        self.update_job(params={}, status=u'FAILURE', current_time=time(), ex=err, traceback=trace,
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
        self.update_job(status=u'FAILURE', current_time=time())    


class JobTask(AbstractJob):
    abstract = True
    inner_type = u'JOBTASK'       

    #
    # api
    #
    def api_admin_request(self, module, path, method, data=u'', other_headers=None):
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.app.api_manager.api_client.admin_request(module, path, method, data, other_headers, silent=True)

    def api_user_request(self, module, path, method, data=u'', other_headers=None):
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.app.api_manager.api_client.user_request(module, path, method, data, other_headers, silent=True)

    def _query_job(self, module, job_id, attempt):
        """Query remote job status.
        
        :param module: beehive module
        :param task_id: id of the remote job
        :return: job status. Possible value are: PENDING, PROGRESS, SUCCESS,
                 FAILURE
        """
        prefix = {
            u'auth': u'nas',
            u'service': u'nws',
            u'resource': u'nrs',
            u'event': u'nes'
        }

        try:
            uri = u'/v1.0/%s/worker/tasks/%s' % (prefix[module], job_id)
            res = self.api_admin_request(module, uri, u'GET', u'').get(u'task_instance', {})
            logger.debug(u'Query job %s: %s' % (job_id, res[u'status']))
        except ApiManagerError as ex:
            # remote job query fails. Return fake state and wait new query
            res = {u'state': u'PROGRESS'}
        return res, attempt

    def invoke_api(self, module, uri, method, data, other_headers=None, link=None):
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
        self.update(u'PROGRESS', msg=u'Invoke api %s [%s] in module %s' % (uri, method, module))

        if link is not None:
            # set up link from remote stack to instance
            self.release_session()
            self.get_session()
            resource = self.get_resource(link)
            resource.add_link(u'%s-link' % res[u'uuid'], u'relation', res[u'uuid'], attributes={})
            # self.release_session()
            self.update(u'PROGRESS', msg=u'Setup link between resource %s and resource %s' %
                                         (res[u'uuid'], resource.oid))
            # self.release_session()

        if method in [u'POST', u'PUT', u'DELETE']:
            job_id = res[u'jobid']
            self.update(u'PROGRESS', msg=u'Invoke job %s' % job_id)
            
            status = u'PENDING'
            attempt = 1
            # after 6 attempt set status to FAILURE and block loop
            while status != u'SUCCESS' and status != u'FAILURE':
                sleep(task_local.delta)
                job = self._query_job(module, job_id, attempt)
                attempt = job[1]
                job = job[0]
                status = job[u'status']
                self.update(u'PROGRESS')
    
            self.update(status, msg=u'Job %s completed with %s' % (job_id, status))
            if status == u'FAILURE':
                try:
                    trace = job[u'traceback'][-1]
                except:
                    trace = u'Job %s was not found' % job_id
                err = u'Remote job %s error: %s' % (job_id, trace)
                trace = str(trace)
                logger.error(err)
                raise JobInvokeApiError(trace)
            else:
                return job[u'result']
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
            self.update(u'PROGRESS', job=task_id)

            # get celery task
            inner_task = TaskResult.get(task_id)
            start = time()

            # loop until inner_task finish with success or error
            status = inner_task.get(u'status')
            start_counter = inner_task.get(u'counter', 0)
            while status != u'SUCCESS' and status != u'FAILURE':
                sleep(task_local.delta)
                inner_task = TaskResult.get(task_id)
                counter = inner_task.get(u'counter')
                elapsed = time() - start
                # verify job is stalled
                if counter - start_counter == 0 and elapsed > 60:
                    raise JobError(u'Job %s is stalled' % task_id)

                self.update(u'PROGRESS', msg=u'Job %s status %s after %ss' % (task_id, status, elapsed))
                status = inner_task.get(u'status')
            
            elapsed = time() - start
            if status == u'FAILURE':
                err = inner_task.get(u'traceback')[-1]
                logger.error(u'Job %s error after %ss' % (task_id, elapsed))
                self.update(u'PROGRESS', msg=u'Job %s status %s after %ss' % (task_id, status, elapsed))
                raise JobError(err)
            elif status == u'SUCCESS':
                self.update(u'PROGRESS', msg=u'Job %s success after %ss' % (task_id, elapsed))
                res = inner_task
            else:
                logger.error(u'Job %s unknown error after %ss' % (task_id, elapsed))
                self.update(u'PROGRESS', msg=u'Job %s status %s after %ss' % (task_id, u'UNKNONWN', elapsed))
                raise JobError(u'Unknown error')
            
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
        self.update(u'PROGRESS', msg=msg)

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
            msg = str(msg)
            if status == u'FAILURE':
                # logger.error(msg, exc_info=1)
                logger.error(msg)
                # msg = u'ERROR: %s' % msg
            else:
                logger.debug(truncate(msg))
        
        # update jobtask result
        task_id = self.request.id
        jobs = None
        if job is not None:
            jobs = [job]
        TaskResult.store(task_id, status=status, traceback=traceback, retval=result, msg=msg, stop_time=current_time,
                         start_time=start_time, inner_type=u'JOBTASK', jobs=jobs)

        # get job start time
        job_start_time = params.get(u'start-time', 0)        
        
        # update job only if job_start_time is not 0. job_start_time=0 if job already finished and shared area is empty
        # don't update job when task status is SUCCESS to avoid async on_success of a task to overwrite job status
        # already written by a following task
        if job_start_time != 0 and status != u'SUCCESS':
            # get elapsed
            elapsed = current_time - float(job_start_time)        
            
            # update job
            self.update_job(current_time=time(), status=u'PROGRESS')
    
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
        err = str(exc)
        BaseTask.on_failure(self, exc, task_id, args, kwargs, einfo)
        trace = format_tb(einfo.tb)
        trace.append(err)
        logger.error(u'', exc_info=1)
        msg = u'ERROR %s:%s %s' % (self.name, task_id, err)
        self.update(u'FAILURE', ex=err, traceback=trace, result=None, msg=msg)
        
        # update job
        self.update_job(params={}, status=u'FAILURE', current_time=time(), ex=err, traceback=trace, result=None,
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
        self.update(u'RETRY')
    
    def on_success(self, retval, task_id, args, kwargs):
        """Run by the worker if the task executes successfully.
        
        Parameters:    
    
            retval - The return value of the task.
            task_id - Unique id of the executed task.
            args - Original arguments for the executed task.
            kwargs - Original keyword arguments for the executed task.
    
        The return value of this handler is ignored.
        """
        self.update(u'SUCCESS', msg=u'STOP - %s:%s' % (self.name, task_id))


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
                user = user_data.pop(u'user', u'task_manager')
                server = user_data.pop(u'server', u'127.0.0.1')
                identity = user_data.pop(u'identity', u'')
            except:
                logger.warn(u'Can not get request user', exc_info=1)
                user = u'task_manager'
                server = u'127.0.0.1'
                identity = u''

            operation.perms = []
            operation.user = (user, server, identity)
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
            
            # record PENDING task and set start-time
            status = u'STARTED'
            # start_time = time()
            # params = {
            #     u'start-time': start_time,
            # }
            # task.set_shared_data(params)
            task.update_job(status=status, current_time=time())
            
            # send event
            task.send_job_event(status, 0, ex=None, msg=None)
                   
            res = fn(task, objid, *args, **kwargs)
            task.release_session()
            return res
        return decorated_view
    return wrapper


def job_task(module=u'', synchronous=True):
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

            operation.perms = []
            operation.user = params[6]
            operation.session = None
            operation.transaction = None
            operation.authorize = False
            operation.cache = False
            operation.encryption_key = task.app.api_manager.app_fernet_key

            res = None
            # task.update(u'STARTED', start_time=time(), msg=u'Start %s:%s' % (task.name, task.request.id))
            task.update(u'STARTED', msg=u'START - %s:%s' % (task.name, task.request.id))
            if synchronous:
                res = fn(task, params, *args, **kwargs)
                task.release_session()
            else:
                
                try:
                    res = fn(task, params, *args, **kwargs)
                except Exception as e:
                    msg = u'FAIL - %s:%s caused by %s' % (task.name, task.request.id, e)
                    
                    task.on_failure(e, task.request.id, args, kwargs, ExceptionInfo())
                    logger.error(msg)
                finally:
                    task.release_session()
                    
            return res
        return decorated_view
    return wrapper
