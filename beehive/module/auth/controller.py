'''
Created on Jan 16, 2014

@author: darkbk
'''
from datetime import datetime
from beecell.auth import extract
#from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate, str2bool, format_date,\
    random_password
from beehive.common.apimanager import ApiManagerError, ApiObject
from beecell.db import TransactionError, QueryError
from beehive.common.controller.authorization import BaseAuthController, \
     User as BaseUser, Token, AuthObject
from beehive.common.data import trace, operation
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
        actions = [u'*', u'view', u'insert', u'update', u'delete', u'use',
                   u'disable', u'recover']
        for action in actions:        
            try:
                self.manager.add_object_action(action)
            except TransactionError as ex:
                self.logger.warn(ex)
                #raise ApiManagerError(ex, code=ex.code)
        
        BaseAuthController.init_object(self)
    
    def count(self):
        """Count users, groups, roles and objects
        """
        try:
            res = {
                u'users':self.manager.count_entities(ModelUser),
                u'groups':self.manager.count_entities(ModelGroup),
                u'roles':self.manager.count_entities(ModelRole),
                u'objects':self.manager.count_entities(ModelObject)
            }
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
        return self.get_entity(Role, ModelRole, oid)
    
    @trace(entity=u'Role', op=u'view')
    def get_roles(self, *args, **kvargs):
        """Get roles.

        :param name: role name [optional]
        :param alias: role alias [optional]
        :param user: user id [optional]
        :param group: group id [optional]
        :param perms_N: list of permissions like objtype,subsystem,objid,action [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]         
        :return: list or Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            perms = kvargs.get(u'perms_N', None)
            group = kvargs.get(u'group', None)
            user = kvargs.get(u'user', None)             
            
            # search roles by permissions
            if perms is not None:
                perms = [perm.split(u',') for perm in perms]
                roles, total = self.objects.get_permissions_roles(perms=perms, *args, **kvargs)

            # search roles by user
            elif user is not None:
                kvargs[u'user_id'] = self.get_entity(User, ModelUser, user).oid
                iroles, total = self.manager.get_user_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    role[0].expiry_date = role[1]
                    roles.append(role[0])

            # search roles by group
            elif group is not None:
                kvargs[u'group_id'] = self.get_entity(Group, ModelGroup, group).oid
                iroles, total = self.manager.get_group_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    role[0].expiry_date = role[1]
                    roles.append(role[0])                
            
            # get all roles
            else:
                roles, total = self.manager.get_roles(*args, **kvargs)
            
            return roles, total
        
        res, total = self.get_paginated_entities(Role, get_entities, *args, **kvargs)
        return res, total    
    
    def add_base_role(self, name, desc=u'', alias=u''):
        """Add new role.

        :param name: name of the role
        :param desc: role desc. [Optional]
        :param alias: role alias. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, u'insert')            

        try:
            objid = id_gen()
            role = self.manager.add_role(objid, name, desc, alias=alias)
            
            # add object and permission
            Role(self, oid=role.id).register_object([objid], desc=desc)

            self.logger.debug(u'Add new role: %s' % name)
            return role
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
    @trace(entity=u'Role', op=u'insert')
    def add_role(self, name=None, desc=u'', alias=u''):
        """Add role.

        :param name: name of the role
        :param desc: role desc. [Optional]
        :param alias: role alias. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role(name, desc, alias)
        return role.uuid
    
    @trace(entity=u'Role', op=u'admin.insert')
    def add_superadmin_role(self, perms):
        """Add beehive admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role(u'ApiSuperadmin', u'Beehive super admin role')
        
        # append permissions
        try:
            self.manager.append_role_permissions(role, perms)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
        return role
    
    @trace(entity=u'Role', op=u'guest.insert')
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role(u'Guest', u'Beehive guest role')        
        return role

    #
    # user manipulation methods
    #
    @trace(entity=u'User', op=u'view')
    def get_user(self, oid, action=u'view'):
        """Get single user.

        :param oid: entity model id or name or uuid         
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        entity_class = User
        entity_name = User.__name__

        try:
            entity = self.manager.get_entity(ModelUser, oid, for_update=False)
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(u'%s %s not found or name is not unique' % (entity_name, oid), code=404)

        if entity is None:
            self.logger.warn(u'%s %s not found' % (entity_name, oid))
            raise ApiManagerError(u'%s %s not found' % (entity_name, oid), code=404)

        # check authorization
        # - check identity has action over some groups that contain user
        groups, tot = self.manager.get_user_groups(user_id=oid, size=-1, with_perm_tag=False)
        groups_objids = [g.objid for g in groups]
        perms_objids = self.can(action, objtype=entity_class.objtype,
                                definition=Group.objdef).get(Group.objdef.lower(), [])
        if len(set(groups_objids) & set(perms_objids)) == 0:
            # - check identity has action over the user
            self.check_authorization(entity_class.objtype, entity_class.objdef, entity.objid, action)

        res = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                           desc=entity.desc, model=entity)

        # execute custom post_get
        res.post_get()

        self.logger.debug(u'Get %s : %s' % (entity_class.__name__, res))
        return res

    def _verify_operation_user_role(self, role=u'ApiSuperadmin'):
        """Check if operation user has a specific role.

        :return: Boolean
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """   
        
        user_name = operation.user[0]
        
        users, total = self.get_users(name=user_name, role=role)      
        if total > 0:
            return True

        return False

    @trace(entity=u'User', op=u'use')
    def get_user_secret(self, oid):
        """Get user secret.

        :param oid: entity model id or name or uuid
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        
        if self._verify_operation_user_role() is False:
            raise ApiManagerError(value=u'Invalid ApiSuperadmin role for operation user %s' % operation.user[0], code=400)
   
        user = self.get_user(oid, action=u'use')
        secret = user.model.secret
        self.logger.debug(u'Get user %s secret' % user.uuid)
        return secret

    @trace(entity=u'User', op=u'update')
    def reset_user_secret(self, oid, match_old_secret=False, old_secret=None):
        """reset user secret.

        :param oid: entity model id or name or uuid
        :param old_secret:  old secret key to reset
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """

        matched = True
        
        if self._verify_operation_user_role() is False:
            raise ApiManagerError(value=u'Invalid ApiSuperadmin role for operation user %s' % operation.user[0], code=400)
                
        user = self.get_user(oid, action=u'update')
        try:
            if match_old_secret:
                matched = self.manager.verify_user_secret(user.model, old_secret)
            if matched is False:
                raise ApiManagerError(value=u'Invalid old secret key for user id %s' % oid, code=400)
            else:
                res = self.manager.set_user_secret(user.model.id)  
            self.logger.debug(u'Reset user %s secret' % user.uuid)
            return user.model.secret
        except (TransactionError) as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(entity=u'User', op=u'view')
    def get_users(self, *args, **kvargs):
        """Get users or single user.

        :param name: user name [optional]
        :param names: user name list [optional]
        :param desc: user desc [optional]
        :param role: role name, id or uuid [optional]
        :param group: group name, id or uuid [optional]
        :param perms_N: list of permissions like objtype,subsystem,objid,action [optional]
        :param active: user status [optional]
        :param expiry_date: user expiry date. Use gg-mm-yyyy [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: List of :class:`User`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get(u'role', None)
            expiry_date = kvargs.get(u'expiry_date', None)
            group_id = kvargs.get(u'group_id', None)
            perms = kvargs.get(u'perms_N', None)

            # search users by permissions
            if perms is not None:
                perms = [perm.split(u',') for perm in perms]
                users, total = self.objects.get_permissions_users(perms=perms, *args, **kvargs)

            # search users by role
            elif role is not None:
                kvargs[u'role_id'] = self.get_entity(Role, ModelRole, role).oid
                users, total = self.manager.get_role_users(*args, **kvargs)

            # search users by group
            elif group_id is not None:
                users, total = self.manager.get_group_users(*args, **kvargs)
            
            # get all users
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split(u'-')
                    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                users, total = self.manager.get_users(*args, **kvargs)            
            
            return users, total

        # check group filter
        group = kvargs.get(u'group', None)

        # search users by group
        if group is not None:
            kvargs[u'group_id'] = self.get_entity(Group, ModelGroup, group).oid
            kvargs[u'authorize'] = False

        res, total = self.get_paginated_entities(User, get_entities, *args, **kvargs)
        return res, total

    @trace(entity=u'User', op=u'insert')
    def add_user(self, name=None, storetype=None, active=True, password=None, desc=u'', expiry_date=None, base=False,
                 system=False):
        """Add new user.

        :param name: name of the user
        :param storetype: type of the user store. Can be DBUSER, LDAPUSER
        :param active: User status. If True user is active [Optional] [Default=True]
        :param desc: User desc. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :param expiry_date: user expiry date. Set as gg-mm-yyyy [default=365 days]
        :param base: if True create a private role for the user [default=False]
        :param system: if True assign super admin role [default=False]        
        :return: user id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(User.objtype, User.objdef, None, u'insert')
        
        try:
            objid = id_gen()
            user = self.manager.add_user(objid, name, active=active, 
                                         password=password, 
                                         desc=desc, 
                                         expiry_date=expiry_date,
                                         is_generic=base,
                                         is_admin=system)
            # add object and permission
            obj = User(self, oid=user.id, objid=user.objid, name=user.name, 
                       desc=user.desc, model=user, active=user.active)
            
            obj.register_object([objid], desc=desc)
            
            # add default attributes
            if system is True:
                systype = u'SYS'
                storetype = u'DBUSER'
            else:
                systype = u'USER'
            self.manager.set_user_attribute(user, u'store_type', storetype, u'Type of user store')
            self.manager.set_user_attribute(user, u'sys_type', systype, u'Type of user')
            
            self.logger.debug(u'Add new user: %s' % name)
            return obj.uuid
        except (TransactionError) as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
    
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
        return self.get_entity(Group, ModelGroup, oid)    
    
    @trace(entity=u'Group', op=u'view')
    def get_groups(self, *args, **kvargs):
        """Get groups or single group.

        :param oid: group id [optional]
        :param name: group name [optional]
        :param role: role name, id or uuid [optional]
        :param user: user name, id or uuid [optional]
        :param perms_N: list of permissions like objtype,subsystem,objid,action [optional]
        :param expiry_date: group expiry date. Use gg-mm-yyyy [optional]
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]       
        :return: tupla (id, name, type, active, desc, attribute
                        creation_date, modification_date)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get(u'role', None)
            user = kvargs.get(u'user', None)
            perms = kvargs.get(u'perms_N', None)
            expiry_date = kvargs.get(u'expiry_date', None)

            # search groups by permissions
            if perms is not None:
                perms = [perm.split(u',') for perm in perms]
                groups, total = self.objects.get_permissions_groups(perms=perms, *args, **kvargs)

            # search groups by role
            elif role:
                kvargs[u'role_id'] = self.get_entity(Role, ModelRole, role).oid
                groups, total = self.manager.get_role_groups(*args, **kvargs)

            # search groups by user
            elif user is not None:
                kvargs[u'user_id'] = self.get_entity(User, ModelUser, user).oid
                groups, total = self.manager.get_user_groups(*args, **kvargs)
            
            # get all groups
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split(u'-')
                    kvargs[u'expiry_date'] = datetime(int(y), int(m), int(g))
                groups, total = self.manager.get_groups(*args, **kvargs)            
            
            return groups, total
        
        res, total = self.get_paginated_entities(Group, get_entities, *args, **kvargs)
        return res, total

    @trace(entity=u'Group', op=u'insert')
    def add_group(self, name=None, desc=u'', active=None, expiry_date=None):
        """Add new group.

        :param name: name of the group
        :param active: Group status. If True user is active [Optional] [Default=True]
        :param desc: Group desc. [Optional]
        :param expiry_date: Group expiry date. Set as gg-mm-yyyy [default=365 days]
        :return: group id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Group.objtype, Group.objdef, None, u'insert')
        
        try:
            objid = id_gen()
            group = self.manager.add_group(objid, name, desc=desc, 
                                           active=active, expiry_date=expiry_date)
            
            # add object and permission
            Group(self, oid=group.id).register_object([objid], desc=desc)          
            
            self.logger.debug(u'Add new group: %s' % name)
            return group.uuid
        except (TransactionError) as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)
        except (Exception) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)


class Objects(AuthObject):
    objdef = u'Objects'
    objdesc = u'Authorization objects'
    objuri = u'nas/objects'
    
    def __init__(self, controller):
        AuthObject.__init__(self, controller, oid=u'', name=u'', desc=u'', active=True)
        
        self.objid = u'*'
    
    #
    # System Object Type manipulation methods
    #    
    @trace(op=u'types.view')
    def get_type(self, oid=None, subsystem=None, type=None,
                 page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object type.
        
        :param oid: id of the system object type [optional]
        :param subsystem: type of the system object type [optional]
        :param type: definition of the system object type [optional]
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
        self.verify_permisssions(u'view')

        try:  
            data, total = self.manager.get_object_type(
                        oid=oid, objtype=subsystem, objdef=type, 
                        page=page, size=size, order=order, field=field)

            res = [{
                u'id':i.id, 
                u'subsystem':i.objtype, 
                u'type':i.objdef,
                u'date':{
                    u'creation':format_date(i.creation_date)
                }                
            }
            for i in data] #if i.objtype != u'event']

            return res, total
        except QueryError as ex:    
            self.logger.error(ex.desc, exc_info=1)
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
        self.verify_permisssions(u'insert')

        try:
            data = [(i[u'subsystem'], i[u'type']) for i in obj_types]
            res = self.manager.add_object_types(data)
            return [i.id for i in res]
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)
    
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
        # verify permissions
        self.verify_permisssions(u'delete')
                
        try:  
            res = self.manager.remove_object_type(oid=oid, objtype=objtype, 
                                                 objdef=objdef)     
            return None
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)

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
        # verify permissions
        self.verify_permisssions(u'view')
                
        try:  
            data = self.manager.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError(u'No data found')
            if type(data) is not list:
                data = [data]            
            res = [{u'id':i.id, u'value':i.value} for i in data]
            return res
        except QueryError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc)

    @trace(op=u'actions.insert')
    def add_actions(self, actions):
        """Add a system object action
        
        :param actions: list of string like 'use', u'view'
        :return: True if operation is successful   
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'insert')

        try:  
            res = self.manager.add_object_actions(actions)
            return True
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)
        
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
        self.verify_permisssions(u'delete')
                
        try:
            res = self.manager.remove_object_action(oid=oid, value=value)
            return None
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)

    #
    # System Object manipulation methods
    #
    @trace(op=u'perms.view')
    def get_object(self, oid):
        """Get system object filtered by id
        
        :param oid: object id
        :return: dict with object desc
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'view')
        
        try:
            data, total = self.manager.get_object(oid=oid)
            data = data[0]
            res = {
                u'id':data.id,
                u'uuid':data.uuid,
                u'subsystem':data.type.objtype,
                u'type':data.type.objdef,
                u'objid':data.objid,
                u'desc':data.desc,
                u'active':str2bool(data.active),
                u'date':{
                    u'creation':format_date(data.creation_date),
                    u'modified':format_date(data.modification_date),
                    u'expiry':u''
                }                
            }
            self.logger.debug(u'Get object: %s' % res)
            return res
        except QueryError as ex:         
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(u'Object %s not found' % (oid), code=404)    
    
    @trace(op=u'view')
    def get_objects(self, objid=None, subsystem=None, type=None, 
            page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object with some filter.

        :param objid: Total or partial objid [optional]
        :param subsystem: type of the system object [optional]
        :param type: definition of the system object [optional]
        :param page: object list page to show [default=0]
        :param size: number of object to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Tuple (id, type, value) 
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'view')
                
        try:
            data, total = self.manager.get_object(objid=objid, 
                    objtype=subsystem, objdef=type, page=page, size=size,
                    order=order, field=field)
                    
            res = [{
                u'id':i.id,
                u'uuid':i.uuid,
                u'subsystem':i.type.objtype,
                u'type':i.type.objdef,
                u'objid':i.objid,
                u'desc':i.desc,
                u'active':str2bool(i.active),
                u'date':{
                    u'creation':format_date(i.creation_date),
                    u'modified':format_date(i.modification_date),
                    u'expiry':u''
                }
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
    def add_objects(self, objs):
        """Add a list ofsystem objects with all the permission related to available 
        action.
        
        :param objs: list of dict like {
                'subsystem':..,
                'type':.., 
                'objid':.., 
                'desc':..        
            }
        :return: list of uuid
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'insert')
                
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
            return [i.id for i in res]
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=ex.code)  

    @trace(op=u'delete')
    def remove_object(self, oid=None, objid=None, objtype=None, objdef=None):
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
        self.verify_permisssions(u'delete')
                
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
            return None
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)          

    '''
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
        # verify permissions
        self.verify_permisssions(u'view')
                
        try:
            if permission_id is not None:
                res = self.manager.get_permission(permission_id)
            elif objid is not None or objtype is not None or objdef is not None:
                res = self.manager.get_permissions(
                    objid=objid, objtype=objtype, objdef=objdef, action=action)
            else:
                res = self.manager.get_permission()
            
            res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]            

            self.logger.debug(u'Get permissions: %s' % len(res))    
            return res
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            return []'''

    @trace(op=u'perms.view')
    def get_permission(self, oid=None, objid=None, objtype=None, objdef=None, action=None):
        """Get system object permisssion with roles.

        :param oid: permission id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: Object type [optional]
        :param objdef: Object definition [optional]
        :param action: Object action [optional]
        :return: dict with permission desc
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'view')
        
        try:
            if oid is not None:
                p = self.manager.get_permission(oid)
            elif objid is not None or objtype is not None or objdef is not None:
                pp, total = self.manager.get_permissions(objid=objid, objtype=objtype, objdef=objdef, action=action)
                p = pp[0]
            res = {
                u'id': p.id,
                u'oid': p.obj.id,
                u'subsystem': p.obj.type.objtype,
                u'type': p.obj.type.objdef,
                u'objid' :p.obj.objid,
                u'aid': p.action.id,
                u'action': p.action.value,
                u'desc': p.obj.desc,
            }
            return res
        except QueryError as ex:         
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(u'Permission %s not found' % (oid), code=404)

    @trace(op=u'perms.view')
    def get_permissions(self, objid=None, subsystem=None, type=None, cascade=False, page=0, size=10, order=u'DESC',
                        field=u'id', **kvargs):
        """Get system object permisssions with roles.
        
        :param objid: Total or partial objid [optional]
        :param cascade: If true filter by objid and childs until 
            objid+'//*//*//*//*//*//*'. Require objid and type [optional]
        :param subsystem str: Object type list comma separated [optional]
        :param type str: Object definition [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]        
        :return: list of dict with permission desc
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions(u'view')
        
        try:
            res = []
            
            subsystems = None
            if subsystem is not None:
                subsystems = subsystem.split(u',')
            
            if cascade is True:
                objids = [
                    objid, 
                    objid+u'//*',
                    objid+u'//*//*',
                    objid+u'//*//*//*',
                    objid+u'//*//*//*//*',
                    objid+u'//*//*//*//*//*',
                    objid+u'//*//*//*//*//*//*'
                ]
                perms, total = self.auth_db_manager.get_deep_permissions(
                        objids=objids, objtypes=subsystems,
                        page=page, size=size, order=order, field=field)
            
            else:
                perms, total = self.manager.get_permissions(
                    objid=objid, objid_filter=None, objtypes=subsystems, 
                    objdef=type, objdef_filter=None, action=None,
                    page=page, size=size, order=order, field=field)
                
            for p in perms:
                res.append({
                    u'id': p.id,
                    u'oid': p.obj.id,
                    u'subsystem': p.obj.type.objtype,
                    u'type': p.obj.type.objdef,
                    u'objid': p.obj.objid,
                    u'aid': p.action.id,
                    u'action': p.action.value,
                    u'desc': p.obj.desc
                })
                
            self.logger.debug(u'Get permissions: %s' % len(res))      
            return res, total
        except QueryError as ex:
            self.logger.error(ex.desc, exc_info=1)
            return [], 0

    @trace(op=u'perms.view')
    def get_permissions_roles(self, perms, *args, **kvargs):
        """List all roles associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        roles = []
        total = 0

        # verify permissions
        self.verify_permisssions(u'view')

        # get permissions id
        perm_ids = []
        for perm in perms:
            try:
                pp, total = self.manager.get_permissions(objid=perm[2], objtype=perm[0], objdef=perm[1], action=perm[3])
                perm_ids.append(str(pp[0].id))
            except:
                self.logger.warn(u'Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            roles, total = self.manager.get_permissions_roles(perms=perm_ids, *args, **kvargs)

        self.logger.debug(u'Permissions %s are used by roles: %s' % (perms, roles))
        return roles, total

    @trace(op=u'perms.view')
    def get_permissions_users(self, perms, *args, **kvargs):
        """List all users associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        users = []
        total = 0

        # verify permissions
        self.verify_permisssions(u'view')

        # get permissions id
        perm_ids = []
        for perm in perms:
            try:
                pp, total = self.manager.get_permissions(objid=perm[2], objtype=perm[0], objdef=perm[1], action=perm[3])
                perm_ids.append(str(pp[0].id))
            except:
                self.logger.warn(u'Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            users, total = self.manager.get_permissions_users(perms=perm_ids, *args, **kvargs)

        self.logger.debug(u'Permissions %s are used by users: %s' % (perms, users))
        return users, total

    @trace(op=u'perms.view')
    def get_permissions_groups(self, perms, *args, **kvargs):
        """List all groups associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        groups = []
        total = 0

        # verify permissions
        self.verify_permisssions(u'view')

        # get permissions id
        perm_ids = []
        for perm in perms:
            try:
                pp, total = self.manager.get_permissions(objid=perm[2], objtype=perm[0], objdef=perm[1], action=perm[3])
                perm_ids.append(str(pp[0].id))
            except:
                self.logger.warn(u'Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            groups, total = self.manager.get_permissions_groups(perms=perm_ids, *args, **kvargs)

        self.logger.debug(u'Permissions %s are used by groups: %s' % (perms, groups))
        return groups, total


class Role(AuthObject):
    objdef = u'Role'
    objdesc = u'System roles'
    objuri = u'nas/roles'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                            desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_role
        self.delete_object = self.manager.remove_role

        self.expiry_date = None

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AuthObject.info(self)
        info[u'alias'] = self.model.alias
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AuthObject.info(self)
        info[u'alias'] = self.model.alias
        return info

    @trace(op=u'perms.view')
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id',**kvargs):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: dictionary with permissions
        :rtype: dict
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, u'*', u'view')
        
        try:  
            perms, total = self.manager.get_role_permissions([self.name], page=page, size=size, order=order,
                                                             field=field)
            role_perms = []
            for i in perms:
                role_perms.append({
                    u'id': i.id,
                    u'oid': i.obj.id,
                    u'subsystem': i.obj.type.objtype,
                    u'type': i.obj.type.objdef,
                    u'objid': i.obj.objid,
                    u'aid': i.action.id,
                    u'action': i.action.value,
                    u'desc': i.obj.desc
                })                
            self.logger.debug(u'Get role %s permissions: %s' % (self.name, truncate(role_perms)))
            return role_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            return [], 0    

    @trace(op=u'perms.update')
    def append_permissions(self, perms):
        """Append permission to role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)
                                    
                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)
            
            res = self.manager.append_role_permissions(self.model, roleperms)
            self.logger.debug(u'Append role %s permission : %s' % (self.name, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @trace(op=u'perms.update')
    def remove_permissions(self, perms):
        """Remove permission from role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)
                                    
                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)  
            
            res = self.manager.remove_role_permission(self.model, roleperms)
            self.logger.debug(u'Remove role %s permission : %s' % (self.name, perms))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)


class User(BaseUser):
    objdef = u'User'
    objdesc = u'System users'
    objuri = u'nas/users'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, model=None, active=True):
        BaseUser.__init__(self, controller, oid=oid, objid=objid, name=name, desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_user
        self.delete_object = self.manager.remove_user

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = BaseUser.info(self)
        # info[u'secret'] = self.model.secret
        if self.model.last_login is not None:
            info[u'date'][u'last_login'] = format_date(self.model.last_login)

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = BaseUser.detail(self)
        # info[u'secret'] = self.model.secret
        if self.model.last_login is not None:
            info[u'date'][u'last_login'] = format_date(self.model.last_login)

        return info

    @trace(op=u'attribs-get.update')
    def get_attribs(self):
        # verify permissions
        self.verify_permisssions(u'use')

        attrib = [{u'name': a.name, u'value': a.value, u'desc': a.desc} for a in self.model.attrib]
        self.logger.debug(u'User %s attributes: %s' % (self.name, attrib))
        return attrib
    
    @trace(op=u'attribs-set.update')
    def set_attribute(self, name=None, value=None, desc='', new_name=None):
        """Set an attribute
        
        :param user: User instance
        :param name: attribute name
        :param new_name: new attribute name [optional]
        :param value: attribute value
        :param desc: attribute desc
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`        
        """
        # verify permissions
        self.verify_permisssions(u'update')

        try:
            res = self.manager.set_user_attribute(self.model, name, value=value, 
                                                 desc=desc, new_name=new_name)
            self.logger.debug(u'Set user %s attribute %s: %s' % 
                              (self.name, name, value))
            return res
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')

        try:
            res = self.manager.remove_user_attribute(self.model, name)
            self.logger.debug(u'Remove user %s attribute %s' % (self.name, name))
            return None
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')
        
        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                y, m, d = expiry_date.split(u'-')
                expiry_date_obj = datetime(int(y), int(m), int(d))
            res = self.manager.append_user_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True: 
                self.logger.debug(u'Append role %s to user %s' % (role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with user %s' % (role, self.name))
            return role_id
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')
        
        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            res = self.manager.remove_user_role(self.model, role.model)
            self.logger.debug(u'Remove role %s from user %s' % (role, self.name))          
            return role_id
        except (QueryError, TransactionError) as ex:         
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'perms.view')
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id', **kvargs):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, u'*', u'view')
        
        try:  
            perms, total = self.manager.get_user_permissions(self.model, page=page, size=size, order=order, field=field)
            user_perms = []
            for i in perms:
                user_perms.append({
                    u'id': i.id,
                    u'oid': i.obj.id,
                    u'subsystem': i.obj.type.objtype,
                    u'type': i.obj.type.objdef,
                    u'objid': i.obj.objid,
                    u'aid': i.action.id,
                    u'action': i.action.value,
                    u'desc': i.obj.desc
                })                
            self.logger.debug(u'Get user %s permissions: %s' % (self.name, truncate(user_perms)))
            return user_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0

    @trace(op=u'perms.update')
    def append_permissions(self, perms):
        """Append permission to user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')

        # get internal user role
        role = self.manager.get_entity(ModelRole, u'User%sRole' % self.oid, for_update=False)

        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)

            res = self.manager.append_role_permissions(role, roleperms)
            self.logger.debug(u'Append user %s permission : %s' % (self.uuid, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @trace(op=u'perms.update')
    def remove_permissions(self, perms):
        """Remove permission from user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')

        # get internal user role
        role = self.manager.get_entity(ModelRole, u'User%sRole' % self.oid, for_update=False)

        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)

            res = self.manager.remove_role_permission(role, roleperms)
            self.logger.debug(u'Remove user %s permission : %s' % (self.uuid, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
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
        # verify permissions
        self.verify_permisssions(u'use')        
                
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
                    if perm_objtype == objtype and perm_definition == definition and perm_action in [u'*', action]:
                        objids.append(perm_objid)
                else:
                    if perm_objtype == objtype and perm_action in [u'*', action]:
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
                self.logger.debug(u'User %s can %s objects {%s, %s}' % (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception(u'User %s can not \'%s\' objects \'%s:%s\'' % 
                                (self.name, action, objtype, definition))

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)


class Group(AuthObject):
    objdef = u'Group'
    objdesc = u'System groups'
    objuri = u'nas/groups'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, desc=desc, active=active, model=model)
        
        self.update_object = self.manager.update_group
        self.patch_object = self.manager.patch_group
        self.delete_object = self.manager.remove_group

    @trace(op=u'roles-set.update')
    def append_role(self, role_id, expiry_date=None):
        """Append role to group.
        
        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')
                
        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                y, m, d = expiry_date.split(u'-')
                expiry_date_obj = datetime(int(y), int(m), int(d))          
            res = self.manager.append_group_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True: 
                self.logger.debug(u'Append role %s to group %s' % (role, self.name))
            else:
                self.logger.debug(u'Role %s already linked with group %s' % (role, self.name))
            return role_id
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')
                
        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            res = self.manager.remove_group_role(self.model, role.model)
            self.logger.debug(u'Remove role %s from group %s' % (role, self.name))   
            return role_id
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')
                
        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, user.objid, u'view')

        try:
            res = self.manager.append_group_user(self.model, user.model)
            if res is True: 
                self.logger.debug(u'Append user %s to group %s' % (user, self.name))
            else:
                self.logger.debug(u'User %s already linked with group %s' % (user, self.name))
            return user_id
        except (QueryError, TransactionError) as ex:
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
        # verify permissions
        self.verify_permisssions(u'update')
                
        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        try:
            res = self.manager.remove_group_user(self.model, user.model)
            self.logger.debug(u'Remove user %s from group %s' % (user, self.name))
            return user_id
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'perms.view')
    def get_permissions(self, page=0, size=10, order=u'DESC', field=u'id', **kvargs):
        """Get groups permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, u'*', u'view')
                
        try:  
            perms, total = self.manager.get_group_permissions(self.model, page=page, size=size, order=order,
                                                              field=field)
            group_perms = []
            for i in perms:
                group_perms.append({
                    u'id': i.id,
                    u'oid': i.obj.id,
                    u'subsystem': i.obj.type.objtype,
                    u'type': i.obj.type.objdef,
                    u'objid': i.obj.objid,
                    u'aid': i.action.id,
                    u'action': i.action.value,
                    u'desc': i.obj.desc
                })                
            self.logger.debug(u'Get group %s permissions: %s' % (self.name, truncate(group_perms)))
            return group_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        return [], 0

    @trace(op=u'perms.update')
    def append_permissions(self, perms):
        """Append permission to group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')

        # get internal group role
        role = self.manager.get_entity(ModelRole, u'Group%sRole' % self.oid, for_update=False)

        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)

            res = self.manager.append_role_permissions(role, roleperms)
            self.logger.debug(u'Append group %s permission : %s' % (self.uuid, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @trace(op=u'perms.update')
    def remove_permissions(self, perms):
        """Remove permission from group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions(u'update')

        # get internal group role
        role = self.manager.get_entity(ModelRole, u'Group%sRole' % self.oid, for_update=False)

        try:
            # get permissions
            roleperms = []
            for perm in perms:
                # perm as permission_id
                if u'id' in perm:
                    perm = self.manager.get_permission(perm[u'id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    perms, total = self.manager.get_permissions(objid=perm[u'objid'], objtype=perm[u'subsystem'],
                                                                objdef=perm[u'type'], action=perm[u'action'], size=10)
                    roleperms.extend(perms)

            res = self.manager.remove_role_permission(role, roleperms)
            self.logger.debug(u'Remove group %s permission : %s' % (self.uuid, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

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
        # verify permissions
        self.verify_permisssions(u'use')
                
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
                    if (perm_objtype == objtype and perm_definition == definition and perm_action in [u'*', action]):
                        objids.append(perm_objid)
                else:
                    if (perm_objtype == objtype and perm_action in [u'*', action]):
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

        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
