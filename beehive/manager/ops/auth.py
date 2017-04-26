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
        
        users list <field>=<value>    field: page, size, order, field, role, group
            field can be: id, objid, uuid, name, description, creation_date, modification_date
            
            Ex. page=2 order=ASC field=name
        users get <id>
        users add <name> <desc>
        users update
        users delete <id>
        users add-role <id> <role>
        users delete-role <id> <role>        
        
        roles list <field>=<value>    field: page, size, order, field, user, group
            field can be: id, objid, uuid, name, description, creation_date, modification_date
            
            Ex. page=2 order=ASC field=name
        roles get <id>
        roles add <name> <desc>
        roles update <id> [name=<name>] [desc=<desc>]
        roles delete <id>
        roles add-perm <id> <subsystem> <ptype> <objid> <action>
        roles delete-perm <id> <subsystem> <ptype> <objid> <action>        
        
        groups list <field>=<value>    field: page, size, order, field, role, user
            field can be: id, objid, uuid, name, description, creation_date, modification_date
            
            Ex. page=2 order=ASC field=name
        groups get <id>
        groups add <name> <desc>
        groups update <id> [name=<name>] [desc=<desc>]
        groups delete <id>
        groups add-role <id> <role>
        groups delete-role <id> <role> 
        groups add-user <id> <user>
        groups delete-user <id> <user>
        
        objects list <field>=<value>    field: page, size, order, field, subsystem, type, objid
            field can be: subsystem, type, id, objid
            
            Ex. page=2 order=ASC field=subsystem
        objects get <id>
        objects add <subsystem> <type> '<objid>' '<desc>'
        objects delete <id>
        
        types list <field>=<value>    field: page, size, order, field, subsystem, type
            field can be: subsystem, type, id
            
            Ex. page=2 order=ASC field=subsystem
        types add <subsystem> <type>
        types delete <id>
        
        perms list <field>=<value>    field: page, size, order, field, subsystem, type, objid, user, role, group
            field can be: subsystem, type, id, objid, aid, action
            
            Ex. page=2 order=ASC field=subsystem
        perms get <id>
        
        actions list
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/keyauth'
        self.authuri = u'/v1.0/auth'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.obj_headers = [u'id', u'objid', u'subsystem', u'type', u'desc']
        self.type_headers = [u'id', u'subsystem', u'type']
        self.act_headers = [u'id', u'value']
        self.perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', 
                             u'aid', u'action', u'desc']
        self.user_headers = [u'id', u'uuid', u'objid', u'name', u'active', 
                              u'date.creation', u'date.modified', u'desc']
        self.role_headers = [u'id', u'uuid', u'objid', u'name', u'active', 
                              u'date.creation', u'date.modified', u'desc']
        self.group_headers = [u'id', u'uuid', u'objid', u'name', u'active', 
                              u'date.creation', u'date.modified', u'desc']
    
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
            #u'users.add': self.add_user,
            #u'users.update': self.update_user,          
            u'users.delete': self.delete_user,
            #u'users.attribs': self.get_user_attribs,
            #u'users.can': self.can_user,
            u'users.add-role':self.add_users_role,
            u'users.delete-role':self.delete_users_role,              
            
            u'roles.list': self.get_roles,
            u'roles.get': self.get_role,
            u'roles.add': self.add_role,
            u'roles.update': self.update_role,
            u'roles.add-perm':self.add_role_perm,
            u'roles.delete-perm':self.delete_role_perm,
            u'roles.delete': self.delete_role,             
            
            u'groups.list': self.get_groups,
            u'groups.get': self.get_group,
            u'groups.add': self.add_group,
            u'groups.update': self.update_group,
            u'groups.add-role':self.add_group_role,
            u'groups.delete-role':self.delete_group_role,
            u'groups.add-user':self.add_group_user,
            u'groups.delete-user':self.delete_group_user,
            u'groups.delete': self.delete_group,
            
            u'objects.list': self.get_objects,
            u'objects.get': self.get_object,
            u'objects.add': self.add_object,
            u'objects.delete': self.delete_object,
            
            u'types.list': self.get_object_types,
            u'types.add': self.add_object_type,
            u'types.delete': self.delete_object_type,            
            
            u'perms.list': self.get_perms,
            u'perms.get': self.get_perm,
            
            u'actions.list': self.get_actions,
        }
        return actions
    
    #
    # actions
    #        
    def get_actions(self):
        uri = u'%s/objects/actions/' % (self.authuri)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object: %s' % truncate(res))
        self.result(res, key=u'object-actions', headers=self.act_headers)     
    
    #
    # perms
    #    
    def get_perms(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects/perms/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    def get_perm(self, perm_id):
        uri = u'%s/objects/perms/%s/' % (self.authuri, perm_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object perm: %s' % truncate(res))
        self.result(res, key=u'perm', headers=self.perm_headers)    
    
    #
    # object types
    #    
    def get_object_types(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects/types/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')
        self.result(res, key=u'object-types', headers=self.type_headers)

    def add_object_type(self, subsystem, otype):
        data = {
            u'object-types':[
                {
                    u'subsystem':subsystem,
                    u'type':otype,
                }
            ]
        }
        uri = u'%s/objects/types/' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add object: %s' % truncate(res))
        #self.result(res)
        print(u'Add object type: %s' % res)
        
    def delete_object_type(self, object_id):
        uri = u'%s/objects/types/%s/' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete object: %s' % truncate(res))
        #self.result(res)
        print(u'Delete object type: %s' % object_id)    
    
    #
    # objects
    #    
    def get_objects(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')
        self.result(res, key=u'objects', headers=self.obj_headers)
    
    def get_object(self, object_id):
        uri = u'%s/objects/%s/' % (self.authuri, object_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object: %s' % truncate(res))
        self.result(res, key=u'object', headers=self.obj_headers)
        
    def add_object(self, subsystem, otype, objid, desc):
        data = {
            "objects":[
                {
                    "subsystem":subsystem,
                    "type":otype,
                    "objid":objid,
                    "desc":desc
                }
            ]
        }
        uri = u'%s/objects/' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add object: %s' % truncate(res))
        #self.result(res)
        print(u'Add object: %s' % res)
        
    def delete_object(self, object_id):
        uri = u'%s/objects/%s/' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete object: %s' % truncate(res))
        #self.result(res)
        print(u'Delete object: %s' % object_id)
    
    #
    # users
    #    
    def get_users(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/users/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get users: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')        
        self.result(res, key=u'users', headers=self.user_headers)
    
    def get_user(self, user_id):
        uri = u'%s/users/%s/' % (self.authuri, user_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get user: %s' % truncate(res))
        self.result(res, key=u'user', headers=self.user_headers)
        
    def add_user(self, subsystem, otype, objid, desc):
        '''data = {
           "user":{
              "name":,
              "storetype":,
              "systype":,
              "active":..,
              "password":..,
              "desc":"",
              "attribute":"",
              "system":"",
              "generic":..
           }
        }'''
        data = None
        uri = u'%s/users/' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add user: %s' % truncate(res))
        #self.result(res)
        print(u'Add user: %s' % res)

    def update_user(self, name, desc):
        '''data = {
           "user":{
              "name":,
              "storetype":,
              "active":..,
              "password":..,
              "desc":"",
              "roles":{
                  "append":[],
                  "remove":[]
              }
           }
        }'''
        data = None
        uri = u'%s/users/' % (self.authuri)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user: %s' % truncate(res))
        #self.result(res)
        print(u'Add user: %s' % res)

    def delete_user(self, user_id):
        uri = u'%s/users/%s/' % (self.authuri, user_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete user: %s' % truncate(res))
        #self.result(res)
        print(u'Delete user: %s' % user_id)
    
    def add_user_role(self, oid, role):
        data = {
            "user":{
                "roles":{
                    "append":[
                        role
                    ],
                    "remove":[]
                },
            }
        }
        uri = u'%s/users/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user roles: %s' % truncate(res))
        #self.result(res)
        print(u'Update user roles: %s' % res)

    def delete_user_role(self, oid, role):
        data = {
            "user":{
                "roles":{
                    "append":[],
                    "remove":[
                        role
                    ]
                },
            }
        }
        uri = u'%s/users/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user roles: %s' % truncate(res))
        #self.result(res)
        print(u'Update user roles: %s' % res)    
    
    #
    # roles
    #    
    def get_roles(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/roles/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get roles: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')        
        self.result(res, key=u'roles', headers=self.role_headers)
    
    def get_role(self, role_id):
        uri = u'%s/roles/%s/' % (self.authuri, role_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get role: %s' % truncate(res))
        self.result(res, key=u'role', headers=self.role_headers)
        
    def add_role(self, name, desc):
        data = {
            "role":{
                "name":name,
                "desc":desc
            }
        }
        uri = u'%s/roles/' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add role: %s' % truncate(res))
        #self.result(res)
        print(u'Add role: %s' % res)

    def update_role(self, oid, *args):
        params = self.get_query_params(*args)
        data = {
            "role":{
                "name":params.get(u'name', None),
                "desc":params.get(u'desc', None)
            }
        }
        uri = u'%s/roles/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role: %s' % truncate(res))
        #self.result(res)
        print(u'Update role: %s' % res)

    def add_role_perm(self, oid, subsystem, ptype, objid, action):
        data = {
            "role":{
                "perms":{
                    "append":[
                        (0, 0, subsystem, ptype, objid, 0, action)
                    ],
                    "remove":[]
                }
            }
        }
        uri = u'%s/roles/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role perms: %s' % truncate(res))
        #self.result(res)
        print(u'Update role: %s' % res)
        
    def delete_role_perm(self, oid, subsystem, ptype, objid, action):
        data = {
            "role":{
                "perms":{
                    "append":[],
                    "remove":[
                        (0, 0, subsystem, ptype, objid, 0, action)                        
                    ]
                }
            }
        }
        uri = u'%s/roles/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role perms: %s' % truncate(res))
        #self.result(res)
        print(u'Update role: %s' % res)

    def delete_role(self, role_id):
        uri = u'%s/roles/%s/' % (self.authuri, role_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete role: %s' % truncate(res))
        #self.result(res)
        print(u'Delete role: %s' % role_id)
        
    #
    # groups
    #    
    def get_groups(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/groups/' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get groups: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))
        print(u'')        
        self.result(res, key=u'groups', headers=self.group_headers)
    
    def get_group(self, group_id):
        uri = u'%s/groups/%s/' % (self.authuri, group_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get group: %s' % truncate(res))
        self.result(res, key=u'group', headers=self.group_headers)
        
    def add_group(self, name, desc):
        data = {
            "group":{
                "name":name,
                "desc":desc
            }
        }
        uri = u'%s/groups/' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add group: %s' % truncate(res))
        #self.result(res)
        print(u'Add group: %s' % res)

    def update_group(self, oid, *args):
        params = self.get_query_params(*args)
        data = {
            "group":{
                "name":params.get(u'name', None),
                "desc":params.get(u'desc', None)
            }
        }
        uri = u'%s/groups/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group: %s' % truncate(res))
        #self.result(res)
        print(u'Update group: %s' % res)
        
    def add_group_role(self, oid, role):
        data = {
            "group":{
                "roles":{
                    "append":[
                        role
                    ],
                    "remove":[]
                },
            }
        }
        uri = u'%s/groups/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group roles: %s' % truncate(res))
        #self.result(res)
        print(u'Update group roles: %s' % res)

    def delete_group_role(self, oid, role):
        data = {
            "group":{
                "roles":{
                    "append":[],
                    "remove":[
                        role
                    ]
                },
            }
        }
        uri = u'%s/groups/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group roles: %s' % truncate(res))
        #self.result(res)
        print(u'Update group roles: %s' % res)

    def add_group_user(self, oid, user):
        data = {
            "group":{
                "users":{
                    "append":[
                        user
                    ],
                    "remove":[]
                },
            }
        }
        uri = u'%s/groups/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group users: %s' % truncate(res))
        #self.result(res)
        print(u'Update group users: %s' % res)

    def delete_group_user(self, oid, user):
        data = {
            "group":{
                "users":{
                    "append":[],
                    "remove":[
                        user
                    ]
                },
            }
        }
        uri = u'%s/groups/%s/' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group users: %s' % truncate(res))
        #self.result(res)
        print(u'Update group users: %s' % res)

    def delete_group(self, group_id):
        uri = u'%s/groups/%s/' % (self.authuri, group_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete group: %s' % truncate(res))
        #self.result(res)
        print(u'Delete group: %s' % group_id)
    
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


        
        
        
        