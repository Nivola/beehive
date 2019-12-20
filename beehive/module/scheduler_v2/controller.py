# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from uuid import uuid4

import ujson as json
from datetime import datetime, timedelta

from celery.result import AsyncResult

from beecell.db.manager import RedisManagerError
from beecell.db.util import QueryError
from beecell.simple import str2uni, get_attrib, truncate, import_class, format_date
from celery.schedules import crontab
from networkx import DiGraph
from networkx.readwrite import json_graph
from beehive.common.apimanager import ApiController, ApiObject, ApiManagerError
from beehive.module.scheduler.redis_scheduler import RedisScheduleEntry, RedisScheduler
from beehive.common.task.manager import task_scheduler, task_manager
from beehive.common.data import trace, operation
from beehive.common.task.canvas import signature
from beehive.module.scheduler_v2.model import SchedulerDbManager


class SchedulerController(ApiController):
    """Scheduler v2.0 Module controller.

    :param module: ApiModule instance
    """
    def __init__(self, module):
        ApiController.__init__(self, module)

        self.version = 'v2.0'
        self.child_classes = [Scheduler, TaskManager]

        self.manager = SchedulerDbManager()
        
    def add_service_class(self, name, version, service_class):
        self.service_classes.append(service_class)

    def get_task_manager(self):
        return TaskManager(self)
        
    def get_scheduler(self):
        return Scheduler(self)        


class Scheduler(ApiObject):
    """Scheduler v2.0 task scheduler class.

    :param controller: SchedulerController instance
    """
    module = 'SchedulerModuleV2'
    objtype = 'task'
    objdef = 'Scheduler'
    objdesc = 'Scheduler'
    
    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid='', name='', desc='', active='')
        try:
            # self._prefix = task_scheduler.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX
            # # self._redis = task_scheduler.conf.CELERY_SCHEDULE_BACKEND
            # self._redis = self.controller.redis_scheduler.conn
            # self._pickler = pickle
            # self.objid = '*'
            # # create or get dictionary from redis
            # self.redis_entries = Dict(key=self._prefix, redis=self._redis)

            self.objid = '*'
            self.scheduler = RedisScheduler(task_scheduler, lazy=True)
            self.scheduler.set_redis(self.controller.redis_scheduler)
        except:
            self.logger.warn('', exc_info=1)

    @trace(op='insert')
    def create_update_entry(self, name, task, schedule, args=None, kwargs=None, options={}, relative=None):
        """Create scheduler entry

        :param name: schedule name
        :param task: task name
        :param schedule: schedule config
        :param args: positional args
        :param kwargs: key value args
        :param options: task options
        :param relative: relative
        :return: {'schedule': <schdule_name>}
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.verify_permisssions('insert')

        try:
            # new entry
            entry = {
                'name': name,
                'task': task,
                'schedule': schedule,
                'options': options
            }

            if args is not None:
                entry['args'] = args
            if kwargs is not None:
                entry['kwargs'] = kwargs
            if relative is not None:
                entry['relative'] = relative

            # insert entry in redis
            res = self.scheduler.write_schedule(entry)

            self.logger.info('Create scheduler entry: %s' % entry)
            return {'schedule': name}
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    # @trace(op='insert')
    # def create_update_entry2(self, name, task, schedule, args=None, kwargs=None, options=None, relative=None):
    #     """Create scheduler entry.
    #
    #     :param name: entry name
    #     :param task: The name of the task to execute.
    #     :param schedule: The frequency of execution. This can be the number of
    #                      seconds as an integer, a timedelta, or a crontab.
    #                      You can also define your own custom schedule types,
    #                      by extending the interface of schedule.
    #                     {'type':'crontab',
    #                      'minute':0,
    #                      'hour':4,
    #                      'day_of_week':'*',
    #                      'day_of_month':None,
    #                      'month_of_year':None}
    #                     {'type':}
    #     :param args: Positional arguments (list or tuple).
    #     :param kwargs: Keyword arguments (dict).
    #     :param options: Execution options (dict). This can be any argument
    #                     supported by apply_async(), e.g. exchange, routing_key,
    #                     expires, and so on.
    #     :param relative: By default timedelta schedules are scheduled “by the
    #                      clock”. This means the frequency is rounded to the
    #                      nearest second, minute, hour or day depending on the
    #                      period of the timedelta.
    #                      If relative is true the frequency is not rounded and
    #                      will be relative to the time when celery beat was started.
    #     :return:
    #     :rtype:
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     self.verify_permisssions('insert')
    #
    #     try:
    #         if schedule['type'] == 'crontab':
    #             minute = get_attrib(schedule, 'minute', '*')
    #             hour = get_attrib(schedule, 'hour', '*')
    #             day_of_week = get_attrib(schedule, 'day_of_week', '*')
    #             day_of_month = get_attrib(schedule, 'day_of_month', '*')
    #             month_of_year = get_attrib(schedule, 'month_of_year', '*')
    #             schedule = crontab(minute=minute,
    #                                hour=hour,
    #                                day_of_week=day_of_week,
    #                                day_of_month=day_of_month,
    #                                month_of_year=month_of_year)
    #         elif schedule['type'] == 'timedelta':
    #             days = get_attrib(schedule, 'days', 0)
    #             seconds = get_attrib(schedule, 'seconds', 0)
    #             minutes = get_attrib(schedule, 'minutes', 0)
    #             hours = get_attrib(schedule, 'hours', 0)
    #             weeks = get_attrib(schedule, 'weeks', 0)
    #             schedule = timedelta(days=days,
    #                                  seconds=seconds,
    #                                  minutes=minutes,
    #                                  hours=hours,
    #                                  weeks=weeks)
    #
    #         # new entry
    #         entry = {
    #             'task': task,
    #             'schedule': schedule,
    #             'options': {'queue': task_scheduler.conf.CELERY_TASK_DEFAULT_QUEUE}
    #         }
    #
    #         if args is not None:
    #             entry['args'] = args
    #         if options is not None:
    #             entry['options'] = options
    #         if kwargs is not None:
    #             entry['kwargs'] = kwargs
    #         if relative is not None:
    #             entry['relative'] = relative
    #
    #         # insert entry in redis
    #         self.redis_entries[name] = RedisScheduleEntry(**dict(entry, name=name, app=task_scheduler))
    #
    #         self.logger.info("Create scheduler entry: %s" % entry)
    #         return {'schedule': name}
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=400)
        
    @trace(op='view')
    def get_entries(self, name=None):
        """Get scheduler entries.
        
        :param name: entry name
        :return: list of (name, entry data) pairs.
        :rtype: list
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions('view')
        
        try:
            entries = self.scheduler.read_schedule(name)
            self.logger.info('Get scheduler entries: %s' % entries)
            return entries
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op='delete')
    def remove_entry(self, name):
        """Remove scheduler entry.

        :param name: entry name
        :return: True
        :rtype: bool
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('delete')

        try:
            res = self.scheduler.delete_schedule(name)
            self.logger.info('Remove scheduler entry: %s' % name)
            return True
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    # @trace(op='delete')
    # def remove_entry2(self, name):
    #     """Remove scheduler entry.
    #
    #     :param name: entry name
    #     :return: True
    #     :rtype: bool
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     self.verify_permisssions('delete')
    #
    #     try:
    #         self.logger.warn(self.redis_entries)
    #         del self.redis_entries[name]
    #         self.logger.warn(self.redis_entries)
    #         self.logger.info('Remove scheduler entry: %s' % name)
    #         return True
    #     except Exception as ex:
    #         self.logger.error(ex)
    #         raise ApiManagerError(ex, code=400)
        
    @trace(op='delete')
    def clear_all_entries(self):
        """Clear all scheduler entries.
        
        :param name: entry name
        :return: True
        :rtype: bool
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions('delete')
        
        try:
            self.redis_entries.clear()
            self.logger.info('Remove all scheduler entries')
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)


class TaskManager(ApiObject):
    """Scheduler v2.0 task maanager class.

    :param controller: SchedulerController instance
    """
    module = 'SchedulerModuleV2'
    objtype = 'task'
    objdef = 'Manager'
    objdesc = 'Task Manager'

    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid='', name='', desc='', active='')

        self.objid = '*'
        try:
            self.hostname = self.celery_broker_queue + '@' + self.api_manager.server_name
            # self.control = task_manager.control.inspect([self.hostname])
            self.prefix = task_manager.conf.CELERY_REDIS_RESULT_KEY_PREFIX
            self.prefix_base = 'celery-task-meta'
        except:
            self.control = None
            self.prefix = ''
            self.prefix_base = ''

        self.expire = float(self.api_manager.params.get('expire', 0))

        # print i.memdump()
        # print i.memsample()
        # print i.objgraph()
        
    @trace(op='use')
    def ping(self):
        """Ping all task manager workers.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('use')
        
        try:
            control = task_manager.control
            # res = control.ping([self.hostname], timeout=1.0)
            res = control.ping(timeout=1.0)
            self.logger.debug('Ping task manager workers: %s' % res)
            resp = {}
            for item in res:
                resp.update(item)
            return resp
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)        
        
    @trace(op='use')
    def stats(self):
        """Get stats from all task manager worker
        
        :return: usage info
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('use')
        
        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.stats()
            self.logger.debug('Get task manager workers stats: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op='use')
    def report(self):
        """Get manager worker report
        
        :return: report info
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        
        self.verify_permisssions('use')
        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.report()
            self.logger.debug('Get task manager report: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op='use')
    def get_active_queues(self):
        """Ping all task manager active queues.

        :return: active queue
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('use')

        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.active_queues()
            self.logger.debug('Get task manager active queues: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op='view')
    def get_registered_tasks(self):
        """Get task definitions
        
        :return: registered tasks
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('view')
        
        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.registered()
            if res is None:
                res = []
            self.logger.debug('Get registered tasks: %s' % res)
            return res
        except Exception as ex:
            self.logger.error('No registered tasks found')
            return []

    @trace(op='view')
    def get_tasks(self, *args, **kvargs):
        """Get tasks.

        :param entity_class: entity_class owner of the tasks to query
        :param task_id: task id
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of :class:`Task`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = []
        tags = []

        objdef = None
        objtype = None
        entity_class = kvargs.pop('entity_class')
        if entity_class is not None:
            entity_class = import_class(entity_class)
            objdef = entity_class.objdef
            objtype = entity_class.objtype

        if operation.authorize is True:
            try:
                # use base permission over task manager - admin
                self.verify_permisssions('view')
                with_perm_tag = False
            except:
                if entity_class is None:
                    raise ApiManagerError('entity_class must be specified')

                # use permission for a specific objtype:objdef - user
                with_perm_tag = True

                # verify permissions
                objs = self.controller.can(u'view', objtype=objtype, definition=objdef)

                # create permission tags
                for entity_def, ps in objs.items():
                    for p in ps:
                        tags.append(self.manager.hash_from_permission(entity_def.lower(), p))
                self.logger.debug(u'Permission tags to apply: %s' % truncate(tags))
        else:
            with_perm_tag = False
            self.logger.debug(u'Auhtorization disabled for command')

        try:
            entities, total = self.manager.get_tasks(tags=tags, with_perm_tag=with_perm_tag, *args, **kvargs)

            for entity in entities:
                obj = Task(self.controller, oid=entity.id, objid=entity.objid, name=entity.name, model=entity)
                res.append(obj)

            self.logger.info(u'Get tasks (total:%s): %s' % (total, truncate(res)))
            return res, total
        except QueryError as ex:
            self.logger.warn(ex, exc_info=1)
            return [], 0

    @trace(op='view')
    def get_task(self, task_id, entity_class_name=None):
        """Get task

        :param entity_class_name: entity_class owner of the tasks to query
        :param task_id: task id
        :return: :class:`Task` instance
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        tasks, tot = self.get_tasks(entity_class=entity_class_name, task_id=task_id)
        if tot == 0:
            raise ApiManagerError('task %s of entity %s does not exist' % (task_id, entity_class_name))
        return tasks[0]

    @trace(op='view')
    def get_task_status(self, task_id, entity_class_name=None):
        """Get task

        :param entity_class_name: entity_class owner of the tasks to query
        :param task_id: task id
        :return: :class:`Task` instance
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # get first task status from celery task stored in celery backend
        task = AsyncResult(task_id, app=task_manager)
        status = task.status
        self.logger.debug('get task from celery: %s' % task)

        # when celery task is removed from celery backend for key elapsed use task from db
        tasks, tot = self.get_tasks(entity_class=entity_class_name, task_id=task_id)
        if tot == 1:
            task = tasks[0]
            status = task.status
            self.logger.debug('get task from database: %s' % task)

        res = {'uuid': task_id, 'status': status}
        return res

    # @trace(op='view')
    # def get_all_tasks(self, elapsed=60, ttype=None, details=False):
    #     """Get all task of type TASK and JOB. Inner job task are not returned.
    #
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     self.verify_permisssions('view')
    #
    #     try:
    #         res = []
    #         manager = self.controller.redis_taskmanager
    #         keys1 = manager.inspect(pattern=self.prefix+'*', debug=False)
    #         self.logger.debug('Get all %s keys form redis' % len(keys1))
    #
    #         keys = []
    #         for k in keys1:
    #             if self.expire - float(k[2]) < elapsed:
    #                 keys.append(k)
    #
    #         self.logger.debug('Get filtered %s keys form redis' % len(keys))
    #
    #         if details is False:
    #             for key in keys:
    #                 key = key[0].lstrip(self.prefix+'-')
    #                 res.append(key)
    #         else:
    #             data = manager.query(keys, ttl=True)
    #             for key, item in data.items():
    #                 try:
    #                     val = json.loads(item[0])
    #                 except:
    #                     val = {}
    #                 ttl = item[1]
    #
    #                 tasktype = val.get('type', None)
    #                 val.pop('trace', None)
    #
    #                 # add time to live
    #                 val['ttl'] = ttl
    #
    #                 # add elapsed
    #                 stop_time = val.get('stop_time', 0)
    #                 start_time = val.get('start_time', 0)
    #                 elapsed = 0
    #                 stop_time_str = 0
    #                 if start_time is not None and stop_time is not None:
    #                     elapsed = stop_time - start_time
    #                     stop_time_str = self.__convert_timestamp(stop_time)
    #
    #                 # add elapsed
    #                 val['elapsed'] = elapsed
    #                 val['stop_time'] = stop_time_str
    #                 val['start_time'] = self.__convert_timestamp(start_time)
    #
    #                 # task status
    #                 available_ttypes = ['JOB', 'JOBTASK', 'TASK']
    #                 ttypes = available_ttypes
    #
    #                 if ttype is not None and ttype in available_ttypes:
    #                     ttypes = [ttype]
    #
    #                 if tasktype in ttypes:
    #                     res.append(val)
    #
    #                 # sort task by date
    #                 res = sorted(res, key=lambda task: task['start_time'])
    #
    #         self.logger.debug('Get all tasks: %s' % truncate(res))
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=404)
    #
    # @trace(op='view')
    # def count_all_tasks(self):
    #     """
    #
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     self.verify_permisssions('view')
    #
    #     try:
    #         res = []
    #         manager = self.controller.redis_taskmanager
    #         res = len(manager.inspect(pattern=self.prefix+'*', debug=False))
    #
    #         self.logger.debug('Count all tasks: %s' % res)
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex)
    #         raise ApiManagerError(ex, code=400)
    #
    # def __convert_timestamp(self, timestamp):
    #     """
    #     """
    #     if isinstance(timestamp, float):
    #         timestamp = datetime.fromtimestamp(timestamp)
    #         return str2uni(timestamp.strftime('%d-%m-%Y %H:%M:%S.%f'))
    #     return ''
    #
    # def __get_redis_task(self, task_id):
    #     """Get task from redis
    #
    #     :param task_id: redis key
    #     :return: task data
    #     :raise ApiManagerError: if task was not found
    #     """
    #     try:
    #         manager = self.controller.redis_taskmanager
    #         task_data, task_ttl = manager.get_with_ttl(self.prefix + task_id, max_retry=3, delay=0.01)
    #     except RedisManagerError as ex:
    #         raise ApiManagerError('Task %s not found' % task_id, code=404)
    #
    #     return task_data, task_ttl
    #
    # def _get_task_info(self, task_id):
    #     """ """
    #     manager = self.controller.redis_taskmanager
    #     # keys = manager.inspect(pattern=self.prefix + task_id, debug=False)
    #     # data = manager.query(keys, ttl=True)[self.prefix + task_id]
    #     task_data, task_ttl = self.__get_redis_task(task_id)
    #
    #     # get task info and time to live
    #     # val = json.loads(data[0])
    #     # ttl = data[1]
    #     val = json.loads(task_data)
    #     ttl = task_ttl
    #
    #     # add time to live
    #     val['ttl'] = ttl
    #
    #     # add elapsed
    #     stop_time = val.get('stop_time', 0)
    #     start_time = val.get('start_time', 0)
    #     elapsed = 0
    #     stop_time_str = 0
    #     if start_time is not None and stop_time is not None:
    #         elapsed = stop_time - start_time
    #         stop_time_str = self.__convert_timestamp(stop_time)
    #
    #     # add elapsed
    #     val['elapsed'] = elapsed
    #     val['stop_time'] = stop_time_str
    #     val['start_time'] = self.__convert_timestamp(start_time)
    #     # val['trace'] = None
    #
    #     # get child jobs
    #     jobs = val.get('jobs', [])
    #     job_list = []
    #     if jobs is not None and len(jobs) > 0:
    #         for job in jobs:
    #             job_list.append(self.query_task(job))
    #     val['jobs'] = job_list
    #     return val
    #
    # def _get_task_graph(self, task, graph, index=1):
    #     """Get task graph.
    #
    #     :return: Dictionary with task node and link
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     try:
    #         child_ids = task['children']
    #         child_index = index + 1
    #         for child_id in child_ids:
    #             try:
    #                 child = self._get_task_info(child_id)
    #                 if len(child['children']) == 0:
    #                     task_type = 'end'
    #                 else:
    #                     task_type = 'inner'
    #                 graph.add_node(child_id,
    #                                id=child['task_id'],
    #                                label=child['name'].split('.')[-1],
    #                                type=task_type,
    #                                details=child)
    #                 graph.add_edge(task['task_id'], child_id)
    #
    #                 # call get_task_graph with task child
    #                 self._get_task_graph(child, graph, child_index)
    #                 child_index += 1
    #                 self.logger.debug('Get child task %s' % child_id)
    #             except:
    #                 self.logger.warn('Child task %s does not exist' % child_id, exc_info=1)
    #
    #         return graph
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=400)
    #
    # def _get_task_childs(self, childs_index, task):
    #     """Get task childs.
    #
    #     :param childs_index: dict with task references
    #     :param task: task to explore
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     try:
    #         child_ids = task.pop('children')
    #         self.logger.debug2('Get task %s children: %s' % (task['task_id'], child_ids))
    #         if child_ids is not None:
    #             for child_id in child_ids:
    #                 try:
    #                     if child_id in childs_index:
    #                         continue
    #
    #                     child = self._get_task_info(child_id)
    #                     childs_index[child_id] = child
    #                     self._get_task_childs(childs_index, child)
    #                 except:
    #                     self.logger.warn('Child task %s does not exist' % child_id)
    #     except Exception as ex:
    #         raise ApiManagerError(ex, code=400)
    #
    # @trace(op='view')
    # def query_task(self, task_id, chain=True):
    #     """Get task info. If task type JOB return graph composed by all the job childs.
    #
    #     :param task_id: id of the celery task
    #     :param chain: if True get all task chain
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     # verify permissions
    #     self.verify_permisssions('view')
    #
    #     res = []
    #     task_data, task_ttl = self.__get_redis_task(task_id)
    #
    #     try:
    #         # get task info and time to live
    #         val = json.loads(task_data)
    #         ttl = task_ttl
    #
    #         tasktype = val.get('type', 'JOB')
    #
    #         # add time to live
    #         val['ttl'] = ttl
    #
    #         # JOB
    #         if tasktype == 'JOB':
    #             stop_time = val.get('stop_time', 0)
    #             start_time = val.get('start_time', 0)
    #             elapsed = 0
    #             stop_time_str = 0
    #             if start_time is not None and stop_time is not None:
    #                 elapsed = stop_time - start_time
    #                 stop_time_str = self.__convert_timestamp(stop_time)
    #
    #             # add elapsed
    #             val['elapsed'] = elapsed
    #             val['stop_time'] = stop_time_str
    #             val['start_time'] = self.__convert_timestamp(start_time)
    #
    #             if chain is True:
    #                 try:
    #                     # get job childs
    #                     childrens = val.pop('children', [])
    #                     if len(childrens) > 0:
    #                         first_child_id = childrens[0]
    #                         first_child = self._get_task_info(first_child_id)
    #                         first_child['inner_type'] = 'start'
    #                         childs_index = {first_child_id: first_child}
    #                         self._get_task_childs(childs_index, first_child)
    #
    #                         # sort childs by date
    #                         childs = sorted(childs_index.values(), key=lambda task: task['start_time'])
    #
    #                         # get childs trace
    #                         trace = []
    #                         for c in childs:
    #                             for t in c.pop('trace'):
    #                                 trace.append((t[0], c['name'], c['task_id'], t[1]))
    #                         # sort trace
    #                         val['trace'] = sorted(trace, key=lambda row: row[0])
    #                         val['children'] = childs
    #                 except:
    #                     self.logger.warn('', exc_info=1)
    #                     val['children'] = None
    #         else:
    #             val['children'] = None
    #
    #         res = val
    #         self.logger.debug('Get task %s info: %s' % (task_id, truncate(res)))
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=400)
    #
    # @trace(op='view')
    # def get_task_graph(self, task_id):
    #     """Get job task child graph
    #
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     # verify permissions
    #     self.verify_permisssions('view')
    #
    #     graph_data = None
    #
    #     task_data, task_ttl = self.__get_redis_task(task_id)
    #
    #     try:
    #         # get task info and time to live
    #         val = json.loads(task_data)
    #
    #         childs = val['children']
    #         tasktype = val['type']
    #
    #         # JOB
    #         if tasktype == 'JOB':
    #             # create graph
    #             graph = DiGraph(name="Task %s child graph" % val['name'])
    #             # populate graph
    #             child = self._get_task_info(childs[0])
    #             graph.add_node(child['task_id'],
    #                            id=child['task_id'],
    #                            label=child['name'].split('.')[-1],
    #                            type='start',
    #                            details=child)
    #             self._get_task_graph(child, graph)
    #             # get graph
    #             graph_data = json_graph.node_link_data(graph)
    #         else:
    #             raise Exception('Task %s is not of type JOB' % task_id)
    #
    #         res = graph_data
    #         self.logger.debug('Get task %s graph: %s' % (task_id, truncate(res)))
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=404)
    #
    # @trace(op='delete')
    # def delete_task_instances(self):
    #     """
    #
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     # verify permissions
    #     self.verify_permisssions('delete')
    #
    #     try:
    #         res = []
    #         manager = self.controller.redis_taskmanager
    #         res = manager.delete(pattern=self.prefix+'*')
    #
    #         self.logger.debug('Purge all tasks: %s' % res)
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex)
    #         raise ApiManagerError(ex, code=400)
    #
    #     self.manager.delete(pattern=self.prefix+'*')
    #
    # def _delete_task_child(self, task_id):
    #     """Delete task child instances from result db.
    #     """
    #     manager = self.controller.redis_taskmanager
    #
    #     # res = AsyncResult(task_id, app=task_manager)
    #
    #     try:
    #         res = manager.server.get(self.prefix + task_id)
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=404)
    #
    #     # get children
    #     if res is not None:
    #         res = json.loads(res)
    #         childrens = res.get('children', [])
    #         for child_id in childrens:
    #             self._delete_task_child(child_id)
    #             task_name = self.prefix + child_id
    #             res = manager.delete(pattern=task_name)
    #             self.logger.debug('Delete task instance %s: %s' % (child_id, res))
    #     return True
    #
    # @trace(op='delete')
    # def delete_task_instance(self, task_id, propagate=True):
    #     """Delete task instance result from results db.
    #
    #     :param task_id: id of the task instance
    #     :param propagate: if True delete all the childs
    #     :return:
    #     :rtype: dict
    #     :raises ApiManagerError: raise :class:`.ApiManagerError`
    #     """
    #     # verify permissions
    #     self.verify_permisssions('delete')
    #
    #     try:
    #         # delete childs
    #         if propagate is True:
    #             self._delete_task_child(task_id)
    #
    #         # delete task instance
    #         manager = self.controller.redis_taskmanager
    #         task_name = self.prefix + task_id
    #         res = manager.delete(pattern=task_name)
    #         self.logger.debug('Delete task instance %s: %s' % (task_id, res))
    #         return res
    #     except Exception as ex:
    #         self.logger.error(ex, exc_info=1)
    #         raise ApiManagerError(ex, code=400)
        
    #
    # test jobs
    #
    @trace(op='insert')
    def run_test_task(self, params):
        """Run test task

        :param params: task input params {'x':.., 'y':.., 'numbers':[]}
        :return: celery task instance
        :rtype: Task
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, None, 'insert')

        params.update(self.get_user())
        params['objid'] = str(uuid4())
        task = signature('beehive.module.scheduler_v2.tasks.test_task', [params], app=task_manager,
                         queue=self.celery_broker_queue)
        job = task.apply_async()

        return job


class Task(ApiObject):
    module = 'SchedulerModuleV2'
    objtype = 'task'
    objdef = 'Manager'
    objdesc = 'Task'

    def __init__(self, *args, **kvargs):
        ApiObject.__init__(self, *args, **kvargs)

        self.parent = None
        self.worker = None
        self.start_time = None
        self.run_time = None
        self.stop_time = None
        self.result = None
        self.status = None
        self.args = None
        self.kwargs = None
        self.duration = None
        self.api_id = None
        self.server = None
        self.user = None
        self.identity = None
        if self.model is not None:
            self.parent = self.model.parent
            self.worker = self.model.worker
            self.status = self.model.status
            self.start_time = self.model.start_time
            self.run_time = self.model.run_time
            self.stop_time = self.model.stop_time
            self.result = self.model.result
            if isinstance(self.start_time, datetime) and isinstance(self.run_time, datetime):
                self.duration = (self.run_time - self.start_time).total_seconds()

            try:
                self.args = json.loads(self.model.args)[0]
                self.args.pop('objid')
                self.api_id = self.args.pop('api_id')
                self.server = self.args.pop('server')
                self.user = self.args.pop('user')
                self.identity = self.args.pop('identity')
            except:
                self.args = None

            try:
                self.kwargs = json.loads(self.model.kwargs)
            except:
                self.kwargs = None

        self.steps = []
        self.trace = []

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'status': self.status,
            'parent': self.parent,
            'worker': self.worker,
            'api_id': self.api_id,
            'server': self.server,
            'user': self.user,
            'identity': self.identity,
            'start_time': format_date(self.start_time),
            'run_time': format_date(self.run_time),
            'stop_time': format_date(self.stop_time),
            'duration': self.duration
        }
        return res

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'status': self.status,
            'parent': self.parent,
            'worker': self.worker,
            'api_id': self.api_id,
            'server': self.server,
            'user': self.user,
            'identity': self.identity,
            'start_time': format_date(self.start_time),
            'run_time': format_date(self.run_time),
            'stop_time': format_date(self.stop_time),
            'duration': self.duration,
            'result': self.result,
            'args': self.args,
            'kwargs': self.kwargs,
            'steps': self.steps
        }
        return res

    def get_trace(self):
        """Get task trace

        :raise ApiManagerError:
        """
        trace = []
        for t in self.manager.get_trace(self.uuid):
            trace.append({
                'id': str(t.id),
                'step': t.step_id,
                'message': t.message,
                'level': t.level,
                'date': format_date(t.date)
            })
        return trace

    #
    # pre, post function
    #
    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        steps = self.manager.get_steps(self.uuid)
        for s in steps:
            duration = None
            stop_time = None
            if isinstance(s.start_time, datetime) and isinstance(s.run_time, datetime):
                duration = (s.run_time - s.start_time).total_seconds()
                stop_time = format_date(s.stop_time)
            self.steps.append({
                'uuid': s.uuid,
                'name': s.name,
                'status': s.status,
                'result': s.result,
                'start_time': format_date(s.start_time),
                'run_time': format_date(s.run_time),
                'stop_time': stop_time,
                'duration': duration
            })
