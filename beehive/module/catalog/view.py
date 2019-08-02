# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from flasgger.marshmallow_apispec import SwaggerView


#
# catalog
#
## list
class ListCatalogsRequestSchema(PaginatedRequestQuerySchema):
    zone = fields.String(context=u'query', default=u'internal')


class ListCatalogsParamsResponseSchema(ApiObjectResponseSchema):
    zone = fields.String(required=True, default=u'internal')


class ListCatalogsResponseSchema(PaginatedResponseSchema):
    catalogs = fields.Nested(ListCatalogsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListCatalogs(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'ListCatalogsResponseSchema': ListCatalogsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListCatalogsRequestSchema)
    parameters_schema = ListCatalogsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListCatalogsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List catalogs
        Call this api to list all the existing catalogs
        """            
        catalogs, total = controller.get_catalogs(**data)
        res = [r.info() for r in catalogs]
        return self.format_paginated_response(res, u'catalogs', total, **data)


## get
class GetCatalogParamsServicesResponseSchema(Schema):
    service = fields.String(required=True, default=u'auth')
    endpoints = fields.List(fields.String(default=u'http://localhost:6060'))


class GetCatalogParamsResponseSchema(ApiObjectResponseSchema):
    zone = fields.String(required=True, default=u'internal')
    services = fields.Nested(GetCatalogParamsServicesResponseSchema, many=True, required=True, allow_none=True)


class GetCatalogResponseSchema(Schema):
    catalog = fields.Nested(GetCatalogParamsResponseSchema, required=True, allow_none=True)


class GetCatalog(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'GetCatalogResponseSchema': GetCatalogResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetCatalogResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        res = catalog.detail()
        resp = {u'catalog':res}        
        return resp

## get perms
class GetCatalogPerms(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        res, total = catalog.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)


## create
class CreateCatalogParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=True)
    zone = fields.String(required=True)


class CreateCatalogRequestSchema(Schema):
    catalog = fields.Nested(CreateCatalogParamRequestSchema)


class CreateCatalogBodyRequestSchema(Schema):
    body = fields.Nested(CreateCatalogRequestSchema, context=u'body')


class CreateCatalog(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'CreateCatalogRequestSchema': CreateCatalogRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateCatalogBodyRequestSchema)
    parameters_schema = CreateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_catalog(**data.get(u'catalog'))
        return ({u'uuid':resp}, 201)


## update
class UpdateCatalogParamRequestSchema(Schema):
    name = fields.String()
    desc = fields.String()
    zone = fields.String()


class UpdateCatalogRequestSchema(Schema):
    catalog = fields.Nested(UpdateCatalogParamRequestSchema)


class UpdateCatalogBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateCatalogRequestSchema, context=u'body')


class UpdateCatalog(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'UpdateCatalogRequestSchema':UpdateCatalogRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateCatalogBodyRequestSchema)
    parameters_schema = UpdateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def put(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        resp = catalog.update(**data.get(u'catalog'))
        return {u'uuid':resp}
    
## delete
class DeleteCatalog(SwaggerApiView):
    tags = [u'directory']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    def delete(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        resp = catalog.delete()
        return (resp, 204)


#
# endpoint
#
class ListEndpointsRequestSchema(PaginatedRequestQuerySchema):
    service = fields.String(context=u'query')
    catalog = fields.String(context=u'query')


class ListEndpointsParamsCatalogResponseSchema(Schema):
    name = fields.String(required=True, default=u'test')
    uuid = fields.UUID(required=True, default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')


class ListEndpointsParamsResponseSchema(ApiObjectResponseSchema):
    catalog = fields.Nested(ListEndpointsParamsCatalogResponseSchema, required=True, allow_none=True)
    service = fields.String(required=True, default=u'auth')
    endpoint = fields.String(required=True, default=u'http://localhost:6060')


class ListEndpointsResponseSchema(PaginatedResponseSchema):
    endpoints = fields.Nested(ListEndpointsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListEndpoints(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'ListEndpointsResponseSchema': ListEndpointsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListEndpointsRequestSchema)
    parameters_schema = ListEndpointsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListEndpointsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        endpoints, total = controller.get_endpoints(**data)
        res = [r.info() for r in endpoints]
        return self.format_paginated_response(res, u'endpoints', total, **data)


## get
class GetEndpointResponseSchema(Schema):
    endpoint = fields.Nested(ListEndpointsParamsResponseSchema, required=True, allow_none=True)


class GetEndpoint(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'GetEndpointResponseSchema': GetEndpointResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetEndpointResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):      
        endpoint = controller.get_endpoint(oid)
        res = endpoint.detail()
        resp = {u'endpoint':res}        
        return resp
        
## get perms
class GetEndpointPerms(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        u'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ApiObjectPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        res, total = endpoint.authorization(**data)
        return self.format_paginated_response(res, u'perms', total, **data)    


## create
class CreateEndpointParamRequestSchema(Schema):
    name = fields.String()
    desc = fields.String()
    catalog = fields.String()
    service = fields.String()
    uri = fields.String()
    active = fields.Boolean()


class CreateEndpointRequestSchema(Schema):
    endpoint = fields.Nested(CreateEndpointParamRequestSchema)


class CreateEndpointBodyRequestSchema(Schema):
    body = fields.Nested(CreateEndpointRequestSchema, context=u'body')


class CreateEndpoint(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'CreateEndpointRequestSchema': CreateEndpointRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateEndpointBodyRequestSchema)
    parameters_schema = CreateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        data = data.get(u'endpoint')
        endpoint = data.pop(u'catalog')
        endpoint_obj = controller.get_catalog(endpoint)
        resp = endpoint_obj.add_endpoint(**data)
        return ({u'uuid':resp}, 201)


## update
class UpdateEndpointParamRequestSchema(Schema):
    name = fields.String()
    desc = fields.String()
    service = fields.String()
    uri = fields.String()
    active = fields.Boolean() 


class UpdateEndpointRequestSchema(Schema):
    endpoint = fields.Nested(UpdateEndpointParamRequestSchema)


class UpdateEndpointBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateEndpointRequestSchema, context=u'body')


class UpdateEndpoint(SwaggerApiView):
    tags = [u'directory']
    definitions = {
        u'UpdateEndpointRequestSchema':UpdateEndpointRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateEndpointBodyRequestSchema)
    parameters_schema = UpdateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
               
    def put(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        resp = endpoint.update(**data.get(u'endpoint'))
        return {u'uuid':resp}
    
## delete
class DeleteEndpoint(SwaggerApiView):
    tags = [u'directory']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    def delete(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        resp = endpoint.delete()
        return (resp, 204)

class CatalogAPI(ApiView):
    """CatalogAPI
    """
    @staticmethod
    def register_api(module):
        base = u'directory'
        rules = [
            # (u'%s/catalogs' % base, u'GET', ListCatalogs, {}),
            # (u'%s/catalogs/<oid>' % base, u'GET', GetCatalog, {}),
            # #('%s/catalog/<oid>/<zone>' % base, 'GET', FilterCatalog, {}),
            # (u'%s/catalogs/<oid>/perms' % base, u'GET', GetCatalogPerms, {}),
            # (u'%s/catalogs' % base, u'POST', CreateCatalog, {}),
            # (u'%s/catalogs/<oid>' % base, u'PUT', UpdateCatalog, {}),
            # (u'%s/catalogs/<oid>' % base, u'DELETE', DeleteCatalog, {}),
            # #('%s/catalogs/<oid>/services' % base, 'GET', GetCatalogServices, {}),
            #
            # (u'%s/endpoints' % base, u'GET', ListEndpoints, {}),
            # (u'%s/endpoints/<oid>' % base, u'GET', GetEndpoint, {}),
            # (u'%s/endpoints/<oid>/perms' % base, u'GET', GetEndpointPerms, {}),
            # (u'%s/endpoints' % base, u'POST', CreateEndpoint, {}),
            # (u'%s/endpoints/<oid>' % base, u'PUT', UpdateEndpoint, {}),
            # (u'%s/endpoints/<oid>' % base, u'DELETE', DeleteEndpoint, {}),

            # new routes
            (u'%s/catalogs' % module.base_path, u'GET', ListCatalogs, {}),
            (u'%s/catalogs/<oid>' % module.base_path, u'GET', GetCatalog, {}),
            # ('%s/catalog/<oid>/<zone>' % module.base_path, 'GET', FilterCatalog, {}),
            (u'%s/catalogs/<oid>/perms' % module.base_path, u'GET', GetCatalogPerms, {}),
            (u'%s/catalogs' % module.base_path, u'POST', CreateCatalog, {}),
            (u'%s/catalogs/<oid>' % module.base_path, u'PUT', UpdateCatalog, {}),
            (u'%s/catalogs/<oid>' % module.base_path, u'DELETE', DeleteCatalog, {}),
            # ('%s/catalogs/<oid>/services' % module.base_path, 'GET', GetCatalogServices, {}),

            (u'%s/endpoints' % module.base_path, u'GET', ListEndpoints, {}),
            (u'%s/endpoints/<oid>' % module.base_path, u'GET', GetEndpoint, {}),
            (u'%s/endpoints/<oid>/perms' % module.base_path, u'GET', GetEndpointPerms, {}),
            (u'%s/endpoints' % module.base_path, u'POST', CreateEndpoint, {}),
            (u'%s/endpoints/<oid>' % module.base_path, u'PUT', UpdateEndpoint, {}),
            (u'%s/endpoints/<oid>' % module.base_path, u'DELETE', DeleteEndpoint, {}),
        ]

        ApiView.register_api(module, rules)