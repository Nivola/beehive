# -*- coding: utf-8 -*-
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from uuid import uuid4

import ujson as json
from datetime import datetime
from celery.result import AsyncResult
from beecell.db.util import QueryError
from beecell.simple import truncate, import_class, format_date
from beehive.common.apimanager import ApiController, ApiObject, ApiManagerError
from beehive.common.task_v2 import run_async
from beehive.module.scheduler_v2.redis_scheduler import RedisScheduler
from beehive.common.data import trace, operation
from beehive.common.task_v2.canvas import signature
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

    def get_entity_for_task(self, entity_class, oid, *args, **kvargs):
        """Get single entity usable bya a celery task

        :param entity_class: Controller ApiObject Extension class. Specify when you want to verif match between
            objdef of the required resource and find resource
        :param oid: entity id
        :return: entity instance
        :raise ApiManagerError`:
        """
        if entity_class == TaskManager:
            return self.get_task_manager()
        elif entity_class == Scheduler:
            return self.get_scheduler()


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
            self.objid = '*'
            self.scheduler = None
            if self.task_scheduler is not None:
                self.scheduler = RedisScheduler(self.task_scheduler, lazy=True)
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
            # self.prefix = task_manager.conf.CELERY_REDIS_RESULT_KEY_PREFIX
            # self.prefix_base = 'celery-task-meta'
        except:
            self.control = None
            self.prefix = ''
            self.prefix_base = ''

        self.expire = float(self.api_manager.params.get('expire', 0))

    @trace(op='use')
    def ping(self):
        """Ping all task manager workers.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions('use')
        
        try:
            control = self.task_manager.control
            res = control.ping(timeout=1.0)
            self.logger.debug('Ping task manager workers: %s' % res)
            resp = {}
            for item in res:
                if list(item.keys())[0].find(self.celery_broker_queue) >= 0:
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
            control = self.task_manager.control.inspect(timeout=1.0)
            res = control.stats()
            self.logger.debug('Get task manager workers stats: %s' % res)
            resp = {}
            for k, v in res.items():
                if k.find(self.celery_broker_queue) >= 0:
                    resp[k] = v
            return resp
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
            control = self.task_manager.control.inspect(timeout=1.0)
            res = control.report()
            self.logger.debug('Get task manager report: %s' % res)
            resp = {}
            for k, v in res.items():
                if k.find(self.celery_broker_queue) >= 0:
                    resp[k] = v
            return resp
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
            control = self.task_manager.control.inspect(timeout=1.0)
            res = control.active_queues()
            self.logger.debug('Get task manager active queues: %s' % res)
            resp = {}
            for k, v in res.items():
                if k.find(self.celery_broker_queue) >= 0:
                    resp[k] = v
            return resp
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
            control = self.task_manager.control.inspect(timeout=1.0)
            res = control.registered()
            if res is None:
                res = []
            self.logger.debug('Get registered tasks: %s' % res)
            resp = {}
            for k, v in res.items():
                if k.find(self.celery_broker_queue) >= 0:
                    resp[k] = v
            return resp
        except Exception as ex:
            self.logger.error('No registered tasks found')
            return []

    @trace(op='view')
    def get_tasks(self, *args, **kvargs):
        """Get tasks.

        :param entity_class: entity_class owner of the tasks to query
        :param task_id: task id
        :param objid: authorization id
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
        task = AsyncResult(task_id, app=self.task_manager)
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
        params['alias'] = 'test_task'
        task = signature('beehive.module.scheduler_v2.tasks.test_task', [params], app=self.task_manager,
                         queue=self.celery_broker_queue)
        task_id = task.apply_async()

        return task_id

    @trace(op='insert')
    def run_test_scheduled_action(self, schedule=None):
        """Run test scheduled action

        :param schedule: schedule [optional]
        :return: schedule name
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, None, 'insert')

        if schedule is None:
            schedule = {
                'type': 'timedelta',
                'minutes': 1
            }
        params = {
            'key1': 'value1',
            'steps': [
                # 'beehive.module.scheduler_v2.tasks.ScheduledActionTask.remove_schedule_step',
                'beehive.module.scheduler_v2.tasks.ScheduledActionTask.task_step'
            ]
        }
        schedule_name = self.scheduled_action('test', schedule, params=params)

        return schedule_name

    #
    # inline task step
    #
    @run_async(action='use', alias='test_inline_task')
    def run_test_inline_task(self, params):
        """Run test task

        :param params: task input params {'x': .., 'y': ..}
        :return: test result
        :raises ApiManagerError if query empty return error.
        """
        res = params.get('x') + params.get('y')
        self.logger.debug('test inline task result from params %s: %s' % (params, res))
        return res


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
        self.api_id = None
        if self.model is not None:
            self.parent = self.model.parent
            self.worker = self.model.worker
            self.status = self.model.status
            self.start_time = self.model.start_time
            self.run_time = self.model.run_time
            self.stop_time = self.model.stop_time
            self.result = self.model.result
            self.api_id = self.model.api_id
            if isinstance(self.start_time, datetime) and isinstance(self.run_time, datetime):
                self.duration = (self.run_time - self.start_time).total_seconds()
            try:
                args = self.model.args
                # args = self.model.args[1:-2]
                # args = args.replace('\'', '"').replace('False', 'false').replace('True', 'true').replace('None', 'null')
                self.args = json.loads(args)[0]
                self.args.pop('objid', None)
                self.args.pop('api_id', None)
                self.args.pop('steps', None)
                self.server = self.args.pop('server')
                self.user = self.args.pop('user')
                self.identity = self.args.pop('identity')
                self.alias = self.args.pop('alias', self.name)
            except:
                self.logger.warn('error parsing task %s args %s' % (self.oid, self.model.args), exc_info=True)
                self.args = None
                self.alias = self.name

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
            'alias': self.alias,
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
            'alias': self.alias,
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
        traces = []
        for trace, step in self.manager.get_trace(self.uuid):
            traces.append({
                'id': str(trace.id),
                'step': trace.step_id,
                'step_name': step.name,
                'message': trace.message,
                'level': trace.level,
                'date': format_date(trace.date)
            })
        return traces

    def get_log(self, size=100, page=0, *args, **kwargs):
        """Get task log

        :param page: page number
        :param size: page size
        :return: log list
        :raise ApiManagerError:
        """
        worker_split = self.worker.split('@')
        if len(worker_split) > 1:
            worker = worker_split[1]
        else:
            worker = worker_split[0]
        kwargs = {
            'size': size,
            'page': page,
            'pod': worker,
            'op': '%s::%s:%s' % (self.api_id, self.name.split('.')[-1], self.uuid),
            'date': format_date(self.start_time, format='%Y.%m.%d')
        }
        logs = self.controller.get_log_from_elastic(**kwargs)
        self.logger.debug('get task %s log: %s' % (self.uuid, truncate(logs)))
        return logs

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
