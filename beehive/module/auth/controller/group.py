# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

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
from .role import Role
from .user import User
from .objects import Objects


class Group(AuthObject):
    objdef = "Group"
    objdesc = "System groups"
    objuri = "nas/groups"

    def __init__(
        self,
        controller,
        oid=None,
        objid=None,
        name=None,
        desc=None,
        model=None,
        active=True,
    ):
        AuthObject.__init__(
            self,
            controller,
            oid=oid,
            objid=objid,
            name=name,
            desc=desc,
            active=active,
            model=model,
        )

        self.update_object = self.manager.update_group
        self.patch_object = self.manager.patch_group
        self.delete_object = self.manager.remove_group

    @trace(op="update")
    def append_role(self, role_id, expiry_date=None):
        """Append role to group.

        :param role_id: role name or id or uuid
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            expiry_date_obj = None
            if expiry_date is not None:
                y, m, d = expiry_date.split("-")
                expiry_date_obj = datetime(int(y), int(m), int(d))
            res = self.manager.append_group_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True:
                self.logger.debug("Append role %s to group %s" % (role, self.name))
            else:
                self.logger.debug("Role %s already linked with group %s" % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        return role_id

    @trace(op="update")
    def remove_role(self, role_id):
        """Remove role from group.

        :param role_id: role name or id or uuid
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get role
        role = self.controller.get_entity(Role, ModelRole, role_id)

        try:
            res = self.manager.remove_group_role(self.model, role.model)
            self.logger.debug("Remove role %s from group %s" % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the users active tokens
        self.controller.remove_identities_for_group(self.oid)

        return role_id

    @trace(op="update")
    def append_user(self, user_id):
        """Append user to group.

        :param user_id: user name, id, or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        # verify user permissions
        self.controller.check_authorization(User.objtype, User.objdef, user.objid, "view")

        try:
            res = self.manager.append_group_user(self.model, user.model)
            if res is True:
                self.logger.debug("Append user %s to group %s" % (user, self.name))
            else:
                self.logger.debug("User %s already linked with group %s" % (user, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(user_id)

        return user_id

    @trace(op="update")
    def remove_user(self, user_id):
        """Remove user from group.

        :param user_id: user id, name or uuid
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get user
        user = self.controller.get_entity(User, ModelUser, user_id)

        try:
            res = self.manager.remove_group_user(self.model, user.model)
            self.logger.debug("Remove user %s from group %s" % (user, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(user_id)

        return user_id

    @trace(op="view")
    def get_permissions(self, page=0, size=10, order="DESC", field="id", **kvargs):
        """Get groups permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, "*", "view")

        try:
            perms, total = self.manager.get_group_permissions(
                self.model, page=page, size=size, order=order, field=field
            )
            group_perms = []
            for i in perms:
                group_perms.append(
                    {
                        "id": i.id,
                        "oid": i.obj.id,
                        "subsystem": i.obj.type.objtype,
                        "type": i.obj.type.objdef,
                        "objid": i.obj.objid,
                        "aid": i.action.id,
                        "action": i.action.value,
                        "desc": i.obj.desc,
                    }
                )
            self.logger.debug("Get group %s permissions: %s" % (self.name, truncate(group_perms)))
            return group_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op="update")
    def append_permissions(self, perms):
        """Append permission to group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get internal group role
        role = self.manager.get_entity(ModelRole, "Group%sRole" % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if "id" in perm:
                    perm = self.manager.get_permission(perm["id"])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm["objid"]
                    objtype = perm["subsystem"]
                    objdef = perm["type"]
                    objaction = perm["action"]
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

        self.logger.debug("Append group %s permission : %s" % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op="update")
    def remove_permissions(self, perms):
        """Remove permission from group internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get internal group role
        role = self.manager.get_entity(ModelRole, "Group%sRole" % self.oid, for_update=False)

        roleperms = []
        try:
            # get permissions
            actions = {a.value: a.id for a in self.manager.get_object_action()}
            for perm in perms:
                # perm as permission_id
                if "id" in perm:
                    perm = self.manager.get_permission(perm["id"])
                    roleperms.append(perm)

                # perm as [subsystem, type, objid, action]
                else:
                    objid = perm["objid"]
                    objtype = perm["subsystem"]
                    objdef = perm["type"]
                    objaction = perm["action"]
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

        self.logger.debug("Remove group %s permission : %s" % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op="use")
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
        self.verify_permisssions("use")

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
                    if perm_objtype == objtype and perm_definition == definition and perm_action in ["*", action]:
                        objids.append(perm_objid)
                else:
                    if perm_objtype == objtype and perm_action in ["*", action]:
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug(
                    "Group %s can %s objects {%s, %s, %s}" % (self.name, action, objtype, definition, res)
                )
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug("Group %s can %s objects {%s, %s}" % (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception("Group %s can not '%s' objects '%s:%s'" % (self.name, action, objtype, definition))

        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)
