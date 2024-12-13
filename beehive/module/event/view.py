# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.apimanager import (
    ApiView,
    PaginatedRequestQuerySchema,
    PaginatedResponseSchema,
    SwaggerApiView,
    GetApiObjectRequestSchema,
    ApiManagerError,
)
from marshmallow import fields, Schema
from marshmallow.validate import OneOf, Range
from beecell.swagger import SwaggerHelper


#
# event
#
class ListEventsRequestSchema(PaginatedRequestQuerySchema):
    type = fields.String(default="API", context="query", description="event type")
    objid = fields.String(
        default="3638282dh82//dhedhw7d8we",
        context="query",
        description="authorization object id",
    )
    objdef = fields.String(
        default="CatalogEndpoint",
        context="query",
        description="authorization object definition",
    )
    objtype = fields.String(default="directory", context="query", description="authorization object type")
    date = fields.DateTime(default="1985-04-12T23:20:50.52Z", context="query")
    datefrom = fields.DateTime(default="1985-04-12T23:20:50.52Z", context="query")
    dateto = fields.DateTime(default="1985-04-12T23:20:50.52Z", context="query")
    source = fields.String(default="{}", context="query", description="event source")
    dest = fields.String(default="{}", context="query", description="event destination")
    data = fields.String(default="{}", context="query", description="event data")
    field = fields.String(
        validate=OneOf(["id", "uuid", "objid", "name"], error="Field can be id, uuid, objid, name"),
        description="entities list order field. Ex. id, uuid, name",
        default="id",
        example="id",
        missing="id",
        context="query",
    )


class EventsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=1)
    event_id = fields.String(required=True, default="384jnd7d4")
    type = fields.String(required=True, default="API")
    objid = fields.String(required=True, default="3638282dh82//dhedhw7d8we")
    objdef = fields.String(required=True, default="CatalogEndpoint")
    objtype = fields.String(required=True, default="directory")
    date = fields.DateTime(required=True, default="1985-04-12T23:20:50.52Z")
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

    def get(self, controller, data, *args, **kwargs):
        objdef = data.get("objdef", None)
        objtype = data.get("objtype", None)
        if objdef is not None and objtype is None:
            raise ApiManagerError("objdef filter param require also objtype")
        events, total = controller.get_events(**data)
        res = [r.info() for r in events]
        return self.format_paginated_response(res, "events", total, **data)


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

    def get(self, controller, data, oid, *args, **kwargs):
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

    def get(self, controller, data, *args, **kwargs):
        resp = controller.get_event_types()
        return {"event_types": resp, "count": len(resp)}


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

    def get(self, controller, data, *args, **kwargs):
        resp = controller.get_entity_definitions()
        return {"event_entities": resp, "count": len(resp)}


#
# api event
#
class ListApisRequestSchema(PaginatedRequestQuerySchema):
    eventid = fields.String(example="1f2435a8ad", context="query", description="api event id")
    uri = fields.String(example="/v1.0/nes/apis:GET", context="query", description="api uri:method")
    user = fields.String(example="guest", context="query", description="api source user")
    ip = fields.String(example="10.10.10.10", context="query", description="api source ip")
    pod = fields.String(
        example="uwsgi-resource-app-69f86b989-g2md",
        context="query",
        description="api destination pod",
    )


class ApisParamsResponseSchema(Schema):
    id = fields.Integer(required=True, example="5c958c4605", description="event id")
    type = fields.String(required=True, example="API", description="event type")
    creation = fields.DateTime(required=True, example="1985-04-12T23:20:50.52Z")
    data = fields.Dict(required=True, description="event internal data")
    source = fields.Dict(required=True, description="event source info")
    dest = fields.Dict(required=True, description="event destination info")


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

    def get(self, controller, data, *args, **kwargs):
        apis, total = controller.get_api_events(**data)
        return self.format_paginated_response(apis, "apis", total, **data)


class GetApiLogLineResponseSchema(PaginatedResponseSchema):
    values = fields.List(fields.String, required=True, example="some text", description="log message")


class GetApiLogResponseSchema(Schema):
    task_log = fields.Nested(GetApiLogLineResponseSchema, required=True, allow_none=True)


class GetApiLogRequestSchema(Schema):
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

    def get(self, controller, data, oid, *args, **kwargs):
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
