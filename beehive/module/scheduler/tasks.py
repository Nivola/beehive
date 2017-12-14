'''
Created on Nov 3, 2015

@author: darkbk
'''
from celery import signature
from celery.utils.log import get_task_logger
from beehive.common.data import operation
from beehive.common.task.job import JobTask, job_task, job, Job
from beehive.common.task.manager import task_manager
from beehive.module.scheduler.controller import TaskManager
from beehive.common.task.util import end_task

logger = get_task_logger(__name__)

#
# test job
#
@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, name=u'test2.insert', delta=1)
def jobtest2(self, objid, params):
    """Test job
    
    :param objid: objid. Ex. 110//2222//334//*
    :param suberror: if True task rise error
    """
    ops = self.get_options()
    self.set_shared_data(params)
    
    Job.create([
        end_task,
        jobtest_task4
    ], ops).delay()
    return True


@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, name=u'insert', delta=1)
def jobtest(self, objid, params):
    """Test job
    
    :param objid: objid. Ex. 110//2222//334//*
    :param x: x
    :param y: y
    :param numbers: numbers
    :param error: error
    :param suberror: suberror
    """
    ops = self.get_options()
    self.set_shared_data(params)

    g1 = []
    for i in range(0, len(params[u'numbers'])):
        g1.append(jobtest_task3.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    if params[u'error'] is True:
        g1.append(test_raise.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    
    g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))

    j = Job.create([
        end_task,
        jobtest_task2,
        jobtest_task1,
        g1,
        jobtest_task0
    ], ops)
    j.delay()
    return True


@task_manager.task(bind=True, base=JobTask)
@job_task()
def jobtest_task0(self, options):
    """Test job add x and y. Read x and y from shared data. Write mul in shared data.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
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
@job_task()
def jobtest_task1(self, options):
    """Test job sum numbers.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user))
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
@job_task()
def jobtest_task2(self, options):
    """Test job sum numbers.
    Read mul_numbers from shared data. Write res in shared data.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    data = self.get_shared_data()
    data[u'res'] = data[u'res'] + 10
    self.set_shared_data(data)
    self.update(u'PROGRESS', msg=u'%s' % data)
    return True


@task_manager.task(bind=True, base=JobTask)
@job_task()
def test_invoke_job(self, options, i):
    """Test job jovoke another job
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    params = self.get_shared_data()
    # data = (u'*', params)
    user = {
        u'user': operation.user[0],
        u'server': operation.user[1],
        u'identity': operation.user[2]
    }
    # job = jobtest2.apply_async(data, **user)

    params.update(user)
    task = signature(u'beehive.module.scheduler.tasks.jobtest2', (u'*', params), app=task_manager,
                     queue=task_manager.conf.TASK_DEFAULT_QUEUE)
    job = task.apply_async()

    job_id = job.id
    self.update(u'PROGRESS')
    
    # - wait job complete
    resp = self.wait_for_job_complete(job_id)
    self.update(u'PROGRESS', msg=u'Job %s completed' % job_id)


@task_manager.task(bind=True, base=JobTask)
@job_task()
def jobtest_task3(self, options, index):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    :param index: index of item in numbers list        
    """
    data = self.get_shared_data()
    numbers = data[u'numbers']
    mul = data[u'mul']
    res = numbers[index] * mul
    self.update(u'PROGRESS', msg=u'mul %s' % numbers)
    self.push_stack_data(res)
    self.update(u'PROGRESS', msg=u'Push item %s to stack' % res)
    
    return res


@task_manager.task(bind=True, base=JobTask)
@job_task()
def test_raise(self, options, i):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    raise Exception('iiii')


@task_manager.task(bind=True, base=JobTask)
@job_task()
def jobtest_task4(self, options):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.
    
    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    params = self.get_shared_data()
    if params[u'suberror'] is True:
        logger.error(u'Test error')
        raise Exception(u'Test error')
    logger.warn(u'hello')
    return True
