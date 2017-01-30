'''
Usage: manage.py [OPTION]... scheduler [PARAMs]...

Scheduler api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    
PARAMS:
    <subsystem> manager ping
    <subsystem> manager stat
    <subsystem> manager report
    <subsystem> tasks list
    <subsystem> task <task_id>
    <subsystem> task test
    <subsystem> task graph <task_id>
    <subsystem> schedule list
    <subsystem> schedule get <schedule_name>
    <subsystem> schedule add <schedule_name> <task> \{\"type\":\"timedelta\",\"minutes\":10\} []
    <subsystem> schedule delete <schedule_name>

Exit status:
 0  if OK,
 1  if problems occurred

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

logger = logging.getLogger(__name__)

class SchedulerManager(ApiManager):
    def __init__(self, auth_config):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/scheduler'
        #self.subsystem = u'scheduler'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'manager.ping': self.ping_task_manager,
            u'manager.stat': self.stat_task_manager,
            u'manager.report': self.report_task_manager,
            u'tasks.list': self.get_all_tasks,
            u'task.get': self.get_task,
            u'task.graph': self.get_task_graph,
            u'tasks.delete': self.delete_all_tasks,
            u'task.delete': self.delete_task,
            u'task.test': self.run_job_test,
            
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
        uri = u'/v1.0/task/ping/'
        res = self._call(uri, u'GET')
        self.msg = res

    def stat_task_manager(self):
        uri = u'/v1.0/task/stats/'
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res

    def report_task_manager(self):
        uri = u'/v1.0/task/report/'
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
    
    def get_all_tasks(self):
        uri = u'/v1.0/task/tasks/'
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
        
    def get_task(self, task_id):
        uri = u'/v1.0/task/task/%s/' % task_id
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
        
    def get_task_graph(self, task_id):
        uri = u'/v1.0/task/task/%s/graph/' % task_id
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res

    def count_all_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/count/'
        
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res

    def registered_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/registered/'
        
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
         
    def active_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/active/'
        
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
        
    def scheduled_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/scheduled/'
        
        res = res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res
        
    def reserved_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/reserved/'
        
        res = res = self._call(uri, u'GET')
        self.msg = res
        
    def revoked_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/revoked/'
        
        res = res = self._call(uri, u'GET')
        self.msg = res
        
    def delete_all_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/'
        
        res = self._call(uri, u'DELETE')
        self.msg = res
        
    def delete_task(self):
        """TODO"""
        uri = u'/v1.0/task/task/%s/' % oid
        
        res = self._call(uri, u'DELETE')       
        
    def purge_tasks(self):
        """TODO"""
        uri = u'/v1.0/task/tasks/purge/'
        
        res = self._call(uri, u'DELETE')
        self.msg = res      

    def revoke_task(self):
        """TODO"""
        uri = u'/v1.0/task/task/revoke/%s/' % task_id
        
        res = self._call(uri, u'DELETE')
        self.msg = res
        
    def run_job_test(self):
        data = {u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]} 
        uri = u'/v1.0/task/task/jobtest/'
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Run job test: %s' % res)
        self.msg = res   

    #
    # scheduler
    #
    def get_scheduler_entries(self):
        uri = u'/v1.0/scheduler/entries/'
        res = self._call(uri, u'GET')
        self.logger.debug(res)
        self.msg = res
        
    def get_scheduler_entry(self, name):
        uri = u'/v1.0/scheduler/entry/%s/' % name
        res = self._call(uri, u'GET')
        self.logger.debug(res)
        self.msg = res        

    def create_scheduler_entries(self, name, task, schedule, args):
        schedule = {
            u'name':name,
            u'task':task,
            u'schedule':json.loads(schedule),
            u'args':args
        }
        uri = u'/v1.0/scheduler/entry/'
        res = self._call(uri, u'POST', data=schedule)
        self.msg = res

    def delete_scheduler_entry(self, name):
        data = {u'name':name}
        uri = u'/v1.0/scheduler/entry/'
        res = self._call(uri, u'DELETE', data=data)
        self.msg = res

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