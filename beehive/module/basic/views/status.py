# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiController, ApiManagerError, ApiView, SwaggerApiView
from marshmallow import fields
from marshmallow.schema import Schema


class ServerPingResponseSchema(Schema):
    name = fields.String(required=True, example="beehive", description="server instance name")
    id = fields.String(required=True, example="auth", description="server instance id")
    hostname = fields.String(required=True, example="tst-beehive", description="server instance host name")
    uri = fields.String(
        required=True,
        example="http://localhost:6060",
        description="server instance uri",
    )


class ServerPing(SwaggerApiView):
    summary = "Server ping api"
    description = "Server ping api"
    tags = ["base"]
    definitions = {
        "ServerPingResponseSchema": ServerPingResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ServerPingResponseSchema}})

    def get(self, controller, data, *args, **kwargs):
        resp = controller.ping()
        return resp


class ServerInfoResponseSchema(Schema):
    name = fields.String(required=True, example="beehive", description="server instance name")
    id = fields.String(required=True, example="auth", description="server instance id")
    modules = fields.Dict(required=True, example={}, description="server modules")


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


class ServerVersionResponseSchema(Schema):
    name = fields.String(required=True, example="beehive", description="package name")
    version = fields.String(required=True, example="auth", description="package version")


class ServerImageInfoResponseSchema(Schema):
    branch = fields.String(required=False, example="devel", description="branch")
    date_created = fields.String(required=False, description="date_created")


class ServerVersionsResponseSchema(Schema):
    packages = fields.Nested(ServerVersionResponseSchema, many=True, required=True, allow_none=True)
    image_info = fields.Nested(ServerImageInfoResponseSchema, required=True, allow_none=True)


class ServerVersion(SwaggerApiView):
    summary = "Server packages version"
    description = "Server packages version"
    tags = ["base"]
    definitions = {
        "ServerVersionResponseSchema": ServerVersionResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": ServerVersionResponseSchema}})

    def get(self, controller: ApiController, data, *args, **kwargs):
        resp_versions = controller.versions()
        resp_image_info = controller.image_info()

        return {
            "packages": resp_versions,
            "image_info": resp_image_info,
        }


class MaintenanceListMethodResponseSchema(Schema):
    method = fields.String(required=True, example="get", description="method name")
    enabled = fields.String(required=True, example="False", description="enabled True/False", allow_none=True)


class MaintenanceListResponseSchema(Schema):
    methods = fields.Nested(MaintenanceListMethodResponseSchema, many=True, required=True, allow_none=True)


class MaintenanceList(SwaggerApiView):
    summary = "Cmp get maintenance"
    description = "Cmp get maintenance"
    tags = ["base"]
    definitions = {
        "MaintenanceListResponseSchema": MaintenanceListResponseSchema,
    }
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": MaintenanceListResponseSchema}})
    response_schema = MaintenanceListResponseSchema

    def get(self, controller: ApiController, data, *args, **kwargs):
        resp = []
        methods = ["get", "post", "put", "delete"]
        for http_method in methods:
            key = "cmp.%s.%s" % (controller.module.name, http_method)
            enabled = controller.module.redis_manager.get(key)

            resp.append({"method": http_method, "enabled": enabled})

        return {"methods": resp}


class MaintenanceSetApiParamRequestSchema(Schema):
    method = fields.String(
        required=True,
        example="get",
        description="http method",
    )
    enabled = fields.String(required=True, example="False", description="enable True/False")


class MaintenanceSetApiRequestSchema(Schema):
    methods = fields.Nested(MaintenanceSetApiParamRequestSchema, context="body")


class MaintenanceSetApiBodyRequestSchema(Schema):
    body = fields.Nested(MaintenanceSetApiRequestSchema, context="body")


class MaintenanceSetApiResponse1Schema(Schema):
    xmlns = fields.String(required=False, data_key="__xmlns")
    ok = fields.Boolean(required=True, example="", allow_none=True)


class MaintenanceSetApiResponseSchema(Schema):
    MaintenanceSetResponse = fields.Nested(
        MaintenanceSetApiResponse1Schema, required=True, many=False, allow_none=False
    )


class MaintenanceSet(SwaggerApiView):
    summary = "Cmp set maintenance"
    description = "Cmp set maintenance"
    tags = ["base"]
    definitions = {
        "MaintenanceSetApiResponseSchema": MaintenanceSetApiResponseSchema,
        "MaintenanceSetApiRequestSchema": MaintenanceSetApiRequestSchema,
    }
    parameters = SwaggerHelper().get_parameters(MaintenanceSetApiBodyRequestSchema)
    parameters_schema = MaintenanceSetApiRequestSchema
    responses = SwaggerApiView.setResponses(
        {200: {"description": "success", "schema": MaintenanceSetApiResponseSchema}}
    )
    response_schema = MaintenanceSetApiResponseSchema

    def post(self, controller: ApiController, data: dict, *args, **kwargs):
        self.logger.debug("MaintenanceSet post - begin")

        if not controller.is_admin_service():
            raise ApiManagerError("You are not SuperAdmin")

        methods = data.get("methods")
        # print("+++++ methods: %s" % methods)
        http_method = methods.get("method")
        enabled = methods.get("enabled")

        key = "cmp.%s.%s" % (controller.module.name, http_method)
        controller.module.redis_manager.set(key, enabled)

        return {"MaintenanceSetResponse": {"__xmlns": self.xmlns, "ok": True}}


class StatusAPI(ApiView):
    """ """

    MAINTENANCE_URI = "/cmp_maintenance"

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            ("%s/ping" % module.base_path, "GET", ServerPing, {"secure": False}),
            (
                "%s/api/capabilities" % module.base_path,
                "GET",
                ServerInfo,
                {"secure": False},
            ),
            ("%s/versions" % module.base_path, "GET", ServerVersion, {"secure": False}),
            ("%s%s" % (module.base_path, StatusAPI.MAINTENANCE_URI), "GET", MaintenanceList, {"secure": False}),
            ("%s%s" % (module.base_path, StatusAPI.MAINTENANCE_URI), "POST", MaintenanceSet, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
