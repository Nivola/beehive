# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from marshmallow.validate import OneOf

from beecell.simple import get_value
from beehive.common.apimanager import (
    ApiView,
    ApiManagerError,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    CrudApiObjectJobResponseSchema,
    ApiObjecCountResponseSchema,
    CrudApiJobResponseSchema,
)
from marshmallow import fields, Schema
from beecell.swagger import SwaggerHelper


class TaskApiView(SwaggerApiView):
    tags = ["scheduler"]


class SchedulerEntryResponseSchema(Schema):
    schedules = fields.List(fields.Dict(), required=True)
    args = fields.List(fields.String(default=""), required=False, allow_none=True)
    kwargs = fields.Dict(required=False, default={}, allow_none=True)
    last_run_at = fields.DateTime(required=True)
    name = fields.String(required=True, default="discover")
    options = fields.Dict(required=True, default={})
    schedule = fields.String(required=True, default="<freq: 5.00 minutes>")
    task = fields.String(required=True, default="tasks.discover_vsphere")
    total_run_count = fields.Integer(required=True, default=679)


class GetSchedulerEntriesResponseSchema(Schema):
    schedules = fields.Nested(SchedulerEntryResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=1)


class GetSchedulerEntries(TaskApiView):
    definitions = {
        "GetSchedulerEntriesResponseSchema": GetSchedulerEntriesResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetSchedulerEntriesResponseSchema}}
    )

    def get(self, controller, dummydata, *args, **kwargs):
        """
        List scheduler entries
        Call this api to list all the scheduler entries
        """
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i.info() for i in data]
        resp = {"schedules": res, "count": len(res)}
        return resp


class GetSchedulerEntryResponseSchema(Schema):
    schedule = fields.Nested(SchedulerEntryResponseSchema, required=True, allow_none=True)


class GetSchedulerEntry(TaskApiView):
    definitions = {
        "GetSchedulerEntryResponseSchema": GetSchedulerEntryResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetSchedulerEntryResponseSchema}}
    )

    def get(self, controller, dummydata, oid, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries(name=oid)[0]
        if data is not None:
            res = data.info()
        else:
            raise ApiManagerError("Scheduler entry %s not found" % oid, code=404)
        resp = {"schedule": res}
        return resp


class CreateSchedulerEntryParamRequestSchema(Schema):
    name = fields.String(required=True, default="discover")
    task = fields.String(required=True, default="tasks.discover_vsphere")
    args = fields.Raw(allow_none=True)
    kwargs = fields.Dict(default={}, allow_none=True)
    options = fields.Dict(default={}, allow_none=True)
    schedule = fields.Dict(required=True, default={}, allow_none=True)
    relative = fields.Boolean(allow_none=True)


class CreateSchedulerEntryRequestSchema(Schema):
    schedule = fields.Nested(CreateSchedulerEntryParamRequestSchema)


class CreateSchedulerEntryBodyRequestSchema(Schema):
    body = fields.Nested(CreateSchedulerEntryRequestSchema, context="body")


class CreateSchedulerEntryResponseSchema(Schema):
    name = fields.String(required=True, defualt="sched")


class CreateSchedulerEntry(TaskApiView):
    definitions = {
        "CreateSchedulerEntryResponseSchema": CreateSchedulerEntryResponseSchema,
        "CreateSchedulerEntryRequestSchema": CreateSchedulerEntryRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateSchedulerEntryBodyRequestSchema)
    parameters_schema = CreateSchedulerEntryRequestSchema
    responses = SwaggerApiView.setResponses(
        {202: {"description": "success", "schema": CreateSchedulerEntryResponseSchema}}
    )

    def post(self, controller, data, *dummyargs, **dummykwargs):
        """
        Create schedule
        Create scheduler schedule
        """
        scheduler = controller.get_scheduler()
        data = get_value(data, "schedule", None, exception=True)
        name = get_value(data, "name", None, exception=True)
        task = get_value(data, "task", None, exception=True)
        args = get_value(data, "args", None)
        kwargs = get_value(data, "kwargs", None)
        options = get_value(data, "options", {})
        relative = get_value(data, "relative", None)

        # get schedule
        schedule = get_value(data, "schedule", None, exception=True)

        resp = scheduler.create_update_entry(
            name,
            task,
            schedule,
            args=args,
            kwargs=kwargs,
            options=options,
            relative=relative,
        )
        return {"name": name}, 202


class DeleteSchedulerEntry(TaskApiView):
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({204: {"description": "no response"}})

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
        "ManagerPingResponseSchema": ManagerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerPingResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        Worker pings
        Ping all active workers
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.ping()
        return {"workers_ping": resp}


## stats
class ManagerStatsResponseSchema(Schema):
    workers_stats = fields.List(fields.Dict(), required=True)


class ManagerStats(TaskApiView):
    definitions = {
        "ManagerStatsResponseSchema": ManagerStatsResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerStatsResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        Worker statistics
        Get all active workers statistics
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.stats()
        return {"workers_stats": resp}


## report
class ManagerReportResponseSchema(Schema):
    workers_report = fields.List(fields.Dict(), required=True)


class ManagerReport(TaskApiView):
    definitions = {
        "ManagerReportResponseSchema": ManagerReportResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerReportResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.report()
        return {"workers_report": resp}


class ManagerActiveQueuesResponseSchema(Schema):
    workers_queues = fields.List(fields.Dict(), required=True)


class ManagerActiveQueues(TaskApiView):
    definitions = {
        "ManagerActiveQueuesResponseSchema": ManagerActiveQueuesResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ManagerActiveQueuesResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        """
        Worker Report
        Get all active workers report
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.get_active_queues()
        return {"workers_queues": resp}


## definition
class GetTasksDefinitionResponseSchema(Schema):
    task_definitions = fields.List(fields.String(default="task.test"), required=True)
    count = fields.Integer(required=True, default=1)


class GetTasksDefinition(TaskApiView):
    definitions = {
        "GetTasksDefinitionResponseSchema": GetTasksDefinitionResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetTasksDefinitionResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        """
        Get task definitions
        List all task definitions
        """
        from beehive.module.scheduler_v2.controller import SchedulerController
        from beehive.module.scheduler_v2.controller import TaskManager

        schedulerController: SchedulerController = controller
        task_manager: TaskManager = schedulerController.get_task_manager()
        res = task_manager.get_registered_tasks()
        resp = {"task_definitions": res, "count": len(res)}
        return resp


class GetAllTasksParamsResponseSchema(Schema):
    status = fields.String(required=True, default="SUCCESS")
    traceback = fields.List(fields.String(default="error"), required=False, allow_none=True)
    jobs = fields.List(
        fields.String(default="c518fa8b-1247-4f9f-9d73-785bcc24b8c7"),
        required=False,
        allow_none=True,
    )
    name = fields.String(required=True, default="beehive.module.scheduler.tasks.jobtest")
    task_id = fields.String(required=True, default="c518fa8b-1247-4f9f-9d73-785bcc24b8c7")
    kwargs = fields.Dict(required=False)
    start_time = fields.String(required=True, default="16-06-2017 14:58:50.352286")
    stop_time = fields.String(required=True, default="16-06-2017 14:58:50.399747")
    # args = fields.List(required=False)
    worker = fields.String(required=True, default="celery@tst-beehive-02")
    elapsed = fields.Float(required=True, default=0.0474607944)
    # result = fields.Boolean(required=True, default=True)
    ttl = fields.Integer(required=True, default=83582)
    type = fields.String(required=True, default="JOB")
    children = fields.List(fields.Dict(), required=False)


class GetAllTasksResponseSchema(Schema):
    task_instances = fields.Nested(GetAllTasksParamsResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=1)


class GetAllTasksRequestSchema(Schema):
    elapsed = fields.Integer(
        required=False,
        missing=60,
        example=60,
        allow_none=True,
        description="Used to filter key not older than",
    )
    ttype = fields.String(
        required=False,
        example="JOB",
        description="Used to filter key type",
        allow_none=True,
        validate=OneOf(["JOB", "JOBTASK", "TASK"]),
    )


class GetAllTasks(TaskApiView):
    definitions = {
        "GetAllTasksResponseSchema": GetAllTasksResponseSchema,
        "GetAllTasksRequestSchema": GetAllTasksRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetAllTasksRequestSchema)
    parameters_schema = GetAllTasksRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetAllTasksResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        List task instances
        Call this api to list all the task instances
        """
        task_manager = controller.get_task_manager()
        res = task_manager.get_all_tasks(details=True, **data)
        resp = {"task_instances": res, "count": len(res)}
        return resp


class GetTasksCount(TaskApiView):
    definitions = {
        "ApiObjecCountResponseSchema": ApiObjecCountResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ApiObjecCountResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        """
        Task count
        Get count of all tasks
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.count_all_tasks()
        return resp


class QueryTaskResponseSchema(Schema):
    task_instance = fields.Nested(GetAllTasksParamsResponseSchema, required=True, allow_none=True)


class QueryTaskRequestSchema(GetApiObjectRequestSchema):
    chain = fields.Boolean(required=False, default=True, missing=True, context="query")


class QueryTask(TaskApiView):
    definitions = {
        "QueryTaskResponseSchema": QueryTaskResponseSchema,
        "QueryTaskRequestSchema": QueryTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(QueryTaskRequestSchema)
    parameters_schema = QueryTaskRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": QueryTaskResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task info
        Query single task by id and return description fields
        """
        task_manager = controller.get_task_manager()
        res = task_manager.query_task(oid, chain=data.get("chain"))
        resp = {"task_instance": res}
        return resp


class GetTaskGraphResponseSchema(Schema):
    task_instance_graph = fields.Dict(required=True, default={})


class GetTaskGraph(TaskApiView):
    definitions = {
        "GetTaskGraphResponseSchema": GetTaskGraphResponseSchema,
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetTaskGraphResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get task graph
        Get list of nodes and link that represents the task childs graph
        """
        task_manager = controller.get_task_manager()
        res = task_manager.get_task_graph(oid)
        resp = {"task_instance_graph": res}
        return resp


## purge all
class PurgeAllTasks(TaskApiView):
    definitions = {}
    responses = SwaggerApiView.setResponses({204: {"description": "success"}})

    def delete(self, controller, data, *args, **kwargs):
        """
        Delete all tasks
        Delete all tasks
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instances()
        return (resp, 204)


"""
class PurgeTasks(TaskApiView):
    def delete(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.purge_tasks()
        return (resp, 202)  """


## delete
class DeleteTask(TaskApiView):
    definitions = {
        "GetApiObjectRequestSchema": GetApiObjectRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({204: {"description": "success"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete task
        Delete task by id
        """
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instance(oid)
        return (resp, 204)


"""
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
        return resp"""


## create
class RunJobTestBodyParamRequestSchema(Schema):
    x = fields.Integer(required=True, default=2, missing=2)
    y = fields.Integer(required=True, default=223, missing=223)
    numbers = fields.List(fields.Integer(default=1), required=True)
    mul_numbers = fields.List(fields.Integer(default=1), required=True)
    error = fields.Boolean(required=False, default=False, missing=False)
    suberror = fields.Boolean(required=False, default=False, missing=False)


class RunJobTestBodyRequestSchema(Schema):
    body = fields.Nested(RunJobTestBodyParamRequestSchema, context="body")


class RunJobTest(TaskApiView):
    definitions = {
        "RunJobTestBodyParamRequestSchema": RunJobTestBodyParamRequestSchema,
        "RunJobTestBodyRequestSchema": RunJobTestBodyRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(RunJobTestBodyRequestSchema)
    parameters_schema = RunJobTestBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiJobResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        job = task_manager.run_jobtest(data)
        return {"jobid": job.id}, 201


class SchedulerAPI(ApiView):
    """ """

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("%s/scheduler/entries" % module.base_path, "GET", GetSchedulerEntries, {}),
            (
                "%s/scheduler/entries/<oid>" % module.base_path,
                "GET",
                GetSchedulerEntry,
                {},
            ),
            (
                "%s/scheduler/entries" % module.base_path,
                "POST",
                CreateSchedulerEntry,
                {},
            ),
            (
                "%s/scheduler/entries/<oid>" % module.base_path,
                "DELETE",
                DeleteSchedulerEntry,
                {},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)


class TaskAPI(ApiView):
    """ """

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("%s/worker/ping" % module.base_path, "GET", ManagerPing, {}),
            ("%s/worker/stats" % module.base_path, "GET", ManagerStats, {}),
            ("%s/worker/report" % module.base_path, "GET", ManagerReport, {}),
            ("%s/worker/queues" % module.base_path, "GET", ManagerActiveQueues, {}),
            ("%s/worker/tasks" % module.base_path, "GET", GetAllTasks, {}),
            ("%s/worker/tasks/count" % module.base_path, "GET", GetTasksCount, {}),
            (
                "%s/worker/tasks/definitions" % module.base_path,
                "GET",
                GetTasksDefinition,
                {},
            ),
            ("%s/worker/tasks/<oid>" % module.base_path, "GET", QueryTask, {}),
            ("%s/worker/tasks/<oid>/graph" % module.base_path, "GET", GetTaskGraph, {}),
            ("%s/worker/tasks" % module.base_path, "DELETE", PurgeAllTasks, {}),
            ("%s/worker/tasks/<oid>" % module.base_path, "DELETE", DeleteTask, {}),
            ("%s/worker/tasks/test" % module.base_path, "POST", RunJobTest, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
