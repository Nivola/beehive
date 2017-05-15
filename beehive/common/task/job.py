'''
Created on May 12, 2017

@author: darkbk
'''
import ujson as json
from time import time
from beehive.common.task import BaseTask
from celery.utils.log import get_task_logger
from beehive.common.apimanager import ApiManagerError, ApiEvent
from celery.result import AsyncResult, GroupResult
from beehive.common.data import operation
from beehive.module.scheduler.manager import task_manager


logger = get_task_logger(__name__)

# job operation
try:
    import gevent
    task_local = gevent.local.local()
except:
    import threading
    task_local = threading.local()

class JobError(Exception):
    def __init__(self, value, code=0):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)
        
    def __repr__(self):
        return "JobError: %s" % self.value

    def __str__(self):
        return "JobError: %s" % self.value
    
class JobInvokeApiError(Exception):
    def __init__(self, value, code=0):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)
        
    def __repr__(self):
        return "JobInvokeApiError: %s" % self.value

    def __str__(self):
        return "JobInvokeApiError: %s" % self.value    
        
class Job(BaseTask):
    abstract = True
    inner_type = 'JOB'

    def __init__(self, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)
        
        '''
        self.controller = None
        self.objtype = None
        self.objdef = None
        self.objid = None
        self.opid = None
        self.op = None
        self.start = 0'''

    @property
    def controller(self):
        return task_local.controller

    def api_admin_request(self, module, path, method, data=u'', 
                          other_headers=None):
        if isinstance(data, dict): data = json.dumps(data)
        return self.app.api_manager.api_client.admin_request(module, path, 
                                                             method, data,
                                                             other_headers)

    def api_user_request(self, module, path, method, data=u'',
                         other_headers=None):
        if isinstance(data, dict): data = json.dumps(data)
        return self.app.api_manager.api_client.user_request(module, path, 
                                                            method, data,
                                                            other_headers)

    def invoke_api(self, module, uri, method, data, other_headers=None):
        """Ivoke cloudapi api.
        
        :param module: cloudapi module
        :param uri: api uri
        :param method: api method
        :param data dict: api data
        :param other_headers: extra headers to pass request
        :return: api result
        :raise: ApiManagerError
        """
        res = self.api_admin_request(module, uri, method, data, other_headers)
        
        if method in [u'POST', u'PUT', u'DELETE']:
            job_id = res[u'jobid']
            self.update(u'PROGRESS', msg=u'Invoke job %s' % job_id)
            
            status = u'PENDING'
            attempt = 1
            # after 6 attempt set status to FAILURE and block loop
            while status != u'SUCCESS' and status != u'FAILURE':
                gevent.sleep(task_local.delta)
                job = self._query_job(module, job_id, attempt)
                attempt = job[1]
                job = job[0]
                status = job[u'state']
                self.update(u'PROGRESS')
    
            self.update(u'PROGRESS', msg=u'Job %s completed with %s' % 
                        (job_id, status))
            if status == u'FAILURE':
                try:
                    trace = job[u'traceback'][-1]
                except:
                    trace = u'Job %s was not found' % job_id
                err = u'Remote job %s error: %s' % (job_id, trace)
                #err = 'Task %s fails' % job_id
                logger.error(err)
                raise JobInvokeApiError(err)
            else:
                return job[u'result']
        else:
            return res

    def _query_job(self, module, job_id, attempt):
        """Query remote job status.
        
        :param module: cloudapi module
        :param task_id: id of the remote job
        :return: job status. Possible value are: PENDING, PROGRESS, SUCCESS,
                 FAILURE
        """
        try:
            uri = u'/v1.0/worker/tasks/%s/' % job_id
            res = self.api_admin_request(module, uri, u'GET', u'')
            logger.debug(u'Query job %s: %s' % (job_id, res[u'state']))
        except ApiManagerError as ex:
            # remote job query fails. Return fake state and wait new query
            res = {u'state':u'PROGRESS'}
            #attempt += 1
            #if attempt > 100:
            #    res = {u'state':u'FAILURE'}    
        return res, attempt
    
    def wait_for_job_complete(self, task_id):
        """Query celery job and wait until status is not SUCCESS or FAILURE
        
        :param task: celery task id
        :return: task results
        """
        try:
            # get celery task
            inner_task = AsyncResult(task_id, app=task_manager)
            res = None
            start = time()
            # loop until inner_task finish with success or error
            while inner_task.status != u'SUCCESS' and inner_task.status != u'FAILURE':
                gevent.sleep(task_local.delta)
                inner_task = AsyncResult(task_id, app=task_manager)
                elapsed = time() - start
                self.update(u'PROGRESS', msg=u'Task %s status %s after %ss' % 
                             (task_id, inner_task.status, elapsed))
            
            elapsed = time() - start
            if inner_task.failed() is True:
                logger.error(u'Task %s error after %ss : %s' % 
                             (task_id, elapsed, inner_task.traceback))
                raise JobError(inner_task.traceback)
            elif inner_task.ready() is True:
                logger.debug(u'Task %s success after %ss' % 
                             (task_id, elapsed))
                res = inner_task.get()
            else:
                logger.error(u'Task %s unknown after %ss' % 
                             (task_id, elapsed))
                raise JobError(u'Unknown error with task %s' % task_id)
            
            return res
        except Exception as ex:
            logger.error(ex, exc_info=1)
            raise JobError(ex)

    #
    # shared area
    #
    def get_shared_data(self):
        """ """
        return BaseTask.get_shared_data(self, task_local.opid)
    
    def set_shared_data(self, data):
        """ """
        return BaseTask.set_shared_data(self, task_local.opid, data)   
    
    def remove_shared_area(self):
        """ """
        return BaseTask.get_shared_data(self, task_local.opid)

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

    def get_session(self):
        self.app.api_manager.get_session()
        
    def flush_session(self):
        self.app.api_manager.flush_session()         
        
    def release_session(self):
        self.app.api_manager.release_session()

    def elapsed(self):
        elapsed = round(time() - task_local.start, 3)
        return elapsed  
    
    def get_entity_class_name(self):
        return task_local.entity_class.__module__ + '.' + task_local.entity_class.__name__
    
    def get_options(self):
        options = (self.get_entity_class_name(), task_local.objid, 
                   task_local.op, task_local.opid, task_local.start, 
                   task_local.delta, task_local.user)
        return options     
    
    def update(self, status, ex=None, traceback=None, result=None, msg=None):
        '''# get params from shared data
        #params = self.get_shared_data()
        #job_state = get_value(params, u'job_state', u'PROGRESS')
        # update job status if task failed
        #if status == u'FAILURE':
            # set job status
            params[u'job_state'] = status
            # save data in shared area
            self.set_shared_data(params)'''
        
        elapsed = self.elapsed()
        if status == u'PROGRESS' and not self.request.called_directly:
            self.update_state(state=u'PROGRESS', meta={u'elapsed': elapsed})

        # send event
        response = [status, elapsed]
        if ex is not None:
            response.append(ex)
        evt = ApiEvent(task_local.controller, oid=None, objid=task_local.objid,
                       data={u'opid':task_local.opid, 
                             u'op':task_local.op,
                             u'taskid':self.request.id, 
                             u'task':self.name,
                             u'params':self.request.args,
                             u'response':response,
                             u'msg':msg})
        entity_class = task_local.entity_class
        evt.objtype =  entity_class.objtype
        evt.objdef =  entity_class.objdef
        evt.publish(entity_class.objtype, u'asyncop')
        
        # log message
        if msg is not None:
            logger.debug(msg)
        
        # update task result
        task_id = self.request.id
        store_task_result(task_id, state=status, traceback=traceback,
                          retval=result, msg=msg)
        
        # get current job state
        #job = self._query_job(self.app.api_manager.app_id, task_local.opid)
        #job_state = job[u'state']
        
        if msg is not None and status == u'FAILURE':
            msg = u'ERROR: %s' % (msg)
            
        # update job status only if it is not already FAILURE
        params = self.get_shared_data()
        job_state = get_value(params, u'job_state', u'PROGRESS')        
        if job_state != u'FAILURE':
            # set job status
            params[u'job_state'] = status
            
            # set start time for job task when status is STARTED
            if status == u'STARTED':
                params[u'job_start_time'] = time()
                elapsed = 0
            # calculate elapsed for job task when status is not STARTED
            else:
                job_start_time = get_value(params, u'job_start_time', time())
                elapsed = round(time() - job_start_time, 4)                
            
            # save data in shared area
            self.set_shared_data(params)            
            
            # set result if status is SUCCESS
            retval = None
            if status == u'SUCCESS':
                if u'result' in params:
                    retval = params[u'result']
                # remove shared area
                self.remove_shared_area()
                
                # remove stack
                self.remove_stack()

            # store job data
            #if msg is not None:
            #    msg = u'[%s - %s] %s' % (self.name, task_id, msg)
            msg = None
            store_task_result(task_local.opid, state=status, retval=retval, 
                              traceback=traceback, duration=elapsed, msg=msg)
            logger.info(u'Job %s status change to %s - %s' % 
                        (task_local.opid, status, elapsed))
        
    def after_return(self, *args, **kwargs):
        """Handler called after the task returns.
        """
        super(Job, self).after_return(*args, **kwargs)
        
        if operation.session is not None:
            self.release_session()
        
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
        BaseTask.on_failure(self, exc, task_id, args, kwargs, einfo)
              
        err = str(exc)
        trace = format_tb(einfo.tb)
        trace.append(err)
        self.update(u'FAILURE', ex=err, traceback=trace, result=None, msg=err)
        
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
        #logger.info('Task %s.%s : RETRY - %s' % (self.name, task_id, self.elapsed()))
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
        pass

class JobTask(Job):
    abstract = True
    inner_type = 'JOBTASK'
        
def job(entity_class=None, job_name=None, module=None, delta=5):
    """Decorator used for workflow main task.
    
    Example::
    
        @job(entity_class=OpenstackSecurityGroup, 
             job_name='openstack.securitygroup.insert', 
             module='ResourceModule', delta=5)
        def func(self, objid, *args, **kwargs):
            pass

    :param entity_class: resource class
    :param job_name: job name
    :param module: cloudapi module 
    :param delta: delta time to use when pull remote resource status
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            task = args[0]
            store_task_result(task.request.id, state=u'PENDING', retval=None, 
                              traceback=None)

            # setup correct user
            try:
                user = get_value(kwargs, u'user', u'task_manager')
                server = get_value(kwargs, u'server', u'127.0.0.1')
                identity = get_value(kwargs, u'identity', u'')
            except:
                logger.warn(u'Can not get request user', exc_info=1)
                user = u'task_manager'
                server = u'127.0.0.1'
                identity = u''

            operation.perms = []
            operation.user = (user, server, identity)
            operation.session = None
            
            if module != None:
                mod = task.app.api_manager.modules[module]
                task_local.controller = mod.get_controller()
            
            task_local.entity_class = entity_class
            task_local.objid = args[1]
            task_local.op = job_name
            task_local.opid = task.request.id
            task_local.start = time()
            task_local.delta = delta
            task_local.user = operation.user
            task.set_shared_data({})
            
            #logger.debug(u'Job %s - master task %s' % (task_local.op, 
            #                                           task_local.opid))            
            #res = fn(*args, **kwargs)
            res = fn(*args)
            task.update(u'STARTED')
            return res
        return decorated_view
    return wrapper

def job_task(module=''):
    """Decorator used for workflow child task.
    
    Example::
    
        @job(module='ResourceModule')
        def func(self, options, *args, **kwargs):
            pass

    :param module: cloudapi module
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            task = args[0]
            params = args[1]
            
            if module != None:
                mod = task.app.api_manager.modules[module]
                task_local.controller = mod.get_controller()
            
            task_local.entity_class = import_class(params[0])
            task_local.objid = params[1]
            task_local.op = params[2]
            task_local.opid = params[3]
            task_local.start = params[4]
            task_local.delta = params[5]
            #task_local.inner_type = 'JOBTASK'

            operation.perms = []
            operation.user = params[6]
            operation.session = None            

            task.update(u'PROGRESS')
            #logger.debug(u'Job %s - child task %s.%s' % (task_local.op, 
            #                                             task_local.opid, 
            #                                             task.request.id))
            res = fn(*args, **kwargs)
            return res
        return decorated_view
    return wrapper

def create_job(tasks, *args):
    """
    """
    process = tasks.pop().si(*args)
    last_task = None
    for task in tasks:
        if isinstance(task, list):
            item = chord(task, last_task)
        else:
            item = task.si(*args)
            if last_task is not None:
                item.link(last_task)
        last_task = item
    process.link(last_task)
    return process