# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectPermsResponseSchema, ApiObjectPermsRequestSchema
from marshmallow import fields, Schema
from beecell.swagger import SwaggerHelper


#
# catalog
#
class ListCatalogsRequestSchema(PaginatedRequestQuerySchema):
    zone = fields.String(context='query', default='internal')


class ListCatalogsParamsResponseSchema(ApiObjectResponseSchema):
    zone = fields.String(required=True, default='internal')


class ListCatalogsResponseSchema(PaginatedResponseSchema):
    catalogs = fields.Nested(ListCatalogsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListCatalogs(SwaggerApiView):
    summary = 'List catalogs'
    description = 'List catalogs'
    tags = ['directory']
    definitions = {
        'ListCatalogsResponseSchema': ListCatalogsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListCatalogsRequestSchema)
    parameters_schema = ListCatalogsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListCatalogsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        catalogs, total = controller.get_catalogs(**data)
        res = [r.info() for r in catalogs]
        return self.format_paginated_response(res, 'catalogs', total, **data)


class GetCatalogParamsServicesResponseSchema(Schema):
    service = fields.String(required=True, default='auth')
    endpoints = fields.List(fields.String(default='http://localhost:6060'))


class GetCatalogParamsResponseSchema(ApiObjectResponseSchema):
    zone = fields.String(required=True, default='internal')
    services = fields.Nested(GetCatalogParamsServicesResponseSchema, many=True, required=True, allow_none=True)


class GetCatalogResponseSchema(Schema):
    catalog = fields.Nested(GetCatalogParamsResponseSchema, required=True, allow_none=True)


class GetCatalog(SwaggerApiView):
    summary = 'Get catalog'
    description = 'Get catalog'
    tags = ['directory']
    definitions = {
        'GetCatalogResponseSchema': GetCatalogResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetCatalogResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        res = catalog.detail()
        resp = {'catalog':res}
        return resp


class GetCatalogPerms(SwaggerApiView):
    summary = 'Get catalog permissions'
    description = 'Get catalog permissions'
    tags = ['directory']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = ApiObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        data.pop('oid', None)
        res, total = catalog.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


class CreateCatalogParamRequestSchema(Schema):
    name = fields.String(required=True)
    desc = fields.String(required=True)
    zone = fields.String(required=True)


class CreateCatalogRequestSchema(Schema):
    catalog = fields.Nested(CreateCatalogParamRequestSchema)


class CreateCatalogBodyRequestSchema(Schema):
    body = fields.Nested(CreateCatalogRequestSchema, context='body')


class CreateCatalog(SwaggerApiView):
    summary = 'Create catalog'
    description = 'Create catalog'
    tags = ['directory']
    definitions = {
        'CreateCatalogRequestSchema': CreateCatalogRequestSchema,
        'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateCatalogBodyRequestSchema)
    parameters_schema = CreateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        resp = controller.add_catalog(**data.get('catalog'))
        return {'uuid': resp}, 201


class UpdateCatalogParamRequestSchema(Schema):
    name = fields.String()
    desc = fields.String()
    zone = fields.String()


class UpdateCatalogRequestSchema(Schema):
    catalog = fields.Nested(UpdateCatalogParamRequestSchema)


class UpdateCatalogBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateCatalogRequestSchema, context='body')


class UpdateCatalog(SwaggerApiView):
    summary = 'Update catalog'
    description = 'Update catalog'
    tags = ['directory']
    definitions = {
        'UpdateCatalogRequestSchema': UpdateCatalogRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateCatalogBodyRequestSchema)
    parameters_schema = UpdateCatalogRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        catalog = controller.get_catalog(oid)
        resp = catalog.update(**data.get('catalog'))
        return {'uuid':resp}


class DeleteCatalog(SwaggerApiView):
    summary = 'Delete catalog'
    description = 'Delete catalog'
    tags = ['directory']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
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
    service = fields.String(context='query')
    catalog = fields.String(context='query')


class ListEndpointsParamsCatalogResponseSchema(Schema):
    name = fields.String(required=True, default='test')
    uuid = fields.UUID(required=True, default='6d960236-d280-46d2-817d-f3ce8f0aeff7')


class ListEndpointsParamsResponseSchema(ApiObjectResponseSchema):
    catalog = fields.Nested(ListEndpointsParamsCatalogResponseSchema, required=True, allow_none=True)
    service = fields.String(required=True, default='auth')
    endpoint = fields.String(required=True, default='http://localhost:6060')


class ListEndpointsResponseSchema(PaginatedResponseSchema):
    endpoints = fields.Nested(ListEndpointsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListEndpoints(SwaggerApiView):
    summary = 'List catalog endpoints'
    description = 'List catalog endpoints'
    tags = ['directory']
    definitions = {
        'ListEndpointsResponseSchema': ListEndpointsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListEndpointsRequestSchema)
    parameters_schema = ListEndpointsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListEndpointsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        endpoints, total = controller.get_endpoints(**data)
        res = [r.info() for r in endpoints]
        return self.format_paginated_response(res, 'endpoints', total, **data)


class GetEndpointResponseSchema(Schema):
    endpoint = fields.Nested(ListEndpointsParamsResponseSchema, required=True, allow_none=True)


class GetEndpoint(SwaggerApiView):
    summary = 'Get catalog endpoint'
    description = 'Get catalog endpoint'
    tags = ['directory']
    definitions = {
        'GetEndpointResponseSchema': GetEndpointResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetEndpointResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        res = endpoint.detail()
        resp = {'endpoint':res}
        return resp


class GetEndpointPerms(SwaggerApiView):
    summary = 'Get catalog endpoint permissions'
    description = 'Get catalog endpoint permissions'
    tags = ['directory']
    definitions = {
        'ApiObjectPermsRequestSchema': ApiObjectPermsRequestSchema,
        'ApiObjectPermsResponseSchema': ApiObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ApiObjectPermsRequestSchema)
    parameters_schema = PaginatedRequestQuerySchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ApiObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        res, total = endpoint.authorization(**data)
        return self.format_paginated_response(res, 'perms', total, **data)


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
    body = fields.Nested(CreateEndpointRequestSchema, context='body')


class CreateEndpoint(SwaggerApiView):
    summary = 'Create catalog endpoint'
    description = 'Create catalog endpoint'
    tags = ['directory']
    definitions = {
        'CreateEndpointRequestSchema': CreateEndpointRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateEndpointBodyRequestSchema)
    parameters_schema = CreateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        data = data.get('endpoint')
        endpoint = data.pop('catalog')
        endpoint_obj = controller.get_catalog(endpoint)
        resp = endpoint_obj.add_endpoint(**data)
        return ({'uuid':resp}, 201)


class UpdateEndpointParamRequestSchema(Schema):
    name = fields.String()
    desc = fields.String()
    service = fields.String()
    uri = fields.String()
    active = fields.Boolean()


class UpdateEndpointRequestSchema(Schema):
    endpoint = fields.Nested(UpdateEndpointParamRequestSchema)


class UpdateEndpointBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateEndpointRequestSchema, context='body')


class UpdateEndpoint(SwaggerApiView):
    summary = 'Update catalog endpoint'
    description = 'Update catalog endpoint'
    tags = ['directory']
    definitions = {
        'UpdateEndpointRequestSchema': UpdateEndpointRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateEndpointBodyRequestSchema)
    parameters_schema = UpdateEndpointRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        resp = endpoint.update(**data.get('endpoint'))
        return {'uuid': resp}


class DeleteEndpoint(SwaggerApiView):
    summary = 'Delete catalog endpoint'
    description = 'Delete catalog endpoint'
    tags = ['directory']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        endpoint = controller.get_endpoint(oid)
        resp = endpoint.delete()
        return resp, 204


class CatalogAPI(ApiView):
    """CatalogAPI
    """
    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ('%s/catalogs' % module.base_path, 'GET', ListCatalogs, {}),
            ('%s/catalogs/<oid>' % module.base_path, 'GET', GetCatalog, {}),
            # ('%s/catalog/<oid>/<zone>' % module.base_path, 'GET', FilterCatalog, {}),
            ('%s/catalogs/<oid>/perms' % module.base_path, 'GET', GetCatalogPerms, {}),
            ('%s/catalogs' % module.base_path, 'POST', CreateCatalog, {}),
            ('%s/catalogs/<oid>' % module.base_path, 'PUT', UpdateCatalog, {}),
            ('%s/catalogs/<oid>' % module.base_path, 'DELETE', DeleteCatalog, {}),
            # ('%s/catalogs/<oid>/services' % module.base_path, 'GET', GetCatalogServices, {}),

            ('%s/endpoints' % module.base_path, 'GET', ListEndpoints, {}),
            ('%s/endpoints/<oid>' % module.base_path, 'GET', GetEndpoint, {}),
            ('%s/endpoints/<oid>/perms' % module.base_path, 'GET', GetEndpointPerms, {}),
            ('%s/endpoints' % module.base_path, 'POST', CreateEndpoint, {}),
            ('%s/endpoints/<oid>' % module.base_path, 'PUT', UpdateEndpoint, {}),
            ('%s/endpoints/<oid>' % module.base_path, 'DELETE', DeleteEndpoint, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)