"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from datetime import datetime
from beecell.simple import get_value, str2bool, AttribException
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedRequestQuerySchema,\
    PaginatedResponseSchema, ApiObjectResponseSchema, SwaggerApiView,\
    CreateApiObjectResponseSchema, GetApiObjectRequestSchema
from flasgger import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError
from beecell.swagger import SwaggerHelper
from flasgger.marshmallow_apispec import SwaggerView

class BaseCreateRequestSchema(Schema):
    name = fields.String(required=True,
                error_messages={u'required': u'name is required.'})
    desc = fields.String(required=True, 
                error_messages={u'required': u'desc is required.'})
    
class BaseUpdateRequestSchema(Schema):
    name = fields.String(context=u'body')
    desc = fields.String(context=u'body')    
    
class BaseCreateExtendedParamRequestSchema(Schema):
    active = fields.Boolean(missing=True)
    expiry_date = fields.String(load_from=u'expirydate', missing=None)
    
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
class ListDomains(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        List authentication domains
        Call this api to list authentication domains
        ---
        deprecated: false
        tags:
          - authorization
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
          200:
            description: Domains list
            schema:
              type: object
              required: [domains, count]
              properties:
                count:
                  type: integer
                  example: 2
                domains:
                  type: array
                  items:
                    type: object
                    required: [name, type]
                    properties:
                      name:
                        type: string
                        example: local
                      type:
                        type: string
                        example: DatabaseAuth 
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
class ListTokens(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        List authentication tokens
        Call this api to list authentication tokens
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
          200:
            description: Tokens list
            schema:
              type: object
              required: [tokens, count]
              properties:
                count:
                  type: integer
                  example: 1
                tokens:
                  type: array
                  items:
                    type: object
                    required: [ip, ttl, token, user, timestamp, type]
                    properties:
                      ip:
                        type: string
                        example: pc160234.csi.it
                      ttl:
                        type: integer
                        example: 3600
                      token:
                        type: string
                        example: 28ff1dd5-5520-42f3-a361-c58f19d20b7c
                      user:
                        type: string
                        example: admin@local
                      timestamp:
                        type: string
                        example: 19-23_14-07-2017
                      type:
                        type: string
                        example: keyauth
        """        
        identities = controller.get_identities()
        res = [{
            u'token':i[u'uid'],
            u'type':i[u'type'],
            u'user':i[u'user'][u'name'],
            u'timestamp':i[u'timestamp'].strftime(u'%H-%M_%d-%m-%Y'), 
            u'ttl':i[u'ttl'], 
            u'ip':i[u'ip']
        } for i in identities]
        resp = {u'tokens':res,
                u'count':len(res)}
        return resp

class GetToken(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get authentication token
        Call this api to get authentication token
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
          type: string
          format: uuid
          required: true
          description: Token id          
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
          200:
            description: Tokens list
            schema:
              type: object
              required: [token]
              properties:
                token:
                  type: object
                  required: [ip, ttl, token, user, timestamp, type]
                  properties:
                    ip:
                      type: string
                      example: pc160234.csi.it
                    ttl:
                      type: integer
                      example: 3600
                    token:
                      type: string
                      example: 28ff1dd5-5520-42f3-a361-c58f19d20b7c
                    user:
                      type: object
                      required: [name, roles, perms, active, id]
                      properties:
                        name:
                          type: string
                          example: admin@local
                        roles:
                          type: array
                          items:
                            type: string
                        perms:
                          type: string
                        active:
                          type: boolean
                          example: true
                        id:
                          type: string
                          example: 6d960236-d280-46d2-817d-f3ce8f0aeff7
                    timestamp:
                      type: string
                      example: 19-23_14-07-2017
                    type:
                      type: string
                      example: keyauth                         
        """                
        data = controller.get_identity(oid)
        res = {
            u'token':data[u'uid'],
            u'type':data[u'type'],
            u'user':data[u'user'],
            u'timestamp':data[u'timestamp'].strftime(u'%H-%M_%d-%m-%Y'), 
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

class DeleteToken(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete authentication token
        Call this api to delete an authentication token
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
          type: string
          format: uuid
          required: true
          description: Token id          
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
        resp = controller.remove_identity(oid)
        return (resp, 204)

#
# user
#
## list
class ListUsersRequestSchema(PaginatedRequestQuerySchema):
    group = fields.String(context=u'query')
    role = fields.String(context=u'query')
    active = fields.Boolean(context=u'query')
    expiry_date = fields.String(load_from=u'expirydate', default=u'2099-12-31',
                                context=u'query')

class ListUsersResponseSchema(PaginatedResponseSchema):
    users = fields.Nested(ApiObjectResponseSchema, many=True)

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

## get
class GetUserResponseSchema(Schema):
    user = fields.Nested(ApiObjectResponseSchema)

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
        res = obj.info()
        #res[u'perms'] = obj.get_permissions()
        #res[u'groups'] = obj.get_groups()
        #res[u'roles'] = obj.get_roles()        
        resp = {u'user':res} 
        return resp

## list attributes
class GetUserAtributesParamResponseSchema(Schema):
    name = fields.String(required=True, default=u'test')
    value = fields.String(required=True, default=u'test')
    desc = fields.String(required=True, default=u'test')

class GetUserAtributesResponseSchema(Schema):
    count = fields.Integer(required=True, defaut=0)
    user_attributes = fields.Nested(GetUserAtributesParamResponseSchema,
                                    many=True)

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
class CreateUserParamRequestSchema(BaseCreateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                          error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'),
                          missing=u'DBUSER')
    base = fields.Boolean(missing=False)
    system = fields.Boolean(missing=False)
    
    @validates(u'name')
    def validate_user(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'User name syntax must be <name>@<domain>') 

class CreateUserRequestSchema(Schema):
    user = fields.Nested(CreateUserParamRequestSchema, context=u'body')
    
class CreateUserBodyRequestSchema(Schema):
    body = fields.Nested(CreateUserRequestSchema, context=u'body')

class CreateUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateUserRequestSchema': CreateUserRequestSchema,
        u'CreateApiObjectResponseSchema':CreateApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateUserBodyRequestSchema)
    parameters_schema = CreateUserRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateApiObjectResponseSchema
        }
    })
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create a user
        Call this api to create a user               
        """
        resp = controller.add_user(**data.get(u'user'))
        return ({u'uuid':resp}, 201)

## update
class UpdateUserParamRoleRequestSchema(Schema):
    append = fields.List(fields.List(fields.String()))
    remove = fields.List(fields.String())
    
class UpdateUserParamRequestSchema(BaseUpdateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    roles = fields.Nested(UpdateUserParamRoleRequestSchema)
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    
    @validates(u'name')
    def validate_user(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'User name syntax must be <name>@<domain>')     

class UpdateUserRequestSchema(Schema):
    user = fields.Nested(UpdateUserParamRequestSchema)

class UpdateUserBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateUserRequestSchema, context=u'body')
    
class UpdateUserResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')
    role_append = fields.List(fields.String, dump_to=u'role_append')
    role_remove = fields.List(fields.String, dump_to=u'role_remove')
    
class UpdateUser(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'UpdateUserRequestSchema':UpdateUserRequestSchema,
        u'UpdateUserResponseSchema':UpdateUserResponseSchema
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
        user = controller.get_user(oid)
        
        resp = {u'update':None, u'role_append':[], u'role_remove':[]}
        
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
        
        # update user
        res = user.update(**data)
        resp[u'update'] = res
        return resp

## create attributes
class UserAttribSchemaCreateParam(Schema):
    name = fields.String(required=True)
    new_name = fields.String()
    value = fields.String(required=True)
    desc = fields.String(required=True)

class CreateUserAttributeRequestSchema(Schema):
    user_attribute = fields.Nested(UserAttribSchemaCreateParam,
                                   load_from=u'user-attribute')

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
## list
class ListRolesRequestSchema(PaginatedRequestQuerySchema):
    user = fields.String(context=u'query')
    group = fields.String(context=u'query')

class ListRolesResponseSchema(PaginatedResponseSchema):
    roles = fields.Nested(ApiObjectResponseSchema, many=True)

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
    role = fields.Nested(ApiObjectResponseSchema)

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
    role = fields.Nested(BaseCreateRequestSchema, context=u'body')
    
class CreateRoleBodyRequestSchema(Schema):
    body = fields.Nested(CreateRoleRequestSchema, context=u'body')

class CreateRole(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateRoleRequestSchema': CreateRoleRequestSchema,
        u'CreateApiObjectResponseSchema':CreateApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateRoleBodyRequestSchema)
    parameters_schema = CreateRoleRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateApiObjectResponseSchema
        }
    })

    def post(self, controller, data, *args, **kwargs):
        """
        Create role
        Call this api to create a role
        """
        resp = controller.add_role(**data.get(u'role'))
        return ({u'uuid':resp}, 201)

## update
class UpdateRoleParamPermDescRequestSchema(Schema):
    type = fields.String()
    subsystem = fields.String()
    objid = fields.String()
    action = fields.String()
    id = fields.Integer()

class UpdateRoleParamPermRequestSchema(Schema):
    append = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True)
    remove = fields.Nested(UpdateRoleParamPermDescRequestSchema, many=True)
    
class UpdateRoleParamRequestSchema(BaseUpdateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    perms = fields.Nested(UpdateRoleParamPermRequestSchema) 

class UpdateRoleRequestSchema(Schema):
    role = fields.Nested(UpdateRoleParamRequestSchema)

class UpdateRoleBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateRoleRequestSchema, context=u'body')
    
class UpdateRoleResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')
    perm_append = fields.List(fields.String, dump_to=u'perm_append')
    perm_remove = fields.List(fields.String, dump_to=u'perm_remove')
    
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
        
        resp = {u'update':None, u'perm_append':[], u'perm_remove':[]}
        
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

## delete
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
    expiry_date = fields.String(load_from=u'expirydate', default=u'2099-12-31',
                                context=u'query')

class ListGroupsResponseSchema(PaginatedResponseSchema):
    groups = fields.Nested(ApiObjectResponseSchema, many=True)

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
    group = fields.Nested(ApiObjectResponseSchema)

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
class CreateGroupParamRequestSchema(BaseCreateRequestSchema, 
                                    BaseCreateExtendedParamRequestSchema):
    pass

class CreateGroupRequestSchema(Schema):
    group = fields.Nested(CreateGroupParamRequestSchema, context=u'body')
    
class CreateGroupBodyRequestSchema(Schema):
    body = fields.Nested(CreateGroupRequestSchema, context=u'body')

class CreateGroup(SwaggerApiView):
    tags = [u'authorization']
    definitions = {
        u'CreateGroupRequestSchema': CreateGroupRequestSchema,
        u'CreateApiObjectResponseSchema':CreateApiObjectResponseSchema
    }
    parameters = SwaggerHelper().get_parameters(CreateGroupBodyRequestSchema)
    parameters_schema = CreateGroupRequestSchema
    responses = SwaggerApiView.setResponses({
        201: {
            u'description': u'success',
            u'schema': CreateApiObjectResponseSchema
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
    
class UpdateGroupParamRequestSchema(BaseUpdateRequestSchema, 
                                   BaseCreateExtendedParamRequestSchema):
    roles = fields.Nested(UpdateGroupParamRoleRequestSchema)
    users = fields.Nested(UpdateGroupParamRoleRequestSchema) 

class UpdateGroupRequestSchema(Schema):
    group = fields.Nested(UpdateGroupParamRequestSchema)

class UpdateGroupBodyRequestSchema(GetApiObjectRequestSchema):
    body = fields.Nested(UpdateGroupRequestSchema, context=u'body')
    
class UpdateGroupResponseSchema(Schema):
    update = fields.String(default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')
    role_append = fields.List(fields.String, dump_to=u'role_append')
    role_remove = fields.List(fields.String, dump_to=u'role_remove')
    user_append = fields.List(fields.String, dump_to=u'user_append')
    user_remove = fields.List(fields.String, dump_to=u'user_remove')    
    
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
class ObjectQuerySchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id', 
                          u'objid', u'aid', u'action'],
                          error=u'Field can be subsystem, type, id, objid, aid, action'),
                          missing=u'id')    
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()

class ListObjects(ApiView):
    parameters_schema = ObjectQuerySchema
    
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
          - name: objid
            in: query
            required: false
            description: Filter object by objid
            type: boolean
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
              required: [objects, count, page, total, sort]
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
                objects:
                  type: array
                  items:
                    type: object
                    required: [id, uuid, objid, type, subsystem, desc, active, date]
                    properties:
                      id:
                        type: integer
                        example: 1
                      uuid:
                        type: string
                        example: 4cdf0ea4-159a-45aa-96f2-708e461130e1                        
                      objid:
                        type: string
                        example: 396587362//3328462822
                      type:
                        type: string
                        example: Objects
                      subsystem:
                        type: string
                        example: auth
                      desc:
                        type: string
                        example: beehive                   
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z         
        """        
        
        '''objtype = request.args.get(u'subsystem', None)
        objdef = request.args.get(u'type', None)
        objid = request.args.get(u'objid', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef'
        '''   
        objid = data.get(u'objid', None)
        if objid is not None:
            data[u'objid'] = objid.replace(u'_', u'//')
        res, total = controller.objects.get_objects(**data)
        
        return self.format_paginated_response(res, u'objects', total, **data)

class GetObject(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get object
        Call this api to get a object
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
          type: string
          required: true
          description: object id          
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
          200:
            description: success
            schema:
              type: object
              required: [object]
              properties:      
                object:
                    type: object
                    required: [id, uuid, objid, type, subsystem, desc, active, date]
                    properties:
                      id:
                        type: integer
                        example: 1
                      uuid:
                        type: string
                        example: 4cdf0ea4-159a-45aa-96f2-708e461130e1                        
                      objid:
                        type: string
                        example: 396587362//3328462822
                      type:
                        type: string
                        example: Objects
                      subsystem:
                        type: string
                        example: auth
                      desc:
                        type: string
                        example: beehive                    
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
        """                        
        obj = controller.objects.get_object(oid)
        res = obj
        resp = {u'object':res} 
        return resp

class ObjectSchemaCreateParam(Schema):
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()
    desc = fields.String()

class ObjectSchemaCreate(Schema):
    objects = fields.Nested(ObjectSchemaCreateParam, many=True)

class CreateObject(ApiView):
    parameters_schema = ObjectSchemaCreate

    def post(self, controller, data, *args, **kwargs):
        """
        Create object
        Call this api to create a object
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
              required: [objects]
              properties:
                objects:
                  type: array
                  items:
                    type: object
                    required: [subsystem, type, objid, desc]
                    properties:
                      subsystem:
                        type: string
                        example: auth
                      type:
                        type: string
                        example: Objects
                      objid:
                        type: string
                        example: 1273dud79w2
                      desc:
                        type: string
                        example: test
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
              required: [id]
              properties:
                id:            
                  type: integer
                  example: 45
        """        
        #data = get_value(data, u'objects', None, exception=True)
        resp = controller.objects.add_objects(data.get(u'objects'))
        return ({u'id':resp}, 201)

class DeleteObject(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete object
        Call this api to delete a object
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
          type: string
          required: true
          description: object id          
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
        return self.format_paginated_response(res, u'object-types', total, **data)

class ObjectTypeSchemaCreateParam(Schema):
    subsystem = fields.String()
    type = fields.String()

class ObjectTypeSchemaCreate(Schema):
    object_types = fields.Nested(ObjectTypeSchemaCreateParam, many=True, 
                                 load_from=u'object-types')

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
                object-types:
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
              required: [object-actions, count]
              properties:
                count:
                  type: integer
                  example: 1     
                object-actions:
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
        resp = {u'object-actions':res,
                u'count':len(res)} 
        return resp    

#
# object perms
#
class PermQuerySchema(PaginatedRequestQuerySchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id', 
                          u'objid', u'aid', u'action'],
                          error=u'Field can be subsystem, type, id, objid, aid, action'),
                          missing=u'id')      
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()
    user = fields.String()
    role = fields.String()
    group = fields.String()

class ListObjectPerms(ApiView):
    parameters_schema = PermQuerySchema    
    
    def get(self, controller, data, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions
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
          - name: objid
            in: query
            required: false
            description: Filter object by objid
            type: string
          - name: role
            in: query
            required: false
            description: Filter object by role
            type: string
          - name: user
            in: query
            required: false
            description: Filter object by user
            type: string
          - name: group
            in: query
            required: false
            description: Filter object by group
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
              required: [perms, count, page, total, sort]
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
                perms:
                  type: array
                  items:
                    type: object
                    required: [id, oid, objid, type, subsystem, desc, aid, action]
                    properties:
                      id:
                        type: integer
                        example: 1
                      oid:
                        type: integer
                        example: 3                  
                      objid:
                        type: string
                        example: 396587362//3328462822
                      type:
                        type: string
                        example: Objects
                      subsystem:
                        type: string
                        example: auth
                      desc:
                        type: string
                        example: beehive
                      aid:
                        type: integer
                        example: 1
                      action:
                        type: string
                        example: view                 
        """
        '''  
        objtype = request.args.get(u'subsystem', None)
        objdef = request.args.get(u'type', None)
        objid = request.args.get(u'objid', None)
        user = request.args.get(u'user', None)
        role = request.args.get(u'role', None)
        group = request.args.get(u'group', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
        '''
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

class GetObjectPerms(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        List object permissions
        Call this api to list object permissions
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
          type: string
          required: true
          description: object permission id           
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
              required: [perm]
              properties:   
                perm:
                    type: object
                    required: [id, oid, objid, type, subsystem, desc, aid, action]
                    properties:
                      id:
                        type: integer
                        example: 1
                      oid:
                        type: integer
                        example: 3                  
                      objid:
                        type: string
                        example: 396587362//3328462822
                      type:
                        type: string
                        example: Objects
                      subsystem:
                        type: string
                        example: auth
                      desc:
                        type: string
                        example: beehive
                      aid:
                        type: integer
                        example: 1
                      action:
                        type: string
                        example: view                 
        """        
        res = controller.objects.get_permission(oid)
        resp = {u'perm':res}
        return resp

class AuthorizationAPI(ApiView):
    """Authorization API
    """
    @staticmethod
    def register_api(module):
        base = u'auth'
        rules = [
            (u'%s/domains' % base, u'GET', ListDomains, {u'secure':False}),
            
            (u'%s/tokens' % base, u'GET', ListTokens, {}),
            (u'%s/tokens/<oid>' % base, u'GET', GetToken, {}),
            #(u'%s/tokens/<oid>/refresh' % base, u'PUT', TokenRefresh, {}),
            (u'%s/tokens/<oid>' % base, u'DELETE', DeleteToken, {}),
            #(u'%s/tokens/<oid>/exist' % base, u'GET', LoginExists, {}),
            
            (u'%s/users' % base, u'GET', ListUsers, {}),
            (u'%s/users/<oid>' % base, u'GET', GetUser, {}),
            (u'%s/users/<oid>/attributes' % base, u'GET', GetUserAtributes, {}),
            (u'%s/users' % base, u'POST', CreateUser, {}),
            (u'%s/users/<oid>' % base, u'PUT', UpdateUser, {}),
            (u'%s/users/<oid>/attributes' % base, u'POST', CreateUserAttribute, {}),
            (u'%s/users/<oid>/attributes/<aid>' % base, u'DELETE', DeleteUserAttribute, {}),
            (u'%s/users/<oid>' % base, u'DELETE', DeleteUser, {}),
            
            (u'%s/roles' % base, u'GET', ListRoles, {}),
            (u'%s/roles/<oid>' % base, u'GET', GetRole, {}),
            (u'%s/roles' % base, u'POST', CreateRole, {}),
            (u'%s/roles/<oid>' % base, u'PUT', UpdateRole, {}),
            (u'%s/roles/<oid>' % base, u'DELETE', DeleteRole, {}),
            
            (u'%s/groups' % base, u'GET', ListGroups, {}),
            (u'%s/groups/<oid>' % base, u'GET', GetGroup, {}),
            (u'%s/groups' % base, u'POST', CreateGroup, {}),
            (u'%s/groups/<oid>' % base, u'PUT', UpdateGroup, {}),
            (u'%s/groups/<oid>' % base, u'DELETE', DeleteGroup, {}),             
         
            (u'%s/objects' % base, u'GET', ListObjects, {}),
            (u'%s/objects/<oid>' % base, u'GET', GetObject, {}),
            (u'%s/objects' % base, u'POST', CreateObject, {}),
            (u'%s/objects/<oid>' % base, u'DELETE', DeleteObject, {}),
            (u'%s/objects/types' % base, u'GET', ListObjectTypes, {}),
            (u'%s/objects/types' % base, u'POST', CreateObjectType, {}),
            (u'%s/objects/types/<oid>' % base, u'DELETE', DeleteObjectType, {}),            
            (u'%s/objects/perms' % base, u'GET', ListObjectPerms, {}),
            (u'%s/objects/perms/<oid>' % base, u'GET', GetObjectPerms, {}),
            (u'%s/objects/actions' % base, u'GET', ListObjectActions, {}),
        ]

        ApiView.register_api(module, rules)
        