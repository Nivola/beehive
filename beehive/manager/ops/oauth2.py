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
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request
from datetime import datetime, timedelta
import jwt

logger = logging.getLogger(__name__)

class GrantType(object):
    AUTHORIZATION_CODE = u'authorization_code'
    IMPLICIT = u'implicit'
    RESOURCE_OWNER_PASSWORD_CREDENTIAL = u'resource_owner_password_credentials'
    CLIENT_CRDENTIAL = u'client_credentials'
    JWT_BEARER = u'urn:ietf:params:oauth:grant-type:jwt-bearer'

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

class Oaut2hManager(ApiManager):
    """
    SECTION: 
        oauth2
        
    PARAMS:
        tokens create <user> <pwd> <client-conf.json>

    """
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/oauth2'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.client_headers = [u'id', u'uuid', u'objid', u'name', 
                               u'grant_type', u'scopes', u'active']
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
        self.result(res, key=u'client', headers=self.client_headers)
        
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
    
    
    