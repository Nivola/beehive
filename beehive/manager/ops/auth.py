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
from re import match

logger = logging.getLogger(__name__)

class AuthManager(ApiManager):
    """
    SECTION: 
        auth
        
    PARAMS:
        sessions list
    
        simplehttp domains
        simplehttp login <name>@<domain> <password> <user-ip>        
        
        domains list
        
        tokens list
        tokens get <token>
        tokens delete <token>
        
        users list <field>=<value>    field: page, size, order, field, role, group, expirydate
            field can be: id, objid, uuid, name, description, creation_date, modification_date, expiry_date, active
            expirydate syntax: dd-mm-yyyy
            
            Ex. page=2 order=ASC field=name
        users get <id>
        users add <name> <password> [<expirydate>=dd-mm-yyyy] [<storetype> default=u'DBUSER']
        users add-admin <name> <password>
        users update <id> [name=<name>] [desc=<desc>] [password=<password>] [active=<active>]
        users delete <id>
        users add-role <id> <role> <expirydate>    expirydate syntax: dd-mm-yyyy
        users delete-role <id> <role>
        users attribs <id>
        users attrib-add <id> <name> <value> <desc>
        users attrib-delete <id> <attrib>        
        
        roles list <field>=<value>    field: page, size, order, field, user, group
            field can be: id, objid, uuid, name, description, creation_date, modification_date, expiry_date, active
            
            Ex. page=2 order=ASC field=name
        roles get <id>
        roles add <name> <desc>
        roles update <id> [name=<name>] [desc=<desc>]
        roles delete <id>
        roles add-perm <id> <subsystem> <ptype> <objid> <action>
        roles delete-perm <id> <subsystem> <ptype> <objid> <action>        
        
        groups list <field>=<value>    field: page, size, order, field, role, user
            field can be: id, objid, uuid, name, description, creation_date, modification_date, expiry_date, active
            
            Ex. page=2 order=ASC field=name
        groups get <id>
        groups add <name> <desc> [<expirydate>=dd-mm-yyyy]
        groups update <id> [name=<name>] [desc=<desc>] [active=<active>]
        groups delete <id>
        groups add-role <id> <role> <expirydate>    expirydate syntax: dd-mm-yyyy
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
        self.simplehttp_uri = u'/v1.0/simplehttp'
        self.authuri = u'/v1.0/auth'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.obj_headers = [u'id', u'objid', u'subsystem', u'type', u'desc']
        self.type_headers = [u'id', u'subsystem', u'type']
        self.act_headers = [u'id', u'value']
        self.perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', 
                             u'aid', u'action']
        self.user_headers = [u'id', u'uuid', u'name', u'active', 
                             u'date.creation', u'date.modified', u'date.expiry']
        self.role_headers = [u'id', u'uuid', u'name', u'active', 
                             u'date.creation', u'date.modified', u'date.expiry']
        self.group_headers = [u'id', u'uuid', u'name', u'active', 
                              u'date.creation', u'date.modified', u'date.expiry']
    
    def actions(self):
        actions = {
            u'sessions.list': self.get_sessions,        
           

            
            u'simplehttp.login': self.simplehttp_login_user,            
            
            u'tokens.list': self.get_auth_tokens,
            u'tokens.get': self.get_auth_token,
            u'tokens.delete': self.delete_auth_token,
            
            u'domains.list': self.login_domains,
            
            u'users.list': self.get_users,
            u'users.get': self.get_user,
            u'users.add': self.add_user,
            u'users.add-admin': self.add_system_user,
            u'users.update': self.update_user,          
            u'users.delete': self.delete_user,
            u'users.attribs': self.get_user_attribs,
            u'users.attrib-add': self.add_user_attrib,
            u'users.attrib-delete': self.delete_user_attrib,
            u'users.add-role':self.add_user_role,
            u'users.delete-role':self.delete_user_role,
            #u'users.can': self.can_user,
            
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
    # authentication domains
    #
    def login_domains(self):
        uri = u'%s/domains' % (self.authuri)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get domains: %s' % res)
        self.result(res, key=u'domains', headers=[u'type', u'name'])    
    
    #
    # actions
    #        
    def get_actions(self):
        uri = u'%s/objects/actions' % (self.authuri)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object_actions', headers=self.act_headers)     
    
    #
    # perms
    #    
    def get_perms(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects/perms' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    def get_perm(self, perm_id):
        uri = u'%s/objects/perms/%s' % (self.authuri, perm_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object perm: %s' % res)
        self.result(res, key=u'perm', headers=self.perm_headers, details=True)    
    
    #
    # object types
    #    
    def get_object_types(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects/types' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'object_types', headers=self.type_headers)

    def add_object_type(self, subsystem, otype, *args):
        data = {
            u'object_types':[
                {
                    u'subsystem':subsystem,
                    u'type':otype,
                }
            ]
        }
        uri = u'%s/objects/types' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object type: %s' % (res)})
        
    def delete_object_type(self, object_id, *args):
        uri = u'%s/objects/types/%s' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object type %s' % (object_id)})   
    
    #
    # objects
    #    
    def get_objects(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/objects' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'objects', headers=self.obj_headers, maxsize=200)
    
    def get_object(self, object_id):
        uri = u'%s/objects/%s' % (self.authuri, object_id)
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object', headers=self.obj_headers, details=True)
        
    def add_object(self, subsystem, otype, objid, desc):
        data = {
            u'objects':[
                {
                    u'subsystem':subsystem,
                    u'type':otype,
                    u'objid':objid,
                    u'desc':desc
                }
            ]
        }
        uri = u'%s/objects' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object: %s' % (res)})
        
    def delete_object(self, object_id):
        uri = u'%s/objects/%s' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object %s' % (object_id)})
    
    #
    # users
    #    
    def get_users(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/users' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get users: %s' % res)  
        self.result(res, key=u'users', headers=self.user_headers)
    
    def get_user(self, user_id, *args):
        uri = u'%s/users/%s' % (self.authuri, user_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get user: %s' % res)
        self.result(res, key=u'user', headers=self.user_headers, details=True)
        
    def add_user(self, name, pwd, expiry_date=None, *args):
        data = {
            u'user':{ 
                u'name':name,
                u'active':True,
                u'password':pwd, 
                u'desc':u'User %s' % name, 
                u'base':True,
                u'expirydate':expiry_date
            }
        }
        uri = u'%s/users' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add user: %s' % res)
        self.result({u'msg':u'Add user: %s' % res[u'uuid']})
        
    def add_system_user(self, name, pwd, *args):
        data = {
            u'user':{
                u'name':name,
                u'active':True,
                u'password':pwd, 
                u'desc':u'User %s' % name, 
                u'system':True
            }
        }
        uri = u'%s/users' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add user: %s' % res)
        self.result({u'msg':u'Add user: %s' % res[u'uuid']})

    def update_user(self, user_id, *args):
        params = self.get_query_params(*args)
        name = params.get(u'name', None)
        if name is not None and not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', name):
            raise Exception(u'Name is not correct. Name syntax is <name>@<domain>')
        data = {
            u'user':{
                u'name':name,
                u'desc':params.get(u'desc', None),
                u'active':params.get(u'active', None),
                u'password':params.get(u'password', None),
                u'expirydate':params.get(u'expiry_date', None)
            }
        }
        uri = u'%s/users/%s' % (self.authuri, user_id)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user: %s' % res)
        self.result({u'msg':u'Update user %s' % (user_id)})

    def delete_user(self, user_id, *args):
        uri = u'%s/users/%s' % (self.authuri, user_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete user: %s' % res)
        self.result({u'msg':u'Delete user: %s' % user_id})
    
    def add_user_role(self, oid, role, expiry, *args):
        data = {
            u'user':{
                u'roles':{
                    u'append':[(role, expiry)],
                    u'remove':[]
                },
            }
        }
        uri = u'%s/users/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user roles: %s' % res)
        self.result({u'msg':u'Add user role: %s' % res[u'role.append']})

    def delete_user_role(self, oid, role, *args):
        data = {
            u'user':{
                u'roles':{
                    u'append':[],
                    u'remove':[role]
                },
            }
        }
        uri = u'%s/users/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update user roles: %s' % res)
        self.result({u'msg':u'Add user role: %s' % res[u'role.remove']})  
    
    def get_user_attribs(self, user_id, *args):
        uri = u'%s/users/%s/attributes' % (self.authuri, user_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get user attributes: %s' % res)
        self.result(res, key=u'user_attributes', 
                    headers=[u'name', u'value', u'desc'])    
    
    def add_user_attrib(self, oid, name, value, desc, *args):
        data = {
            u'user_attribute':{
                u'name':name,
                u'value':value,
                u'desc':desc
            }
        }
        uri = u'%s/users/%s/attributes' % (self.authuri, oid)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Add/update user attrib %s' % name})     
    
    def delete_user_attrib(self, oid, attrib, *args):
        uri = u'%s/users/%s/attributes/%s' % (self.authuri, oid, attrib)
        res = self._call(uri, u'dELETE', data=u'')
        self.logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Delete user attrib %s' % attrib})
    
    #
    # roles
    #    
    def get_roles(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/roles' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get roles: %s' % res)
        self.result(res, key=u'roles', headers=self.role_headers)
    
    def get_role(self, role_id, *args):
        uri = u'%s/roles/%s' % (self.authuri, role_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get role: %s' % res)
        self.result(res, key=u'role', headers=self.role_headers, details=True)
        
    def add_role(self, name, desc, *args):
        data = {
            u'role':{
                u'name':name,
                u'desc':desc
            }
        }
        uri = u'%s/roles' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add role: %s' % res)
        self.result({u'msg':u'Add role: %s' % res[u'uuid']})

    def update_role(self, role_id, *args):
        params = self.get_query_params(*args)
        data = {
            u'role':{
                u'name':params.get(u'name', None),
                u'desc':params.get(u'desc', None)
            }
        }
        uri = u'%s/roles/%s' % (self.authuri, role_id)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role: %s' % res)
        self.result({u'msg':u'Update role %s' % (role_id)})

    def add_role_perm(self, roleid, permid, *args):
        data = {
            u'role':{
                u'perms':{
                    u'append':[{u'id':permid}],
                    u'remove':[]
                }
            }
        }
        uri = u'%s/roles/%s' % (self.authuri, roleid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role perms: %s' % res)
        self.result({u'msg':u'Add role perms: %s' % res[u'perm.append']})
        
    def delete_role_perm(self, roleid, permid, *args):
        data = {
            u'role':{
                u'perms':{
                    u'append':[],
                    u'remove':[{u'id':permid}]
                }
            }
        }
        uri = u'%s/roles/%s' % (self.authuri, roleid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update role perms: %s' % res)
        self.result({u'msg':u'Remove role perms: %s' % res[u'perm.remove']})

    def delete_role(self, role_id, *args):
        uri = u'%s/roles/%s' % (self.authuri, role_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete role: %s' % res)
        self.result({u'msg':u'Delete role: %s' % role_id})
        
    #
    # groups
    #    
    def get_groups(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/groups' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get groups: %s' % res)
        self.result(res, key=u'groups', headers=self.group_headers)
    
    def get_group(self, group_id):
        uri = u'%s/groups/%s' % (self.authuri, group_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get group: %s' % res)
        self.result(res, key=u'group', headers=self.group_headers, details=True)
        
    def add_group(self, name, desc, expiry_date=None):
        data = {
            u'group':{
                u'name':name,
                u'desc':desc,
                u'active':True,
                u'expirydate':expiry_date
            }
        }
        uri = u'%s/groups' % (self.authuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add group: %s' % res)
        self.result({u'msg':u'Add group %s' % (res[u'uuid'])})

    def update_group(self, oid, *args):
        params = self.get_query_params(*args)
        data = {
            u'group':{
                u'name':params.get(u'name', None),
                u'desc':params.get(u'desc', None),
                u'active':params.get(u'active', None),
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group: %s' % res)
        self.result({u'msg':u'Update group %s' % (oid)})
        
    def add_group_role(self, oid, role):
        data = {
            u'group':{
                "roles":{
                    "append":[
                        role
                    ],
                    "remove":[]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Add group role: %s' % res[u'role.remove']})

    def delete_group_role(self, oid, role):
        data = {
            u'group':{
                "roles":{
                    "append":[],
                    "remove":[
                        role
                    ]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Remove group role: %s' % res[u'role.remove']})

    def add_group_user(self, oid, user):
        data = {
            u'group':{
                "users":{
                    "append":[
                        user
                    ],
                    "remove":[]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group users: %s' % res)
        self.result({u'msg':u'Add group %s user: %s' % (oid, res[u'user.append'])})

    def delete_group_user(self, oid, user):
        data = {
            u'group':{
                "users":{
                    "append":[],
                    "remove":[
                        user
                    ]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update group users: %s' % res)
        self.result({u'msg':u'Remove group %s user: %s' % (oid, res[u'user.delete'])})

    def delete_group(self, group_id):
        uri = u'%s/groups/%s' % (self.authuri, group_id)
        res = self._call(uri, u'DELETE', data=u'')
        self.logger.info(u'Delete group: %s' % res)
        self.result({u'msg':u'Delete group %s' % (group_id)})
    
    #
    # sessions
    #
    def get_sessions(self):
        uri = u'/v1.0/server/sessions'
        res = self._call(uri, u'GET', data=u'')
        self.logger.info(u'Get sessions: %s' % res)
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
        self.logger.info(u'Get domains: %s' % res)
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
        self.logger.info(u'Login user %s: %s' % (user, res))
        self.result(res, headers=[u'user.id', u'uid', u'user.name', u'timestamp',
                                  u'user.active'])
         
    #
    # tokens
    #    
    def get_auth_tokens(self):
        uri = u'%s/tokens' % (self.authuri)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get tokens: %s' % res)
        self.result(res, key=u'tokens', headers=[u'token', u'type', u'user', 
                    u'ip', u'ttl', u'timestamp'])
    
    def get_auth_token(self, oid):
        uri = u'%s/tokens/%s' % (self.authuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get identity: %s' % res)
        self.result(res, key=u'token', headers=[u'token', u'type', u'user', 
                    u'ip', u'ttl', u'timestamp'], details=True)
        
    def delete_auth_token(self, oid):
        uri = u'%s/tokens/%s' % (self.authuri, oid)
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete identity: %s' % res)
        self.result({u'token':oid}, headers=[u'token']) 


        
        
        
        