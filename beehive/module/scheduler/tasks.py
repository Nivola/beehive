'''
Created on Nov 3, 2015

@author: darkbk
'''
import ujson as json
from celery import Celery
from celery.utils.log import get_task_logger
from celery import chain, chord, group, signature
from time import sleep
from beehive.common.data import operation
from gevent import sleep
from time import time
from .manager import task_manager
from functools import wraps
from celery import Task
from beecell.simple import id_gen, truncate, get_value
from beehive.common.apimanager import ApiManagerError, ApiEvent
from beecell.simple import import_class, str2uni
from datetime import datetime
from celery.result import AsyncResult, GroupResult
from traceback import format_tb
import gevent, random
from beehive.module.scheduler.controller import TaskManager
from celery.signals import after_task_publish, task_prerun, task_postrun, \
                           task_success, task_failure, task_retry, task_revoked, \
                           before_task_publish

logger = get_task_logger(__name__)

# job operation
try:
    import gevent
    task_local = gevent.local.local()
except:
    import threading
    task_local = threading.local()

#@task_postrun.connect
#def task_task_postrun(sender=None, task_id=None, task=None, args=None,
#                      kwargs=None, retval=None, state=None):
#    pass

'''
@after_task_publish.connect
def after_task_publish(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [after_task_publish] %s' % kwargs)
    
@task_prerun.connect
def task_prerun(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_prerun] %s' % kwargs)
    
@task_postrun.connect
def task_postrun(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_postrun] %s' % kwargs)
    
@task_success.connect
def task_success(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_success] %s' % kwargs)
    
@task_failure.connect
def task_failure(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_failure] %s' % kwargs)
    
@task_retry.connect
def task_retry(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_retry] %s' % kwargs)
    
@task_revoked.connect
def task_revoked(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_revoked] %s' % kwargs)
'''

def store_task_result(task_id, name=None, hostname=None, args=None, kwargs=None, 
                      state=None, retval=None, timestamp=None, duration=None, 
                      childs=None, traceback=None, inner_type=None, msg=None):
    """ """
    _redis = task_manager.api_manager.redis_taskmanager.conn
    _prefix = task_manager.conf[u'CELERY_REDIS_RESULT_KEY_PREFIX']
    _expire = task_manager.conf[u'CELERY_REDIS_RESULT_EXPIRES']
    
    data = {u'id':task_id}
    
    def set_data(key, value):
        if value is not None:
            data[key] = value
    
    set_data(u'name', name)
    set_data(u'type', inner_type)
    set_data(u'worker', hostname)
    set_data(u'args', args)
    set_data(u'kwargs', kwargs)
    set_data(u'state', state)
    set_data(u'result', retval)
    set_data(u'timestamp', timestamp)
    set_data(u'duration', duration)
    set_data(u'childs', childs)
    set_data(u'traceback', traceback)
    
    # get data from redis
    val = _redis.get(_prefix + task_id)
    if val is not None:
        result = json.loads(val)
        result.update(data)
    else:
        result = {
            u'name':name,
            u'type':inner_type,
            u'id':task_id,
            u'worker':hostname,
            u'args':args,
            u'kwargs':kwargs,
            u'state':state,
            u'result':retval,
            u'traceback':traceback,
            u'timestamp':timestamp,
            u'duration':duration,
            u'childs':childs,
            u'trace':[]}
    
    # update task trace
    if msg is not None:
        _timestamp = str2uni(datetime.today().strftime(u'%d-%m-%y %H:%M:%S-%f'))
        result[u'trace'].append((_timestamp, msg))
    
    # serialize data
    val = json.dumps(result)
    # save data in redis
    _redis.setex(_prefix + task_id, _expire, val)
    logger.debug(u'Save task %s result: %s' % (task_id, truncate(data)))        
    return val

@task_prerun.connect
def task_prerun(task, sender, task_id, signal, args, kwargs):
    # store task
    #store_task_result(task_id, task.name, task.request.hostname, args, kwargs, 
    #                  'PENDING', None, None, None, None, None, 
    #                  task.inner_type)
    
    # get task timestamp
    _timestamp = str2uni(datetime.today().strftime(u'%d-%m-%y %H:%M:%S-%f'))
    
    # get task initial time
    task.inner_start = time()
    
    # store task
    store_task_result(task_id, task.name, task.request.hostname, args, kwargs, 
                      u'PENDING', None, _timestamp, None, None, None, 
                      task.inner_type)

@task_postrun.connect
def task_postrun(task, sender, task_id, signal, args, state, kwargs, retval):
    # get task childrens
    childrens = task.request.children
    chord = task.request.chord
    
    childs = []
    if len(childrens) > 0:
        for c in childrens:
            if isinstance(c, AsyncResult):
                childs.append(c.id)
            elif isinstance(c, GroupResult):
                for i in c:
                    childs.append(i.id)
    if chord is not None:
        childs.append(chord[u'options'][u'task_id'])
        
    # get task duration
    duration = round(time() - task.inner_start, 3)

    # set retval to None when failure occurs
    if state == u'FAILURE':
        retval = None

    # reset state for JOB task to PROGRESS when state is SUCCESS
    # state SUCCESS will be set when the last child task end
    if task.inner_type == u'JOB' and \
       task_local.opid == task_id and \
       state == u'SUCCESS':
        state = u'PROGRESS'
    
    # store task
    store_task_result(task_id, task.name, task.request.hostname, args, kwargs, 
                      state, retval, None, duration, set(childs))

@task_failure.connect
def task_failure(exception, traceback, sender, task_id, signal, args, 
                 kwargs, einfo):
    # store task
    #try:
    #    err = exception.message
    #except:
    #    err = exception

    #trace = format_tb(einfo.tb)
    #trace.append(exception)
    #logger.warn('$$$$$$$$ %s ' % trace)
    #store_task_result(task_id, traceback=trace)
    pass  
    
@task_retry.connect
def task_retry(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_retry] %s' % kwargs)
    
@task_revoked.connect
def task_revoked(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_revoked] %s' % kwargs)

class BaseTask(Task):
    abstract = True
    inner_type = 'TASK'
    prefix = 'celery-task-shared-'
    prefix_stack = 'celery-task-stack-'
    expire = 3600
    
    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)
        
        try:
            self._redis = self.app.api_manager.redis_taskmanager.conn
        except:
            self._redis = None
    
    '''
    def __call__(self, *args, **kwargs):
        """In celery task this function call the run method, here you can
        set some environment variable before the run of the task"""
        res = self.run(*args, **kwargs)
        return res'''

    #
    # shared area
    #
    def get_shared_data(self, task_id):
        """Get data from shared memory area. Use this to pass data from different
        tasks. Shared area could not ensure synchronization
        """
        data = None
        val = self._redis.get(self.prefix + task_id)
        if val is not None:
            data = json.loads(val)
        #logger.debug(u'Get shared data for job %s: %s' % 
        #             (task_id, truncate(data)))   
        return data
    
    def set_shared_data(self, task_id, data):
        """Set data to shared memory area. Use this to pass data from different
        tasks. Shared area could not ensure synchronization
        """
        val = json.dumps(data)
        self._redis.setex(self.prefix + task_id, self.expire, val)
        #logger.debug(u'Set shared data for job %s: %s' % 
        #             (task_id, truncate(data)))
        return True
    
    def remove_shared_area(self, task_id):
        """Remove shared memory area reference from redis"""
        keys = self._redis.keys(self.prefix + task_id)
        res = self._redis.delete(*keys)
        return res

    #
    # shared stack area
    #
    def pop_stack_data(self, task_id):
        """Pop item from shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        data = None
        val = self._redis.lpop(self.prefix_stack + task_id)
        if val is not None:
            data = json.loads(val)
        logger.debug('Pop stack data for job %s: %s' % 
                     (task_id, truncate(data)))   
        return data
    
    def push_stack_data(self, task_id, data):
        """Set data to shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        val = json.dumps(data)
        self._redis.lpush(self.prefix_stack + task_id, val)
        logger.debug('Push stack data for job %s: %s' % 
                     (task_id, truncate(data)))
        return True
    
    def remove_stack(self, task_id):
        """Remove shared memory stack reference from redis"""
        try:
            keys = self._redis.keys(self.prefix_stack + task_id)
            res = self._redis.delete(*keys)
            return res
        except:
            pass

    def after_return(self, *args, **kwargs):
        """Handler called after the task returns.
        
        Parameters:    
    
            status - Current task state.
            retval - Task return value/exception.
            task_id - Unique id of the task.
            args - Original arguments for the task that returned.
            kwargs - Original keyword arguments for the task that returned.
            einfo - ExceptionInfo instance, containing the traceback (if any).
    
        The return value of this handler is ignored.
        """
        super(BaseTask, self).after_return(*args, **kwargs) 

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
        pass

class DatabaseTask(BaseTask):
    abstract = True

    def __init__(self, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)

    def _get_session(self):
        self.app.api_manager.get_session()
        
    def _flush_session(self):
        self.app.api_manager.flush_session()        
        
    def _release_session(self):
        self.app.api_manager.release_session()   

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called after the task returns.
        
        Parameters:    
    
            status - Current task state.
            retval - Task return value/exception.
            task_id - Unique id of the task.
            args - Original arguments for the task that returned.
            kwargs - Original keyword arguments for the task that returned.
            einfo - ExceptionInfo instance, containing the traceback (if any).
    
        The return value of this handler is ignored.
        """
        BaseTask.after_return(self, status, retval, task_id, args, kwargs, einfo)
        
        if operation.session is not None:
            self._release_session()
            
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

    def api_admin_request(self, module, path, method, data='', 
                          other_headers=None):
        return self.app.api_manager.api_client.admin_request(module, path, 
                                                             method, data,
                                                             other_headers)

    def api_user_request(self, module, path, method, data='',
                         other_headers=None):
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
        res = self.api_admin_request(module, uri, method, json.dumps(data),
                                     other_headers)
        
        if method in ['POST', 'PUT', 'DELETE']:
            job_id = res[u'jobid']
            
            status = 'PENDING'
            while status != 'SUCCESS' and status != 'FAILURE':
                job = self._query_job(module, job_id)
                status = job[u'state']
                gevent.sleep(task_local.delta)
                self.update(u'PROGRESS')
    
            if status == 'FAILURE':
                err = "Remote job %s error: %s" % (job_id, job[u'traceback'][-1])
                #err = 'Task %s fails' % job_id
                logger.error(err, exc_info=True)
                raise JobInvokeApiError(err)
            else:
                return job[u'result']
        else:
            return res

    def _query_job(self, module, job_id):
        """Query remote job status.
        
        :param module: cloudapi module
        :param task_id: id of the remote job
        :return: job status. Possible value are: PENDING, PROGRESS, SUCCESS,
                 FAILURE
        """
        try:
            uri = u'/v1.0/task/task/%s/' % job_id
            res = self.api_admin_request(module, uri, 'GET', '')
            logger.debug('Query job %s: %s' % (job_id, res[u'state']))
        except ApiManagerError as ex:
            # remote job query fails. Return fake state and wait new query
            res = {u'state':u'PROGRESS'}
            '''# try to re-query if the first call failed
            if ex.code == 404:
                gevent.sleep(0.1)

                uri = '/v1.0/task/task/%s/' % job_id
                res = self.api_admin_request(module, uri, 'GET', '')
                logger.debug('Re-Query job %s: %s' % (job_id, res[u'state']))
            #logger.warn('Task %s not found' % job_id)'''     
        return res

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
        logger.debug(u"Send event: %s" % response)
        
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
        
        # get params from shared data
        params = self.get_shared_data()
        job_state = get_value(params, u'job_state', u'PROGRESS')

        # update job status only if it is not already FAILURE
        if job_state != u'FAILURE':
            # set start time for job task when status is STARTED
            if status == u'STARTED':
                params[u'job_start_time'] = time()
            # calculate elapsed for job task when status is not STARTED
            else:
                job_start_time = get_value(params, u'job_start_time', time())
                elapsed = round(time() - job_start_time, 3)                
            
            # set result if status is SUCCESS
            retval = None
            if status == u'SUCCESS':
                if u'result' in params:
                    retval = params[u'result']
                # remove shared area
                self.remove_shared_area()
                
                # remove stack
                self.remove_stack()
                            
            # set job status
            params[u'job_state'] = status
            
            # save data in shared area
            self.set_shared_data(params)
            
            # store job data
            #if msg is not None:
            #    msg = u'[%s - %s] %s' % (self.name, task_id, msg)
            msg = None
            store_task_result(task_local.opid, state=status, retval=retval, 
                              traceback=traceback, duration=elapsed, msg=msg)            
        
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called after the task returns.
        
        Parameters:    
    
            status - Current task state.
            retval - Task return value/exception.
            task_id - Unique id of the task.
            args - Original arguments for the task that returned.
            kwargs - Original keyword arguments for the task that returned.
            einfo - ExceptionInfo instance, containing the traceback (if any).
    
        The return value of this handler is ignored.
        """
        BaseTask.after_return(self, status, retval, task_id, args, kwargs, einfo)
        
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
        self.update('FAILURE', ex=err, traceback=trace, result=None, msg=err)
        
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
            logger.debug(args)
            logger.debug(kwargs)
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

#
# tasks
#
@task_manager.task(bind=True, base=BaseTask, name='tasks.test')
def test(self):
    logger.info('Start %s' % self.name)
    sleep(2)
    logger.info('Stop %s' % self.name)
    #raise Exception('eee')
    return True

#
# test job
#
@task_manager.task(bind=True, base=Job, name='tasks.jobtest2')
@job(entity_class=TaskManager, job_name='manager.jobtest2.insert', 
     module='ResourceModule', delta=2)
def jobtest2(self, objid, params):
    """Test job
    
    :param objid: objid of the task manager. Ex. 110//2222//334//*
    :param params: task input params
    
            {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]}    
    """
    #operation.perms = [
    #    (1, 1, 'task', 'manager', 'TaskManager', '*', 1, '*')
    #]
    
    module = 'resource'
    uri = '/v1.0/task/task/jobtest/'
    res = self.invoke_api(module, uri, 'POST', params)
    return res

@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, 
     job_name='tenant.jobtest.insert', 
     module='ResourceModule', delta=5)
def jobtest(self, objid, params):
    """Test job
    
    :param objid: objid of the cloud domain. Ex. 110//2222//334//*
    :param params: task input params 
                    {u'x':.., u'y':.., u'numbers':[], u'mul_numbers':[]}
    """
    ops = self.get_options()
    
    self.set_shared_data(params)
    
    numbers = params[u'numbers']
    g1 = []
    for i in range(0,len(numbers)):
        g1.append(jobtest_mul.si(ops, i))
    
    #process = (jobtest_add.si(ops) | chain(*g1) | jobtest_sum.si(ops))
    process = (jobtest_add.si(ops) | group(*g1) | jobtest_sum.si(ops) | jobtest_sum2.si(ops))
    
    task = process.delay()
    return True

@task_manager.task(bind=True, base=JobTask)
@job_task(module='ResourceModule')
def jobtest_add(self, options):
    """Test job add x and y.
    Read x and y from shared data. Write mul in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    """
    data = self.get_shared_data()
    x = data[u'x']
    y = data[u'y']
    res = x + y
    
    # save data. Shared data must be re-kept before save modification because 
    # concurrent tasks can change its content during task elaboration 
    data = self.get_shared_data()    
    data[u'mul'] = res
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'add %s' % data)
    return res

@task_manager.task(bind=True, base=JobTask)
@job_task(module='ResourceModule')
def jobtest_sum(self, options):
    """Test job sum numbers.
    Read mul_numbers from shared data. Write res in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    """
    res = 0
    data = 0
    numbers = []
    while data is not None:
        numbers.append(data)
        res += int(data)        
        data = self.pop_stack_data()
    
    # save data. Shared data must be re-kept before save modification because 
    # concurrent tasks can change its content during task elaboration 
    data = self.get_shared_data()
    data[u'res'] = res
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'sum %s' % numbers)
    return res

@task_manager.task(bind=True, base=JobTask)
@job_task(module='ResourceModule')
def jobtest_sum2(self, options):
    """Test job sum numbers.
    Read mul_numbers from shared data. Write res in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    """
    '''
    data = self.get_shared_data()
    numbers = data[u'mul_numbers']
    res = sum(numbers)
    
    # save data. Shared data must be re-kept before save modification because 
    # concurrent tasks can change its content during task elaboration 
    data = self.get_shared_data()
    data[u'res'] = res
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'sum2 %s' % data)'''
    #raise Exception('prova')
    self.update(u'SUCCESS')
    return True

@task_manager.task(bind=True, base=JobTask)
@job_task(module='ResourceModule')
def jobtest_mul(self, options, index):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    :param index: index of item in numbers list
    """
    data = self.get_shared_data()
    numbers = data[u'numbers']
    mul = data[u'mul']
    res = numbers[index] * mul
    self.update(u'PROGRESS', msg=u'mul %s' % numbers)
    
    #gevent.sleep(random.randint(1, 3))
    
    # save data. Shared data must be re-kept before save modification because 
    # concurrent tasks can change its content during task elaboration 
    '''data = self.get_shared_data()    
    data[u'mul_numbers'].append(res)   
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'mul %s' % numbers)'''
    
    self.push_stack_data(res)
    self.update(u'PROGRESS', msg=u'Push item %s to stack' % res)
    
    return res