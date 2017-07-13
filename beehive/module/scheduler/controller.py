# -*- coding: utf-8 -*-
'''
Created on Nov 14, 2015

@author: darkbk
'''
import ujson as json
from datetime import datetime, timedelta
import pickle
#from beecell.perf import watch
from beecell.simple import str2uni, id_gen, get_attrib, truncate
from redis_collections import Dict
from celery.schedules import crontab
from celery.result import AsyncResult
from networkx import DiGraph
from networkx.readwrite import json_graph
from beehive.common.apimanager import ApiController, ApiObject, ApiManagerError
from beehive.module.scheduler.redis_scheduler import RedisScheduleEntry
from beehive.common.task.manager import task_scheduler, task_manager
from time import time
from functools import wraps
from beehive.common.data import trace

class SchedulerController(ApiController):
    """Scheduler Module controller.
    """    
    version = u'v1.0'    
    
    def __init__(self, module):
        ApiController.__init__(self, module)

        self.child_classes = [Scheduler, TaskManager]
        
    def add_service_class(self, name, version, service_class):
        self.service_classes.append(service_class)

    '''
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        # register all child class
        for child_class in self.child_classes:
            child_class(self).init_object()'''

    def get_task_manager(self):
        return TaskManager(self)
        
    def get_scheduler(self):
        return Scheduler(self)        
        
class Scheduler(ApiObject):
    objtype = u'task'
    objdef = u'Scheduler'
    objdesc = u'Scheduler'
    
    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid='', name='', desc='', active='')
        try:
            self._prefix = task_scheduler.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX
            self._redis = self.controller.redis_scheduler.conn
            self._pickler = pickle
            self.objid = '*'
            
            # create or get dictionary from redis
            self.redis_entries = Dict(key=self._prefix, 
                                      redis=self._redis)            
        except:
            pass

    @trace(op=u'schedule.insert')
    def create_update_entry(self, name, task, schedule, args=None, kwargs=None, 
                            options=None, relative=None):
        """Create scheduler entry.
        
        :param name: entry name
        :param task: The name of the task to execute.
        :param schedule: The frequency of execution. This can be the number of 
                         seconds as an integer, a timedelta, or a crontab. 
                         You can also define your own custom schedule types, 
                         by extending the interface of schedule.
                        {'type':'crontab',
                         'minute':0,
                         'hour':4,
                         'day_of_week':'*',
                         'day_of_month':None,
                         'month_of_year':None}
                        {'type':} 
        :param args: Positional arguments (list or tuple).
        :param kwargs: Keyword arguments (dict).
        :param options: Execution options (dict). This can be any argument 
                        supported by apply_async(), e.g. exchange, routing_key, 
                        expires, and so on.
        :param relative: By default timedelta schedules are scheduled “by the 
                         clock”. This means the frequency is rounded to the 
                         nearest second, minute, hour or day depending on the 
                         period of the timedelta.
                         If relative is true the frequency is not rounded and 
                         will be relative to the time when celery beat was started.
        :return: 
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions(u'insert')
        
        try:
            if schedule['type'] == 'crontab':
                minute = get_attrib(schedule, 'minute', '*')
                hour = get_attrib(schedule, 'hour', '*')
                day_of_week = get_attrib(schedule, 'day_of_week', '*')
                day_of_month = get_attrib(schedule, 'day_of_month', '*')
                month_of_year = get_attrib(schedule, 'month_of_year', '*')                
                schedule = crontab(minute=minute, 
                                   hour=hour, 
                                   day_of_week=day_of_week, 
                                   day_of_month=day_of_month, 
                                   month_of_year=month_of_year)
            elif schedule['type'] == 'timedelta':
                days = get_attrib(schedule, 'days', 0)
                seconds = get_attrib(schedule, 'seconds', 0)
                minutes = get_attrib(schedule, 'minutes', 0)
                hours = get_attrib(schedule, 'hours', 0)
                weeks = get_attrib(schedule, 'weeks', 0)
                schedule = timedelta(days=days, 
                                     seconds=seconds, 
                                     minutes=minutes, 
                                     hours=hours, 
                                     weeks=weeks)
            
            # new entry
            entry = {
                'task': task,
                'schedule': schedule,
            }
            
            if args is not None:
                entry['args'] = args
            if options is not None:
                entry['options'] = options
            if kwargs is not None:
                entry['kwargs'] = kwargs
            if relative is not None:
                entry['relative'] = relative
                
            # insert entry in redis
            self.redis_entries[name] = RedisScheduleEntry(**dict(entry, name=name, 
                                                                 app=task_scheduler))
            
            self.logger.info("Create scheduler entry: %s" % entry)
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
        
    @trace(op=u'schedules.view')
    def get_entries(self, name=None):
        """Get scheduler entries.
        
        :param name: entry name
        :return: list of (name, entry data) pairs.
        :rtype: list
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions(u'view')
        
        try:
            if name is not None:
                entries = [(name, self.redis_entries.get(name))]
            else:
                entries = self.redis_entries.items()
            
            self.logger.info("Get scheduler entries: %s" % entries)
            return entries
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=404)
        
    @trace(op=u'schedule.delete')
    def remove_entry(self, name):
        """Remove scheduler entry.
        
        :param name: entry name
        :return: 
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions(u'delete')
        
        try:
            del self.redis_entries[name]
            self.logger.info("Remove scheduler entry: %s" % name)
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
        
    @trace(op=u'schedules.delete')
    def clear_all_entries(self):
        """Clear all scheduler entries.
        
        :param name: entry name
        :return: 
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`  
        """
        self.verify_permisssions(u'delete')
        
        try:
            res = self.redis_entries.clear()
            self.logger.info("Remove all scheduler entries")
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)        
        self.redis_entries.clear()
        
class TaskManager(ApiObject):
    objtype = u'task'
    objdef = u'Manager'
    objdesc = u'Task Manager'
    
    prefix = 'celery-task-meta2'
    prefix_base = 'celery-task-meta'
    
    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid='', name='', desc='', active='')
        self.control = task_manager.control.inspect()
        self.objid = '*'
        
        #print i.memdump()
        #print i.memsample()
        #print i.objgraph()
        
    @trace(op=u'use')
    def ping(self, id=None):
        """Ping all task manager workers.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(u'use')
        
        try:
            res = task_manager.control.ping(timeout=0.5)
            self.logger.debug('Ping task manager workers: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)        
        
    @trace(op=u'use')
    def stats(self):
        """Get stats from all task manager worker
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(u'use')
        
        try:
            res = self.control.stats()
            self.logger.debug('Get task manager workers stats: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op=u'use')
    def report(self):
        """Get manager worker report
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        
        self.verify_permisssions(u'use')
        try:
            res = self.control.report()#.split('/n')
            self.logger.debug('Get task manager report: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)       
    
    @trace(op=u'definitions.view')
    def get_registered_tasks(self):
        """Get task definitions
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(u'view')
        
        try:
            res = self.control.registered()
            self.logger.debug(u'Get registered tasks: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(u'No registered tasks found')
            return []
    
    '''
    @trace(op=u'view')
    def get_active_tasks(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = self.control.active()
            self.logger.debug(u'Get active tasks: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(u'No active tasks found')
            return []

    @trace(op=u'view')
    def get_scheduled_tasks(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = self.control.scheduled()
            self.logger.debug(u'Get scheduled tasks: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(u'No scheduled tasks found')
            return []
        
    @trace(op=u'view')
    def get_reserved_tasks(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = self.control.reserved()
            self.logger.debug(u'Get reserved tasks: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(u'No reserved tasks found')
            return []
        
    @trace(op=u'view')
    def get_revoked_tasks(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = self.control.revoked()
            self.logger.debug(u'Get revoked tasks: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(u'No revokes tasks found')
            return []
    '''

    @trace(op=u'tasks.view')
    def get_all_tasks(self, details=False):
        """Get all task of type TASK and JOB. Inner job task are not returned.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(u'view')
        
        try:
            res = []
            manager = self.controller.redis_taskmanager
            keys = manager.inspect(pattern=self.prefix+u'*', debug=False)
            if details is False:
                for key in keys:
                    key = key[0].lstrip(self.prefix+'-')
                    res.append(key)
            else:
                data = manager.query(keys, ttl=True)
                for key, item in data.iteritems():
                    val = json.loads(item[0])
                    ttl = item[1]
                    
                    tasktype = val[u'type']
                    val.pop(u'trace')
                    
                    # add time to live
                    val[u'ttl'] = ttl
                    
                    # add elapsed
                    val[u'elapsed'] = val[u'stop_time'] - val[u'start_time']
                    val[u'stop_time'] = self.__convert_timestamp(val[u'stop_time'])
                    val[u'start_time'] = self.__convert_timestamp(val[u'start_time'])                    
                    
                    # task status
                    #if tasktype == 'JOB':
                    #    status = self.query_chain_status(tid)[2]            

                    if tasktype in [u'JOB', u'TASK']:
                        res.append(val)
                        #res = AsyncResult(key, app=task_manager).get()
            
                    # sort task by date
                    res = sorted(res, key=lambda task: task[u'start_time'])
            
            self.logger.debug(u'Get all tasks: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op=u'tasks-count.view')
    def count_all_tasks(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions(u'view')
        
        try:
            res = []
            manager = self.controller.redis_taskmanager
            res = len(manager.inspect(pattern=self.prefix+u'*', debug=False))
            
            self.logger.debug(u'Count all tasks: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    def __convert_timestamp(self, timestamp):
        """
        """
        timestamp = datetime.fromtimestamp(timestamp)
        return str2uni(timestamp.strftime(u'%d-%m-%Y %H:%M:%S.%f'))        

    def _get_task_info(self, task_id):
        """ """
        manager = self.controller.redis_taskmanager
        keys = manager.inspect(pattern=self.prefix+u'-'+task_id, debug=False)
        data = manager.query(keys, ttl=True)[self.prefix+u'-'+task_id]
        # get task info and time to live
        val = json.loads(data[0])
        ttl = data[1]
        
        # add time to live
        val[u'ttl'] = ttl
        
        # add elapsed
        val[u'elapsed'] = val[u'stop_time'] - val[u'start_time']
        val[u'stop_time'] = self.__convert_timestamp(val[u'stop_time'])
        val[u'start_time'] = self.__convert_timestamp(val[u'start_time'])
        
        return val

    def _get_task_graph(self, task, graph, index=1):
        """Get task graph.
   
        :return: Dictionary with task node and link
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            child_ids = task[u'children']
            child_index = index + 1
            for child_id in child_ids:
                try:
                    child = self._get_task_info(child_id)
                    if len(child[u'children']) == 0:
                        task_type = u'end'
                    else:
                        task_type = u'inner'
                    graph.add_node(child_id, 
                                   id=child[u'task_id'], 
                                   label=child[u'name'].split(u'.')[-1],
                                   type=task_type,
                                   details=child)
                    graph.add_edge(task[u'task_id'], child_id)
                    
                    # call get_task_graph with task child
                    self._get_task_graph(child, graph, child_index)
                    child_index += 1
                    self.logger.debug(u'Get child task %s' % child_id)
                except:
                    self.logger.warn(u'Child task %s does not exist' % child_id, exc_info=1)
            
            return graph
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
        
    def _get_task_childs(self, childs_index, task):
        """Get task childs.

        :param childs_index: dict with task references
        :param task: task to explore
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            child_ids = task.pop(u'children')
            if child_ids is not None:
                for child_id in child_ids:
                    try:
                        child = self._get_task_info(child_id)
                        
                        if child[u'children'] is not None and \
                           len(child[u'children']) == 0:
                            child[u'inner_type'] = u'end'
                        else:
                            child[u'inner_type']  = u'inner'
                            
                        childs_index[child_id] = child
                        
                        # call get_task_graph with task child
                        self._get_task_childs(childs_index, child)
                    except:
                        self.logger.warn('Child task %s does not exist' % child_id)                        
        except Exception as ex:
            raise ApiManagerError(ex, code=400)        

    @trace(op=u'task.view')
    def query_task(self, task_id):
        """Get task info. If task type JOB return graph composed by all the job 
        childs.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'view')     
        
        try:
            res = []
            manager = self.controller.redis_taskmanager
            keys = manager.inspect(pattern=self.prefix+u'-'+task_id, debug=False)
            data = manager.query(keys, ttl=True)[self.prefix+u'-'+task_id]
        except Exception as ex:
            err = u'Task %s not found' % task_id
            self.logger.error(err)
            raise ApiManagerError(err, code=404)            
            
        try:
            # get task info and time to live
            val = json.loads(data[0])
            ttl = data[1]
            
            tasktype = val[u'type']
            
            # add time to live
            val[u'ttl'] = ttl
            
            # JOB
            if tasktype == u'JOB':
                # add elapsed
                val[u'elapsed'] = val[u'stop_time'] - val[u'start_time']
                val[u'stop_time'] = self.__convert_timestamp(val[u'stop_time'])
                val[u'start_time'] = self.__convert_timestamp(val[u'start_time'])           
                try:
                    # get job childs
                    first_child_id = val.pop(u'children')[0]
                    first_child = self._get_task_info(first_child_id)
                    first_child[u'inner_type'] = u'start'
                    childs_index = {first_child_id:first_child}
                    self._get_task_childs(childs_index, first_child)
                    
                    # sort childs by date
                    childs = sorted(childs_index.values(), 
                                    key=lambda task: task[u'start_time'])
                    
                    # get childs trace
                    trace = []
                    for c in childs:
                        for t in c[u'trace']:
                            trace.append((t[0], c[u'name'], c[u'task_id'], t[1]))
                    # sort trace
                    val[u'trace'] = sorted(trace, key=lambda row: row[0])                
                    val[u'children'] = childs
                except:
                    self.logger.warn(u'', exc_info=1)
                    val[u'children'] = None
            else:
                val[u'children'] = None
                
            res = val
            self.logger.debug(u'Get task %s info: %s' % (task_id, truncate(res)))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    '''
    @trace(op=u'view')
    def query_task_status(self, task_id):
        """Get task status. 
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'view')     
        
        try:
            res = []
            manager = self.controller.redis_taskmanager
            keys = manager.inspect(pattern=self.prefix+u'-'+task_id, debug=False)
            data = manager.query(keys, ttl=True)[self.prefix+u'-'+task_id]
        except Exception as ex:
            err = u'Task %s not found' % task_id
            self.logger.error(err)
            raise ApiManagerError(err, code=404)                    
        
        try:
            # get task status
            res = json.loads(data[0])
            
            self.logger.debug(u'Get task %s status: %s' % (task_id, truncate(res)))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)    
    
    def query_chain_status(self, task_id):
        res = AsyncResult(task_id, app=task_manager)
        state = res.state
        
        if res.failed() is True:
            return task_id, True, state
        
        # get children
        if res.children is not None and len(res.children) > 0:
            c = res.children[0]
            stask_id, failed, state = self.query_chain_status(c.task_id)
            return stask_id, failed, state
        
        return task_id, False, state    '''
    
    '''
    def _query_task_graph_item(self, task_id):
        res = AsyncResult(task_id, app=task_manager)
        
        resp = {u'status':res.state,
                u'result':None, 
                u'traceback':None,
                u'children':[], 
                u'id':task_id,
                u'start_time':None,
                u'type':None,
                u'name':None, 
                u'args':None}
        
        # get children
        if res.children is not None:
            for c in res.children:
                sub = self._query_task_graph_item(c.task_id)
                resp[u'children'].append(sub)
        
        result = res.info
        try: name = result[0]
        except: name = None                    
        try: args = result[1]
        except: args = None
        try: start_time = result[2]
        except: start_time = None
        try: elapsed = result[3]
        except: elapsed = None
        try: tasktype = result[4]
        except: tasktype = None                    
        try: result = result[5]
        except: result = None
        
        resp[u'name'] = name
        resp[u'args'] = args
        resp[u'start_time'] = start_time
        resp[u'elapsed'] = elapsed
        resp[u'type'] = tasktype        
        
        if res.state == u'ERROR':
            resp[u'traceback'] = res.traceback
        elif res.ready() is True:
            resp[u'result'] = result
            
        return resp    '''
    
    @trace(op=u'task-graph.view')
    def get_task_graph(self, task_id):
        """Get job task child graph
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'view')      
        
        try:
            graph_data = None
            manager = self.controller.redis_taskmanager
            keys = manager.inspect(pattern=self.prefix+'-'+task_id, debug=False)
            data = manager.query(keys, ttl=True)[self.prefix+'-'+task_id]
            
            # get task info and time to live
            val = json.loads(data[0])

            childs = val[u'children']
            tasktype = val[u'type']
            
            # JOB
            if tasktype == 'JOB':
                # create graph
                graph = DiGraph(name="Task %s child graph" % val[u'name'])
                # populate graph
                child = self._get_task_info(childs[0])
                graph.add_node(child[u'task_id'], 
                               id=child[u'task_id'], 
                               label=child[u'name'].split(u'.')[-1],
                               type=u'start',
                               details=child)                
                self._get_task_graph(child, graph)
                # get graph
                graph_data = json_graph.node_link_data(graph)
            else:
                raise Exception('Task %s is not of type JOB' % task_id)

            res = graph_data
            self.logger.debug('Get task %s graph: %s' % (task_id, truncate(res)))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op=u'tasks.delete')
    def purge_tasks(self):
        """Discard all waiting tasks.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = task_manager.control.purge()
            self.logger.debug(u'Purge waiting task: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
    
    @trace(op=u'tasks.delete')
    def delete_task_instances(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'delete')
        
        try:
            res = []
            manager = self.controller.redis_taskmanager
            res = manager.delete(pattern=self.prefix+'*')
            
            self.logger.debug(u'Purge all tasks: %s' % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
        
        self.manager.delete(pattern=self.prefix+'*')    
    
    def _delete_task_child(self, task_id):
        """Delete task child instances from result db.
        """
        manager = self.controller.redis_taskmanager
        
        res = AsyncResult(task_id, app=task_manager)
        
        # get children
        if res.children is not None:
            for c in res.children:
                self._delete_task_child(c.task_id)
                task_name = 'celery-task-meta-%s' % c.task_id
                res = manager.delete(pattern=task_name)
                self.logger.debug('Delete task instance %s: %s' % (c.task_id, res))
        return True
    
    @trace(op=u'task.delete')
    def delete_task_instance(self, task_id, propagate=True):
        """Delete task instance result from results db.
        
        :param task_id: id of the task instance
        :param propagate: if True delete all the childs
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'delete')        
        
        try:
            # delete childs
            if propagate is True:
                self._delete_task_child(task_id)
            
            # delete task instance
            manager = self.controller.redis_taskmanager
            task_name = u'celery-task-meta-%s' % task_id
            res = manager.delete(pattern=task_name)
            self.logger.debug('Delete task instance %s: %s' % (task_id, res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
    
    '''
    @trace(op=u'view')
    def revoke_task(self, task_id):
        """Tell all (or specific) workers to revoke a task by id.
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = task_manager.control.revoke(task_id, 
                                              terminate=True, 
                                              signal='SIGKILL')
            self.logger.debug('Revoke task %s: %s' % (task_id, res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
        
    @trace(op=u'view')
    def time_limit_task(self, task_name, limit):
        """Tell all (or specific) workers to set time limits for a task by type.
        
        :param task_name: type of task
        :param limit: time limit to set
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            res = task_manager.control.time_limit(task_name, limit)
            self.logger.debug('Set task %s time limit: %s' % (task_name, res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)'''

    @trace(op=u'view')
    def get_active_queue(self):
        """
        
        :return: 
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'view')        
        
        try:
            res = self.control.active_queues()
            self.logger.debug('Get task manager active queue: %s' % (res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=404)
        
    #
    # test jobs
    #
    @trace(op=u'task.test.insert')
    def run_jobtest(self, params):
        """Run jobtest task

        :param params: task input params
                        
                        {u'x':.., 
                         u'y':.., 
                         u'numbers':[], 
                         u'mul_numbers':[]}      
        
        :return: celery task instance
        :rtype: Task
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            None, u'insert')
        
        from beehive.module.scheduler.tasks import jobtest

        data = (self.objid, params)
        job = jobtest.apply_async(data, self.get_user())
        return job    