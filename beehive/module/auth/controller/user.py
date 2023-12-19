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
from .objects import Objects


class User(BaseUser):
    objdef = "User"
    objdesc = "System users"
    objuri = "nas/users"

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
        BaseUser.__init__(
            self,
            controller,
            oid=oid,
            objid=objid,
            name=name,
            desc=desc,
            active=active,
            model=model,
        )

        self.update_object = self.manager.update_user
        self.delete_object = self.manager.remove_user

    def info(self):
        """Get object info

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = BaseUser.info(self)
        info["email"] = self.model.email
        if self.model.last_login is not None:
            info["date"]["last_login"] = format_date(self.model.last_login)

        return info

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = BaseUser.detail(self)
        info["email"] = self.model.email
        if self.model.last_login is not None:
            info["date"]["last_login"] = format_date(self.model.last_login)

        return info

    @trace(op="update")
    def get_attribs(self):
        # verify permissions
        self.verify_permisssions("use")

        attrib = [{"name": a.name, "value": a.value, "desc": a.desc} for a in self.model.attrib]
        self.logger.debug("User %s attributes: %s" % (self.name, attrib))
        return attrib

    @trace(op="update")
    def set_attribute(self, name=None, value=None, desc="", new_name=None):
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
        self.verify_permisssions("update")

        try:
            res = self.manager.set_user_attribute(self.model, name, value=value, desc=desc, new_name=new_name)
            self.logger.debug("Set user %s attribute %s: %s" % (self.name, name, value))
            return res
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="update")
    def remove_attribute(self, name):
        """Remove an attribute

        :param name: attribute name
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        try:
            res = self.manager.remove_user_attribute(self.model, name)
            self.logger.debug("Remove user %s attribute %s" % (self.name, name))
            return None
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="update")
    def append_role(self, role_id, expiry_date=None):
        """Append role to user.

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
            res = self.manager.append_user_role(self.model, role.model, expiry_date=expiry_date_obj)
            if res is True:
                self.logger.debug("Append role %s to user %s" % (role, self.name))
            else:
                self.logger.debug("Role %s already linked with user %s" % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        return role_id

    @trace(op="update")
    def remove_role(self, role_id):
        """Remove role from user.

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
            res = self.manager.remove_user_role(self.model, role.model)
            self.logger.debug("Remove role %s from user %s" % (role, self.name))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        return role_id

    @trace(op="view")
    def get_permissions(self, page=0, size=10, order="DESC", field="id", **kvargs):
        """Get users permissions.

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
            perms, total = self.manager.get_user_permissions(self.model, page=page, size=size, order=order, field=field)
            user_perms = []
            for i in perms:
                user_perms.append(
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
            self.logger.debug("Get user %s permissions: %s" % (self.name, truncate(user_perms)))
            return user_perms, total
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

    @trace(op="update")
    def append_permissions(self, perms):
        """Append permission to user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get internal user role
        role = self.manager.get_entity(ModelRole, "User%sRole" % self.oid, for_update=False)

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

            res = self.manager.append_role_permissions(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        self.logger.debug("Append user %s permission : %s" % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op="update")
    def remove_permissions(self, perms):
        """Remove permission from user internal role

        :param perms: list of tuple ("id", "oid", "type", "definition", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("update")

        # get internal user role
        role = self.manager.get_entity(ModelRole, "User%sRole" % self.oid, for_update=False)

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

            res = self.manager.remove_role_permission(role, roleperms)
        except QueryError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)

        # remove all the user active tokens
        self.controller.remove_identities_for_user(self.oid)

        self.logger.debug("Remove user %s permission : %s" % (self.uuid, res))
        return [str(p.id) for p in roleperms]

    @trace(op="use")
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
                self.logger.debug("User %s can %s objects {%s, %s, %s}" % (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug("User %s can %s objects {%s, %s}" % (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception("User %s can not '%s' objects '%s:%s'" % (self.name, action, objtype, definition))

        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex)
