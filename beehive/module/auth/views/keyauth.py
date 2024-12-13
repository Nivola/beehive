# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from flask import request
from beecell.flask.api_util import get_remote_ip
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiView, SwaggerApiView
from beehive.common.data import operation
from marshmallow import fields, Schema, validates, ValidationError


def get_ip():
    return get_remote_ip(request)


class CreateTokenRequestSchema(Schema):
    user = fields.String(required=True, error_messages={"required": "user is required."})
    password = fields.String(required=True, error_messages={"required": "password is required."})
    login_ip = fields.String(data_key="login-ip", missing=get_ip)

    @validates("user")
    def validate_user(self, value):
        try:
            value.index("@")
        except ValueError:
            raise ValidationError("User syntax must be <user>@<domain>")


class CreateTokenBodyRequestSchema(Schema):
    body = fields.Nested(CreateTokenRequestSchema, context="body")


class CreateTokenResponseSchema(Schema):
    access_token = fields.String(required=True, example="39cdae88-74a7-466b-9817-ced52c90239c")
    expires_in = fields.Integer(example=3600)
    expires_at = fields.Integer(example=1502739783)
    token_type = fields.String(required=True, example="Bearer")
    seckey = fields.String(required=True, example="LS0tLS1CRUdJTiBSU0Eg........")
    pubkey = fields.String(required=True, example="LS0tLS1CRUdJTiBQVUJMSUMgS0VZL..........")
    user = fields.String(required=True, example="6d960236-d280-46d2-817d-f3ce8f0aeff7")


class CreateToken(SwaggerApiView):
    summary = "Create keyauth token"
    description = "Create keyauth token"
    tags = ["authorization"]
    definitions = {
        "CreateTokenRequestSchema": CreateTokenRequestSchema,
        "CreateTokenResponseSchema": CreateTokenResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(CreateTokenBodyRequestSchema)
    parameters_schema = CreateTokenRequestSchema
    responses = SwaggerApiView.setResponses({200: {"description": "success", "schema": CreateTokenResponseSchema}})
    from beehive.module.auth.controller import AuthController

    def post(self, controller: AuthController, data, *args, **kwargs):
        innerperms = [
            (1, 1, "auth", "objects", "ObjectContainer", "*", 1, "*"),
            (1, 1, "auth", "role", "RoleContainer", "*", 1, "*"),
            (1, 1, "auth", "user", "UserContainer", "*", 1, "*"),
        ]
        operation.perms = innerperms
        res = controller.create_keyauth_token(**data)
        resp = res
        return resp


class KeyAuthApi(ApiView):
    """Asymmetric key authentication API"""

    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            (
                "%s/keyauth/token" % module.base_path,
                "POST",
                CreateToken,
                {"secure": False},
            ),
        ]

        ApiView.register_api(module, rules, **kwargs)
