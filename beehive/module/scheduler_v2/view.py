# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from marshmallow.validate import OneOf
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError, SwaggerApiView, \
    GetApiObjectRequestSchema, CrudApiObjectJobResponseSchema, \
    ApiObjecCountResponseSchema, CrudApiJobResponseSchema, PaginatedResponseSchema
from marshmallow import fields, Schema
from beecell.swagger import SwaggerHelper


class TaskApiView(SwaggerApiView):
    tags = ['scheduler_v2']


class SchedulerEntryResponseSchema(Schema):
    schedules = fields.List(fields.Dict(), required=True)
    args = fields.List(fields.String(default=''), required=False, allow_none=True)
    kwargs = fields.Dict(required=False, default={}, allow_none=True)
    last_run_at = fields.DateTime(required=True)
    name = fields.String(required=True, default='discover')
    options = fields.Dict(required=True, default={})
    schedule = fields.String(required=True, default='<freq: 5.00 minutes>')
    task = fields.String(required=True, default='tasks.discover_vsphere')
    total_run_count = fields.Integer(required=True, default=679)


class GetSchedulerEntriesResponseSchema(Schema):
    schedules = fields.Nested(SchedulerEntryResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=1)


class GetSchedulerEntries(TaskApiView):
    definitions = {
        'GetSchedulerEntriesResponseSchema': GetSchedulerEntriesResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetSchedulerEntriesResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        """
        List scheduler entries
        Call this api to list all the scheduler entries
        """
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i.info() for i in data]
        resp = {
            'schedules': res,
            'count': len(res)
        }
        return resp


class GetSchedulerEntryResponseSchema(Schema):
    schedule = fields.Nested(SchedulerEntryResponseSchema, required=True, allow_none=True)


class GetSchedulerEntry(TaskApiView):
    definitions = {
        'GetSchedulerEntryResponseSchema': GetSchedulerEntryResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetSchedulerEntryResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries(name=oid)[0]
        if data is not None:
            res = data.info()
        else:
            raise ApiManagerError('Scheduler entry %s not found' % oid, code=404)
        resp = {
            'schedule': res
        }
        return resp


class CreateSchedulerEntryParamRequestSchema(Schema):
    name = fields.String(required=True, default='discover')
    task = fields.String(required=True, default='tasks.discover_vsphere')
    args = fields.Raw(allow_none=True)
    kwargs = fields.Dict(default={}, allow_none=True)    
    options = fields.Dict(default={}, allow_none=True)
    schedule = fields.Dict(required=True, default={}, allow_none=True)
    relative = fields.Boolean(allow_none=True)


class CreateSchedulerEntryRequestSchema(Schema):
    schedule = fields.Nested(CreateSchedulerEntryParamRequestSchema)


class CreateSchedulerEntryBodyRequestSchema(Schema):
    body = fields.Nested(CreateSchedulerEntryRequestSchema, context='body')


class CreateSchedulerEntryResponseSchema(Schema):
    name = fields.String(required=True, defualt='sched')


class CreateSchedulerEntry(TaskApiView):
    definitions = {
        'CreateSchedulerEntryResponseSchema': CreateSchedulerEntryResponseSchema,
        'CreateSchedulerEntryRequestSchema': CreateSchedulerEntryRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateSchedulerEntryBodyRequestSchema)
    parameters_schema = CreateSchedulerEntryRequestSchema
    responses = SwaggerApiView.setResponses({
        202: {
            'description': 'success',
            'schema': CreateSchedulerEntryResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create schedule
        Create scheduler schedule
        """        
        scheduler = controller.get_scheduler()
        data = get_value(data, 'schedule', None, exception=True)
        name = get_value(data, 'name', None, exception=True)
        task = get_value(data, 'task', None, exception=True)
        args = get_value(data, 'args', None)
        kwargs = get_value(data, 'kwargs', None)
        options = get_value(data, 'options', {})
        relative = get_value(data, 'relative', None)
        
        # get schedule
        schedule = get_value(data, 'schedule', None, exception=True)
        
        resp = scheduler.create_update_entry(name, task, schedule, args=args, kwargs=kwargs, options=options,
                                             relative=relative)
        return {'name': name}, 202


class DeleteSchedulerEntry(TaskApiView):
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    }) 
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete schedule
        Delete scheduler schedule by name
        """
        scheduler = controller.get_scheduler()
        # name = get_value(data, 'name', None, exception=True)
        resp = scheduler.remove_entry(oid)
        return (resp, 204)


#
# Task manager
#
## ping
class ManagerPingResponseSchema(Schema):
    workers_ping = fields.List(fields.Dict(), required=True)


class ManagerPing(TaskApiView):
    definitions = {
        'ManagerPingResponseSchema': ManagerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ManagerPingResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker pings
        Ping all active workers
        """        
        task_manager = controller.get_task_manager()
        resp = task_manager.ping()
        return {'workers_ping':resp}


## stats
class ManagerStatsResponseSchema(Schema):
    workers_stats = fields.List(fields.Dict(), required=True)


class ManagerStats(TaskApiView):
    definitions = {
        'ManagerStatsResponseSchema': ManagerStatsResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ManagerStatsResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker statistics
        Get all active workers statistics
        """        
        task_manager = controller.get_task_manager()
        resp = task_manager.stats()
        return {'workers_stats':resp}


## report
class ManagerReportResponseSchema(Schema):
    workers_report = fields.List(fields.Dict(), required=True)


class ManagerReport(TaskApiView):
    definitions = {
        'ManagerReportResponseSchema': ManagerReportResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ManagerReportResponseSchema
        }
    })     
    
    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.report()
        return {'workers_report':resp}


class ManagerActiveQueuesResponseSchema(Schema):
    workers_queues = fields.List(fields.Dict(), required=True)


class ManagerActiveQueues(TaskApiView):
    definitions = {
        'ManagerActiveQueuesResponseSchema': ManagerActiveQueuesResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ManagerActiveQueuesResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.get_active_queues()
        return {'workers_queues': resp}


class GetTasksDefinitionResponseSchema(Schema):
    task_definitions = fields.List(fields.String(default='task.test'), required=True)
    count = fields.Integer(required=True, default=1)


class GetTasksDefinition(TaskApiView):
    definitions = {
        'GetTasksDefinitionResponseSchema': GetTasksDefinitionResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTasksDefinitionResponseSchema
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
            'task_definitions': res,
            'count': len(res)
        }
        return resp    


class GetTasksRequestSchema(Schema):
    entity_class = fields.String(required=True, default='beehive.module.scheduler_v2.controller.Task',
                                 missing='beehive.module.scheduler_v2.controller.Task',
                                 description='entity_class owner of the tasks to query')
    elapsed = fields.Integer(required=False, missing=60, example=60, allow_none=True,
                             description='Used to filter key not older than')
    ttype = fields.String(required=False, example='JOB', description='Used to filter key type',
                          allow_none=True, validate=OneOf(['JOB', 'JOBTASK', 'TASK']))


class GetSingleTaskResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(required=True, default='4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example='4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, default='test', example='test')
    desc = fields.String(required=True, default='test', example='test')
    active = fields.Boolean(required=True, default=True, example=True)



    status = fields.String(required=True, default='SUCCESS')
    traceback = fields.List(fields.String(default='error'), required=False, allow_none=True)
    jobs = fields.List(fields.String(default='c518fa8b-1247-4f9f-9d73-785bcc24b8c7'), required=False, allow_none=True)
    name = fields.String(required=True, default='beehive.module.scheduler.tasks.jobtest')
    task_id = fields.String(required=True, default='c518fa8b-1247-4f9f-9d73-785bcc24b8c7')
    kwargs = fields.Dict(required=False)
    start_time = fields.String(required=True, default='16-06-2017 14:58:50.352286')
    stop_time = fields.String(required=True, default='16-06-2017 14:58:50.399747')
    # args = fields.List(required=False)
    worker = fields.String(required=True, default='celery@tst-beehive-02')
    elapsed = fields.Float(required=True, default=0.0474607944)
    # result = fields.Boolean(required=True, default=True)
    ttl = fields.Integer(required=True, default=83582)
    type = fields.String(required=True, default='JOB')
    children = fields.List(fields.Dict(), required=False)


class GetTasksResponseSchema(PaginatedResponseSchema):
    task_instances = fields.Nested(GetSingleTaskResponseSchema, many=True, required=True, allow_none=True)


class GetTasks(TaskApiView):
    definitions = {
        'GetTasksResponseSchema': GetTasksResponseSchema,
        'GetTasksRequestSchema': GetTasksRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(GetTasksRequestSchema)
    parameters_schema = GetTasksRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTasksResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        """
        List task instances
        Call this api to list all the task instances
        """
        objs, total = controller.get_task_manager().get_tasks(**data)
        res = [r.info() for r in objs]

        return self.format_paginated_response(res, 'task_instances', total, **data)


class GetTaskRequestSchema(GetApiObjectRequestSchema):
    entity_class = fields.String(required=True, default='beehive.module.scheduler_v2.controller.Task',
                                 missing='beehive.module.scheduler_v2.controller.Task',
                                 description='entity_class owner of the tasks to query')


class GetTaskResponseSchema(Schema):
    task_instance = fields.Nested(GetSingleTaskResponseSchema, required=True, allow_none=True)


class GetTask(TaskApiView):
    definitions = {
        'GetTaskResponseSchema': GetTaskResponseSchema,
        'GetTaskRequestSchema': GetTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTaskRequestSchema)
    parameters_schema = GetTaskRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTaskResponseSchema
        }
    }) 
        
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task info
        Query single task by id and return description fields
        """
        task_manager = controller.get_task_manager()
        entity_class_name = data.get('entity_class')
        res = task_manager.get_task(entity_class_name, oid)
        res.post_get()
        resp = {'task_instance': res.detail()}
        return resp


class GetTraceLineResponseSchema(Schema):
    id = fields.String(required=True, default='10', description='trace line id')
    step = fields.String(required=True, default='<uuid>', description='step id')
    message = fields.String(required=True, default='some text', description='trace message')
    level = fields.String(required=True, default='INFO', description='trace level')
    date = fields.String(required=True, default='1999-12-31T', description='trace date')


class GetTraceResponseSchema(Schema):
    task_trace = fields.Nested(GetTraceLineResponseSchema, required=True, allow_none=True)


class GetTrace(TaskApiView):
    definitions = {
        'GetTraceResponseSchema': GetTraceResponseSchema,
        'GetTaskRequestSchema': GetTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTaskRequestSchema)
    parameters_schema = GetTaskRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTraceResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task trace
        Query single task by id and return execution trace
        """
        task_manager = controller.get_task_manager()
        entity_class_name = data.get('entity_class')
        res = task_manager.get_task(entity_class_name, oid)
        resp = {'task_trace': res.get_trace()}
        return resp


class GetTaskGraphResponseSchema(Schema):
    task_instance_graph = fields.Dict(required=True, default={})


class GetTaskGraph(TaskApiView):
    definitions = {
        'GetTaskGraphResponseSchema':GetTaskGraphResponseSchema,
        'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)    
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTaskGraphResponseSchema
        }
    }) 
        
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task graph
        Get list of nodes and link that represents the task childs graph
        """ 
        task_manager = controller.get_task_manager()
        res = task_manager.get_task_graph(oid)
        resp = {'task_instance_graph':res}
        return resp    
    

## purge all
class PurgeAllTasks(TaskApiView):
    definitions = {
    }
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'success'
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
        'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)    
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'success'
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
class RunTestTaskBodyParamRequestSchema(Schema):
    x = fields.Integer(required=True, default=2, missing=2)
    y = fields.Integer(required=True, default=223, missing=223)
    numbers = fields.List(fields.Integer(default=1), required=True)
    mul_numbers = fields.List(fields.Integer(default=1), required=True)
    error = fields.Boolean(required=False, default=False, missing=False)
    suberror = fields.Boolean(required=False, default=False, missing=False)


class RunTestTaskBodyRequestSchema(Schema):
    body = fields.Nested(RunTestTaskBodyParamRequestSchema, context='body')


class RunTestTask(TaskApiView):
    definitions = {
        'RunTestTaskBodyParamRequestSchema': RunTestTaskBodyParamRequestSchema,
        'RunTestTaskBodyRequestSchema': RunTestTaskBodyRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(RunTestTaskBodyRequestSchema)
    parameters_schema = RunTestTaskBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiJobResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        task = task_manager.run_jobtest(data)
        return {'taskid': task.id}, 201


class SchedulerAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('%s/scheduler/entries' % module.base_path, 'GET', GetSchedulerEntries, {}),
            ('%s/scheduler/entries/<oid>' % module.base_path, 'GET', GetSchedulerEntry, {}),
            ('%s/scheduler/entries' % module.base_path, 'POST', CreateSchedulerEntry, {}),
            ('%s/scheduler/entries/<oid>' % module.base_path, 'DELETE', DeleteSchedulerEntry, {}),
        ]

        ApiView.register_api(module, rules)

        
class TaskAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('%s/worker/ping' % module.base_path, 'GET', ManagerPing, {}),
            ('%s/worker/stats' % module.base_path, 'GET', ManagerStats, {}),
            ('%s/worker/report' % module.base_path, 'GET', ManagerReport, {}),
            ('%s/worker/queues' % module.base_path, 'GET', ManagerActiveQueues, {}),
            ('%s/worker/tasks' % module.base_path, 'GET', GetTasks, {}),
            ('%s/worker/tasks/definitions' % module.base_path, 'GET', GetTasksDefinition, {}),
            ('%s/worker/tasks/<oid>' % module.base_path, 'GET', GetTask, {}),
            ('%s/worker/tasks/<oid>/trace' % module.base_path, 'GET', GetTrace, {}),
            # ('%s/worker/tasks/<oid>/graph' % module.base_path, 'GET', GetTaskGraph, {}),
            # ('%s/worker/tasks' % module.base_path, 'DELETE', PurgeAllTasks, {}),
            # ('%s/worker/tasks/<oid>' % module.base_path, 'DELETE', DeleteTask, {}),
            # ('%s/worker/tasks/test' % module.base_path, 'POST', RunTestTask, {}),
        ]

        ApiView.register_api(module, rules)