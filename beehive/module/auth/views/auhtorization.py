# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from re import match
from datetime import datetime
from beecell.simple import get_value, str2bool, AttribException, format_date
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectResponseDateSchema
from beecell.swagger import SwaggerHelper
from marshmallow import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from typing import TYPE_CHECKING
from beehive.module.auth.controller import AuthController

class BaseCreateRequestSchema(Schema):
    name = fields.String(required=True, error_messages={'required': 'name is required.'})
    desc = fields.String(required=True, error_messages={'required': 'desc is required.'})


class BaseUpdateRequestSchema(Schema):
    name = fields.String(allow_none=True)
    desc = fields.String(allow_none=True)
    active = fields.Boolean(context='query', allow_none=True)
    expiry_date = fields.String(default='2099-12-31', allow_none=True)


class BaseCreateExtendedParamRequestSchema(Schema):
    active = fields.Boolean(missing=True, allow_none=True)
    expiry_date = fields.String(data_key='expirydate', missing=None,
                                allow_none=True, example='',
                                description='expiration date. [default=365days]')

    @post_load
    def make_expiry_date(self, data, *args, **kvargs):
        expiry_date = data.get('expiry_date', None)
        if expiry_date is not None:
            y, m, d = expiry_date.split('-')
            expiry_date = datetime(int(y), int(m), int(d))
            data['expiry_date'] = expiry_date
        return data


class BaseUpdateMultiRequestSchema(Schema):
    append = fields.List(fields.String())
    remove = fields.List(fields.String())


class ListProviderResponseSchema(Schema):
    name = fields.String(required=True, example='local', description='login provider name')
    type = fields.String(required=True, example='DatabaseAuth', description='login provider description')


class ListProvidersResponseSchema(Schema):
    providers = fields.Nested(ListProviderResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, example=1, description='Providers count')


class ListProviders(SwaggerApiView):
    summary = 'List authentication providers'
    description = 'List authentication providers'
    tags = ['authorization']
    definitions = {
        'ListProvidersResponseSchema': ListProvidersResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListProvidersResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        auth_providers = controller.module.authentication_manager.auth_providers
        res = []
        for provider, auth_provider in auth_providers.items():
            res.append({'name': provider, 'type': auth_provider.__class__.__name__})
        resp = {'providers': res, 'count': len(res)}
        return resp


#
# identity
#
class ListTokensRequestSchema(Schema):
    pass


class ListTokenResponseSchema(Schema):
    ip = fields.String(required=True, example='pc160234.csi.it', description='client login ip address')
    ttl = fields.Integer(required=True, example=3600, description='token ttl')
    token = fields.String(required=True, example='28ff1dd5-5520-42f3-a361-c58f19d20b7c', description='token')
    user = fields.String(required=True, example='admin@local', description='client login user')
    provider = fields.String(required=True, example='local', description='authentication provider')
    timestamp = fields.String(required=True, example='internal', description='token timestamp')
    type = fields.String(required=True, example='internal', description='token type')


class ListTokensResponseSchema(Schema):
    tokens = fields.Nested(ListTokenResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, example=1, description='Token count')


class ListTokens(SwaggerApiView):
    summary = 'List authentication tokens'
    description = 'List authentication tokens'
    tags = ['authorization']
    definitions = {
        'ListTokensResponseSchema': ListTokensResponseSchema
    }
    # parameters = SwaggerHelper().get_parameters(ListTokensRequestSchema)
    # parameters_schema = ListTokensRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListTokensResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        identities = controller.get_identities()
        res = []
        for i in identities:
            user = i.get('user')
            user_name = None
            user_domain = None
            if user is not None:
                user_name = user.get('id', None)
                user_email = user.get('name', None)
                user_domain = user.get('domain', None)
            res.append({
                'token': i['uid'],
                'type': i['type'],
                'user': user_name,
                'email': user_email,
                'provider': user_domain,
                'timestamp': format_date(i['timestamp']),
                'ttl': i['ttl'],
                'ip': i['ip']
            })
        resp = {'tokens': res,
                'count': len(res)}
        return resp


class GetTokenUserResponseSchema(Schema):
    name = fields.String(required=True, example='admin@local', description='client login user')
    roles = fields.List(fields.String(example='admin@local'), required=True, description='client login user')
    perms = fields.String(required=True, example='admin@local', description='client login perms')
    active = fields.Boolean(required=True, example=True, description='client login active')
    id = fields.UUID(required=True, description='client login uuid', example='6d960236-d280-46d2-817d-f3ce8f0aeff7')


class GetTokenParamsResponseSchema(Schema):
    ip = fields.String(required=True, example='pc160234.csi.it', description='client login ip address')
    ttl = fields.Integer(required=True, example=3600, description='token ttl')
    token = fields.String(required=True, example='28ff1dd5-5520-42f3-a361-c58f19d20b7c', description='token')
    user = fields.Nested(GetTokenUserResponseSchema, required=True, description='client login user', allow_none=True)
    timestamp = fields.String(required=True, example='internal', description='token timestamp')
    type = fields.String(required=True, example='internal', description='token type')


class GetTokenResponseSchema(Schema):
    token = fields.Nested(ListTokenResponseSchema, required=True, allow_none=True)


class GetToken(SwaggerApiView):
    summary = 'Get authentication tokens'
    description = 'Get authentication tokens'
    tags = ['authorization']
    definitions = {
        'GetTokenResponseSchema': GetTokenResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetTokenResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        data = controller.get_identity(oid)
        res = {
            'token': data['uid'],
            'type': data['type'],
            'user': data['user'],
            'timestamp': format_date(data['timestamp']),
            'ttl': data['ttl'],
            'ip': data['ip']}
        resp = {'token': res}
        return resp


class DeleteToken(SwaggerApiView):
    summary = 'Delete authentication tokens'
    description = 'Delete authentication tokens'
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        resp = controller.remove_identity(oid)
        return resp, 204


class ListUsersRequestSchema(PaginatedRequestQuerySchema):
    group = fields.String(context='query')
    role = fields.String(context='query')
    active = fields.Boolean(context='query')
    expiry_date = fields.String(data_key='expirydate', default='2099-12-31', context='query')
    name = fields.String(context='query')
    names = fields.String(context='query')
    desc = fields.String(context='query')
    email = fields.String(context='query')
    perms_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                          collection_format='multi', data_key='perms.N', description='permissions list')


class ListUserResponseSchema(ApiObjectResponseSchema):
    email = fields.String(required=True, example='test@local')


class ListUsersResponseSchema(PaginatedResponseSchema):
    users = fields.Nested(ListUserResponseSchema, many=True, required=True, allow_none=True)


class ListUsers(SwaggerApiView):
    summary = 'List users'
    description = 'List users'
    tags = ['authorization']
    definitions = {
        'ListUsersResponseSchema': ListUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListUsersRequestSchema)
    parameters_schema = ListUsersRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListUsersResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        objs, total = controller.get_users(**data)
        res = [r.info() for r in objs]

        return self.format_paginated_response(res, 'users', total, **data)


class GetUserParamsResponseSchema(ApiObjectResponseSchema):
    # secret = fields.String(required=True, example='test')
    pass


class GetUserResponseSchema(Schema):
    user = fields.Nested(GetUserParamsResponseSchema, required=True, allow_none=True)


class GetUser(SwaggerApiView):
    summary = 'Get user'
    description = 'Get user'
    tags = ['authorization']
    definitions = {
        'GetUserResponseSchema': GetUserResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetUserResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        obj = controller.get_user(oid)
        res = obj.detail()
        resp = {'user': res}
        return resp


class UserSecretParamsResponseSchema(Schema):
    secret = fields.String(required=True, example='test')


class UserSecretResponseSchema(Schema):
    user = fields.Nested(UserSecretParamsResponseSchema, required=True, allow_none=True)


class GetUserSecret(SwaggerApiView):
    summary = 'Get user secret'
    description = 'Get user secret'
    tags = ['authorization']
    definitions = {
        'UserSecretResponseSchema': UserSecretResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UserSecretResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        secret = controller.get_user_secret(oid)
        resp = {'user': {'secret': secret}}
        return resp


class UserSecretParamsRequestSchema(Schema):
    old_secret = fields.String(required=False, example='test', description='user secret key to reset to',
                               context='query')


class UserSecretRequestSchema (Schema):
    user = fields.Nested(UserSecretParamsRequestSchema, required=True, allow_none=True)


class ResetUserSecretBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UserSecretRequestSchema, context='body')


class ResetUserSecret(SwaggerApiView):
    summary = 'Reset user secret'
    description = 'Reset user secret'
    tags = ['authorization']
    definitions = {
        'UserSecretRequestSchema': UserSecretRequestSchema,
        'UserSecretResponseSchema': UserSecretResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ResetUserSecretBodyRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UserSecretResponseSchema
        }
    })

    def put(self, controller:AuthController, data, oid, *args, **kwargs):
        old_secret = data.get('user', {}).get('old_secret', None)
        secret = controller.reset_user_secret(oid, old_secret=old_secret)
        resp = {'user': {'secret': secret}}
        return resp


class GetUserAtributesParamResponseSchema(Schema):
    name = fields.String(required=True, default='test')
    value = fields.String(required=True, default='test')
    desc = fields.String(required=True, default='test')


class GetUserAtributesResponseSchema(Schema):
    count = fields.Integer(required=True, defaut=0)
    user_attributes = fields.Nested(GetUserAtributesParamResponseSchema, many=True, required=True, allow_none=True)


class GetUserAtributes(SwaggerApiView):
    summary = 'Get user attributes'
    description = 'Get user attributes'
    tags = ['authorization']
    definitions = {
        'GetUserAtributesResponseSchema': GetUserAtributesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetUserAtributesResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        user = controller.get_user(oid)
        res = user.get_attribs()
        resp = {'user_attributes': res, 'count': len(res)}
        return resp


class CreateUserParamRequestSchema(BaseCreateRequestSchema, BaseCreateExtendedParamRequestSchema):
    password = fields.String(validate=Length(min=8, max=20), error='Password must be at least 8 characters')
    email = fields.String(error='email address', missing=None)
    storetype = fields.String(validate=OneOf(['DBUSER', 'LDAPUSER'], error='Field can be DBUSER, LDAPUSER'),
                              missing='DBUSER')
    base = fields.Boolean(missing=False)
    system = fields.Boolean(missing=False)

    @validates('name')
    def validate_user(self, value):
        if not match(r'[\w\W]+@[\w\W]+', value):
            raise ValidationError('User name syntax must be <name>@<domain>')


class CreateUserRequestSchema(Schema):
    user = fields.Nested(CreateUserParamRequestSchema)


class CreateUserBodyRequestSchema(Schema):
    body = fields.Nested(CreateUserRequestSchema, context='body')


class CreateUser(SwaggerApiView):
    summary = 'Create a user'
    description = 'Create a user'
    tags = ['authorization']
    definitions = {
        'CreateUserRequestSchema': CreateUserRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateUserBodyRequestSchema)
    parameters_schema = CreateUserRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller:AuthController, data, *args, **kwargs):
        resp = controller.add_user(**data.get('user'))
        return {'uuid': resp}, 201


class UpdateUserParamPermRequestSchema(Schema):
    type = fields.String()
    subsystem = fields.String()
    objid = fields.String()
    action = fields.String()
    id = fields.Integer()


class UpdateUserParamPermsRequestSchema(Schema):
    append = fields.Nested(UpdateUserParamPermRequestSchema, many=True, allow_none=True)
    remove = fields.Nested(UpdateUserParamPermRequestSchema, many=True, allow_none=True)


class UpdateUserParamRoleRequestSchema(Schema):
    append = fields.List(fields.List(fields.String()))
    remove = fields.List(fields.String())


class UpdateUserParamRequestSchema(BaseUpdateRequestSchema):
    perms = fields.Nested(UpdateUserParamPermsRequestSchema, allow_none=True)
    roles = fields.Nested(UpdateUserParamRoleRequestSchema, allow_none=True)
    password = fields.String(validate=Length(min=8, max=20), allow_none=True,
                             error='Password must be at least 8 characters')


class UpdateUserRequestSchema(Schema):
    user = fields.Nested(UpdateUserParamRequestSchema)


class UpdateUserBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateUserRequestSchema, context='body')


class UpdateUserResponseSchema(Schema):
    update = fields.String(default='6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    role_append = fields.List(fields.String, dump_to='role_append', required=True)
    role_remove = fields.List(fields.String, dump_to='role_remove', required=True)
    perm_append = fields.List(fields.String, dump_to='perm_append', required=True)
    perm_remove = fields.List(fields.String, dump_to='perm_remove', required=True)


class UpdateUser(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'UpdateUserRequestSchema': UpdateUserRequestSchema,
        'UpdateUserResponseSchema': UpdateUserResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateUserBodyRequestSchema)
    parameters_schema = UpdateUserRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UpdateUserResponseSchema
        }
    })

    def put(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Update user
        Call this api to update a user
        """
        data = data.get('user')
        role = data.pop('roles', None)
        role_perm = data.pop('perms', None)
        user = controller.get_user(oid)

        resp = {'update': None, 'role_append': [], 'role_remove': [], 'perm_append': [], 'perm_remove': []}

        # append, remove role
        if role is not None:
            # append role
            if 'append' in role:
                for role, expiry in role.get('append'):
                    res = user.append_role(role, expiry_date=expiry)
                    resp['role_append'].append(res)

            # remove role
            if 'remove' in role:
                for role in role.get('remove'):
                    res = user.remove_role(role)
                    resp['role_remove'].append(res)

        # append, remove perms
        if role_perm is not None:
            # append role
            if 'append' in role_perm:
                perms = []
                for perm in role_perm.get('append'):
                    perms.append(perm)
                res = user.append_permissions(perms)
                resp['perm_append'] = res

            # remove role
            if 'remove' in role_perm:
                perms = []
                for perm in role_perm.get('remove'):
                    perms.append(perm)
                res = user.remove_permissions(perms)
                resp['perm_remove'] = res

        # update user
        res = user.update(**data)
        resp['update'] = res
        return resp


class UserAttribSchemaCreateParam(Schema):
    name = fields.String(required=True)
    new_name = fields.String()
    value = fields.String(required=True)
    desc = fields.String(required=True)


class CreateUserAttributeRequestSchema(Schema):
    user_attribute = fields.Nested(UserAttribSchemaCreateParam, data_key='user_attribute')


class CreateUserAttributeBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CreateUserAttributeRequestSchema, context='body')


class CreateUserAttributeResponseSchema(Schema):
    name = fields.String(required=True, default='test')
    value = fields.String(required=True, default='test')
    desc = fields.String(required=True, default='test')


class CreateUserAttribute(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'CreateUserAttributeRequestSchema': CreateUserAttributeRequestSchema,
        'CreateUserAttributeResponseSchema': CreateUserAttributeResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateUserAttributeBodyRequestSchema)
    parameters_schema = CreateUserAttributeRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CreateUserAttributeResponseSchema
        }
    })

    def post(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user
        """
        user = controller.get_user(oid)
        attr = user.set_attribute(**data.get('user_attribute'))
        resp = {'name':attr.name, 'value':attr.value, 'desc':attr.desc}
        return (resp, 201)

## delete attributes
class DeleteUserAttributeRequestSchema(GetApiObjectRequestSchema):
    aid = fields.String(required=True, description='attribute name',
                        context='path')

class DeleteUserAttribute(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(DeleteUserAttributeRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, aid, *args, **kwargs):
        """
        Delete user attribute
        Call this api to delete a user attribute
        """
        user = controller.get_user(oid)
        resp = user.remove_attribute(aid)
        return resp, 204


class DeleteUser(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user
        """
        user = controller.get_user(oid)
        resp = user.delete()
        return resp, 204


#
# role
#
class ListRolesRequestSchema(PaginatedRequestQuerySchema):
    user = fields.String(context='query')
    group = fields.String(context='query')
#     groups_N = fields.List(fields.String(example='1'), required=False, allow_none=True, context='query',
#                           collection_format='multi', data_key='groups.N', description='groups id list')
    names = fields.String(context='query')
    alias = fields.String(context='query')
    perms_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                          collection_format='multi', data_key='perms.N', description='permissions list')


class ListRoleResponseSchema(ApiObjectResponseSchema):
    alias = fields.String(required=True, default='test', example='test')


class ListRolesResponseSchema(PaginatedResponseSchema):
    roles = fields.Nested(ListRoleResponseSchema, many=True, required=True, allow_none=True)


class ListRoles(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'ListRolesResponseSchema': ListRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListRolesRequestSchema)
    parameters_schema = ListRolesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListRolesResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        """
        List roles
        Call this api to list roles
        """
        objs, total = controller.get_roles(**data)

        res = [r.info() for r in objs]
        return self.format_paginated_response(res, 'roles', total, **data)


class GetRoleItemResponseSchema(ApiObjectResponseSchema):
    alias = fields.String(required=True, default='test', example='test')


class GetRoleResponseSchema(Schema):
    role = fields.Nested(GetRoleItemResponseSchema, required=True, allow_none=True)


class GetRole(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'GetRoleResponseSchema': GetRoleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetRoleResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Get role
        Call this api to get a role
        """
        obj = controller.get_role(oid)
        res = obj.info()
        resp = {'role': res}
        return resp


class CreateRoleItemRequestSchema(BaseCreateRequestSchema):
    alias = fields.String(required=False, description='Role alias')


class CreateRoleRequestSchema(Schema):
    role = fields.Nested(CreateRoleItemRequestSchema)


class CreateRoleBodyRequestSchema(Schema):
    body = fields.Nested(CreateRoleRequestSchema, context='body')


class CreateRole(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'CreateRoleRequestSchema': CreateRoleRequestSchema,
        'CrudApiObjectResponseSchema': CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateRoleBodyRequestSchema)
    parameters_schema = CreateRoleRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller:AuthController, data, *args, **kwargs):
        """
        Create role
        Call this api to create a role
        """
        resp = controller.add_role(**data.get('role'))
        return {'uuid': resp}, 201


class UpdateRoleParamPermDescRequestSchema(Schema):
    type = fields.String()
    subsystem = fields.String()
    objid = fields.String()
    action = fields.String()
    id = fields.Integer()
    alias = fields.String()


class UpdateRoleParamPermRequestSchema(Schema):
    append = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True, allow_none=True)
    remove = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True, allow_none=True)


class UpdateRoleParamRequestSchema(BaseUpdateRequestSchema, BaseCreateExtendedParamRequestSchema):
    perms = fields.Nested(UpdateRoleParamPermRequestSchema, allow_none=True)


class UpdateRoleRequestSchema(Schema):
    role = fields.Nested(UpdateRoleParamRequestSchema)


class UpdateRoleBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateRoleRequestSchema, context='body')


class UpdateRoleResponseSchema(Schema):
    update = fields.String(default='6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    perm_append = fields.List(fields.String, dump_to='perm_append', required=True)
    perm_remove = fields.List(fields.String, dump_to='perm_remove', required=True)


class UpdateRole(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'UpdateRoleRequestSchema': UpdateRoleRequestSchema,
        'UpdateRoleResponseSchema': UpdateRoleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateRoleBodyRequestSchema)
    parameters_schema = UpdateRoleRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UpdateRoleResponseSchema
        }
    })

    def put(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Update role
        Call this api to update a role
        """
        data = data.get('role')
        role_perm = data.pop('perms', None)
        role = controller.get_role(oid)

        resp = {'update': None, 'perm_append': [], 'perm_remove': []}

        # append, remove role
        if role_perm is not None:
            # append role
            if 'append' in role_perm:
                perms = []
                for perm in role_perm.get('append'):
                    perms.append(perm)
                if len(perms) > 0:
                    res = role.append_permissions(perms)
                    resp['perm_append'] = res
                else:
                    resp['perm_append'] = []

            # remove role
            if 'remove' in role_perm:
                perms = []
                for perm in role_perm.get('remove'):
                    perms.append(perm)
                if len(perms) > 0:
                    res = role.remove_permissions(perms)
                    resp['perm_remove'] = res
                else:
                    resp['perm_remove'] = []

        # update role
        res = role.update(**data)
        resp['update'] = res
        return resp


class DeleteRole(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete role
        Call this api to delete a role
        """
        role = controller.get_role(oid)
        resp = role.delete()
        return resp, 204


#
# group
#
class ListGroupsRequestSchema(PaginatedRequestQuerySchema):
    user = fields.String(context='query')
    role = fields.String(context='query')
    active = fields.Boolean(context='query')
    expiry_date = fields.String(data_key='expirydate', default='2099-12-31', context='query')
    perms_N = fields.List(fields.String(example=''), required=False, allow_none=True, context='query',
                          collection_format='multi', data_key='perms.N', description='permissions list')


class ListGroupsResponseSchema(PaginatedResponseSchema):
    groups = fields.Nested(ApiObjectResponseSchema, many=True, required=True, allow_none=True)


class ListGroups(SwaggerApiView):
    summary = 'List groups'
    description = 'List authorization groups'
    tags = ['authorization']
    definitions = {
        'ListGroupsResponseSchema': ListGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListGroupsRequestSchema)
    parameters_schema = ListGroupsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListGroupsResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        objs, total = controller.get_groups(**data)

        res = [r.info() for r in objs]
        return self.format_paginated_response(res, 'groups', total, **data)


## get
class GetGroupResponseSchema(Schema):
    group = fields.Nested(ApiObjectResponseSchema, required=True, allow_none=True)


class GetGroup(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'GetGroupResponseSchema': GetGroupResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetGroupResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Get group
        Call this api to get a group
        """
        obj = controller.get_group(oid)
        res = obj.info()
        resp = {'group':res}
        return resp


## create
class CreateGroupParamRequestSchema(BaseCreateRequestSchema, BaseCreateExtendedParamRequestSchema):
    pass


class CreateGroupRequestSchema(Schema):
    group = fields.Nested(CreateGroupParamRequestSchema)


class CreateGroupBodyRequestSchema(Schema):
    body = fields.Nested(CreateGroupRequestSchema, context='body')


class CreateGroup(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'CreateGroupRequestSchema': CreateGroupRequestSchema,
        'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateGroupBodyRequestSchema)
    parameters_schema = CreateGroupRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller:AuthController, data, *args, **kwargs):
        """
        Create group
        Call this api to create a group
        """
        resp = controller.add_group(**data.get('group'))
        return {'uuid':resp}, 201


class UpdateGroupParamRoleRequestSchema(Schema):
    append = fields.List(fields.List(fields.String()))
    remove = fields.List(fields.String())


class UpdateGroupParamUserRequestSchema(Schema):
    append = fields.List(fields.String())
    remove = fields.List(fields.String())


class UpdateGroupParamPermRequestSchema(Schema):
    type = fields.String()
    subsystem = fields.String()
    objid = fields.String()
    action = fields.String()
    id = fields.Integer()


class UpdateGroupParamPermsRequestSchema(Schema):
    append = fields.Nested(UpdateGroupParamPermRequestSchema, many=True, allow_none=True)
    remove = fields.Nested(UpdateGroupParamPermRequestSchema, many=True, allow_none=True)


class UpdateGroupParamRequestSchema(BaseUpdateRequestSchema, BaseCreateExtendedParamRequestSchema):
    roles = fields.Nested(UpdateGroupParamRoleRequestSchema, allow_none=True)
    users = fields.Nested(UpdateGroupParamUserRequestSchema, allow_none=True)
    perms = fields.Nested(UpdateGroupParamPermsRequestSchema, allow_none=True)


class UpdateGroupRequestSchema(Schema):
    group = fields.Nested(UpdateGroupParamRequestSchema)


class UpdateGroupBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateGroupRequestSchema, context='body')


class UpdateGroupResponseSchema(Schema):
    update = fields.String(default='6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    role_append = fields.List(fields.String, dump_to='role_append', required=True)
    role_remove = fields.List(fields.String, dump_to='role_remove', required=True)
    user_append = fields.List(fields.String, dump_to='user_append', required=True)
    user_remove = fields.List(fields.String, dump_to='user_remove', required=True)
    perm_append = fields.List(fields.String, dump_to='perm_append', required=True)
    perm_remove = fields.List(fields.String, dump_to='perm_remove', required=True)


class UpdateGroup(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'UpdateGroupRequestSchema':UpdateGroupRequestSchema,
        'UpdateGroupResponseSchema':UpdateGroupResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateGroupBodyRequestSchema)
    parameters_schema = UpdateGroupRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': UpdateGroupResponseSchema
        }
    })

    def put(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Update group
        Call this api to update a group
        """
        data = data.get('group')
        group_role = data.pop('roles', None)
        group_user = data.pop('users', None)
        role_perm = data.pop('perms', None)

        group = controller.get_group(oid)

        resp = {'update': None,
                'role_append': [], 'role_remove': [],
                'user_append': [], 'user_remove': [],
                'perm_append': [], 'perm_remove': []}

        # append, remove role
        if group_role is not None:
            # append role
            if 'append' in group_role:
                for role, expiry in group_role.get('append'):
                    res = group.append_role(role, expiry_date=expiry)
                    resp['role_append'].append(res)

            # remove role
            if 'remove' in group_role:
                for role in group_role.get('remove'):
                    res = group.remove_role(role)
                    resp['role_remove'].append(res)

        # append, remove perms
        if role_perm is not None:
            # append role
            if 'append' in role_perm:
                perms = []
                for perm in role_perm.get('append'):
                    perms.append(perm)
                res = group.append_permissions(perms)
                resp['perm_append'] = res

            # remove role
            if 'remove' in role_perm:
                perms = []
                for perm in role_perm.get('remove'):
                    perms.append(perm)
                res = group.remove_permissions(perms)
                resp['perm_remove'] = res

        # append, remove user
        if group_user is not None:
            # append user
            if 'append' in group_user:
                for user in group_user.get('append'):
                    res = group.append_user(user)
                    resp['user_append'].append(res)

            # remove user
            if 'remove' in group_user:
                for user in group_user.get('remove'):
                    res = group.remove_user(user)
                    resp['user_remove'].append(res)

        # update group
        res = group.update(**data)
        resp['update'] = res
        return resp


class PatchGroup(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def patch(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete group
        Call this api to delete a group
        """
        group = controller.get_group(oid)
        resp = group.patch()
        return resp, 204


class DeleteGroup(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete group
        Call this api to delete a group
        """
        group = controller.get_group(oid)
        resp = group.delete()
        return resp, 204


#
# object
#
class ListObjectsRequestSchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf(['subsystem', 'type', 'id', 'objid'],
                          error='Field can be subsystem, type, id, objid'), missing='id')
    subsystem = fields.String(context='query')
    type = fields.String(context='query')
    objid = fields.String(context='query')


class ListObjectsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=10)
    uuid = fields.String(required=True, default='4cdf0ea4-159a-45aa-96f2-708e461130e1')
    objid = fields.String(required=True, default='396587362//3328462822')
    subsystem = fields.String(required=True, default='auth')
    type = fields.String(required=True, default='Role')
    desc = fields.String(required=True, default='test')
    date = fields.Nested(ApiObjectResponseDateSchema, required=True, allow_none=True)
    active = fields.Boolean(required=True, default=True)


class ListObjectsResponseSchema(PaginatedResponseSchema):
    objects = fields.Nested(ListObjectsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListObjects(SwaggerApiView):
    summary = 'List objects'
    description = 'List objects'
    tags = ['authorization']
    definitions = {
        'ListObjectsResponseSchema': ListObjectsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListObjectsRequestSchema)
    parameters_schema = ListObjectsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListObjectsResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        objid = data.get('objid', None)
        if objid is not None:
            data['objid'] = objid.replace('_', '//')
        res, total = controller.objects.get_objects(**data)

        return self.format_paginated_response(res, 'objects', total, **data)


class GetObjectResponseSchema(Schema):
    object = fields.Nested(ListObjectsParamsResponseSchema, required=True, allow_none=True)


class GetObject(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'GetObjectResponseSchema': GetObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetObjectResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Get object
        Call this api to get a object
        """
        obj = controller.objects.get_object(oid)
        res = obj
        resp = {'object': res}
        return resp


class CreateObjectParamRequestSchema(Schema):
    subsystem = fields.String(required=True)
    type = fields.String(required=True)
    objid = fields.String(required=True)
    desc = fields.String(required=True)


class CreateObjectRequestSchema(Schema):
    objects = fields.Nested(CreateObjectParamRequestSchema, many=True)


class CreateObjectBodyRequestSchema(Schema):
    body = fields.Nested(CreateObjectRequestSchema, context='body')


class CreateObjectResponseSchema(Schema):
    ids = fields.List(fields.Int(required=True, default=10))


class CreateObject(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'CreateObjectRequestSchema': CreateObjectRequestSchema,
        'CreateObjectResponseSchema':CreateObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateObjectBodyRequestSchema)
    parameters_schema = CreateObjectRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CreateObjectResponseSchema
        }
    })

    def post(self, controller:AuthController, data, *args, **kwargs):
        """
        Create object
        Call this api to create a object
        """
        resp = controller.objects.add_objects(data.get('objects'))
        return {'ids': resp}, 201


class DeleteObject(SwaggerApiView):
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        Delete object
        Call this api to delete a object
        """
        # oid syntax: objtype:objdef:objid
        if oid.find(':') >= 0:
            objtype, objdef, objid = oid.split(':')
            objid = objid.replace('__', '//')
            resp = controller.objects.remove_object(objdef=objdef, objtype=objtype, objid=objid)
        # oid syntax: int or uuid
        else:
            resp = controller.objects.remove_object(oid=oid)
        return resp, 204


#
# object types
#
class ListObjectTypesRequestSchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf(['subsystem', 'type', 'id', 'objid'],
                          error='Field can be subsystem, type, id, objid'), missing='id')
    subsystem = fields.String(context='query')
    type = fields.String(context='query')
    objid = fields.String(context='query')


class ListObjectTypesParamsResponseSchema(Schema):
    subsystem = fields.String(required=True, default='auth')
    type = fields.String(required=True, default='Role')


class ListObjectTypesResponseSchema(PaginatedResponseSchema):
    object_types = fields.Nested(ListObjectTypesParamsResponseSchema, many=True, required=True, allow_none=True)


class ListObjectTypes(SwaggerApiView):
    summary = 'List object types'
    description = 'List object types'
    tags = ['authorization']
    definitions = {
        'ListObjectTypesResponseSchema': ListObjectTypesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListObjectTypesRequestSchema)
    parameters_schema = ListObjectTypesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListObjectTypesResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        """
        List object types
        Call this api to list object types
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
          - name: subsystem
            in: query
            required: false
            description: Filter object by subsystem
            type: string
          - name: type
            in: query
            required: false
            description: Filter object by type
            type: string
          - name: page
            in: query
            required: false
            description: Set list page
            type: integer
            default: 0
          - name: size
            in: query
            required: false
            description: Set list page size
            type: integer
            minimum: 0
            maximum: 100
            default: 10
          - name: order
            in: query
            required: false
            description: Set list order
            type: string
            enum:
              - ASC
              - DESC
            default: DESC
          - name: field
            in: query
            required: false
            description: Set list order field
            type: string
            default: id
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          403:
            $ref: "#/responses/Forbidden"
          405:
            $ref: "#/responses/MethodAotAllowed"
          408:
            $ref: "#/responses/Timeout"
          410:
            $ref: "#/responses/Gone"
          415:
            $ref: "#/responses/UnsupportedMediaType"
          422:
            $ref: "#/responses/UnprocessableEntity"
          429:
            $ref: "#/responses/TooManyRequests"
          200:
            description: success
            schema:
              type: object
              required: [object-types, count, page, total, sort]
              properties:
                count:
                  type: integer
                  example: 1
                page:
                  type: integer
                  example: 0
                total:
                  type: integer
                  example: 10
                sort:
                  type: object
                  required: [field, order]
                  properties:
                    order:
                      type: string
                      enum:
                        - ASC
                        - DESC
                      example: DESC
                    field:
                      type: string
                      example: id
                object-types:
                  type: array
                  items:
                    type: object
                    required: [id, type, subsystem, date]
                    properties:
                      id:
                        type: integer
                        example: 1
                      type:
                        type: string
                        example: Objects
                      subsystem:
                        type: string
                        example: auth
                      date:
                        type: object
                        required: [creation]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
        """
        res, total = controller.objects.get_type(**data)
        return self.format_paginated_response(res, 'object_types', total, **data)


class CreateObjectTypeParamRequestSchema(Schema):
    subsystem = fields.String(required=True)
    type = fields.String(required=True)


class CreateObjectTypeRequestSchema(Schema):
    object_types = fields.Nested(CreateObjectTypeParamRequestSchema, many=True)


class CreateObjectTypeBodyRequestSchema(Schema):
    body = fields.Nested(CreateObjectTypeRequestSchema, context='body')


class CreateObjectTypeResponseSchema(Schema):
    ids = fields.List(fields.Int(required=True, default=10))


class CreateObjectType(SwaggerApiView):
    summary = 'Create object type'
    description = 'Create object type'
    tags = ['authorization']
    definitions = {
        'CreateObjectTypeRequestSchema': CreateObjectTypeRequestSchema,
        'CreateObjectTypeResponseSchema': CreateObjectTypeResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateObjectTypeBodyRequestSchema)
    parameters_schema = CreateObjectTypeRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            'description': 'success',
            'schema': CreateObjectTypeResponseSchema
        }
    })

    def post(self, controller:AuthController, data, *args, **kwargs):
        resp = controller.objects.add_types(data['object_types'])
        return {'ids': resp}, 201


class DeleteObjectType(SwaggerApiView):
    summary = 'Delete object type'
    description = 'Delete object type'
    tags = ['authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            'description': 'no response'
        }
    })

    def delete(self, controller:AuthController, data, oid, *args, **kwargs):
        resp = controller.objects.remove_type(oid=oid)
        return resp, 204


#
# object action
#
class ListObjectActionResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, description='action id')
    value = fields.String(required=True, default='test', description='action value')


class ListObjectActionsResponseSchema(Schema):
    object_actions = fields.Nested(ListObjectActionResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, default=10, example=10, description='number of query items returned')


class ListObjectActions(ApiView):
    summary = 'List object actions'
    description = 'List object actions'
    tags = ['authorization']
    definitions = {
        'ListObjectActionsResponseSchema': ListObjectActionsResponseSchema,
    }
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListObjectActionsResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        res = controller.objects.get_action()
        resp = {'object_actions': res, 'count': len(res)}
        return resp


#
# object perms
#
class ListObjectPermsRequestSchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf(['subsystem', 'type', 'id', 'objid', 'aid', 'action'],
                          error='Field can be subsystem, type, id, objid, aid, action'), missing='id')
    subsystem = fields.String(context='query')
    type = fields.String(context='query')
    objid = fields.String(context='query')
    oid = fields.String(context='query')
    user = fields.String(context='query')
    role = fields.String(context='query')
    group = fields.String(context='query')
    cascade = fields.Boolean(context='query', missing=False)


class ListObjectPermsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=10)
    oid = fields.Integer(required=True, default=11)
    objid = fields.String(required=True, default='396587362//3328462822')
    type = fields.String(required=True, default='auth')
    subsystem = fields.String(required=True, default='Role')
    desc = fields.String(required=True, default='test')
    aid = fields.Integer(required=True, default=12)
    action = fields.String(required=True, default='view')


class ListObjectPermsResponseSchema(PaginatedResponseSchema):
    perms = fields.Nested(ListObjectPermsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListObjectPerms(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'ListObjectPermsResponseSchema': ListObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListObjectPermsRequestSchema)
    parameters_schema = ListObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': ListObjectPermsResponseSchema
        }
    })

    def get(self, controller:AuthController, data, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions
        """
        user = data.get('user', None)
        role = data.get('role', None)
        group = data.get('group', None)
        objid = data.get('objid', None)
        subsystem = data.get('subsystem', None)
        type = data.get('type', None)
        oid = data.get('oid', None)
        if user is None and role is None and group is None and objid is None and subsystem is None and type is None and oid is None :
            raise ApiManagerError("No parameters when qeryin permisssions", code=400)


        if objid is not None:
            data['objid'] = objid.replace('_', '//')
        if user is not None:
            user = controller.get_user(user)
            objs, total = user.get_permissions(**data)
        elif role is not None:
            role = controller.get_role(role)
            objs, total = role.get_permissions(**data)
        elif group is not None:
            group = controller.get_group(group)
            objs, total = group.get_permissions(**data)
        else:
            objs, total = controller.objects.get_permissions(**data)
        return self.format_paginated_response(objs, 'perms', total, **data)


class GetObjectPermResponseSchema(Schema):
    perm = fields.Nested(ListObjectPermsParamsResponseSchema, required=True, allow_none=True)


class GetObjectPerm(SwaggerApiView):
    tags = ['authorization']
    definitions = {
        'GetObjectPermResponseSchema': GetObjectPermResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            'description': 'success',
            'schema': GetObjectPermResponseSchema
        }
    })

    def get(self, controller:AuthController, data, oid, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions
        """
        res = controller.objects.get_permission(oid)
        resp = {'perm': res}
        return resp


class AuthorizationAPI(ApiView):
    """Authorization API
    """
    @staticmethod
    def register_api(module, **kwargs):
        rules = [
            # new routes
            ('%s/providers' % module.base_path, 'GET', ListProviders, {'secure': False}),

            ('%s/tokens' % module.base_path, 'GET', ListTokens, {}),
            ('%s/tokens/<oid>' % module.base_path, 'GET', GetToken, {}),
            # ('%s/tokens/<oid>/refresh' % module.base_path, 'PUT', TokenRefresh, {}),
            ('%s/tokens/<oid>' % module.base_path, 'DELETE', DeleteToken, {}),
            # ('%s/tokens/<oid>/exist' % module.base_path, 'GET', LoginExists, {}),

            ('%s/users' % module.base_path, 'GET', ListUsers, {}),
            ('%s/users/<oid>' % module.base_path, 'GET', GetUser, {}),
            ('%s/users/<oid>/attributes' % module.base_path, 'GET', GetUserAtributes, {}),
            ('%s/users' % module.base_path, 'POST', CreateUser, {}),
            ('%s/users/<oid>' % module.base_path, 'PUT', UpdateUser, {}),
            ('%s/users/<oid>/secret' % module.base_path, 'GET', GetUserSecret, {}),
            ('%s/users/<oid>/secret' % module.base_path, 'PUT', ResetUserSecret, {}),
            ('%s/users/<oid>/attributes' % module.base_path, 'POST', CreateUserAttribute, {}),
            ('%s/users/<oid>/attributes/<aid>' % module.base_path, 'DELETE', DeleteUserAttribute, {}),
            ('%s/users/<oid>' % module.base_path, 'DELETE', DeleteUser, {}),

            ('%s/roles' % module.base_path, 'GET', ListRoles, {}),
            ('%s/roles/<oid>' % module.base_path, 'GET', GetRole, {}),
            ('%s/roles' % module.base_path, 'POST', CreateRole, {}),
            ('%s/roles/<oid>' % module.base_path, 'PUT', UpdateRole, {}),
            ('%s/roles/<oid>' % module.base_path, 'DELETE', DeleteRole, {}),

            ('%s/groups' % module.base_path, 'GET', ListGroups, {}),
            ('%s/groups/<oid>' % module.base_path, 'GET', GetGroup, {}),
            ('%s/groups' % module.base_path, 'POST', CreateGroup, {}),
            ('%s/groups/<oid>' % module.base_path, 'PUT', UpdateGroup, {}),
            ('%s/groups/<oid>' % module.base_path, 'PATCH', PatchGroup, {}),
            ('%s/groups/<oid>' % module.base_path, 'DELETE', DeleteGroup, {}),

            ('%s/objects' % module.base_path, 'GET', ListObjects, {}),
            ('%s/objects/<oid>' % module.base_path, 'GET', GetObject, {}),
            ('%s/objects' % module.base_path, 'POST', CreateObject, {}),
            ('%s/objects/<oid>' % module.base_path, 'DELETE', DeleteObject, {}),
            ('%s/objects/types' % module.base_path, 'GET', ListObjectTypes, {}),
            ('%s/objects/types' % module.base_path, 'POST', CreateObjectType, {}),
            ('%s/objects/types/<oid>' % module.base_path, 'DELETE', DeleteObjectType, {}),
            ('%s/objects/perms' % module.base_path, 'GET', ListObjectPerms, {}),
            ('%s/objects/perms/<oid>' % module.base_path, 'GET', GetObjectPerm, {}),
            ('%s/objects/actions' % module.base_path, 'GET', ListObjectActions, {}),
        ]

        ApiView.register_api(module, rules, **kwargs)
