'''
Created on Oct 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match

logger = logging.getLogger(__name__)


class Oauth2Controller(BaseController):
    class Meta:
        label = 'oauth2'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Oauth2 Authorization management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
    #
    # sessions
    #
    '''
    def get_sessions(self):
        uri = u'/v1.0/server/sessions'
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get sessions: %s' % res)
        res = [{u'id':truncate(i[u'sid']),
                u'ttl':i[u'ttl'],
                u'oauth2_credentials':i[u'oauth2_credentials'],
                u'oauth2_user':i[u'oauth2_user']}
               for i in res[u'sessions']]
        self.result(res, headers=
                    [u'id', u'ttl', u'oauth2_credentials.scope', 
                     u'oauth2_credentials.state', 
                     u'oauth2_credentials.redirect_uri',
                     u'oauth2_credentials.client_id',
                     u'oauth2_user.name',])
                     
    #
    # simplehttp login
    #
    def simplehttp_login_domains(self):
        uri = u'%s/login/domains' % (self.simplehttp_uri)
        res = self._call(uri, u'GET')
        logger.info(u'Get domains: %s' % res)
        domains = []
        for item in res[u'domains']:
            domains.append({u'domain':item[0],
                            u'type':item[1]})
        self.result(domains, headers=[u'domain', u'type'])
        
    def simplehttp_login_user(self, user, pwd, ip):
        data = {u'user':user, u'password':pwd, u'login-ip':ip}
        uri = u'%s/login' % (self.simplehttp_uri)
        res = self.client.send_signed_request(
                u'auth', uri, u'POST', data=json.dumps(data))
        res = res[u'response']
        logger.info(u'Login user %s: %s' % (user, res))
        self.result(res, headers=[u'user.id', u'uid', u'user.name', u'timestamp',
                                  u'user.active'])
    '''


class Oauth2ControllerChild(ApiController):
    baseuri = u'/v1.0/keyauth'
    simplehttp_uri = u'/v1.0/simplehttp'
    authuri = u'/v1.0/oauth2'
    subsystem = u'auth'
    
    obj_headers = [u'id', u'objid', u'subsystem', u'type', u'desc']
    type_headers = [u'id', u'subsystem', u'type']
    act_headers = [u'id', u'value']
    perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', 
                         u'aid', u'action']
    user_headers = [u'id', u'uuid', u'name', u'active', 
                         u'date.creation', u'date.modified', u'date.expiry']
    role_headers = [u'id', u'uuid', u'name', u'active', 
                         u'date.creation', u'date.modified', u'date.expiry']
    group_headers = [u'id', u'uuid', u'name', u'active', 
                          u'date.creation', u'date.modified', u'date.expiry']    
    token_headers = [u'token', u'type', u'user', u'ip', u'ttl', u'timestamp']
    
    class Meta:
        stacked_on = 'oauth2'
        stacked_type = 'nested'   


class Oauth2SessionController(Oauth2ControllerChild):
    session_headers = [u'sid', u'ttl', u'oauth2_user', u'oauth2_credentials']

    class Meta:
        label = 'user-sessions'
        description = "User Session management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all sessions
    field: valid, client, user 
        """
        # data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/user_sessions' % self.authuri        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'user_sessions', 
                    headers=self.session_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get session by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/user_sessions/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'user_session', headers=self.session_headers, 
                    details=True)
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete session by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/user_sessions/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete user session %s' % value}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'deletes <id1,id2,..>'], aliases_only=True)
    @check_error
    def deletes(self):
        """Delete sessions by list of id
        """
        value = self.get_arg(name=u'ids')
        for item in value.split(u','):
            uri = u'%s/user_sessions/%s' % (self.authuri, item)
            res = self._call(uri, u'DELETE')
            logger.info(res)
        res = {u'msg':u'Delete user session %s' % value}
        self.result(res, headers=[u'msg'])        


class AuthorizationCodeController(Oauth2ControllerChild):
    authorization_code_headers = [u'id', u'code', u'expires_at', u'client', 
                                  u'user', u'scope', u'expired']

    class Meta:
        label = 'authorization_codes'
        description = "AuthorizationCode management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all authorization_codes
    field: valid, client, user 
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/authorization_codes' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'authorization_codes', 
                    headers=self.authorization_code_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get authorization_code by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/authorization_codes/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'authorization_code', headers=self.authorization_code_headers, 
                    details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete authorization_code by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/authorization_codes/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete authorization_code %s' % value}
        self.result(res, headers=[u'msg'])        


class ClientController(Oauth2ControllerChild):
    client_headers = [u'id', u'uuid', u'name', u'response_type', u'grant_type', u'scopes']
    
    class Meta:
        label = 'clients'
        description = "Client management"
        
    @expose(aliases=[u'add <name> <grant_type> <redirect_uri> <scopes> <expiry_date>'], aliases_only=True)
    @check_error
    def add(self):
        """Add client
    - scopes: comma separated list of scopes
    - expire_date syntax: yyyy-mm-dd
    - valid grant_type: 
       - authorization_code 
       - implicit 
       - password 
       - client_credentials
       - urn:ietf:params:oauth:grant-type:jwt-bearer
        """
        name = self.get_arg(name=u'name')
        grant_type = self.get_arg(name=u'grant_type')
        redirect_uri = self.get_arg(name=u'redirect_uri')
        scopes = self.get_arg(name=u'scopes')
        expiry_date = self.get_arg(name=u'expiry_date')
        data = {
            u'client': {
                u'name': name,
                u'grant_type': grant_type,
                u'redirect_uri': redirect_uri,
                u'desc': u'Client %s' % name,
                u'response_type': u'code',
                u'scopes': scopes,
                u'expiry_date': expiry_date
            }
        } 
        uri = u'%s/clients' % self.authuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add client: %s' % res)
        res = {u'msg': u'Add client %s' % res}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all clients       
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/clients' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'clients', headers=self.client_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get client by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/clients/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'client', headers=self.client_headers, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete client by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/clients/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete client %s' % value}
        self.result(res, headers=[u'msg'])        


class ScopeController(Oauth2ControllerChild):
    scope_headers = [u'id', u'uuid', u'name', u'active', u'date.creation']

    class Meta:
        label = 'scopes'
        description = "Scope management"
        
    @expose(aliases=[u'add <name>'], aliases_only=True)
    @check_error
    def add(self):
        """Add scope
        """          
        name = self.get_arg(name=u'name')
        data = {
            u'scope': {
                u'name': name,
                u'desc': u'Scope %s' % name
            }  
        } 
        uri = u'%s/scopes' % self.authuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add scope: %s' % res)
        res = {u'msg': u'Add scope %s' % res}
        self.result(res, headers=[u'msg'])        
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all scopes       
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/scopes' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'scopes', 
                    headers=self.scope_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get scope by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/scopes/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'scope', headers=self.scope_headers, 
                    details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete scope by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/scopes/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete scope %s' % value}
        self.result(res, headers=[u'msg'])        


oauth2_controller_handlers = [
    Oauth2Controller,
    Oauth2SessionController,
    ClientController,
    ScopeController,
    AuthorizationCodeController
]
