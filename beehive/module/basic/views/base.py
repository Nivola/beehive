# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from beehive.common.apimanager import ApiView, SwaggerApiView
#from marshmallow import fields
#from marshmallow.schema import Schema
from flasgger import fields, Schema

class ServerPingBaseResponseSchema(Schema):
    name = fields.String(required=True,
                         metadata={"example": "beehive", "description": "server instance name"})
    id = fields.String(required=True,
                       metadata={"example": "auth", "description": "server instance id"})
    hostname = fields.String(required=True,
                             metadata={"example": "tst-beehive", "description": "server instance host name"})
    uri = fields.String(
        required=True,
        example="http://localhost:6060",
        description="server instance uri",
    )


class ServerBasePing(SwaggerApiView):
    summary = "Server ping api"
    description = "Server ping api"
    tags = ["base"]
    definitions = {
        "ServerPingBaseResponseSchema": ServerPingBaseResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ServerPingBaseResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        resp = controller.ping()
        return resp


class ServerInfoResponseSchema(Schema):
    name = fields.String(required=True,
                         metadata={"example": "beehive", "description": "server instance name"})
    id = fields.String(required=True,
                       metadata={"example": "auth", "description": "server instance id"})
    modules = fields.Dict(required=True, example={},
                          metadata={"description": "server modules"})


class ServerInfo(SwaggerApiView):
    summary = "Server info api"
    description = "Server info api"
    tags = ["base"]
    definitions = {
        "ServerInfoResponseSchema": ServerInfoResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ServerInfoResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        resp = controller.info()
        return resp


class BaseAPI(ApiView):
    """ """

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("server/ping", "GET", ServerBasePing, {"secure": False}),
            ("server", "GET", ServerInfo, {"secure": False}),
        ]

        ApiView.register_api(module, rules, **kwargs)
