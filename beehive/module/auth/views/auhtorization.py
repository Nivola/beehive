"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from datetime import datetime
from beecell.simple import get_value, str2bool, AttribException
from beehive.common.apimanager import ApiView, ApiManagerError, PaginatedSchema
from marshmallow import fields, Schema
from marshmallow.validate import OneOf, Range, Length
from marshmallow.decorators import post_load, validates
from marshmallow.exceptions import ValidationError

class BaseSchemaCreateParam(Schema):
    name = fields.String(required=True,
                error_messages={u'required': u'name is required.'})
    desc = fields.String(required=True, 
                error_messages={u'required': u'desc is required.'})
    
class BaseSchemaUpdateParam(Schema):
    name = fields.String()
    desc = fields.String()    
    
class BaseSchemaExtendedParam(Schema):
    active = fields.Boolean(missing=True)
    expiry_date = fields.String(load_from=u'expiry-date', missing=None)
    
    @post_load
    def make_expiry_date(self, data):
        expiry_date = data.get(u'expiry_date', None)
        if expiry_date is not None:
            #expiry_date = expiry_date.replace(u'T', u'')
            y, m, d = expiry_date.split(u'-')
            expiry_date = datetime(int(y), int(m), int(d))
            data[u'expiry_date'] = expiry_date
        return data

class BaseSchemaUpdateParamMulti(Schema):
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
class UserQuerySchema(PaginatedSchema):
    group = fields.String()
    role = fields.String()
    active = fields.Boolean()
    expiry_date = fields.String(load_from=u'expiry-date')

class ListUsers(ApiView):
    query_schema = UserQuerySchema
    
    def get(self, controller, data, *args, **kwargs):
        """
        List users
        Call this api to list users
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
          - name: group
            in: query
            required: false
            description: Filter user by group
            type: string
          - name: role
            in: query
            required: false
            description: Filter user by role
            type: string
          - name: active
            in: query
            required: false
            description: Filter user by status
            type: boolean
          - name: expiry-date
            in: query
            required: false
            description: Filter user with expiry-date >= 
            type: string
            format: date
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
              required: [users, count, page, total, sort]
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
                users:
                  type: array
                  items:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: User                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/users                        
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified, expiry]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                          
                          expiry:              
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                        
        """
        objs, total = controller.get_users(**data)
        res = [r.info() for r in objs]

        return self.format_paginated_response(res, u'users', total, **data)

class GetUser(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get user
        Call this api to get user by id, uuid or name
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
            required: true
            type: string
            description: The user id          
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
              required: [user]
              properties:
                user:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: User                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/users                        
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified, expiry]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                          
                          expiry:              
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
        """        
        obj = controller.get_user(oid)
        res = obj.info()
        #res[u'perms'] = obj.get_permissions()
        #res[u'groups'] = obj.get_groups()
        #res[u'roles'] = obj.get_roles()        
        resp = {u'user':res} 
        return resp

class GetUserAtributes(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get user
        Call this api to get user by id, uuid or name
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
            required: true
            type: string
            description: The user id          
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
              required: [user-attributes]
              properties:
                count:
                  type: integer
                  example: 2
                user-attributes:
                  type: array
                  items:
                    type: object
                    required: [name, value, desc]
                    properties:
                      name:
                        type: string
                        example: test
                      value:
                        type: string
                        example: test
                      desc:
                        type: string
                        example: test
        """
        user = controller.get_user(oid)
        res = user.get_attribs()
        resp = {u'user-attributes':res,
                u'count':len(res)} 
        return resp

class UserSchemaCreateParam(BaseSchemaCreateParam, BaseSchemaExtendedParam):
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                          error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'),
                          missing=u'DBUSER')
    base = fields.Boolean(missing=True)
    system = fields.Boolean()
    
    @validates(u'name')
    def validate_user(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'User name syntax must be <name>@<domain>') 

class UserSchemaCreate(Schema):
    user = fields.Nested(UserSchemaCreateParam)

class CreateUser(ApiView):
    input_schema = UserSchemaCreate
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create a user
        Call this api to create a user
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
              required: [user]
              properties:
                user:
                  type: object
                  required: [name, desc]
                  properties:
                    name:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    active:
                      type: boolean
                      example: true
                    expiry-date:
                      type: string
                      format: date
                      example: 1990-12-31  
                    password:
                      type: string
                      example: xxxxxx
                    storetype:
                      type: string
                      enum: [DBUSER, LDAPUSER', SPID]
                      example: DBUSER
                    base:
                      type: boolean
                      example: true
                    system:
                      type: boolean
                      example: false
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
          201:
            description: success
            schema:
              type: object
              required: [uuid]
              properties:
                uuid:
                  type: string
                  example: 6d960236-d280-46d2-817d-f3ce8f0aeff7                 
        """
        resp = controller.add_user(**data.get(u'user'))
        return ({u'uuid':resp}, 201)
    
class UserSchemaUpdateParam(BaseSchemaUpdateParam, BaseSchemaExtendedParam):
    roles = fields.Nested(BaseSchemaUpdateParamMulti)
    password = fields.String(validate=Length(min=10, max=20),
                             error=u'Password must be at least 8 characters')
    
    @validates(u'name')
    def validate_user(self, value):
        if not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', value):
            raise ValidationError(u'User name syntax must be <name>@<domain>')     

class UserSchemaUpdate(Schema):
    user = fields.Nested(UserSchemaUpdateParam)
    
class UpdateUser(ApiView):
    input_schema = UserSchemaUpdate    

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update user
        Call this api to update a user
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
            description: user id          
          - in : body
            name: body
            schema:
              type: object
              required: [user]
              properties:
                user:
                  type: object
                  required: []
                  properties:
                    name:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    active:
                      type: boolean
                      example: true
                    expiry-date:
                      type: string
                      format: date
                      example: 1990-12-31T
                    password:
                      type: string
                      example: xxxxxx                     
                    roles:
                      type: object
                      required: []
                      properties:
                        append:
                          type: array
                          items:
                            type: string
                            example: Guest
                        remove:  
                          type: array
                          items:
                            type: string
                            example: Guest        
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
              required: [update, role-append, role-remove]
              properties:
                update:            
                  type: integer
                  example: 67
                role-append:
                  type: array
                  items:
                    type: integer
                    example: 18             
                role-remove:
                  type: array
                  items:
                    type: integer
                    example: 18
        """
        data = data.get(u'user')
        role = data.pop(u'roles', None)
        user = controller.get_user(oid)
        
        resp = {u'update':None, u'role-append':[], u'role-remove':[]}
        
        # append, remove role
        if role is not None:
            # append role
            if u'append' in role:
                for role, expiry in role.get(u'append'):
                    res = user.append_role(role, expiry_date=expiry)
                    resp[u'role-append'].append(res)
        
            # remove role
            if u'remove' in role:
                for role in role.get(u'remove'):
                    res = user.remove_role(role)
                    resp[u'role-remove'].append(res)
        
        # update user
        res = user.update(**data)
        resp[u'update'] = res
        return resp

class UserAttribSchemaCreateParam(Schema):
    name = fields.String(required=True)
    new_name = fields.String()
    value = fields.String(required=True)
    desc = fields.String(required=True)

class UserAttribSchemaCreate(Schema):
    user_attribute = fields.Nested(UserAttribSchemaCreateParam,
                                   load_from=u'user-attribute')

class CreateUserAttribute(ApiView):
    input_schema = UserAttribSchemaCreate

    def post(self, controller, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user
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
          description: user id          
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
          201:
            description: success
            schema:
              type: object
              required: [user-attribute]
              properties:
                user-attribute:
                  type: object
                  required: [name, value, desc]
                  properties:
                    name:
                      type: string
                      example: test
                    value:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    new_name:
                      type: string
                      example: new_test
        """
        user = controller.get_user(oid)
        attr = user.set_attribute(**data.get(u'user_attribute'))
        resp = {u'name':attr.name, u'value':attr.value, u'desc':attr.desc}
        return (resp, 201)

class DeleteUserAttribute(ApiView):
    def delete(self, controller, data, oid, aid, *args, **kwargs):
        """
        Delete user attribute
        Call this api to delete a user attribute
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
          description: user id
        - in: path
          name: aid
          type: string
          required: true
          description: attribute id
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
        user = controller.get_user(oid)
        resp = user.remove_attribute(aid)
        return (resp, 204)

class DeleteUser(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete user
        Call this api to delete a user
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
          description: user id          
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
        user = controller.get_user(oid)
        resp = user.delete()
        return (resp, 204)

#
# role
#
class RoleQuerySchema(PaginatedSchema):
    group = fields.String()
    user = fields.String()

class ListRoles(ApiView):
    query_schema = RoleQuerySchema
    
    def get(self, controller, data, *args, **kwargs):
        """
        List roles
        Call this api to list roles
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
          - name: user
            in: query
            required: false
            description: Filter role by user
            type: string
          - name: group
            in: query
            required: false
            description: Filter role by role
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
              required: [roles, count, page, total, sort]
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
                roles:
                  type: array
                  items:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: role                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/roles                        
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
                          expiry:              
                            type: string
                            example: 1990-12-31T23:59:59Z
        """      
        objs, total = controller.get_roles(**data)
        
        res = [r.info() for r in objs]
        return self.format_paginated_response(res, u'roles', total, **data)

class GetRole(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get role
        Call this api to get a role
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
          description: role id          
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
              required: [role]
              properties:      
                role:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: role                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/roles                        
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
                          expiry:
                            type: string
                            example: 1990-12-31T23:59:59Z 
        """             
        obj = controller.get_role(oid)
        res = obj.info()      
        resp = {u'role':res} 
        return resp

class RoleSchemaCreateParam(BaseSchemaCreateParam):
    pass

class RoleSchemaCreate(Schema):
    role = fields.Nested(RoleSchemaCreateParam)

class CreateRole(ApiView):
    input_schema = RoleSchemaCreate

    def post(self, controller, data, *args, **kwargs):
        """
        Create role
        Call this api to create a role
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
              required: [role]
              properties:
                role:
                  type: object
                  required: [name, desc]
                  properties:
                    name:
                      type: string
                      example: test
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
              required: [uuid]
              properties:
                uuid:            
                  type: string
                  format: uuid
                  example: 6d960236-d280-46d2-817d-f3ce8f0aeff7
        """
        resp = controller.add_role(**data.get(u'role'))
        return ({u'uuid':resp}, 201)

class RoleSchemaUpdateParamMulti(Schema):
    append = fields.List(fields.Integer())
    remove = fields.List(fields.Integer())
    
class RoleSchemaUpdateParam(BaseSchemaUpdateParam):
    perms = fields.Nested(RoleSchemaUpdateParamMulti)

class RoleSchemaUpdate(Schema):
    role = fields.Nested(RoleSchemaUpdateParam)    
    
class UpdateRole(ApiView):
    input_schema = RoleSchemaUpdate

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update role
        Call this api to update a role
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
            description: role id          
          - in : body
            name: body
            schema:
              type: object
              required: [role]
              properties:
                role:
                  type: object
                  required: []
                  properties:
                    name:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    perms:
                      type: object
                      required: []
                      properties:
                        append:
                          type: array
                          items:
                            type: integer
                            example: 2
                        remove:  
                          type: array
                          items:
                            type: integer
                            example: 2             
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
              required: [update, perm-append, perm-remove]
              properties:
                update:            
                  type: integer
                  example: 67
                perm-append:
                  type: array
                  items:
                    type: integer
                    example: 18             
                perm-remove:
                  type: array
                  items:
                    type: integer
                    example: 18  
        """
        data = data.get(u'role')
        role_perm = data.pop(u'perms', None)
        role = controller.get_role(oid)
        
        resp = {u'update':None, u'perm-append':[], u'perm-remove':[]}
        
        # append, remove role
        if role_perm is not None:
            # append role
            if u'append' in role_perm:
                perms = []
                for perm in role_perm.get(u'append'):
                    perms.append(perm)
                res = role.append_permissions(perms)
                resp[u'perm-append'] = res
        
            # remove role
            if u'remove' in role_perm:
                perms = []
                for perm in role_perm.get(u'remove'):
                    perms.append(perm)
                res = role.remove_permissions(perms)
                resp[u'perm-remove'] = res
        
        # update role
        res = role.update(**data)        
        resp[u'update'] = res
        return resp

class DeleteRole(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete role
        Call this api to delete a role
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
          description: role id          
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
        role = controller.get_role(oid)
        resp = role.delete()
        return (resp, 204)

#
# group
#
class GroupQuerySchema(PaginatedSchema):
    user = fields.String()
    role = fields.String()
    active = fields.Boolean()
    expiry_date = fields.String(load_from=u'expiry-date')

class ListGroups(ApiView):
    query_schema = GroupQuerySchema
    
    def get(self, controller, data, *args, **kwargs):
        """
        List groups
        Call this api to list groups
        ---
        deprecated: false
        tags:
          - authorization
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        parameters:
          - name: user
            in: query
            required: false
            description: Filter group by user
            type: string
          - name: role
            in: query
            required: false
            description: Filter group by role
            type: string
          - name: active
            in: query
            required: false
            description: Filter group by status
            type: boolean
          - name: expiry-date
            in: query
            required: false
            description: Filter group with expiry-date >= 
            type: string
            format: date
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
              required: [groups, count, page, total, sort]
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
                groups:
                  type: array
                  items:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: group                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/groups                        
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified, expiry]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                          
                          expiry:              
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                        
        """
        objs, total = controller.get_groups(**data)
        
        res = [r.info() for r in objs]  
        return self.format_paginated_response(res, u'groups', total, **data)

class GetGroup(ApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        """
        Get group
        Call this api to get a group
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
          description: Group id          
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
              required: [group]
              properties:      
                group:
                    type: object
                    required: [id, uuid, objid, type, definition, name, desc, uri, active, date]
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
                        example: auth
                      definition:
                        type: string
                        example: group                        
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      uri:
                        type: string
                        example: /v1.0/auth/groups                        
                      active:
                        type: boolean
                        example: true
                      date:
                        type: object
                        required: [creation, modified, expiry]
                        properties:
                          creation:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z
                          modified:
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z                          
                          expiry:              
                            type: string
                            format: date-time
                            example: 1990-12-31T23:59:59Z   
        """                
        obj = controller.get_group(oid)
        res = obj.info()      
        resp = {u'group':res} 
        return resp

class GroupSchemaCreateParam(BaseSchemaCreateParam, BaseSchemaExtendedParam):
    pass

class GroupSchemaCreate(Schema):
    group = fields.Nested(GroupSchemaCreateParam)

class CreateGroup(ApiView):
    input_schema = GroupSchemaCreate
    
    def post(self, controller, data, *args, **kwargs):
        """
        Create group
        Call this api to create a group
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
              required: [group]
              properties:
                group:
                  type: object
                  required: [name, desc]
                  properties:
                    name:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    active:
                      type: boolean
                      example: true
                    expiry-date:
                      type: string
                      format: date
                      example: 1990-12-31T
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
              required: [uuid]
              properties:
                uuid:            
                  type: string
                  format: uuid
                  example: 6d960236-d280-46d2-817d-f3ce8f0aeff7
        """
        '''
        data = get_value(data, u'group', None, exception=True)
        groupname = get_value(data, u'name', None, exception=True)
        description = get_value(data, u'desc', u'Group %s' % groupname)
        active = get_value(data, u'active', True)
        active = str2bool(active)
        expiry_date = get_value(data, u'expiry-date', None)    '''    
                       
        resp = controller.add_group(**data.get(u'group'))
        return ({u'uuid':resp}, 201)   

class GroupSchemaUpdateParam(BaseSchemaUpdateParam, BaseSchemaExtendedParam):
    roles = fields.Nested(BaseSchemaUpdateParamMulti)
    users = fields.Nested(BaseSchemaUpdateParamMulti)

class GroupSchemaUpdate(Schema):
    group = fields.Nested(GroupSchemaUpdateParam)    

class UpdateGroup(ApiView):
    input_schema = GroupSchemaUpdate

    def put(self, controller, data, oid, *args, **kwargs):
        """
        Update group
        Call this api to update a group
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
            description: Group id          
          - in : body
            name: body
            schema:
              type: object
              required: [group]
              properties:
                group:
                  type: object
                  required: []
                  properties:
                    name:
                      type: string
                      example: test
                    desc:
                      type: string
                      example: test
                    active:
                      type: boolean
                      example: true
                    expiry-date:
                      type: string
                      format: date
                      example: 1990-12-31T
                    roles:
                      type: object
                      required: []
                      properties:
                        append:
                          type: array
                          items:
                            type: string
                            example: Guest
                        remove:  
                          type: array
                          items:
                            type: string
                            example: Guest
                    users:
                      type: object
                      required: []
                      properties:
                        append:
                          type: array
                          items:
                            type: string
                            example: admin@local
                        remove:  
                          type: array
                          items:
                            type: string
                            example: admin@local                 
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
              required: [update, role-append, role-remove, user-append, user-remove]
              properties:
                update:            
                  type: integer
                  example: 67
                role-append:
                  type: array
                  items:
                    type: integer
                    example: 18             
                role-remove:
                  type: array
                  items:
                    type: integer
                    example: 18  
                user-append:
                  type: array
                  items:
                    type: integer
                    example: 18
                user-remove:
                  type: array
                  items:
                    type: integer
                    example: 18
        """        
        data = data.get(u'group')
        group_role = data.pop(u'roles', None)
        group_user = data.pop(u'users', None)
        
        group = controller.get_group(oid)
        
        resp = {u'update':None,
                u'role-append':[], u'role-remove':[], 
                u'user-append':[], u'user-remove':[]}
        
        # append, remove role
        if group_role is not None:
            # append role
            if u'append' in group_role:
                for role in group_role.get(u'append'):
                    res = group.append_role(role)
                    resp[u'role-append'].append(res)
        
            # remove role
            if u'remove' in group_role:
                for role in group_role.get(u'remove'):
                    res = group.remove_role(role)
                    resp[u'role-remove'].append(res)
                    
        # append, remove user
        if group_user is not None:
            # append user
            if u'append' in group_user:
                for user in group_user.get(u'append'):
                    res = group.append_user(user)
                    resp[u'user-append'].append(res)
        
            # remove user
            if u'remove' in group_user:
                for user in group_user.get(u'remove'):
                    res = group.remove_user(user)
                    resp[u'user-remove'].append(res)                    
        
        # update group
        res = group.update(**data)        
        resp[u'update'] = res
        return resp

class DeleteGroup(ApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        """
        Delete group
        Call this api to delete a group
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
          description: Group id          
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
        group = controller.get_group(oid)
        resp = group.delete()
        return (resp, 204)
    
#
# object
#
class ObjectQuerySchema(PaginatedSchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id', 
                          u'objid', u'aid', u'action'],
                          error=u'Field can be subsystem, type, id, objid, aid, action'),
                          missing=u'id')    
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()

class ListObjects(ApiView):
    query_schema = ObjectQuerySchema
    
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
    input_schema = ObjectSchemaCreate

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
class TypeQuerySchema(PaginatedSchema):
    field = fields.String(validate=OneOf([u'subsystem', u'type', u'id'],
                          error=u'Field can be subsystem, type, id'),
                          missing=u'id')    
    subsystem = fields.String()
    type = fields.String()
    objid = fields.String()

class ListObjectTypes(ApiView):
    query_schema = TypeQuerySchema
    
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
    input_schema = ObjectTypeSchemaCreate

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
class PermQuerySchema(PaginatedSchema):
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
    query_schema = PermQuerySchema    
    
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
        