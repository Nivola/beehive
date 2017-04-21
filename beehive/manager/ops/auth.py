'''
Created on Mar 24, 2017

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

logger = logging.getLogger(__name__)

class AuthManager(ApiManager):
    """
    SECTION: 
        resource
        
    PARAMS:
        auth <entity> <op>

            
        catalogs list
        catalogs get <id>
        catalogs add <name> <zone>
        catalogs delete <id>
        
        endpoints list
        endpoints get <id>
        endpoints add <name> <catalog_id> <subsystem> <uri=http://localhost:3030>
        endpoints delete <id>
        
        keyauth domains
        keyauth login <name>@<domain> <password>
        keyauth token <token>
        keyauth logout
        
        users list
        users get <id>
        users add <name> <zone>
        users delete <id>        
        
        <entity> <op>        
            entity: users, roles, objects, perms
            op: list, get, add, update, delete        
        
        perm 
        object
        role
        role get <name>
        user
        user get <name>
        user add_system <name> <pwdd> <desc> 
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/keyauth'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                            u'date.creation', u'date.modification']
        self.end_headers = [u'id', u'uuid', u'catalog_id', u'catalog', 
                            u'name', u'service', u'active',
                            u'endpoint', u'date.creation', u'date.modification']  
    
    def actions(self):
        actions = {
            u'catalogs.list': self.get_catalogs,
            u'catalogs.get': self.get_catalog,
            u'catalogs.add': self.add_catalog,
            u'catalogs.delete': self.delete_catalog,
           
            u'endpoints.list': self.get_endpoints,
            u'endpoints.get': self.get_endpoint,
            u'endpoints.add': self.add_endpoint,
            u'endpoints.delete': self.delete_endpoint,           
           
            u'keyauth.domains': self.login_domains,
            u'keyauth.login': self.login_user,
            u'keyauth.token': self.verify_token,
            u'keyauth.logout': self.logout_user,
            
            u'identities.list': self.get_identities,
            u'identities.get': self.get_identity,
            u'identities.delete': self.delete_identity,
            
            u'users.list': self.get_users,
            u'users.get': self.get_user,
            u'users.perms': self.get_user_perms,
            u'users.roles': self.get_user_roles,
            u'users.groups': self.get_user_groups,
            u'users.attribs': self.get_user_attribs,
            u'users.can': self.can_user,
            u'users.add': self.add_user,
            u'users.update': self.update_user,
            u'users.delete': self.delete_user,
            
            u'roles.list': self.get_roles,
            u'roles.get': self.get_role,
            u'roles.perms': self.get_role_perms,
            u'roles.users': self.get_role_users,
            u'roles.groups': self.get_role_groups,
            u'roles.add': self.add_role,
            u'roles.update': self.update_role,
            u'roles.delete': self.delete_role,             
            
            u'groups.list': self.get_groups,
            u'groups.get': self.get_group,
            u'groups.perms': self.get_group_perms,
            u'groups.roles': self.get_group_roles,
            u'groups.users': self.get_group_users,
            u'groups.add': self.add_group,
            u'groups.update': self.update_group,
            u'groups.delete': self.delete_group,
            
            u'objects.list': self.get_objects,
            u'objects.get': self.get_object,
            u'objects.perms': self.get_object_perms,
            u'objects.add': self.add_object,
            u'objects.delete': self.delete_object,
            u'types.list': self.get_types,
            u'types.add': self.add_type,
            u'types.delete': self.delete_type,            
            u'perms.list': self.get_perms,
            u'perms.get': self.get_perm,
            u'actions.list': self.get_actions,
        }
        return actions    
    
    #
    # catalogs
    #
    def get_catalogs(self):
        res = self.client.get_catalogs()
        self.logger.info(u'Get catalogs: %s' % truncate(res))
        self.result(res, headers=self.cat_headers)
    
    def get_catalog(self, catalog_id):
        res = self.client.get_catalog(catalog_id)
        self.logger.info(u'Get catalog: %s' % truncate(res))
        services = []
        for k,v in res.get(u'services', {}).items():
            for v1 in v:
                services.append({u'service':k, u'endpoint':v1})
        self.result(res, headers=self.cat_headers)
        if self.format == u'table':
            print(u'Services: ')
            self.result(services, headers=[u'service', u'endpoint'])
        
    def add_catalog(self, name, zone):
        res = self.client.create_catalog(name, zone)
        self.logger.info(u'Add catalog: %s' % truncate(res))
        self.result(res)
        
    def delete_catalog(self, catalog_id):
        res = self.client.delete_catalog(catalog_id)
        self.logger.info(u'Delete catalog: %s' % truncate(res))
        self.result(res)
        
    #
    # endpoints
    #    
    def get_endpoints(self):
        res = self.client.get_endpoints()
        self.logger.info(u'Get endpoints: %s' % truncate(res))
        self.result(res, key=u'endpoints', headers=self.end_headers)
    
    def get_endpoint(self, endpoint_id):
        res = self.client.get_endpoint(endpoint_id)
        self.logger.info(u'Get endpoint: %s' % truncate(res))
        self.result(res, key=u'endpoint', headers=self.end_headers)
        
    def add_endpoint(self, name, catalog, service, uri):
        # if endpoint exist update it else create new one
        try:
            res = self.client.get_endpoint(name)
            res = self.client.update_endpoint(name, catalog_id=catalog, 
                                              name=name, 
                                              service=service, uri=uri)
        except Exception as ex:
            logger.error(ex, exc_info=1)
            res = self.client.create_endpoint(catalog, name, service, uri)
        self.logger.info(u'Add endpoint: %s' % truncate(res))
        self.result(res)
        
    def delete_endpoint(self, endpoint_id):
        res = self.client.delete_endpoint(endpoint_id)
        self.logger.info(u'Delete endpoint: %s' % truncate(res))
        self.result(res)        
         
    #
    # keyauth login
    #
    def login_domains(self):
        uri = u'%s/login/domains/' % (self.baseuri)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get domains: %s' % truncate(res))
        domains = []
        for item in res[u'domains']:
            domains.append({u'domain':item[0],
                            u'type':item[1]})
        self.result(domains, headers=[u'domain', u'type'])
        
    def login_user(self, user, pwd):
        data = {u'user':user, u'password':pwd}
        uri = u'%s/login/' % (self.baseuri)
        res = self.client.send_signed_request(
                u'auth', uri, u'POST', data=json.dumps(data))
        res = res[u'response']
        self.logger.info(u'Login user %s: %s' % (user, res))
        self.result(res, headers=[u'user.id', u'uid', u'user.name', u'timestamp',
                                  u'user.active'])
        print(u'Secret key: %s' % res.get(u'seckey'))
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
        self.result(perms, headers=self.perm_headers)          

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
    
    def get_users(self, *args):
        data = self.format_http_get_query_params(*args)
        uri = u'%s/user/' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get users: %s' % truncate(res))
        self.result(res, headers=self.cat_headers)
    
    def get_user(self, user_id):
        uri = u'%s/user/%s/' % (self.baseuri, user_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get user: %s' % truncate(res))
        self.result(res, headers=self.cat_headers)
        
    def add_user(self, name, zone):
        res = self.client.create_user(name, zone)
        self.logger.info(u'Add user: %s' % truncate(res))
        self.result(res)
        
    def delete_user(self, user_id):
        res = self.client.delete_user(user_id)
        self.logger.info(u'Delete user: %s' % truncate(res))
        self.result(res)

    #
    # keyauth identities
    #    
    def get_identities(self):
        uri = u'%s/identities/' % (self.baseuri)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get identities: %s' % truncate(res))
        self.result(res, headers=[u'uid', u'user', u'ip', u'ttl', u'timestamp'])
    
    def get_identity(self, oid):
        uri = u'%s/identities/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get identity: %s' % truncate(res))
        self.result(res, headers=[u'uid', u'user', u'ip', u'ttl', u'timestamp'])
        
    def delete_identity(self, oid):
        uri = u'%s/identities/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete identity: %s' % truncate(res))
        self.result({u'identity':oid}, headers=[u'identity']) 


        
        
        
        