"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from datetime import datetime
from beecell.simple import get_value, str2bool, AttribException, format_date
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CrudApiObjectResponseSchema, GetApiObjectRequestSchema,\
    ApiObjectResponseDateSchema
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from flasgger.marshmallow_apispec import SwaggerView


class BaseCreateRequestSchema(Schema):
    name = fields.String(required=True, error_messages={u'required': u'name is required.'})
    desc = fields.String(required=True, error_messages={u'required': u'desc is required.'})


class BaseUpdateRequestSchema(Schema):
    name = fields.String(allow_none=True)
    desc = fields.String(allow_none=True)
    active = fields.Boolean(context=u'query', allow_none=True)
    expiry_date = fields.String(default=u'2099-12-31', allow_none=True)


class BaseCreateExtendedParamRequestSchema(Schema):
    active = fields.Boolean(missing=True, allow_none=True)
    expiry_date = fields.String(load_from=u'expirydate', missing=None, 
                                allow_none=True, example=u'',
                                description=u'expiration date. [default=365days]')
    
    @post_load
    def make_expiry_date(self, data):
        expiry_date = data.get(u'expiry_date', None)
        if expiry_date is not None:
            #expiry_date = expiry_date.replace(u'T', u'')
            y, m, d = expiry_date.split(u'-')
            expiry_date = datetime(int(y), int(m), int(d))
            data[u'expiry_date'] = expiry_date
        return data


class BaseUpdateMultiRequestSchema(Schema):
    append = fields.List(fields.String())
    remove = fields.List(fields.String())

#
# authentication domains
#
class ListDomainsRequestSchema(Schema):
    pass


class ListDomainsParamsResponseSchema(Schema):
    name = fields.String(required=True, example=u'local', description=u'login domain name')
    type = fields.String(required=True, example=u'DatabaseAuth', description=u'login domain description')


class ListDomainsResponseSchema(Schema):
    domains = fields.Nested(ListDomainsParamsResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, example=1, description=u'Domains count')


class ListDomains(SwaggerApiView):
    tags = [u'auth']
    definitions = {
        u'ListDomainsResponseSchema': ListDomainsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListDomainsRequestSchema)
    parameters_schema = ListDomainsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListDomainsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        List authentication domains
        Call this api to list authentication domains
        """
        auth_providers = controller.module.authentication_manager.auth_providers
        res = []
        for domain, auth_provider in auth_providers.iteritems():
            res.append({u'name':domain, 
                        u'type':auth_provider.__class__.__name__})
        resp = {u'domains':res,
                u'count':len(res)}
        return resp

#
# identity
#
## list
class ListTokensRequestSchema(Schema):
    pass


class ListTokensParamsResponseSchema(Schema):
    ip = fields.String(required=True, example=u'pc160234.csi.it', description=u'client login ip address')
    ttl = fields.Integer(required=True, example=3600, description=u'token ttl')
    token = fields.String(required=True, example=u'28ff1dd5-5520-42f3-a361-c58f19d20b7c', description=u'token')
    user = fields.String(required=True, example=u'admin@local', description=u'client login user')
    timestamp = fields.String(required=True, example=u'internal', description=u'token timestamp')
    type = fields.String(required=True, example=u'internal', description=u'token type')


class ListTokensResponseSchema(Schema):
    tokens = fields.Nested(ListTokensParamsResponseSchema, many=True, required=True, allow_none=True)
    count = fields.Integer(required=True, example=1, description=u'Token count')


class ListTokens(SwaggerApiView):
    tags = [u'auth']
    definitions = {
        u'ListTokensResponseSchema': ListTokensResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListTokensRequestSchema)
    parameters_schema = ListTokensRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListTokensResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        List authentication tokens
        Call this api to list authentication tokens
        """        
        identities = controller.get_identities()        
        res = []
        for i in identities:            
            user = i.get(u'user')
            user_name = None
            if user is not None:
                user_name = user[u'name']
            res.append({
                u'token':i[u'uid'],
                u'type':i[u'type'],
                u'user':user_name,
                u'timestamp':format_date(i[u'timestamp']), 
                u'ttl':i[u'ttl'], 
                u'ip':i[u'ip']
            })
        resp = {u'tokens': res,
                u'count': len(res)}
        return resp


## get
class GetTokenUserResponseSchema(Schema):
    name = fields.String(required=True, example=u'admin@local', description=u'client login user')
    roles = fields.List(fields.String(example=u'admin@local'), required=True, description=u'client login user')
    perms = fields.String(required=True, example=u'admin@local', description=u'client login perms')
    active = fields.Boolean(required=True, example=True, description=u'client login active')
    id = fields.UUID(required=True, description=u'client login uuid', example=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')


class GetTokenParamsResponseSchema(Schema):
    ip = fields.String(required=True, example=u'pc160234.csi.it', description=u'client login ip address')
    ttl = fields.Integer(required=True, example=3600, description=u'token ttl')
    token = fields.String(required=True, example=u'28ff1dd5-5520-42f3-a361-c58f19d20b7c', description=u'token')
    user = fields.Nested(GetTokenUserResponseSchema, required=True, description=u'client login user', allow_none=True)
    timestamp = fields.String(required=True, example=u'internal', description=u'token timestamp')
    type = fields.String(required=True, example=u'internal', description=u'token type')


class GetTokenResponseSchema(Schema):
    token = fields.Nested(ListTokensParamsResponseSchema, required=True, allow_none=True)


class GetToken(SwaggerApiView):
    tags = [u'auth']
    definitions = {
        u'ListTokensResponseSchema': ListTokensResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetTokenResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get authentication token
        Call this api to get authentication token                      
        """                
        data = controller.get_identity(oid)
        res = {
            u'token':data[u'uid'],
            u'type':data[u'type'],
            u'user':data[u'user'],
            u'timestamp':format_date(data[u'timestamp']), 
            u'ttl':data[u'ttl'], 
            u'ip':data[u'ip']}
        resp = {u'token':res}
        return resp

'''
class TokenRefresh(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        uid, sign, data = self.get_current_identity()
        # refresh user permisssions
        res = controller.refresh_user(oid, sign, data)
        resp = res      
        return resp

class LoginExists(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        resp = controller.exist_identity(oid)
        return {u'token':oid, u'exist':resp} '''

## delete
class DeleteToken(SwaggerApiView):
    tags = [u'auth']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })

    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete authentication token
        Call this api to delete an authentication token     
        """        
        resp = controller.remove_identity(oid)
        return (resp, 204)

#
# user
#
class ListUsersRequestSchema(PaginatedRequestQuerySchema):
    group = fields.String(context=u'query')
    role = fields.String(context=u'query')
    active = fields.Boolean(context=u'query')
    expiry_date = fields.String(load_from=u'expirydate', default=u'2099-12-31',context=u'query')
    name = fields.String(context=u'query')
    names = fields.String(context=u'query')


class ListUsersResponseSchema(PaginatedResponseSchema):
    users = fields.Nested(ApiObjectResponseSchema, many=True, required=True, allow_none=True)


class ListUsers(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'ListUsersResponseSchema': ListUsersResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListUsersRequestSchema)
    parameters_schema = ListUsersRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListUsersResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List users
        Call this api to list users
        """
        objs, total = controller.get_users(**data)
        res = [r.info() for r in objs]

        return self.format_paginated_response(res, u'users', total, **data)


class GetUserParamsResponseSchema(ApiObjectResponseSchema):
    secret = fields.String(required=True, default=u'test', example=u'test')


class GetUserResponseSchema(Schema):
    user = fields.Nested(GetUserParamsResponseSchema, required=True, allow_none=True)


class GetUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetUserResponseSchema': GetUserResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetUserResponseSchema
        }
    })    
    
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get user
        Call this api to get user by id, uuid or name
        """
        obj = controller.get_user(oid)
        res = obj.detail()
        resp = {u'user': res}
        return resp


## list attributes
class GetUserAtributesParamResponseSchema(Schema):
    name = fields.String(required=True, default=u'test')
    value = fields.String(required=True, default=u'test')
    desc = fields.String(required=True, default=u'test')


class GetUserAtributesResponseSchema(Schema):
    count = fields.Integer(required=True, defaut=0)
    user_attributes = fields.Nested(GetUserAtributesParamResponseSchema, many=True, required=True, allow_none=True)


class GetUserAtributes(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetUserAtributesResponseSchema': GetUserAtributesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetUserAtributesResponseSchema
        }
    })     
    
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get user attributes
        Call this api to get user attributes
        """
        user = controller.get_user(oid)
        res = user.get_attribs()
        resp = {u'user_attributes':res,
                u'count':len(res)} 
        return resp

## create
class CreateUserParamRequestSchema(BaseCreateRequestSchema, BaseCreateExtendedParamRequestSchema):
    password = fields.String(validate=Length(min=8, max=20), error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                                             error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'), missing=u'DBUSER')
    base = fields.Boolean(missing=False)
    system = fields.Boolean(missing=False)
    
    @validates(u'name')
    def validate_user(self, value):
        if not match(u'[\w\W]+@[\w\W]+', value):
            raise ValidationError(u'User name syntax must be <name>@<domain>') 


class CreateUserRequestSchema(Schema):
    user = fields.Nested(CreateUserParamRequestSchema)


class CreateUserBodyRequestSchema(Schema):
    body = fields.Nested(CreateUserRequestSchema, context=u'body')


class CreateUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateUserRequestSchema': CreateUserRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateUserBodyRequestSchema)
    parameters_schema = CreateUserRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create a user
        Call this api to create a user               
        """
        resp = controller.add_user(**data.get(u'user'))
        return {u'uuid': resp}, 201


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
                             error=u'Password must be at least 8 characters')

    
    # @validates(u'name')
    # def validate_user(self, value):
    #     if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
    #         raise ValidationError(u'User name syntax must be <name>@<domain>')


class UpdateUserRequestSchema(Schema):
    user = fields.Nested(UpdateUserParamRequestSchema)


class UpdateUserBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateUserRequestSchema, context=u'body')


class UpdateUserResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    role_append = fields.List(fields.String, dump_to=u'role_append', required=True)
    role_remove = fields.List(fields.String, dump_to=u'role_remove', required=True)
    perm_append = fields.List(fields.String, dump_to=u'perm_append', required=True)
    perm_remove = fields.List(fields.String, dump_to=u'perm_remove', required=True)


class UpdateUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateUserRequestSchema': UpdateUserRequestSchema,
        u'UpdateUserResponseSchema': UpdateUserResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateUserBodyRequestSchema)
    parameters_schema = UpdateUserRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': UpdateUserResponseSchema
        }
    })    

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update user
        Call this api to update a user
        """
        data = data.get(u'user')
        role = data.pop(u'roles', None)
        role_perm = data.pop(u'perms', None)
        user = controller.get_user(oid)
        
        resp = {u'update': None, u'role_append': [], u'role_remove': [], u'perm_append': [], u'perm_remove': []}
        
        # append, remove role
        if role is not None:
            # append role
            if u'append' in role:
                for role, expiry in role.get(u'append'):
                    res = user.append_role(role, expiry_date=expiry)
                    resp[u'role_append'].append(res)
        
            # remove role
            if u'remove' in role:
                for role in role.get(u'remove'):
                    res = user.remove_role(role)
                    resp[u'role_remove'].append(res)

        # append, remove perms
        if role_perm is not None:
            # append role
            if u'append' in role_perm:
                perms = []
                for perm in role_perm.get(u'append'):
                    perms.append(perm)
                res = user.append_permissions(perms)
                resp[u'perm_append'] = res

            # remove role
            if u'remove' in role_perm:
                perms = []
                for perm in role_perm.get(u'remove'):
                    perms.append(perm)
                res = user.remove_permissions(perms)
                resp[u'perm_remove'] = res

        # update user
        res = user.update(**data)
        resp[u'update'] = res
        return resp


class UserAttribSchemaCreateParam(Schema):
    name = fields.String(required=True)
    new_name = fields.String()
    value = fields.String(required=True)
    desc = fields.String(required=True)


class CreateUserAttributeRequestSchema(Schema):
    user_attribute = fields.Nested(UserAttribSchemaCreateParam, load_from=u'user_attribute')


class CreateUserAttributeBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(CreateUserAttributeRequestSchema, context=u'body')


class CreateUserAttributeResponseSchema(Schema):
    name = fields.String(required=True, default=u'test')
    value = fields.String(required=True, default=u'test')
    desc = fields.String(required=True, default=u'test')


class CreateUserAttribute(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateUserAttributeRequestSchema': CreateUserAttributeRequestSchema,
        u'CreateUserAttributeResponseSchema': CreateUserAttributeResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateUserAttributeBodyRequestSchema)
    parameters_schema = CreateUserAttributeRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateUserAttributeResponseSchema
        }
    })       

    def post(self, controller, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user
        """
        user = controller.get_user(oid)
        attr = user.set_attribute(**data.get(u'user_attribute'))
        resp = {u'name':attr.name, u'value':attr.value, u'desc':attr.desc}
        return (resp, 201)

## delete attributes
class DeleteUserAttributeRequestSchema(GetApiObjectRequestSchema):
    aid = fields.String(required=True, description=u'attribute name',
                        context=u'path')

class DeleteUserAttribute(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(DeleteUserAttributeRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })    
    
    def delete(self, controller, data, oid, aid, *args, **kwargs):
        """
        Delete user attribute
        Call this api to delete a user attribute   
        """        
        user = controller.get_user(oid)
        resp = user.remove_attribute(aid)
        return (resp, 204)

## delete
class DeleteUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })      
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user 
        """
        user = controller.get_user(oid)
        resp = user.delete()
        return (resp, 204)


#
# role
#
class ListRolesRequestSchema(PaginatedRequestQuerySchema):
    user = fields.String(context=u'query')
    group = fields.String(context=u'query')
    names = fields.String(context=u'query')


class ListRolesResponseSchema(PaginatedResponseSchema):
    roles = fields.Nested(ApiObjectResponseSchema, many=True, required=True, allow_none=True)


class ListRoles(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'ListRolesResponseSchema': ListRolesResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListRolesRequestSchema)
    parameters_schema = ListRolesRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListRolesResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List roles
        Call this api to list roles
        """      
        objs, total = controller.get_roles(**data)
        
        res = [r.info() for r in objs]
        return self.format_paginated_response(res, u'roles', total, **data)


class GetRoleResponseSchema(Schema):
    role = fields.Nested(ApiObjectResponseSchema, required=True, allow_none=True)


class GetRole(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetRoleResponseSchema': GetRoleResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetRoleResponseSchema
        }
    })      
    
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get role
        Call this api to get a role
        """             
        obj = controller.get_role(oid)
        res = obj.info()      
        resp = {u'role':res} 
        return resp


## create
class CreateRoleRequestSchema(Schema):
    role = fields.Nested(BaseCreateRequestSchema)


class CreateRoleBodyRequestSchema(Schema):
    body = fields.Nested(CreateRoleRequestSchema, context=u'body')


class CreateRole(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateRoleRequestSchema': CreateRoleRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateRoleBodyRequestSchema)
    parameters_schema = CreateRoleRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        """
        Create role
        Call this api to create a role
        """
        resp = controller.add_role(**data.get(u'role'))
        return ({u'uuid':resp}, 201)


class UpdateRoleParamPermDescRequestSchema(Schema):
    type = fields.String()
    subsystem = fields.String()
    objid = fields.String()
    action = fields.String()
    id = fields.Integer()


class UpdateRoleParamPermRequestSchema(Schema):
    append = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True, allow_none=True)
    remove = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True, allow_none=True)


class UpdateRoleParamRequestSchema(BaseUpdateRequestSchema, BaseCreateExtendedParamRequestSchema):
    perms = fields.Nested(UpdateRoleParamPermRequestSchema, allow_none=True)


class UpdateRoleRequestSchema(Schema):
    role = fields.Nested(UpdateRoleParamRequestSchema)


class UpdateRoleBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateRoleRequestSchema, context=u'body')


class UpdateRoleResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    perm_append = fields.List(fields.String, dump_to=u'perm_append', required=True)
    perm_remove = fields.List(fields.String, dump_to=u'perm_remove', required=True)

    
class UpdateRole(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateRoleRequestSchema':UpdateRoleRequestSchema,
        u'UpdateRoleResponseSchema':UpdateRoleResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateRoleBodyRequestSchema)
    parameters_schema = UpdateRoleRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': UpdateRoleResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update role
        Call this api to update a role
        """
        data = data.get(u'role')
        role_perm = data.pop(u'perms', None)
        role = controller.get_role(oid)
        
        resp = {u'update': None, u'perm_append': [], u'perm_remove': []}
        
        # append, remove role
        if role_perm is not None:
            # append role
            if u'append' in role_perm:
                perms = []
                for perm in role_perm.get(u'append'):
                    perms.append(perm)
                res = role.append_permissions(perms)
                resp[u'perm_append'] = res
        
            # remove role
            if u'remove' in role_perm:
                perms = []
                for perm in role_perm.get(u'remove'):
                    perms.append(perm)
                res = role.remove_permissions(perms)
                resp[u'perm_remove'] = res
        
        # update role
        res = role.update(**data)        
        resp[u'update'] = res
        return resp


class DeleteRole(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete role
        Call this api to delete a role
        """
        role = controller.get_role(oid)
        resp = role.delete()
        return (resp, 204)


#
# group
#
## list
class ListGroupsRequestSchema(PaginatedRequestQuerySchema):
    user = fields.String(context=u'query')
    role = fields.String(context=u'query')
    active = fields.Boolean(context=u'query')
    expiry_date = fields.String(load_from=u'expirydate', default=u'2099-12-31', context=u'query')


class ListGroupsResponseSchema(PaginatedResponseSchema):
    groups = fields.Nested(ApiObjectResponseSchema, many=True, required=True, allow_none=True)


class ListGroups(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'ListGroupsResponseSchema': ListGroupsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListGroupsRequestSchema)
    parameters_schema = ListGroupsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListGroupsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List groups
        Call this api to list groups                      
        """
        objs, total = controller.get_groups(**data)
        
        res = [r.info() for r in objs]  
        return self.format_paginated_response(res, u'groups', total, **data)


## get
class GetGroupResponseSchema(Schema):
    group = fields.Nested(ApiObjectResponseSchema, required=True, allow_none=True)


class GetGroup(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetGroupResponseSchema': GetGroupResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetGroupResponseSchema
        }
    })

    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get group
        Call this api to get a group
        """                
        obj = controller.get_group(oid)
        res = obj.info()      
        resp = {u'group':res} 
        return resp


## create
class CreateGroupParamRequestSchema(BaseCreateRequestSchema, BaseCreateExtendedParamRequestSchema):
    pass


class CreateGroupRequestSchema(Schema):
    group = fields.Nested(CreateGroupParamRequestSchema)


class CreateGroupBodyRequestSchema(Schema):
    body = fields.Nested(CreateGroupRequestSchema, context=u'body')


class CreateGroup(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateGroupRequestSchema': CreateGroupRequestSchema,
        u'CrudApiObjectResponseSchema':CrudApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateGroupBodyRequestSchema)
    parameters_schema = CreateGroupRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CrudApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create group
        Call this api to create a group
        """
        resp = controller.add_group(**data.get(u'group'))
        return ({u'uuid':resp}, 201)   


## update
class UpdateGroupParamRoleRequestSchema(Schema):
    append = fields.List(fields.String())
    remove = fields.List(fields.String())


class UpdateGroupParamRequestSchema(BaseUpdateRequestSchema, BaseCreateExtendedParamRequestSchema):
    roles = fields.Nested(UpdateGroupParamRoleRequestSchema, allow_none=True)
    users = fields.Nested(UpdateGroupParamRoleRequestSchema, allow_none=True)


class UpdateGroupRequestSchema(Schema):
    group = fields.Nested(UpdateGroupParamRequestSchema)


class UpdateGroupBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateGroupRequestSchema, context=u'body')


class UpdateGroupResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7', required=True)
    role_append = fields.List(fields.String, dump_to=u'role_append', required=True)
    role_remove = fields.List(fields.String, dump_to=u'role_remove', required=True)
    user_append = fields.List(fields.String, dump_to=u'user_append', required=True)
    user_remove = fields.List(fields.String, dump_to=u'user_remove', required=True)


class UpdateGroup(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateGroupRequestSchema':UpdateGroupRequestSchema,
        u'UpdateGroupResponseSchema':UpdateGroupResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(UpdateGroupBodyRequestSchema)
    parameters_schema = UpdateGroupRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': UpdateGroupResponseSchema
        }
    })

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update group
        Call this api to update a group
        """        
        data = data.get(u'group')
        group_role = data.pop(u'roles', None)
        group_user = data.pop(u'users', None)
        
        group = controller.get_group(oid)
        
        resp = {u'update':None,
                u'role_append':[], u'role_remove':[], 
                u'user_append':[], u'user_remove':[]}
        
        # append, remove role
        if group_role is not None:
            # append role
            if u'append' in group_role:
                for role in group_role.get(u'append'):
                    res = group.append_role(role)
                    resp[u'role_append'].append(res)
        
            # remove role
            if u'remove' in group_role:
                for role in group_role.get(u'remove'):
                    res = group.remove_role(role)
                    resp[u'role_remove'].append(res)
                    
        # append, remove user
        if group_user is not None:
            # append user
            if u'append' in group_user:
                for user in group_user.get(u'append'):
                    res = group.append_user(user)
                    resp[u'user_append'].append(res)
        
            # remove user
            if u'remove' in group_user:
                for user in group_user.get(u'remove'):
                    res = group.remove_user(user)
                    resp[u'user_remove'].append(res)                    
        
        # update group
        res = group.update(**data)        
        resp[u'update'] = res
        return resp

## delete
class DeleteGroup(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })      
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete group
        Call this api to delete a group   
        """                
        group = controller.get_group(oid)
        resp = group.delete()
        return (resp, 204)


#
# object
#
class ListObjectsRequestSchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id', u'objid'],
                          error=u'Field can be subsystem, type, id, objid'),
                          missing=u'id')    
    subsystem = fields.String(context=u'query')
    type = fields.String(context=u'query')
    objid = fields.String(context=u'query')


class ListObjectsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=10)
    uuid = fields.String(required=True, default=u'4cdf0ea4-159a-45aa-96f2-708e461130e1')
    objid = fields.String(required=True, default=u'396587362//3328462822')
    subsystem = fields.String(required=True, default=u'auth')
    type = fields.String(required=True, default=u'Role')
    desc = fields.String(required=True, default=u'test')
    date = fields.Nested(ApiObjectResponseDateSchema, required=True, allow_none=True)
    active = fields.Boolean(required=True, default=True)


class ListObjectsResponseSchema(PaginatedResponseSchema):
    objects = fields.Nested(ListObjectsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListObjects(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'ListObjectsResponseSchema': ListObjectsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListObjectsRequestSchema)
    parameters_schema = ListObjectsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListObjectsResponseSchema
        }
    })
    
    def get(self, controller, data, *args, **kwargs):
        """
        List objects
        Call this api to list objects
        """
        objid = data.get(u'objid', None)
        if objid is not None:
            data[u'objid'] = objid.replace(u'_', u'//')
        res, total = controller.objects.get_objects(**data)
        
        return self.format_paginated_response(res, u'objects', total, **data)


## get
class GetObjectResponseSchema(Schema):
    object = fields.Nested(ListObjectsParamsResponseSchema, required=True, allow_none=True)


class GetObject(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetObjectResponseSchema': GetObjectResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetObjectResponseSchema
        }
    })
    
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get object
        Call this api to get a object
        """                        
        obj = controller.objects.get_object(oid)
        res = obj
        resp = {u'object':res} 
        return resp


## create
class CreateObjectParamRequestSchema(Schema):
    subsystem = fields.String(required=True)
    type = fields.String(required=True)
    objid = fields.String(required=True)
    desc = fields.String(required=True)    


class CreateObjectRequestSchema(Schema):
    objects = fields.Nested(CreateObjectParamRequestSchema, many=True)

    
class CreateObjectBodyRequestSchema(Schema):
    body = fields.Nested(CreateObjectRequestSchema, context=u'body')


class CreateObjectResponseSchema(Schema):
    ids = fields.List(fields.Int(required=True, default=10))


class CreateObject(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateObjectRequestSchema': CreateObjectRequestSchema,
        u'CreateObjectResponseSchema':CreateObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateObjectBodyRequestSchema)
    parameters_schema = CreateObjectRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create object
        Call this api to create a object
        """        
        resp = controller.objects.add_objects(data.get(u'objects'))
        return ({u'ids':resp}, 201)

class DeleteObject(SwaggerApiView):
    tags = [u'authorization']
    definitions = {}
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        204: {
            u'description': u'no response'
        }
    })    
    
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete object
        Call this api to delete a object      
        """                        
        resp = controller.objects.remove_object(oid=oid)
        return (resp, 204)   

#
# object types
#
class TypeQuerySchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id'],
                          error=u'Field can be subsystem, type, id'),
                          missing=u'id')    
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()

class ListObjectTypes(ApiView):
    parameters_schema = TypeQuerySchema
    
    def get(self, controller, data, *args, **kwargs):
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
        return self.format_paginated_response(res, u'object_types', total, **data)


class ObjectTypeSchemaCreateParam(Schema):
    subsystem = fields.String()
    type = fields.String()


class ObjectTypeSchemaCreate(Schema):
    object_types = fields.Nested(ObjectTypeSchemaCreateParam, many=True, required=True, allow_none=True)


class CreateObjectType(ApiView):
    parameters_schema = ObjectTypeSchemaCreate

    def post(self, controller, data, *args, **kwargs):
        """
        Create object type
        Call this api to create a object type
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
          - in : body
            name: body
            schema:
              type: object
              required: [object-types]
              properties:
                object_types:
                  type: array
                  items:
                    type: object
                    required: [subsystem, type]
                    properties:
                      subsystem:
                        type: string
                        example: auth
                      type:
                        type: string
                        example: Objects
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
          201:
            description: success
            schema:
              type: object
              required: [ids]
              properties:
                ids:            
                  type: array
                  items:
                    type: integer
        """
        #data = get_value(data, u'object-types', None, exception=True)
        resp = controller.objects.add_types(data[u'object_types'])
        return ({u'ids':resp}, 201)  
    
class DeleteObjectType(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete object type
        Call this api to delete a object type
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
        - in: path
          name: oid
          type: integer
          required: true
          description: object type id          
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          403:
            $ref: "#/responses/Forbidden"
          404:
            $ref: "#/responses/NotFound"
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
          204:
            description: No response        
        """        
        resp = controller.objects.remove_type(oid=oid)
        return (resp, 204)      
    
#
# object action
#    
class ListObjectActions(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        List objects
        Call this api to list objects
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]          
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
              required: [object_actions, count]
              properties:
                count:
                  type: integer
                  example: 1     
                object_actions:
                  type: array
                  items:
                    type: object
                    required: [id, value]
                    properties:
                      id:
                        type: integer
                        example: 1
                      value:
                        type: string
                        example: beehive
        """
        res = controller.objects.get_action()
        resp = {u'object_actions':res,
                u'count':len(res)} 
        return resp    


#
# object perms
#
class ListObjectPermsRequestSchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id', 
                          u'objid', u'aid', u'action'],
                          error=u'Field can be subsystem, type, id, objid, aid, action'),
                          missing=u'id')      
    subsystem = fields.String(context=u'query')
    type = fields.String(context=u'query')
    objid = fields.String(context=u'query')
    user = fields.String(context=u'query')
    role = fields.String(context=u'query')
    group = fields.String(context=u'query')
    cascade = fields.Boolean(context=u'query')


class ListObjectPermsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=10)
    oid = fields.Integer(required=True, default=11)
    objid = fields.String(required=True, default=u'396587362//3328462822')
    type = fields.String(required=True, default=u'auth')
    subsystem = fields.String(required=True, default=u'Role')
    desc = fields.String(required=True, default=u'test')
    aid = fields.Integer(required=True, default=12)
    action = fields.String(required=True, default=u'view')


class ListObjectPermsResponseSchema(PaginatedResponseSchema):
    perms = fields.Nested(ListObjectPermsParamsResponseSchema, many=True, required=True, allow_none=True)


class ListObjectPerms(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'ListObjectPermsResponseSchema': ListObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(ListObjectPermsRequestSchema)
    parameters_schema = ListObjectPermsRequestSchema
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': ListObjectPermsResponseSchema
        }
    })

    def get(self, controller, data, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions              
        """
        user = data.get(u'user', None)
        role = data.get(u'role', None)
        group = data.get(u'group', None)
        objid = data.get(u'objid', None)
        if objid is not None:
            data[u'objid'] = objid.replace(u'_', u'//')
            
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
        return self.format_paginated_response(objs, u'perms', total, **data)


## get
class GetObjectPermsResponseSchema(Schema):
    perm = fields.Nested(ListObjectPermsParamsResponseSchema, required=True, allow_none=True)


class GetObjectPerms(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'GetObjectPermsResponseSchema': GetObjectPermsResponseSchema,
    }
    parameters = SwaggerHelper().get_parameters(GetApiObjectRequestSchema)
    responses = SwaggerApiView.setResponses({
        200: {
            u'description': u'success',
            u'schema': GetObjectPermsResponseSchema
        }
    })  

    def get(self, controller, data, oid, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions               
        """        
        res = controller.objects.get_permission(oid)
        resp = {u'perm':res}
        return resp


class AuthorizationAPI(ApiView):
    """Authorization API
    """
    @staticmethod
    def register_api(module):
        rules = [
            # new routes
            (u'%s/domains' % module.base_path, u'GET', ListDomains, {u'secure': False}),

            (u'%s/tokens' % module.base_path, u'GET', ListTokens, {}),
            (u'%s/tokens/<oid>' % module.base_path, u'GET', GetToken, {}),
            # (u'%s/tokens/<oid>/refresh' % module.base_path, u'PUT', TokenRefresh, {}),
            (u'%s/tokens/<oid>' % module.base_path, u'DELETE', DeleteToken, {}),
            # (u'%s/tokens/<oid>/exist' % module.base_path, u'GET', LoginExists, {}),

            (u'%s/users' % module.base_path, u'GET', ListUsers, {}),
            (u'%s/users/<oid>' % module.base_path, u'GET', GetUser, {}),
            (u'%s/users/<oid>/attributes' % module.base_path, u'GET', GetUserAtributes, {}),
            (u'%s/users' % module.base_path, u'POST', CreateUser, {}),
            (u'%s/users/<oid>' % module.base_path, u'PUT', UpdateUser, {}),
            (u'%s/users/<oid>/attributes' % module.base_path, u'POST', CreateUserAttribute, {}),
            (u'%s/users/<oid>/attributes/<aid>' % module.base_path, u'DELETE', DeleteUserAttribute, {}),
            (u'%s/users/<oid>' % module.base_path, u'DELETE', DeleteUser, {}),

            (u'%s/roles' % module.base_path, u'GET', ListRoles, {}),
            (u'%s/roles/<oid>' % module.base_path, u'GET', GetRole, {}),
            (u'%s/roles' % module.base_path, u'POST', CreateRole, {}),
            (u'%s/roles/<oid>' % module.base_path, u'PUT', UpdateRole, {}),
            (u'%s/roles/<oid>' % module.base_path, u'DELETE', DeleteRole, {}),

            (u'%s/groups' % module.base_path, u'GET', ListGroups, {}),
            (u'%s/groups/<oid>' % module.base_path, u'GET', GetGroup, {}),
            (u'%s/groups' % module.base_path, u'POST', CreateGroup, {}),
            (u'%s/groups/<oid>' % module.base_path, u'PUT', UpdateGroup, {}),
            (u'%s/groups/<oid>' % module.base_path, u'DELETE', DeleteGroup, {}),

            (u'%s/objects' % module.base_path, u'GET', ListObjects, {}),
            (u'%s/objects/<oid>' % module.base_path, u'GET', GetObject, {}),
            (u'%s/objects' % module.base_path, u'POST', CreateObject, {}),
            (u'%s/objects/<oid>' % module.base_path, u'DELETE', DeleteObject, {}),
            (u'%s/objects/types' % module.base_path, u'GET', ListObjectTypes, {}),
            (u'%s/objects/types' % module.base_path, u'POST', CreateObjectType, {}),
            (u'%s/objects/types/<oid>' % module.base_path, u'DELETE', DeleteObjectType, {}),
            (u'%s/objects/perms' % module.base_path, u'GET', ListObjectPerms, {}),
            (u'%s/objects/perms/<oid>' % module.base_path, u'GET', GetObjectPerms, {}),
            (u'%s/objects/actions' % module.base_path, u'GET', ListObjectActions, {}),
        ]

        ApiView.register_api(module, rules)
