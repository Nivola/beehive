'''
Created on Jan 16, 2014

@author: darkbk
'''
from datetime import datetime
from beecell.auth import extract
#from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate
from beehive.common.apimanager import ApiManagerError, ApiObject
from beecell.db import TransactionError, QueryError
from beehive.common.controller.authorization import BaseAuthController, \
     User as BaseUser, Token, AuthObject
from beehive.common.data import trace
from beehive.common.model.authorization import User as ModelUser, \
    Role as ModelRole, Group as ModelGroup, SysObject as ModelObject

class AuthController(BaseAuthController):
    """Auth Module controller.
    
    :param module: Beehive module
    """
    version = u'v1.0'    
    
    def __init__(self, module):
        BaseAuthController.__init__(self, module)
        
        self.objects = Objects(self)
        self.child_classes = [Objects, Role, User, Group, Token]
    
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        # add actions
        try:
            actions = [u'*', u'view', u'insert', u'update', u'delete', u'use']
            self.manager.add_object_actions(actions)
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
        BaseAuthController.init_object(self)
    
    def count(self):
        """Count users, groups, roles and objects
        """
        try:
            res = {u'users':self.manager.count_entities(ModelUser),
                   u'groups':self.manager.count_entities(ModelGroup),
                   u'roles':self.manager.count_entities(ModelRole),
                   u'objects':self.manager.count_entities(ModelObject)}
            return res
        except QueryError as ex:
            raise ApiManagerError(ex, code=ex.code)
    
    #
    # role manipulation methods
    #
    @trace(entity=u'Role', op=u'view')
    def get_role(self, oid):
        """Get single role.

        :param oid: entity model id or name or uuid         
        :return: Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_object(Role, ModelRole, oid)
    
    @trace(entity=u'Role', op=u'view')
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
                perm = self.manager.get_permission_by_object(
                    objid=objid, objtype=objtype,  objdef=objdef, action=action)[0]
                roles, total = self.manager.get_permission_roles(
                    perm, *args, **kvargs)

            # search roles by user
            elif user is not None:
                kvargs[u'user'] = self.manager.get_entity(ModelUser, user)
                #self.get_entity(user, self.manager.get_users)
                roles, total = self.manager.get_user_roles_with_expiry(*args, **kvargs)

            # search roles by group
            elif group is not None:
                kvargs[u'group'] = self.manager.get_entity(ModelUser, group)
                #kvargs[u'group'] = self.get_entity(group, self.manager.get_groups)
                roles, total = self.manager.get_group_roles(*args, **kvargs)
            
            # get all roles
            else:
                roles, total = self.manager.get_roles(*args, **kvargs)
            
            return roles, total
        
        res, total = self.get_paginated_objects(Role, get_entities, 
                                                *args, **kvargs)
        return res, total    
    
    @trace(entity=u'Role', op=u'insert')
    def add_role(self, name, description=u''):
        """Add new role.

        :param name: name of the role
        :param description: role description. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, u'insert')            

        try:
            objid = id_gen()
            role = self.manager.add_role(objid, name, description)
            
            # add object and permission
            Role(self, oid=role.id).register_object([objid], desc=description)

            self.logger.debug(u'Add new role: %s' % name)
            return role.id
        except (TransactionError) as ex:       
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
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
            self.manager.append_role_permissions(role, perms)
            return role
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_role(u'Guest', u'Beehive guest role')        
        return role

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
    @trace(entity=u'User', op=u'view')
    def get_user(self, oid):
        """Get single user.

        :param oid: entity model id or name or uuid         
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_object(User, ModelUser, oid)    
    
    @trace(entity=u'User', op=u'view')
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
                kvargs[u'role'] = self.manager.get_entity(ModelRole, role)
                users, total = self.manager.get_role_users(*args, **kvargs)

            # search users by group
            elif group is not None:
                kvargs[u'group'] = self.manager.get_entity(ModelGroup, group)
                users, total = self.manager.get_group_users(*args, **kvargs)
            
            # get all users
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split(u'-')
                    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                users, total = self.manager.get_users(*args, **kvargs)            
            
            return users, total
        print args, kvargs
        res, total = self.get_paginated_objects(User, get_entities, 
                                                *args, **kvargs)
        return res, total

    @trace(entity=u'User', op=u'insert')
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
        # check authorization
        self.check_authorization(User.objtype, User.objdef, None, u'insert')
        
        try:
            objid = id_gen()
            if expiry_date is not None:
                g, m, y = expiry_date.split(u'-')
                expiry_date = datetime(int(y), int(m), int(g))
            user = self.manager.add_user(objid, name, active=active, 
                                        password=password, 
                                        desc=description, 
                                        expiry_date=expiry_date)
            # add object and permission
            User(self, oid=user.id).register_object([objid], desc=description)
            
            # add default attributes
            self.manager.set_user_attribute(user, u'store_type', storetype, 
                                           u'Type of user store')
            self.manager.set_user_attribute(user, u'sys_type', systype, 
                                           u'Type of user')            
            
            self.logger.debug(u'Add new user: %s' % name)
            return user.id
        except (TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    @trace(entity=u'User', op=u'generic.insert')
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
    
    @trace(entity=u'User', op=u'system.insert')
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
    @trace(entity=u'Group', op=u'view')
    def get_group(self, oid):
        """Get single group.

        :param oid: entity model id or name or uuid         
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_object(Group, ModelGroup, oid)    
    
    @trace(entity=u'Group', op=u'view')
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
                kvargs[u'role'] = self.manager.get_entity(ModelRole, role)
                groups, total = self.manager.get_role_groups(*args, **kvargs)

            # search groups by user
            elif user is not None:
                kvargs[u'user'] = self.manager.get_entity(ModelUser, user)
                groups, total = self.manager.get_user_groups(*args, **kvargs)
            
            # get all groups
            else:
                #if expiry_date is not None:
                #    g, m, y = expiry_date.split(u'-')
                #    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                groups, total = self.manager.get_groups(*args, **kvargs)            
            
            return groups, total
        
        res, total = self.get_paginated_objects(Group, get_entities, *args, **kvargs)
        return res, total

    @trace(entity=u'Group', op=u'insert')
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
        
        try:
            objid = id_gen()
            group = self.manager.add_group(objid, name, desc=description)
            
            # add object and permission
            Group(self, oid=group.id).register_object([objid], desc=description)          
            
            self.logger.debug(u'Add new group: %s' % name)
            return group.id
        except (TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

class Objects(AuthObject):
    objdef = u'Objects'
    objdesc = u'Authorization objects'
    
    def __init__(self, controller):
        AuthObject.__init__(self, controller, oid=u'', name=u'', desc=u'', 
                            active=True)
    
    #
    # System Object Type manipulation methods
    #    
    @trace(op=u'types.view')
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
        #opts = {u'oid':oid, u'objtype':objtype, u'objdef':objdef,
        #        u'page':page, u'size':size, u'order':order, u'field':field}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)

        try:  
            data, total = self.manager.get_object_type(
                        oid=oid, objtype=objtype, objdef=objdef, 
                        page=page, size=size, order=order, field=field)

            res = [{u'id':i.id, u'subsystem':i.objtype, u'type':i.objdef}
                    for i in data] #if i.objtype != u'event']
            #self.send_event(u'type.view', params=opts)
            return res, total
        except QueryError as ex:
            #self.send_event(u'type.view', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            return [], 0
    
    @trace(op=u'types.insert')
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
            res = self.manager.add_object_types(data)
            #self.send_event(u'type.insert', params=obj_types)
            return [i.id for i in res]
        except TransactionError as ex:
            #self.send_event(u'type.insert', params=obj_types, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @trace(op=u'types.delete')
    def remove_type(self, oid=None, objtype=None, objdef=None):
        """Remove system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        #params = {u'oid':oid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:  
            res = self.manager.remove_object_type(oid=oid, objtype=objtype, 
                                                 objdef=objdef)
            #self.send_event(u'type.delete', params=params)          
            return res
        except TransactionError as ex:
            #self.send_event(u'type.delete', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object Action manipulation methods
    #
    @trace(op=u'actions.view')
    def get_action(self, oid=None, value=None):
        """Get system object action.
        
        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: List of Tuple (id, value)   
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        #params = {u'oid':oid, u'value':value}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            data = self.manager.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError(u'No data found')
            if type(data) is not list:
                data = [data]            
            res = [{u'id':i.id, u'value':i.value} for i in data]
            #self.send_event(u'action.view', params=params)
            return res
        except QueryError as ex:
            #self.send_event(u'action.view', params=params, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @trace(op=u'actions.insert')
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
            res = self.manager.add_object_actions(actions)
            return True
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
    @trace(op=u'actions.delete')
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
            res = self.manager.remove_object_action(oid=oid, value=value)
            return res
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object manipulation methods
    #
    @trace(op=u'view')
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
            data,total = self.manager.get_object(oid=oid, objid=objid, 
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
            return res, total
        except QueryError as ex:
            self.logger.error(ex.desc, exc_info=1)
            return [], 0
        except Exception as ex:        
            self.logger.error(ex, exc_info=1)
            return [], 0        

    @trace(op=u'insert')
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
            actions = self.manager.get_object_action()            
            
            # create objects
            data = []
            for obj in objs:
                obj_type, total = self.manager.get_object_type(
                    objtype=obj[u'subsystem'], objdef=obj[u'type'])
                data.append((obj_type[0], obj[u'objid'], obj[u'desc']))

            res = self.manager.add_object(data, actions)
            self.logger.debug(u'Add objects: %s' % res)
            #self.send_event(u'insert', params=objs)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'insert', params=objs, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)  

    @trace(op=u'delete')
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
        #opts = {u'oid':oid, u'objid':objid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'delete', self.objtype, definition=self.objdef)
                
        try:
            if objtype is not None or objdef is not None:
                # get object types
                obj_types = self.manager.get_object_type(objtype=objtype, 
                                                        objdef=objdef)
                for obj_type in obj_types:            
                    res = self.manager.remove_object(oid=oid, objid=objid, 
                                                    objtype=obj_type)
            else:
                res = self.manager.remove_object(oid=oid, objid=objid)
            self.logger.debug(u'Remove objects: %s' % res)
            #self.send_event(u'delete', params=opts)
            return res
        except TransactionError as ex:
            #self.send_event(u'delete', params=opts, exception=ex)     
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)          

    @trace(op=u'perms.view')
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
        #opts = {u'permission_id':permission_id, u'objid':objid, 
        #        u'objtype':objtype, u'objdef':objdef, u'action':action}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:
            if permission_id is not None:
                res = self.manager.get_permission_by_id(permission_id=permission_id)
            elif objid is not None or objtype is not None or objdef is not None:
                res = self.manager.get_permission_by_object(objid=objid, 
                                                           objtype=objtype, 
                                                           objdef=objdef,
                                                           action=action)
            else:
                res = self.manager.get_permission_by_id()
            
            res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]            

            self.logger.debug(u'Get permissions: %s' % len(res))
            #self.send_event(u'perms.view', params=opts)          
            return res
        except QueryError as ex:
            #self.send_event(u'perms.view', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return []

    @trace(op=u'perms.view')
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
        #opts = {u'objid':objid, u'objtype':objtype, u'objdef':objdef}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)        
        
        try:
            res = []
            if oid is not None:
                perms = self.manager.get_permission_by_id(permission_id=oid)
                total = 1
            
            # get permissions
            else:
                perms, total = self.manager.get_permission_by_object(
                            objid=objid, objid_filter=None, objtype=objtype, 
                            objdef=objdef, objdef_filter=None, action=None,
                            page=page, size=size, order=order, field=field)
                
            for p in perms:
                try:
                    #roles = [(r.id, r.name, r.description) for r in 
                    #         self.manager.get_permission_roles(p)]
                    roles = [{u'id':r.id, 
                              u'name':r.name, 
                              u'desc':r.desc} for r in 
                             self.manager.get_permission_roles(p)]
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
            #self.send_event(u'perms.view', params=opts)           
            return res, total
        except QueryError as ex:
            #self.send_event(u'perms.view', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return [], 0

class Role(AuthObject):
    objdef = u'Role'
    objdesc = u'System roles'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_role
        self.delete_object = self.manager.remove_role
        
        #if self.model is not None:
        #    self.uuid = self.model.uuid
        self.expiry_date = None

    def info(self):
        """Get role info
        
        :return: Dictionary with role info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
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

    @trace(op=u'perms.view')
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: dictionary with permissions
        :rtype: dict
        :raises ApiManagerError: if query empty return error.
        """
        try:  
            perms, total = self.manager.get_role_permissions([self.name], 
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
            #self.send_event(u'perms.view', params=opts)           
            return role_perms, total
        except QueryError as ex:
            #self.send_event(u'perms.view', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            return [], 0    

    @trace(op=u'perms.update')
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
                perms, total = self.manager.get_permission_by_object(
                        objid=perm[4], objtype=perm[2], objdef=perm[3],
                        action=perm[6], size=1000)
                roleperms.extend(perms)
            
            res = self.manager.append_role_permissions(self.model, roleperms)
            self.logger.debug(u'Append role %s permission : %s' % (self.name, perms))
            #self.send_event(u'perms-set.update', params=opts)            
            return res
        except QueryError as ex:
            #self.send_event(u'perms-set.update', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @trace(op=u'perms.update')
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
                perms, total = self.manager.get_permission_by_object(
                        objid=perm[4], objtype=perm[2], objdef=perm[3],
                        action=perm[6], size=1000)
                roleperms.extend(perms)        
            
            res = self.manager.remove_role_permission(self.model, roleperms)
            self.logger.debug(u'Remove role %s permission : %s' % (self.name, perms))
            #self.send_event(u'perms-unset.update', params=opts)       
            return res
        except QueryError as ex:
            #self.send_event(u'perms-unset.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

class User(BaseUser):
    objdef = u'User'
    objdesc = u'System users'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        BaseUser.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_user
        self.delete_object = self.manager.remove_user        
        
        #if self.model is not None:
        #    self.uuid = self.model.uuid

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

    @trace(op=u'delete')
    def delete(self):
        """Delete entity.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #params = {u'id':self.oid}
        
        if self.delete_object is None:
            raise ApiManagerError(u'Delete is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))        
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            # remove associated roles
            roles, total = self.manager.get_user_roles(user=self.model, size=1000)
            for role in roles:
                res = self.manager.remove_user_role(self.model, role)
            
            # delete user
            res = self.delete_object(oid=self.oid)
            # remove object and permissions
            self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete %s: %s' % (self.objdef, self.oid))
            #self.send_event(u'delete', params=params)
            return res
        except TransactionError as ex:
            #self.send_event(u'delete', params=params, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'attribs-get.update')
    def get_attribs(self):
        attrib = [{u'name':a.name, u'value':a.value, u'desc':a.desc}
                   for a in self.model.attrib]
        self.logger.debug(u'User %s attributes: %s' % (self.name, attrib))
        return attrib   
    
    @trace(op=u'attribs-set.update')
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
        #opts = {u'name':self.name, u'attrib':name, u'value':value}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.manager.set_user_attribute(self.model, name, value=value, 
                                                 desc=desc, new_name=new_name)
            self.logger.debug(u'Set user %s attribute %s: %s' % 
                              (self.name, name, value))
            #self.send_event(u'attrib-set.update', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'attrib-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @trace(op=u'attribs-unset.update')
    def remove_attribute(self, name):
        """Remove an attribute
        
        :param name: attribute name
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`           
        """
        #opts = {u'name':self.name}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')

        try:
            res = self.manager.remove_user_attribute(self.model, name)
            self.logger.debug(u'Remove user %s attribute %s' % (self.name, name))
            #self.send_event(u'attrib-unset.update', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'attrib-unset.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @trace(op=u'roles-set.update')
    def append_role(self, role_id, expiry_date=None):
        """Append role to user.
        
        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'role':role_id, u'expiry_date':expiry_date}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.manager.get_entity(ModelRole, role_id)
            #role = self.controller.get_entity(role_id, self.manager.get_roles)         
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-set.update', params=opts, exception=ex)
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
            res = self.manager.append_user_role(self.model, role, 
                                                expiry_date=expiry_date_obj)
            if res is True: 
                self.logger.debug(u'Append role %s to user %s' % (
                                            role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with user %s' % (
                                            role, self.name))
            #self.send_event(u'role-set.update', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'roles-unset.update')
    def remove_role(self, role_id):
        """Remove role from user.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.manager.get_entity(ModelRole, role_id)
            #role = self.controller.get_entity(role_id, self.manager.get_roles)          
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-unset.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.manager.remove_user_role(self.model, role)
            self.logger.debug(u'Remove role %s from user %s' % (role, self.name))
            #self.send_event(u'role-unset.update', params=opts)           
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-unset.update', params=opts, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'perms.view')
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
        #opts = {u'name':self.name}
        
        # verify permissions
        self.controller.can(u'view', self.objtype, definition=self.objdef)
                
        try:  
            perms, total = self.manager.get_user_permissions(self.model, 
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
            #self.send_event(u'perms.view', params=opts)
            return user_perms, total
        except QueryError as ex:
            #self.send_event(u'perms.view', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0
        
    @trace(op=u'perms.use')
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
                
            #self.send_event(u'can', params=opts)   
        except Exception as ex:
            #self.send_event(u'can', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
class Group(AuthObject):
    objdef = u'Group'
    objdesc = u'System groups'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_group
        self.delete_object = self.manager.remove_group
        
        #if self.model is not None:
        #    self.uuid = self.model.uuid

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

    @trace(op=u'delete')
    def delete(self):
        """Delete entity.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #params = {u'id':self.oid}
        
        if self.delete_object is None:
            raise ApiManagerError(u'Delete is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))        
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'delete')
                
        try:
            # remove associated roles
            roles, total = self.manager.get_group_roles(group=self.model, size=1000)
            for role in roles:
                res = self.manager.remove_group_role(self.model, role)
            
            # delete user
            res = self.delete_object(oid=self.oid)
            # remove object and permissions
            self.deregister_object([self.objid])
            
            self.logger.debug(u'Delete %s: %s' % (self.objdef, self.oid))
            #self.send_event(u'delete', params=params)
            return res
        except TransactionError as ex:
            #self.send_event(u'delete', params=params, exception=ex)         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'roles-set.update')
    def append_role(self, role_id):
        """Append role to group.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.manager.get_entity(ModelRole, role_id)
            #role = self.controller.get_entity(role_id, self.manager.get_roles)
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.manager.append_group_role(self.model, role)
            if res is True: 
                self.logger.debug(u'Append role %s to group %s' % (
                                            role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with group %s' % (
                                            role, self.name))
            #self.send_event(u'role-set.update', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'roles-unset.update')
    def remove_role(self, role_id):
        """Remove role from group.
        
        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'role':role_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            role = self.manager.get_entity(ModelRole, role_id)
            #role = self.controller.get_entity(role_id, self.manager.get_roles) 
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-unset.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify role permissions
        self.controller.check_authorization(Role.objtype, Role.objdef, 
                                            role.objid, u'view')

        try:
            res = self.manager.remove_group_role(self.model, role)
            self.logger.debug(u'Remove role %s from group %s' % (role, self.name))
            #self.send_event(u'role-unset.update', params=opts)          
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'role-unset.update', params=opts, exception=ex)        
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'users-set.update')
    def append_user(self, user_id):
        """Append user to group.
        
        :param user_id: user name, id, or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'user':user_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user = self.manager.get_entity(ModelUser, user_id)
            #user = self.controller.get_entity(user_id, self.manager.get_users)
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'user-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, 
                                            user.objid, u'view')

        try:
            res = self.manager.append_group_user(self.model, user)
            if res is True: 
                self.logger.debug(u'Append user %s to group %s' % (
                                            user, self.name))
            else:
                self.logger.debug(u'User %s already linked with group %s' % (
                                            user, self.name))
            #self.send_event(u'user-set.update', params=opts)
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'user-set.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'users-unset.update')
    def remove_user(self, user_id):
        """Remove user from group.
        
        :param user_id: user id, name or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        #opts = {u'name':self.name, u'user':user_id}
        
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
                
        try:
            user = self.manager.get_entity(ModelUser, user_id)
            #user = self.controller.get_entity(user_id, self.manager.get_users)   
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'user-unset.update', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, 
                                            user.objid, u'view')

        try:
            res = self.manager.remove_group_user(self.model, user)
            self.logger.debug(u'Remove user %s from group %s' % (user, self.name))
            #self.send_event(u'user-unset.update', params=opts)       
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'user-unset.update', params=opts, exception=ex)    
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'perms.view')
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
            perms, total = self.manager.get_group_permissions(self.model, 
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
            self.send_event(u'perm.view', params=opts)
            return group_perms, total
        except QueryError as ex:
            self.send_event(u'perm.view', params=opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0
        
    @trace(op=u'perms.use')
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
                
            #self.send_event(u'can', params=opts)              
        except Exception as ex:
            #self.send_event(u'can', params=opts, exception=ex)  
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
           
     
        