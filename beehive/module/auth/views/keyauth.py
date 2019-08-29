# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from flask import request
from beecell.simple import get_value, str2bool, get_remote_ip
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiView, ApiManagerError, SwaggerApiView
from beehive.common.data import operation
from marshmallow import fields, Schema, validates, ValidationError


def get_ip():
    return get_remote_ip(request)


class CreateTokenRequestSchema(Schema):
    user = fields.String(required=True, error_messages={u'required': u'user is required.'})
    password = fields.String(required=True, error_messages={u'required': u'password is required.'})
    login_ip = fields.String(load_from=u'login-ip', missing=get_ip)
    
    @validates(u'user')
    def validate_user(self, value):
        try:
            value.index(u'@')
        except ValueError:
            raise ValidationError(u'User syntax must be <user>@<domain>')


class CreateTokenResponseSchema(Schema):
    access_token = fields.String(required=True, example=u'39cdae88-74a7-466b-9817-ced52c90239c')
    expires_in = fields.Integer(example=3600)
    expires_at = fields.Integer(example=1502739783)
    token_type = fields.String(required=True, example=u'Bearer')
    seckey = fields.String(required=True, example=u'LS0tLS1CRUdJTiBSU0Eg........')
    pubkey = fields.String(required=True, example=u'LS0tLS1CRUdJTiBQVUJMSUMgS0VZL..........')
    user = fields.String(required=True, example=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')


class CreateToken(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateTokenRequestSchema': CreateTokenRequestSchema,
        u'CreateTokenResponseSchema': CreateTokenResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateTokenRequestSchema)
    parameters_schema = CreateTokenRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': CreateTokenResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        """
        Create keyauth token
        Call this api to create keyauth token
        """
        innerperms = [
            (1, 1, u'auth', u'objects', u'ObjectContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'role', u'RoleContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'user', u'UserContainer', u'*', 1, u'*')]
        operation.perms = innerperms     
        res = controller.create_keyauth_token(**data)
        resp = res       
        return resp


class KeyAuthApi(ApiView):
    """Asymmetric key authentication API
    """
    @staticmethod
    def register_api(module):
        # base = u'keyauth'
        rules = [
            # (u'%s/token' % base, u'POST', CreateToken, {u'secure': False}),

            # new routes
            (u'%s/keyauth/token' % module.base_path, u'POST', CreateToken, {u'secure': False}),
        ]
        
        ApiView.register_api(module, rules)