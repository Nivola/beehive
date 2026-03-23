# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    ApiManagerError,
)
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range
from beecell.swagger import SwaggerHelper
from .controller import EventController, EventDbManager


#
# event
#
class ListEventsRequestSchema(PaginatedRequestQuerySchema):
    type = fields.String(dump_default="API", context="query",
                         metadata={"description": "event type"})
    objid = fields.String(
        dump_default="3638282dh82//dhedhw7d8we",
        context="query",
        description="authorization object id",
    )
    objdef = fields.String(
        dump_default="CatalogEndpoint",
        context="query",
        description="authorization object definition",
    )
    objtype = fields.String(dump_default="directory", context="query",
                            metadata={"description": "authorization object type"})
    date = fields.DateTime(dump_default="1985-04-12T23:20:50.52Z", context="query")
    datefrom = fields.DateTime(dump_default="1985-04-12T23:20:50.52Z", context="query")
    dateto = fields.DateTime(dump_default="1985-04-12T23:20:50.52Z", context="query")
    source = fields.String(dump_default="{}", context="query",
                           metadata={"description": "event source"})
    dest = fields.String(dump_default="{}", context="query",
                         metadata={"description": "event destination"})
    data = fields.String(dump_default="{}", context="query",
                         metadata={"description": "event data"})
    field = fields.String(
        validate=OneOf(["id", "uuid", "objid", "name"], error="Field can be id, uuid, objid, name"),
        description="entities list order field. Ex. id, uuid, name",
        dump_default="id",
        example="id",
        load_default="id",
        context="query",
    )


class EventsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, dump_default=1)
    event_id = fields.String(required=True, dump_default="384jnd7d4")
    type = fields.String(required=True, dump_default="API")
    objid = fields.String(required=True, dump_default="3638282dh82//dhedhw7d8we")
    objdef = fields.String(required=True, dump_default="CatalogEndpoint")
    objtype = fields.String(required=True, dump_default="directory")
    date = fields.DateTime(required=True, dump_default="1985-04-12T23:20:50.52Z")
    data = fields.Dict(required=True)
    source = fields.Dict(required=True)
    dest = fields.Dict(required=True)


class ListEventsResponseSchema(PaginatedResponseSchema):
    events = fields.Nested(EventsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListEvents(SwaggerApiView):
    summary = "List events"
    description = "List events"
    tags = ["event"]
    definitions = {
        "ListEventsResponseSchema": ListEventsResponseSchema,
        "ListEventsRequestSchema": ListEventsRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListEventsRequestSchema)
    parameters_schema = ListEventsRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListEventsResponseSchema}})

    def get(self, controller: EventController, data, *args, **kwargs):
        objdef = data.get("objdef", None)
        objtype = data.get("objtype", None)
        if objdef is not None and objtype is None:
            raise ApiManagerError("objdef filter param require also objtype")
        # events, total = controller.get_events(**data)
        # res = [r.info() for r in events]
        # return self.format_paginated_response(res, "events", total, **data)
        return self.format_paginated_response([], "events", 0, **data)


class GetEventResponseSchema(Schema):
    event = fields.Nested(EventsParamsResponseSchema, required=True, allow_none=True)


class GetEvent(SwaggerApiView):
    summary = "Get event"
    description = "Get event"
    tags = ["event"]
    definitions = {
        "GetEventResponseSchema": GetEventResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetEventResponseSchema}})

    def get(self, controller: EventController, data, oid, *args, **kwargs):
        event = controller.get_event(oid)
        res = event.detail()
        resp = {"event": res}
        return resp


class GetEventTypesResponseSchema(Schema):
    count = fields.Integer()
    event_types = fields.List(fields.String)


class GetEventTypes(SwaggerApiView):
    summary = "Get event types"
    description = "Get event types"
    tags = ["event"]
    definitions = {
        "GetEventTypesResponseSchema": GetEventTypesResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetEventTypesResponseSchema}})

    def get(self, controller: EventController, data, *args, **kwargs):
        resp = controller.get_event_types()
        return {"event_types": list(resp), "count": len(resp)}


class GetEventEntityDefinitionResponseSchema(Schema):
    count = fields.Integer()
    event_entities = fields.List(fields.String)


class GetEventEntityDefinition(SwaggerApiView):
    summary = "Get event entity definitions"
    description = "Get event entity definitions"
    tags = ["event"]
    definitions = {
        "GetEventEntityDefinitionResponseSchema": GetEventEntityDefinitionResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses(
        {
            200: {
                "description": "success",
                "schema": GetEventEntityDefinitionResponseSchema,
            }
        }
    )

    def get(self, controller: EventController, data, *args, **kwargs):
        resp = controller.get_entity_definitions()
        return {"event_entities": resp, "count": len(resp)}


#
# api event
#
class ListApisRequestSchema(PaginatedRequestQuerySchema):
    eventid = fields.String(metadata={"example": "1f2435a8ad", "description": "api event id"}, context="query")
    uri = fields.String(metadata={"example": "/v1.0/nes/apis:GET", "description": "api uri:method"}, context="query")
    user = fields.String(metadata={"example": "guest", "description": "api source user"}, context="query")
    ip = fields.String(metadata={"example": "10.10.10.10", "description": "api source ip"}, context="query")
    pod = fields.String(
        example="uwsgi-resource-app-69f86b989-g2md",
        context="query",
        description="api destination pod",
    )


class ApisParamsResponseSchema(Schema):
    id = fields.Integer(required=True,
                        metadata={"example": "5c958c4605", "description": "event id"})
    type = fields.String(required=True,
                         metadata={"example": "API", "description": "event type"})
    creation = fields.DateTime(required=True,
                               metadata={"example": "1985-04-12T23:20:50.52Z"})
    data = fields.Dict(required=True,
                       metadata={"description": "event internal data"})
    source = fields.Dict(required=True,
                         metadata={"description": "event source info"})
    dest = fields.Dict(required=True,
                       metadata={"description": "event destination info"})


class ListApisResponseSchema(PaginatedResponseSchema):
    apis = fields.Nested(ApisParamsResponseSchema, many=True, required=True, allow_none=True)


class ListApis(SwaggerApiView):
    summary = "List api events"
    description = "List api events"
    tags = ["event"]
    definitions = {
        "ListApisResponseSchema": ListApisResponseSchema,
        "ListApisRequestSchema": ListApisRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListApisRequestSchema)
    parameters_schema = ListApisRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ListApisResponseSchema}})

    def get(self, controller: EventController, data, *args, **kwargs):
        apis, total = controller.get_api_events(**data)
        return self.format_paginated_response(apis, "apis", total, **data)


class GetApiLogLineResponseSchema(PaginatedResponseSchema):
    values = fields.List(fields.String, required=True,
                         metadata={"example": "some text", "description": "log message"})


class GetApiLogResponseSchema(Schema):
    task_log = fields.Nested(GetApiLogLineResponseSchema, required=True, allow_none=True)


class GetApiLogRequestSchema(Schema):
    oid = fields.String(
        example="4d5e87cd-0139-400d-a787-5a15eba786e9",
        context="path",
        description="task id",
    )
    size = fields.Integer(
        dump_default=20,
        example=20,
        load_default=20,
        context="query",
        description="log list page size. -1 to get all the logs",
        validate=Range(min=-1, max=1000, error="Size is out from range"),
    )
    page = fields.Integer(
        dump_default=0,
        example=0,
        load_default=0,
        context="query",
        description="log list page selected",
        validate=Range(min=0, max=10000, error="Page is out from range"),
    )


class GetApiLog(SwaggerApiView):
    summary = "List api events"
    description = "List api events"
    tags = ["event"]
    definitions = {
        "GetApiLogResponseSchema": GetApiLogResponseSchema,
        "GetApiLogRequestSchema": GetApiLogRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiLogRequestSchema)
    parameters_schema = GetApiLogRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": GetApiLogResponseSchema}})

    def get(self, controller: EventController, data, oid, *args, **kwargs):
        apis = controller.get_api_event_logs(oid, **data)
        resp = {"api_log": apis}
        return resp


class EventAPI(ApiView):
    """Event api"""

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("%s/events" % module.base_path, "GET", ListEvents, {}),
            ("%s/events/<oid>" % module.base_path, "GET", GetEvent, {}),
            ("%s/events/types" % module.base_path, "GET", GetEventTypes, {}),
            (
                "%s/events/entities" % module.base_path,
                "GET",
                GetEventEntityDefinition,
                {},
            ),
            ("%s/apis" % module.base_path, "GET", ListApis, {}),
            ("%s/apis/<oid>/log" % module.base_path, "GET", GetApiLog, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
