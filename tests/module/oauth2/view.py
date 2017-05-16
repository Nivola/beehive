'''
Created on May 3, 2017

@author: darkbk
'''
import os
from re import match
from flask import request, send_from_directory
from beecell.simple import id_gen, import_class, get_value, str2bool,\
    get_remote_ip, truncate
from gibboncloudapi.util.data import operation
from gibboncloudapi.module.base import ApiView, ApiManagerError
from beecell.simple import get_attrib

import ujson as json
from flask import redirect
from flask import request, Response
from flask import session
from urllib import urlencode

from beecell.flask.render import render_template
from beecell.flask.login.forms import LoginForm
from beecell.flask.decorators import login_required
from beecell.simple import get_attrib

from logging import getLogger
from beecell.perf import watch

#import oauthlib.oauth2
from oauthlib.oauth2 import FatalClientError, OAuth2Error
from gibboncloudapi.module.oauth2.model import GrantType
from flask.helpers import url_for

class Oauth2ApiView(ApiView):
    """Oauth2 base view
    """
    def authorize_error(self, redirect_uri, error, state, 
                        error_description=None, error_uri=None):
        """Return error from authorize request.
        
        For example, the authorization server redirects the user-agent by 
        sending the following HTTP response:

        HTTP/1.1 302 Found Location: 
            https://client.example.com/cb?error=access_denied&state=xyz            
        
        :param error: A single error code from the following:  
            invalid_request - The request is missing a required 
                              parameter, includes an invalid parameter 
                              value, or is otherwise malformed.  
            unauthorized_client - The client is not authorized to 
                                  request an authorization code using 
                                  this method.  
            access_denied - The resource owner or authorization server 
                            denied the request.  
            unsupported_response_type - The authorization server does 
                                        not support obtaining an 
                                        authorization code using this 
                                        method.  
            invalid_scope - The requested scope is invalid, unknown, or 
                            malformed.  
            server_error - The authorization server encountered an 
                           unexpected condition which prevented it from 
                           fulfilling the request.  
            temporarily_unavailable - The authorization server is 
                                      currently unable to handle the 
                                      request due to a temporary 
                                      overloading or maintenance of the 
                                      server. 
        :param error_description: [OPTIONAL]  A human-readable UTF-8 encoded 
            text providing  additional information, used to assist the client 
            developer in understanding the error that occurred. 
        :param error_uri: [OPTIONAL] A URI identifying a human-readable web page 
            with  information about the error, used to provide the client  
            developer with additional information about the error. 
        :param state: if a "state" parameter was present in the client 
            authorization request. The exact value received from the client.        
        """
        #params = urlencode({'error_description':error_description})     
        resp = redirect(u'%s' % (redirect_uri))
        return resp

    @watch
    def get_error(self, exception, code, error):
        """
        
        :param code: error code. If code 420 redirect to client error page
                     If code 421 return error page. For other code return 
                     json error response.
        """
        self.logger.error(u'Code: %s, Error: %s' % (code, exception), 
                          exc_info=True)        
        if code == 420:
            #resp = self.authorize_error(error.in_uri(error.redirect_uri), 
            #                            error.error, state, 
            #                            error.description)
            resp = redirect(u'%s' % (error.redirect_uri))  
        elif code == 421:
            resp = render_template(u'error.html', errors=error)
        else:
            headers = {u'Cache-Control':u'no-store',
                       u'Pragma':u'no-cache'}
            body = {u'error':exception, u'error_description':error}
            resp = Response(json.dumps(body), 
                            mimetype=u'application/json;charset=UTF-8', 
                            status=code,
                            headers=headers) 
        return resp

#
# authorization
#
class GetAuthorization(Oauth2ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        # authenticate client
        uri = request.path
        http_method = request.method
        body = request.args.to_dict()
        headers = request.headers
        
        # validate input params
        response_type = get_value(body, u'response_type', None, exception=True)
        client_id = get_value(body, u'client_id', None, exception=True)
        redirect_uri = get_value(body, u'redirect_uri', None, exception=True)
        scope = get_value(body, u'scope', None, exception=True)
        state = get_value(body, u'state', None, exception=True)
        
        # call controller  
        credentials = controller.authenticate_client(uri, http_method, body, headers)
        session_credentials = controller.get_credentials(session)
        
        if session_credentials is None:
            # redirect to login page
            controller.save_credentials(session, credentials)
            resp = redirect(u'/%s/oauth2/login/?state=%s' % 
                            (controller.version, state))
            return resp, resp.status_code
            
        # check credentials - if client credentials and session credentials
        # does not match invalidate session and redirect to login page
        if controller.check_credentials(session, credentials) is False:
            # redirect to login page
            controller.save_credentials(session, credentials)
            resp = redirect(u'/%s/oauth2/login/?state=%s' % 
                            (controller.version, state))
            return resp, resp.status_code         
        
        # check login
        user = controller.check_login(session)
        if user is None:
            # redirect to login page
            resp = redirect(u'/%s/oauth2/login/?state=%s' % 
                            (controller.version, state))
            return resp, resp.status_code
        
        # check user agree scopes
        user_scope = controller.check_login_scopes(user)
        if user_scope is None:
            # redirect to login scope page
            resp = redirect(u'/%s/oauth2/authorize/scope/?state=%s' % 
                            (controller.version, state))
            return resp, resp.status_code
        
        # set user oid in session_credentials to remedy a bug in oauthlib
        session_credentials[u'user'] = user[u'id']
        
        # create authorization token
        body, status, headers = controller.create_authorization(
            uri, http_method, body, headers, user_scope, 
            session_credentials)

        return Response(body, status=status, headers=headers), status

class GetAuthorizationScope(ApiView):
    """
    """
    def dispatch(self, controller, data, *args, **kwargs):   
        msg, client_id, scope = controller.get_client_scopes(session)
        return render_template(
            u'scope.html',
            msg=msg, 
            client=client_id, 
            scope=scope,
            scope_uri=u'/%s/oauth2/authorize/scope/' % controller.version), 200

class SetAuthorizationScope(ApiView):
    """
    """
    def dispatch(self, controller, data, *args, **kwargs):
        scopes = request.form.to_dict().get(u'scope')
        credentials = controller.set_user_scopes(session, scopes.split(u' '))
        credentials[u'scope'] = scopes
        params = urlencode(credentials)
        self.logger.warn(params)
        resp = redirect(u'/%s/oauth2/authorize/?%s' % 
                        (controller.version, params))
        #resp = redirect(u'/%s/oauth2/authorize/' % 
        #                (controller.version))
        self.logger.warn(session[u'oauth2_credentials']) 
        return resp, resp.status_code
    
class CreateAccessToken(Oauth2ApiView):
    """
    {u'code': u'bUCrCB2IMuIowKMt7fllpMh35H2aIY', 
     u'client_secret': u'exh7ez922so3eeQjbsJLgiSR3fW3AVc1dsmQiBIi', 
     u'grant_type': u'authorization_code', 
     u'client_id': u'8a994dd1-e96b-4092-8a14-ede3f77d8a2c', 
     u'redirect_uri': u'https://localhost:7443/authorize'}    
    """
    def dispatch(self, controller, data, *args, **kwargs):
        # authenticate client
        uri = request.path
        http_method = request.method
        body = request.form.to_dict()
        headers = request.headers
        login_ip = get_remote_ip(request)
        body, status, headers = controller.create_token(
            uri, http_method, body, headers, session, login_ip)
        
        return Response(body, status=status, headers=headers)        

#
# login, logout
#
class ListDomains(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        auth_providers = controller.module.authentication_manager.auth_providers
        res = []
        for domain, auth_provider in auth_providers.iteritems():
            res.append([domain, auth_provider.__class__.__name__])
        resp = {u'domains':res,
                u'count':len(res)}
        return resp

class Login(ApiView):
    """
     data: {u'user':.., u'password':.., u'login-ip':..}    
    """
    def dispatch(self, controller, data, *args, **kwargs):
        user = request.form.to_dict()        
        name = get_value(user, u'username', None, exception=True)
        domain = get_value(user, u'domain', None, exception=True)
        password = get_value(user, u'password', None, exception=True)
        login_ip = get_remote_ip(request)
        
        innerperms = [
            (1, 1, u'auth', u'objects', u'ObjectContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'role', u'RoleContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'user', u'UserContainer', u'*', 1, u'*')]
        operation.perms = innerperms     
        res = controller.login(session, name, domain, password, login_ip)
        if res is True:
            resp = redirect(u'/%s/oauth2/authorize/scope' % controller.version)
        else:
            resp = redirect(u'/%s/oauth2/login' % controller.version)
        return resp
    
class LoginPage(ApiView):
    """Open Login Page 
    """
    def dispatch(self, controller, data, *args, **kwargs):
        msg = session.get(u'msg', None)
        redirect_uri = request.args.get(u'redirect-uri', None)
        style = u'css/style.%s.css' % request.args.get(u'style', u'blue')
        domains, redirect_uri = controller.login_page(redirect_uri)
        return render_template(
            u'login.html', 
            msg=msg, 
            domains=domains,
            redirect_uri=redirect_uri,
            login_uri=u'/%s/oauth2/login/' % controller.version,
            style=url_for(u'static', filename=style)), 200

class Oauth2Api(ApiView):
    """Asymmetric key authentication API
    """
    @staticmethod
    def register_api(module):
        base = u'oauth2'
        rules = [
            (u'%s/login/domains' % base, u'GET', ListDomains, {u'secure':False}),
            (u'%s/login' % base, u'POST', Login, {u'secure':False}),
            (u'%s/login' % base, u'GET', LoginPage, {u'secure':False}),
            
            
            #(u'%s/login/refresh' % base, u'PUT', LoginRefresh, {}),
            #(u'%s/login/<oid>' % base, u'GET', LoginExists, {}),
            #(u'%s/logout' % base, u'DELETE', Logout, {}),
            
            #(u'%s/identities' % base, u'GET', ListIdentities, {}),
            #(u'%s/identities/<oid>' % base, u'GET', GetIdentity, {}),
            #(u'%s/identities/<oid>' % base, u'DELETE', DeleteIdentity, {}),
            
            
            (u'%s/authorize' % base, u'GET', GetAuthorization, {u'secure':False}),
            #(u'%s/authorize' % base, u'POST', CreateAuthorization, {u'secure':False}),
            (u'%s/authorize/scope' % base, u'GET', GetAuthorizationScope, {u'secure':False}),
            (u'%s/authorize/scope' % base, u'POST', SetAuthorizationScope, {u'secure':False}),
            (u'%s/token' % base, u'POST', CreateAccessToken, {u'secure':False}),
        ]
        
        ApiView.register_api(module, rules)