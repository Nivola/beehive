"""
Created on Jan 12, 2017

@author: darkbk
"""
from flask import request
from beecell.simple import get_value, str2bool, get_remote_ip
from beehive.common.apimanager import ApiView, ApiManagerError
from beehive.common.data import operation

#
# token
#
class CreateToken(ApiView):
    def post(self, controller, data, *args, **kwargs):
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
          - in : body
            name: body
            schema:
              type: object
              required: [user, password]
              properties:
                user:
                  type: string
                password:
                  type: string
                login-ip:
                  type: string      
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
              required: [access_token, expires_in, expires_at, token_type, seckey, pubkey, user]
              properties:
                access_token:
                  type: string
                  example: 39cdae88-74a7-466b-9817-ced52c90239c
                expires_in:
                  type: integer
                  example: 3600
                expires_at:
                  type: integer
                  example: 1502739783
                token_type:
                  type: string
                  example: Bearer
                seckey:
                  type: string
                  example: LS0tLS1CRUdJTiBSU0Eg........
                pubkey:
                  type: string
                  example: LS0tLS1CRUdJTiBQVUJMSUMgS0VZL..........
                user:
                  type: string
                  example: 6d960236-d280-46d2-817d-f3ce8f0aeff7
        """        
        user = get_value(data, u'user', None, exception=True)
        password = get_value(data, u'password', None, exception=True)
        login_ip = get_value(data, u'login-ip', get_remote_ip(request))
        
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
        res = controller.login(name, domain, password, login_ip)
        resp = res       
        return resp
    
class KeyAuthApi(ApiView):
    """Asymmetric key authentication API
    """
    @staticmethod
    def register_api(module):
        base = u'keyauth'
        rules = [
            (u'%s/token' % base, u'POST', CreateToken, {u'secure':False}),
        ]
        
        ApiView.register_api(module, rules)