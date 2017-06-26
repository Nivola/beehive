'''
Created on May 31, 2017

@author: darkbk
'''
import ujson as json
import logging
import binascii
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager, ComponentManager
import sys
from beecell.simple import truncate
from re import match
from beehive.common.jwtclient import JWTClient, GrantType
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Oaut2hManager(ApiManager):
    """
    SECTION: 
        oauth2
        
    PARAMS:
        tokens create <user> <pwd> <client-conf.json>
        
        clients list
        clients get
        clients add <name> [<authorization_code>|jwt grant code] 
                    [<redirect_uri>|https://localhost] [<scopes>|beehive]
                    [<response_type>|code] [<expiry_date>|today+365days]
        clients delete <id>

        scopes list
        scopes get
        scopes add <name> <desc>
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

        token = JWTClient.create_token(client_id, client_email, client_scope, 
                                       private_key, client_token_uri, aud, 
                                       user, pwd)
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
        
    def add_client(self, name, authorization_code=None, 
                   redirect_uri=u'https://localhost', scopes=u'beehive', 
                   response_type=u'code', expiry_date=None):
        if expiry_date is None:
            expiry_date = datetime.today() + timedelta(days=365)
            expiry_date = expiry_date.strftime(u'%d-%m-%Y')
        if authorization_code is None:
            authorization_code = GrantType.JWT_BEARER
        data = {
            u'client':{
                u'name':name,
                u'grant-type':authorization_code,
                u'redirect-uri':redirect_uri,
                u'description':u'Client %s' % name,
                u'response-type':u'code',
                u'scopes':scopes,
                u'expiry-date':expiry_date
            }
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
    