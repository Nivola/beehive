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

logger = logging.getLogger(__name__)

class KeyauthManager(ApiManager):
    """
    SECTION: 
        keyauth
        
    PARAMS:
        tokens create <user> <pwd>
    """
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/keyauth'
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
            u'tokens.create': self.cerate_token,
            
            u'keyauth.token': self.verify_token,
            u'keyauth.logout': self.logout_user,         
        }
        return actions
    
    #
    # keyauth login
    #
    def cerate_token(self, user, pwd):
        data = {u'user':user, u'password':pwd}
        uri = u'%s/login/' % (self.baseuri)
        res = self.client.send_signed_request(
                u'auth', uri, u'POST', data=json.dumps(data))
        res = res[u'response']
        self.logger.info(u'Login user %s: %s' % (user, res))
        self.result(res, headers=[u'user.id', u'uid', u'user.name', u'timestamp',
                                  u'user.active'], details=True)
        '''print(u'Secret key: %s' % res.get(u'seckey'))
        print(u'Public key: %s' % res.get(u'pubkey'))
        print(u'Roles: %s' % u', '.join(res[u'user'][u'roles']))
        print(u'')
        print(u'Attributes:')
        attrs = []
        for k,v in res[u'user'][u'attribute'].items():
            attrs.append({
                u'name':k, 
                u'value':v[0],
                u'desc':v[1]
            })
        self.result(attrs, headers=[u'name', u'value', u'desc'])
        print(u'Permissions:')
        perms = []
        for v in res[u'user'][u'perms']:
            perms.append({
                u'pid':v[0], 
                u'oid':v[1], 
                u'objtype':v[2], 
                u'objdef':v[3], 
                u'objid':v[5], 
                u'action':v[7]
            })        
        self.result(perms, headers=self.perm_headers)'''    

    def verify_token(self, token):
        uri = u'%s/login/%s/' % (self.baseuri, token)
        res = self._call(uri, u'GET')
        self.logger.info(u'Verify user token %s: %s' % (token, truncate(res)))
        self.result(res, headers=[u'token', u'exist']) 
    
    def logout_user(self, token, seckey):
        uri = u'%s/logout/' % (self.baseuri)
        res = self.client.send_signed_request(
                u'auth', uri, u'DELETE', data=u'', uid=token, seckey=seckey)
        res = res[u'response']
        self.logger.info(u'Logout %s: %s' % (token, truncate(res)))
        self.result(res)