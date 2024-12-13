# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from datetime import datetime
from re import match
from six import ensure_text

from beecell.auth import extract
from beecell.simple import id_gen, truncate, str2bool, format_date
from beehive.common.apimanager import ApiManagerError
from beecell.db import TransactionError, QueryError
from beehive.common.controller.authorization import (
    BaseAuthController,
    User as BaseUser,
    Token,
    AuthObject,
)
from beehive.common.data import trace, operation
from beehive.common.model.authorization import (
    AuthDbManager,
    User as ModelUser,
    Role as ModelRole,
    Group as ModelGroup,
    SysObject as ModelObject,
)
from typing import List, Tuple, TYPE_CHECKING


from .group import Group
from .objects import Objects
from .user import User
from .role import Role


class AuthController(BaseAuthController):
    """Auth Module controller.

    :param module: Beehive module
    """

    version = "v1.0"

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
        actions = [
            "*",
            "view",
            "insert",
            "update",
            "delete",
            "use",
            "disable",
            "recover",
        ]
        for action in actions:
            try:
                self.manager.add_object_action(action)
            except TransactionError as ex:
                self.logger.warning(ex)

        BaseAuthController.init_object(self)

    def count(self):
        """Count users, groups, roles and objects"""
        try:
            res = {
                "users": self.manager.count_entities(ModelUser),
                "groups": self.manager.count_entities(ModelGroup),
                "roles": self.manager.count_entities(ModelRole),
                "objects": self.manager.count_entities(ModelObject),
            }
            return res
        except QueryError as ex:
            raise ApiManagerError(ex, code=ex.code)

    #
    # role manipulation methods
    #
    @trace(entity="Role", op="view")
    def get_role(self, oid):
        """Get single role.

        :param oid: entity model id or name or uuid
        :return: Role
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Role, ModelRole, oid)

    def use_role(self, roleoid):
        pass

    @trace(entity="Role", op="view")
    def get_roles(self, *args, **kvargs) -> Tuple[List, int]:
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
            perms = kvargs.get("perms_N", None)
            groups = kvargs.get("groups_N", None)
            group = kvargs.get("group", None)
            user = kvargs.get("user", None)

            # search roles by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                roles, total = self.objects.get_permissions_roles(perms=perms, *args, **kvargs)

            # search roles by user
            elif user is not None:
                kvargs["user_id"] = self.get_entity(User, ModelUser, user).oid
                iroles, total = self.manager.get_user_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    self.logger.debug("+++++ role: %s" % role)
                    role[0].expiry_date = role[1]
                    roles.append(role[0])

            # search roles by group
            elif group is not None:
                kvargs["group_id"] = self.get_entity(Group, ModelGroup, group).oid
                iroles, total = self.manager.get_group_roles(*args, **kvargs)
                roles = []
                for role in iroles:
                    self.logger.debug("+++++ role: %s" % role)
                    role[0].expiry_date = role[1]
                    roles.append(role[0])

            # search roles by groups_N
            elif groups is not None:
                kvargs["group_id_list"] = [str(self.get_entity(Group, ModelGroup, group).oid) for group in groups]
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

    def add_base_role(self, name, desc="", alias=""):
        """Add new role.

        :param name: name of the role
        :param desc: role desc. [Optional]
        :param alias: role alias. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Role.objtype, Role.objdef, None, "insert")

        try:
            objid = id_gen()
            role = self.manager.add_role(objid, name, desc, alias=alias)

            # add object and permission
            Role(self, oid=role.id).register_object([objid], desc=desc)

            self.logger.debug("Add new role: %s" % name)
            return role
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity="Role", op="insert")
    def add_role(self, name=None, desc="", alias=""):
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

    @trace(entity="Role", op="admin.insert")
    def add_superadmin_role(self, perms):
        """Add beehive admin role with all the required permissions.

        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role("ApiSuperadmin", "Beehive super admin role")

        # append permissions
        try:
            self.manager.append_role_permissions(role, perms)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        return role

    @trace(entity="Role", op="guest.insert")
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.

        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_base_role("Guest", "Beehive guest role")
        return role

    #
    # user manipulation methods
    #
    @trace(entity="User", op="view")
    def exist_user(self, oid):
        """Check user exists.

        :param oid: entity model id or name or uuid
        :return: True if exists
        """
        return self.manager.exist_entity(ModelUser, oid)

    @trace(entity="User", op="view")
    def get_user(self, oid, action="view"):
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
            raise ApiManagerError("%s %s not found or name is not unique" % (entity_name, oid), code=404)

        if entity is None:
            self.logger.warning("%s %s not found" % (entity_name, oid))
            raise ApiManagerError("%s %s not found" % (entity_name, oid), code=404)

        # check authorization
        # - check identity has action over some groups that contain user
        groups, tot = self.manager.get_user_groups(user_id=entity.id, size=-1, with_perm_tag=False)
        groups_objids = [g.objid for g in groups]
        perms_objids = self.can(action, objtype=entity_class.objtype, definition=Group.objdef).get(
            Group.objdef.lower(), []
        )
        if len(set(groups_objids) & set(perms_objids)) == 0:
            # - check identity has action over the user
            self.check_authorization(entity_class.objtype, entity_class.objdef, entity.objid, action)

        res = entity_class(
            self,
            oid=entity.id,
            objid=entity.objid,
            name=entity.name,
            active=entity.active,
            desc=entity.desc,
            model=entity,
        )

        # execute custom post_get
        res.post_get()

        self.logger.debug("Get %s : %s" % (entity_class.__name__, res))
        return res

    def _verify_operation_user_role(self, role="ApiSuperadmin"):
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
            self.logger.debug("User %s has role %s" % (user_name, role))
            return True

        self.logger.warning("User %s has not role %s" % (user_name, role))
        return False

    @trace(entity="User", op="use")
    def get_user_secret(self, oid):
        """Get user secret.

        :param oid: entity model id or name or uuid
        :return: User
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # disable authorization check
        # operation.authorize = False

        role1 = "ApiSuperadmin"
        role2 = "CsiOperator"
        if self._verify_operation_user_role(role1) is True or self._verify_operation_user_role(role2) is True:
            user = self.get_user(oid, action="use")
            secret = user.model.secret
            self.logger.debug("Get user %s secret" % user.uuid)
            return secret
        else:
            raise ApiManagerError(
                value="This operation require one of this roles: %s, %s" % (role1, role2),
                code=400,
            )

        # enable authorization check
        # operation.authorize = True

    @trace(entity="User", op="update")
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
            raise ApiManagerError(
                value="Invalid ApiSuperadmin role for operation user %s" % operation.user[0],
                code=400,
            )

        user = self.get_user(oid, action="update")
        try:
            if match_old_secret:
                matched = self.manager.verify_user_secret(user.model, old_secret)
            if matched is False:
                raise ApiManagerError(value="Invalid old secret key for user id %s" % oid, code=400)
            else:
                res = self.manager.set_user_secret(user.model.id)
            self.logger.debug("Reset user %s secret" % user.uuid)
            return user.model.secret
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity="User", op="view")
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
            role = kvargs.get("role", None)
            expiry_date = kvargs.get("expiry_date", None)
            group_id = kvargs.get("group_id", None)
            perms = kvargs.get("perms_N", None)

            # search users by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                users, total = self.objects.get_permissions_users(perms=perms, *args, **kvargs)

            # search users by role
            elif role is not None:
                kvargs["role_id"] = self.get_entity(Role, ModelRole, role).oid
                users, total = self.manager.get_role_users(*args, **kvargs)

            # search users by group
            elif group_id is not None:
                users, total = self.manager.get_group_users(*args, **kvargs)

            # get all users
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split("-")
                    kvargs["expiry_date"] = datetime(int(y), int(m), int(g))
                users, total = self.manager.get_users(*args, **kvargs)

            return users, total

        # check group filter
        group = kvargs.get("group", None)

        # search users by group
        if group is not None:
            kvargs["group_id"] = self.get_entity(Group, ModelGroup, group).oid
            operation.authorize = False

        res, total = self.get_paginated_entities(User, get_entities, *args, **kvargs)
        return res, total

    @trace(entity="User", op="insert")
    def add_user(
        self,
        name=None,
        storetype=None,
        active=True,
        password=None,
        desc="",
        expiry_date=None,
        base=False,
        system=False,
        email=None,
        taxcode=None,
        ldap=None,
    ):
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
        self.check_authorization(User.objtype, User.objdef, None, "insert")

        try:
            objid = id_gen()
            user = self.manager.add_user(
                objid,
                name,
                active=active,
                password=password,
                desc=desc,
                expiry_date=expiry_date,
                is_generic=base,
                is_admin=system,
                email=email,
                taxcode=taxcode,
                ldap=ldap,
            )
            # add object and permission
            obj = User(
                self,
                oid=user.id,
                objid=user.objid,
                name=user.name,
                desc=user.desc,
                model=user,
                active=user.active,
            )

            obj.register_object([objid], desc=desc)

            # add default attributes
            if system is True:
                systype = "SYS"
                storetype = "DBUSER"
            else:
                systype = "USER"
            self.manager.set_user_attribute(user, "store_type", storetype, "Type of user store")
            self.manager.set_user_attribute(user, "sys_type", systype, "Type of user")

            self.logger.debug("Add new user: %s" % name)
            return obj.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity="Token", op="delete")
    def remove_identities_for_user(self, user_id):
        """Remove active beehive identities for a certain user

        :param user_id: user name or email
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, "*", "delete")

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

                self.logger.debug("Remove identity %s from redis" % uid)
            except:
                self.logger.warning("Can not remove identity %s" % uid)
        return True

    #
    # group manipulation methods
    #
    @trace(entity="Group", op="view")
    def get_group(self, oid):
        """Get single group.

        :param oid: entity model id or name or uuid
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Group, ModelGroup, oid)

    @trace(entity="Group", op="view")
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
            role = kvargs.get("role", None)
            user = kvargs.get("user", None)
            perms = kvargs.get("perms_N", None)
            expiry_date = kvargs.get("expiry_date", None)

            # search groups by permissions
            if perms is not None:
                # perms = [perm.split(',') for perm in perms]
                groups, total = self.objects.get_permissions_groups(perms=perms, *args, **kvargs)

            # search groups by role
            elif role:
                kvargs["role_id"] = self.get_entity(Role, ModelRole, role).oid
                groups, total = self.manager.get_role_groups(*args, **kvargs)

            # search groups by user
            elif user is not None:
                kvargs["user_id"] = self.get_entity(User, ModelUser, user).oid
                groups, total = self.manager.get_user_groups(*args, **kvargs)

            # get all groups
            else:
                if expiry_date is not None:
                    g, m, y = expiry_date.split("-")
                    kvargs["expiry_date"] = datetime(int(y), int(m), int(g))
                groups, total = self.manager.get_groups(*args, **kvargs)

            return groups, total

        res, total = self.get_paginated_entities(Group, get_entities, *args, **kvargs)
        return res, total

    @trace(entity="Group", op="insert")
    def add_group(self, name=None, desc="", active=None, expiry_date=None):
        """Add new group.

        :param name: name of the group
        :param active: Group status. If True user is active [Optional] [Default=True]
        :param desc: Group desc. [Optional]
        :param expiry_date: Group expiry date. Set as gg-mm-yyyy [default=365 days]
        :return: group id
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # check authorization
        self.check_authorization(Group.objtype, Group.objdef, None, "insert")

        try:
            objid = id_gen()
            group = self.manager.add_group(objid, name, desc=desc, active=active, expiry_date=expiry_date)

            # add object and permission
            Group(self, oid=group.id).register_object([objid], desc=desc)

            self.logger.debug("Add new group: %s" % name)
            return group.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=400)

    @trace(entity="Token", op="delete")
    def remove_identities_for_group(self, group_id):
        """Remove active beehive identities for all the users in a group

        :param group_id: group id
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, "*", "delete")

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

                    self.logger.debug("Remove identity %s from redis" % uid)
                except:
                    self.logger.warning("Can not remove identity %s" % uid)
        return True
