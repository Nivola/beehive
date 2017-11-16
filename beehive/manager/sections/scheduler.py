'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate, str2bool

logger = logging.getLogger(__name__)

class SchedulerController(BaseController):
    class Meta:
        label = 'scheduler'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Scheduler management"

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Scheduler management", hide=True)
    def default(self):
        self.app.args.print_help()
        
class SchedulerControllerChild(ApiController):
    cataloguri = u'/v1.0/schedulers'
    
    cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                   u'date.creation', u'date.modified']
    end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                   u'service', u'active', 
                   u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'scheduler'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*')),            
            ( ['-s', '--subsystem'],
              dict(action='store', help='beehive subsystem like auth, resource, ..') ),
        ]
    
    @check_error
    def _ext_parse_args(self):
        ApiController._ext_parse_args(self)
        
        self.subsystem = self.app.pargs.subsystem
        if self.subsystem is None:
            raise Exception(u'Subsystem is not specified')
        
class WorkerController(SchedulerControllerChild):    
    class Meta:
        label = 'workers'
        description = "Worker management"
        
    #
    # task worker
    #
    @expose()
    def ping(self):
        """Ping
        """
        uri = u'/v1.0/worker/ping'
        res = self._call(uri, u'GET').get(u'workers_ping', {})
        logger.info(res)
        resp = []
        for k,v in res.items():
            resp.append({u'worker':k, u'res':v})
        self.result(resp, headers=[u'worker', u'res'])

    @expose()
    def stat(self):
        """Stat
        """
        uri = u'/v1.0/worker/stats'
        res = self._call(uri, u'GET').get(u'workers_stats', {})
        logger.info(res)
        resp = []
        for k,v in res.items():
            v[u'worker'] = k
            resp.append(v)        
        self.result(res, details=True)

    @expose()
    def report(self):
        """Report
        """
        uri = u'/v1.0/worker/report'
        res = self._call(uri, u'GET').get(u'workers_report', {})
        logger.info(res)
        resp = []
        for k,v in res.items():
            vals = v.values()[0].split(u'\n')
            row = 0
            for val in vals:
                row += 1
                resp.append({u'worker':u'%s.%s' % (k, row), u'report':val}) 
        self.result(resp, headers=[u'worker', u'report'], maxsize=300)
    
class TaskController(SchedulerControllerChild):    
    class Meta:
        label = 'tasks'
        description = "Task management"
        
    @expose(help="Task management", hide=True)
    def default(self):
        self.app.args.print_help()
        
    @expose()    
    def definitions(self):
        """List all available tasks you can invoke
        """
        uri = u'/v1.0/worker/tasks/definitions'
        res = self._call(uri, u'GET')
        logger.info(res)
        resp = []
        for k,v in res[u'task_definitions'].items():
            for v1 in v:
                resp.append({u'worker':k, u'task':v1})
        self.result(resp, headers=[u'worker', u'task'], maxsize=400)    
    
    @expose()
    def list(self):
        """List all task instance
        """
        uri = u'/v1.0/worker/tasks'
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'task_instances', 
                    headers=[u'task_id', u'type', u'status', u'name', 
                             u'start_time', u'stop_time', u'elapsed'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get task instance by id
        """
        task_id = self.get_arg(name=u'id')
        uri = u'/v1.0/worker/tasks/%s' % task_id
        res = self._call(uri, u'GET').get(u'task_instance')
        logger.info(res)
        resp = []
        resp.append(res)
        resp.extend(res.get(u'children'))
        self.result(resp, headers=[u'task_id', u'type', u'status', u'name', 
                                  u'start_time', u'stop_time', u'elapsed'])
    
    @expose(aliases=[u'trace <id>'], aliases_only=True)
    def trace(self):
        """Get task instance execution trace by id
        """        
        task_id = self.get_arg(name=u'id')
        uri = u'/v1.0/worker/tasks/%s' % task_id
        res = self._call(uri, u'GET').get(u'task_instance').get(u'trace')
        logger.info(res)
        resp = []
        for i in res:
            resp.append({u'timestamp':i[0], u'task':i[1], u'task id':i[2], 
                         u'msg':truncate(i[3], 150)})
        self.result(resp, headers=[u'timestamp', u'msg'], maxsize=200)        
    
    @expose(aliases=[u'graph <id>'], aliases_only=True)
    def graph(self):
        """Get task instance execution graph by id
        """        
        task_id = self.get_arg(name=u'id')
        uri = u'/v1.0/worker/tasks/%s/graph' % task_id
        res = self._call(uri, u'GET').get(u'task_instance_graph')
        logger.info(res)
        print(u'Nodes:')
        self.result(res, key=u'nodes', headers=[u'details.task_id', 
                    u'details.type', u'details.status', u'label', 
                    u'details.start_time', u'details.stop_time', 
                    u'details.elapsed'])
        print(u'Links:')
        self.result(res, key=u'links', headers=[u'source', u'target'])

    @expose()
    def deletes(self):
        """Delete all task instance
        """
        uri = u'/v1.0/worker/tasks'
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete all task')
        res = {u'msg':u'Delete all task'}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete task instance by id
        """             
        task_id = self.get_arg(name=u'id')
        uri = u'/v1.0/worker/tasks/%s' % task_id
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete task %s' % task_id)
        res = {u'msg':u'Delete task %s' % task_id}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'test [error=true/false] [suberror=true/false]'], 
            aliases_only=True)
    def test(self):
        """Run test job
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'x':2,
            u'y':234, 
            u'numbers':[2, 78], 
            u'mul_numbers':[],
            u'error':str2bool(params.get(u'error', False)),
            u'suberror':str2bool(params.get(u'suberror', False))
        }
        uri = u'/v1.0/worker/tasks/test'
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Run job test: %s' % res)
        self.result(res)

class ScheduleController(SchedulerControllerChild):
    sched_headers = [u'name', u'task', u'schedule', u'args', u'kwargs', 
                     u'options', u'last_run_at', u'total_run_count']    
       
    class Meta:
        label = 'schedules'
        description = "Schedule management"
        
    @expose()
    def list(self):
        """List all schedules
        """
        uri = u'/v1.0/scheduler/entries'
        res = self._call(uri, u'GET')
        logger.debug(res)
        self.result(res, key=u'schedules', headers=self.sched_headers)
    
    @expose(aliases=[u'get <name>'], aliases_only=True)
    def get(self):
        """Get schedule by name
        """
        name = self.get_arg(name=u'name')        
        uri = u'/v1.0/scheduler/entry/%s' % name
        res = self._call(uri, u'GET')
        logger.debug(res)
        self.result(res, key=u'schedule', headers=self.sched_headers)        

    @expose(aliases=[u'create <data file>'], aliases_only=True)
    def create(self):
        """Create schedule reading data from a json file
        """
        data_file = self.get_arg(name=u'data file')
        data = self.load_config(data_file)
        uri = u'/v1.0/scheduler/entry'
        res = self._call(uri, u'POST', data=data)
        self.result({u'msg':u'Create schedule %s' % data}, headers=[u'msg'])

    @expose(aliases=[u'delete <name>'], aliases_only=True)
    def delete(self):
        """Delete schedule by name
        """
        name = self.get_arg(name=u'name')
        data = {u'name':name}
        uri = u'/v1.0/scheduler/entry'
        res = self._call(uri, u'DELETE', data=data)
        self.result({u'msg':u'Delete schedule %s' % name}, headers=[u'msg'])        
        
scheduler_controller_handlers = [
    SchedulerController,
    WorkerController,
    TaskController,
    ScheduleController
]        