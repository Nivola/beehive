# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from flask import request
from beecell.simple import get_value, str2bool, get_remote_ip
from beecell.swagger import SwaggerHelper
from beehive.common.apimanager import ApiView, ApiManagerError, SwaggerApiView
from beehive.common.data import operation
from marshmallow import fields, Schema, validates, ValidationError


# class ListDomains(ApiView):
#     def dispatch(self, controller, data, *args, **kwargs):
#         auth_providers = controller.module.authentication_manager.auth_providers
#         res = []
#         for domain, auth_provider in auth_providers.iteritems():
#             res.append([domain, auth_provider.__class__.__name__])
#         resp = {u'domains':res,
#                 u'count':len(res)}
#         return resp


def get_ip():
    return get_remote_ip(request)


class SimpleHttpLoginRequestSchema(Schema):
    user = fields.String(required=True, error_messages={u'required': u'user is required.'})
    password = fields.String(required=True, error_messages={u'required': u'password is required.'})
    login_ip = fields.String(load_from=u'login-ip', missing=get_ip)

    @validates(u'user')
    def validate_user(self, value):
        try:
            value.index(u'@')
        except ValueError:
            raise ValidationError(u'User syntax must be <user>@<domain>')


class SimpleHttpLoginResponseSchema(Schema):
    uid = fields.String(required=True, example=u'')
    type = fields.String(example=u'simplehttp')
    timestamp = fields.DateTime(required=True, example=u'')
    user = fields.Dict(required=True, example={})


class SimpleHttpLogin(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'SimpleHttpLoginRequestSchema': SimpleHttpLoginRequestSchema,
        u'SimpleHttpLoginResponseSchema': SimpleHttpLoginResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(SimpleHttpLoginRequestSchema)
    parameters_schema = SimpleHttpLoginRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': SimpleHttpLoginResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        """
        Login user with simple http authentication
        Login user with simple http authentication
        """
        user = get_value(data, u'user', None, exception=True)
        password = get_value(data, u'password', None, exception=True)
        login_ip = get_value(data, u'login-ip', None, exception=True)
        
        try:
            name_domain = user.split(u'@')
            name = name_domain[0]
            try:
                domain = name_domain[1]
            except:
                domain = u'local'
        except:
            ApiManagerError(u'User must be <user>@<domain>')

        innerperms = [
            (1, 1, u'auth', u'objects', u'ObjectContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'role', u'RoleContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'user', u'UserContainer', u'*', 1, u'*')]
        operation.perms = innerperms     
        resp = controller.simple_http_login(name, domain, password, login_ip)    
        return resp


class SimpleHttpAuthApi(ApiView):
    """Simple http authentication API
    """
    @staticmethod
    def register_api(module):
        # base = u'simplehttp'
        rules = [
            # (u'%s/login/domains' % base, u'GET', ListDomains, {u'secure': False}),
            # (u'%s/login' % base, u'POST', Login, {u'secure': False}),

            # new routes
            # (u'%s/simplehttp/login/domains' % module.base_path, u'GET', ListDomains, {u'secure': False}),
            (u'%s/simplehttp/login' % module.base_path, u'POST', SimpleHttpLogin, {u'secure': False})
        ]
        
        ApiView.register_api(module, rules)    
