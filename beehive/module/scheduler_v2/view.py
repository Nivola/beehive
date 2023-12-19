# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from marshmallow.validate import OneOf, Range
from beecell.simple import get_value
from beehive.common.apimanager import (
    ApiView,
    ApiManagerError,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    CrudApiObjectJobResponseSchema,
    ApiObjecCountResponseSchema,
    CrudApiJobResponseSchema,
    PaginatedResponseSchema,
    PaginatedRequestQuerySchema,
    ApiObjectMetadataResponseSchema,
)
from marshmallow import fields, Schema
from beecell.swagger import SwaggerHelper


class TaskApiView(SwaggerApiView):
    tags = ["scheduler_v2"]


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
    summary = "List scheduler entries"
    description = "List scheduler entries"
    definitions = {
        "GetSchedulerEntriesResponseSchema": GetSchedulerEntriesResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetSchedulerEntriesResponseSchema}}
    )

    def get(self, controller, dummydata, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i.info() for i in data]
        resp = {"schedules": res, "count": len(res)}
        return resp


class GetSchedulerEntryResponseSchema(Schema):
    schedule = fields.Nested(SchedulerEntryResponseSchema, required=True, allow_none=True)


class GetSchedulerEntry(TaskApiView):
    summary = "Get scheduler entry"
    description = "Get scheduler entry"
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
    summary = "Create scheduler entry"
    description = "Create scheduler entry"
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

        scheduler.create_update_entry(
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
    summary = "Delete scheduler entry"
    description = "Delete scheduler entry"
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({204: {"description": "no response"}})

    def delete(self, controller, data, oid, *args, **kwargs):
        scheduler = controller.get_scheduler()
        # name = get_value(data, 'name', None, exception=True)
        resp = scheduler.remove_entry(oid)
        return resp, 204


#
# Task manager
#
class ManagerPingResponseSchema(Schema):
    workers_ping = fields.List(fields.Dict(), required=True)


class ManagerPing(TaskApiView):
    summary = "Workers ping"
    description = "Workers ping"
    definitions = {
        "ManagerPingResponseSchema": ManagerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerPingResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        resp = task_manager.ping()
        return {"workers_ping": resp}


class ManagerStatsResponseSchema(Schema):
    workers_stats = fields.List(fields.Dict(), required=True)


class ManagerStats(TaskApiView):
    summary = "Workers statistics"
    description = "Workers statistics"
    definitions = {
        "ManagerStatsResponseSchema": ManagerStatsResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerStatsResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        resp = task_manager.stats()
        return {"workers_stats": resp}


class ManagerReportResponseSchema(Schema):
    workers_report = fields.List(fields.Dict(), required=True)


class ManagerReport(TaskApiView):
    summary = "Workers report"
    description = "Workers report"
    definitions = {
        "ManagerReportResponseSchema": ManagerReportResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ManagerReportResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        resp = task_manager.report()
        return {"workers_report": resp}


class ManagerActiveQueuesResponseSchema(Schema):
    workers_queues = fields.List(fields.Dict(), required=True)


class ManagerActiveQueues(TaskApiView):
    summary = "Workers active queues"
    description = "Workers active queues"
    definitions = {
        "ManagerActiveQueuesResponseSchema": ManagerActiveQueuesResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": ManagerActiveQueuesResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        resp = task_manager.get_active_queues()
        return {"workers_queues": resp}


class GetTasksDefinitionResponseSchema(Schema):
    task_definitions = fields.List(fields.String(default="task.test"), required=True)
    count = fields.Integer(required=True, default=1)


class GetTasksDefinition(TaskApiView):
    summary = "Get task definitions"
    description = "Get task definitions"
    definitions = {
        "GetTasksDefinitionResponseSchema": GetTasksDefinitionResponseSchema,
    }
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": GetTasksDefinitionResponseSchema}}
    )

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        res = task_manager.get_registered_tasks()
        resp = {"task_definitions": res, "count": len(res)}
        return resp


class GetTasksRequestSchema(PaginatedRequestQuerySchema):
    objid = fields.String(
        required=False,
        default="396587362//3328462822",
        example="396587362//3328462822",
        description="authorization id",
    )
    entity_class = fields.String(
        required=False,
        example="beehive.module.scheduler_v2.controller.Manager",
        missing=None,
        description="entity_class owner of the tasks to query",
    )
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


class GetSingleTaskResponseSchema(Schema):
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(
        required=True,
        default="4cdf0ea4-159a-45aa-96f2-708e461130e1",
        example="4cdf0ea4-159a-45aa-96f2-708e461130e1",
    )
    name = fields.String(required=True, default="test", example="test")
    status = fields.String(required=True, default="SUCCESS")
    parent = fields.String(required=True, default="4cdf0ea4-159a-45aa-96f2-708e461130e1")
    worker = fields.String(required=True, default="celery@tst-beehive-02")
    api_id = fields.String(required=True, default="12345")
    server = fields.String(required=True, default="localhost")
    user = fields.String(required=True, default="test1@local")
    identity = fields.String(required=True, default="4cdf0ea4-159a-45aa-96f2-708e461130e1")
    start_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    run_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    stop_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    duration = fields.Integer(required=True, default=10)


class GetTasksResponseSchema(PaginatedResponseSchema):
    task_instances = fields.Nested(GetSingleTaskResponseSchema, many=True, required=True, allow_none=True)


class GetTasks(TaskApiView):
    summary = "List task instances"
    description = "List task instances"
    definitions = {
        "GetTasksResponseSchema": GetTasksResponseSchema,
        "GetTasksRequestSchema": GetTasksRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTasksRequestSchema)
    parameters_schema = GetTasksRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetTasksResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        objs, total = task_manager.get_tasks(**data)
        res = [r.info() for r in objs]

        return self.format_paginated_response(res, "task_instances", total, **data)


class GetTaskRequestSchema(GetApiObjectRequestSchema):
    entity_class = fields.String(
        required=False,
        example="beehive.module.scheduler_v2.controller.Manager",
        missing=None,
        description="entity_class owner of the tasks to query",
    )


class GetSingleTaskStepSchema(GetSingleTaskResponseSchema):
    uuid = fields.String(
        required=True,
        default="4cdf0ea4-159a-45aa-96f2-708e461130e1",
        example="4cdf0ea4-159a-45aa-96f2-708e461130e1",
    )
    name = fields.String(required=True, default="test", example="test")
    status = fields.String(required=True, default="SUCCESS")
    result = fields.String(required=True, default="123")
    start_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    run_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    stop_time = fields.DateTime(required=True, default="1990-12-31T23:59:59Z", example="1990-12-31T23:59:59Z")
    duration = fields.Integer(required=True, default=10)


class GetSingleTask1ResponseSchema(GetSingleTaskResponseSchema):
    result = fields.String(required=True, default="23")
    args = fields.String(required=True, default="....")
    kwargs = fields.String(required=True, default="....")
    steps = fields.Nested(GetSingleTaskStepSchema, many=True, required=True, allow_none=True)


class GetTaskResponseSchema(Schema):
    task_instance = fields.Nested(GetSingleTask1ResponseSchema, required=True, allow_none=True)


class GetTask(TaskApiView):
    summary = "Get task instance info"
    description = "Get task instance info"
    definitions = {
        "GetTaskResponseSchema": GetTaskResponseSchema,
        "GetTaskRequestSchema": GetTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTaskRequestSchema)
    parameters_schema = GetTaskRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetTaskResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        entity_class_name = data.get("entity_class")
        res = task_manager.get_task(oid, entity_class_name=entity_class_name)
        res.post_get()
        resp = {"task_instance": res.detail()}
        return resp


class GetSingleTaskStatusResponseSchema(Schema):
    uuid = fields.String(
        required=True,
        default="4cdf0ea4-159a-45aa-96f2-708e461130e1",
        example="4cdf0ea4-159a-45aa-96f2-708e461130e1",
    )
    status = fields.String(required=True, default="SUCCESS")


class GetTaskStatusResponseSchema(Schema):
    task_instance = fields.Nested(GetSingleTaskStatusResponseSchema, required=True, allow_none=True)


class GetTaskStatus(TaskApiView):
    summary = "Get task instance status"
    description = "Get task instance status"
    definitions = {
        "GetTaskStatusResponseSchema": GetTaskStatusResponseSchema,
        "GetTaskRequestSchema": GetTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTaskRequestSchema)
    parameters_schema = GetTaskRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetTaskResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        entity_class_name = data.get("entity_class")
        res = task_manager.get_task_status(oid, entity_class_name=entity_class_name)
        resp = {"task_instance": res}
        return resp


class GetTraceLineResponseSchema(Schema):
    id = fields.String(required=True, default="10", description="trace line id")
    step = fields.String(required=True, default="<uuid>", description="step id")
    message = fields.String(required=True, default="some text", description="trace message")
    level = fields.String(required=True, default="INFO", description="trace level")
    date = fields.String(required=True, default="1999-12-31T", description="trace date")


class GetTraceResponseSchema(Schema):
    task_trace = fields.Nested(GetTraceLineResponseSchema, required=True, allow_none=True)


class GetTrace(TaskApiView):
    summary = "Get task instance trace"
    description = "Get task instance trace"
    definitions = {
        "GetTraceResponseSchema": GetTraceResponseSchema,
        "GetTaskRequestSchema": GetTaskRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetTaskRequestSchema)
    parameters_schema = GetTaskRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetTraceResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        task_manager = controller.get_task_manager()
        entity_class_name = data.get("entity_class")
        res = task_manager.get_task(oid, entity_class_name=entity_class_name)
        resp = {"task_trace": res.get_trace()}
        return resp


class GetLogLineResponseSchema(PaginatedResponseSchema):
    values = fields.List(fields.String, required=True, example="some text", description="log message")


class GetLogResponseSchema(Schema):
    task_log = fields.Nested(GetLogLineResponseSchema, required=True, allow_none=True)


class GetLogRequestSchema(Schema):
    oid = fields.String(
        example="4d5e87cd-0139-400d-a787-5a15eba786e9",
        context="path",
        description="task id",
    )
    size = fields.Integer(
        default=20,
        example=20,
        missing=20,
        context="query",
        description="log list page size. -1 to get all the logs",
        validate=Range(min=-1, max=1000, error="Size is out from range"),
    )
    page = fields.Integer(
        default=0,
        example=0,
        missing=0,
        context="query",
        description="log list page selected",
        validate=Range(min=0, max=10000, error="Page is out from range"),
    )


class GetLog(TaskApiView):
    summary = "Get task instance log"
    description = "Get task instance log"
    definitions = {
        "GetLogResponseSchema": GetLogResponseSchema,
        "GetLogRequestSchema": GetLogRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetLogRequestSchema)
    parameters_schema = GetLogRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetLogResponseSchema}})

    def get(self, controller, data, oid, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager, Task

        task_manager: TaskManager = controller.get_task_manager()
        entity_class_name = data.get("entity_class")
        task: Task = task_manager.get_task(oid, entity_class_name=entity_class_name)
        print("GetLog - task: %s" % task)
        resp = {"task_log": task.get_log(**data)}
        return resp


# class GetTaskGraphResponseSchema(Schema):
#     task_instance_graph = fields.Dict(required=True, default={})
#
#
# class GetTaskGraph(TaskApiView):
#     definitions = {
#         'GetTaskGraphResponseSchema':GetTaskGraphResponseSchema,
#         'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = SwaggerApiView.setResponses({
#         200: {
#             'description': 'success',
#             'schema': GetTaskGraphResponseSchema
#         }
#     })
#
#     def get(self, controller, data, oid, *args, **kwargs):
#         """
#         Get task graph
#         Get list of nodes and link that represents the task childs graph
#         """
#         task_manager = controller.get_task_manager()
#         res = task_manager.get_task_graph(oid)
#         resp = {'task_instance_graph':res}
#         return resp


# class PurgeAllTasks(TaskApiView):
#     definitions = {
#     }
#     responses = SwaggerApiView.setResponses({
#         204: {
#             'description': 'success'
#         }
#     })
#
#     def delete(self, controller, data, *args, **kwargs):
#         """
#         Delete all tasks
#         Delete all tasks
#         """
#         task_manager = controller.get_task_manager()
#         resp = task_manager.delete_task_instances()
#         return (resp, 204)

# ## delete
# class DeleteTask(TaskApiView):
#     definitions = {
#         'GetApiObjectRequestSchema': GetApiObjectRequestSchema,
#     }
#     parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
#     responses = SwaggerApiView.setResponses({
#         204: {
#             'description': 'success'
#         }
#     })
#
#     def delete(self, controller, data, oid, *args, **kwargs):
#         """
#         Delete task
#         Delete task by id
#         """
#         task_manager = controller.get_task_manager()
#         resp = task_manager.delete_task_instance(oid)
#         return (resp, 204)

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


class RunTestTaskBodyParamRequestSchema(Schema):
    x = fields.Integer(required=True, default=2)
    y = fields.Integer(required=True, default=223)
    numbers = fields.List(fields.Integer(default=1), required=True)
    mul_numbers = fields.List(fields.Integer(default=1), required=True)
    error = fields.Boolean(required=False, default=False, missing=False)
    suberror = fields.Boolean(required=False, default=False, missing=False)


class RunTestTaskBodyRequestSchema(Schema):
    body = fields.Nested(RunTestTaskBodyParamRequestSchema, context="body")


class RunTestTask(TaskApiView):
    summary = "Run test task"
    description = "Run test task"
    definitions = {
        "RunTestTaskBodyParamRequestSchema": RunTestTaskBodyParamRequestSchema,
        "RunTestTaskBodyRequestSchema": RunTestTaskBodyRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(RunTestTaskBodyRequestSchema)
    parameters_schema = RunTestTaskBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiJobResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        task = task_manager.run_test_task(data)
        return {"taskid": task.id}, 201


class RunTest2TaskBodyParamRequestSchema(Schema):
    pass


class RunTest2TaskBodyRequestSchema(Schema):
    body = fields.Nested(RunTest2TaskBodyParamRequestSchema, context="body")


class RunTest2ResponseSchema(Schema):
    schedule_name = fields.String(required=True, example="prova", description="schedule name")


class RunTest2Task(TaskApiView):
    summary = "Run test task"
    description = "Run test task"
    definitions = {
        "RunTest2TaskBodyRequestSchema": RunTest2TaskBodyRequestSchema,
        "RunTest2ResponseSchema": RunTest2ResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(RunTest2TaskBodyRequestSchema)
    parameters_schema = RunTest2TaskBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": RunTest2ResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        schedule_name = task_manager.run_test_scheduled_action()
        return {"schedule_name": schedule_name}, 200


class RunTestInlineTaskBodyParamRequestSchema(Schema):
    x = fields.Integer(required=True, default=2)
    y = fields.Integer(required=True, default=223)


class RunTestInlineTaskBodyRequestSchema(Schema):
    body = fields.Nested(RunTestInlineTaskBodyParamRequestSchema, context="body")


class RunTestInlineTask(TaskApiView):
    summary = "Run test task"
    description = "Run test task"
    definitions = {
        "RunTestInlineTaskBodyParamRequestSchema": RunTestInlineTaskBodyParamRequestSchema,
        "RunTestInlineTaskBodyRequestSchema": RunTestInlineTaskBodyRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(RunTestInlineTaskBodyRequestSchema)
    parameters_schema = RunTestInlineTaskBodyParamRequestSchema
    responses = SwaggerApiView.setResponses({201: {"description": "success", "schema": CrudApiJobResponseSchema}})

    def post(self, controller, data, *args, **kwargs):
        from beehive.module.scheduler_v2.controller import TaskManager

        task_manager: TaskManager = controller.get_task_manager()
        res = task_manager.run_test_inline_task(data)
        return res


class SchedulerAPI(ApiView):
    """Task scheduler api"""

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
    """Task manager api"""

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("%s/worker/ping" % module.base_path, "GET", ManagerPing, {}),
            ("%s/worker/stats" % module.base_path, "GET", ManagerStats, {}),
            ("%s/worker/report" % module.base_path, "GET", ManagerReport, {}),
            ("%s/worker/queues" % module.base_path, "GET", ManagerActiveQueues, {}),
            ("%s/worker/tasks" % module.base_path, "GET", GetTasks, {}),
            (
                "%s/worker/tasks/definitions" % module.base_path,
                "GET",
                GetTasksDefinition,
                {},
            ),
            ("%s/worker/tasks/<oid>" % module.base_path, "GET", GetTask, {}),
            (
                "%s/worker/tasks/<oid>/status" % module.base_path,
                "GET",
                GetTaskStatus,
                {},
            ),
            ("%s/worker/tasks/<oid>/trace" % module.base_path, "GET", GetTrace, {}),
            ("%s/worker/tasks/<oid>/log" % module.base_path, "GET", GetLog, {}),
            # ('%s/worker/tasks/<oid>/graph' % module.base_path, 'GET', GetTaskGraph, {}),
            # ('%s/worker/tasks' % module.base_path, 'DELETE', PurgeAllTasks, {}),
            # ('%s/worker/tasks/<oid>' % module.base_path, 'DELETE', DeleteTask, {}),
            ("%s/worker/tasks/test" % module.base_path, "POST", RunTestTask, {}),
            ("%s/worker/tasks/test2" % module.base_path, "POST", RunTest2Task, {}),
            ("%s/worker/tasks/test3" % module.base_path, "POST", RunTestInlineTask, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
