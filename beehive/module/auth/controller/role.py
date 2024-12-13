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

from .objects import Objects


class Role(AuthObject):
    objdef = "Role"
    objdesc = "System roles"
    objuri = "nas/roles"

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
        self.manager: AuthDbManager
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
        info["alias"] = self.model.alias
        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AuthObject.info(self)
        info["alias"] = self.model.alias
        return info

    @trace(op="view")
    def get_permissions(self, page=0, size=10, order="DESC", field="id", **kvargs):
        """Get users permissions.

        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: dictionary with permissions
        :rtype: dict
        :raises ApiManagerError: if query empty return error.
        """
        self.controller.check_authorization(Objects.objtype, Objects.objdef, "*", "view")

        try:
            perms, total = self.manager.get_role_permissions(
                [self.name], page=page, size=size, order=order, field=field
            )
            role_perms = []
            for i in perms:
                role_perms.append(
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
            self.logger.debug("Get role %s permissions: %s" % (self.name, truncate(role_perms)))
            return role_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            return [], 0

    @trace(op="update")
    def append_permissions(self, perms):
        """Append permission to role

        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        try:
            # get permissions
            roleperms = []
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

            res = self.manager.append_role_permissions(self.model, roleperms)
            self.logger.debug("Append role %s permission : %s" % (self.name, res))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op="update")
    def remove_permissions(self, perms):
        """Remove permission from role

        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        try:
            # get permissions
            roleperms = []
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

            res = self.manager.remove_role_permission(self.model, roleperms)
            self.logger.debug("Remove role %s permission : %s" % (self.name, perms))
            return [str(p.id) for p in roleperms]
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)
