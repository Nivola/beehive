'''
Created on Jan 16, 2014

@author: darkbk
'''
import logging
import binascii
import pickle
from re import match
from datetime import datetime
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
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)        
        
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
        self.logger.warn(user)
        self.logger.warn(pwd)
        self.logger.warn(user_ip)
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
    def get_roles(self, oid=None, name=None, permission=None, user=None, 
                  group=None, page=0, size=10, order=u'DESC', field=u'id'):
        """Get roles or single role.

        :param oid: role id [optional]
        :param name: role name [optional]
        :param user: user id [optional]
        :param group: group id [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :param permission: permission (type, value, action) [optional]
        :return: List of (role.id, role.name, role.desc)
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can(u'view', Role.objtype, definition=Role.objdef)        
        res = []
        
        # query roles
        try:
            # search roles by oid
            if oid is not None:
                roles, total = self.dbauth.get_role(oid=oid)
                if not roles:
                    self.logger.warn(u'Role %s was not found' % oid)
            
            # search roles by name        
            elif name is not None:
                roles, total = self.dbauth.get_role(name=name)
                if not roles:
                    self.logger.warn(u'Role %s was not found' % name)
            
            # search roles by permission
            elif permission is not None:
                # get permission
                # ("id", "oid", "type", "definition", "objclass", "objid", "aid", "action")
                objid = permission[5]
                objtype = permission[2]
                objdef = permission[3]
                action = permission[7]
                perm = self.dbauth.get_permission_by_object(objid=objid,
                                                            objtype=objtype, 
                                                            objdef=objdef,
                                                            action=action)[0]
                roles, total = self.dbauth.get_permission_roles(perm, 
                                                    page=page, size=size, 
                                                    order=order, field=field)
            
            # search roles by user
            elif user is not None:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    user = self.dbauth.get_user(uuid=user)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(user)):
                    user = self.dbauth.get_user(oid=user)[0][0]
                # get obj by name
                else:
                    user = self.dbauth.get_user(name=user)[0][0]

                roles, total = self.dbauth.get_user_roles(user, 
                                                    page=page, size=size, 
                                                    order=order, field=field)

            # search roles by group
            elif group is not None:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    group = self.dbauth.get_group(uuid=group)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(group)):
                    group = self.dbauth.get_group(oid=group)[0][0]
                # get obj by name
                else:
                    group = self.dbauth.get_group(name=group)[0][0]
                    
                roles, total = self.dbauth.get_group_roles(group, 
                                                    page=page, size=size, 
                                                    order=order, field=field)
            
            # get all roles
            else:
                roles, total = self.dbauth.get_role(page=page, size=size, 
                                                    order=order, field=field)
            
            for role in roles:
                # check authorization
                objset = set(objs[Role.objdef.lower()])

                # create needs
                needs = self.get_needs([role.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    obj = Role(self, oid=role.id, objid=role.objid, 
                               name=role.name, desc=role.description, 
                               model=role)
                    res.append(obj)            
            
            self.logger.debug(u'Get roles: %s' % len(res))
            
            Role(self).event(u'role.view', 
                             {u'oid':oid, u'name':name, u'permission':permission}, 
                             (True))
            return res, total
        except QueryError as ex:
            Role(self).event(u'role.view', 
                             {u'oid':oid, u'name':name, u'permission':permission}, 
                             (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            return [], 0
            #raise ApiManagerError(ex)

    @watch
    def add_role(self, name, description=''):
        """Add new role.

        :param name: name of the role
        :param description: role description. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, u'insert')            
        
        '''
        # verify permissions
        objs = self.can(u'insert', Role.objtype, definition=Role.objdef)
        if len(objs) > 0 and objs[Role.objdef][0].split(u'//')[-1] != '*':
            raise ApiManagerError(u'You need more privileges to add role', 
                                  code=2000)'''
                
        try:
            objid = id_gen()
            role = self.dbauth.add_role(objid, name, description)
            self.logger.warn(role)
            # add object and permission
            Role(self).register_object([objid], desc=description)
            
            self.logger.debug(u'Add new role: %s' % name)
            Role(self).event(u'role.insert', 
                             {u'name':name, u'description':description}, 
                             (True))
            return role.id
        except (TransactionError) as ex:
            Role(self).event(u'role.insert', 
                             {u'name':name, u'description':description}, 
                             (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            Role(self).event(u'role.insert', 
                             {u'name':name, u'description':description}, 
                             (False, ex))            
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
    def get_users(self, oid=None, name=None, role=None, group=None,
                  page=0, size=10, order=u'DESC', field=u'id'):
        """Get users or single user.

        :param oid: user id [optional]
        :param name: user name [optional]
        :param role: role name, id or uuid [optional]
        :param group: group name, id or uuid [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: tupla (id, name, type, active, description, attribute
                        creation_date, modification_date)
        :rtype: :class:`SystemUser`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can(u'view', User.objtype, definition=User.objdef)
        res = []
                
        try:
            # search users by id
            if oid:
                users, total = self.dbauth.get_user(oid=oid)
                if not users:
                    self.logger.warn(u'User %s was not found' % oid)
            
            # search users by name
            elif name:
                users, total = self.dbauth.get_user(name=name)
                if not users:
                    self.logger.warn(u'User %s was not found' % name)
                
            # search users by role
            elif role:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    role_obj = self.dbauth.get_role(uuid=role)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(oid)):
                    role_obj = self.dbauth.get_role(oid=role)[0][0]
                # get obj by name
                else:
                    role_obj = self.dbauth.get_role(name=role)[0][0]
                #role_obj = self.dbauth.get_role(name=role)[0]
                users, total = self.dbauth.get_role_users(role_obj, page=page, 
                                        size=size, order=order, field=field)

            # search users by group
            elif group is not None:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    group = self.dbauth.get_group(uuid=group)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(oid)):
                    group = self.dbauth.get_group(oid=group)[0][0]
                # get obj by name
                else:
                    group = self.dbauth.get_group(name=group)[0][0]
                    
                users, total = self.dbauth.get_group_users(group, 
                                                    page=page, size=size, 
                                                    order=order, field=field)            
            
            # get all users
            else:
                users, total = self.dbauth.get_user(page=page, size=size, 
                                                    order=order, field=field)
            
            for user in users:
                # check authorization
                objset = set(objs[User.objdef.lower()])

                # create needs
                needs = self.get_needs([user.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    obj = User(self, oid=user.id, objid=user.objid, 
                               name=user.name, active=user.active, 
                               desc=user.description, model=user)
                    res.append(obj)                
            
            self.logger.debug(u'Get users: %s' % len(res))
            User(self).event(u'user.view', 
                             {u'oid':oid, u'name':name, u'role':role}, 
                             (True))            
            return res, total
        except QueryError as ex:
            User(self).event(u'user.view', 
                             {u'oid':oid, u'name':name, u'role':role}, 
                             (False, ex.desc))              
            self.logger.error(ex, exc_info=1)
            return [], 0
            #raise ApiManagerError(ex)

    @watch
    def add_user(self, username, storetype, systype, active=True, 
                       password=None, description=''):
        """Add new user.

        :param username: name of the user
        :param storetype: type of the user store. Can be DBUSER, LDAPUSER
        :param systype: type of user. User can be a human USER or a system 
                        module SYS
        :param profile: Profile name [Optional]
        :param active: User status. If True user is active [Optional] [Default=True]
        :param description: User description. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(User.objtype, User.objdef, None, u'insert')
        
        # verify permissions
        '''objs = self.can(u'insert', u'auth', definition=User.objdef)
        if len(objs) > 0 and objs[User.objdef][0].split(u'//')[-1] != '*':
            raise ApiManagerError(u'You need more privileges to add user', 
                                  code=2000)'''
                
        try:
            objid = id_gen()
            user = self.dbauth.add_user(objid, username, [], active=active, 
                                        password=password, 
                                        description=description)
            # add object and permission
            User(self).register_object([objid], desc=description)
            
            # add default attributes
            self.dbauth.set_user_attribute(user, u'store_type', storetype, 
                                           'Type of user store')
            self.dbauth.set_user_attribute(user, u'sys_type', systype, 
                                           'Type of user')            
            
            self.logger.debug(u'Add new user: %s' % username)
            User(self).event(u'user.insert', 
                             {u'username':username, u'storetype':storetype, 
                              'active':active,
                              'password':password, u'description':description}, 
                             (True))
            #user = self.get_users(name=username)[0]
            return user.id
        except TransactionError as ex:
            User(self).event(u'user.insert', 
                             {u'username':username, u'storetype':storetype, 
                              'active':active,
                              'password':password, u'description':description}, 
                             (False, ex))              
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    @watch
    def add_generic_user(self, name, storetype, password=None,
                         description=''):
        """Add cloudapi generic user. A generic user has a default role
        associated and the guest role. A generic user role has no permissions
        associated.
        
        :param name: user name
        :param storetype: type of the user. Can be DBUSER, LDAPUSER
        :param password: user password for DBUSER
        :param description: User description. [Optional]        
        :return: True if user is added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        self.add_user(name, storetype, u'USER', active=True, 
                      password=password, description=description)
        user = self.get_users(name=name)[0][0]
        self.logger.warn(self.get_users(name=name))
        # create user role
        self.add_role(u'User%sRole' % user.oid, u'User %s private role' % name)
        
        # append role to user
        user.append_role(u'User%sRole' % user.oid)
        user.append_role("Guest")
        return user.oid
    
    @watch
    def add_system_user(self, name, password=None, description=''):
        """Add cloudapi system user. A system user is used by a module to 
        call the apis of the other modules.
        
        :param name: user name
        :param password: user password for DBUSER
        :param description: User description. [Optional]        
        :return: True if user is added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        self.add_user(name, u'DBUSER', u'SYS', active=True, 
                      password=password, description=description)
        user = self.get_users(name=name)[0][0]
        
        # create user role
        self.add_role("%sRole" % name.split(u'@')[0], u'User %s private role' % name)
        
        # append role to user
        user.append_role("ApiSuperadmin")
        return user.oid
    
    #
    # group manipulation methods
    #
    @watch
    def get_groups(self, oid=None, name=None, role=None, user=None,
                  page=0, size=10, order=u'DESC', field=u'id'):
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
        :rtype: :class:`SystemGroup`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can(u'view', Group.objtype, definition=Group.objdef)
        res = []
                
        try:
            # search groups by id
            if oid:
                groups, total = self.dbauth.get_group(oid=oid)
                if not groups:
                    self.logger.warn(u'Group %s was not found' % oid)
            
            # search groups by name
            elif name:
                groups, total = self.dbauth.get_group(name=name)
                if not groups:
                    self.logger.warn(u'Group %s was not found' % name)
                
            # search groups by role
            elif role:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    role_obj = self.dbauth.get_role(uuid=role)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(role)):
                    role_obj = self.dbauth.get_role(oid=role)[0][0]
                # get obj by name
                else:
                    role_obj = self.dbauth.get_role(name=role)[0][0]
                #role_obj = self.dbauth.get_role(name=role)[0]
                groups, total = self.dbauth.get_role_groups(role_obj, page=page, 
                                        size=size, order=order, field=field)

            # search grousp by user
            elif user is not None:
                # get obj by uuid
                if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
                    user = self.dbauth.get_user(uuid=user)[0][0]
                # get link by id
                elif match(u'[0-9]+', str(user)):
                    user = self.dbauth.get_user(oid=user)[0][0]
                # get obj by name
                else:
                    user = self.dbauth.get_user(name=user)[0][0]
                    
                groups, total = self.dbauth.get_user_groups(user, 
                                                    page=page, size=size, 
                                                    order=order, field=field)              
            
            # get all groups
            else:
                groups, total = self.dbauth.get_group(page=page, size=size, 
                                                    order=order, field=field)
            
            for group in groups:
                # check authorization
                objset = set(objs[Group.objdef.lower()])

                # create needs
                needs = self.get_needs([group.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    obj = Group(self, oid=group.id, objid=group.objid, 
                                name=group.name, active=True, 
                                desc=group.description, model=group)
                    res.append(obj)                
            
            self.logger.debug(u'Get groups: %s' % len(res))
            Group(self).event(u'group.view', 
                             {u'oid':oid, u'name':name, u'role':role}, 
                             (True))            
            return res, total
        except QueryError as ex:
            Group(self).event(u'group.view', 
                             {u'oid':oid, u'name':name, u'role':role}, 
                             (False, ex.desc))              
            self.logger.error(ex, exc_info=1)
            return [], 0
            #raise ApiManagerError(ex)

    @watch
    def add_group(self, name, description=u''):
        """Add new group.

        :param name: name of the group
        :param description: Group description. [Optional]
        :return: True if group added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Group.objtype, Group.objdef, None, u'insert')
        
        # verify permissions
        '''objs = self.can(u'insert', u'auth', definition=Group.objdef)
        if len(objs) > 0 and objs[Group.objdef][0].split(u'//')[-1] != '*':
            raise ApiManagerError(u'You need more privileges to add group', 
                                  code=2000)'''
                
        try:
            objid = id_gen()
            group = self.dbauth.add_group(objid, name, description=description)
            # add object and permission
            Group(self).register_object([objid], desc=description)          
            
            self.logger.debug(u'Add new group: %s' % name)
            Group(self).event(u'group.insert', 
                             {u'name':name, u'description':description}, 
                             (True))
            #group = self.get_groups(name=groupname)[0]
            return group.id
        except TransactionError as ex:
            Group(self).event(u'group.insert', 
                             {u'name':name, u'description':description}, 
                             (False, ex))              
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)  
    
    #
    # identity manipulation methods
    #
    @watch
    def set_identity(self, uid, identity, expire=True):
        val = pickle.dumps(identity)
        self.module.redis_manager.setex(self.prefix + uid, self.expire, val)
        if expire is False:
            self.module.redis_manager.persist(self.prefix + uid)
        self.logger.debug(u'Set identity %s in redis' % uid)
        User(self).event(u'user.identity.add', 
                         {u'uid':uid}, 
                         (True))
    
    @watch
    def remove_identity(self, uid):
        if self.module.redis_manager.get(self.prefix + uid) is None:
            User(self).event(u'user.identity.delete', 
                             {u'uid':uid}, 
                             (False, "Identity %s does not exist" % uid))            
            self.logger.error("Identity %s does not exist" % uid)
            raise ApiManagerError("Identity %s does not exist" % uid, code=1115)            
        
        try:
            self.module.redis_manager.delete(self.prefix + uid)
            self.logger.debug(u'Remove identity %s from redis' % uid)
            User(self).event(u'user.identity.delete', 
                             {u'uid':uid}, 
                             (True))            
            return True
        except Exception as ex:
            User(self).event(u'user.identity.delete', 
                             {u'uid':uid}, 
                             (False, ex))            
            self.logger.error("Can not remove identity %s" % uid)
            raise ApiManagerError("Can not remove identity %s" % uid, code=1115)       

    @watch
    def exist_identity(self, uid):
        """Get identity
        :return: True or False
        :rtype: dict
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error("Identity %s retrieve error: %s" % (uid, ex))
            raise ApiManagerError("Identity %s retrieve error" % uid, code=1014)
        
        if identity is not None:
            self.logger.debug(u'Identity %s exists' % (uid))           
            return True
        else:
            self.logger.debug(u'Identity does not %s exists' % (uid))           
            return False            
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=1014)

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
            self.logger.error("Identity %s retrieve error: %s" % (uid, ex))
            raise ApiManagerError("Identity %s retrieve error" % uid, code=404)
            
        if identity is not None:
            data = pickle.loads(identity)
            data[u'ttl'] = self.module.redis_manager.ttl(self.prefix + uid)
            self.logger.debug(u'Get identity %s from redis: %s' % (uid, truncate(data)))   
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=404)

    @watch
    def get_identities(self):
        try:
            res =  []
            for key in self.module.redis_manager.keys(self.prefix+'*'):
                identity = self.module.redis_manager.get(key)
                data = pickle.loads(identity)
                ttl = self.module.redis_manager.ttl(key)
                res.append({u'uid':data[u'uid'], u'user':data[u'user'][u'name'],
                            'timestamp':data[u'timestamp'], u'ttl':ttl, 
                            'ip':data[u'ip']})
        except Exception as ex:
            self.logger.error(u'No identities found: %s' % ex)
            raise ApiManagerError(u'No identities found')
        
        User(self).event(u'user.identity.get', {}, (True))
        self.logger.debug(u'Get identities from redis: %s' % (res))
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
            timestamp = datetime.now().strftime(u'%y-%m-%d-%H-%M')        
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
    
            res = {u'uid':uid,
                   u'user':user.get_dict(),
                   u'timestamp':timestamp,
                   u'pubkey':pubkey,
                   u'seckey':seckey}
        except Exception as ex:
            User(self).event(u'login.keyauth', opts, (False, ex))
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
        except ApiManagerError as ex:
            User(self).event(u'login', {u'name':name, u'domain':domain, 
                              u'password':u'xxxxxxx', u'login_ip':login_ip}, 
                             (False, ex.value))
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
            dbuser = self.dbauth.get_user(name=user_name)[0][0]
            # get user attributes
            dbuser_attribs = {a.name:(a.value, a.desc) for a in dbuser.attrib}
        except (QueryError, Exception) as ex:
            msg = u'User %s does not exist' % user_name
            User(self).event(u'User.get', 
                             {u'name':name, u'domain':domain, 
                              u'password':u'xxxxxxx', u'login_ip':login_ip}, 
                             (False, msg))
            self.logger.error(msg, exc_info=1)
            raise ApiManagerError(msg, code=404)
        
        self.logger.debug(u'User %s exists' % user_name)
        
        return dbuser, dbuser_attribs   
    
    @watch
    def base_login(self, name, domain, password, login_ip, 
                     dbuser, dbuser_attribs):
        """Simple http authentication login.
        
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
            User(self).event(u'login', opts, (False, ex.desc))
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
            User(self).event(u'login', opts, (False, ex.desc))
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
        self.validate_login_params(name, domain, password, login_ip)
        
        # check user
        dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                   password, login_ip)        
        
        # check user has authentication filter
        auth_filters = dbuser_attribs.get(u'auth-filters', (u'', None))[0].split(u',')
        if u'simplehttp' not in auth_filters:
            msg = u'Simple http authentication is not allowed for user %s' % \
                  user_name
            User(self).event(u'login.simplehttp', opts, (False, msg))
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
            User(self).event(u'login.simplehttp', opts, (False, msg))
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)            
        
        # login user
        user, attrib = self.base_login(name, domain, password, login_ip, 
                                         dbuser, dbuser_attribs)
        
        res = {u'uid':id_gen(20),
               u'type':u'simplehttp',
               u'user':user.get_dict(),
               u'timestamp':datetime.now().strftime(u'%y-%m-%d-%H-%M')}        
        
        User(self).event(u'login.simplehttp', opts, (True))
        
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
        # validate input params
        self.validate_login_params(name, domain, password, login_ip)
        
        # check user
        dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                   password, login_ip)        
        
        # check user attributes
        
        # login user
        user, attrib = self.base_login(name, domain, password, login_ip, 
                                         dbuser, dbuser_attribs)
        

        # generate asymmetric keys
        res = self._gen_authorizaion_key(user, domain, name, login_ip, attrib)

        User(self).event(u'user.login',
                         {u'name':name, u'domain':domain, u'password':u'xxxxxxx', 
                          u'login_ip':login_ip},
                         (True))
        
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
            User(self).event(u'user.login.delete', {u'uid':uid}, (True))
        except Exception as ex:
            User(self).event(u'user.login.delete', {u'uid':uid}, (False, ex))
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=1013)
                
        return res
    
    @watch
    def refresh_user(self, uid, sign, data):
        """Refresh permissions stored in redis identity for a logged user
        """
        # get identity and verify signature
        #identity = self.verify_request_signature(uid, sign, data)
        #operation.user = (identity[u'user'][u'name'], identity[u'ip'], identity[u'uid'])

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
            dbuser = self.dbauth.get_user(name=user_name)[0]
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

            User(self).event(u'user.login.update', 
                             {u'name':user_name, u'login_ip':identity[u'ip']}, 
                             (True))    
        except QueryError as ex:
            User(self).event(u'user.login.update',
                             {u'name':user_name, u'login_ip':identity[u'ip']}, 
                             (False, ex.desc))
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=400)
        except Exception as ex:
            User(self).event(u'user.login.update',
                             {u'name':user_name, u'login_ip':identity[u'ip']}, 
                             (False, ex))
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
        """ """
        try:
            role, total = self.dbauth.get_role(name=role_name)
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
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)

        try:  
            data, total = self.dbauth.get_object_type(
                        oid=oid, objtype=objtype, objdef=objdef, 
                        page=page, size=size, order=order, field=field)

            #res = [[i.id, i.objtype, i.objdef, i.objclass) for i in data 
            #       if i.objtype != 'event']
            res = [{u'id':i.id, u'subsystem':i.objtype, u'type':i.objdef}
                    for i in data] #if i.objtype != u'event']            
            self.event(u'objects.type.view', 
                       {u'oid':oid, u'objtype':objtype, u'objdef':objdef}, 
                       (True))
            return res, total
        except QueryError as ex:
            self.event(u'objects.type.view', 
                       {u'oid':oid, u'objtype':objtype, u'objdef':objdef}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            return [], 0
            #raise ApiManagerError(ex)
    
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
            self.event(u'objects.type.insert', {u'obj_types':obj_types}, (True))
            return [i.id for i in res]
        except TransactionError as ex:
            self.event(u'objects.type.insert', {u'obj_types':obj_types}, 
                       (False, ex.desc))
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
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:  
            res = self.dbauth.remove_object_type(oid=oid, objtype=objtype, 
                                                 objdef=objdef)
            self.event(u'objects.type.delete', 
                       {u'oid':oid, u'objtype':objtype, u'objdef':objdef}, 
                       (True))            
            return res
        except TransactionError as ex:
            self.event(u'objects.type.delete', 
                       {u'oid':oid, u'objtype':objtype, u'objdef':objdef}, 
                       (False, ex.desc))
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
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            data = self.dbauth.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError(u'No data found')
            if type(data) is not list:
                data = [data]            
            res = [{u'id':i.id, u'value':i.value} for i in data]
            self.event(u'objects.action.view', {u'oid':oid, u'value':value}, 
                       (True))
            return res
        except QueryError as ex:
            self.event(u'objects.action.view', {u'oid':oid, u'value':value}, 
                       (False, ex.desc))
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
            self.event(u'objects.action.insert', {u'actions':actions}, (True))
            return True
        except TransactionError as ex:
            self.event(u'objects.action.insert', {u'actions':actions}, 
                       (False, ex.desc))
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
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:
            res = self.dbauth.remove_object_action(oid=oid, value=value)
            self.event(u'objects.action.delete', {u'oid':oid, u'value':value}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event(u'objects.action.delete', {u'oid':oid, u'value':value}, 
                       (False, ex.desc))
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
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:
            '''# get object types
            if objtype is not None or objdef is not None:
                obj_types = self.dbauth.get_object_type(objtype=objtype, 
                                                        objdef=objdef)
                # get objects
                data = []
                total = 0
                for obj_type in obj_types:
                    #if obj_type.objtype != 'event':
                    pdata, ptotal = self.dbauth.get_object(
                            oid=oid, objid=objid, objtype=obj_type, 
                            objdef=objdef, page=int(page), size=int(size))
                    data.extend(pdata)
                    total += ptotal
            else:'''
            data,total = self.dbauth.get_object(oid=oid, objid=objid, 
                    objtype=objtype, objdef=objdef, page=page, size=size,
                    order=order, field=field)
                    
            #res = [(i.id, i.type.objtype, i.type.objdef, i.objid, i.desc) 
            #       for i in data]
            res = [{
                u'id':i.id,
                u'subsystem':i.type.objtype,
                u'type':i.type.objdef,
                u'objid':i.objid,
                u'desc':i.desc
            } for i in data]
            self.logger.debug(u'Get objects: %s' % len(res))
            self.event(u'objects.view', 
                       {u'oid':oid, u'objid':objid, u'objtype':objtype, 
                        'objdef':objdef}, 
                       (True))
            return res, total
        except QueryError as ex:
            self.event(u'objects.view', 
                       {u'oid':oid, u'objid':objid, u'objtype':objtype, 
                        'objdef':objdef}, 
                       (False, ex.desc))            
            self.logger.error(ex.desc, exc_info=1)
            return [], 0
        except Exception as ex:
            self.event(u'objects.view', 
                       {u'oid':oid, u'objid':objid, u'objtype':objtype, 
                        'objdef':objdef}, 
                       (False, ex))            
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
            self.event(u'objects.insert', {u'objs':objs}, (True))        
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'objects.insert', {u'objs':objs}, (False, ex.desc))
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
            self.event(u'objects.delete', 
                       {u'oid':oid, u'objid':objid, u'objtype':objtype, 
                        'objdef':objdef}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event(u'objects.delete', 
                       {u'oid':oid, u'objid':objid, u'objtype':objtype, 
                        'objdef':objdef}, 
                       (False, ex.desc))            
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
            
            '''res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.type.objclass, i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]'''
            res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]            

            self.logger.debug(u'Get permissions: %s' % len(res))
            self.event(u'objects.permission.view', 
                       {u'permission_id':permission_id, u'objid':objid, 
                        'objtype':objtype, u'objdef':objdef, 
                        'action':action}, 
                       (True))              
            return res
        except QueryError as ex:
            self.event(u'objects.permission.view', 
                       {u'permission_id':permission_id, u'objid':objid, 
                        'objtype':objtype, u'objdef':objdef, 
                        'action':action}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

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
                '''res.append(((p.id, p.obj.id, p.obj.type.objtype, 
                             p.obj.type.objdef, p.obj.type.objclass, 
                             p.obj.objid, p.action.id, p.action.value, 
                             p.obj.desc), roles))'''
                '''res.append(((p.id, p.obj.id, p.obj.type.objtype, 
                             p.obj.type.objdef, 
                             p.obj.objid, p.action.id, p.action.value, 
                             p.obj.desc), roles))'''
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
            self.event(u'objects.permission.view', 
                       {u'objid':objid, u'objtype':objtype, u'objdef':objdef}, 
                       (True))              
            return res, total
        except QueryError as ex:
            self.event(u'objects.permission.view', 
                       {u'objid':objid, u'objtype':objtype, u'objdef':objdef}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            return [], 0
            #raise ApiManagerError(ex)

class Role(AuthObject):
    objdef = u'Role'
    objdesc = u'System roles'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        if self.model is not None:
            self.uuid = self.model.uuid

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
                                .strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%y %H:%M:%S'))   
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
    def update(self, new_name=None, new_description=None):
        """Update a role.
        
        :param new_name: new role name [optional]
        :param new_description: new role description [optional]
        :return: True if role updated correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:  
            res = self.dbauth.update_role(oid=self.oid, new_name=new_name, 
                                          new_description=new_description)
            # update object reference
            #self.dbauth.update_object(new_name, objid=self.objid)
            #self.objid = new_name
            
            self.logger.debug(u'Update role: %s' % self.name)
            self.event(u'role.update', 
                       {u'name':self.name, u'new_name':new_name, 
                        'new_description':new_description}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event(u'role.update',
                       {u'name':self.name, u'new_name':new_name, 
                        'new_description':new_description}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Delete role.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:  
            res = self.dbauth.remove_role(role_id=self.oid)
            # remove object and permissions
            self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete role: %s' % self.name)
            self.event(u'role.delete', 
                       {u'name':self.name}, 
                       (True))            
            return res
        except TransactionError as ex:
            self.event(u'role.delete', 
                       {u'name':self.name}, 
                       (False, ex.desc))            
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
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            perms, total = self.dbauth.get_role_permissions([self.name], 
                            page=page, size=size, order=order, field=field)      
            role_perms = []
            for i in perms:
                '''user_perms.append((i.id, i.obj.id, i.obj.type.objtype, 
                                   i.obj.type.objdef, i.obj.type.objclass, 
                                   i.obj.objid, i.action.id, i.action.value,
                                   i.obj.desc))'''
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
            self.event(u'role.permission.view', {u'name':self.name}, (True))
            return role_perms, total
        except QueryError as ex:
            self.event(u'role.permission.view', {u'name':self.name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
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
            self.event(u'role.permission.update', 
                       {u'name':self.name}, 
                       (True))               
            return res
        except QueryError as ex:
            self.event(u'role.permission.update', 
                       {u'name':self.name}, 
                       (False, ex.desc))             
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
            self.event(u'role.permission.update', 
                       {u'name':self.name}, 
                       (True))             
            return res
        except QueryError as ex:
            self.event(u'role.permission.update', 
                       {u'name':self.name}, 
                       (False, ex.desc))              
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

class User(AuthObject):
    objdef = u'User'
    objdesc = u'System users'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
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
                                .strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%y %H:%M:%S'))
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
            #u'attribute':attrib,
            u'active':self.active, 
            u'date':{
                u'creation':creation_date,
                u'modified':modification_date
            }
        }

    @watch
    def update(self, new_name=None, new_storetype=None, new_description=None, 
                     new_active=None, new_password=None):
        """Update a user.
        
        :param username: user name
        :param new_name: new user name [optional]
        :param new_storetype: new type of the user. Can be DBUSER, LDAPUSER [optional]
        :param new_description: new user description [optional]
        :param new_active: new user status [optional]
        :param new_password: new user password [optional]
        :return: True if user updated correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            res = self.dbauth.update_user(oid=self.oid, new_name=new_name,
                                          new_description=new_description, 
                                          new_active=new_active, 
                                          new_password=new_password)
            if new_storetype is not None:
                self.dbauth.set_user_attribute(self.model, u'store_type', 
                                               new_storetype)
            
            # update object reference
            #self.dbauth.update_object(new_name, objid=self.objid)
            #self.objid = new_name            
            
            self.logger.debug(u'Update user: %s' % self.name)
            self.event(u'user.update', 
                       {u'name':self.name, u'new_name':new_name, 
                        u'new_storetype':new_storetype, 
                        u'new_description':new_description, 
                        u'new_active':new_active, u'new_password':u'xxxxxxxx'}, 
                       (True))               
            return res
        except TransactionError as ex:
            self.event(u'user.update', 
                       {u'name':self.name, u'new_name':new_name, 
                        u'new_storetype':new_storetype, 
                        u'new_description':new_description, 
                        u'new_active':new_active, u'new_password':u'xxxxxxxx'}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Delete a user.
        
        :return: True if user deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            res = self.dbauth.remove_user(username=self.name)
            # remove object and permission
            self.deregister_object([self.objid])
            
            try:
                # generic ueser has specific role associated. Delete also role
                role = self.controller.get_roles(name="%sRole" % self.name.split(u'@')[0])[0]
                role.delete()
            except Exception as ex:
                self.logger.warning(u'User %s has not role associated' % self.name)
            
            self.logger.debug(u'Delete user: %s' % self.name)
            self.event(u'user.delete', 
                       {u'name':self.name}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event(u'user.delete', 
                       {u'name':self.name}, 
                       (False, ex.desc))            
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
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.dbauth.set_user_attribute(self.model, name, value=value, 
                                                 desc=desc, new_name=new_name)
            self.logger.debug(u'Set user %s attribute %s: %s' % 
                              (self.name, name, value))
            self.event(u'user.attribute.update', 
                       {u'name':self.name, u'attrib':name, u'value':value}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'user.attribute.update', 
                       {u'name':self.name, u'attrib':name, u'value':value}, 
                       (False, ex.desc))
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
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.dbauth.remove_user_attribute(self.model, name)
            self.logger.debug(u'Remove user %s attribute %s' % (self.name, name))
            self.event(u'user.attribute.update', 
                       {u'name':self.name, u'attrib':name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'user.attribute.update', 
                       {u'name':self.name, u'attrib':name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def append_role(self, role_name):
        """Append role to user.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role, total = self.dbauth.get_role(name=role_name)
            if total <= 0:
                raise QueryError(u'Role %s does not exist' % role_name)
            else:
                role = role[0]          
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:            
            self.logger.warn(role)
            self.logger.warn(total)
            res = self.dbauth.append_user_role(self.model, role)
            if res is True: 
                self.logger.debug(u'Append role %s to user %s' % (
                                            role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with user %s' % (
                                            role, self.name))
            self.event(u'user.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'user.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_role(self, role_name):
        """Remove role from user.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role, total = self.dbauth.get_role(name=role_name)
            if total <= 0:
                raise QueryError(u'Role %s does not exist' % role_name)
            else:
                role = role[0]          
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.dbauth.remove_user_role(self.model, role)
            self.logger.debug(u'Remove role %s from user %s' % (role, self.name))
            self.event(u'user.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (True))            
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'user.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))            
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
            self.event(u'user.permission.view', {u'name':self.name}, (True))
            return user_perms, total
        except QueryError as ex:
            self.event(u'user.permission.view', {u'name':self.name}, 
                       (False, ex.desc))
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
                
            User(self).event(u'user.can.use', 
                             {u'action':action, u'objtype':objtype, 
                              'definition':definition, u'name':self.name, 
                              'perms':perms}, 
                             (True))                 
        except Exception as ex:
            User(self).event(u'user.can.use', 
                             {u'action':action, u'objtype':objtype, 
                              'definition':definition, u'name':self.name, 
                              'perms':perms}, 
                             (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
class Group(AuthObject):
    objdef = u'Group'
    objdesc = u'System groups'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
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
                                .strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%y %H:%M:%S'))
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
    def update(self, new_name=None, new_description=None, 
                     new_active=None, new_password=None):
        """Update a group.
        
        :param groupname: group name
        :param new_name: new group name [optional]
        :param new_storetype: new type of the group. Can be DBUSER, LDAPUSER [optional]
        :param new_description: new group description [optional]
        :param new_active: new group status [optional]
        :param new_password: new group password [optional]
        :return: True if group updated correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            res = self.dbauth.update_group(oid=self.oid, new_name=new_name,
                                          new_description=new_description)
            
            self.logger.debug(u'Update group: %s' % self.name)
            self.event(u'group.update', 
                       {u'name':self.name, u'new_name':new_name, 
                        u'new_description':new_description, 
                        u'new_active':new_active, u'new_password':u'xxxxxxxx'}, 
                       (True))               
            return res
        except TransactionError as ex:
            self.event(u'group.update', 
                       {u'name':self.name, u'new_name':new_name, 
                        u'new_description':new_description, 
                        u'new_active':new_active, u'new_password':u'xxxxxxxx'}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Delete a group.
        
        :return: True if group deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            res = self.dbauth.remove_group(group_id=self.oid)
            # remove object and permission
            self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete group: %s' % self.name)
            self.event(u'group.delete', 
                       {u'name':self.name}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event(u'group.delete', 
                       {u'name':self.name}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def append_role(self, role_name):
        """Append role to group.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role, total = self.dbauth.get_role(name=role_name)
            if total <= 0:
                raise QueryError(u'Role %s does not exist' % role_name)
            else:
                role = role[0]  
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
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
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_role(self, role_name):
        """Remove role from group.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role, total = self.dbauth.get_role(name=role_name)
            if total <= 0:
                raise QueryError(u'Role %s does not exist' % role_name)
            else:
                role = role[0]  
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.dbauth.remove_group_role(self.model, role)
            self.logger.debug(u'Remove role %s from group %s' % (role, self.name))
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (True))            
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'group.role.update', 
                       {u'name':self.name, u'role':role_name}, 
                       (False, ex.desc))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def append_user(self, user_name):
        """Append user to group.
        
        :param user_name: user name
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user, total = self.dbauth.get_user(name=user_name)
            if total <= 0:
                raise QueryError(u'User %s does not exist' % user_name)
            else:
                user = user[0]  
        except (QueryError, TransactionError) as ex:
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (False, ex.desc))
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
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_user(self, user_name):
        """Remove user from group.
        
        :param user_name: user name
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user, total = self.dbauth.get_user(name=user_name)
            if total <= 0:
                raise QueryError(u'User %s does not exist' % user_name)
            else:
                user = user[0]  
        except (QueryError, TransactionError) as ex:
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (False, ex.desc))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, 
                                            user.objid, u'view')

        try:
            res = self.dbauth.remove_group_user(self.model, user)
            self.logger.debug(u'Remove user %s from group %s' % (user, self.name))
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (True))            
            return res
        except (QueryError, TransactionError) as ex:
            self.event(u'group.user.update', 
                       {u'name':self.name, u'user':user_name}, 
                       (False, ex.desc))            
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
            self.event(u'group.permission.view', {u'name':self.name}, (True))
            return group_perms, total
        except QueryError as ex:
            self.event(u'group.permission.view', {u'name':self.name}, 
                       (False, ex.desc))
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
                
            Group(self).event(u'group.can.use', 
                             {u'action':action, u'objtype':objtype, 
                              u'definition':definition, u'name':self.name, 
                              u'perms':perms}, 
                             (True))                 
        except Exception as ex:
            Group(self).event(u'group.can.use', 
                             {u'action':action, u'objtype':objtype, 
                              u'definition':definition, u'name':self.name, 
                              u'perms':perms}, 
                             (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
           
        
        