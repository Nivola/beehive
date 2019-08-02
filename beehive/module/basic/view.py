# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.apimanager import ApiView, SwaggerApiView
from ansible.modules.system import hostname
from marshmallow import fields
from marshmallow.schema import Schema


class ServerPingResponseSchema(Schema):
    name = fields.String(required=True, example=u'beehive', description=u'server instance name')
    id = fields.String(required=True, example=u'auth', description=u'server instance id')
    hostname = fields.String(required=True, example=u'tst-beehive', description=u'server instance host name')
    uri = fields.String(required=True, example=u'http://localhost:6060', description=u'server instance uri')


class ServerPing(SwaggerApiView):
    tags = [u'base']
    definitions = {
        u'ServerPingResponseSchema': ServerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ServerPingResponseSchema
        }
    })    
    
    def get(self, controller, data, *args, **kwargs):
        """
        Server ping api
        Call this api to ping server
        """
        resp = controller.ping()
        return resp


class ServerInfo(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """

        """  
        resp = controller.info()
        return resp


class ServerProcessTree(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.processes()
        return resp


class ServerWorkers(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """

        """        
        resp = controller.workers()
        return resp


class ServerConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.get_configs()
        return resp


class ServerUwsgiConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.get_uwsgi_configs()
        return resp


class ServerReload(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.reload()
        return resp


class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'server/ping', u'GET', ServerPing, {u'secure': False}),
            (u'server', u'GET', ServerInfo, {u'secure': False}),
            # (u'server/processes', u'GET', ServerProcessTree, {}),
            # (u'server/workers', u'GET', ServerWorkers, {u'secure':False}),
            # (u'server/configs', u'GET', ServerConfigs, {}),
            # (u'server/uwsgi/configs', u'GET', ServerUwsgiConfigs, {}),
            # (u'server/reload', u'PUT', ServerReload, {}),
        ]

        ApiView.register_api(module, rules)