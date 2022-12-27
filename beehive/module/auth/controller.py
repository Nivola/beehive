# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from datetime import datetime
from re import match
from six import ensure_text

from beecell.auth import extract
from beecell.simple import id_gen, truncate, str2bool, format_date
from beehive.common.apimanager import ApiManagerError
from beecell.db import TransactionError, QueryError
from beehive.common.controller.authorization import BaseAuthController, \
     User as BaseUser, Token, AuthObject
from beehive.common.data import trace, operation
from beehive.common.model.authorization import AuthDbManager, User as ModelUser, \
    Role as ModelRole, Group as ModelGroup, SysObject as ModelObject
from typing import List, Tuple, TYPE_CHECKING



class AuthController(BaseAuthController):
    """Auth Module controller.

    :param module: Beehive module
    """
    version = 'v1.0'

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
        actions = ['*', 'view', 'insert', 'update', 'delete', 'use', 'disable', 'recover']
        for action in actions:
            try:
                self.manager.add_object_action(action)
            except TransactionError as ex:
                self.logger.warning(ex)

        BaseAuthController.init_object(self)

    def count(self):
        """Count users, groups, roles and objects
        """
        try:
            res = {
                'users': self.manager.count_entities(ModelUser),
                'groups': self.manager.count_entities(ModelGroup),
                'roles': self.manager.count_entities(ModelRole),
                'objects': self.manager.count_entities(ModelObject)
            }
            return res
        except QueryError as ex:
            raise ApiManagerError(ex, code=ex.code)

    #
    # role manipulation methods
    #
    @trace(entity='Role', op='view')
    def get_role(self, oid):
        """Get single role.

        :param oid: entity model id or name or uuid
        :return: Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Role, ModelRole, oid)

    @trace(entity='Role', op='view')
    def get_roles(self, *args, **kvargs)-> Tuple[List, int]:
        """Get roles.

        :param name: role name [optional]
        :param alias: role alias [optional]
        :param user: user id [optional]
        :param group: group id [optional]
        :param groups_N: list of groups [optional]
        :param perms_N: list of permissions like objtype,subsystem,objid,action [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]oles(**
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list or Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            perms = kvargs.get('perms_N', None)
            groups = kvargs.get('groups_N', None)
            group = kvargs.get('group', None)
            user = kvargs.get('user', None)

            # search roles by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                roles, total = self.objects.get_permissions_roles(perms=perms, *args, **kvargs)

            # search roles by user
            elif user is not None:
                kvargs['user_id'] = self.get_entity(User, ModelUser, user).oid
                iroles, total = self.manager.get_user_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    role[0].expiry_date = role[1]
                    roles.append(role[0])

            # search roles by group
            elif group is not None:
                kvargs['group_id'] = self.get_entity(Group, ModelGroup, group).oid
                iroles, total = self.manager.get_group_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    role[0].expiry_date = role[1]
                    roles.append(role[0])

            # search roles by groups_N
            elif groups is not None:
                kvargs['group_id_list'] = [str(self.get_entity(Group, ModelGroup, group).oid) for group in groups ]
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

    def add_base_role(self, name, desc='', alias=''):
        """Add new role.

        :param name: name of the role
        :param desc: role desc. [Optional]
        :param alias: role alias. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, 'insert')

        try:
            objid = id_gen()
            role = self.manager.add_role(objid, name, desc, alias=alias)

            # add object and permission
            Role(self, oid=role.id).register_object([objid], desc=desc)

            self.logger.debug('Add new role: %s' % name)
            return role
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity='Role', op='insert')
    def add_role(self, name=None, desc='', alias=''):
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

    @trace(entity='Role', op='admin.insert')
    def add_superadmin_role(self, perms):
        """Add beehive admin role with all the required permissions.

        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role('ApiSuperadmin', 'Beehive super admin role')

        # append permissions
        try:
            self.manager.append_role_permissions(role, perms)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        return role

    @trace(entity='Role', op='guest.insert')
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.

        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role('Guest', 'Beehive guest role')
        return role

    #
    # user manipulation methods
    #
    @trace(entity='User', op='view')
    def exist_user(self, oid):
        """Check user exists.

        :param oid: entity model id or name or uuid
        :return: True if exists
        """
        return self.manager.exist_entity(ModelUser, oid)

    @trace(entity='User', op='view')
    def get_user(self, oid, action='view'):
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
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError('%s %s not found or name is not unique' % (entity_name, oid), code=404)

        if entity is None:
            self.logger.warning('%s %s not found' % (entity_name, oid))
            raise ApiManagerError('%s %s not found' % (entity_name, oid), code=404)

        # check authorization
        # - check identity has action over some groups that contain user
        groups, tot = self.manager.get_user_groups(user_id=entity.id, size=-1, with_perm_tag=False)
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

        self.logger.debug('Get %s : %s' % (entity_class.__name__, res))
        return res

    def _verify_operation_user_role(self, role='ApiSuperadmin'):
        """Check if operation user has a specific role.

        :param role: role to check [default=ApiSuperadmin]
        :return: Boolean
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # disable authorization
        operation.authorize = False

        user_email = operation.user[0]
        users, tot = self.manager.get_users(email=user_email, with_perm_tag=False)
        user_name = users[0].name

        # check if role is assigned to the user
        users, total_users = self.get_users(email=user_email, role=role, with_perm_tag=False)

        # check if role is assigned to a group of which a user is a member
        groups, total = self.get_groups(user=user_name)
        total_groups = 0
        for group in groups:
            groups, total = self.get_groups(name=group.name, role=role, with_perm_tag=False)
            total_groups += total

        # disable authorization
        operation.authorize = True

        if total_users > 0 or total_groups > 0:
            self.logger.debug('User %s has role %s' % (user_name, role))
            return True

        self.logger.warning('User %s has not role %s' % (user_name, role))
        return False

    @trace(entity='User', op='use')
    def get_user_secret(self, oid):
        """Get user secret.

        :param oid: entity model id or name or uuid
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # disable authorization check
        # operation.authorize = False

        role1 = 'ApiSuperadmin'
        role2 = 'CsiOperator'
        if self._verify_operation_user_role(role1) is True or self._verify_operation_user_role(role2) is True:
            user = self.get_user(oid, action='use')
            secret = user.model.secret
            self.logger.debug('Get user %s secret' % user.uuid)
            return secret
        else:
            raise ApiManagerError(value='This operation require one of this roles: %s, %s' % (role1, role2), code=400)

        # enable authorization check
        # operation.authorize = True

    @trace(entity='User', op='update')
    def reset_user_secret(self, oid, match_old_secret=False, old_secret=None):
        """reset user secret.

        :param oid: entity model id or name or uuid
        :param match_old_secret: if True match old secret [default=False]
        :param old_secret: old secret key to reset [optional]
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        matched = True

        if self._verify_operation_user_role() is False:
            raise ApiManagerError(value='Invalid ApiSuperadmin role for operation user %s' % operation.user[0],
                                  code=400)

        user = self.get_user(oid, action='update')
        try:
            if match_old_secret:
                matched = self.manager.verify_user_secret(user.model, old_secret)
            if matched is False:
                raise ApiManagerError(value='Invalid old secret key for user id %s' % oid, code=400)
            else:
                res = self.manager.set_user_secret(user.model.id)
            self.logger.debug('Reset user %s secret' % user.uuid)
            return user.model.secret
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity='User', op='view')
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
        :param email: email [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of :class:`User`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get('role', None)
            expiry_date = kvargs.get('expiry_date', None)
            group_id = kvargs.get('group_id', None)
            perms = kvargs.get('perms_N', None)

            # search users by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                users, total = self.objects.get_permissions_users(perms=perms, *args, **kvargs)

            # search users by role
            elif role is not None:
                kvargs['role_id'] = self.get_entity(Role, ModelRole, role).oid
                users, total = self.manager.get_role_users(*args, **kvargs)

            # search users by group
            elif group_id is not None:
                users, total = self.manager.get_group_users(*args, **kvargs)

            # get all users
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split('-')
                    kvargs['expiry_date'] = datetime(int(y), int(m), int(g))
                users, total = self.manager.get_users(*args, **kvargs)

            return users, total

        # check group filter
        group = kvargs.get('group', None)

        # search users by group
        if group is not None:
            kvargs['group_id'] = self.get_entity(Group, ModelGroup, group).oid
            operation.authorize = False

        res, total = self.get_paginated_entities(User, get_entities, *args, **kvargs)
        return res, total

    @trace(entity='User', op='insert')
    def add_user(self, name=None, storetype=None, active=True, password=None, desc='', expiry_date=None, base=False,
                 system=False, email=None):
        """Add new user.

        :param name: name of the user
        :param storetype: type of the user store. Can be DBUSER, LDAPUSER
        :param active: User status. If True user is active [Optional] [Default=True]
        :param desc: User desc. [Optional]
        :param password: Password of the user. Set only for user like <user>@local [Optional]
        :param expiry_date: user expiry date. Set as gg-mm-yyyy [default=365 days]
        :param base: if True create a private role for the user [default=False]
        :param system: if True assign super admin role [default=False]
        :param email: email [optional]
        :return: user id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(User.objtype, User.objdef, None, 'insert')

        try:
            objid = id_gen()
            user = self.manager.add_user(objid, name, active=active, password=password, desc=desc,
                                         expiry_date=expiry_date, is_generic=base, is_admin=system, email=email)
            # add object and permission
            obj = User(self, oid=user.id, objid=user.objid, name=user.name, desc=user.desc, model=user,
                       active=user.active)

            obj.register_object([objid], desc=desc)

            # add default attributes
            if system is True:
                systype = 'SYS'
                storetype = 'DBUSER'
            else:
                systype = 'USER'
            self.manager.set_user_attribute(user, 'store_type', storetype, 'Type of user store')
            self.manager.set_user_attribute(user, 'sys_type', systype, 'Type of user')

            self.logger.debug('Add new user: %s' % name)
            return obj.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity='Token', op='delete')
    def remove_identities_for_user(self, user_id):
        """Remove active beehive identities for a certain user

        :param user_id: user name or email
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, '*', 'delete')

        user_obj = self.get_entity(User, ModelUser, user_id)
        # self.logger.warn(user_obj)
        user = user_obj.name
        # if user_obj.model.email is not None:
        #     user = user_obj.model.email

        # get identities from identity user index
        uids = self.module.redis_identity_manager.lrange(self.prefix_index + user, 0, -1)
        for uid in uids:
            try:
                uid = ensure_text(uid)
                self.module.redis_identity_manager.delete(self.prefix + uid)

                # delete identity from identity user index
                self.module.redis_identity_manager.lrem(self.prefix_index + user, 1, uid)

                self.logger.debug('Remove identity %s from redis' % uid)
            except:
                self.logger.warning('Can not remove identity %s' % uid)
        return True

    #
    # group manipulation methods
    #
    @trace(entity='Group', op='view')
    def get_group(self, oid):
        """Get single group.

        :param oid: entity model id or name or uuid
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Group, ModelGroup, oid)

    @trace(entity='Group', op='view')
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
        :return: tupla (id, name, type, active, desc, attribute creation_date, modification_date)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        def get_entities(*args, **kvargs):
            # get filter field
            role = kvargs.get('role', None)
            user = kvargs.get('user', None)
            perms = kvargs.get('perms_N', None)
            expiry_date = kvargs.get('expiry_date', None)

            # search groups by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                groups, total = self.objects.get_permissions_groups(perms=perms, *args, **kvargs)

            # search groups by role
            elif role:
                kvargs['role_id'] = self.get_entity(Role, ModelRole, role).oid
                groups, total = self.manager.get_role_groups(*args, **kvargs)

            # search groups by user
            elif user is not None:
                kvargs['user_id'] = self.get_entity(User, ModelUser, user).oid
                groups, total = self.manager.get_user_groups(*args, **kvargs)

            # get all groups
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split('-')
                    kvargs['expiry_date'] = datetime(int(y), int(m), int(g))
                groups, total = self.manager.get_groups(*args, **kvargs)

            return groups, total

        res, total = self.get_paginated_entities(Group, get_entities, *args, **kvargs)
        return res, total

    @trace(entity='Group', op='insert')
    def add_group(self, name=None, desc='', active=None, expiry_date=None):
        """Add new group.

        :param name: name of the group
        :param active: Group status. If True user is active [Optional] [Default=True]
        :param desc: Group desc. [Optional]
        :param expiry_date: Group expiry date. Set as gg-mm-yyyy [default=365 days]
        :return: group id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Group.objtype, Group.objdef, None, 'insert')

        try:
            objid = id_gen()
            group = self.manager.add_group(objid, name, desc=desc, active=active, expiry_date=expiry_date)

            # add object and permission
            Group(self, oid=group.id).register_object([objid], desc=desc)

            self.logger.debug('Add new group: %s' % name)
            return group.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity='Token', op='delete')
    def remove_identities_for_group(self, group_id):
        """Remove active beehive identities for all the users in a group

        :param group_id: group id
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, '*', 'delete')

        users, tot = self.get_users(group=group_id)
        for user in users:
            # get identities from identity user index
            uids = self.module.redis_identity_manager.lrange(self.prefix_index + user.name, 0, -1)

            for uid in uids:
                try:
                    uid = ensure_text(uid)
                    self.module.redis_identity_manager.delete(self.prefix + uid)

                    # delete identity from identity user index
                    self.module.redis_identity_manager.lrem(self.prefix_index + user.name, 1, uid)

                    self.logger.debug('Remove identity %s from redis' % uid)
                except:
                    self.logger.warning('Can not remove identity %s' % uid)
        return True


class Objects(AuthObject):
    objdef = 'Objects'
    objdesc = 'Authorization objects'
    objuri = 'nas/objects'

    def __init__(self, controller):
        AuthObject.__init__(self, controller, oid='', name='', desc='', active=True)

        self.objid = '*'

    #
    # System Object Type manipulation methods
    #
    @trace(op='view')
    def get_type(self, oid=None, subsystem=None, type=None, page=0, size=10, order='DESC', field='id'):
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        :raises ApiAuthorizationError if query empty return error.
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            data, total = self.manager.get_object_type(oid=oid, objtype=subsystem, objdef=type, page=page, size=size,
                                                       order=order, field=field)

            res = [{
                'id': i.id,
                'subsystem': i.objtype,
                'type': i.objdef,
                'date': {
                    'creation': format_date(i.creation_date)
                }
            }
            for i in data]

            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0

    @trace(op='insert')
    def add_types(self, obj_types):
        """Add a system object types

        :param obj_types: list of dict {'subsystem':.., 'type':..}
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('insert')

        try:
            data = [(i['subsystem'], i['type']) for i in obj_types]
            res = self.manager.add_object_types(data)
            return [i.id for i in res]
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='delete')
    def remove_type(self, oid=None, objtype=None, objdef=None):
        """Remove system object type.

        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('delete')

        try:
            res = self.manager.remove_object_type(oid=oid, objtype=objtype, objdef=objdef)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object Action manipulation methods
    #
    @trace(op='view')
    def get_action(self, oid=None, value=None):
        """Get system object action.

        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: List of Tuple (id, value)
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            data = self.manager.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError('No data found')
            if type(data) is not list:
                data = [data]
            res = [{'id': i.id, 'value': i.value} for i in data]
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError(ex.value)

    @trace(op='insert')
    def add_actions(self, actions):
        """Add a system object action

        :param actions: list of string like 'use', 'view'
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('insert')

        try:
            res = self.manager.add_object_actions(actions)
            return True
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='delete')
    def remove_action(self, oid=None, value=None):
        """Add a system object action

        :param oid: System object action id [optional]
        :param value: string like 'use', 'view' [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('delete')

        try:
            res = self.manager.remove_object_action(oid=oid, value=value)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object manipulation methods
    #
    @trace(op='view')
    def get_object(self, oid):
        """Get system object filtered by id

        :param oid: object id
        :return: dict with object desc
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            data, total = self.manager.get_object(oid=oid)
            data = data[0]
            res = {
                'id': data.id,
                'uuid': data.uuid,
                'subsystem': data.type.objtype,
                'type': data.type.objdef,
                'objid': data.objid,
                'desc': data.desc,
                'active': str2bool(data.active),
                'date': {
                    'creation': format_date(data.creation_date),
                    'modified': format_date(data.modification_date),
                    'expiry': ''
                }
            }
            self.logger.debug('Get object: %s' % res)
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError('Object %s not found' % (oid), code=404)

    @trace(op='view')
    def get_objects(self, objid=None, subsystem=None, type=None, page=0, size=10, order='DESC', field='id'):
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            data, total = self.manager.get_object(objid=objid, objtype=subsystem, objdef=type, page=page, size=size,
                                                  order=order, field=field)

            res = [{
                'id': i.id,
                'uuid': i.uuid,
                'subsystem': i.type.objtype,
                'type': i.type.objdef,
                'objid': i.objid,
                'desc': i.desc,
                'active': str2bool(i.active),
                'date': {
                    'creation': format_date(i.creation_date),
                    'modified': format_date(i.modification_date),
                    'expiry': ''
                }
            } for i in data]
            self.logger.debug('Get objects: %s' % len(res))
            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            return [], 0

    @trace(op='insert')
    def add_objects(self, objs):
        """Add a list ofsystem objects with all the permission related to available action.

        :param objs: list of dict like {'subsystem':.., 'type':.., 'objid':.., 'desc':..}
        :return: list of uuid
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('insert')

        try:
            # get actions
            actions = self.manager.get_object_action()

            # create objects
            data = []
            for obj in objs:
                obj_type, total = self.manager.get_object_type(objtype=obj['subsystem'], objdef=obj['type'])
                data.append((obj_type[0], obj['objid'], obj['desc']))

            res = self.manager.add_object(data, actions)
            self.logger.debug('Add objects: %s' % objs)
            return [i.id for i in res]
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='delete')
    def remove_object(self, oid=None, objid=None, objtype=None, objdef=None):
        """Delete system object filtering by id, by name or by type. System remove also all the related permission.

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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('delete')

        try:
            if objtype is not None or objdef is not None:
                # get object types
                obj_types, tot = self.manager.get_object_type(objtype=objtype, objdef=objdef)
                for obj_type in obj_types:
                    res = self.manager.remove_object(oid=oid, objid=objid, objtype=obj_type)
            else:
                res = self.manager.remove_object(oid=oid, objid=objid)
            self.logger.debug('Remove objects: %s' % res)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='view')
    def get_permission(self, oid=None, objid=None, objtype=None, objdef=None, action=None):
        """Get system object permisssion with roles.

        :param oid: permission id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: Object type [optional]
        :param objdef: Object definition [optional]
        :param action: Object action [optional]
        :return: dict with permission desc
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            if oid is not None:
                p = self.manager.get_permission(oid)
            elif objid is not None or objtype is not None or objdef is not None:
                pp, total = self.manager.get_permissions(objid=objid, objtype=objtype, objdef=objdef, action=action)
                p = pp[0]
            res = {
                'id': p.id,
                'oid': p.obj.id,
                'subsystem': p.obj.type.objtype,
                'type': p.obj.type.objdef,
                'objid': p.obj.objid,
                'aid': p.action.id,
                'action': p.action.value,
                'desc': p.obj.desc,
            }
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError('Permission %s not found' % (oid), code=404)

    @trace(op='view')
    def get_permissions(self, oid=None, objid=None, subsystem=None, type=None, cascade=False, page=0, size=10,
                        order='DESC', field='id', **kvargs):
        """Get system object permisssions with roles.

        :param oid: object id [optional]
        :param objid: Total or partial objid [optional]
        :param cascade: If true filter by objid and childs until objid+'//*//*//*//*//*//*'.
            Require objid and type [optional]
        :param subsystem str: Object type list comma separated [optional]
        :param type str: Object definition [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: list of dict with permission desc
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('view')

        try:
            res = []

            subsystems = None
            if subsystem is not None:
                subsystems = subsystem.split(',')

            if cascade is True:
                objids = [
                    objid,
                    objid+'//*',
                    objid+'//*//*',
                    objid+'//*//*//*',
                    objid+'//*//*//*//*',
                    objid+'//*//*//*//*//*',
                    objid+'//*//*//*//*//*//*'
                ]
                perms, total = self.auth_db_manager.get_deep_permissions(
                        objids=objids, objtypes=subsystems, page=page, size=size, order=order, field=field)

            else:
                perms, total = self.manager.get_permissions(oid=oid, objid=objid, objid_filter=None,
                                                            objtypes=subsystems, objdef=type, objdef_filter=None,
                                                            action=None, page=page, size=size, order=order, field=field)

            for p in perms:
                res.append({
                    'id': p.id,
                    'oid': p.obj.id,
                    'subsystem': p.obj.type.objtype,
                    'type': p.obj.type.objdef,
                    'objid': p.obj.objid,
                    'aid': p.action.id,
                    'action': p.action.value,
                    'desc': p.obj.desc
                })

            self.logger.debug('Get permissions: %s' % len(res))
            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0

    @trace(op='view')
    def get_permissions_roles(self, perms, *args, **kvargs):
        """List all roles associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        roles = []
        total = 0

        # verify permissions
        self.verify_permisssions('view')

        # get permissions id
        perm_ids = []
        actions = {a.value: a.id for a in self.manager.get_object_action()}
        for perm in perms:
            if match('^\d+$', perm):
                perm = int(perm)

            if isinstance(perm, list):
                objtype, objdef, objid, objaction = perm
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(',')
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            else:
                try:
                    pp = self.manager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            roles, total = self.manager.get_permissions_roles(perms=perm_ids, *args, **kvargs)

        self.logger.debug('Permissions %s are used by roles: %s' % (perms, truncate(roles)))
        return roles, total

    @trace(op='view')
    def get_permissions_users(self, perms, *args, **kvargs):
        """List all users associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        users = []
        total = 0

        # verify permissions
        self.verify_permisssions('view')

        # get permissions id
        perm_ids = []
        actions = {a.value: a.id for a in self.manager.get_object_action()}
        for perm in perms:
            if match('^\d+$', perm):
                perm = int(perm)

            if isinstance(perm, list):
                objtype, objdef, objid, objaction = perm
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(',')
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            else:
                try:
                    pp = self.manager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            users, total = self.manager.get_permissions_users(perms=perm_ids, *args, **kvargs)

        self.logger.debug('Permissions %s are used by users: %s' % (perms, truncate(users)))
        return users, total

    @trace(op='view')
    def get_permissions_groups(self, perms, *args, **kvargs):
        """List all groups associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        groups = []
        total = 0

        # verify permissions
        self.verify_permisssions('view')

        # get permissions id
        perm_ids = []
        actions = {a.value: a.id for a in self.manager.get_object_action()}
        for perm in perms:
            if match('^\d+$', perm):
                perm = int(perm)

            if isinstance(perm, list):
                objtype, objdef, objid, objaction = perm
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(',')
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)
            else:
                try:
                    pp = self.manager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning('Permission %s was not found' % perm)

        if len(perm_ids) > 0:
            groups, total = self.manager.get_permissions_groups(perms=perm_ids, *args, **kvargs)

        self.logger.debug('Permissions %s are used by groups: %s' % (perms, truncate(groups)))
        return groups, total


class Role(AuthObject):
    objdef = 'Role'
    objdesc = 'System roles'
    objuri = 'nas/roles'

    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, model=None, active=True):
        self.manager: AuthDbManager
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, desc=desc, active=active, model=model)

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
        info['alias'] = self.model.alias
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AuthObject.info(self)
        info['alias'] = self.model.alias
        return info

    @trace(op='view')
    def get_permissions(self, page=0, size=10, order='DESC', field='id', **kvargs):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: dictionary with permissions
        :rtype: dict
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, '*', 'view')

        try:
            perms, total = self.manager.get_role_permissions([self.name], page=page, size=size, order=order,
                                                             field=field)
            role_perms = []
            for i in perms:
                role_perms.append({
                    'id': i.id,
                    'oid': i.obj.id,
                    'subsystem': i.obj.type.objtype,
                    'type': i.obj.type.objdef,
                    'objid': i.obj.objid,
                    'aid': i.action.id,
                    'action': i.action.value,
                    'desc': i.obj.desc
                })
            self.logger.debug('Get role %s permissions: %s' % (self.name, truncate(role_perms)))
            return role_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            return [], 0

    @trace(op='update')
    def append_permissions(self, perms):
        """Append permission to role

        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        try:
            # get permissions
            roleperms = []
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)

                    # perms, total = self.manager.get_permissions(objid=perm['objid'], objtype=perm['subsystem'],
                    #                                             objdef=perm['type'], action=perm['action'], size=10)
                    # roleperms.extend(perms)

            res = self.manager.append_role_permissions(self.model, roleperms)
            self.logger.debug('Append role %s permission : %s' % (self.name, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op='update')
    def remove_permissions(self, perms):
        """Remove permission from role

        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        try:
            # get permissions
            roleperms = []
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)
                    # perms, total = self.manager.get_permissions(objid=perm['objid'], objtype=perm['subsystem'],
                    #                                             objdef=perm['type'], action=perm['action'], size=10)
                    # roleperms.extend(perms)

            res = self.manager.remove_role_permission(self.model, roleperms)
            self.logger.debug('Remove role %s permission : %s' % (self.name, perms))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)


class User(BaseUser):
    objdef = 'User'
    objdesc = 'System users'
    objuri = 'nas/users'

    def __init__(self, controller:AuthController, oid=None, objid=None, name=None, desc=None, model=None, active=True):
        self.manager: AuthDbManager
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
        info['email'] = self.model.email
        if self.model.last_login is not None:
            info['date']['last_login'] = format_date(self.model.last_login)

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = BaseUser.detail(self)
        info['email'] = self.model.email
        if self.model.last_login is not None:
            info['date']['last_login'] = format_date(self.model.last_login)

        return info

    @trace(op='update')
    def get_attribs(self):
        # verify permissions
        self.verify_permisssions('use')

        attrib = [{'name': a.name, 'value': a.value, 'desc': a.desc} for a in self.model.attrib]
        self.logger.debug('User %s attributes: %s' % (self.name, attrib))
        return attrib

    @trace(op='update')
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
        self.verify_permisssions('update')

        try:
            res = self.manager.set_user_attribute(self.model, name, value=value, desc=desc, new_name=new_name)
            self.logger.debug('Set user %s attribute %s: %s' % (self.name, name, value))
            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='update')
    def remove_attribute(self, name):
        """Remove an attribute

        :param name: attribute name
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        try:
            res = self.manager.remove_user_attribute(self.model, name)
            self.logger.debug('Remove user %s attribute %s' % (self.name, name))
            return None
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='update')
    def append_role(self, role_id, expiry_date=None):
        """Append role to user.

        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                y, m, d = expiry_date.split('-')
                expiry_date_obj = datetime(int(y), int(m), int(d))
            res = self.manager.append_user_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True:
                self.logger.debug('Append role %s to user %s' % (role, self.name))
            else:
                self.logger.debug('Role %s already linked with user %s' % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        return role_id

    @trace(op='update')
    def remove_role(self, role_id):
        """Remove role from user.

        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            res = self.manager.remove_user_role(self.model, role.model)
            self.logger.debug('Remove role %s from user %s' % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        return role_id

    @trace(op='view')
    def get_permissions(self, page=0, size=10, order='DESC', field='id', **kvargs):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, '*', 'view')

        try:
            perms, total = self.manager.get_user_permissions(self.model, page=page, size=size, order=order, field=field)
            user_perms = []
            for i in perms:
                user_perms.append({
                    'id': i.id,
                    'oid': i.obj.id,
                    'subsystem': i.obj.type.objtype,
                    'type': i.obj.type.objdef,
                    'objid': i.obj.objid,
                    'aid': i.action.id,
                    'action': i.action.value,
                    'desc': i.obj.desc
                })
            self.logger.debug('Get user %s permissions: %s' % (self.name, truncate(user_perms)))
            return user_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op='update')
    def append_permissions(self, perms):
        """Append permission to user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get internal user role
        role = self.manager.get_entity(ModelRole, 'User%sRole' % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)

            res = self.manager.append_role_permissions(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        self.logger.debug('Append user %s permission : %s' % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op='update')
    def remove_permissions(self, perms):
        """Remove permission from user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get internal user role
        role = self.manager.get_entity(ModelRole, 'User%sRole' % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)

            res = self.manager.remove_role_permission(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        self.logger.debug('Remove user %s permission : %s' % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op='use')
    def can(self, action, objtype, definition=None, name=None, perms=None):
        """Verify if  user can execute an action over a certain object type. Specify at least name or perms.

        :param perms: user permissions. Pandas Series with permissions
                      (pid, oid, type, definition, class, objid, aid, action) [optional]
        :param objtype: object type. Es. 'reosurce', 'service,
        :param definition: object definition. Es. 'container.org.group.vm'
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: list of non redundant permission objids
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('use')

        if perms is None:
            try:
                perms = self.get_permissions(self.name)
            except QueryError as ex:
                self.logger.error(ex, exc_info=False)
                raise ApiManagerError(ex)

        try:
            objids = []
            defs = []
            for perm in perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, 'resource', 'container.org.group.vm', 'Vm', 'c1.o1.g1.*', 6, 'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]

                # no definition is specify
                if definition is not None:
                    # verify object type, definition and action. If they match
                    # objid to values list
                    if perm_objtype == objtype and perm_definition == definition and perm_action in ['*', action]:
                        objids.append(perm_objid)
                else:
                    if perm_objtype == objtype and perm_action in ['*', action]:
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug('User %s can %s objects {%s, %s, %s}' %
                                  (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug('User %s can %s objects {%s, %s}' % (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception('User %s can not \'%s\' objects \'%s:%s\'' %
                                (self.name, action, objtype, definition))

        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)


class Group(AuthObject):
    objdef = 'Group'
    objdesc = 'System groups'
    objuri = 'nas/groups'

    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, model=None, active=True):
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, desc=desc, active=active, model=model)

        self.update_object = self.manager.update_group
        self.patch_object = self.manager.patch_group
        self.delete_object = self.manager.remove_group

    @trace(op='update')
    def append_role(self, role_id, expiry_date=None):
        """Append role to group.

        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                y, m, d = expiry_date.split('-')
                expiry_date_obj = datetime(int(y), int(m), int(d))
            res = self.manager.append_group_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True:
                self.logger.debug('Append role %s to group %s' % (role, self.name))
            else:
                self.logger.debug('Role %s already linked with group %s' % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        return role_id

    @trace(op='update')
    def remove_role(self, role_id):
        """Remove role from group.

        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            res = self.manager.remove_group_role(self.model, role.model)
            self.logger.debug('Remove role %s from group %s' % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        return role_id

    @trace(op='update')
    def append_user(self, user_id):
        """Append user to group.

        :param user_id: user name, id, or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, user.objid, 'view')

        try:
            res = self.manager.append_group_user(self.model, user.model)
            if res is True:
                self.logger.debug('Append user %s to group %s' % (user, self.name))
            else:
                self.logger.debug('User %s already linked with group %s' % (user, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(user_id)

        return user_id

    @trace(op='update')
    def remove_user(self, user_id):
        """Remove user from group.

        :param user_id: user id, name or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        try:
            res = self.manager.remove_group_user(self.model, user.model)
            self.logger.debug('Remove user %s from group %s' % (user, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(user_id)

        return user_id

    @trace(op='view')
    def get_permissions(self, page=0, size=10, order='DESC', field='id', **kvargs):
        """Get groups permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, '*', 'view')

        try:
            perms, total = self.manager.get_group_permissions(self.model, page=page, size=size, order=order,
                                                              field=field)
            group_perms = []
            for i in perms:
                group_perms.append({
                    'id': i.id,
                    'oid': i.obj.id,
                    'subsystem': i.obj.type.objtype,
                    'type': i.obj.type.objdef,
                    'objid': i.obj.objid,
                    'aid': i.action.id,
                    'action': i.action.value,
                    'desc': i.obj.desc
                })
            self.logger.debug('Get group %s permissions: %s' % (self.name, truncate(group_perms)))
            return group_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op='update')
    def append_permissions(self, perms):
        """Append permission to group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get internal group role
        role = self.manager.get_entity(ModelRole, 'Group%sRole' % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)

                    # perms, total = self.manager.get_permissions(objid=perm['objid'], objtype=perm['subsystem'],
                    #                                             objdef=perm['type'], action=perm['action'], size=10)
                    # roleperms.extend(perms)

            res = self.manager.append_role_permissions(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        self.logger.debug('Append group %s permission : %s' % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op='update')
    def remove_permissions(self, perms):
        """Remove permission from group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('update')

        # get internal group role
        role = self.manager.get_entity(ModelRole, 'Group%sRole' % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if 'id' in perm:
                    perm = self.manager.get_permission(perm['id'])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm['objid']
                    objtype = perm['subsystem']
                    objdef = perm['type']
                    objaction = perm['action']
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                roleperms.append(perm)
                    # perms, total = self.manager.get_permissions(objid=perm['objid'], objtype=perm['subsystem'],
                    #                                             objdef=perm['type'], action=perm['action'], size=10)
                    # roleperms.extend(perms)

            res = self.manager.remove_role_permission(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        self.logger.debug('Remove group %s permission : %s' % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op='use')
    def can(self, action, objtype, definition=None, name=None, perms=None):
        """Verify if  group can execute an action over a certain object type. Specify at least name or perms.

        :param perms: group permissions. Pandas Series with permissions
                      (pid, oid, type, definition, class, objid, aid, action) [optional]
        :param objtype: object type. Es. 'reosurce', 'service,
        :param definition: object definition. Es. 'container.org.group.vm'
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: list of non redundant permission objids
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions('use')

        if perms is None:
            try:
                perms = self.get_permissions(self.name)
            except QueryError as ex:
                self.logger.error(ex, exc_info=False)
                raise ApiManagerError(ex)

        try:
            objids = []
            defs = []
            for perm in perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, 'resource', 'container.org.group.vm', 'Vm', 'c1.o1.g1.*', 6, 'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]

                # no definition is specify
                if definition is not None:
                    # verify object type, definition and action. If they match
                    # objid to values list
                    if perm_objtype == objtype and perm_definition == definition and perm_action in ['*', action]:
                        objids.append(perm_objid)
                else:
                    if perm_objtype == objtype and perm_action in ['*', action]:
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug('Group %s can %s objects {%s, %s, %s}' %
                                  (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug('Group %s can %s objects {%s, %s}' % (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception('Group %s can not \'%s\' objects \'%s:%s\'' % (self.name, action, objtype, definition))

        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)
