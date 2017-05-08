'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager
import sys
from beecell.simple import str2bool

logger = logging.getLogger(__name__)

class SchedulerManager(ApiManager):
    """
    SECTION: 
        scheduler
    
    PARAMS:
        <subsystem> manager ping
        <subsystem> manager stat
        <subsystem> manager report
        <subsystem> manager tasks      get available tasks
        <subsystem> tasks list         get all the task instances
        <subsystem> tasks get <task_id>
        <subsystem> tasks test
        <subsystem> tasks graph <task_id>
        <subsystem> schedule list
        <subsystem> schedule get <schedule_name>
        <subsystem> schedule add <schedule_name> <task> \{\"type\":\"timedelta\",\"minutes\":10\} []
        <subsystem> schedule delete <schedule_name>    
    """
    def __init__(self, auth_config, env, frmt, subsystem=None):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/scheduler'
        self.subsystem = subsystem
        self.logger = logger
        self.msg = None
        
        self.sched_headers = [u'name', u'task', u'schedule', u'args', u'kwargs', 
                              u'options', u'last_run_at', u'total_run_count']


    def actions(self):
        actions = {
            u'manager.ping': self.ping_task_manager,
            u'manager.stat': self.stat_task_manager,
            u'manager.report': self.report_task_manager,
            u'manager.tasks': self.registered_tasks,            
            u'tasks.list': self.get_all_tasks,
            u'tasks.get': self.get_task,
            u'tasks.status': self.get_task_status,
            u'tasks.graph': self.get_task_graph,
            u'tasks.delete': self.delete_all_tasks,
            u'tasks.delete': self.delete_task,
            u'tasks.test': self.run_job_test,
            
            u'schedule.list': self.get_scheduler_entries,
            u'schedule.get': self.get_scheduler_entry,
            u'schedule.add': self.create_scheduler_entries,
            u'schedule.delete': self.delete_scheduler_entry,
        }
        return actions    
    
    #
    # task manager
    #
    def ping_task_manager(self):
        uri = u'/v1.0/worker/ping/'
        res = self._call(uri, u'GET')
        self.result(res)

    def stat_task_manager(self):
        uri = u'/v1.0/worker/stats/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def report_task_manager(self):
        uri = u'/v1.0/worker/report/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
    
    def registered_tasks(self):
        uri = u'/v1.0/worker/tasks/registered/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        resp = []
        for k,v in res[u'tasks'].items():
            for v1 in v:
                resp.append({u'worker':k, u'task':v1})
        self.result(resp, headers=[u'worker', u'task'])    
    
    def get_all_tasks(self):
        uri = u'/v1.0/worker/tasks/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'instances', headers=[u'id', u'type', u'state', u'name', u'timestamp'])
        
    def get_task(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/' % task_id
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'instance', headers=[u'id', u'type', u'state', u'name', 
                                  u'timestamp'])
        
    def get_task_status(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/status/' % task_id
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)        
        
    def get_task_graph(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/graph/' % task_id
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    '''
    def count_all_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/count/'
        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def registered_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/registered/'
        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
         
    def active_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/active/'
        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def scheduled_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/scheduled/'
        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def reserved_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/reserved/'
        
        res = self._call(uri, u'GET')
        self.result(res)
        
    def revoked_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/revoked/'
        
        res = self._call(uri, u'GET')
        self.result(res)
        
     
        
    def purge_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/purge/'
        
        res = self._call(uri, u'DELETE')
        self.result(res)      

    def revoke_task(self):
        """TODO"""
        uri = u'/v1.0/manager/tasks/revoke/%s/' % task_id
        
        res = self._call(uri, u'DELETE')
        self.result(res)'''
        
    def delete_all_tasks(self):
        uri = u'/v1.0/worker/tasks/'
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete all task')
        self.result(res)        
        
    def delete_task(self, task_id):
        uri = u'/v1.0/worker/task/%s/' % task_id
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete task %s' % task_id)
        self.result(res)
        
    def run_job_test(self, error=False):
        data = {u'x':2, u'y':234, u'numbers':[2, 78], u'mul_numbers':[],
                u'error':str2bool(error)}
        uri = u'/v1.0/worker/tasks/jobtest/'
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Run job test: %s' % res)
        self.result(res)   

    #
    # scheduler
    #
    def get_scheduler_entries(self):
        uri = u'/v1.0/scheduler/entries/'
        res = self._call(uri, u'GET')
        self.logger.debug(res)
        self.result(res, key=u'schedules', headers=self.sched_headers)
        
    def get_scheduler_entry(self, name):
        uri = u'/v1.0/scheduler/entry/%s/' % name
        res = self._call(uri, u'GET')
        self.logger.debug(res)
        self.result(res, key=u'schedule', headers=self.sched_headers)        

    def create_scheduler_entries(self, data):
        data = self.load_config(data)
        uri = u'/v1.0/scheduler/entry/'
        res = self._call(uri, u'POST', data=data)
        self.result({u'msg':u'Create schedule %s' % data})

    def delete_scheduler_entry(self, name):
        data = {u'name':name}
        uri = u'/v1.0/scheduler/entry/'
        res = self._call(uri, u'DELETE', data=data)
        self.result(res)

def scheduler_main(auth_config, format, opts, args):
    """
    
    :param auth_config: {u'pwd': u'..', 
                         u'endpoint': u'http://10.102.160.240:6060/api/', 
                         u'user': u'admin@local'}
    """
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print __doc__
            return 0
    
    try:
        args[1]
    except:
        print __doc__
        return 0
    
    client = SchedulerManager(auth_config)
    
    actions = client.actions()
    
    subsystem = args.pop(0)
    client.subsystem = subsystem
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else: 
        raise Exception(u'Scheduler entity and/or command are not correct')
        return 1
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Scheduler entity and/or command does not exist')
        return 1
            
    if format == u'text':
        for i in res:
            pass
    else:
        print(u'Scheduler response:')
        print(u'')
        if isinstance(client.msg, dict) or isinstance(client.msg, list):
            client.pp.pprint(client.msg)
        else:
            print(client.msg)
        
    return 0