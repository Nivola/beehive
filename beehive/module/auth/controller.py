'''
Created on Jan 16, 2014

@author: darkbk
'''
from logging import getLogger
import binascii
import pickle
from re import match
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv4Network, AddressValueError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from beecell.auth import extract
from beecell.auth import AuthError
from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate
from socket import gethostbyname
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beecell.db import TransactionError, QueryError
from beehive.common.data import operation
from beehive.common.authorization import AuthDbManager

class AuthenticationManager(object):
    """Manager used to login and logout user on authentication provider.
    
    """
    def __init__(self, auth_providers):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)        
        
        self.auth_providers = auth_providers

    def __str__(self):
        return "<AuthenticationManager id:%s>" % id(self)

    @watch
    def login(self, username, password, domain, ipaddr):
        """Login user using ldap server.
        
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug(u'Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug(u'Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error(u'Authentication domain %s does not exist' % domain)
            raise AuthError(u'', u'Authentication domain %s does not exist' % domain, 
                            code=10)
        
        # login over authentication provider and get user attributes
        username = u'%s@%s' % (username, domain)

        auth_user = auth_provider.login(username, password)

        # set user ip address
        auth_user.current_login_ip = ipaddr
        
        self.logger.debug(u'Login user: %s' % (username))
        return auth_user
    
    @watch
    def refresh(self, uid, username, domain):
        """Refresh user.
        
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug(u'Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug(u'Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error(u'Authentication domain %s does not exist' % domain)
            raise AuthError(u'', u'Authentication domain %s does not exist' % domain, 
                            code=10)
        
        # login over authentication provider and get user attributes
        username = u'%s@%s' % (username, domain)
        auth_user = auth_provider.refresh(username, uid)
        
        self.logger.debug(u'Login user: %s' % (username))
        return auth_user    

class AuthController(ApiController):
    """Auth Module controller.
    
    :param module: Beehive module
    """
    version = u'v1.0'    
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.dbauth = AuthDbManager()
        self.objects = Objects(self)
        
        self.child_classes = [Objects, Role, User, Group]
    
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        # add actions
        try:
            actions = [u'*', u'view', u'insert', u'update', u'delete', u'use']
            self.dbauth.add_object_actions(actions)
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
        # init container
        for child in self.child_classes:
            child(self).init_object()
    
    def set_superadmin_permissions(self):
        """ """
        try:
            self.set_admin_permissions(u'ApiSuperadmin', [])
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    def set_admin_permissions(self, role_name, args):
        """ """
        try:
            for item in self.child_classes:
                item(self).set_admin_permissions(role_name, args)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.
        
        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        :raise ApiManagerError:
        """
        name, domain = user.split(u'@')
        identity = self.simple_http_login(name, domain, pwd, user_ip)

        return identity    
    
    @watch
    def count(self):
        """Count users, groups, roles and objects
        """
        try:
            res = {u'users':self.dbauth.count_user(),
                   u'groups':self.dbauth.count_group(),
                   u'roles':self.dbauth.count_role(),
                   u'objects':self.dbauth.count_object()}
            return res
        except QueryError as ex:
            raise ApiManagerError(ex, code=ex.code)
    
    #
    # role manipulation methods
    #
    @watch
    def get_roles(self, *args, **kvargs):
        """Get roles or single role.

        :param oid: role id [optional]
        :param name: role name [optional]
        :param user: user id [optional]
        :param group: group id [optional]
        :param permission: permission (type, value, action) [optional]           
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]         
        :return: list or Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            permission = kvargs.get(u'permission', None)
            group = kvargs.get(u'group', None)
            user = kvargs.get(u'user', None)             
            
            # search roles by role
            if permission is not None:
                # get permission
                # ("id", "oid", "type", "definition", "objid", "aid", "action")
                objid = permission[5]
                objtype = permission[2]
                objdef = permission[3]
                action = permission[6]
                perm = self.dbauth.get_permission_by_object(objid=objid,
                                                            objtype=objtype, 
                                                            objdef=objdef,
                                                            action=action)[0]
                roles, total = self.dbauth.get_permission_roles(
                    perm, *args, **kvargs)

            # search roles by user
            elif user is not None:
                kvargs[u'user'] = self.get_entity(user, self.dbauth.get_users)
                roles, total = self.dbauth.get_user_roles_with_expiry(*args, **kvargs)

            # search roles by group
            elif group is not None:
                kvargs[u'group'] = self.get_entity(group, self.dbauth.get_groups)
                roles, total = self.dbauth.get_group_roles(*args, **kvargs)
            
            # get all roles
            else:
                roles, total = self.dbauth.get_roles(*args, **kvargs)            
            
            return roles, total
        
        res, total = self.get_paginated_objects(Role, get_entities, *args, **kvargs)
        return res, total    
    
    @watch
    def add_role(self, name, description=u''):
        """Add new role.

        :param name: name of the role
        :param description: role description. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        params = {u'name':name, u'description':description}
        
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, u'insert')            

        try:
            objid = id_gen()
            role = self.dbauth.add_role(objid, name, description)
            
            # add object and permission
            Role(self).register_object([objid], desc=description)
            
            self.logger.debug(u'Add new role: %s' % name)
            Role(self).send_event(u'add', params=params)
            return role.id
        except (TransactionError) as ex:
            Role(self).send_event(u'add', params=params, exception=ex)           
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            Role(self).send_event(u'add', params=params, exception=ex)        
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    @watch
    def add_superadmin_role(self, perms):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_role(u'ApiSuperadmin', u'Beehive super admin role')
        
        # append permissions
        try:
            self.dbauth.append_role_permissions(role, perms)
            return role
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_role(u'Guest', u'Beehive guest role')        
        return role

    @watch
    def add_app_role(self, name):
        """Add role used by an app that want to connect to cloudapi 
        to get configuration and make admin action.
        
        :param name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.add_role(name, u'Beehive app \'%s\' role' % name)

    #
    # user manipulation methods
    #
    @watch
    def get_users(self, *args, **kvargs):
        """Get users or single user.

        :param oid: user id [optional]
        :param name: user name [optional]
        :param role: role name, id or uuid [optional]
        :param group: group name, id or uuid [optional]
        :param active: user status [optional]
        :param expiry_date: user expiry date. Use gg-mm-yyyy [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: tupla (id, name, type, active, description, attribute
                        creation_date, modification_date)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get(u'role', None)
            group = kvargs.get(u'group', None)
            expiry_date = kvargs.get(u'expiry_date', None)             
            
            # search users by role
            if role:
                kvargs[u'role'] = self.get_entity(role, self.dbauth.get_roles)
                users, total = self.dbauth.get_role_users(*args, **kvargs)

            # search users by group
            elif group is not None:
                kvargs[u'group'] = self.get_entity(group, self.dbauth.get_groups)
                users, total = self.dbauth.get_group_users(*args, **kvargs)
            
            # get all users
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split(u'-')
                    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                users, total = self.dbauth.get_users(*args, **kvargs)            
            
            return users, total
        
        res, total = self.get_paginated_objects(User, get_entities, *args, **kvargs)
        return res, total

    @watch
    def add_user(self, name, storetype, systype, active=True, 
                       password=None, description=u'', expiry_date=None):
        """Add new user.

        :param name: name of the user
        :param storetype: type of the user store. Can be DBUSER, LDAPUSER
        :param systype: type of user. User can be a human USER or a system 
                        module SYS
        :param active: User status. If True user is active [Optional] [Default=True]
        :param description: User description. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :param expiry_date: user expiry date. Set as gg-mm-yyyy [default=365 days]
        :return: user id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        params = {u'name':name, u'description':description, 
                  u'storetype':storetype, u'systype':systype, u'active':active, 
                  u'expiry_date':expiry_date}
        
        # check authorization
        self.check_authorization(User.objtype, User.objdef, None, u'insert')
        
        try:
            objid = id_gen()
            if expiry_date is not None:
                g, m, y = expiry_date.split(u'-')
                expiry_date = datetime(int(y), int(m), int(g))
            user = self.dbauth.add_user(objid, name, active=active, 
                                        password=password, 
                                        description=description, 
                                        expiry_date=expiry_date)
            # add object and permission
            User(self).register_object([objid], desc=description)
            
            # add default attributes
            self.dbauth.set_user_attribute(user, u'store_type', storetype, 
                                           u'Type of user store')
            self.dbauth.set_user_attribute(user, u'sys_type', systype, 
                                           u'Type of user')            
            
            self.logger.debug(u'Add new user: %s' % name)
            User(self).send_event(u'add', params=params)
            return user.id
        except (TransactionError) as ex:
            User(self).send_event(u'add', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            User(self).send_event(u'add', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    @watch
    def add_generic_user(self, name, storetype, password=None,
                         description=u'', expiry_date=None):
        """Add cloudapi generic user. A generic user has a default role
        associated and the guest role. A generic user role has no permissions
        associated.
        
        :param name: user name
        :param storetype: type of the user. Can be DBUSER, LDAPUSER
        :param password: user password for DBUSER
        :param description: User description. [Optional]
        :param expiry_date: user expiry date. Set as gg-mm-yyyy [default=365 days]     
        :return: user id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        self.add_user(name, storetype, u'USER', active=True, 
                      password=password, description=description,
                      expiry_date=expiry_date)
        user = self.get_users(name=name)[0][0]

        # create user role
        self.add_role(u'User%sRole' % user.oid, u'User %s private role' % name)
        
        # append role to user
        expiry_date = u'31-12-2099'
        user.append_role(u'User%sRole' % user.oid)
        user.append_role(u'Guest', expiry_date=expiry_date)
        return user.oid
    
    @watch
    def add_system_user(self, name, password=None, description=u''):
        """Add cloudapi system user. A system user is used by a module to 
        call the apis of the other modules.
        
        :param name: user name
        :param password: user password for DBUSER
        :param description: User description. [Optional]        
        :return: user id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        self.add_user(name, u'DBUSER', u'SYS', active=True, 
                      password=password, description=description)
        user = self.get_users(name=name)[0][0]
        
        # create user role
        self.add_role(u'%sRole' % name.split(u'@')[0], u'User %s private role' % name)
        
        # append role to user
        expiry_date = u'31-12-2099'
        user.append_role(u'ApiSuperadmin', expiry_date=expiry_date)
        return user.oid
    
    #
    # group manipulation methods
    #
    @watch
    def get_groups(self, *args, **kvargs):
        """Get groups or single group.

        :param oid: group id [optional]
        :param name: group name [optional]
        :param role: role name, id or uuid [optional]
        :param user: user name, id or uuid [optional]
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]       
        :return: tupla (id, name, type, active, description, attribute
                        creation_date, modification_date)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get(u'role', None)
            user = kvargs.get(u'user', None)
            #expiry_date = kvargs.get(u'expiry_date', None)             
            
            # search groups by role
            if role:
                kvargs[u'role'] = self.get_entity(role, self.dbauth.get_roles)
                groups, total = self.dbauth.get_role_groups(*args, **kvargs)

            # search groups by user
            elif user is not None:
                kvargs[u'user'] = self.get_entity(user, self.dbauth.get_users)
                groups, total = self.dbauth.get_user_groups(*args, **kvargs)
            
            # get all groups
            else:
                #if expiry_date is not None:
                #    g, m, y = expiry_date.split(u'-')
                #    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                groups, total = self.dbauth.get_groups(*args, **kvargs)            
            
            return groups, total
        
        res, total = self.get_paginated_objects(Group, get_entities, *args, **kvargs)
        return res, total

    @watch
    def add_group(self, name, description=u''):
        """Add new group.

        :param name: name of the group
        :param description: Group description. [Optional]
        :return: True if group added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        params = {u'name':name, u'description':description}
        
        # check authorization
        self.check_authorization(Group.objtype, Group.objdef, None, u'insert')
        
        try:
            objid = id_gen()
            group = self.dbauth.add_group(objid, name, description=description)
            # add object and permission
            Group(self).register_object([objid], desc=description)          
            
            self.logger.debug(u'Add new group: %s' % name)
            Group(self).send_event(u'add', params=params)
            return group.id
        except (TransactionError) as ex:
            Group(self).send_event(u'add', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            Group(self).send_event(u'add', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    #
    # identity manipulation methods
    #
    @watch
    def set_identity(self, uid, identity, expire=True, expire_time=None):
        if expire_time is None:
            expire_time = self.expire
        val = pickle.dumps(identity)
        self.module.redis_manager.setex(self.prefix + uid, expire_time, val)
        if expire is False:
            self.module.redis_manager.persist(self.prefix + uid)
        self.logger.info(u'Set identity %s in redis' % uid)
        User(self).send_event(u'identity.add', params={u'uid':uid})
    
    @watch
    def remove_identity(self, uid):
        if self.module.redis_manager.get(self.prefix + uid) is None:
            err = u'Identity %s does not exist' % uid
            User(self).send_event(u'identity.remove', params={u'uid':uid}, 
                                  exception=err)
            self.logger.error(err)
            raise ApiManagerError(err, code=404)            
        
        try:
            self.module.redis_manager.delete(self.prefix + uid)
            self.logger.debug(u'Remove identity %s from redis' % uid)
            User(self).send_event(u'identity.remove', params={u'uid':uid})      
            return uid
        except Exception as ex:
            err = u'Can not remove identity %s' % uid
            User(self).send_event(u'identity.remove', params={u'uid':uid}, 
                                  exception=err)  
            self.logger.error(err)
            raise ApiManagerError(err, code=400)       

    @watch
    def exist_identity(self, uid):
        """Get identity
        :return: True or False
        :rtype: dict
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.warn(u'Identity %s retrieve error: %s' % (uid, ex))
            return False
        
        if identity is not None:
            self.logger.debug(u'Identity %s exists' % (uid))           
            return True
        else:
            self.logger.warn(u'Identity does not %s exists' % (uid))           
            return False

    @watch
    def get_identity(self, uid):
        """Get identity
        :return: {u'uid':..., u'user':..., u'timestamp':..., u'pubkey':..., 
                  'seckey':...}
        :rtype: dict
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error(u'Identity %s retrieve error: %s' % (uid, ex))
            raise ApiManagerError(u'Identity %s retrieve error' % uid, code=404)
            
        if identity is not None:
            data = pickle.loads(identity)
            data[u'ttl'] = self.module.redis_manager.ttl(self.prefix + uid)
            self.logger.debug(u'Get identity %s from redis: %s' % 
                              (uid, truncate(data)))   
            return data
        else:
            self.logger.error(u'Identity %s does not exist or is expired' % uid)
            raise ApiManagerError(u'Identity %s does not exist or is '\
                                  u'expired' % uid, code=404)

    @watch
    def get_identities(self):
        try:
            res =  []
            for key in self.module.redis_manager.keys(self.prefix+'*'):
                identity = self.module.redis_manager.get(key)
                data = pickle.loads(identity)
                data[u'ttl'] = self.module.redis_manager.ttl(key)
                res.append(data)
        except Exception as ex:
            self.logger.error(u'No identities found: %s' % ex)
            raise ApiManagerError(u'No identities found')
        
        User(self).send_event(u'identity.list', params={}) 
        self.logger.debug(u'Get identities from redis: %s' % truncate(res))
        return res    
    
    @watch
    def _gen_authorizaion_key(self, user, domain, name, login_ip, attrib):
        '''Generate asymmetric key for keyauth filter.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param attrib: user attributes
        
        :raise ApiManagerError: 
        '''
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }
        user_name = u'%s@%s' % (name, domain) 
        
        try:
            uid = id_gen(20)
            timestamp = datetime.now()#.strftime(u'%H-%M_%d-%m-%Y')     
            private_key = rsa.generate_private_key(public_exponent=65537,
                                                   key_size=1024,
                                                   backend=default_backend())        
            public_key = private_key.public_key()
            pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo)    
            pubkey = binascii.b2a_base64(pem)
            pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL, 
                        encryption_algorithm=serialization.NoEncryption())    
            seckey = binascii.b2a_base64(pem)
            
            # create identity
            identity = {u'uid':uid,
                        u'type':u'keyauth',
                        u'user':user.get_dict(),
                        u'timestamp':timestamp,
                        u'ip':login_ip,
                        u'pubkey':pubkey,
                        u'seckey':seckey}
            self.logger.debug(u'Create user %s identity: %s' % 
                              (user_name, truncate(identity)))
            operation.user = (user_name, login_ip, uid)
            
            # save identity in redis
            expire = True
            if attrib[u'sys_type'][0] == u'SYS':
                self.logger.debug(u'Login system user')
                #expire = False
            self.set_identity(uid, identity, expire=expire)
    
            '''
            res = {u'uid':uid,
                   u'type':u'keyauth',
                   u'user':user.get_dict(),
                   u'timestamp':timestamp,
                   u'pubkey':pubkey,
                   u'seckey':seckey}
            '''
            res = {
                u'token_type':u'Bearer',
                u'user':user.get_dict().get(u'id'),
                u'access_token':uid,
                u'pubkey':pubkey,
                u'seckey':seckey,
                u'expires_in':self.expire,
                u'expires_at':timestamp+timedelta(seconds=self.expire),
            }  
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=401)            
        
        return res
    
    @watch
    def _set_user_attribs(self, user, attribs):
        """Set user attributes"""
        user.set_attributes(attribs)
    
    @watch
    def _set_user_perms(self, dbuser, user):
        """Set user permissions """
        perms = self.dbauth.get_user_permissions2(dbuser)
        user.set_perms(perms)
    
    @watch
    def _set_user_roles(self, dbuser, user):
        """Set user roles """    
        roles, total = self.dbauth.get_user_roles(dbuser)
        user.set_roles([r.name for r in roles])    
    
    #
    # base inner login
    #
    @watch
    def validate_login_params(self, name, domain, password, login_ip):
        """Validate main login params.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        
        :raise ApiManagerError:        
        """
        if domain is None:
            domain = u'local'    
    
        # set user in thread local variable
        operation.user = (u'%s@%s' % (name, domain), login_ip, None)    
    
        # Validate input data and login user
        try:
            if name.strip() == u'':
                msg = u'Username is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if password.strip() == u'':
                msg = u'Password is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if domain.strip() == u'':
                msg = u'Domain is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            
            try:
                login_ip = gethostbyname(login_ip)
                IPv4Address(str2uni(login_ip))
            except Exception as ex:
                msg = u'Ip address is not provided or syntax is wrong'
                self.logger.error(msg, exc_info=1)
                raise ApiManagerError(msg, code=400)
            
            self.logger.debug(u'User %s@%s:%s validated' % 
                              (name, domain, login_ip))        
        except ApiManagerError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
    
    @watch
    def check_login_user(self, name, domain, password, login_ip):
        """Simple http authentication login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        
        :return: database user instance, user attributes as dict
        :raise ApiManagerError:        
        """
        # verify user exists in beehive database
        try:
            user_name = u'%s@%s' % (name, domain)
            dbuser = self.dbauth.get_users(name=user_name)[0][0]
            # get user attributes
            dbuser_attribs = {a.name:(a.value, a.desc) for a in dbuser.attrib}
        except (QueryError, Exception) as ex:
            msg = u'User %s does not exist' % user_name
            self.logger.error(msg, exc_info=1)
            raise ApiManagerError(msg, code=404)
        
        self.logger.debug(u'User %s exists' % user_name)
        
        return dbuser, dbuser_attribs   
    
    @watch
    def base_login(self, name, domain, password, login_ip, 
                     dbuser, dbuser_attribs):
        """Base login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param dbuser: database user instance
        :param dbuser_attribs: user attributes as dict
        :return: SystemUser instance, user attributes as dict
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }        
        
        # login user
        try:
            user = self.module.authentication_manager.login(name, password, 
                                                            domain, login_ip)
        except (AuthError) as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)
        
        self.logger.info(u'Login user: %s' % user)
        
        # append attributes, roles and perms to SystemUser
        try:
            # set user attributes
            #self._set_user_attribs(user, dbuser_attribs)
            # set user permission
            self._set_user_perms(dbuser, user)
            # set user roles
            self._set_user_roles(dbuser, user)
        except QueryError as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)
        
        return user, dbuser_attribs
    #
    # simple http login
    #
    @watch
    def simple_http_login(self, name, domain, password, login_ip):
        """Simple http authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }
        user_name = u'%s@%s' % (name, domain)
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            User(self).send_event(u'simplehttp.login.add', params=opts, 
                                  exception=ex)
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                       password, login_ip)
        except ApiManagerError as ex:
            User(self).send_event(u'simplehttp.login.add', params=opts, 
                                  exception=ex)
            raise
        
        # check user has authentication filter
        auth_filters = dbuser_attribs.get(u'auth-filters', (u'', None))[0].split(u',')
        if u'simplehttp' not in auth_filters:
            msg = u'Simple http authentication is not allowed for user %s' % \
                  user_name
            User(self).send_event(u'simplehttp.login.add', params=opts, 
                                  exception=msg)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)
        
        # check user ip is in allowed cidr
        auth_cidrs = dbuser_attribs.get(u'auth-cidrs', u'')[0].split(u',')
        allowed = False
        for auth_cidr in auth_cidrs:
            allowed_cidr = IPv4Network(str2uni(auth_cidr))
            user_ip = IPv4Network(u'%s/32' % login_ip)
            if user_ip.overlaps(allowed_cidr) is True:
                allowed = True
                break
        
        if allowed is False:
            msg = u'User %s ip %s can not perform simple http authentication' % \
                  (user_name, login_ip)
            User(self).send_event(u'simplehttp.login.add', params=opts, 
                                  exception=msg)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)            
        
        # login user
        try:
            user, attrib = self.base_login(name, domain, password, login_ip, 
                                           dbuser, dbuser_attribs)
        except ApiManagerError as ex:
            User(self).send_event(u'simplehttp.login.add', params=opts, 
                                  exception=ex)
            raise
        
        res = {u'uid':id_gen(20),
               u'type':u'simplehttp',
               u'user':user.get_dict(),
               u'timestamp':datetime.now().strftime(u'%y-%m-%d-%H-%M')}        
    
        User(self).send_event(u'simplehttp.login.add', params=opts)
        
        return res
    
    #
    # keyauth login, logout, refresh_user
    #
    @watch
    def login(self, name, domain, password, login_ip):
        """Asymmetric keys authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }        
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            User(self).send_event(u'keyauth.token.add', params=opts, 
                                  exception=ex)
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                       password, login_ip)
        except ApiManagerError as ex:
            User(self).send_event(u'keyauth.token.add', params=opts, 
                                  exception=ex)
            raise     
        
        # check user attributes
        
        # login user
        try:
            user, attrib = self.base_login(name, domain, password, login_ip, 
                                           dbuser, dbuser_attribs)
        except ApiManagerError as ex:
            User(self).send_event(u'keyauth.token.add', params=opts, 
                                  exception=ex)
        
        # generate asymmetric keys
        res = self._gen_authorizaion_key(user, domain, name, login_ip, attrib)

        User(self).send_event(u'keyauth.token.add', params=opts)
        
        return res
    
    @watch
    def logout(self, uid, sign, data):
        """Logout user
        """
        # get identity and verify signature
        #identity = self.verify_request_signature(uid, sign, data)
        #operation.user = (identity[u'user'][u'name'], identity[u'ip'], identity[u'uid'])
        identity = self.get_identity(uid)
        
        try:
            # remove identity from redis
            self.remove_identity(identity[u'uid'])
    
            res = u'Identity %s successfully logout' % identity[u'uid']
            self.logger.debug(res)
            User(self).send_event(u'keyauth-login.remove', params={u'uid':uid})
        except Exception as ex:
            User(self).send_event(u'keyauth-login.remove', params={u'uid':uid}, 
                                  exception=ex)
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=400)
                
        return res
    
    @watch
    def refresh_user(self, uid, sign, data):
        """Refresh permissions stored in redis identity for a logged user
        """
        self.logger.info(u'Refresh identity: %s' % uid)        
        identity = self.get_identity(uid)
        #user = identity[u'user']
        
        user_name = operation.user[0]
        name, domain = user_name.split(u'@')
        res = None
        
        try:
            # reresh user in authentication manager
            user = self.module.authentication_manager.refresh(uid, name, domain)            
            # get user reference in db
            dbuser = self.dbauth.get_users(name=user_name)[0]
            # set user attributes
            self._set_user_attribs(dbuser, user)
            # set user permission
            self._set_user_perms(dbuser, user)
            # set user roles
            self._set_user_roles(dbuser, user)
            
            # set user in identity
            identity[u'user'] = user.get_dict()
            
            # save identity in redis
            self.set_identity(uid, identity)
            
            res = {u'uid':uid,
                   u'user':user.get_dict(),
                   u'timestamp':identity[u'timestamp'],
                   u'pubkey':identity[u'pubkey'],
                   u'seckey':identity[u'seckey']}   

            User(self).send_event(u'keyauth-login.modify', params={u'uid':uid})
        except QueryError as ex:
            User(self).send_event(u'keyauth-login.modify', params={u'uid':uid}, 
                                  exception=ex)
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=400)
        except Exception as ex:
            User(self).send_event(u'keyauth-login.modify', params={u'uid':uid}, 
                                  exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)        

        return res

class AuthObject(ApiObject):
    objtype = u'auth'
    objdef = u'abstract'
    objdesc = u'Authorization abstract object'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 active=True, model=None):
        ApiObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                           desc=desc, active=active)
        self.model = model
    
    def __del__(self):
        pass    
    
    @property
    def dbauth(self):
        return self.controller.dbauth    
    
    def set_admin_permissions(self, role_name, args):
        """Set admin permissions
        """
        try:
            role, total = self.dbauth.get_roles(name=role_name)
            perms, total = self.dbauth.get_permission_by_object(
                                    objid=self._get_value(self.objdef, args),
                                    objtype=None, 
                                    objdef=self.objdef,
                                    action=u'*')            
            
            # set container main permissions
            self.dbauth.append_role_permissions(role[0], perms)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

class Objects(AuthObject):
    objdef = u'Objects'
    objdesc = u'Authorization objects'
    
    def __init__(self, controller):
        AuthObject.__init__(self, controller, oid=u'', name=u'', desc=u'', 
                            active=u'')
    
    #
    # System Object Type manipulation methods
    #    
    @watch
    def get_type(self, oid=None, objtype=None, objdef=None,
                 page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :param page: type list page to show [default=0]
        :param size: number of types to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]        
        :return: List of Tuple (id, type, definition, objclass)
        :rtype: list
        :raises ApiManagerError if query empty return error.
        :raises ApiAuthorizationError if query empty return error.
        """
        opts = {u'oid':oid, u'objtype':objtype, u'objdef':objdef,
                u'page':page, u'size':size, u'order':order, u'field':field}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)

        try:  
            data, total = self.dbauth.get_object_type(
                        oid=oid, objtype=objtype, objdef=objdef, 
                        page=page, size=size, order=order, field=field)

            res = [{u'id':i.id, u'subsystem':i.objtype, u'type':i.objdef}
                    for i in data] #if i.objtype != u'event']
            self.send_event(u'type.list', params=opts)
            return res, total
        except QueryError as ex:
            self.send_event(u'type.list', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            return [], 0
    
    @watch
    def add_types(self, obj_types):
        """Add a system object types
        
        :param obj_types: list of dict {u'subsystem':.., u'type':..}
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can(u'insert', self.objtype, definition=self.objdef)
        try:
            data = [(i[u'subsystem'], i[u'type']) for i in obj_types]
            res = self.dbauth.add_object_types(data)
            self.send_event(u'type.add', params=obj_types)
            return [i.id for i in res]
        except TransactionError as ex:
            self.send_event(u'type.add', params=obj_types, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def remove_type(self, oid=None, objtype=None, objdef=None):
        """Remove system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        params = {u'oid':oid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:  
            res = self.dbauth.remove_object_type(oid=oid, objtype=objtype, 
                                                 objdef=objdef)
            self.send_event(u'type.add', params=params)          
            return res
        except TransactionError as ex:
            self.send_event(u'type.add', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object Action manipulation methods
    #
    @watch
    def get_action(self, oid=None, value=None):
        """Get system object action.
        
        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: List of Tuple (id, value)   
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        params = {u'oid':oid, u'value':value}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            data = self.dbauth.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError(u'No data found')
            if type(data) is not list:
                data = [data]            
            res = [{u'id':i.id, u'value':i.value} for i in data]
            self.send_event(u'action.list', params=params)
            return res
        except QueryError as ex:
            self.send_event(u'action.list', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @watch
    def add_actions(self, actions):
        """Add a system object action
        
        :param actions: list of string like 'use', u'view'
        :return: True if operation is successful   
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can(u'insert', self.objtype, definition=self.objdef)

        try:  
            res = self.dbauth.add_object_actions(actions)
            self.send_event(u'action.add', params=actions)
            return True
        except TransactionError as ex:
            self.send_event(u'action.add', params=actions, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
    @watch
    def remove_action(self, oid=None, value=None):
        """Add a system object action
        
        :param oid: System object action id [optional]
        :param value: string like 'use', u'view' [optional]
        :return: True if operation is successful   
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        params = {u'oid':oid, u'value':value}
        
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:
            res = self.dbauth.remove_object_action(oid=oid, value=value)
            self.send_event(u'action.remove', params=params)
            return res
        except TransactionError as ex:
            self.send_event(u'action.remove', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object manipulation methods
    #
    @watch
    def get(self, oid=None, objid=None, objtype=None, objdef=None, 
            page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object filtered by id, by name or by type.

        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: type of the system object [optional]
        :param objdef: definition of the system object [optional]
        :param page: object list page to show [default=0]
        :param size: number of object to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Tuple (id, type, value) 
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        opts = {u'oid':oid, u'objtype':objtype, u'objdef':objdef, u'objid':objid,
                u'page':page, u'size':size, u'order':order, u'field':field}        
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:
            data,total = self.dbauth.get_object(oid=oid, objid=objid, 
                    objtype=objtype, objdef=objdef, page=page, size=size,
                    order=order, field=field)
                    
            res = [{
                u'id':i.id,
                u'subsystem':i.type.objtype,
                u'type':i.type.objdef,
                u'objid':i.objid,
                u'desc':i.desc
            } for i in data]
            self.logger.debug(u'Get objects: %s' % len(res))
            self.send_event(u'list', params=opts)
            return res, total
        except QueryError as ex:
            self.send_event(u'list', params=opts, exception=ex)
            self.logger.error(ex.desc, exc_info=1)
            return [], 0
        except Exception as ex:
            self.send_event(u'list', params=opts, exception=ex)          
            self.logger.error(ex, exc_info=1)
            return [], 0        

    @watch
    def add(self, objs):
        """Add a system object with all the permission related to available 
        action.
        
        :param objs: list of dict like {
                'subsystem':..,
                'type':.., 
                'objid':.., 
                'desc':..        
            }
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can(u'insert', self.objtype, definition=self.objdef)
                
        try:
            # get actions
            actions = self.dbauth.get_object_action()            
            
            # create objects
            data = []
            for obj in objs:
                obj_type, total = self.dbauth.get_object_type(
                    objtype=obj[u'subsystem'], objdef=obj[u'type'])
                data.append((obj_type[0], obj[u'objid'], obj[u'desc']))

            res = self.dbauth.add_object(data, actions)
            self.logger.debug(u'Add objects: %s' % res)
            self.send_event(u'add', params=objs)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'add', params=objs, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)  

    @watch
    def remove(self, oid=None, objid=None, objtype=None, objdef=None):
        """Delete system object filtering by id, by name or by type. System 
        remove also all the related permission. 
        
        Examples:
            manager.remove_object(oid='123242')
            manager.remove_object(value='', type="cloudstack.vm")
            manager.remove_object(value='clsk42_01.ROOT/CSI.')        
        
        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: type of the system object [optional]
        :param objdef: definition of the system object [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        opts = {u'oid':oid, u'objid':objid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:
            if objtype is not None or objdef is not None:
                # get object types
                obj_types = self.dbauth.get_object_type(objtype=objtype, 
                                                        objdef=objdef)
                for obj_type in obj_types:            
                    res = self.dbauth.remove_object(oid=oid, objid=objid, 
                                                    objtype=obj_type)
            else:
                res = self.dbauth.remove_object(oid=oid, objid=objid)
            self.logger.debug(u'Remove objects: %s' % res)
            self.send_event(u'remove', params=opts)
            return res
        except TransactionError as ex:
            self.send_event(u'remove', params=opts, exception=ex)     
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)          

    @watch
    def get_permission(self, permission_id=None, objid=None, objtype=None, 
                             objdef=None, action=None):
        """Get system object permisssion.
        
        :param permission_id: System Object Permission id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :param action str: Object action [optional]
        :return: list of tuple like ("id", "oid", "type", "definition", 
                 "objclass", "objid", "aid", "action").
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        opts = {u'permission_id':permission_id, u'objid':objid, 
                u'objtype':objtype, u'objdef':objdef, u'action':action}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:
            if permission_id is not None:
                res = self.dbauth.get_permission_by_id(permission_id=permission_id)
            elif objid is not None or objtype is not None or objdef is not None:
                res = self.dbauth.get_permission_by_object(objid=objid, 
                                                           objtype=objtype, 
                                                           objdef=objdef,
                                                           action=action)
            else:
                res = self.dbauth.get_permission_by_id()
            
            res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]            

            self.logger.debug(u'Get permissions: %s' % len(res))
            self.send_event(u'perms.list', params=opts)          
            return res
        except QueryError as ex:
            self.send_event(u'perms.list', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return []

    def get_permissions_with_roles(self, oid=None, objid=None, objtype=None, 
                                   objdef=None, page=0, size=10, order=u'DESC', 
                                   field=u'id'):
        """Get system object permisssion with roles.
        
        :param oid: permission id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]        
        :return: list of tuple like (((id, rid, type, definition, 
                                       objclass, objid, aid, action, desc), 
                                      (role_id, role_name, role_desc))).
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        opts = {u'objid':objid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)        
        
        try:
            res = []
            if oid is not None:
                perms = self.dbauth.get_permission_by_id(permission_id=oid)
                total = 1
            
            # get permissions
            else:
                perms, total = self.dbauth.get_permission_by_object(
                            objid=objid, objid_filter=None, objtype=objtype, 
                            objdef=objdef, objdef_filter=None, action=None,
                            page=page, size=size, order=order, field=field)
                
            for p in perms:
                try:
                    #roles = [(r.id, r.name, r.description) for r in 
                    #         self.dbauth.get_permission_roles(p)]
                    roles = [{u'id':r.id, 
                              u'name':r.name, 
                              u'desc':r.description} for r in 
                             self.dbauth.get_permission_roles(p)]
                except:
                    roles = []
                res.append({
                    u'id':p.id, 
                    u'oid':p.obj.id, 
                    u'subsystem':p.obj.type.objtype, 
                    u'type':p.obj.type.objdef,
                    u'objid':p.obj.objid, 
                    u'aid':p.action.id, 
                    u'action':p.action.value, 
                    u'desc':p.obj.desc, 
                    u'roles':roles
                })
                
            self.logger.debug(u'Get permissions: %s' % len(res))
            self.send_event(u'perms.list', params=opts)           
            return res, total
        except QueryError as ex:
            self.send_event(u'perms.list', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return [], 0

class Role(AuthObject):
    objdef = u'Role'
    objdesc = u'System roles'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.dbauth.update_role
        self.delete_object = self.dbauth.remove_role        
        
        if self.model is not None:
            self.uuid = self.model.uuid
        self.expiry_date = None

    @watch
    def info(self):
        """Get role info
        
        :return: Dictionary with role info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')
           
        creation_date = str2uni(self.model.creation_date\
                                .strftime(u'%d-%m-%Y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%Y %H:%M:%S'))
        res = {
            u'id':self.oid, 
            u'uuid':self.uuid,    
            u'type':self.objtype, 
            u'definition':self.objdef, 
            u'name':self.name, 
            u'objid':self.objid, 
            u'desc':self.desc,
            u'active':self.active, 
            u'date':{
                u'creation':creation_date,
                u'modified':modification_date
            }
        }
        
        if self.expiry_date is not None:
            expiry_date = str2uni(self.expiry_date\
                                  .strftime(u'%d-%m-%Y %H:%M:%S'))
            res[u'date'][u'expiry'] = expiry_date
        
        return res

    @watch
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            perms, total = self.dbauth.get_role_permissions([self.name], 
                            page=page, size=size, order=order, field=field)      
            role_perms = []
            for i in perms:
                role_perms.append({
                    u'id':i.id, 
                    u'oid':i.obj.id, 
                    u'subsystem':i.obj.type.objtype, 
                    u'type':i.obj.type.objdef,
                    u'objid':i.obj.objid, 
                    u'aid':i.action.id, 
                    u'action':i.action.value,
                    u'desc':i.obj.desc
                })                
            self.logger.debug(u'Get role %s permissions: %s' % (
                                        self.name, truncate(role_perms)))
            self.send_event(u'perms.list', params=opts)           
            return role_perms, total
        except QueryError as ex:
            self.send_event(u'perms.list', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return [], 0    

    @watch
    def append_permissions(self, perms):
        """Append permission to role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", 
                      "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                perms, total = self.dbauth.get_permission_by_object(
                        objid=perm[4], objtype=perm[2], objdef=perm[3],
                        action=perm[6], size=1000)
                roleperms.extend(perms)
            
            res = self.dbauth.append_role_permissions(self.model, roleperms)
            self.logger.debug(u'Append role %s permission : %s' % (self.name, perms))
            self.send_event(u'perms-set.modify', params=opts)            
            return res
        except QueryError as ex:
            self.send_event(u'perms-set.modify', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    def remove_permissions(self, perms):
        """Remove permission from role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", 
                      "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                perms, total = self.dbauth.get_permission_by_object(
                        objid=perm[4], objtype=perm[2], objdef=perm[3],
                        action=perm[6], size=1000)
                roleperms.extend(perms)        
            
            res = self.dbauth.remove_role_permission(self.model, roleperms)
            self.logger.debug(u'Remove role %s permission : %s' % (self.name, perms))
            self.send_event(u'perms-unset.modify', params=opts)       
            return res
        except QueryError as ex:
            self.send_event(u'perms-unset.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

class User(AuthObject):
    objdef = u'User'
    objdesc = u'System users'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.dbauth.update_user
        self.delete_object = self.dbauth.remove_user        
        
        if self.model is not None:
            self.uuid = self.model.uuid     

    @watch
    def info(self):
        """Get user info
        
        :return: Dictionary with user info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')
           
        creation_date = str2uni(self.model.creation_date\
                                .strftime(u'%d-%m-%Y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%Y %H:%M:%S'))
        expiry_date = u''
        if self.model.expiry_date is not None:
            expiry_date = str2uni(self.model.expiry_date\
                                  .strftime(u'%d-%m-%Y %H:%M:%S'))
        #attrib = self.get_attribs()
        return {
            u'id':self.oid,
            u'uuid':self.uuid,
            u'type':self.objtype, 
            u'definition':self.objdef, 
            u'name':self.name, 
            u'objid':self.objid, 
            u'desc':self.desc,
            u'password':self.model.password,
            u'active':self.active, 
            u'date':{
                u'creation':creation_date,
                u'modified':modification_date,
                u'expiry':expiry_date
            }
        }

    @watch
    def delete(self):
        """Delete entity.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        params = {u'id':self.oid}
        
        if self.delete_object is None:
            raise ApiManagerError(u'Delete is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))        
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            # remove associated roles
            roles, total = self.dbauth.get_user_roles(user=self.model, size=1000)
            for role in roles:
                res = self.dbauth.remove_user_role(self.model, role)
            
            # delete user
            res = self.delete_object(oid=self.oid)
            if self.register is True:
                # remove object and permissions
                self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete %s: %s' % (self.objdef, self.oid))
            self.send_event(u'remove', params=params)
            return res
        except TransactionError as ex:
            self.send_event(u'remove', params=params, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def get_attribs(self):
        attrib = [{u'name':a.name, u'value':a.value, u'desc':a.desc}
                   for a in self.model.attrib]
        self.logger.debug(u'User %s attributes: %s' % (self.name, attrib))
        return attrib   
    
    @watch
    def set_attribute(self, name, value, desc='', new_name=None):
        """Set an attribute
        
        :param user: User instance
        :param name: attribute name
        :param new_name: new attribute name
        :param value: attribute value
        :param desc: attribute description
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`        
        """
        opts = {u'name':self.name, u'attrib':name, u'value':value}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.dbauth.set_user_attribute(self.model, name, value=value, 
                                                 desc=desc, new_name=new_name)
            self.logger.debug(u'Set user %s attribute %s: %s' % 
                              (self.name, name, value))
            self.send_event(u'attrib-set.modify', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'attrib-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def remove_attribute(self, name):
        """Remove an attribute
        
        :param name: attribute name
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`           
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.dbauth.remove_user_attribute(self.model, name)
            self.logger.debug(u'Remove user %s attribute %s' % (self.name, name))
            self.send_event(u'attrib-unset.modify', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'attrib-unset.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def append_role(self, role_id, expiry_date=None):
        """Append role to user.
        
        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'role':role_id, u'expiry_date':expiry_date}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.controller.get_entity(role_id, self.dbauth.get_roles)         
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                g, m, y = expiry_date.split(u'-')
                expiry_date_obj = datetime(int(y), int(m), int(g))
            res = self.dbauth.append_user_role(self.model, role, 
                                               expiry_date=expiry_date_obj)
            if res is True: 
                self.logger.debug(u'Append role %s to user %s' % (
                                            role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with user %s' % (
                                            role, self.name))
            self.send_event(u'role-set.modify', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_role(self, role_id):
        """Remove role from user.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.controller.get_entity(role_id, self.dbauth.get_roles)          
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-unset.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.dbauth.remove_user_role(self.model, role)
            self.logger.debug(u'Remove role %s from user %s' % (role, self.name))
            self.send_event(u'role-unset.modify', params=opts)           
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-unset.modify', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            perms, total = self.dbauth.get_user_permissions(self.model, 
                            page=page, size=size, order=order, field=field)      
            user_perms = []
            for i in perms:
                user_perms.append({
                    u'id':i.id, 
                    u'oid':i.obj.id, 
                    u'subsystem':i.obj.type.objtype, 
                    u'type':i.obj.type.objdef,
                    u'objid':i.obj.objid, 
                    u'aid':i.action.id, 
                    u'action':i.action.value,
                    u'desc':i.obj.desc
                })                
            self.logger.debug(u'Get user %s permissions: %s' % (
                                        self.name, truncate(user_perms)))
            self.send_event(u'perms.list', params=opts)
            return user_perms, total
        except QueryError as ex:
            self.send_event(u'perms.list', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0
        
    @watch
    def can(self, action, objtype, definition=None, name=None, perms=None):
        """Verify if  user can execute an action over a certain object type.
        Specify at least name or perms.
        
        :param perms: user permissions. Pandas Series with permissions 
                      (pid, oid, type, definition, class, objid, aid, action) [optional]
        :param objtype: object type. Es. 'reosurce', u'service,
        :param definition: object definition. Es. 'container.org.group.vm'                                        
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: list of non redundant permission objids
        :rtype: list
        :raises ApiManagerError: if there are problems retrieving permissions
                                  or user is not enabled to execute action
                                  over object with type specified
        """
        opts = {u'action':action, u'objtype':objtype, u'definition':definition, 
                u'name':self.name, u'perms':perms}
        
        # verify permissions
        self.controller.can(u'use', self.objtype, definition=self.objdef)
                
        if perms is None:
            try:
                perms = self.get_permissions(self.name)
            except QueryError as ex:
                self.logger.error(ex, exc_info=1)
                raise ApiManagerError(ex)

        try:
            objids = []
            defs = []
            for perm in perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, u'resource', u'container.org.group.vm', u'Vm', u'c1.o1.g1.*', 6, u'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]
                
                # no definition is specify
                if definition is not None:
                    # verify object type, definition and action. If they match 
                    # objid to values list
                    if (perm_objtype == objtype and
                        perm_definition == definition and
                        perm_action in [u'*', action]):
                        objids.append(perm_objid)
                else:
                    if (perm_objtype == objtype and
                        perm_action in [u'*', action]):
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug(u'User %s can %s objects {%s, %s, %s}' % 
                                  (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug(u'User %s can %s objects {%s, %s}' % 
                                  (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception(u'User %s can not \'%s\' objects \'%s:%s\'' % 
                                (self.name, action, objtype, definition))
                
            self.send_event(u'can', params=opts)   
        except Exception as ex:
            self.send_event(u'can', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
class Group(AuthObject):
    objdef = u'Group'
    objdesc = u'System groups'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.dbauth.update_group
        self.delete_object = self.dbauth.remove_group
        
        if self.model is not None:
            self.uuid = self.model.uuid          

    @watch
    def info(self):
        """Get group info
        
        :return: Dictionary with group info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')
           
        creation_date = str2uni(self.model.creation_date\
                                .strftime(u'%d-%m-%Y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%Y %H:%M:%S'))
        #attrib = self.get_attribs()
        return {
            u'id':self.oid,
            u'uuid':self.uuid,
            u'type':self.objtype, 
            u'definition':self.objdef, 
            u'name':self.name, 
            u'objid':self.objid, 
            u'desc':self.desc,
            u'active':self.active, 
            u'date':{
                u'creation':creation_date,
                u'modified':modification_date
            }
        }

    @watch
    def delete(self):
        """Delete entity.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        params = {u'id':self.oid}
        
        if self.delete_object is None:
            raise ApiManagerError(u'Delete is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))        
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            # remove associated roles
            roles, total = self.dbauth.get_group_roles(group=self.model, size=1000)
            for role in roles:
                res = self.dbauth.remove_group_role(self.model, role)
            
            # delete user
            res = self.delete_object(oid=self.oid)
            if self.register is True:
                # remove object and permissions
                self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete %s: %s' % (self.objdef, self.oid))
            self.send_event(u'remove', params=params)
            return res
        except TransactionError as ex:
            self.send_event(u'remove', params=params, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def append_role(self, role_id):
        """Append role to group.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.controller.get_entity(role_id, self.dbauth.get_roles)
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.dbauth.append_group_role(self.model, role)
            if res is True: 
                self.logger.debug(u'Append role %s to group %s' % (
                                            role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with group %s' % (
                                            role, self.name))
            self.send_event(u'role-set.modify', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_role(self, role_id):
        """Remove role from group.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.controller.get_entity(role_id, self.dbauth.get_roles) 
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-unset.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.dbauth.remove_group_role(self.model, role)
            self.logger.debug(u'Remove role %s from group %s' % (role, self.name))
            self.send_event(u'role-unset.modify', params=opts)          
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'role-unset.modify', params=opts, exception=ex)        
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def append_user(self, user_id):
        """Append user to group.
        
        :param user_id: user name, id, or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'user':user_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user = self.controller.get_entity(user_id, self.dbauth.get_users)
        except (QueryError, TransactionError) as ex:
            self.send_event(u'user-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, 
                                            user.objid, u'view')

        try:
            res = self.dbauth.append_group_user(self.model, user)
            if res is True: 
                self.logger.debug(u'Append user %s to group %s' % (
                                            user, self.name))
            else:
                self.logger.debug(u'User %s already linked with group %s' % (
                                            user, self.name))
            self.send_event(u'user-set.modify', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'user-set.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_user(self, user_id):
        """Remove user from group.
        
        :param user_id: user id, name or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        opts = {u'name':self.name, u'user':user_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user = self.controller.get_entity(user_id, self.dbauth.get_users)   
        except (QueryError, TransactionError) as ex:
            self.send_event(u'user-unset.modify', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, 
                                            user.objid, u'view')

        try:
            res = self.dbauth.remove_group_user(self.model, user)
            self.logger.debug(u'Remove user %s from group %s' % (user, self.name))
            self.send_event(u'user-unset.modify', params=opts)       
            return res
        except (QueryError, TransactionError) as ex:
            self.send_event(u'user-unset.modify', params=opts, exception=ex)    
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Get groups permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        opts = {u'name':self.name}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            perms, total = self.dbauth.get_group_permissions(self.model, 
                            page=page, size=size, order=order, field=field)
            group_perms = []
            for i in perms:
                group_perms.append({
                    u'id':i.id, 
                    u'oid':i.obj.id, 
                    u'subsystem':i.obj.type.objtype, 
                    u'type':i.obj.type.objdef,
                    u'objid':i.obj.objid, 
                    u'aid':i.action.id, 
                    u'action':i.action.value,
                    u'desc':i.obj.desc
                })                
            self.logger.debug(u'Get group %s permissions: %s' % (
                                        self.name, truncate(group_perms)))
            self.send_event(u'perm.list', params=opts)
            return group_perms, total
        except QueryError as ex:
            self.send_event(u'perm.list', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0
        
    @watch
    def can(self, action, objtype, definition=None, name=None, perms=None):
        """Verify if  group can execute an action over a certain object type.
        Specify at least name or perms.
        
        :param perms: group permissions. Pandas Series with permissions 
                      (pid, oid, type, definition, class, objid, aid, action) [optional]
        :param objtype: object type. Es. 'reosurce', u'service,
        :param definition: object definition. Es. 'container.org.group.vm'                                        
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: list of non redundant permission objids
        :rtype: list
        :raises ApiManagerError: if there are problems retrieving permissions
                                  or group is not enabled to execute action
                                  over object with type specified
        """
        opts = {u'action':action, u'objtype':objtype, u'definition':definition, 
                u'name':self.name, u'perms':perms}
        
        # verify permissions
        self.controller.can(u'use', self.objtype, definition=self.objdef)
                
        if perms is None:
            try:
                perms = self.get_permissions(self.name)
            except QueryError as ex:
                self.logger.error(ex, exc_info=1)
                raise ApiManagerError(ex)

        try:
            objids = []
            defs = []
            for perm in perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, u'resource', u'container.org.group.vm', u'Vm', u'c1.o1.g1.*', 6, u'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]
                
                # no definition is specify
                if definition is not None:
                    # verify object type, definition and action. If they match 
                    # objid to values list
                    if (perm_objtype == objtype and
                        perm_definition == definition and
                        perm_action in [u'*', action]):
                        objids.append(perm_objid)
                else:
                    if (perm_objtype == objtype and
                        perm_action in [u'*', action]):
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug(u'Group %s can %s objects {%s, %s, %s}' % 
                                  (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug(u'Group %s can %s objects {%s, %s}' % 
                                  (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception(u'Group %s can not \'%s\' objects \'%s:%s\'' % 
                                (self.name, action, objtype, definition))
                
            self.send_event(u'can', params=opts)              
        except Exception as ex:
            self.send_event(u'can', params=opts, exception=ex)  
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
           
        
        