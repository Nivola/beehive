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
from beecell.simple import str2bool, truncate

logger = logging.getLogger(__name__)

class SchedulerManager(ApiManager):
    """
    SECTION: 
        scheduler
    
    PARAMS:
        <subsystem> worker ping
        <subsystem> worker stat
        <subsystem> worker report
        <subsystem> tasks definitions         get all the task definitions
        <subsystem> tasks list                get all the task instances
        <subsystem> tasks get <task_id>       get task details
        <subsystem> tasks task <task_id>      get task execution trace
        <subsystem> tasks graph <task_id>     get task execution graph
        <subsystem> tasks test
        <subsystem> tasks delete-all
        <subsystem> tasks delete <task_id>
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

    @staticmethod
    def get_params(args):
        try: subsystem = args.pop(0)
        except:
            raise Exception(u'ERROR : Container id is missing')
        return {u'subsystem':subsystem}

    def actions(self):
        actions = {
            u'worker.ping': self.ping_task_worker,
            u'worker.stat': self.stat_task_worker,
            u'worker.report': self.report_task_worker,
            
            u'tasks.definitions': self.get_task_definitions,
            u'tasks.list': self.get_all_tasks,
            u'tasks.get': self.get_task,
            u'tasks.trace': self.get_task_trace,
            #u'tasks.status': self.get_task_status,
            u'tasks.graph': self.get_task_graph,
            u'tasks.delete-all': self.delete_all_tasks,
            u'tasks.delete': self.delete_task,
            u'tasks.test': self.run_test,
            
            u'schedule.list': self.get_scheduler_entries,
            u'schedule.get': self.get_scheduler_entry,
            u'schedule.add': self.create_scheduler_entries,
            u'schedule.delete': self.delete_scheduler_entry,
        }
        return actions    
    
    #
    # task worker
    #
    def ping_task_worker(self):
        uri = u'/v1.0/worker/ping/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        resp = []
        for r in res:
            resp.append({u'worker':r.keys()[0], u'res':r.values()[0]})
        self.result(resp, headers=[u'worker', u'res'])

    def stat_task_worker(self):
        uri = u'/v1.0/worker/stats/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        resp = []
        for k,v in res.items():
            v[u'worker'] = k
            resp.append(v)        
        self.result(res, details=True)

    def report_task_worker(self):
        uri = u'/v1.0/worker/report/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        resp = []
        for k,v in res.items():
            vals = v.values()[0].split(u'\n')
            row = 0
            for val in vals:
                row += 1
                resp.append({u'worker':u'%s.%s' % (k, row), u'report':val}) 
        self.result(resp, headers=[u'worker', u'report'])
    
    def get_task_definitions(self):
        uri = u'/v1.0/worker/tasks/definitions/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        resp = []
        for k,v in res[u'task-definitions'].items():
            for v1 in v:
                resp.append({u'worker':k, u'task':v1})
        self.result(resp, headers=[u'worker', u'task'])    
    
    def get_all_tasks(self):
        uri = u'/v1.0/worker/tasks/'
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'task-instances', 
                    headers=[u'task_id', u'type', u'status', u'name', 
                             u'start_time', u'stop_time', u'elapsed'])
        
    def get_task(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/' % task_id
        res = self._call(uri, u'GET').get(u'task-instance')
        self.logger.info(res)
        resp = []
        resp.append(res)
        resp.extend(res.get(u'children'))
        self.result(resp, headers=[u'task_id', u'type', u'status', u'name', 
                                  u'start_time', u'stop_time', u'elapsed'])
        
    def get_task_trace(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/' % task_id
        res = self._call(uri, u'GET').get(u'task-instance').get(u'trace')
        self.logger.info(res)
        resp = []
        for i in res:
            resp.append({u'timestamp':i[0], u'task':i[1], u'task id':i[2], 
                         u'msg':truncate(i[3], 150)})
        self.result(resp, headers=[u'timestamp', u'msg'], maxsize=200)        
        
    '''
    def get_task_status(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/status/' % task_id
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)      '''  
        
    def get_task_graph(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/graph/' % task_id
        res = self._call(uri, u'GET').get(u'task-instance-graph')
        self.logger.info(res)
        print(u'Nodes:')
        self.result(res, key=u'nodes', headers=[u'details.task_id', 
                    u'details.type', u'details.status', u'label', 
                    u'details.start_time', u'details.stop_time', 
                    u'details.elapsed'])
        print(u'Links:')
        self.result(res, key=u'links', headers=[u'source', u'target'])        

    '''
    def count_all_tasks(self):
        """TODO"""
        uri = u'/v1.0/worker/tasks/count/'
        
        res = self._call(uri, u'GET')
        self.logger.info(res)
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
        
    def run_test(self, error=False, suberror=False):
        data = {
            u'x':2,
            u'y':234, 
            u'numbers':[2, 78], 
            u'mul_numbers':[],
            u'error':str2bool(error),
            u'suberror':str2bool(suberror)
        }
        uri = u'/v1.0/worker/tasks/test/'
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Run job test: %s' % res)
        self.result(res)
        #self.query_task_status(res[u'jobid'])

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
        self.result({u'msg':u'Create schedule %s' % data}, headers=[u'msg'])

    def delete_scheduler_entry(self, name):
        data = {u'name':name}
        uri = u'/v1.0/scheduler/entry/'
        res = self._call(uri, u'DELETE', data=data)
        self.result({u'msg':u'Delete schedule %s' % name}, headers=[u'msg'])

