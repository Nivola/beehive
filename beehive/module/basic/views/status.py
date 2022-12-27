# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiView, SwaggerApiView
from marshmallow import fields
from marshmallow.schema import Schema


class ServerPingResponseSchema(Schema):
    name = fields.String(required=True, example='beehive', description='server instance name')
    id = fields.String(required=True, example='auth', description='server instance id')
    hostname = fields.String(required=True, example='tst-beehive', description='server instance host name')
    uri = fields.String(required=True, example='http://localhost:6060', description='server instance uri')


class ServerPing(SwaggerApiView):
    summary = 'Server ping api'
    description = 'Server ping api'
    tags = ['base']
    definitions = {
        'ServerPingResponseSchema': ServerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ServerPingResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        resp = controller.ping()
        return resp


class ServerInfoResponseSchema(Schema):
    name = fields.String(required=True, example='beehive', description='server instance name')
    id = fields.String(required=True, example='auth', description='server instance id')
    modules = fields.Dict(required=True, example={}, description='server modules')


class ServerInfo(SwaggerApiView):
    summary = 'Server info api'
    description = 'Server info api'
    tags = ['base']
    definitions = {
        'ServerInfoResponseSchema': ServerInfoResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ServerInfoResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        resp = controller.info()
        return resp


class ServerVersionResponseSchema(Schema):
    name = fields.String(required=True, example='beehive', description='package name')
    version = fields.String(required=True, example='auth', description='package version')


class ServerVersionsResponseSchema(Schema):
    packages = fields.Nested(ServerVersionResponseSchema, many=True, required=True, allow_none=True)


class ServerVersion(SwaggerApiView):
    summary = 'Server packages version'
    description = 'Server packages version'
    tags = ['base']
    definitions = {
        'ServerVersionResponseSchema': ServerVersionResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ServerVersionResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        resp = controller.versions()
        return {'packages': resp}


class StatusAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ('%s/ping' % module.base_path, 'GET', ServerPing, {'secure': False}),
            ('%s/api/capabilities' % module.base_path, 'GET', ServerInfo, {'secure': False}),
            ('%s/versions' % module.base_path, 'GET', ServerVersion, {'secure': False}),
        ]

        ApiView.register_api(module, rules, **kwargs)
