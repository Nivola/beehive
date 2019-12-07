# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema, \
    PaginatedResponseSchema, SwaggerApiView, GetApiObjectRequestSchema, ApiManagerError
from marshmallow import fields, Schema
from marshmallow.validate import OneOf
from beecell.swagger import SwaggerHelper


#
# event
#
class ListEventsRequestSchema(PaginatedRequestQuerySchema):   
    type = fields.String(default='API', context='query', description='event type')
    objid = fields.String(default='3638282dh82//dhedhw7d8we', context='query', description='authorization object id')
    objdef = fields.String(default='CatalogEndpoint', context='query', description='authorization object definition')
    objtype = fields.String(default='directory', context='query', description='authorization object type')
    date = fields.DateTime(default='1985-04-12T23:20:50.52Z', context='query')
    datefrom = fields.DateTime(default='1985-04-12T23:20:50.52Z', context='query')
    dateto = fields.DateTime(default='1985-04-12T23:20:50.52Z', context='query')
    source = fields.String(default='{}', context='query', description='event source')
    dest = fields.String(default='{}', context='query', description='event destination')
    data = fields.String(default='{}', context='query', description='event data')
    field = fields.String(validate=OneOf(['id', 'uuid', 'objid', 'name'], error='Field can be id, uuid, objid, name'),
                          description='entities list order field. Ex. id, uuid, name',
                          default='id', example='id', missing='id', context='query')


class EventsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=1)
    event_id = fields.String(required=True, default='384jnd7d4')
    type = fields.String(required=True, default='API')
    objid = fields.String(required=True, default='3638282dh82//dhedhw7d8we')
    objdef = fields.String(required=True, default='CatalogEndpoint')
    objtype = fields.String(required=True, default='directory')
    date = fields.DateTime(required=True, default='1985-04-12T23:20:50.52Z')
    data = fields.Dict(required=True)
    source = fields.Dict(required=True)
    dest = fields.Dict(required=True)


class ListEventsResponseSchema(PaginatedResponseSchema):
    events = fields.Nested(EventsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListEvents(SwaggerApiView):
    tags = ['event']
    definitions = {
        'ListEventsResponseSchema': ListEventsResponseSchema,
        'ListEventsRequestSchema': ListEventsRequestSchema
    }
    parameters = SwaggerHelper().get_parameters(ListEventsRequestSchema)
    parameters_schema = ListEventsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListEventsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List events
        Call this api to list all the existing events
        """
        objdef = data.get('objdef', None)
        objtype = data.get('objtype', None)
        if objdef is not None and objtype is None:
            raise ApiManagerError('objdef filter param require also objtype')
        events, total = controller.get_events(**data)
        res = [r.info() for r in events]
        return self.format_paginated_response(res, 'events', total, **data)


class GetEventResponseSchema(Schema):
    event = fields.Nested(EventsParamsResponseSchema, required=True, allow_none=True)


class GetEvent(SwaggerApiView):
    tags = ['event']
    definitions = {
        'GetEventResponseSchema': GetEventResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetEventResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        event = controller.get_event(oid)
        res = event.detail()
        resp = {'event':res}        
        return resp


# types
class GetEventTypesResponseSchema(Schema):
    count = fields.Integer()
    event_types = fields.List(fields.String)


class GetEventTypes(SwaggerApiView):
    tags = ['event']
    definitions = {
        'GetEventTypesResponseSchema': GetEventTypesResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetEventTypesResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):    
        resp = controller.get_event_types()
        return {'event_types': resp,
                'count': len(resp)}


class GetEventEntityDefinitionResponseSchema(Schema):
    count = fields.Integer()
    event_entities = fields.List(fields.String)


class GetEventEntityDefinition(SwaggerApiView):
    tags = ['event']
    definitions = {
        'GetEventEntityDefinitionResponseSchema': GetEventEntityDefinitionResponseSchema,
    }
    # parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetEventEntityDefinitionResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):    
        resp = controller.get_entity_definitions()
        return {'event_entities': resp,
                'count': len(resp)}


class EventAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('%s/events' % module.base_path, 'GET', ListEvents, {}),
            ('%s/events/<oid>' % module.base_path, 'GET', GetEvent, {}),
            ('%s/events/types' % module.base_path, 'GET', GetEventTypes, {}),
            ('%s/events/entities' % module.base_path, 'GET', GetEventEntityDefinition, {}),
        ]

        ApiView.register_api(module, rules)
