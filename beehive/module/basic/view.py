# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.apimanager import ApiView, SwaggerApiView
from ansible.modules.system import hostname
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


# class ServerProcessTree(ApiView):
#     def dispatch(self, controller, data, *args, **kwargs):
#         """
#         bla bla
#         ---
#         """
#         resp = controller.processes()
#         return resp
#
#
# class ServerWorkers(ApiView):
#     def get(self, controller, data, *args, **kwargs):
#         """
#
#         """
#         resp = controller.workers()
#         return resp
#
#
# class ServerConfigs(ApiView):
#     def dispatch(self, controller, data, *args, **kwargs):
#         """
#         bla bla
#         ---
#         """
#         resp = controller.get_configs()
#         return resp
#
#
# class ServerUwsgiConfigs(ApiView):
#     def dispatch(self, controller, data, *args, **kwargs):
#         """
#         bla bla
#         ---
#         """
#         resp = controller.get_uwsgi_configs()
#         return resp
#
#
# class ServerReload(ApiView):
#     def dispatch(self, controller, data, *args, **kwargs):
#         """
#         bla bla
#         ---
#         """
#         resp = controller.reload()
#         return resp


class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('server/ping', 'GET', ServerPing, {'secure': False}),
            ('server', 'GET', ServerInfo, {'secure': False}),
            # ('server/processes', 'GET', ServerProcessTree, {}),
            # ('server/workers', 'GET', ServerWorkers, {'secure':False}),
            # ('server/configs', 'GET', ServerConfigs, {}),
            # ('server/uwsgi/configs', 'GET', ServerUwsgiConfigs, {}),
            # ('server/reload', 'PUT', ServerReload, {}),
        ]

        ApiView.register_api(module, rules)