'''
Created on Apr 2, 2026

@author: darkbk
'''
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError, SwaggerApiView,\
    GetApiObjectRequestSchema, CrudApiObjectJobResponseSchema,\
    ApiObjecCountResponseSchema
from flasgger import fields, Schema
from beecell.swagger import SwaggerHelper

class TaskApiView(SwaggerApiView):
    tags = [u'scheduler']

#
# Scheduler
#
## list
class SchedulerEntryResponseSchema(Schema):
    schedules = fields.List(fields.Dict(), required=True)
    args = fields.List(fields.String(default=u''), required=False, allow_none=True)
    kwargs = fields.Dict(required=False, default={}, allow_none=True)
    last_run_at = fields.Integer(required=True, default=1459755371)
    name = fields.String(required=True, default=u'discover')
    options = fields.Dict(required=True, default={})
    schedule = fields.String(required=True, default=u'<freq: 5.00 minutes>')
    task = fields.String(required=True, default=u'tasks.discover_vsphere')
    total_run_count = fields.Integer(required=True, default=679)

class GetSchedulerEntriesResponseSchema(Schema):
    schedules = fields.Nested(SchedulerEntryResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=1)

class GetSchedulerEntries(TaskApiView):
    definitions = {
        u'GetSchedulerEntriesResponseSchema': GetSchedulerEntriesResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetSchedulerEntriesResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        """
        List scheduler entries
        Call this api to list all the scheduler entries
        """
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i[1].info() for i in data]
        resp = {
            u'schedules':res,
            u'count':len(res)
        }
        return resp

## get
class GetSchedulerEntryResponseSchema(Schema):
    schedule = fields.Nested(SchedulerEntryResponseSchema, required=True, allow_none=True)

class GetSchedulerEntry(TaskApiView):
    definitions = {
        u'GetSchedulerEntryResponseSchema': GetSchedulerEntryResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetSchedulerEntryResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries(name=oid)[0][1]
        if data is not None:
            res = data.info()
        else:
            raise ApiManagerError(u'Scheduler entry %s not found' % oid, code=404)
        resp = {
            u'schedule':res
        }
        return resp

## create
class CreateSchedulerEntryParamRequestSchema(Schema):
    name = fields.String(required=True, default=u'discover')
    task = fields.String(required=True, default=u'tasks.discover_vsphere')
    args = fields.Raw(required=True, allow_none=True)
    kwargs = fields.Dict(default={}, allow_none=True)    
    options = fields.Dict(default={}, allow_none=True)
    schedule = fields.Dict(required=True, default={}, allow_none=True)
    relative = fields.Boolean(allow_none=True)

class CreateSchedulerEntryRequestSchema(Schema):
    schedule = fields.Nested(CreateSchedulerEntryParamRequestSchema)
    
class CreateSchedulerEntryBodyRequestSchema(Schema):
    body = fields.Nested(CreateSchedulerEntryRequestSchema, context=u'body')

class CreateSchedulerEntryResponseSchema(Schema):
    name = fields.String(required=True, defualt=u'sched')

class CreateSchedulerEntry(TaskApiView):
    definitions = {
        u'CreateSchedulerEntryResponseSchema': CreateSchedulerEntryResponseSchema,
        u'CreateSchedulerEntryRequestSchema':CreateSchedulerEntryRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateSchedulerEntryBodyRequestSchema)
    parameters_schema = CreateSchedulerEntryRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            u'description': u'success',
            u'schema': CreateSchedulerEntryResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create schedule
        Create scheduler schedule
        """        
        scheduler = controller.get_scheduler()
        data = get_value(data, u'schedule', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        task = get_value(data, u'task', None, exception=True)
        args = get_value(data, u'args', None)
        kwargs = get_value(data, u'kwargs', None)
        options = get_value(data, u'options', None)
        relative = get_value(data, u'relative', None)
        
        # get schedule
        schedule = get_value(data, u'schedule', None, exception=True)
        
        resp = scheduler.create_update_entry(name, task, schedule, 
                                             args=args, kwargs=kwargs,
                                             options=options, 
                                             relative=relative)        
        return (resp, 202)

## delete
class DeleteSchedulerEntry(TaskApiView):
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    }) 
    
    def delete(self, controller, data, *args, **kwargs):
        """
        Delete schedule
        Delete scheduler schedule by name
        """
        scheduler = controller.get_scheduler()
        name = get_value(data, u'name', None, exception=True)
        resp = scheduler.remove_entry(name)        
        return (resp, 204)


#
# Task manager
#
## ping
class ManagerPingResponseSchema(Schema):
    workers_ping = fields.List(fields.Dict(), required=True)


class ManagerPing(TaskApiView):
    definitions = {
        u'ManagerPingResponseSchema': ManagerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ManagerPingResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker pings
        Ping all active workers
        """        
        task_manager = controller.get_task_manager()
        resp = task_manager.ping()
        return {u'workers_ping':resp}


## stats
class ManagerStatsResponseSchema(Schema):
    workers_stats = fields.List(fields.Dict(), required=True)


class ManagerStats(TaskApiView):
    definitions = {
        u'ManagerStatsResponseSchema': ManagerStatsResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ManagerStatsResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker statistics
        Get all active workers statistics
        """        
        task_manager = controller.get_task_manager()
        resp = task_manager.stats()
        return {u'workers_stats':resp}


## report
class ManagerReportResponseSchema(Schema):
    workers_report = fields.List(fields.Dict(), required=True)


class ManagerReport(TaskApiView):
    definitions = {
        u'ManagerReportResponseSchema': ManagerReportResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ManagerReportResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.report()
        return {u'workers_report':resp}


class ManagerActiveQueuesResponseSchema(Schema):
    workers_queues = fields.List(fields.Dict(), required=True)


class ManagerActiveQueues(TaskApiView):
    definitions = {
        u'ManagerActiveQueuesResponseSchema': ManagerActiveQueuesResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ManagerActiveQueuesResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.get_active_queues()
        return {u'workers_queues': resp}


## definition
class GetTasksDefinitionResponseSchema(Schema):
    task_definitions = fields.List(fields.String(default=u'task.test'), required=True)
    count = fields.Integer(required=True, default=1)


class GetTasksDefinition(TaskApiView):
    definitions = {
        u'GetTasksDefinitionResponseSchema': GetTasksDefinitionResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetTasksDefinitionResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Get task definitions
        List all task definitions
        """  
        task_manager = controller.get_task_manager()
        res = task_manager.get_registered_tasks()
        resp = {
            u'task_definitions':res,
            u'count':len(res)
        }
        return resp    

## list
class GetAllTasksParamsResponseSchema(Schema):
    status = fields.String(required=True, default=u'SUCCESS')
    traceback = fields.List(fields.String(default=u'error'), 
                            required=False, allow_none=True)
    jobs = fields.List(fields.String(default=u'c518fa8b-1247-4f9f-9d73-785bcc24b8c7'), 
                            required=False, allow_none=True)
    name = fields.String(required=True, default=u'beehive.module.scheduler.tasks.jobtest')
    task_id = fields.String(required=True, default=u'c518fa8b-1247-4f9f-9d73-785bcc24b8c7')
    kwargs = fields.Dict(required=True, default={})
    start_time = fields.String(required=True, default=u'16-06-2017 14:58:50.352286')
    stop_time = fields.String(required=True, default=u'16-06-2017 14:58:50.399747')
    args = fields.List(fields.String(default=u''), required=False)
    worker = fields.String(required=True, default=u'celery@tst-beehive-02')
    elapsed = fields.Float(required=True, default=0.0474607944)
    result = fields.Boolean(required=True, default=True)
    ttl = fields.Integer(required=True, default=83582)
    type = fields.String(required=True, default=u'JOB')
    children = fields.List(fields.String(default=u'd069c405-d9db-45f3-967e-f052fbeb3c3e'), 
                           required=False)

class GetAllTasksResponseSchema(Schema):
    task_instances = fields.Nested(GetAllTasksParamsResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=1)

class GetAllTasks(TaskApiView):
    definitions = {
        u'GetSchedulerEntriesResponseSchema': GetSchedulerEntriesResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetSchedulerEntriesResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        """
        List task instances
        Call this api to list all the task instances
        """  
        task_manager = controller.get_task_manager()
        res = task_manager.get_all_tasks(details=True)
        resp = {
            u'task_instances':res,
            u'count':len(res)
        }        
        return resp

## count
class GetTasksCount(TaskApiView):
    definitions = {
        u'ApiObjecCountResponseSchema': ApiObjecCountResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjecCountResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Task count
        Get count of all tasks
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.count_all_tasks()
        return resp

## get
class QueryTaskResponseSchema(Schema):
    task_instance = fields.Nested(GetAllTasksParamsResponseSchema, required=True, allow_none=True)

class QueryTask(TaskApiView):
    definitions = {
        u'QueryTaskResponseSchema':QueryTaskResponseSchema,
        u'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)    
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': QueryTaskResponseSchema
        }
    }) 
        
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task info
        Query single task by id and return description fields
        """
        task_manager = controller.get_task_manager()
        res = task_manager.query_task(oid)
        resp = {u'task_instance':res}
        return resp

## graph
class GetTaskGraphResponseSchema(Schema):
    task_instance_graph = fields.Dict(required=True, default={})

class GetTaskGraph(TaskApiView):
    definitions = {
        u'GetTaskGraphResponseSchema':GetTaskGraphResponseSchema,
        u'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)    
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetTaskGraphResponseSchema
        }
    }) 
        
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task graph
        Get list of nodes and link that represents the task childs graph
        """ 
        task_manager = controller.get_task_manager()
        res = task_manager.get_task_graph(oid)
        resp = {u'task_instance_graph':res}
        return resp    
    

## purge all
class PurgeAllTasks(TaskApiView):
    definitions = {
    }
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'success'
        }
    })    
    
    def delete(self, controller, data, *args, **kwargs):
        """
        Delete all tasks
        Delete all tasks
        """        
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instances()
        return (resp, 204)
    
'''
class PurgeTasks(TaskApiView):
    def delete(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.purge_tasks()
        return (resp, 202)  '''
    
## delete
class DeleteTask(TaskApiView):
    definitions = {
        u'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)    
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'success'
        }
    })     
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete task
        Delete task by id
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instance(oid)
        return (resp, 204)  

'''
class RevokeTask(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.revoke_task(oid)
        return (resp, 202)  
    
class SetTaskTimeLimit(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        cmd = get_value(data, 'cmd', None)
        # set tasks category time limit
        if cmd == 'time_limit':
            task_name = get_value(data, 'name', '')
            limit = get_value(data, 'value', 0)
            resp = task_manager.time_limit_task(task_name, limit)
        return resp'''
    
## create
class RunJobTestBodyParamRequestSchema(Schema):
    x = fields.Integer(required=True, default=2)
    y = fields.Integer(required=True, default=223)
    numbers = fields.List(fields.Integer(default=1), required=True)
    mul_numbers = fields.List(fields.Integer(default=1), required=True)
    error = fields.Boolean(required=False, default=False)
    suberror = fields.Boolean(required=False, default=False)

class RunJobTestBodyRequestSchema(Schema):
    body = fields.Nested(RunJobTestBodyParamRequestSchema, context=u'body')

class RunJobTest(TaskApiView):
    definitions = {
        u'RunJobTestBodyParamRequestSchema':RunJobTestBodyParamRequestSchema,
        u'RunJobTestBodyRequestSchema':RunJobTestBodyRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(RunJobTestBodyRequestSchema)
    parameters_schema = RunJobTestBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectJobResponseSchema
        }
    })    
    
    def post(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        job = task_manager.run_jobtest(data)
        return {u'jobid':job.id}
    
class SchedulerAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'scheduler/entries', u'GET', GetSchedulerEntries, {}),
            (u'scheduler/entry/<oid>', u'GET', GetSchedulerEntry, {}),
            (u'scheduler/entry', u'POST', CreateSchedulerEntry, {}),
            (u'scheduler/entry', u'DELETE', DeleteSchedulerEntry, {}),
        ]

        ApiView.register_api(module, rules)

        
class TaskAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'worker/ping', u'GET', ManagerPing, {}),
            (u'worker/stats', u'GET', ManagerStats, {}),
            (u'worker/report', u'GET', ManagerReport, {}),
            (u'worker/queues', u'GET', ManagerActiveQueues, {}),
            (u'worker/tasks', u'GET', GetAllTasks, {}),
            (u'worker/tasks/count', u'GET', GetTasksCount, {}),
            (u'worker/tasks/definitions', u'GET', GetTasksDefinition, {}),
            (u'worker/tasks/<oid>', u'GET', QueryTask, {}),
            (u'worker/tasks/<oid>/graph', u'GET', GetTaskGraph, {}),
            (u'worker/tasks', u'DELETE', PurgeAllTasks, {}),
            (u'worker/tasks/<oid>', u'DELETE', DeleteTask, {}),
            (u'worker/tasks/test', u'POST', RunJobTest, {}),
        ]

        ApiView.register_api(module, rules)