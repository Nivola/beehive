'''
Created on May 16, 2017

@author: darkbk
'''
import ujson as json
from beehive.common.task.manager import task_manager
from beecell.simple import str2uni, truncate
from datetime import datetime
from time import time
from celery.utils.log import get_task_logger
from celery.result import AsyncResult, GroupResult
from celery.signals import task_prerun, task_postrun, task_failure, \
                           task_retry, task_revoked

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
        result = {u'type':None}
        if val is not None:
            result = json.loads(val)
        return result
    
    @staticmethod
    def store(task_id, name=None, hostname=None, args=None, kwargs=None, 
                          state=None, retval=None, timestamp=None, duration=None, 
                          childs=None, traceback=None, inner_type=None, msg=None,
                          jobs=None):
        """Store task result in redis
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        _legacy_prefix = u'celery-task-meta-'
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
        set_data(u'jobs', jobs)
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
                u'jobs':jobs,
                u'trace':[]}
        
        # update task trace
        if msg is not None:
            _timestamp = str2uni(datetime.today().strftime(u'%d-%m-%y %H:%M:%S-%f'))
            result[u'trace'].append((_timestamp, msg))
        
        # serialize data
        val = json.dumps(result)
        # save data in redis
        _redis.setex(_prefix + task_id, _expire, val)
        # save celery legacy data to redis
        if state == u'FAILURE':
            result = {u'exc_message':u'', u'exc_type':u'Exception'}
        else:
            result = True
        val = {u'status':state, u'traceback':u'', u'result':result, 
               u'task_id':task_id, u'children': []}
        _redis.setex(_legacy_prefix + task_id, _expire, json.dumps(val))
        logger.debug(u'Save task %s result: %s' % (task_id, truncate(data)))        
        return val

@task_prerun.connect
def task_prerun(**args):
    # store task
    #TaskResult.store(task_id, task.name, task.request.hostname, args, kwargs, 
    #                  'PENDING', None, None, None, None, None, 
    #                  task.inner_type)
    
    task = args.get(u'task')
    task_id = args.get(u'task_id')
    vargs = args.get(u'args')
    kwargs = args.get(u'kwargs')
    
    # get task timestamp
    _timestamp = str2uni(datetime.today().strftime(u'%d-%m-%y %H:%M:%S-%f'))
    
    # get task initial time
    task.inner_start = time()
    
    # store task
    TaskResult.store(task_id, task.name, task.request.hostname, vargs, kwargs, 
                      u'PENDING', None, _timestamp, None, None, None, 
                      task.inner_type)

@task_postrun.connect
def task_postrun(**args):
    task = args.get(u'task')
    task_id = args.get(u'task_id')
    vargs = args.get(u'args')
    kwargs = args.get(u'kwargs')
    state = args.get(u'state')
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
                    #if i.id != chord_callback_task:
                    childs.append(i.id)

    # get task duration
    duration = round(time() - task.inner_start, 3)

    # set retval to None when failure occurs
    if state == u'FAILURE':
        retval = None

    # reset state for JOB task to PROGRESS when state is SUCCESS
    # state SUCCESS will be set when the last child task end
    if task.inner_type == u'JOB' and task_local.opid == task_id and \
       state == u'SUCCESS':
        state = u'PROGRESS'
    
    # store task
    TaskResult.store(task_id, task.name, task.request.hostname, vargs, kwargs, 
                      state, retval, None, duration, set(childs), jobs=jobs)

@task_failure.connect
def task_failure(**kwargs):
    pass
    
@task_retry.connect
def task_retry(**kwargs):
    logger.warn(u'[task_retry] %s' % kwargs)
    
@task_revoked.connect
def task_revoked(**kwargs):
    logger.warn(u'[task_revoked] %s' % kwargs)