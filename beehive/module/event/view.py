"""
Created on Aug 13, 2014

@author: darkbk
"""
from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    GetApiObjectRequestSchema, ApiObjectPermsResponseSchema,\
    ApiObjectPermsRequestSchema
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from flasgger.marshmallow_apispec import SwaggerView


#
# event
#
## list
class ListEventsRequestSchema(PaginatedRequestQuerySchema):   
    type = fields.String(default=u'API', context=u'query')
    objid = fields.String(default=u'3638282dh82//dhedhw7d8we', context=u'query')
    objdef = fields.String(default=u'CatalogEndpoint', context=u'query')
    objtype = fields.String(default=u'directory', context=u'query')
    date = fields.DateTime(default=u'1985-04-12T23:20:50.52Z', context=u'query')
    datefrom = fields.DateTime(default=u'1985-04-12T23:20:50.52Z', context=u'query')
    dateto = fields.DateTime(default=u'1985-04-12T23:20:50.52Z', context=u'query')
    source = fields.String(default=u'{}', context=u'query')
    dest = fields.String(default=u'{}', context=u'query')
    data = fields.String(default=u'{}', context=u'query')


class EventsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=1)
    event_id = fields.String(required=True, default=u'384jnd7d4')
    type = fields.String(required=True, default=u'API')
    objid = fields.String(required=True, default=u'3638282dh82//dhedhw7d8we')
    objdef = fields.String(required=True, default=u'CatalogEndpoint')
    objtype = fields.String(required=True, default=u'directory')
    date = fields.DateTime(required=True, default=u'1985-04-12T23:20:50.52Z')
    data = fields.Dict(required=True)
    source = fields.Dict(required=True)
    dest = fields.Dict(required=True)


class ListEventsResponseSchema(PaginatedResponseSchema):
    events = fields.Nested(EventsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListEvents(SwaggerApiView):
    tags = [u'event']
    definitions = {
        u'ListEventsResponseSchema': ListEventsResponseSchema,
        u'ListEventsRequestSchema': ListEventsRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListEventsRequestSchema)
    parameters_schema = ListEventsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListEventsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List events
        Call this api to list all the existing events
        """            
        events, total = controller.get_events(**data)
        res = [r.info() for r in events]
        return self.format_paginated_response(res, u'events', total, **data)


class GetEventResponseSchema(Schema):
    event = fields.Nested(EventsParamsResponseSchema, required=True, allow_none=True)


class GetEvent(SwaggerApiView):
    tags = [u'event']
    definitions = {
        u'GetEventResponseSchema': GetEventResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetEventResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        event = controller.get_event(oid)
        res = event.detail()
        resp = {u'event':res}        
        return resp


# types
class GetEventTypesResponseSchema(Schema):
    count = fields.Integer()
    event_types = fields.List(fields.String)


class GetEventTypes(SwaggerApiView):
    tags = [u'event']
    definitions = {
        u'GetEventTypesResponseSchema': GetEventTypesResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetEventTypesResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):    
        resp = controller.get_event_types()
        return {u'event_types': resp,
                u'count': len(resp)}


class GetEventEntityDefinitionResponseSchema(Schema):
    count = fields.Integer()
    event_entities = fields.List(fields.String)


class GetEventEntityDefinition(SwaggerApiView):
    tags = [u'event']
    definitions = {
        u'GetEventEntityDefinitionResponseSchema': GetEventEntityDefinitionResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetEventEntityDefinitionResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):    
        resp = controller.get_entity_definitions()
        return {u'event_entities': resp,
                u'count': len(resp)}


class EventAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'%s/events' % module.base_path, u'GET', ListEvents, {}),
            (u'%s/events/<oid>' % module.base_path, u'GET', GetEvent, {}),
            (u'%s/events/types' % module.base_path, u'GET', GetEventTypes, {}),
            (u'%s/events/entities' % module.base_path, u'GET', GetEventEntityDefinition, {}),
        ]

        ApiView.register_api(module, rules)
