"""
Created on Sep 27, 2017

@author: darkbk
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate, str2bool

logger = logging.getLogger(__name__)


'''
class SchedulerController(BaseController):
    class Meta:
        label = 'sched'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Scheduler management"

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class SchedulerControllerChild(ApiController):
    uri_prefix = {
        u'auth': u'nas',
        u'event': u'nes',
        u'dir': u'ncs',
        u'resource': u'nrs',
        u'service': u'nws'
    }

    class Meta:
        stacked_on = 'sched'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-s', '--subsystem'], dict(action='store', help='beehive subsystem like auth, resource, ..')),
        ]

    def _ext_parse_args(self):
        ApiController._ext_parse_args(self)
        
        self.subsystem = self.app.pargs.subsystem
        self.prefix = self.uri_prefix.get(self.app.pargs.subsystem, u'')
        if self.subsystem is None:
            raise Exception(u'Subsystem is not specified')'''


class WorkerController(object):
    # class Meta:
    #     label = 'workers'
    #     description = "Worker management"
    @expose()
    @check_error
    def ping(self):
        """Ping
        """
        uri = u'%s/worker/ping' % self.baseuri
        res = self._call(uri, u'GET').get(u'workers_ping', {})
        logger.info(res)
        resp = []
        for k, v in res.items():
            resp.append({u'worker': k, u'res': v})
        self.result(resp, headers=[u'worker', u'res'])

    @expose()
    @check_error
    def stat(self):
        """Statistics
        """
        uri = u'%s/worker/stats' % self.baseuri
        res = self._call(uri, u'GET').get(u'workers_stats', {})
        logger.info(res)
        resp = []
        for k,v in res.items():
            v[u'worker'] = k
            resp.append(v)        
        self.result(res, details=True)

    @expose()
    @check_error
    def report(self):
        """Report
        """
        uri = u'%s/worker/report' % self.baseuri
        res = self._call(uri, u'GET').get(u'workers_report', {})
        logger.info(res)
        resp = []
        for k,v in res.items():
            vals = v.values()[0].split(u'\n')
            row = 0
            for val in vals:
                row += 1
                resp.append({u'worker': u'%s.%s' % (k, row), u'report':val})
        self.result(resp, headers=[u'worker', u'report'], maxsize=300)


class TaskController(object):
    # class Meta:
    #     label = 'tasks'
    #     description = "Task management"
        
    @expose()
    @check_error
    def definitions(self):
        """List all available tasks you can invoke
        """
        uri = u'%s/worker/tasks/definitions' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        resp = []
        for k,v in res[u'task_definitions'].items():
            for v1 in v:
                resp.append({u'worker':k, u'task':v1})
        self.result(resp, headers=[u'worker', u'task'], maxsize=400)    
    
    @expose()
    @check_error
    def list(self):
        """List all task instance
        """
        uri = u'%s/worker/tasks' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'task_instances', headers=[u'task_id', u'type', u'status', u'name', u'start_time',
                                                         u'stop_time', u'elapsed'], maxsize=200)
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get task instance by id
        """
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
        res = self._call(uri, u'GET').get(u'task_instance')
        logger.info(res)
        resp = []
        resp.append(res)
        resp.extend(res.get(u'children'))
        self.result(resp, headers=[u'task_id', u'type', u'status', u'name', u'start_time', u'stop_time', u'elapsed'],
                    maxsize=100)
    
    @expose(aliases=[u'trace <id>'], aliases_only=True)
    @check_error
    def trace(self):
        """Get task instance execution trace by id
        """        
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
        res = self._call(uri, u'GET').get(u'task_instance').get(u'trace')
        logger.info(res)
        resp = []
        for i in res:
            resp.append({u'timestamp':i[0], u'task':i[1], u'task id':i[2], 
                         u'msg':truncate(i[3], 150)})
        self.result(resp, headers=[u'timestamp', u'msg'], maxsize=200)        
    
    @expose(aliases=[u'graph <id>'], aliases_only=True)
    @check_error
    def graph(self):
        """Get task instance execution graph by id
        """        
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks%s/graph' % (self.baseuri, task_id)
        res = self._call(uri, u'GET').get(u'task_instance_graph')
        logger.info(res)
        print(u'Nodes:')
        headers = [u'details.task_id', u'details.type', u'details.status', u'label', u'details.start_time',
                   u'details.stop_time', u'details.elapsed']
        self.result(res, key=u'nodes', headers=headers)
        print(u'Links:')
        self.result(res, key=u'links', headers=[u'source', u'target'])

    @expose()
    @check_error
    def deletes(self):
        """Delete all task instance
        """
        uri = u'%s/worker/tasks' % self.baseuri
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete all task')
        res = {u'msg':u'Delete all task'}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete task instance by id
        """             
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete task %s' % task_id)
        res = {u'msg':u'Delete task %s' % task_id}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'test [error=true/false] [suberror=true/false]'], aliases_only=True)
    @check_error
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
        uri = u'%s/worker/tasks/test' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Run job test: %s' % res)
        self.result(res)


class ScheduleController(object):
    sched_headers = [u'name', u'task', u'schedule', u'args', u'kwargs', u'options', u'last_run_at', u'total_run_count']
       
    # class Meta:
    #     label = 'schedules'
    #     description = "Schedule management"
        
    @expose()
    @check_error
    def list(self):
        """List all schedules
        """
        uri = u'%s/scheduler/entries' % self.baseuri
        res = self._call(uri, u'GET')
        logger.debug(res)
        self.result(res, key=u'schedules', headers=self.sched_headers)
    
    @expose(aliases=[u'get <name>'], aliases_only=True)
    @check_error
    def get(self):
        """Get schedule by name
        """
        name = self.get_arg(name=u'name')        
        uri = u'%s/scheduler/entries/%s' % (self.baseuri, name)
        res = self._call(uri, u'GET')
        logger.debug(res)
        self.result(res, key=u'schedule', headers=self.sched_headers)        

    @expose(aliases=[u'create <data file>'], aliases_only=True)
    @check_error
    def create(self):
        """Create schedule reading data from a json file
        """
        data_file = self.get_arg(name=u'data file')
        data = self.load_config(data_file)
        uri = u'%s/scheduler/entries' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        self.result({u'msg': u'Create schedule %s' % data}, headers=[u'msg'])

    @expose(aliases=[u'delete <name>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete schedule by name
        """
        name = self.get_arg(name=u'name')
        data = {u'name':name}
        uri = u'%s/scheduler/entries' % self.baseuri
        res = self._call(uri, u'DELETE', data=data)
        self.result({u'msg': u'Delete schedule %s' % name}, headers=[u'msg'])


# scheduler_controller_handlers = [
#     SchedulerController,
#     WorkerController,
#     TaskController,
#     ScheduleController
# ]