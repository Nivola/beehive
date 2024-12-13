# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from datetime import datetime
from re import match

# from six import ensure_text

# from beecell.auth import extract
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


class Objects(AuthObject):
    objdef = "Objects"
    objdesc = "Authorization objects"
    objuri = "nas/objects"

    def __init__(self, controller):
        AuthObject.__init__(self, controller, oid="", name="", desc="", active=True)

        self.objid = "*"

    #
    # System Object Type manipulation methods
    #
    @trace(op="view")
    def get_type(
        self,
        oid=None,
        subsystem=None,
        type=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
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
        self.verify_permisssions("view")

        try:
            data, total = self.manager.get_object_type(
                oid=oid,
                objtype=subsystem,
                objdef=type,
                page=page,
                size=size,
                order=order,
                field=field,
            )

            res = [
                {
                    "id": i.id,
                    "subsystem": i.objtype,
                    "type": i.objdef,
                    "date": {"creation": format_date(i.creation_date)},
                }
                for i in data
            ]

            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0

    @trace(op="insert")
    def add_types(self, obj_types):
        """Add a system object types

        :param obj_types: list of dict {'subsystem':.., 'type':..}
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("insert")

        try:
            data = [(i["subsystem"], i["type"]) for i in obj_types]
            res = self.manager.add_object_types(data)
            return [i.id for i in res]
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="delete")
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
        self.verify_permisssions("delete")

        try:
            res = self.manager.remove_object_type(oid=oid, objtype=objtype, objdef=objdef)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object Action manipulation methods
    #
    @trace(op="view")
    def get_action(self, oid=None, value=None):
        """Get system object action.

        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: List of Tuple (id, value)
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("view")

        try:
            data = self.manager.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError("No data found")
            if type(data) is not list:
                data = [data]
            res = [{"id": i.id, "value": i.value} for i in data]
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError(ex.value)

    @trace(op="insert")
    def add_actions(self, actions):
        """Add a system object action

        :param actions: list of string like 'use', 'view'
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("insert")

        try:
            res = self.manager.add_object_actions(actions)
            return True
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="delete")
    def remove_action(self, oid=None, value=None):
        """Add a system object action

        :param oid: System object action id [optional]
        :param value: string like 'use', 'view' [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("delete")

        try:
            res = self.manager.remove_object_action(oid=oid, value=value)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object manipulation methods
    #
    @trace(op="view")
    def get_object(self, oid):
        """Get system object filtered by id

        :param oid: object id
        :return: dict with object desc
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("view")

        try:
            data, total = self.manager.get_object(oid=oid)
            data = data[0]
            res = {
                "id": data.id,
                "uuid": data.uuid,
                "subsystem": data.type.objtype,
                "type": data.type.objdef,
                "objid": data.objid,
                "desc": data.desc,
                "active": str2bool(data.active),
                "date": {
                    "creation": format_date(data.creation_date),
                    "modified": format_date(data.modification_date),
                    "expiry": "",
                },
            }
            self.logger.debug("Get object: %s" % res)
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError("Object %s not found" % (oid), code=404)

    @trace(op="view")
    def get_objects(
        self,
        objid=None,
        subsystem=None,
        type=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
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
        self.verify_permisssions("view")

        try:
            authDbManager: AuthDbManager = self.manager
            data, total = authDbManager.get_object(
                objid=objid,
                objtype=subsystem,
                objdef=type,
                page=page,
                size=size,
                order=order,
                field=field,
            )

            res = [
                {
                    "id": i.id,
                    "uuid": i.uuid,
                    "subsystem": i.type.objtype,
                    "type": i.type.objdef,
                    "objid": i.objid,
                    "desc": i.desc,
                    "active": str2bool(i.active),
                    "date": {
                        "creation": format_date(i.creation_date),
                        "modified": format_date(i.modification_date),
                        "expiry": "",
                    },
                }
                for i in data
            ]
            self.logger.debug("Get objects: %s" % len(res))
            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0
        except Exception as ex:
            self.logger.error(ex, exc_info=False)
            return [], 0

    @trace(op="insert")
    def add_objects(self, objs):
        """Add a list of system objects with all the permission related to available action.

        :param objs: list of dict like {'subsystem':.., 'type':.., 'objid':.., 'desc':..}
        :return: list of uuid
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("insert")

        try:
            # get actions
            actions = self.manager.get_object_action()

            # create objects
            data = []
            for obj in objs:
                obj_type, total = self.manager.get_object_type(objtype=obj["subsystem"], objdef=obj["type"])
                data.append((obj_type[0], obj["objid"], obj["desc"]))

            res = self.manager.add_object(data, actions)
            self.logger.debug("Add objects: %s" % objs)
            return [i.id for i in res]
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="delete")
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
        self.verify_permisssions("delete")
        authDbManager: AuthDbManager = self.manager

        try:
            if objtype is not None or objdef is not None:
                # get object types
                obj_types, tot = authDbManager.get_object_type(objtype=objtype, objdef=objdef)
                for obj_type in obj_types:
                    res = authDbManager.remove_object(oid=oid, objid=objid, objtype=obj_type)
            else:
                res = authDbManager.remove_object(oid=oid, objid=objid)
            self.logger.debug("Remove objects: %s" % res)
            return None
        except TransactionError as ex:
            self.logger.error(ex, exc_info=False)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op="view")
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
        self.verify_permisssions("view")

        try:
            if oid is not None:
                p = self.manager.get_permission(oid)
            elif objid is not None or objtype is not None or objdef is not None:
                pp, total = self.manager.get_permissions(objid=objid, objtype=objtype, objdef=objdef, action=action)
                p = pp[0]
            res = {
                "id": p.id,
                "oid": p.obj.id,
                "subsystem": p.obj.type.objtype,
                "type": p.obj.type.objdef,
                "objid": p.obj.objid,
                "aid": p.action.id,
                "action": p.action.value,
                "desc": p.obj.desc,
            }
            return res
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            raise ApiManagerError("Permission %s not found" % (oid), code=404)

    @trace(op="view")
    def get_permissions(
        self,
        oid=None,
        objid=None,
        subsystem=None,
        type=None,
        cascade=False,
        page=0,
        size=10,
        order="DESC",
        field="id",
        **kvargs,
    ):
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
        self.verify_permisssions("view")

        try:
            res = []

            subsystems = None
            if subsystem is not None:
                subsystems = subsystem.split(",")

            if cascade is True:
                objids = [
                    objid,
                    objid + "//*",
                    objid + "//*//*",
                    objid + "//*//*//*",
                    objid + "//*//*//*//*",
                    objid + "//*//*//*//*//*",
                    objid + "//*//*//*//*//*//*",
                ]
                perms, total = self.auth_db_manager.get_deep_permissions(
                    objids=objids,
                    objtypes=subsystems,
                    page=page,
                    size=size,
                    order=order,
                    field=field,
                )

            else:
                perms, total = self.manager.get_permissions(
                    oid=oid,
                    objid=objid,
                    objid_filter=None,
                    objtypes=subsystems,
                    objdef=type,
                    objdef_filter=None,
                    action=None,
                    page=page,
                    size=size,
                    order=order,
                    field=field,
                )

            for p in perms:
                res.append(
                    {
                        "id": p.id,
                        "oid": p.obj.id,
                        "subsystem": p.obj.type.objtype,
                        "type": p.obj.type.objdef,
                        "objid": p.obj.objid,
                        "aid": p.action.id,
                        "action": p.action.value,
                        "desc": p.obj.desc,
                    }
                )

            self.logger.debug("Get permissions: %s" % len(res))
            return res, total
        except QueryError as ex:
            self.logger.error(ex.value, exc_info=False)
            return [], 0

    @trace(op="view")
    def get_permissions_roles(self, perms, *args, **kvargs):
        """List all roles associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        roles = []
        total = 0

        # verify permissions
        self.verify_permisssions("view")

        # get permissions id
        perm_ids = []
        authDbManager: AuthDbManager = self.manager
        actions = {a.value: a.id for a in authDbManager.get_object_action()}
        for perm in perms:
            if match("^\d+$", perm):
                perm = int(perm)

            if isinstance(perm, list):
                objtype, objdef, objid, objaction = perm
                try:
                    objs, tot = authDbManager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = authDbManager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(",")
                try:
                    objs, tot = authDbManager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = authDbManager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)
            else:
                try:
                    pp = authDbManager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)

        if len(perm_ids) > 0:
            roles, total = authDbManager.get_permissions_roles(perms=perm_ids, *args, **kvargs)

        self.logger.debug("Permissions %s are used by roles: %s" % (perms, truncate(roles)))
        return roles, total

    @trace(op="view")
    def get_permissions_users(self, perms, *args, **kvargs):
        """List all users associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        users = []
        total = 0

        # verify permissions
        self.verify_permisssions("view")

        # get permissions id
        perm_ids = []
        actions = {a.value: a.id for a in self.manager.get_object_action()}
        for perm in perms:
            if match("^\d+$", perm):
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
                    self.logger.warning("Permission %s was not found" % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(",")
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)
            else:
                try:
                    pp = self.manager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)

        if len(perm_ids) > 0:
            users, total = self.manager.get_permissions_users(perms=perm_ids, *args, **kvargs)

        self.logger.debug("Permissions %s are used by users: %s" % (perms, truncate(users)))
        return users, total

    @trace(op="view")
    def get_permissions_groups(self, perms, *args, **kvargs):
        """List all groups associated to a set of permissions

        :param perms: list of (subsystem, type, objid, action)
        :return:
        """
        groups = []
        total = 0

        # verify permissions
        self.verify_permisssions("view")

        # get permissions id
        perm_ids = []
        actions = {a.value: a.id for a in self.manager.get_object_action()}
        for perm in perms:
            if match("^\d+$", perm):
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
                    self.logger.warning("Permission %s was not found" % perm)
            elif isinstance(perm, str):
                objtype, objdef, objid, objaction = perm.split(",")
                try:
                    objs, tot = self.manager.get_object(objid=objid, objtype=objtype, objdef=objdef)
                    for obj in objs:
                        perms = self.manager.get_permission_by_id(object_id=obj.id)
                        for perm in perms:
                            if perm.action_id == actions.get(objaction):
                                perm_ids.append(str(perm.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)
            else:
                try:
                    pp = self.manager.get_permission(int(perm))
                    perm_ids.append(str(pp.id))
                except:
                    self.logger.warning("Permission %s was not found" % perm)

        if len(perm_ids) > 0:
            groups, total = self.manager.get_permissions_groups(perms=perm_ids, *args, **kvargs)

        self.logger.debug("Permissions %s are used by groups: %s" % (perms, truncate(groups)))
        return groups, total
