"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CreateApiObjectResponseSchema, GetApiObjectRequestSchema
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

class ListCatalogsResponseSchema(PaginatedResponseSchema):
    catalogs = fields.Nested(ApiObjectResponseSchema, many=True)

class ListCatalogs(SwaggerApiView):
    tags = [u'catalog']
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
class GetCatalogResponseSchema(Schema):
    catalog = fields.Nested(ApiObjectResponseSchema)

class GetCatalog(SwaggerApiView):
    tags = [u'authorization']
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
        catalog = self.controller.get_catalog(oid)
        res = catalog.detail()
        resp = {u'catalog':res}        
        return resp
              
## get perms
class GetCatalogPermsResponseSchema(Schema):
    perms = fields.Nested(ApiObjectResponseSchema)

class GetCatalogPerms(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetCatalogResponseSchema': GetCatalogPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetCatalogPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        res, total = catalog.authorization()
        return self.format_paginated_response(res, u'perms', total, **data)

## create
class CreateCatalogParamRequestSchema(BaseCreateRequestSchema, 
                                      BaseCreateExtendedParamRequestSchema):
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                          error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'),
                          missing=u'DBUSER')
    base = fields.Boolean(missing=True)
    system = fields.Boolean()
    
    @validates(u'name')
    def validate_catalog(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'Catalog name syntax must be <name>@<domain>') 

class CreateCatalogRequestSchema(Schema):
    catalog = fields.Nested(CreateCatalogParamRequestSchema, context=u'body')
    
class CreateCatalogBodyRequestSchema(Schema):
    body = fields.Nested(CreateCatalogRequestSchema, context=u'body')

class CreateCatalog(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateCatalogRequestSchema': CreateCatalogRequestSchema,
        u'CreateApiObjectResponseSchema':CreateApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateCatalogBodyRequestSchema)
    parameters_schema = CreateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_catalog(**data.get(u'catalog'))
        return (resp, 201)

## update
class UpdateCatalogParamRoleRequestSchema(Schema):
    append = fields.List(fields.List(fields.String()))
    remove = fields.List(fields.String())
    
class UpdateCatalogParamRequestSchema(BaseUpdateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    oid = fields.String()
    roles = fields.Nested(UpdateCatalogParamRoleRequestSchema)
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    
    @validates(u'name')
    def validate_catalog(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'Catalog name syntax must be <name>@<domain>')     

class UpdateCatalogRequestSchema(Schema):
    catalog = fields.Nested(UpdateCatalogParamRequestSchema)

class UpdateCatalogBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateCatalogRequestSchema, context=u'body')
    
class UpdateCatalogResponseSchema(Schema):
    update = fields.Integer(default=67)
    role_append = fields.List(fields.String, dump_to=u'role_append')
    role_remove = fields.List(fields.String, dump_to=u'role_remove')
    
class UpdateCatalog(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateCatalogRequestSchema':UpdateCatalogRequestSchema,
        u'UpdateCatalogResponseSchema':UpdateCatalogResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateCatalogBodyRequestSchema)
    parameters_schema = UpdateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': UpdateCatalogResponseSchema
        }
    })
    
    def put(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        data = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        zone = get_value(data, u'zone', None)
        resp = catalog.update(name=name, desc=desc, zone=zone)
        return resp
    
## delete
class DeleteCatalog(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    def delete(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        resp = catalog.delete()
        return (resp, 204)

#
# endpoint
#
class ListEndpointsRequestSchema(PaginatedRequestQuerySchema):
    endpoint = fields.String(context=u'query')
    role = fields.String(context=u'query')
    active = fields.Boolean(context=u'query')
    expiry_date = fields.String(load_from=u'expirydate', default=u'2099-12-31',
                                context=u'query')

class ListEndpointsResponseSchema(PaginatedResponseSchema):
    endpoints = fields.Nested(ApiObjectResponseSchema, many=True)

class ListEndpoints(SwaggerApiView):
    tags = [u'authorization']
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
        headers = request.headers
        name = get_attrib(headers, u'name', None)
        service = get_attrib(headers, u'service', None)       
        catalog = get_attrib(headers, u'catalog', None)          
        endpoints = controller.get_endpoints(name=name, 
                                             service=service, 
                                             catalog_id=catalog)
        endpoints, total = controller.get_endpoints(name=name)
        res = [r.info() for r in endpoints]
        return self.format_paginated_response(res, u'endpoints', total, **data)

## get
class GetEndpointResponseSchema(Schema):
    endpoint = fields.Nested(ApiObjectResponseSchema)

class GetEndpoint(SwaggerApiView):
    tags = [u'authorization']
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
        endpoint = self.controller.get_endpoint(oid)
        res = endpoint.detail()
        resp = {u'endpoint':res}        
        return resp
              
## get
class GetEndpointPermsResponseSchema(Schema):
    perms = fields.Nested(ApiObjectResponseSchema)

class GetEndpointPerms(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetEndpointResponseSchema': GetEndpointPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetEndpointPermsResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        res, total = endpoint.authorization()
        return self.format_paginated_response(res, u'perms', total, **data)

## create
class CreateEndpointParamRequestSchema(BaseCreateRequestSchema, 
                                      BaseCreateExtendedParamRequestSchema):
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                          error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'),
                          missing=u'DBUSER')
    base = fields.Boolean(missing=True)
    system = fields.Boolean()
    
    @validates(u'name')
    def validate_endpoint(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'Endpoint name syntax must be <name>@<domain>') 

class CreateEndpointRequestSchema(Schema):
    endpoint = fields.Nested(CreateEndpointParamRequestSchema, context=u'body')
    
class CreateEndpointBodyRequestSchema(Schema):
    body = fields.Nested(CreateEndpointRequestSchema, context=u'body')

class CreateEndpoint(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateEndpointRequestSchema': CreateEndpointRequestSchema,
        u'CreateApiObjectResponseSchema':CreateApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateEndpointBodyRequestSchema)
    parameters_schema = CreateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        service = get_value(data, u'service', None, exception=True)
        uri = get_value(data, u'uri', None, exception=True)
        active = get_value(data, u'active', True)
        catalog_obj = self.get_catalog(controller, catalog)
        resp = catalog_obj.add_endpoint(name, desc, service, uri, active)
        return (resp, 201)

## update
class UpdateEndpointParamRoleRequestSchema(Schema):
    append = fields.List(fields.List(fields.String()))
    remove = fields.List(fields.String())
    
class UpdateEndpointParamRequestSchema(BaseUpdateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    oid = fields.String()
    roles = fields.Nested(UpdateEndpointParamRoleRequestSchema)
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    
    @validates(u'name')
    def validate_endpoint(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'Endpoint name syntax must be <name>@<domain>')     

class UpdateEndpointRequestSchema(Schema):
    endpoint = fields.Nested(UpdateEndpointParamRequestSchema)

class UpdateEndpointBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateEndpointRequestSchema, context=u'body')
    
class UpdateEndpointResponseSchema(Schema):
    update = fields.Integer(default=67)
    role_append = fields.List(fields.String, dump_to=u'role_append')
    role_remove = fields.List(fields.String, dump_to=u'role_remove')
    
class UpdateEndpoint(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateEndpointRequestSchema':UpdateEndpointRequestSchema,
        u'UpdateEndpointResponseSchema':UpdateEndpointResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateEndpointBodyRequestSchema)
    parameters_schema = UpdateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': UpdateEndpointResponseSchema
        }
    })
               
    def update(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        service = get_value(data, u'service', None)
        uri = get_value(data, u'uri', None)
        active = get_value(data, u'active', None)
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.update(name=name, desc=desc, 
                               service=service, uri=uri,
                               active=active, catalog=catalog)
        return resp
    
## delete
class DeleteEndpoint(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    def delete(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.delete()
        return (resp, 204)

class CatalogAPI(ApiView):
    """CatalogAPI
    """
    @staticmethod
    def register_api(module):
        base = u'dir'
        rules = [
            (u'%s/catalogs' % base, u'GET', ListCatalogs, {}),
            (u'%s/catalogs/<oid>' % base, u'GET', GetCatalog, {}),
            #('%s/catalog/<oid>/<zone>' % base, 'GET', FilterCatalog, {}),
            (u'%s/catalogs/<oid>/perms' % base, u'GET', GetCatalogPerms, {}),
            (u'%s/catalogs' % base, u'POST', CreateCatalog, {}),
            (u'%s/catalogs/<oid>' % base, u'PUT', UpdateCatalog, {}),
            (u'%s/catalogs/<oid>' % base, u'DELETE', DeleteCatalog, {}),
            #('%s/catalogs/<oid>/services' % base, 'GET', GetCatalogServices, {}),

            (u'%s/endpoints' % base, u'GET', ListEndpoints, {}),
            (u'%s/endpoint/<oid>' % base, u'GET', GetEndpoint, {}),
            (u'%s/endpoint/<oid>/perms' % base, u'GET', GetEndpointPerms, {}),
            (u'%s/endpoint' % base, u'POST', CreateEndpoint, {}),
            (u'%s/endpoint/<oid>' % base, u'PUT', UpdateEndpoint, {}),
            (u'%s/endpoint/<oid>' % base, u'DELETE', DeleteEndpoint, {}),
        ]

        ApiView.register_api(module, rules)