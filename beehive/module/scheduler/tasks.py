'''
Created on Nov 3, 2015

@author: darkbk
'''
import ujson as json
from celery import Celery
from celery.utils.log import get_task_logger
from celery import chain, chord, group, signature
from time import time
from .manager import task_manager
from functools import wraps
from celery import Task
from beecell.simple import id_gen, truncate, get_value
from beecell.simple import import_class, str2uni
from datetime import datetime
from celery.result import AsyncResult, GroupResult
from traceback import format_tb
from celery.signals import after_task_publish, task_prerun, task_postrun, \
                           task_success, task_failure, task_retry, task_revoked, \
                           before_task_publish
from beehive.common.data import operation
from beehive.common.apimanager import ApiManagerError, ApiEvent
from beehive.module.scheduler.controller import TaskManager

logger = get_task_logger(__name__)

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

def get_task_result(task_id):
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

def store_task_result(task_id, name=None, hostname=None, args=None, kwargs=None, 
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
    #store_task_result(task_id, task.name, task.request.hostname, args, kwargs, 
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
    store_task_result(task_id, task.name, task.request.hostname, vargs, kwargs, 
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
                child_task = get_task_result(c.id)
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
    if task.inner_type == u'JOB' and \
       task_local.opid == task_id and \
       state == u'SUCCESS':
        state = u'PROGRESS'
    
    # store task
    store_task_result(task_id, task.name, task.request.hostname, vargs, kwargs, 
                      state, retval, None, duration, set(childs), jobs=jobs)

@task_failure.connect
def task_failure(**kwargs):
    pass
    
@task_retry.connect
def task_retry(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_retry] %s' % kwargs)
    
@task_revoked.connect
def task_revoked(**kwargs):
    logger.warn('$$$$$$$$$$$$$ [task_revoked] %s' % kwargs)



#
# multi purpose tasks
#
@task_manager.task(bind=True, base=JobTask)
@job_task(module='SchedulerModule')
def join_task(self, options):
    """Use this task as join task befor/after a group in the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    self.update(u'PROGRESS')
    return None

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def end_task(self, options):
    """Use this task to close the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    self.update(u'SUCCESS')
    return None

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def start_task(self, options):
    """Use this task to close the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    self.update(u'PROGRESS')
    return None

@task_manager.task(bind=True, base=BaseTask, name='tasks.test')
def test(self):
    logger.info('Start %s' % self.name)
    #sleep(2)
    logger.info('Stop %s' % self.name)
    #raise Exception('eee')
    return True

#
# test job
#
@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, job_name=u'manager.jobtest_simple.insert', 
     module=u'SchedulerModule', delta=1)
def jobtest_simple(self, objid, params):
    """Test job
    
    :param objid: objid of the task manager. Ex. 110//2222//334//*
    :param params: task input params  
    """
    ops = self.get_options()
    self.set_shared_data(params)
    
    create_job([
        test_end,
        test_hello
    ], ops).delay()
    return True

@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, job_name=u'manager.jobtest.add.insert', 
     module=u'SchedulerModule', delta=1)
def jobtest(self, objid, params):
    """Test job
    
    :param objid: objid of the cloud domain. Ex. 110//2222//334//*
    :param params: task input params 
                    {u'x':.., u'y':.., u'numbers':[], u'mul_numbers':[], 
                     u'error':True}
    """
    ops = self.get_options()
    self.set_shared_data(params)
    
    numbers = params[u'numbers']
    g1 = []
    for i in range(0,len(numbers)):
        g1.append(test_mul.si(ops, i))
    if params[u'error'] is True:
        g1.append(test_raise.si(ops, i))
    
    g1.append(test_invoke_job.si(ops))

    #process = (test_add.si(ops) | chain(*g1) | test_sum.si(ops))
    '''process = (test_add.si(ops) |
               chord(g1, join_task.si(ops)) | (
               jobtest_sum.si(ops) |
               jobtest_sum2.si(ops))
              )'''
    '''
    t1 = jobtest_sum.si(ops)
    t1.link(jobtest_sum2.si(ops))
    #join = join_task.si(ops)
    #join.link(t1)
    c1 = chord(g1, t1)
    process = jobtest_add.si(ops)
    process.link(c1)'''
    
    create_job([
        test_sum2,
        test_sum,
        g1,
        test_add
    ], ops).delay()
    return True

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_add(self, options):
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
    logger.warn(data)
    self.update(u'PROGRESS', msg=u'add %s' % data)
    return res

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_sum(self, options):
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
@job_task(module=u'SchedulerModule')
def test_sum2(self, options):
    """Test job sum numbers.
    Read mul_numbers from shared data. Write res in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    """
    data = self.get_shared_data()
    numbers = data[u'mul_numbers']
    res = sum(numbers)
    
    # save data. Shared data must be re-kept before save modification because 
    # concurrent tasks can change its content during task elaboration 
    data = self.get_shared_data()
    data[u'res'] = res
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'sum2 %s' % data)
    #raise Exception('prova')
    self.update(u'SUCCESS')
    return True


@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_invoke_job(self, options):
    """Test job jovoke another job
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    """
    params = self.get_shared_data()
    data = (u'*', params)
    user = {
        u'user':operation.user[0], 
        u'server':operation.user[1], 
        u'identity':operation.user[2]
    }
    job = jobtest_simple.apply_async(data, user)
    job_id = job.id
    self.update(u'PROGRESS')
    
    # - wait job complete
    resp = self.wait_for_job_complete(job_id)
    self.update(u'PROGRESS', msg=u'Job %s completed' % job_id)

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_mul(self, options, index):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    :param index: index of item in numbers list
    """
    data = self.get_shared_data()
    logger.warn(data)
    numbers = data[u'numbers']
    mul = data[u'mul']
    res = numbers[index] * mul
    self.update(u'PROGRESS', msg=u'mul %s' % numbers)
    self.push_stack_data(res)
    self.update(u'PROGRESS', msg=u'Push item %s to stack' % res)
    
    return res

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_raise(self, options, index):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    :param index: index of item in numbers list
    """
    raise Exception('iiii')

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_hello(self, options):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    :param index: index of item in numbers list
    """
    params = self.get_shared_data()
    if params[u'error'] is True:
        logger.error(u'Test error')
        raise Exception(u'Test error')
    logger.warn(u'hello')
    return True

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
def test_end(self, options):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param options: tupla that must contain (class_name, objid, job, job id, 
                                             start time, time before new query)
    :param index: index of item in numbers list
    """
    self.update(u'SUCCESS')
    return True
