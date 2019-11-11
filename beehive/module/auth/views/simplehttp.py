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


class SimpleHttpLoginRequestSchema(Schema):
    user = fields.String(required=True, error_messages={'required': 'user is required.'})
    password = fields.String(required=True, error_messages={'required': 'password is required.'})
    login_ip = fields.String(load_from='login-ip', missing=get_ip)

    @validates('user')
    def validate_user(self, value):
        try:
            value.index('@')
        except ValueError:
            raise ValidationError('User syntax must be <user>@<domain>')


class SimpleHttpLoginResponseSchema(Schema):
    uid = fields.String(required=True, example='')
    type = fields.String(example='simplehttp')
    timestamp = fields.DateTime(required=True, example='')
    user = fields.Dict(required=True, example={})


class SimpleHttpLogin(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'SimpleHttpLoginRequestSchema': SimpleHttpLoginRequestSchema,
        'SimpleHttpLoginResponseSchema': SimpleHttpLoginResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(SimpleHttpLoginRequestSchema)
    parameters_schema = SimpleHttpLoginRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': SimpleHttpLoginResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        """
        Login user with simple http authentication
        Login user with simple http authentication
        """
        user = get_value(data, 'user', None, exception=True)
        password = get_value(data, 'password', None, exception=True)
        login_ip = get_value(data, 'login-ip', None, exception=True)
        
        try:
            name_domain = user.split('@')
            name = name_domain[0]
            try:
                domain = name_domain[1]
            except:
                domain = 'local'
        except:
            ApiManagerError('User must be <user>@<domain>')

        innerperms = [
            (1, 1, 'auth', 'objects', 'ObjectContainer', '*', 1, '*'),
            (1, 1, 'auth', 'role', 'RoleContainer', '*', 1, '*'),
            (1, 1, 'auth', 'user', 'UserContainer', '*', 1, '*')]
        operation.perms = innerperms     
        resp = controller.simple_http_login(name, domain, password, login_ip)    
        return resp


class SimpleHttpAuthApi(ApiView):
    """Simple http authentication API
    """
    @staticmethod
    def register_api(module):
        # base = 'simplehttp'
        rules = [
            # ('%s/login/domains' % base, 'GET', ListDomains, {'secure': False}),
            # ('%s/login' % base, 'POST', Login, {'secure': False}),

            # new routes
            # ('%s/simplehttp/login/domains' % module.base_path, 'GET', ListDomains, {'secure': False}),
            ('%s/simplehttp/login' % module.base_path, 'POST', SimpleHttpLogin, {'secure': False})
        ]
        
        ApiView.register_api(module, rules)    
