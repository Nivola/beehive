# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import ujson as json
from six import b
from beehive.common.task.manager import task_manager
from beecell.simple import str2uni, truncate
from datetime import datetime
from time import time, sleep
from celery.utils.log import get_task_logger
from celery.result import AsyncResult, GroupResult
from celery.signals import task_prerun, task_postrun, task_failure
from traceback import format_tb


logger = get_task_logger(__name__)

# job operation
try:
    import gevent
    task_local = gevent.local.local()
except BaseException:
    import threading
    task_local = threading.local()


class TaskResult(object):
    @staticmethod
    def get_from_redis_with_retry(task_id, max_retry=3, delay=0.1):
        """Get task from redis

        :param task_id: task id
        :param max_retry: max get retry if value is None [default=3]
        :param delay: time to wait between two retry [default=0.01]
        :return: task dict result or None
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        _prefix = task_manager.conf['CELERY_REDIS_RESULT_KEY_PREFIX']

        def get_data(task_id):
            key = '%s%s' % (_prefix, task_id)
            task_data = _redis.get(key)
            return task_data

        retry = 0
        while retry < max_retry:
            task_data = get_data(task_id)
            if task_data is not None:
                task_data = json.loads(task_data)
                return task_data
            sleep(delay)
            retry += 1

        return None

    @staticmethod
    def set_to_redis_with_retry(task_id, value):
        """Set task to redis

        :param task_id: task id
        :param value: task result
        :return: task dict result or None
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        _prefix = task_manager.conf['CELERY_REDIS_RESULT_KEY_PREFIX']
        _expire = task_manager.conf['CELERY_REDIS_RESULT_EXPIRES']
        key = '%s%s' % (_prefix, task_id)

        # serialize data
        data = json.dumps(value)

        # save data
        _redis.setex(key, _expire, data)

        return value

    @staticmethod
    def get(task_id):
        """Get task result from redis

        :param task_id: task id
        :return: task dict info or None
        """
        val = TaskResult.get_from_redis_with_retry(task_id)
        if val is None:
            val = {'type': None, 'status': None}
        return val

        # _redis = task_manager.api_manager.redis_taskmanager.conn
        # _prefix = task_manager.conf['CELERY_REDIS_RESULT_KEY_PREFIX']
        #
        # # get data from redis
        # val = _redis.get(_prefix + task_id)
        # result = {'type': None, 'status': None}
        # if val is not None:
        #     result = json.loads(val)
        # return result

    @staticmethod
    def store(task_id, name=None, hostname=None, args=None, kwargs=None, status=None, retval=None, start_time=None,
              stop_time=None, childs=None, traceback=None, inner_type=None, msg=None, jobs=None, counter=None,
              failure=False):
        """Store task result in redis
        """
        _redis = task_manager.api_manager.redis_taskmanager.conn
        _prefix = task_manager.conf['CELERY_REDIS_RESULT_KEY_PREFIX']
        _expire = task_manager.conf['CELERY_REDIS_RESULT_EXPIRES']

        data = {'task_id': task_id}

        def set_data(key, value):
            if value is not None:
                data[key] = value

        set_data('name', name)
        set_data('type', inner_type)
        set_data('worker', hostname)
        set_data('args', args)
        set_data('kwargs', kwargs)
        set_data('status', status)
        set_data('result', retval)
        set_data('start_time', start_time)
        set_data('stop_time', stop_time)
        set_data('children', childs)
        set_data('jobs', jobs)
        set_data('traceback', traceback)
        set_data('counter', counter)

        def update_data():
            # get data from redis
            # key = '%s%s' % (_prefix, task_id)

            # get data from redis
            result = TaskResult.get_from_redis_with_retry(task_id)

            # try:
            #     val = _redis.get(key)
            # except:
            #     logger.warn('', exc_info=1)
            #     val = None

            if result is not None:
                # result = json.loads(val)
                if result.get('status') != 'FAILURE':
                    result.update(data)
                else:
                    result.update({'stop_time': stop_time})

                # check job already present in task jobs list
                val_jobs = result.get('jobs', [])
                if val_jobs is None:
                    result['jobs'] = []
                    val_jobs = []
                if jobs is not None:
                    for job in jobs:
                        if job not in val_jobs:
                            result['jobs'].append(job)

            else:
                result = {
                    'name': name,
                    'type': inner_type,
                    'task_id': task_id,
                    'worker': hostname,
                    'args': args,
                    'kwargs': kwargs,
                    'status': status,
                    'result': retval,
                    'traceback': traceback,
                    'start_time': time(),
                    # 'start_time': start_time,
                    'stop_time': stop_time,
                    'children': childs,
                    'jobs': jobs,
                    'counter': 0,
                    'trace': []}

            # update task trace
            if msg is not None:
                # msg1 = '(%s) %s' % (task_id, msg)
                msg1 = msg
                if failure is True:
                    msg1 = 'ERROR %s' % msg1
                else:
                    msg1 = 'DEBUG %s' % msg1
                _timestamp = str2uni(datetime.today().strftime('%d-%m-%y %H:%M:%S-%f'))
                result['trace'].append((_timestamp, msg1))

            # save data
            val = TaskResult.set_to_redis_with_retry(task_id, result)

            return val

        val = update_data()

        if inner_type == 'JOB':
            logger.debug2('Save %s %s result: %s' % (inner_type, task_id, truncate(val, size=400)))

        return data

    @staticmethod
    def task_pending(task_id):
        # store task
        # start_time = time()
        start_time = None
        task = TaskResult.store(task_id, name=None, hostname=None, args=None, kwargs=None, status='PENDING',
                                retval=None, start_time=start_time, stop_time=0, childs=[], traceback=None,
                                inner_type=None, msg=None, jobs=None, counter=0)
        return task

    @staticmethod
    def task_prerun(**args):
        # store task
        task = args.get('task')
        task_id = args.get('task_id')
        vargs = args.get('args')
        kwargs = args.get('kwargs')

        # store task
        TaskResult.store(task_id, name=task.name, hostname=task.request.hostname, args=vargs, kwargs=kwargs,
                         status='STARTING', retval=None, childs=[], traceback=None,
                         inner_type=getattr(task, 'inner_type', None), msg=None, jobs=None)

    @staticmethod
    def task_postrun(**args):
        task = args.get('task')
        task_id = args.get('task_id')
        vargs = args.get('args')
        kwargs = args.get('kwargs')
        status = args.get('state')
        retval = args.get('retval')

        # get task childrens
        childrens = task.request.children
        chord = task.request.chord

        childs = []
        jobs = []

        # get chord callback task
        chord_callback_task = None
        if chord is not None:
            chord_callback_task = chord['options'].get('task_id', None)
            childs.append(chord_callback_task)

        if len(childrens) > 0:
            for c in childrens:
                if isinstance(c, AsyncResult):
                    child_task = TaskResult.get(c.id)
                    if child_task['type'] == 'JOB':
                        jobs.append(c.id)
                    else:
                        childs.append(c.id)
                elif isinstance(c, GroupResult):
                    for i in c:
                        childs.append(i.id)

        # get task stop_time
        stop_time = time()

        # set retval to None when failure occurs
        if status == 'FAILURE':
            retval = None

        # when RETRY store PROGRESS and ignore retval
        if status == 'RETRY':
            retval = None
            status = 'PROGRESS'

        # reset status for JOB task to PROGRESS when status is SUCCESS
        # status SUCCESS will be set when the last child task end
        inner_type = getattr(task, 'inner_type', None)
        if inner_type == 'JOB' and status == 'SUCCESS':
            status = 'PROGRESS'

        # store task
        TaskResult.store(task_id, name=task.name, hostname=task.request.hostname, args=vargs, kwargs=kwargs,
                         status=status, retval=retval, start_time=None, stop_time=stop_time, childs=set(childs),
                         traceback=None, inner_type=inner_type, msg=None, jobs=jobs)

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
        task_id = args.get('task_id')
        exception = args.get('exception')
        kwargs = args.get('kwargs')
        kwargs = args.get('kwargs')
        traceback = args.get('traceback')
        einfo = args.get('einfo')

        # set status
        status = 'FAILURE'

        # get task stop_time
        stop_time = time()

        # get exception info
        err = b(exception)
        trace = format_tb(einfo.tb)
        trace.append(err)

        # store task
        TaskResult.store(task_id, name=None, hostname=None, args=None, kwargs=None, status=status, retval=None,
                         start_time=None, stop_time=stop_time, childs=None, traceback=trace, inner_type=None, msg=err,
                         jobs=None, failure=True)


# @task_prerun.connect
# def task_prerun(**args):
#     TaskResult.task_prerun(**args)
#
#
# @task_postrun.connect
# def task_postrun(**args):
#     TaskResult.task_postrun(**args)
#
#
# @task_failure.connect
# def task_failure(**args):
#     TaskResult.task_failure(**args)
