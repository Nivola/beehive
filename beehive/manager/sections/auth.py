"""
Created on Sep 22, 2017

@author: darkbk
"""
import binascii
import logging
import sh
from datetime import datetime, timedelta
import jwt
from cement.core.controller import expose
from requests_oauthlib import OAuth2Session

from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beehive.manager.sections.scheduler import WorkerController, ScheduleController, TaskController

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


class AuthControllerChild(ApiController):
    # baseuri = u'/v1.0/nas/keyauth'
    # simplehttp_uri = u'/v1.0/nas/simplehttp'
    baseuri = u'/v1.0/nas'
    subsystem = u'auth'
    
    obj_headers = [u'id', u'objid', u'subsystem', u'type', u'desc']
    type_headers = [u'id', u'subsystem', u'type']
    act_headers = [u'id', u'value']
    perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', u'aid', u'action']
    user_headers = [u'id', u'uuid', u'name', u'desc', u'active', u'date.creation', u'date.modified', u'date.expiry']
    role_headers = [u'id', u'uuid', u'name', u'desc', u'active', u'date.creation', u'date.modified', u'date.expiry']
    group_headers = [u'id', u'uuid', u'name', u'desc', u'active', u'date.creation', u'date.modified', u'date.expiry']
    token_headers = [u'token', u'type', u'user', u'ip', u'ttl', u'timestamp']
    
    class Meta:
        stacked_on = 'auth'
        stacked_type = 'nested'


class AuthWorkerController(AuthControllerChild, WorkerController):
    class Meta:
        label = 'auth.workers'
        aliases = ['workers']
        aliases_only = True
        description = "Worker management"


class AuthTaskController(AuthControllerChild, TaskController):
    class Meta:
        label = 'auth.tasks'
        aliases = ['tasks']
        aliases_only = True
        description = "Task management"


class AuthScheduleController(AuthControllerChild, ScheduleController):
    class Meta:
        label = 'auth.schedules'
        aliases = ['schedules']
        aliases_only = True
        description = "Schedule management"
        

class DomainController(AuthControllerChild):
    class Meta:
        label = 'domains'
        description = "Domain management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all domains       
        """
        uri = u'%s/domains' % (self.baseuri)
        res = self._call(uri, u'GET')
        logger.info(u'Get domains: %s' % res)
        self.result(res, key=u'domains', headers=[u'type', u'name'])      


class TokenController(AuthControllerChild):
    class Meta:
        label = 'tokens'
        description = "Token management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all tokens       
        """
        # data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/tokens' % self.baseuri        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'tokens', headers=self.token_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get token by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/tokens/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'token', headers=self.token_headers, 
                    details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete token by id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/tokens/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete token %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'create [user=..] [pwd=..] [login-ip=..] [client=..] [type=..] [sub=..]'], aliases_only=True)
    @check_error
    def create(self):
        """Create keyauth or oauth2 jwt token
    - type: can be keyauth, oauth2, simplehttp. [dafault=keyauth]
        - oauth2: create a token using a jwt oauth2 client

    Ex.
        create client-id=client1 type=oauth2 sub=client1
        """
        user = self.get_arg(name=u'user', default=None, keyvalue=True)
        pwd = self.get_arg(name=u'pwd', default=None, keyvalue=True)
        client_id = self.get_arg(name=u'client', default=None, keyvalue=True)
        login_ip = self.get_arg(name=u'login-ip', default=sh.hostname().stdout.rstrip(), keyvalue=True)
        auth_type = self.get_arg(name=u'type', default=u'keyauth', keyvalue=True)
        sub = self.get_arg(name=u'sub', default=None, keyvalue=True)

        if auth_type == u'keyauth':
            data = {u'user': user, u'password': pwd, u'login-ip': login_ip}
            res = self.client.send_request(u'auth', u'/v1.0/nas/keyauth/token', u'POST', data=data)
            token = res[u'access_token']
        elif auth_type == u'oauth2':
            try:
                from beehive_oauth2.jwtgrant import JWTClient
            except:
                raise Exception(u'JWTClient can not be imported')

            # get client
            uri = u'/v1.0/oauth2/clients/%s' % client_id
            client = self._call(uri, u'GET').get(u'client')

            client_id = client[u'uuid']
            client_email = client[u'client_email']
            client_scope = client[u'scopes']
            private_key = binascii.a2b_base64(client[u'private_key'])
            client_token_uri = client[u'token_uri']

            client = JWTClient(client_id=client_id)
            oauth = OAuth2Session(client=client)

            now = datetime.utcnow()
            claims = {
                u'iss': client_email,
                u'aud': client_token_uri,
                u'exp': now + timedelta(seconds=60),
                u'iat': now,
                u'nbf': now
            }
            if sub is not None:
                claims[u'sub'] = sub
            # priv_key = RSA.importKey(private_key)
            encoded = jwt.encode(claims, private_key, algorithm=u'RS512')
            res = client.prepare_request_body(assertion=encoded, client_id=client_id, scope=client_scope)
            token = oauth.fetch_token(token_url=client_token_uri, body=res, verify=False)

            # client_id = self.api_client_config[u'uuid']
            # client_email = self.api_client_config[u'client_email']
            # client_scope = self.api_client_config[u'scopes']
            # private_key = binascii.a2b_base64(self.api_client_config[u'private_key'])
            # client_token_uri = u'%s/v1.0/oauth2/token' % self.main_endpoint
            # aud = self.api_client_config[u'aud']
            #
            # res = JWTClient.create_token(client_id, client_email, client_scope, private_key, client_token_uri, aud,
            #                              api_user, api_user_pwd)
            # self.uid = res[u'access_token']

        logger.debug(u'Get %s token: %s' % (auth_type, token))
        res = {u'msg': u'Get token %s' % token}
        self.result(res, headers=[u'msg'], maxsize=200)


class UserController(AuthControllerChild):
    class Meta:
        label = 'users'
        description = "User management"
        
    @expose(aliases=[u'add <name> [password=..] [storetype=..] [expirydate=yyyy-mm-dd]'], aliases_only=True)
    @check_error
    def add(self):
        """Add user <name>
    - storetype: can be DBUSER, LDAPUSER
        """
        name = self.get_arg(name=u'name')
        pwd = self.get_arg(name=u'password', default=None, keyvalue=True)
        storetype = self.get_arg(name=u'storetype', default=u'DBUSER', keyvalue=True)
        expirydate = self.get_arg(name=u'expirydate', default=None, keyvalue=True)
        data = {
            u'user': {
                u'name': name,
                u'active': True,
                u'desc': u'User %s' % name,
                u'base': True,
                u'storetype': storetype,
                u'expiry_date': expirydate
            }
        }
        if pwd is not None:
            data[u'user'][u'password'] = pwd
        uri = u'%s/users' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg': u'Add user %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-system <name> <password>'], aliases_only=True)
    @check_error
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
        uri = u'%s/users' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add user: %s' % res)
        self.result({u'msg':u'Add user: %s' % res[u'uuid']}, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all users by field: page, size, order, field, role, group, expirydate
    - field can be: id, objid, uuid, name, description, creation_date, 
    modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/users' % self.baseuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'users', headers=self.user_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get user by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'user', headers=self.user_headers, details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>] [password=<password>] [active=<active>]'],
            aliases_only=True)
    @check_error
    def update(self):
        """Update user with new value
        """
        value = self.get_arg(name=u'id')
        params = self.app.kvargs
        name = params.get(u'name', None)
        if name is not None and not match(u'[a-zA-z0-9]+@[a-zA-z0-9]+', name):
            raise Exception(u'Name is not correct. Name syntax is <name>@<domain>')
        data = {
            u'user': {
                u'name': name,
                u'desc': params.get(u'desc', None),
                u'active': params.get(u'active', None),
                u'password': params.get(u'password', None),
                u'expirydate': params.get(u'expiry_date', None)
            }
        }
        uri = u'%s/users/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update user %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete user
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete user %s' % value}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'add-role <id> <role> <expirydate>'], aliases_only=True)
    @check_error
    def add_role(self):
        """Add role to user
    - expirydate syntax: yyyy-mm-dd
        """
        oid = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')
        expiry = self.get_arg(name=u'expiry')
        data = {
            u'user': {
                u'roles': {
                    u'append': [(role, expiry)],
                    u'remove': []
                },
            }
        }
        uri = u'%s/users/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update user roles: %s' % res)
        self.result({u'msg': u'Add user role: %s' % res[u'role_append']}, headers=[u'msg'])

    @expose(aliases=[u'del-role <id> <role>'], aliases_only=True)
    @check_error
    def del_role(self):
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
        uri = u'%s/users/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update user roles: %s' % res)
        self.result({u'msg':u'Add user role: %s' % res[u'role_remove']}, headers=[u'msg'])
    
    @expose(aliases=[u'attribs <id>'], aliases_only=True)
    @check_error
    def attribs(self):
        value = self.get_arg(name=u'id')
        uri = u'%s/users/%s/attributes' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get user attributes: %s' % res)
        self.result(res, key=u'user_attributes', 
                    headers=[u'name', u'value', u'desc'])    
    
    @expose(aliases=[u'add-attrib <id> <attrib> <value> <desc>'], aliases_only=True)
    @check_error
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
        uri = u'%s/users/%s/attributes' % (self.baseuri, oid)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Add/update user attrib %s' % attrib}, headers=[u'msg'])
    
    @expose(aliases=[u'delete-attrib <id> <attrib>'], aliases_only=True)
    @check_error
    def delete_attrib(self):
        oid = self.get_arg(name=u'id')
        attrib = self.get_arg(name=u'attrib')
        uri = u'%s/users/%s/attributes/%s' % (self.baseuri, oid, attrib)
        res = self._call(uri, u'dELETE', data=u'')
        logger.info(u'Add user attribute: %s' % res)
        self.result({u'msg':u'Delete user attrib %s' % attrib}, headers=[u'msg'])


class RoleController(AuthControllerChild):
    class Meta:
        label = 'roles'
        description = "Role management"
        
    @expose(aliases=[u'add <name> <desc>'], aliases_only=True)
    @check_error
    def add(self):
        """Add role <name>
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc')
        data = {
            u'role': {
                u'name': name,
                u'desc': desc
            }
        }
        uri = u'%s/roles' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add role %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all roles by field: page, size, order, field, role, group, expirydate
    - field can be: id, objid, uuid, name, description, creation_date, 
    modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/roles' % self.baseuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'roles', headers=self.role_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get role by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/roles/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'role', headers=self.role_headers, details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>]'], aliases_only=True)
    @check_error
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
        uri = u'%s/roles/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update role %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete role
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/roles/%s' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete role %s' % value}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'add-perm <id> <permid>'], aliases_only=True)
    @check_error
    def add_perm(self):
        roleid = self.get_arg(name=u'id')
        permid = self.get_arg(name=u'permid')
        data = {
            u'role': {
                u'perms': {
                    u'append': [{u'id':permid}],
                    u'remove': []
                }
            }
        }
        uri = u'%s/roles/%s' % (self.baseuri, roleid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update role perms: %s' % res)
        self.result({u'msg': u'Add role perms: %s' % res[u'perm_append']}, headers=[u'msg'])
    
    @expose(aliases=[u'delete-perm <id> <permid>'], aliases_only=True)
    @check_error
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
        uri = u'%s/roles/%s' % (self.baseuri, roleid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update role perms: %s' % res)
        self.result({u'msg':u'Remove role perms: %s' % res[u'perm_remove']}, headers=[u'msg'])


class GroupController(AuthControllerChild):
    class Meta:
        label = 'groups'
        description = "Group management"
        
    @expose(aliases=[u'add <name> <desc> [<expirydate>=yyyy-mm-dd]'], aliases_only=True)
    @check_error
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
        uri = u'%s/groups' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add group %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [filter=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all groups by filter: page, size, order, field, role, user
    - field can be: id, objid, uuid, name, description, creation_date, modification_date, expiry_date, active
    - expirydate syntax: yyyy-mm-dd        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/groups' % self.baseuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'groups', headers=self.group_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get group by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/groups/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'group', headers=self.group_headers, 
                    details=True)
    
    @expose(aliases=[u'update <id> [name=<name>] [desc=<desc>]  [active=<active>]'], aliases_only=True)
    @check_error
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
        uri = u'%s/groups/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update group %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete group
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/groups/%s' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete group %s' % value}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'add-role <id> <role> <expirydate>'], aliases_only=True)
    @check_error
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
        uri = u'%s/groups/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Add group role: %s' % res[u'role_append']}, headers=[u'msg'])

    @expose(aliases=[u'del-role <id> <role>'], aliases_only=True)
    @check_error
    def del_role(self):
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
        uri = u'%s/groups/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group roles: %s' % res)
        self.result({u'msg':u'Add group role: %s' % res[u'role_remove']}, headers=[u'msg'])
        
    @expose(aliases=[u'add-user <id> <user>'], aliases_only=True)
    @check_error
    def add_user(self):
        """Add user to group
        """
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        expiry = self.get_arg(name=u'expiry')
        data = {
            u'group': {
                u'users': {
                    u'append': [
                        user
                    ],
                    u'remove': []
                },
            }
        }
        uri = u'%s/groups/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group users: %s' % res)
        self.result({u'msg': u'Add group user: %s' % res[u'user_append']}, headers=[u'msg'])

    @expose(aliases=[u'delete-user <id> <user>'], aliases_only=True)
    @check_error
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
        uri = u'%s/groups/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Update group users: %s' % res)
        self.result({u'msg':u'Add group user: %s' % res[u'user_remove']}, headers=[u'msg'])


class ObjectController(AuthControllerChild):
    class Meta:
        label = 'objects'
        description = "Object management"

    #
    # actions
    #
    @expose()
    @check_error
    def actions(self):
        """List object actions
        """
        uri = u'%s/objects/actions' % (self.baseuri)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object_actions', headers=self.act_headers)     
    
    #
    # perms
    #
    @expose(aliases=[u'perms [<filter=..>]'], aliases_only=True)
    @check_error
    def perms(self):
        """Get permissions. Filter by: page, size, order, field, subsystem, 
    type, objid. field can be: subsystem, type, id, action
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects/perms' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers, maxsize=200)
    
    @expose(aliases=[u'perm <id>'], aliases_only=True)
    @check_error
    def perm(self):
        """Get permission by id
        """
        perm_id = self.get_arg(name=u'id')
        uri = u'%s/objects/perms/%s' % (self.baseuri, perm_id)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object perm: %s' % res)
        self.result(res, key=u'perm', headers=self.perm_headers, details=True)    
    
    #
    # object types
    #
    @expose(aliases=[u'types [<filter=..>]'], aliases_only=True)
    @check_error
    def types(self):
        """Get object types. Filter by: page, size, order, field, subsystem, type
    field can be: subsystem, type, id
        """        
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects/types' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'object_types', headers=self.type_headers, maxsize=200)

    @expose(aliases=[u'add-type <subsystem> <type>'], aliases_only=True)
    @check_error
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
        uri = u'%s/objects/types' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object type: %s' % (res)}, headers=[u'msg'])
    
    @expose(aliases=[u'delete-type <id>'], aliases_only=True)
    @check_error
    def delete_type(self):
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/types/%s' % (self.baseuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object type %s' % (object_id)}, headers=[u'msg'])
    
    #
    # objects
    #
    @expose(aliases=[u'list [<filter=..>]'], aliases_only=True)
    @check_error
    def list(self):
        """Get objects. Filter by: page, size, order, field, subsystem, type, 
    objid. field can be: subsystem, type, id, objid
        """                
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/objects' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get objects: %s' % res)
        self.result(res, key=u'objects', headers=self.obj_headers, maxsize=200)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get object
        """
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/%s' % (self.baseuri, object_id)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get object: %s' % res)
        self.result(res, key=u'object', headers=self.obj_headers, details=True)
    
    @expose(aliases=[u'add <subsystem> <type> "<objid>" "<desc>"'], aliases_only=True)
    @check_error
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
        uri = u'%s/objects' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add object: %s' % res)
        self.result({u'msg':u'Add object: %s' % (res)}, headers=[u'msg'])
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete object
        """
        object_id = self.get_arg(name=u'id')
        uri = u'%s/objects/%s' % (self.baseuri, object_id)
        res = self._call(uri, u'DELETE', data=u'')
        logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete object %s' % (object_id)}, headers=[u'msg'])
        
    @expose(aliases=[u'deletes <id1,id2,..>'], aliases_only=True)
    @check_error
    def deletes(self):
        """Delete objects
        """
        object_ids = self.get_arg(name=u'ids').split(u',')
        
        for object_id in object_ids:
            uri = u'%s/objects/%s' % (self.baseuri, object_id)
            res = self._call(uri, u'DELETE', data=u'')
            logger.info(u'Delete object: %s' % res)
        self.result({u'msg':u'Delete objects %s' % (object_ids)}, headers=[u'msg'])


auth_controller_handlers = [
    AuthController,
    DomainController,
    TokenController,
    UserController,
    RoleController,
    GroupController,
    ObjectController,
    AuthWorkerController,
    AuthScheduleController,
    AuthTaskController
]                
