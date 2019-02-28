"""
Created on May 16, 2017

@author: darkbk
"""
import ujson as json
from beehive.common.task.manager import task_manager
from beecell.simple import str2uni, truncate
from datetime import datetime
from time import time
from celery.utils.log import get_task_logger
from celery.result import AsyncResult, GroupResult
from celery.signals import task_prerun, task_postrun, task_failure, before_task_publish, task_retry, task_revoked
from traceback import format_tb
from celery.utils import static

logger = get_task_logger(__name__)

# job operation
try:
    import gevent
    task_local = gevent.local.local()
except:
    import threading
    task_local = threading.local()


class TaskResult(object):
    @staticmethod
    def get(task_id):
        """Get task result from redis
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        _prefix = task_manager.conf[u'CELERY_REDIS_RESULT_KEY_PREFIX']
        
        # get data from redis
        val = _redis.get(_prefix + task_id)
        result = {u'type': None, u'status': None}
        if val is not None:
            result = json.loads(val)
        return result
    
    @staticmethod
    def store(task_id, name=None, hostname=None, args=None, kwargs=None, status=None, retval=None, start_time=None,
              stop_time=None, childs=None, traceback=None, inner_type=None, msg=None, jobs=None, counter=None,
              failure=False):
        """Store task result in redis
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        # _legacy_prefix = u'celery-task-meta-'
        _prefix = task_manager.conf[u'CELERY_REDIS_RESULT_KEY_PREFIX']
        _expire = task_manager.conf[u'CELERY_REDIS_RESULT_EXPIRES']
        
        data = {u'task_id': task_id}
        
        def set_data(key, value):
            if value is not None:
                data[key] = value
        
        set_data(u'name', name)
        set_data(u'type', inner_type)
        set_data(u'worker', hostname)
        set_data(u'args', args)
        set_data(u'kwargs', kwargs)
        set_data(u'status', status)
        set_data(u'result', retval)
        set_data(u'start_time', start_time)
        set_data(u'stop_time', stop_time)
        set_data(u'children', childs)
        set_data(u'jobs', jobs)
        set_data(u'traceback', traceback)
        set_data(u'counter', counter)
        
        def update_data():
            # create pipe
            # pipe = _redis.pipeline()

            # get data from redis
            # logger.debug(u'prefix: %s, task_id: %s' % (_prefix, task_id))
            key = u'%s%s' % (_prefix, task_id)
            try:
                val = _redis.get(key)
            except:
                logger.warn(u'', exc_info=1)
                val = None

            if val is not None:
                result = json.loads(val)
                if result.get(u'status') != u'FAILURE':
                    # val_counter = int(data.get(u'counter', 0)) + 1
                    result.update(data)
                    # result[u'counter'] = val_counter
                else:
                    result.update({u'stop_time': stop_time})

                # check job already present in task jobs list
                val_jobs = result.get(u'jobs', [])
                if val_jobs is None:
                    result[u'jobs'] = []
                    val_jobs = []
                if jobs is not None:
                    for job in jobs:
                        if job not in val_jobs:
                            result[u'jobs'].append(job)

            else:
                result = {
                    u'name': name,
                    u'type': inner_type,
                    u'task_id': task_id,
                    u'worker': hostname,
                    u'args': args,
                    u'kwargs': kwargs,
                    u'status': status,
                    u'result': retval,
                    u'traceback': traceback,
                    u'start_time': time(),
                    u'stop_time': stop_time,
                    u'children': childs,
                    u'jobs': jobs,
                    u'counter': 0,
                    u'trace': []}
            
            # update task trace
            if msg is not None:
                if failure is True:
                    msg1 = u'ERROR - %s' % msg
                else:
                    msg1 = u'DEBUG - %s' % msg
                _timestamp = str2uni(datetime.today().strftime(u'%d-%m-%y %H:%M:%S-%f'))
                result[u'trace'].append((_timestamp, msg1))
            
            # serialize data
            val = json.dumps(result)
            
            # save data in redis
            _redis.setex(key, _expire, val)

            # check key exists
            val_redis = _redis.get(key)

            # resave data in redis if key does not exist
            if val_redis is None:
                _redis.setex(key, _expire, val)

            return val

        val = update_data()
        
        logout = logger.debug2
        if inner_type == u'JOB':
            logout = logger.info
            logout(u'Save %s %s result: %s' % (inner_type, task_id, truncate(val, size=400)))

        return data

    @staticmethod
    def task_pending(task_id):
        # store task
        start_time = time()
        task = TaskResult.store(task_id, name=None, hostname=None, args=None, kwargs=None, status=u'PENDING',
                                retval=None, stop_time=0, childs=[], traceback=None,
                                inner_type=None, msg=None, jobs=None, counter=0)
        return task

    @staticmethod
    def task_prerun(**args):
        # store task
        task = args.get(u'task')
        task_id = args.get(u'task_id')
        vargs = args.get(u'args')
        kwargs = args.get(u'kwargs')
        
        # store task
        TaskResult.store(task_id, name=task.name, hostname=task.request.hostname, args=vargs, kwargs=kwargs,
                         status=u'STARTING', retval=None, childs=[], traceback=None, inner_type=task.inner_type,
                         msg=None, jobs=None)
    
    @staticmethod
    def task_postrun(**args):
        task = args.get(u'task')
        task_id = args.get(u'task_id')
        vargs = args.get(u'args')
        kwargs = args.get(u'kwargs')
        status = args.get(u'state')
        retval = args.get(u'retval')
        
        # get task childrens
        childrens = task.request.children
        chord = task.request.chord
        
        childs = []
        jobs = []
        
        # get chord callback task
        chord_callback_task = None
        if chord is not None:
            chord_callback_task = chord[u'options'].get(u'task_id', None)
            childs.append(chord_callback_task)
        
        if len(childrens) > 0:
            for c in childrens:
                if isinstance(c, AsyncResult):
                    child_task = TaskResult.get(c.id)
                    if child_task[u'type'] == u'JOB':
                        jobs.append(c.id)
                    else:
                        childs.append(c.id)
                elif isinstance(c, GroupResult):
                    for i in c:
                        childs.append(i.id)
    
        # get task stop_time
        stop_time = time()

        logger.debug(u'POST RUN =============== task_id: %s status %s' % (task_id, status))
        # set retval to None when failure occurs
        if status == u'FAILURE':
            retval = None

        # when RETRAY store PROGRESS and ignore retval
        if status == u'RETRY':
            retval = None
            status = u'PROGRESS'

        # reset status for JOB task to PROGRESS when status is SUCCESS
        # status SUCCESS will be set when the last child task end
        # if task.inner_type == u'JOB' and task_local.opid == task_id and \
        #   status == u'SUCCESS':
        if task.inner_type == u'JOB' and status == u'SUCCESS':
            status = u'PROGRESS'
        
        # store task
        TaskResult.store(task_id, name=task.name, hostname=task.request.hostname, args=vargs, kwargs=kwargs,
                         status=status, retval=retval, start_time=None, stop_time=stop_time, childs=set(childs),
                         traceback=None, inner_type=task.inner_type, msg=None, jobs=jobs)

    @staticmethod
    def task_failure(**args):
        """Dispatched when a task fails.
        Sender is the task object executed.
    
        Provides arguments:
        - task_id: Id of the task.
        - exception: Exception instance raised.
        - args: Positional arguments the task was called with.
        - kwargs: Keyword arguments the task was called with.
        - traceback: Stack trace object.
        - einfo: The billiard.einfo.ExceptionInfo instance.
        """
        task_id = args.get(u'task_id')
        exception = args.get(u'exception')
        kwargs = args.get(u'kwargs')
        kwargs = args.get(u'kwargs')
        traceback = args.get(u'traceback')
        einfo = args.get(u'einfo')
        
        # set status
        status = u'FAILURE'
        
        # get task stop_time
        stop_time = time()        
        
        # get exception info
        err = str(exception)
        trace = format_tb(einfo.tb)
        trace.append(err)    
    
        # store task
        TaskResult.store(task_id, name=None, hostname=None, args=None, kwargs=None, status=status, retval=None,
                         start_time=None, stop_time=stop_time, childs=None, traceback=trace, inner_type=None, msg=err,
                         jobs=None, failure=True)


# @before_task_publish.connect
# def before_task_publish(**args):
#     logger.warn(u'--------------------------')
#     logger.warn(args)

@task_prerun.connect
def task_prerun(**args):
    TaskResult.task_prerun(**args)


@task_postrun.connect
def task_postrun(**args):
    TaskResult.task_postrun(**args)


@task_failure.connect
def task_failure(**args):
    TaskResult.task_failure(**args)


'''
@task_failure.connect
def task_failure(**args):
    """Dispatched when a task fails.
    Sender is the task object executed.

    Provides arguments:
    - task_id: Id of the task.
    - exception: Exception instance raised.
    - args: Positional arguments the task was called with.
    - kwargs: Keyword arguments the task was called with.
    - traceback: Stack trace object.
    - einfo: The billiard.einfo.ExceptionInfo instance.
    """
    task_id = args.get(u'task_id')
    exception = args.get(u'exception')
    kwargs = args.get(u'kwargs')
    kwargs = args.get(u'kwargs')
    traceback = args.get(u'traceback')
    einfo = args.get(u'einfo')
    
    # set status
    status = u'FAILURE'
    
    # get exception info
    err = str(exception)
    trace = format_tb(einfo.tb)
    trace.append(err)    

    # store task
    TaskResult.store(task_id, name=None, hostname=None, 
                     args=None, kwargs=None, status=status, retval=None, 
                     start_time=None, stop_time=None, childs=None, 
                     traceback=trace, inner_type=None, msg=err, jobs=None)    
    
@task_retry.connect
def task_retry(**kwargs):
    logger.warn(u'[task_retry] %s' % kwargs)
    
@task_revoked.connect
def task_revoked(**kwargs):
    logger.warn(u'[task_revoked] %s' % kwargs)
'''