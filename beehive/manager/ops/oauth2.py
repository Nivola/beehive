'''
Created on May 31, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager, ComponentManager
import sys
from beecell.simple import truncate
from re import match
import binascii
from requests_oauthlib.oauth2_session import OAuth2Session
from oauthlib.oauth2.rfc6749.clients.base import Client
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request,\
    parse_token_response
from datetime import datetime, timedelta
import jwt
from oauthlib.oauth2.rfc6749 import errors, tokens, utils
from time import time
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

logger = logging.getLogger(__name__)

class GrantType(object):
    AUTHORIZATION_CODE = u'authorization_code'
    IMPLICIT = u'implicit'
    RESOURCE_OWNER_PASSWORD_CREDENTIAL = u'resource_owner_password_credentials'
    CLIENT_CRDENTIAL = u'client_credentials'
    JWT_BEARER = u'urn:ietf:params:oauth:grant-type:jwt-bearer'

class InvalidJwtError(errors.OAuth2Error):

    """The requested jwt is invalid, unknown, or malformed."""
    error = 'invalid_jwt'
    status_code = 401
    
class InvalidUserError(errors.OAuth2Error):

    """The requested user is invalid, unknown, or malformed."""
    error = 'invalid_user'
    status_code = 401
    
class OAuth2Error(errors.OAuth2Error):
    def __init__(self, description=None, uri=None, state=None, status_code=None,
                 request=None, error=None):
        self.error = error
        errors.OAuth2Error.__init__(self, description, uri, state, status_code,
                                    request)

class JWTClient(Client):
    """A client that implement the use case 'JWTs as Authorization Grants' of 
    the rfc7523.
    """
    def prepare_request_body(self, body=u'', scope=None, **kwargs):
        """Add the client credentials to the request body.
        """
        grant_type = GrantType.JWT_BEARER
        return prepare_token_request(grant_type, body=body,
                                     scope=scope, **kwargs)
        
    def parse_request_body_response(self, body, scope=None, **kwargs):
        logger.warn(body)
        self.token = self.__parse_token_response(body, scope=scope)
        self._populate_attributes(self.token)
        return self.token     

    def __parse_token_response(self, body, scope=None):
        """Parse the JSON token response body into a dict.
        """
        try:
            params = json.loads(body)
        except ValueError:
    
            # Fall back to URL-encoded string, to support old implementations,
            # including (at time of writing) Facebook. See:
            #   https://github.com/idan/oauthlib/issues/267
    
            params = dict(urlparse.parse_qsl(body))
            for key in ('expires_in', 'expires'):
                if key in params:  # cast a couple things to int
                    params[key] = int(params[key])
    
        if 'scope' in params:
            params['scope'] = utils.scope_to_list(params['scope'])
    
        if 'expires' in params:
            params['expires_in'] = params.pop('expires')
    
        if 'expires_in' in params:
            params['expires_at'] = time() + int(params['expires_in'])
    
        params = tokens.OAuth2Token(params, old_scope=scope)
        self.__validate_token_parameters(params)
        return params
    
    def __validate_token_parameters(self, params):
        """Ensures token precence, token type, expiration and scope in params."""
        if 'error' in params:
            kwargs = {
                'description': params.get('error_description'),
                'uri': params.get('error_uri'),
                'state': params.get('state'),
                'error': params.get('error')
            }
            raise OAuth2Error(**kwargs)
    
        if not 'access_token' in params:
            raise errors.MissingTokenError(description="Missing access token parameter.")
    
        '''
        if not 'token_type' in params:
            if os.environ.get('OAUTHLIB_STRICT_TOKEN_TYPE'):
                raise MissingTokenTypeError()
    
        # If the issued access token scope is different from the one requested by
        # the client, the authorization server MUST include the "scope" response
        # parameter to inform the client of the actual scope granted.
        # http://tools.ietf.org/html/rfc6749#section-3.3
        if params.scope_changed:
            message = 'Scope has changed from "{old}" to "{new}".'.format(
                old=params.old_scope, new=params.scope,
            )
            scope_changed.send(message=message, old=params.old_scopes, new=params.scopes)
            if not os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE', None):
                w = Warning(message)
                w.token = params
                w.old_scope = params.old_scopes
                w.new_scope = params.scopes
                raise w'''

class Oaut2hManager(ApiManager):
    """
    SECTION: 
        oauth2
        
    PARAMS:
        tokens create <user> <pwd> <client-conf.json>
        
        clients list
        clients get
        clients add
        clients delete <id>

        scopes list
        scopes get
        scopes add
        scopes delete <id>
    """
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/oauth2'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.client_headers = [u'id', u'uuid', u'objid', u'name', 
                               u'grant_type', u'active']
        self.scope_headers = [u'id', u'uuid', u'objid', u'name', u'desc']        
        self.token_headers = [u'token_type', u'access_token', u'scope',
                              u'user', u'expires_in', u'expires_at']
    
    def actions(self):
        actions = {
            u'tokens.create': self.create_token,
            u'tokens.list': self.verify_token,

            u'clients.list': self.get_clients,
            u'clients.get': self.get_client,
            u'clients.add': self.add_client,
            u'clients.delete': self.delete_client,
            
            u'scopes.list': self.get_scopes,
            u'scopes.get': self.get_scope,
            u'scopes.add': self.add_scope,
            u'scopes.delete': self.delete_scope,            
        }
        return actions
    
    #
    # token
    #
    def create_token(self, user, pwd, config):
        client = self.load_config(config)
        
        # get client
        client_id = client[u'uuid']
        client_email = client[u'client_email']
        client_scope = client[u'scopes'][0][u'name']
        private_key = binascii.a2b_base64(client[u'private_key'])
        client_token_uri = client[u'token_uri']
        aud = client[u'aud']

        client = JWTClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        
        now = datetime.utcnow()
        claims = {
            u'iss':client_email,
            u'sub':u'%s:%s' % (user, pwd),
            u'scope':client_scope,
            u'aud':aud,
            u'exp':now + timedelta(seconds=60),
            u'iat':now,
            u'nbf':now
        }
        #priv_key = RSA.importKey(private_key)
        encoded = jwt.encode(claims, private_key, algorithm=u'RS512')
        #encoded = ''
        res = client.prepare_request_body(assertion=encoded, client_id=client_id)
        token = oauth.fetch_token(token_url=client_token_uri, 
                                  body=res, verify=False)
        self.logger.debug(u'Get token : %s' % token)
        self.result(token, headers=self.token_headers)          

    def verify_token(self, token):
        uri = u'%s/login/%s/' % (self.baseuri, token)
        res = self._call(uri, u'GET')
        self.logger.info(u'Verify user token %s: %s' % (token, truncate(res)))
        self.result(res, headers=[u'token', u'exist'])     
    
    #
    # clients
    #    
    def get_clients(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/clients/' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get clients: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')
        self.result(res, key=u'clients', headers=self.client_headers)
    
    def get_client(self, client_id):
        uri = u'%s/clients/%s/' % (self.baseuri, client_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get client: %s' % truncate(res))
        self.result(res, key=u'client', headers=self.client_headers, 
                    details=True)
        
    def add_client(self, subsystem, otype, objid, desc):
        data = {
            u'clients':[
                {
                    u'subsystem':subsystem,
                    u'type':otype,
                    u'objid':objid,
                    u'desc':desc
                }
            ]
        }
        uri = u'%s/clients/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add client: %s' % truncate(res))
        #self.result(res)
        print(u'Add client: %s' % res)
        
    def delete_client(self, client_id):
        uri = u'%s/clients/%s/' % (self.baseuri, client_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete client: %s' % truncate(res))
        #self.result(res)
        print(u'Delete client: %s' % client_id)
    
    #
    # scopes
    #    
    def get_scopes(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/scopes/' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get scopes: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')
        self.result(res, key=u'scopes', headers=self.scope_headers)
    
    def get_scope(self, scope_id):
        uri = u'%s/scopes/%s/' % (self.baseuri, scope_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get scope: %s' % truncate(res))
        self.result(res, key=u'scope', headers=self.scope_headers, details=True)
        
    def add_scope(self, name, desc):
        data = {
            u'scope':{
                u'name':name,
                u'desc':desc
            }
        }
        uri = u'%s/scopes/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add scope: %s' % truncate(res))
        #self.result(res)
        print(u'Add scope: %s' % res)
        
    def delete_scope(self, scope_id):
        uri = u'%s/scopes/%s/' % (self.baseuri, scope_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete scope: %s' % truncate(res))
        #self.result(res)
        print(u'Delete scope: %s' % scope_id)    
    