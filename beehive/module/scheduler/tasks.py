# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from gevent import sleep

from beehive.common.apimanager import ApiManagerError
from beehive.common.task.canvas import signature
from celery.utils.log import get_task_logger
from beehive.common.data import operation
from beehive.common.task.job import JobTask, job_task, job, Job
from beehive.common.task.manager import task_manager
from beehive.module.scheduler.controller import TaskManager
from beehive.common.task.util import end_task, start_task, join_task

logger = get_task_logger(__name__)


#
# test job
#
@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, name="test2.insert", delta=1)
def jobtest_inner(self, objid, params):
    """Test job

    :param objid: objid. Ex. 110//2222//334//*
    :param suberror: if True task rise error
    """
    ops = self.get_options()
    self.set_shared_data(params)

    Job.create([end_task, jobtest_task4, start_task], ops).delay()
    return True


@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, name="test.insert", delta=1)
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
    for i in range(0, len(params["numbers"])):
        g1.append(jobtest_task3.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    if params["error"] is True:
        g1.append(test_raise.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))

    g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    # g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    # g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    # g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))
    # g1.append(test_invoke_job.signature((ops, i), immutable=True, queue=task_manager.conf.TASK_DEFAULT_QUEUE))

    j = Job.create(
        [
            end_task,
            jobtest_task2,
            jobtest_task1,
            g1,
            join_task,
            g1,
            jobtest_task0,
            start_task,
        ],
        ops,
    )
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
    x = data["x"]
    y = data["y"]
    res = x + y

    # save data. Shared data must be re-kept before save modification because
    # concurrent tasks can change its content during task elaboration
    data = self.get_shared_data()
    data["mul"] = res
    self.set_shared_data(data)
    self.update("PROGRESS", msg="add %s" % data)
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
    data["res"] = res
    self.set_shared_data(data)
    self.update("PROGRESS", msg="sum %s" % numbers)
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
    data["res"] = data["res"] + 10
    self.set_shared_data(data)
    sleep(5)
    self.update("PROGRESS", msg="%s" % data)
    return True


@task_manager.task(bind=True, base=JobTask)
@job_task()
def test_invoke_job(self, options, i):
    """Test job jovoke another job

    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    params = self.get_shared_data()
    # data = ('*', params)
    user = {
        "user": operation.user[0],
        "server": operation.user[1],
        "identity": operation.user[2],
        "api_id": operation.id,
    }
    # job = jobtest_inner.apply_async(data, **user)

    params.update(user)
    task = signature(
        "beehive.module.scheduler.tasks.jobtest_inner",
        ("*", params),
        app=task_manager,
        queue=task_manager.conf.TASK_DEFAULT_QUEUE,
    )
    job = task.apply_async()

    job_id = job.id
    self.update("PROGRESS")

    # - wait job complete
    resp = self.wait_for_job_complete(job_id)
    self.update("PROGRESS", msg="Job %s completed" % job_id)


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
    numbers = data["numbers"]
    mul = data["mul"]
    res = numbers[index] * mul
    self.update("PROGRESS", msg="mul %s" % numbers)
    self.push_stack_data(res)
    self.update("PROGRESS", msg="Push item %s to stack" % res)

    return res


@task_manager.task(bind=True, base=JobTask)
@job_task()
def test_raise(self, options, i):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.

    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    # raise ApiManagerError('Error in main job')
    raise Exception(ApiManagerError("Error in main job"))


@task_manager.task(bind=True, base=JobTask)
@job_task()
def jobtest_task4(self, options):
    """Test job mul x and y.
    Read numbers and mul from shared data. Write mul_numbers item in shared data.

    :param tupla options: Tupla with some useful options.
        (class_name, objid, job, job id, start time, time before new query, user)
    """
    params = self.get_shared_data()
    if params["suberror"] is True:
        logger.error("Test error in internal job")
        raise ApiManagerError("Test error in internal job")

    res = 0
    for n in range(10000):
        res += n
    sleep(3)
    return res


@task_manager.task(bind=True, base=Job)
@job(entity_class=TaskManager, name="test.insert")
def test(self, objid, params):
    """Test job"""
    ops = self.get_options()
    self.set_shared_data(params)
    logger.warn("warning")
    return True
