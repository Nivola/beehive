'''
Created on Sep 22, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match

logger = logging.getLogger(__name__)

class AuthController(BaseController):
    class Meta:
        label = 'auth'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Authorization management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Authorization management", hide=True)
    def default(self):
        self.app.args.print_help()
        
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
        
class AuthControllerChild(ApiController):
    baseuri = u'/v1.0/keyauth'
    simplehttp_uri = u'/v1.0/simplehttp'
    authuri = u'/v1.0/auth'
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
        stacked_on = 'auth'
        stacked_type = 'nested'
        
class DomainController(AuthControllerChild):    
    class Meta:
        label = 'domains'
        description = "Domain management"
        
    @expose(help="Domain management", hide=True)
    def default(self):
        self.app.args.print_help()
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all domains       
        """
        uri = u'%s/domains' % (self.authuri)
        res = self._call(uri, u'GET')
        logger.info(u'Get domains: %s' % res)
        self.result(res, key=u'domains', headers=[u'type', u'name'])      
        
class TokenController(AuthControllerChild):    
    class Meta:
        label = 'tokens'
        description = "Token management"
        
    @expose(help="Token management", hide=True)
    def default(self):
        self.app.args.print_help()
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all tokens       
        """
        #data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/tokens' % self.authuri        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'tokens', headers=self.token_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get token by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/tokens/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'token', headers=self.token_headers, 
                    details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete token by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/tokens/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete token %s' % value}
        self.result(res, headers=[u'msg'])        
        
class UserController(AuthControllerChild):    
    class Meta:
        label = 'users'
        description = "User management"
        
    @expose(help="User management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'add <name> <password> [<expirydate>=yyyy-mm-dd]'], 
            aliases_only=True)
    def add(self):
        """Add user <name>
        """
        name = self.get_arg(name=u'name')
        pwd = self.get_arg(name=u'pwd')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'user':{ 
                u'name':name,
                u'active':True,
                u'password':pwd, 
                u'desc':u'User %s' % name, 
                u'base':True,
                u'expirydate':params.get(u'expiry_date', None)
            }
        }
        uri = u'%s/users' % self.authuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add user %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-system <name> <password>'], 
            aliases_only=True)
    def add_system(self):
        """Add system user <name>
        """        
        name = self.get_arg(name=u'name')
        pwd = self.get_arg(name=u'pwd')
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
        logger.info(u'Add user: %s' % res)
        self.result({u'msg':u'Add user: %s' % res[u'uuid']})

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all users by field: page, size, order, field, role, group, expirydate
    - field can be: id, objid, uuid, name, description, creation_date, 
    modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/users' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'users', headers=self.user_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get user by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'user', headers=self.user_headers, 
                    details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>] '\
                     u'[password=<password>] [active=<active>]'], aliases_only=True)
    def update(self):
        """Update user with new value
        """
        value = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
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
        uri = u'%s/users/%s' % (self.authuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update user %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete user
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s' % (self.authuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete user %s' % value}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'add-role <id> <role> <expirydate>'], aliases_only=True)
    def add_role(self):
        """Add role to user
    - expirydate syntax: yyyy-mm-dd
        """
        oid = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')
        expiry = self.get_arg(name=u'expiry')
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
        logger.info(u'Update user roles: %s' % res)
        self.result({u'msg':u'Add user role: %s' % res[u'role_append']})

    @expose(aliases=[u'delete-role <id> <role>'], aliases_only=True)
    def delete_role(self):
        """Remove role from user
    - expirydate syntax: yyyy-mm-dd
        """
        oid = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')        
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
        logger.info(u'Update user roles: %s' % res)
        self.result({u'msg':u'Add user role: %s' % res[u'role_remove']})  
    
    @expose(aliases=[u'attribs <id>'], aliases_only=True)
    def attribs(self):
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s/attributes' % (self.authuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get user attributes: %s' % res)
        self.result(res, key=u'user_attributes', 
                    headers=[u'name', u'value', u'desc'])    
    
    @expose(aliases=[u'add-attrib <id> <attrib> <value> <desc>'], 
            aliases_only=True)
    def add_attrib(self):
        oid = self.get_arg(name=u'id')
        attrib = self.get_arg(name=u'attrib')
        value = self.get_arg(name=u'value')
        desc = self.get_arg(name=u'desc')
        data = {
            u'user_attribute':{
                u'name':attrib,
                u'value':value,
                u'desc':desc
            }
        }
        uri = u'%s/users/%s/attributes' % (self.authuri, oid)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Add/update user attrib %s' % attrib})     
    
    @expose(aliases=[u'delete-attrib <id> <attrib>'], aliases_only=True)
    def delete_attrib(self):
        oid = self.get_arg(name=u'id')
        attrib = self.get_arg(name=u'attrib')
        uri = u'%s/users/%s/attributes/%s' % (self.authuri, oid, attrib)
        res = self._call(uri, u'dELETE', data=u'')
        logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Delete user attrib %s' % attrib})        
        
class RoleController(AuthControllerChild):    
    class Meta:
        label = 'roles'
        description = "Role management"
        
    @expose(help="Role management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'add <name> <desc>'], 
            aliases_only=True)
    def add(self):
        """Add role <name>
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc')
        data = {
            u'role':{
                u'name':name,
                u'desc':desc
            }
        }
        uri = u'%s/roles' % self.authuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add role %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all roles by field: page, size, order, field, role, group, expirydate
    - field can be: id, objid, uuid, name, description, creation_date, 
    modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/roles' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'roles', headers=self.role_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get role by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/roles/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'role', headers=self.role_headers, 
                    details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>]'], aliases_only=True)
    def update(self):
        """Update role with new name or desc
        """
        value = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'role':{
                u'name':params.get(u'name', None),
                u'desc':params.get(u'desc', None)
            }
        }
        uri = u'%s/roles/%s' % (self.authuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update role %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete role
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/roles/%s' % (self.authuri, value)        
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete role %s' % value}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'add-perm <id> <permid>'], aliases_only=True)
    def add_perm(self):
        roleid = self.get_arg(name=u'id')
        permid = self.get_arg(name=u'permid')
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
        logger.info(u'Update role perms: %s' % res)
        self.result({u'msg':u'Add role perms: %s' % res[u'perm_append']})
    
    @expose(aliases=[u'delete-perm <id> <permid>'], aliases_only=True)
    def delete_perm(self):
        roleid = self.get_arg(name=u'id')
        permid = self.get_arg(name=u'permid')        
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
        logger.info(u'Update role perms: %s' % res)
        self.result({u'msg':u'Remove role perms: %s' % res[u'perm_remove']})        
        
class GroupController(AuthControllerChild):    
    class Meta:
        label = 'groups'
        description = "Group management"
        
    @expose(help="Group management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'add <name> <desc> [<expirydate>=yyyy-mm-dd]'], 
            aliases_only=True)
    def add(self):
        """Add group <name>
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc')
        expiry_date = self.get_arg(name=u'expiry_date')
        data = {
            u'group':{ 
                u'name':name,
                u'desc':desc,
                u'active':True,
                u'expirydate':expiry_date
            }
        }
        uri = u'%s/groups' % self.authuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add group %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [filter=..]'], aliases_only=True)
    def list(self):
        """List all groups by filter: page, size, order, field, role, user
    - field can be: id, objid, uuid, name, description, creation_date, modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/groups' % self.authuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'groups', headers=self.group_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get group by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/groups/%s' % (self.authuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'group', headers=self.group_headers, 
                    details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>]  [active=<active>]'], 
            aliases_only=True)
    def update(self):
        """Update group with new value
        """
        value = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'group':{
                u'name':params.get(u'name', None),
                u'desc':params.get(u'desc', None),
                u'active':params.get(u'active', None),
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update group %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete group
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/groups/%s' % (self.authuri, value)        
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete group %s' % value}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'add-role <id> <role> <expirydate>'], aliases_only=True)
    def add_role(self):
        """Add role to group
    - expirydate syntax: yyyy-mm-dd
        """
        oid = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')
        expiry = self.get_arg(name=u'expiry')
        data = {
            u'group':{
                u'roles':{
                    u'append':[(role, expiry)],
                    u'remove':[]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Add group role: %s' % res[u'role_append']})

    @expose(aliases=[u'delete-role <id> <role>'], aliases_only=True)
    def delete_role(self):
        """Remove role from group
    - expirydate syntax: yyyy-mm-dd
        """
        oid = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')        
        data = {
            u'group':{
                u'roles':{
                    u'append':[],
                    u'remove':[role]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Add group role: %s' % res[u'role_remove']})  
        
    @expose(aliases=[u'add-user <id> <user>'], aliases_only=True)
    def add_user(self):
        """Add user to group
        """
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        expiry = self.get_arg(name=u'expiry')
        data = {
            u'group':{
                u'users':{
                    u'append':[
                        user
                    ],
                    u'remove':[]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group users: %s' % res)
        self.result({u'msg':u'Add group user: %s' % res[u'user_append']})

    @expose(aliases=[u'delete-user <id> <user>'], aliases_only=True)
    def delete_user(self):
        """Remove user from group
        """
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')        
        data = {
            u'group':{
                u'users':{
                    u'append':[],
                    u'remove':[
                        user
                    ]
                },
            }
        }
        uri = u'%s/groups/%s' % (self.authuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group users: %s' % res)
        self.result({u'msg':u'Add group user: %s' % res[u'user_remove']})          
        
class ObjectController(AuthControllerChild):    
    class Meta:
        label = 'objects'
        description = "Object management"
        
    @expose(help="Object management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    #
    # actions
    #
    @expose
    def actions(self):
        """List object actions
        """
        uri = u'%s/objects/actions' % (self.authuri)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object_actions', headers=self.act_headers)     
    
    #
    # perms
    #
    @expose(aliases=[u'perms [<filter=..>]'], aliases_only=True)    
    def perms(self):
        """Get permissions. Filter by: page, size, order, field, subsystem, 
    type, objid. field can be: subsystem, type, id, action
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects/perms' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    @expose(aliases=[u'perm <id>'], 
            aliases_only=True)    
    def perm(self):
        """Get permission by id
        """
        perm_id = self.get_arg(name=u'id')
        uri = u'%s/objects/perms/%s' % (self.authuri, perm_id)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object perm: %s' % res)
        self.result(res, key=u'perm', headers=self.perm_headers, details=True)    
    
    #
    # object types
    #
    @expose(aliases=[u'types [<filter=..>]'], aliases_only=True)  
    def types(self):
        """Get object types. Filter by: page, size, order, field, subsystem, type
    field can be: subsystem, type, id
        """        
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects/types' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'object_types', headers=self.type_headers)

    @expose(aliases=[u'add-type <subsystem> <type>'], aliases_only=True)  
    def add_type(self):
        subsystem = self.get_arg(name=u'subsystem')
        otype = self.get_arg(name=u'type')
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
        logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object type: %s' % (res)})
    
    @expose(aliases=[u'delete-type <id>'], aliases_only=True)  
    def delete_type(self):
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/types/%s' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object type %s' % (object_id)})   
    
    #
    # objects
    #
    @expose(aliases=[u'list [<filter=..>]'], aliases_only=True) 
    def list(self):
        """Get objects. Filter by: page, size, order, field, subsystem, type, 
    objid. field can be: subsystem, type, id, objid
        """                
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects' % (self.authuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'objects', headers=self.obj_headers, maxsize=200)
    
    @expose(aliases=[u'get <id>'], aliases_only=True) 
    def get(self):
        """Get object
        """
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/%s' % (self.authuri, object_id)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object', headers=self.obj_headers, details=True)
    
    @expose(aliases=[u'add <subsystem> <type> "<objid>" "<desc>"'],
                     aliases_only=True) 
    def add(self):
        """Add object
        """
        subsystem = self.get_arg(name=u'subsystem')
        otype = self.get_arg(name=u'otype')
        objid = self.get_arg(name=u'objid')
        desc = self.get_arg(name=u'desc')
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
        logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object: %s' % (res)})
    
    @expose(aliases=[u'delete <id>'], aliases_only=True) 
    def delete(self):
        """Delete object
        """
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/%s' % (self.authuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object %s' % (object_id)})
        
auth_controller_handlers = [
    AuthController,
    DomainController,
    TokenController,
    UserController,
    RoleController,
    GroupController,
    ObjectController
]                
        
        