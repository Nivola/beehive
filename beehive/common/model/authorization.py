# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import inspect
import logging
from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt
from beecell.auth import AbstractAuthDbManager
from sqlalchemy import Column, Integer, String, Table, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func
from sqlalchemy.sql import text
from beecell.simple import truncate, id_gen, random_password, is_encrypted
from beecell.db import ModelError, QueryError
from beehive.common.data import query, transaction, decrypt_data
from sqlalchemy.dialects import mysql
from typing import List
from re import match

Base = declarative_base()

from beehive.common.model import AbstractDbManager, BaseEntity, PaginatedQueryGenerator


logger = logging.getLogger(__name__)

# Many-to-Many Relationship among groups and useradd_users
group_user = Table(
    "groups_users",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("group_id", Integer, ForeignKey("group.id")),
    Column("user_id", Integer, ForeignKey("user.id")),
)

# Many-to-Many Relationship among system roles and objects permissions
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id")),
    Column("permission_id", Integer, ForeignKey("sysobject_permission.id")),
)

# # Many-to-Many Relationship among system role_templates and policies
# role_template_policy = Table('role_template_policy', Base.metadata,
#     Column('id', Integer, primary_key=True),
#     Column('role_template_id', Integer, ForeignKey('role_template.id')),
#     Column('policy_id', Integer, ForeignKey('syspolicy.id'))
# )


class RoleUser(Base):
    """Authorizationrole user association

    :param user_id: user id
    :param role_id: role id
    :param expiry_date: relation expiry date [default=365 days]. Set using a datetime object
    """

    __tablename__ = "roles_users"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    role_id = Column(Integer, ForeignKey("role.id"))
    expiry_date = Column(DateTime())
    user = relationship("User", back_populates="role")
    role = relationship("Role", back_populates="user")

    def __init__(self, user_id, role_id, expiry_date=None):
        self.user_id = user_id
        self.role_id = role_id
        if expiry_date is None:
            expiry_date = datetime.today() + timedelta(days=365)
        self.expiry_date = expiry_date

    def __repr__(self):
        return "<RoleUser user=%s role=%s expiry=%s>" % (
            self.user_id,
            self.role_id,
            self.expiry_date,
        )


class RoleGroup(Base):
    """Authorizationrole group association

    :param group_id: group id
    :param role_id: role id
    :param expiry_date: relation expiry date [default=365 days]. Set using a datetime object
    """

    __tablename__ = "roles_groups"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group.id"))
    role_id = Column(Integer, ForeignKey("role.id"))
    expiry_date = Column(DateTime())
    group = relationship("Group", back_populates="role")
    role = relationship("Role", back_populates="group")

    def __init__(self, group_id, role_id, expiry_date=None):
        self.group_id = group_id
        self.role_id = role_id
        if expiry_date is None:
            expiry_date = datetime.today() + timedelta(days=365)
        self.expiry_date = expiry_date

    def __repr__(self):
        return "<RoleGroup group=%s role=%s expiry=%s>" % (
            self.group_id,
            self.role_id,
            self.expiry_date,
        )


# Systems roles
class Role(Base):
    """Authorization role

    :param objid: authorization id
    :param name: name
    :param permission: permission
    :param desc: description [optional]
    :param active: active [default=True]
    :param alias: alias [default='']
    """

    __tablename__ = "role"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    permission = relationship(
        "SysObjectPermission",
        secondary=role_permission,
        backref=backref("role", lazy="dynamic"),
    )
    user = relationship("RoleUser", back_populates="role")
    group = relationship("RoleGroup", back_populates="role")
    alias = Column(String(100))
    template = Column(Integer())
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())

    def __init__(self, objid, name, permission, desc="", active=True, alias=""):
        BaseEntity.__init__(self, objid, name, desc, active)

        self.uuid = str(uuid4())
        self.objid = str(objid)
        self.name = name
        self.desc = desc
        self.active = active
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date
        self.permission = permission
        self.alias = alias
        self.expiry_date = None


# Systems roles
class UserAttribute(Base):
    """Authorization user attribute

    :param user: user id
    :param name: attribute name
    :param value: attribute value
    :param desc: attribute desc
    """

    __tablename__ = "user_attribute"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer(), primary_key=True)
    name = Column(String(30))
    value = Column(String(100))
    desc = Column(String(255))
    user_id = Column(Integer(), ForeignKey("user.id"))

    def __init__(self, user, name, value, desc=""):
        self.user_id = user
        self.name = name
        self.value = value
        self.desc = desc

    def __repr__(self):
        return "<UserAttribute id=%s user=%s name=%s value=%s>" % (
            self.id,
            self.user_id,
            self.name,
            self.value,
        )


class User(Base, BaseEntity):
    """Authorization user

    :param objid: authorization id
    :param username: name of the user
    :param active: set if user is active [default=True]
    :param password: user password [optional]
    :param desc: user desc [default='']
    :param expiry_date: user expiry date [default=365 days]. Set using a datetime object
    :param email: email [optional]
    """

    __tablename__ = "user"

    password = Column(String(150))
    email = Column(String(100))
    secret = Column(String(150))
    role = relationship("RoleUser", back_populates="user")
    attrib = relationship("UserAttribute")
    last_login = Column(DateTime())
    taxcode = Column(String(16))
    ldap = Column(String(100))

    def __init__(
        self,
        objid,
        name,
        active=True,
        password=None,
        desc="",
        expiry_date=None,
        email=None,
        taxcode=None,
        ldap=None,
    ):
        BaseEntity.__init__(self, objid, name, desc, active)

        self.role = []

        if expiry_date is None:
            expiry_date = datetime.today() + timedelta(days=365)
        self.expiry_date = expiry_date

        if password is not None:
            password = password.encode("utf-8")
            # generate new salt, and hash a password
            # self.password = sha256_crypt.encrypt(password)
            self.password = bcrypt.hashpw(password, bcrypt.gensalt(14))

        self.secret = random_password(length=100)
        self.last_login = None
        self.email = email
        self.taxcode = taxcode
        self.ldap = ldap

    def _check_password(self, password):
        # verifying the password
        if is_encrypted(self.password):
            res = decrypt_data(self.password) == password.encode("utf-8")
        else:
            res = bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))
        return res

    def _check_secret(self, secret):
        # verifying the secret
        res = secret == self.secret
        return res


class Group(Base, BaseEntity):
    """Authorization group

    :param objid: authorization id
    :param name: name of the group
    :param member: user member [default=[]]
    :param role: role [optional]
    :param desc: group desc [default='']
    :param active: set if group is active [default=True]
    :param expiry_date: group expiry date [default=365 days]. Set using a datetime object
    """

    __tablename__ = "group"

    member = relationship("User", secondary=group_user, backref=backref("group", lazy="dynamic"))
    role = relationship("RoleGroup", back_populates="group")

    def __init__(self, objid, name, member=[], role=[], desc=None, active=True, expiry_date=None):
        BaseEntity.__init__(self, objid, name, desc, active)

        self.member = member
        self.role = role

        if expiry_date is None:
            expiry_date = datetime.today() + timedelta(days=365)
        self.expiry_date = expiry_date


# System object types
class SysObjectType(Base):
    """Authorization object type

    :param objtype: object type. String like service, resource, container
    :param objdef: object defintition. String like vdcservice, openstack
    :param objclass: object class. String like Openstack
    """

    __tablename__ = "sysobject_type"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    objtype = Column(String(100))
    objdef = Column(String(200))
    objclass = Column(String(100))
    creation_date = Column(DateTime())

    def __init__(self, objtype, objdef, objclass):
        self.objtype = objtype
        self.objdef = objdef
        self.objclass = None
        self.creation_date = datetime.today()

    def __repr__(self):
        return "<SysObjectType id=%s type=%s def=%s>" % (
            self.id,
            self.objtype,
            self.objdef,
        )


# System objects
class SysObject(Base, BaseEntity):
    """Authorization object

    :param objid: authorization id
    :param otype: object type
    :param desc: object desc [default='']
    """

    __tablename__ = "sysobject"

    name = Column(String(100))
    type_id = Column(Integer(), ForeignKey("sysobject_type.id"))
    type = relationship("SysObjectType", backref="sysobject")

    def __init__(self, otype, objid, desc=""):
        BaseEntity.__init__(self, objid, "", desc, True)

        self.type = otype

    def __repr__(self):
        return "<SysObject id=%s type=%s def=%s objid=%s>" % (
            self.id,
            self.type.objtype,
            self.type.objdef,
            self.objid,
        )


# System object actions
class SysObjectAction(Base):
    """Authorization object action

    :param value: action
    """

    __tablename__ = "sysobject_action"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    value = Column(String(20), unique=True)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<SysObjectAction id=%s value=%s>" % (self.id, self.value)


# System object permissions
class SysObjectPermission(Base):
    """Authorization object permission

    :param obj: object
    :param action: action
    """

    __tablename__ = "sysobject_permission"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = Column(Integer, primary_key=True)
    obj_id = Column(Integer(), ForeignKey("sysobject.id"))
    obj = relationship("SysObject")
    action_id = Column(Integer(), ForeignKey("sysobject_action.id"))
    action = relationship("SysObjectAction")

    def __init__(self, obj, action):
        self.obj = obj
        self.action = action

    def __repr__(self):
        return "<SysObjectPermission id=%s type=%s def=%s objid=%s action=%s>" % (
            self.id,
            self.obj.type.objtype,
            self.obj.type.objdef,
            self.obj.objid,
            self.action.value,
        )


# # System object policy
# class SysPolicy(Base):
#     __tablename__ = 'syspolicy'
#     __table_args__ = {'mysql_engine': 'InnoDB'}
#
#     id = Column(Integer, primary_key=True)
#     objid_tmpl = Column(String(400))
#     type_id = Column(Integer(), ForeignKey('sysobject_type.id'))
#     type = relationship(u"SysObjectType", backref=u"sysobject_type")
#     action_id = Column(Integer(), ForeignKey('sysobject_action.id'))
#     action = relationship('SysObjectAction')
#
#     def __init__(self, objid_tmpl, type, action):
#         self.type = type
#         self.action = action
#
#     def __repr__(self):
#         return u"<SysPolicy id=%s type=%s def=%s action=%s>" % (
#                     self.id, self.type.objtype, self.type.objdef, self.action.value)


class AuthDbManager(AbstractAuthDbManager, AbstractDbManager):
    """Authorization db manager

    :param session: sqlalchemy session
    """

    def __init__(self, session=None):
        AbstractDbManager.__init__(self, session)
        AbstractAuthDbManager.__init__(self, session)

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table" statements in raw SQL

        :param db_uri: db uri
        """
        AbstractDbManager.create_table(db_uri)

        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=1;")
            Base.metadata.create_all(engine)
            logger.info("Create tables on : %s" % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    @staticmethod
    def remove_table(db_uri):
        """Remove all tables in the engine. This is equivalent to "Drop Table" statements in raw SQL

        :param db_uri: db uri
        """
        AbstractDbManager.remove_table(db_uri)

        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=0;")
            Base.metadata.drop_all(engine)
            logger.info("Remove tables from : %s" % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    def set_initial_data(self):
        """Set initial data."""

        @transaction(self.get_session())
        def func(session):
            # object actions
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
            data = []
            for item in actions:
                data.append(SysObjectAction(item))
            session.add_all(data)
            self.logger.debug("Add object actions: %s" % actions)

        return func()

    #
    # System Object Type manipulation methods
    #
    @query
    def get_object_type(
        self,
        oid=None,
        objtype=None,
        objdef=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
        """Get system object type.

        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :param page: type list page to show [default=0]
        :param size: number of types to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: SysObjectType corresponding to oid or value. If no param are  specified return all the system object
            types.
        :rtype: list of :class:`SysObjectType`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if oid is not None:
            ot = session.query(SysObjectType).filter_by(id=oid)
        elif objtype is not None or objdef is not None:
            ot = session.query(SysObjectType)
            if objtype is not None:
                ot = ot.filter_by(objtype=objtype)
            if objdef is not None:
                ot = ot.filter_by(objdef=objdef)
        else:
            ot = session.query(SysObjectType)

        total = ot.count()

        start = size * page
        end = size * (page + 1)
        ot = ot.order_by(text("%s %s" % (field, order)))[start:end]

        if len(ot) <= 0:
            raise ModelError("No object types found")

        self.logger.debug("Get object types: %s" % truncate(ot))
        return ot, total

    @transaction
    def add_object_types(self, items):
        """Add a list of system object types.

        :param items: list of (objtype, objdef) tuple
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        data = []

        # insert new types only if they doesn't already exist
        for objtype, objdef in items:
            ot = session.query(SysObjectType).filter_by(objtype=objtype).filter_by(objdef=objdef).first()
            if ot is None:
                record = SysObjectType(objtype, objdef, None)
                data.append(record)
        session.add_all(data)
        session.flush()

        self.logger.debug("Add object types: %s" % data)
        return data

    @transaction
    def remove_object_type(self, oid=None, objtype=None, objdef=None):
        """Remove system object type.

        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid:
            ots = session.query(SysObjectType).filter_by(id=oid).all()
        elif objtype is not None or objdef is not None:
            ots = session.query(SysObjectType)
            if objtype is not None:
                ots = ots.filter_by(objtype=objtype)
            if objdef is not None:
                ots = ots.filter_by(objdef=objdef)
            ots = ots.all()

        # delete object types
        if len(ots) > 0:
            for ot in ots:
                session.delete(ot)
            self.logger.debug("Remove object types: %s" % ots)
            return True
        else:
            raise ModelError("No object types found")

    #
    # System Object Action manipulation methods
    #
    @query
    def get_object_action(self, oid=None, value=None):
        """Get system object action.

        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: SysObjectAction corresponding to oid or value. If no param are specified return all the system object
            actions.
        :rtype: list of :class:`SysObjectAction`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if oid is not None:
            oa = session.query(SysObjectAction).filter_by(id=oid).first()
        elif value is not None:
            oa = session.query(SysObjectAction).filter_by(value=value).first()
        else:
            oa = session.query(SysObjectAction).all()
        self.logger.debug("Get object action: %s" % truncate(oa))
        return oa

    @transaction
    def add_object_actions(self, items):
        """Add a list of system object actions.

        :param items: list of strings that define the action. Es. 'view', 'use', 'insert'
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        data = []
        for item in items:
            data.append(SysObjectAction(item))

        session.add_all(data)
        self.logger.debug("Add object action: %s" % data)
        session.flush()
        return items

    @transaction
    def add_object_action(self, item):
        """Add a system object actions.

        :param item: action. Es. 'view', 'use', 'insert'
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        session.add(SysObjectAction(item))
        self.logger.debug("Add object action: %s" % item)
        session.flush()
        return item

    @transaction
    def remove_object_action(self, oid=None, value=None):
        """Remove system object action.

        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid is not None:
            ot = session.query(SysObjectAction).filter_by(id=oid).first()
        elif value is not None:
            ot = session.query(SysObjectAction).filter_by(value=value).first()
        if ot is not None:
            # delete object action
            session.delete(ot)
            self.logger.debug("Delete action: %s" % ot)
            return True
        else:
            return False

    #
    # System Object manipulation methods
    #
    @query
    def count_object(self):
        """Coint system object."""
        session = self.get_session()
        res = session.query(func.count(SysObject.id))

        self.logger.debug("Count objects: %s" % res)
        return res

    @query
    def get_object(
        self,
        oid=None,
        objid=None,
        objtype=None,
        objdef=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
        """Get system object filtering by id, by name or by type.

        :param str oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: object type [optional]
        :param objdef: object definition [optional]
        :param page: object list page to show [default=0]
        :param size: number of object to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: one SysObject or a list of SysObject
        :rtype: :class:`SysObject` or list of :class:`SysObject`
        :raises QueryError: raise :class:`.decorator.QueryError` if query return error
        """
        session = self.get_session()
        sqlcount = ["SELECT count(t1.id) as count FROM sysobject t1, sysobject_type t2 WHERE t1.type_id=t2.id"]
        sql = [
            "SELECT t1.id as id, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef",
            "FROM sysobject t1, sysobject_type t2 WHERE t1.type_id=t2.id",
        ]

        params = {}
        if oid is not None:
            sql.append("AND t1.id LIKE :id")
            sqlcount.append("AND t1.id = :id")
            params["id"] = oid
        if objid is not None:
            sql.append("AND t1.objid LIKE :objid")
            sqlcount.append("AND t1.objid LIKE :objid")
            params["objid"] = objid
        if objtype is not None:
            sql.append("AND t2.objtype LIKE :objtype")
            sqlcount.append("AND t2.objtype = :objtype")
            params["objtype"] = objtype
        if objdef is not None:
            sql.append("AND t2.objdef LIKE :objdef")
            sqlcount.append("AND t2.objdef LIKE :objdef")
            params["objdef"] = objdef

        # get total rows
        total = session.execute(" ".join(sqlcount), params).fetchone()[0]

        sql.append("ORDER BY %s %s" % (field, order))

        if size > 0:
            offset = size * page
            sql.append("LIMIT %s OFFSET %s" % (size, offset))
        elif size == -1:
            sql.append("LIMIT 10000")
        else:
            sql.append("LIMIT %s" % (size))

        query = session.query(SysObject).from_statement(text(" ".join(sql))).params(params)
        self.logger.debug2("+++++ SQL - stmp: %s" % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2("+++++ SQL - params: %s" % truncate(params, size=2000))

        res = query.all()
        if len(res) <= 0:
            self.logger.error("No objects (%s, %s, %s, %s) found" % (oid, objid, objdef, objtype))
            raise ModelError("No objects (%s, %s, %s, %s) found" % (oid, objid, objdef, objtype))

        self.logger.debug("Get objects: %s" % truncate(res))
        return res, total

    @transaction
    def add_object(self, objs, actions):
        """Add a system object.

        :param objs: list of (SysObjectType, objid) tuple
        :param objs: list of SysObjectAction
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        res = []
        items = []
        for obj in objs:
            # verify if object already exists
            sysobj = session.query(SysObject).filter_by(objid=obj[1]).filter_by(type=obj[0]).first()
            if sysobj is not None:
                self.logger.error("Object %s already exists" % sysobj)
                raise ModelError("Object %s already exists" % sysobj, code=409)

            # add object
            sysobj = SysObject(obj[0], obj[1], desc=obj[2])
            # session.add(sysobj)
            items.append(sysobj)
            # session.flush()
            self.logger.debug("Add system object: %s" % sysobj)

            # add permissions
            for action in actions:
                perm = SysObjectPermission(sysobj, action)
                # session.add(perm)
                items.append(perm)
            self.logger.debug("Add system object %s permissions" % sysobj.id)
        session.add_all(items)
        return items

    @transaction
    def update_object(self, new_objid, oid=None, objid=None, objtype=None):
        """Delete system object filtering by id, by name or by type.

        Examples:
            manager.update_object(oid='123242')
            manager.update_object(value='', type="cloudstack.vm")
            manager.update_object(value='clsk42_01.ROOT/CSI.')

        :param new_objid: new object id [optional]
        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: System object type [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        data = {"objid": new_objid, "modification_date": datetime.today()}
        if oid is not None:
            query = session.query(SysObject).filter_by(oid=oid)
        if objid is not None:
            query = session.query(SysObject).filter_by(objid=objid)
        if objtype is not None:
            query = session.query(SysObject).filter_by(objtype=objtype)

        query.update(data)
        self.logger.debug("Update objects: %s" % data)
        return True

    @transaction
    def remove_object(self, oid=None, objid=None, objtype=None):
        """Delete system object filtering by id, by name or by type.

        Examples:
            manager.remove_object(oid='123242')
            manager.remove_object(value='', type="cloudstack.vm")
            manager.remove_object(value='clsk42_01.ROOT/CSI.')

        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: System object type [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        # query object
        sql = [
            "SELECT t1.id as id, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef",
            "FROM sysobject t1, sysobject_type t2 WHERE t1.type_id=t2.id ",
        ]

        params = {}
        if oid is not None:
            sql.append("AND t1.id LIKE :id")
            params["id"] = oid
        if objid is not None:
            sql.append("AND t1.objid LIKE :objid")
            params["objid"] = objid
        if objtype is not None:
            sql.append("AND t2.objtype LIKE :objtype AND t2.objdef LIKE :objdef")
            params["objtype"] = objtype.objtype
            params["objdef"] = objtype.objdef

        query = session.query(SysObject).from_statement(text(" ".join(sql))).params(params).all()

        if len(query) <= 0:
            self.logger.error("No objects found")
            raise ModelError("No objects found")

        for item in query:
            # remove permissions
            session.query(SysObjectPermission).filter_by(obj_id=item.id).delete()
            # perms = session.query(SysObjectPermission).filter_by(obj_id=item.id).all()
            # for perm in perms:
            #     session.delete(perm)

            # remove object
            session.delete(item)
        self.logger.debug("Remove objects: %s %s %s" % (oid, objid, objtype))
        return True

    #
    # System Object Permission manipulation methods
    #
    @query
    def get_permission(self, permission_id):
        """Get system object permisssion.

        :param permission_id: System Object Permission id [optional]
        :return: list of SysObjectPermissionue.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sql = [
            "SELECT t4.id as id, t1.id as oid, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef,",
            "t3.id as aid, t3.value as action FROM sysobject t1, sysobject_type t2, sysobject_action t3, ",
            "sysobject_permission t4 WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id ",
            "AND t4.id=:permission_id",
        ]

        params = {"permission_id": permission_id}

        res = session.query(SysObjectPermission).from_statement(text(" ".join(sql))).params(params).first()

        if res is None:
            self.logger.error("Permission %s was not found" % permission_id)
            raise ModelError("Permission %s was not found" % permission_id)

        self.logger.debug("Get permission: %s" % res)
        return res

    @query
    def get_permission_by_id(self, object_id=None, action_id=None):
        """Get system object permissions filtered by object or action.

        :param permission_id: System Object Permission id [optional]
        :param object_id: System Object id [optional]
        :param action_id: System Object Action id [optional]
        :return: list of SysObjectPermissionue.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sql = [
            "SELECT t4.id as id, t1.id as oid, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef, ",
            "t3.id as aid, t3.value as action FROM sysobject t1, sysobject_type t2, sysobject_action t3, ",
            "sysobject_permission t4 WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id",
        ]

        params = {}
        if object_id is not None:
            sql.append("AND t1.id=:object_id ")
            params["object_id"] = object_id
        if action_id is not None:
            sql.append("AND t3.id=:action_id ")
            params["action_id"] = action_id

        res = session.query(SysObjectPermission).from_statement(text(" ".join(sql))).params(params).all()

        if len(res) <= 0:
            self.logger.error("No permissions found")
            raise ModelError("No permissions found")

        self.logger.debug("Get object permissions: %s" % truncate(res))
        return res

    @query
    def get_permissions(
        self,
        oid=None,
        objid=None,
        objids=None,
        objid_filter=None,
        objtype=None,
        objtypes=None,
        objdef=None,
        objdef_filter=None,
        action=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
        """Get system object permisssion.

        :param oid: object id [optional]
        :param objid: Total or partial objid [optional]
        :param objids: list of objid [optional]
        :param objtype: Object type [optional]
        :param objtypes: Object type list [optional]
        :param objdef: Object definition [optional]
        :param objdef_filter: Part of object definition [optional]
        :param action: Object action [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of SysObjectPermission.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        tables = [
            "sysobject t1",
            "sysobject_type t2",
            "sysobject_action t3",
            "sysobject_permission t4",
        ]

        sqlcount = [
            "SELECT count(t4.id) FROM",
            ", ".join(tables),
            "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id",
        ]

        # sqlcount = [
        #     'SELECT count(t4.id) FROM sysobject_permission t4'
        # ]

        # add indexes
        if objid is None and objids is None and objdef is None and objdef_filter is None and oid is None:
            tables[0] += " FORCE INDEX(type_id)"
            if field == "id":
                tables[3] += " FORCE INDEX (PRIMARY)"

        sql = [
            "SELECT t4.id as id, t1.id as oid, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef,",
            "t3.id as aid, t3.value as action FROM",
            ", ".join(tables),
            "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id",
        ]

        params = {}
        if oid is not None:
            sql.append("AND t1.id LIKE :oid")
            sqlcount.append("AND t1.id LIKE :oid")
            params["oid"] = oid
        if objid is not None:
            sql.append("AND t1.objid LIKE :objid")
            sqlcount.append("AND t1.objid LIKE :objid")
            params["objid"] = objid
        if objids is not None:
            sql.append("AND t1.objid in :objids")
            sqlcount.append("AND t1.objid in :objids")
            params["objids"] = objids
        if objid_filter is not None:
            sql.append("AND t1.objid LIKE :objid")
            sqlcount.append("AND t1.objid LIKE :objid")
            params["objid"] = "%" + objid_filter + "%"
        if objtype is not None:
            sql.append("AND t2.objtype LIKE :objtype")
            sqlcount.append("AND t2.objtype LIKE :objtype")
            params["objtype"] = objtype
        if objtypes is not None:
            sql.append("AND t2.objtype IN :objtypes")
            sqlcount.append("AND t2.objtype IN :objtypes")
            params["objtypes"] = objtypes
        if objdef is not None:
            sql.append("AND t2.objdef LIKE :objdef")
            sqlcount.append("AND t2.objdef LIKE :objdef")
            params["objdef"] = objdef
        if objdef_filter is not None:
            sql.append("AND t2.objdef LIKE :objdef")
            sqlcount.append("AND t2.objdef LIKE :objdef")
            params["objdef"] = "%" + objdef_filter + "%"
        if action is not None:
            sql.append("AND t3.value LIKE :action")
            sqlcount.append("AND t3.value LIKE :action")
            params["action"] = action

        # get total rows
        total = session.execute(" ".join(sqlcount), params).fetchone()[0]
        self.logger.debug2(" ".join(sqlcount))

        offset = size * page
        sql.append("ORDER BY %s %s" % (field, order))
        if size != -1:
            sql.append("LIMIT %s OFFSET %s" % (size, offset))

        query = session.query(SysObjectPermission).from_statement(text(" ".join(sql))).params(params)
        self.print_query(self.get_permissions, query, inspect.getargvalues(inspect.currentframe()))

        res = query.all()

        if len(res) <= 0:
            filter = "objid=%s, objid_filter=%s, objtype =%s, objtypes=%s, objdef=%s, objdef_filter=%s, action=%s" % (
                objid,
                objid_filter,
                objtype,
                objtypes,
                objdef,
                objdef_filter,
                action,
            )
            self.logger.error("No permissions found for params: %s" % filter)
            raise ModelError("No permissions found for params: %s" % filter)

        self.logger.debug("Get object permissions: %s" % truncate(res))
        return res, total

    @query
    def get_deep_permissions(
        self,
        objids=[],
        objtype=None,
        objtypes=None,
        objdef=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
    ):
        """Get all the system object permisssions for an object with its childs .

        :param objids: list of objid [optional]
        :param objtype str: Object type [optional]
        :param objtypes str: Object type list [optional]
        :param objdef str: Object definition [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of SysObjectPermission.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sqlcount = [
            "SELECT count(t4.id)",
            "FROM sysobject t1, sysobject_type t2, sysobject_action t3, sysobject_permission t4",
            "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id",
        ]
        sql = [
            "SELECT t4.id as id, t1.id as oid, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef,",
            "t3.id as aid, t3.value as action",
            "FROM sysobject t1, sysobject_type t2, sysobject_action t3, sysobject_permission t4",
            "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id AND t1.type_id=t2.id",
        ]

        params = {}
        if objids is not None:
            sql.append("AND t1.objid in :objids")
            sqlcount.append("AND t1.objid in :objids")
            params["objids"] = objids
        if objtype is not None:
            sql.append("AND t2.objtype LIKE :objtype")
            sqlcount.append("AND t2.objtype LIKE :objtype")
            params["objtype"] = objtype
        if objtypes is not None:
            sql.append("AND t2.objtype IN :objtypes")
            sqlcount.append("AND t2.objtype IN :objtypes")
            params["objtypes"] = objtypes
        if objdef is not None:
            sql.append("AND t2.objdef LIKE :objdef")
            sqlcount.append("AND t2.objdef LIKE :objdef")
            params["objdef"] = objdef

        # get total rows
        total = session.execute(" ".join(sqlcount), params).fetchone()[0]

        offset = size * page
        sql.append("ORDER BY %s %s" % (field, order))
        sql.append("LIMIT %s OFFSET %s" % (size, offset))

        query = session.query(SysObjectPermission).from_statement(text(" ".join(sql))).params(params)
        res = query.all()
        self.logger.warn("stmp: %s" % query.statement.compile(dialect=mysql.dialect()))
        self.logger.warn("objids: %s" % objids)
        self.logger.warn("objtype: %s" % objtype)
        self.logger.warn("objtypes: %s" % objtypes)
        self.logger.warn("objdef: %s" % objdef)

        if len(res) <= 0:
            res = []
            total = 0

        self.logger.debug("Get object permissions: %s" % truncate(res))
        return res, total

    # #
    # # RoleTemplateTemplate manipulation methods
    # #
    # def get_role_templates(self, *args, **kvargs):
    #     """Get role_templates
    #
    #     :param tags: list of permission tags
    #     :param name: name like [optional]
    #     :param active: active [optional]
    #     :param creation_date: creation_date [optional]
    #     :param modification_date: modification_date [optional]
    #     :param expiry_date: expiry_date [optional]
    #     :param page: users list page to show [default=0]
    #     :param size: number of users to show in list per page [default=0]
    #     :param order: sort order [default=DESC]
    #     :param field: sort field [default=id]
    #     :return: list of :class:`RoleTemplate`
    #     :raises QueryError: raise :class:`QueryError`
    #     """
    #     filters = []
    #     res, total = self.get_paginated_entities(RoleTemplate, filters=filters, *args, **kvargs)
    #
    #     return res, total
    #
    # @query
    # def get_permission_role_templates(self, tags=None, perm=None, page=0, size=10, order='DESC', field='id',
    #                                   *args, **kvargs):
    #     """Get role_templates related to a permission.
    #
    #     :param perm: permission id
    #     :param page: role_templates list page to show [default=0]
    #     :param size: number of role_templates to show in list per page [default=0]
    #     :param order: sort order [default=DESC]
    #     :param field: sort field [default=id]
    #     :return: List of RoleTemplate instances
    #     :rtype: list of :class:`RoleTemplate`
    #     :raises QueryError: raise :class:`QueryError`
    #     """
    #     session = self.get_session()
    #     query = PaginatedQueryGenerator(RoleTemplate, session)
    #     query.add_filter('AND role_template_permission.permission_id=:perm_id')
    #     query.set_pagination(page=page, size=size, order=order, field=field)
    #     res = query.run(tags, permn_id=perm, *args, **kvargs)
    #     return res
    #
    # @transaction
    # def add_role_template(self, objid, name, desc, policies):
    #     """Add a role_template.
    #
    #     :param objid: role_template objid
    #     :param name: role_template name
    #     :param policies: list of policies {'objid_tmpl':.., 'type':.., 'action':..}
    #         Ex. [{'objid_tmpl':'%account_objid', 'type':'service:Org.Div.Account', 'action':'*'},..]
    #     :param desc: role_template desc
    #     :return: True if operation is successful, False otherwise
    #     :rtype: bool
    #     :raises TransactionError: raise :class:`TransactionError`
    #     """
    #     session = self.get_session()
    #
    #     rt_policies = []
    #     for policy in policies:
    #         # get object type
    #         objtype, objdef = policy.get('type').split(':')
    #         policy_type = session.query(SysObjectType).filter_by(objtype=objtype).filter_by(objdef=objdef).first()
    #         if policy_type is None:
    #             raise ModelError('Type %s not found' % policy.get('type'))
    #         # get action
    #         objtype, objdef = policy.get('type').split(':')
    #         policy_act = session.query(SysObjectAction).filter_by(objtype=objtype).filter_by(objdef=objdef).first()
    #         if policy_act is None:
    #             raise ModelError('Type %s not found' % policy.get('type'))
    #         # TODO: add control to objid
    #         rt_policies.append(SysPolicy(policy.get('objid_tmpl'), policy_type, policy_act))
    #
    #     record = RoleTemplate(objid, name, rt_policies, desc=desc, active=True)
    #     session.add(record)
    #
    #     self.logger.debug('Add role_template %s' % name)
    #     return record
    #
    # @transaction
    # def remove_role_template(self, *args, **kvargs):
    #     """Remove role_template.
    #
    #     :param int oid: entity id. [optional]
    #     :raises TransactionError: raise :class:`TransactionError`
    #     """
    #     # remove policies
    #
    #     res = self.remove_entity(RoleTemplate, *args, **kvargs)
    #     return res
    #
    # @transaction
    # def append_role_template_permissions(self, role_template, perms):
    #     """Append permission to role_template
    #
    #     :param role_template: RoleTemplate instance
    #     :param perms: list of permissions
    #     :return: True if operation is successful, False otherwise
    #     :rtype: bool
    #     :raises TransactionError: raise :class:`TransactionError`
    #     """
    #     session = self.get_session()
    #     append_perms = []
    #     for perm in perms:
    #         # append permission to role_template if it doesn't already exists
    #         if role_template not in perm.role_template:
    #             role_template.permission.append(perm)
    #             append_perms.append(perm.id)
    #         else:
    #             self.logger.warn('Permission %s already exists in role_template %s' % (
    #                 perm, role_template))
    #
    #     self.logger.debug('Append to role_template %s permissions: %s' % (role_template, perms))
    #     return append_perms
    #
    # @transaction
    # def remove_role_template_permission(self, role_template, perms):
    #     """Remove permission from role_template
    #
    #     :param role_template: RoleTemplate instance
    #     :param perms: list of permissions
    #     :return: True if operation is successful, False otherwise
    #     :rtype: bool
    #     :raises TransactionError: raise :class:`TransactionError`
    #     """
    #     session = self.get_session()
    #     remove_perms = []
    #     for perm in perms:
    #         # remove permission from role_template
    #         # if len(perm.role_template.all()) > 0:
    #         role_template.permission.remove(perm)
    #         remove_perms.append(perm.id)
    #
    #     self.logger.debug('Remove from role_template %s permissions: %s' % (role_template, perms))
    #     return remove_perms

    #
    # Role manipulation methods
    #
    def get_roles(self, *args, **kvargs):
        """Get roles

        :param tags: list of permission tags
        :param name: name [optional]
        :param alias: alias [optional]
        :param names: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if kvargs.get("names", None) is not None:
            filters.append("AND t3.name like :names")
        if kvargs.get("alias", None) is not None:
            filters.append("AND t3.alias like :alias")

        filters.append("AND t3.active=1")
        filters.append("AND (t3.expiry_date IS NULL OR t3.expiry_date > NOW()) ")

        res, total = self.get_paginated_entities(Role, filters=filters, *args, **kvargs)

        return res, total

    @query
    def get_role_permissions_by_role_id(self, role_id: int):
        """Get role permissions by role id."""
        if type(role_id) != int:
            raise Exception("expected integer")
        session = self.get_session()
        # perm = (0-pid,    1-oid,    2-type, 3-definition, 4-objid, 5-aid, 6-action)
        sql = """SELECT
    op.id as id,
    o.id as oid,
    ot.objtype as objtype,
    ot.objdef as objdef,
    o.objid as objid,
    a.id as aid,
    a.value as action
FROM
    sysobject o
    inner join sysobject_type ot on o.type_id= ot.id
    inner join sysobject_permission op on op.obj_id=o.id
    inner join sysobject_action a on op.action_id=a.id
    inner join role_permission rp on rp.permission_id =op.id
    inner join role r on rp.role_id = r.id
WHERE
    r.id  = :role_id """

        # get total rows
        query = session.execute(sql, {"role_id": role_id})
        self.logger.debug("Get role permission by role_id: %s %s" % (role_id, truncate(query)))
        result = query.all()
        # convert result in list of list  of  values
        if len(result) <= 0:
            res = []
        else:
            res = [[x for x in row] for row in result]

        return res

    @query
    def get_role_permissions(self, names=None, page=0, size=10, order="DESC", field="id", *args, **kvargs):
        """Get role permissions.

        :param names: list of roles name
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of object with the following fields: (id, oid, value, type, aid, action)
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sqlcount = [
            "SELECT count(distinct t4.id) FROM sysobject t1, sysobject_type t2, sysobject_action t3, ",
            "sysobject_permission t4, role t5, role_permission t6",
            "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and t1.type_id=t2.id and t6.role_id = t5.id and",
            "t6.permission_id=t4.id and t5.name IN :role_names",
        ]
        sql = [
            "SELECT t4.id as id, t1.id as oid, t1.objid as objid,  t2.objtype as objtype, t2.objdef as objdef, ",
            "t3.id as aid, t3.value as action",
            "FROM sysobject t1, sysobject_type t2, sysobject_action t3, sysobject_permission t4,",
            "role t5, role_permission t6",
            "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and t1.type_id=t2.id and t6.role_id = t5.id and",
            "t6.permission_id=t4.id and t5.name IN :role_names GROUP BY t4.id",
        ]

        # get total rows
        query = session.execute(" ".join(sqlcount), {"role_names": names})
        total = query.fetchone()[0]

        offset = size * page
        sql.append("ORDER BY %s %s" % (field, order))
        sql.append("LIMIT %s OFFSET %s" % (size, offset))

        query = session.query(SysObjectPermission).from_statement(text(" ".join(sql))).params(role_names=names)

        self.print_query(self.get_permissions, query, inspect.getargvalues(inspect.currentframe()))

        query = query.all()

        self.logger.debug("Get role %s permissions: %s" % (names, truncate(query)))
        return query, total

    @query
    def get_permission_roles(
        self,
        tags=None,
        perm=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get roles related to a permission.

        :param perm: permission id
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        query = PaginatedQueryGenerator(Role, session)
        query.add_table("role_permission", "t4")
        query.add_filter("AND role_permission.permission_id=:perm_id")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, permn_id=perm, *args, **kvargs)
        return res

    @query
    def get_permissions_roles(
        self,
        tags=None,
        perms=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get roles related to some permissions.

        :param perms: permission id list
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        perms = sorted(perms)
        perms_string = ",".join(perms)

        custom_select = (
            "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.permission_id ORDER BY t2.permission_id) as perms "
            "FROM role t1, role_permission t2 "
            "WHERE t2.role_id=t1.id and (t2.permission_id in :perms) GROUP BY t1.id)"
        )

        query = PaginatedQueryGenerator(Role, session, custom_select=custom_select)
        query.add_filter("AND t3.perms=:perms_string")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, perms=perms, perms_string=perms_string, *args, **kvargs)
        return res

    @query
    def get_permissions_users(
        self,
        tags=None,
        perms=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get users related to some permissions.

        :param perms: permission id list
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        perms = sorted(perms)
        perms_string = ",".join(perms)

        custom_select = (
            "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.permission_id ORDER BY t2.permission_id) as perms "
            "FROM user t1, role_permission t2, roles_users t3 "
            "WHERE t2.role_id=t3.role_id AND t3.user_id=t1.id and (t2.permission_id in :perms) "
            "GROUP BY t1.id)"
        )

        query = PaginatedQueryGenerator(User, session, custom_select=custom_select)
        query.add_filter("AND t3.perms=:perms_string")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, perms=perms, perms_string=perms_string, *args, **kvargs)
        return res

    @query
    def get_permissions_groups(
        self,
        tags=None,
        perms=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get groups related to some permissions.

        :param perms: permission id list
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        perms = sorted(perms)
        perms_string = ",".join(perms)

        custom_select = (
            "(SELECT t1.*, GROUP_CONCAT(DISTINCT t2.permission_id ORDER BY t2.permission_id) as perms "
            "FROM `group` t1, role_permission t2, roles_groups t3 "
            "WHERE t2.role_id=t3.role_id AND t3.group_id=t1.id and (t2.permission_id in :perms) "
            "GROUP BY t1.id)"
        )

        query = PaginatedQueryGenerator(Group, session, custom_select=custom_select)
        query.add_filter("AND t3.perms=:perms_string")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, perms=perms, perms_string=perms_string, *args, **kvargs)
        return res

    def add_role(self, objid, name, desc, alias=""):
        """Add a role.

        :param objid: role objid
        :param name: role name
        :param alias: role alias [optional]
        :param desc: role desc
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(Role, objid, name, [], desc=desc, active=True, alias=alias)
        return res

    def update_role(self, *args, **kvargs):
        """Update role. Extend :function:`update_entity`

        :param int oid: entity id. [optional]
        :param str name: entity name. [optional]
        :param desc: role desc. [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Role, *args, **kvargs)
        return res

    def remove_role(self, *args, **kvargs):
        """Remove role.

        :param int oid: entity id. [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Role, *args, **kvargs)
        return res

    @transaction
    def append_role_permissions(self, role, perms):
        """Append permission to role

        :param role: Role instance
        :param perms: list of permissions
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        append_perms = []
        for perm in perms:
            roles = session.query(role_permission).filter_by(role_id=role.id).filter_by(permission_id=perm.id).all()
            # append permission to role only if it does not already exist
            if len(roles) == 0:
                role.permission.append(perm)
                append_perms.append(perm.id)
            else:
                self.logger.warn("Permission %s already exists in role %s" % (perm, role))

        self.logger.debug("Append permissions %s to role %s" % (append_perms, role))
        return append_perms

    @transaction
    def remove_role_permission(self, role, perms):
        """Remove permission from role

        :param role: Role instance
        :param perms: list of permissions
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        remove_perms = []
        for perm in perms:
            # remove permission from role
            if perm in role.permission:
                role.permission.remove(perm)
                remove_perms.append(perm.id)

        self.logger.debug("Remove from role %s permissions: %s" % (role, perms))
        return remove_perms

    #
    # Group manipulation methods
    #
    def count_group(self):
        """Count group."""
        return self.count_entities(User)

    def get_groups(self, *args, **kvargs):
        """Get groups

        :param tags: list of permission tags
        :param name: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiry_date [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if "expiry_date" in kvargs and kvargs.get("expiry_date") is not None:
            filters.append("AND expiry_date>=:expiry_date")
        res, total = self.get_paginated_entities(Group, filters=filters, *args, **kvargs)

        return res, total

    @query
    def get_group_roles(
        self,
        tags=None,
        group_id=None,
        group_id_list=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get roles of a user with expiry date of the association

        :param tags: list of permission tags
        :param group_id: Orm Group instance
        :param group_id_list: list id group instance
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        query = PaginatedQueryGenerator(Role, session, other_entities=[RoleGroup.expiry_date])
        query.add_table("roles_groups", "t4")
        query.add_select_field("t4.expiry_date as roles_users_expiry_date")
        query.add_filter("AND t4.role_id=t3.id")
        if group_id is not None:
            query.add_filter("AND t4.group_id=:group_id")
        if kvargs.get("group_id_list") is not None:
            group_id_list = tuple(kvargs.pop("group_id_list"))
            query.add_filter("AND t4.group_id IN :group_id_list")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, group_id=group_id, group_id_list=group_id_list, *args, **kvargs)
        return res

    def get_role_groups(self, *args, **kvargs):
        """Get groups of a role.

        :param tags: list of permission tags
        :param role_id: role id
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("roles_groups", "t4")]
        filters = ["AND t3.id=t4.group_id", "AND t4.role_id=:role_id"]
        res, total = self.get_paginated_entities(Group, filters=filters, tables=tables, *args, **kvargs)
        return res, total

    def get_group_users(self, *args, **kvargs):
        """Get users of a group.

        :param group_id: Orm Role instance
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("groups_users", "t4")]
        filters = ["AND t3.id=t4.user_id", "AND t4.group_id=:group_id"]
        res, total = self.get_paginated_entities(User, filters=filters, tables=tables, *args, **kvargs)
        return res, total

    def get_user_groups(self, *args, **kvargs):
        """Get groups of a user.

        :param user_id: user id
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("groups_users", "t4")]
        filters = ["AND t3.id=t4.group_id", "AND t4.user_id=:user_id"]
        res, total = self.get_paginated_entities(Group, filters=filters, tables=tables, *args, **kvargs)
        return res, total

    @query
    def get_group_permissions(self, group, page=0, size=10, order="DESC", field="id", *args, **kvargs):
        """Get group permissions.

        :param group: Orm Group instance
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of object with the following fields:
                 (id, oid, value, type, aid, action)
        :rtype: list of tuple):
        """
        session = self.get_session()

        if group is None:
            raise ModelError("Group is not correct or does not exist")

        # get group roles
        roles = []
        group_roles = session.query(Role).join(RoleGroup).filter(RoleGroup.group_id == group.id).all()
        for role in group_roles:
            roles.append(role.name)

        if len(roles) == 0:
            self.logger.warn("Group %s has no roles associated" % group.id)
            total = 0
            perms = []
        else:
            perms, total = self.get_role_permissions(names=roles, page=page, size=size, order=order, field=field)

        self.logger.debug("Get group %s perms : %s" % (group, truncate(perms)))
        return perms, total

    @transaction
    def add_group(self, objid, name, desc="", members=[], roles=[], active=True, expiry_date=None):
        """Add group.

        :param objid: authorization id
        :param name: name of the user
        :param active: set if user is active [default=True]
        :param desc: user desc [default='']
        :param expiry_date: user expiry date [default=365 days]. Set using a datetime object
        :param members: List with User instances. [Optional]
        :param roles: List with Role instances. [Optional]
        :return: :class:`Group`
        :raises TransactionError: raise :class:`TransactionError`
        """
        group = self.add_entity(
            Group,
            objid,
            name,
            member=members,
            role=roles,
            desc=desc,
            active=active,
            expiry_date=expiry_date,
        )

        # create group role
        objid = id_gen()
        name = "Group%sRole" % group.id
        desc = "Group %s private role" % name
        expiry_date = datetime(2099, 12, 31)
        role = self.add_role(objid, name, desc)

        # append role to user
        self.append_group_role(group, role, expiry_date=expiry_date)

        return group

    def patch_group(self, group):
        """Patch group to the last configuration.

        :param group: group object
        :raises TransactionError: raise :class:`TransactionError`
        """
        name = "Group%sRole" % group.id

        try:
            self.get_entity(Role, name)
        except Exception:
            # create group role
            objid = id_gen()
            desc = "Group %s private role" % name
            expiry_date = datetime(2099, 12, 31)
            role = self.add_role(objid, name, desc)

            # append role to user
            self.append_group_role(group, role, expiry_date=expiry_date)

        self.logger.debug("Patch group %s" % group.uuid)
        return True

    def update_group(self, *args, **kvargs):
        """Update group. Extend :function:`update_entity`

        :param int oid: entity id. [optional]
        :param name: name of the group
        :param active: set if group is active [optional]
        :param desc: group desc [optional]
        :param expiry_date: group expiry date. Set using a datetime object [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Group, *args, **kvargs)
        return res

    @transaction
    def remove_group(self, *args, **kvargs):
        """Remove group.

        :param int oid: entity id. [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get group roles
        rus = session.query(RoleGroup).filter(RoleGroup.group_id == kvargs["oid"]).all()

        # remove roles from group if it exists
        for ru in rus:
            session.delete(ru)
        session.flush()

        # remove internal role
        name = "Group%sRole" % kvargs["oid"]
        try:
            role = self.get_entity(Role, name)
            self.remove_role(oid=role.id)
        except QueryError:
            pass

        # remove user
        res = self.remove_entity(Group, oid=kvargs["oid"])

        return res

    @transaction
    def append_group_role(self, group, role, expiry_date=None):
        """Append a role to an group

        :param group: group instance
        :param role: Role instance
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # append role to group if it doesn't already appended
        ru = session.query(RoleGroup).filter_by(group_id=group.id).filter_by(role_id=role.id)
        if ru.first() is not None:
            self.logger.warn("Role %s already exists in group %s" % (role, group))
            return False
        else:
            if expiry_date is None:
                expiry_date = datetime.today() + timedelta(days=365)
            ru = RoleGroup(group.id, role.id, expiry_date)
            session.add(ru)
            session.flush()
            self.logger.debug("Append group %s role: %s" % (group, role))
            return role.id

    @transaction
    def remove_group_role(self, group, role):
        """Remove role from group

        :param group: group instance
        :param role: Role instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # remove role from group if it exists
        ru = session.query(RoleGroup).filter_by(group_id=group.id).filter_by(role_id=role.id).first()
        if ru is not None:
            session.delete(ru)
            self.logger.debug("Remove group %s role: %s" % (group, role))
            return role.id
        else:
            self.logger.warn("Role %s doesn" "t exists in group %s" % (role, group))
            return False

    @transaction
    def append_group_user(self, group, user):
        """Append a user to an group

        :param group: Group instance
        :param user: User instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # append role to user if it doesn't already appended
        if user.group.filter_by(name=group.name).first():
            self.logger.warn("User %s already exists in group %s" % (user, group))
            return False
        else:
            group.member.append(user)
            self.logger.debug("Append user %s role : %s" % (group, user))
            return user.id

    @transaction
    def remove_group_user(self, group, user):
        """Remove user from group

        :param group: Group instance
        :param user: User instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # remove role form user if it exists
        if user.group.filter_by(name=group.name).first():
            group.member.remove(user)
            self.logger.debug("Remove group %s user : %s" % (group, user))
            return user.id
        else:
            self.logger.error("User %s doesn" "t exist in group %s" % (user, group))
            return False

    #
    # User manipulation methods
    #
    def count_user(self):
        """Count user."""
        return self.count_entities(User)

    def get_user(self, oid):
        """Method used by authentication manager"""
        return self.get_entity(User, oid)

    def get_users(self, *args, **kvargs):
        """Get users

        :param tags: list of permission tags
        :param name: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiry_date [optional]
        :param email: email [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        email = kvargs.get("email", None)
        taxcode = kvargs.get("taxcode", None)
        ldap = kvargs.get("ldap", None)
        expiry_date = kvargs.get("expiry_date", None)

        if email is not None:
            filters.append("AND t3.email=:email")

        if taxcode is not None:
            filters.append("AND t3.taxcode=:taxcode")

        if ldap is not None:
            filters.append("AND t3.ldap=:ldap")

        if expiry_date is not None:
            filters.append("AND expiry_date>=:expiry_date")

        res, total = self.get_paginated_entities(User, filters=filters, *args, **kvargs)

        return res, total

    @query
    def get_user_roles(
        self,
        tags=None,
        user_id=None,
        page=0,
        size=10,
        order="DESC",
        field="id",
        *args,
        **kvargs,
    ):
        """Get roles of a user with expiry date of the association

        :param tags: list of permission tags
        :param user_id: Orm User instance
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        query = PaginatedQueryGenerator(Role, session, other_entities=[RoleUser.expiry_date])
        query.add_table("roles_users", "t4")
        query.add_select_field("t4.expiry_date as roles_users_expiry_date")
        query.add_filter("AND t4.role_id=t3.id")
        query.add_filter("AND t4.user_id=:user_id")
        query.add_filter("AND t3.active=1")
        query.add_filter("AND (t3.expiry_date IS NULL OR t3.expiry_date > NOW()) ")
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, user_id=user_id, *args, **kvargs)
        return res

    def get_role_users(self, *args, **kvargs):
        """Get users of a role.

        :param tags: list of permission tags
        :param role_id: role id
        :param email: user email
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`
        """
        tables = [("roles_users", "t4")]
        filters = ["AND t3.id=t4.user_id", "AND t4.role_id=:role_id"]
        email = kvargs.get("email", None)
        if email is not None:
            filters.append("AND t3.email=:email")
        res, total = self.get_paginated_entities(User, filters=filters, tables=tables, *args, **kvargs)
        return res, total

    @query
    def get_user_permissions(self, user, page=0, size=10, order="DESC", field="id", *args, **kvargs):
        """Get user permissions.

        :param user: Orm User instance
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        if user is None:
            raise ModelError("User is not correct or does not exist")

        # get user roles
        roles = []
        user_roles = session.query(Role).join(RoleUser).filter(RoleUser.user_id == user.id).all()
        for role in user_roles:
            roles.append(role.name)

        # get user roles from user groups
        for group in user.group:
            group_roles = session.query(Role).join(RoleGroup).filter(RoleGroup.group_id == group.id).all()
            for role in group_roles:
                roles.append(role.name)

        if len(roles) == 0:
            self.logger.warn("User %s has no roles associated" % user.id)
            total = 0
            perms = []
        else:
            perms, total = self.get_role_permissions(names=roles, page=page, size=size, order=order, field=field)
        self.logger.debug("Get user %s perms: %s" % (user.name, truncate(perms)))
        return perms, total

    @query
    def get_login_permissions(self, user: User, *args, **kvargs):
        """Get login user permissions.

        :param user: Orm User instance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        if user is None:
            raise ModelError("User is not correct or does not exist")

        # get all user roles
        roles: List[Role] = []
        user_roles = session.query(Role).join(RoleUser).filter(RoleUser.user_id == user.id).all()
        for role in user_roles:
            roles.append(role.name)
        for group in user.group:
            group_roles = session.query(Role).join(RoleGroup).filter(RoleGroup.group_id == group.id).all()
            for role in group_roles:
                roles.append(role.name)

        perms = []

        self.logger.debug("Get user %s perms - roles: %s" % (user, roles))
        if len(roles) > 0:
            # get user permissions from user roles
            # sql = [
            #     "SELECT t4.id as id, t1.id as oid, t2.objtype as objtype, t2.objdef as objdef, t1.objid as objid, ",
            #     "t3.id as aid, t3.value as action",
            #     "FROM sysobject t1, sysobject_type t2, sysobject_action t3, sysobject_permission t4,",
            #     "role t5, role_permission t6",
            #     "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and t1.type_id=t2.id and t6.role_id = t5.id and",
            #     "t6.permission_id=t4.id and t5.name IN :role_name",
            # ]
            sqlstmnt = """SELECT
                pe.id as id,
                so.id as oid,
                ty.objtype as objtype,
                ty.objdef as objdef,
                so.objid as objid,
                ac.id as aid,
                ac.value as action
            FROM
                sysobject_permission pe
                inner join sysobject so on pe.obj_id=so.id
                inner join sysobject_type ty on so.type_id=ty.id
                inner join sysobject_action ac on pe.action_id=ac.id
                inner join role_permission rp on rp.permission_id=pe.id
                inner join `role` ro on rp.role_id = ro.id
            WHERE
                ro.name IN :role_name"""
            # columns = [text('id'), text('oid'), text('objtype'), text('objdef'), text('objid'), text('aid'),
            #           text('action')]
            columns = [
                Column("id"),
                Column("oid"),
                Column("objtype"),
                Column("objdef"),
                Column("objid"),
                Column("aid"),
                Column("action"),
            ]
            query = (
                session.query(*columns)
                # .from_statement(text(" ".join(sql)))
                .from_statement(text(sqlstmnt)).params(role_name=roles)
            )
            self.print_query(
                self.get_login_permissions,
                query,
                inspect.getargvalues(inspect.currentframe()),
            )
            perms = query.all()
            res = [[p[0], p[1], p[2], p[3], p[4], p[5], p[6]] for p in perms]
        self.logger.debug("Get user %s perms: %s" % (user, truncate(res)))
        return res

    @query
    def get_login_roles(self, user=None):
        """Get roles of a user during login.

        :param user: Orm User instance
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        roles = session.query(Role).join(RoleUser).filter(RoleUser.user_id == user.id).all()

        self.logger.debug("Get user %s roles: %s" % (user, truncate(roles)))
        return roles

    @query
    def verify_user_password(self, user, password):
        """Verify user password.

        :param user: Orm User instance
        :param password: Password to verify
        :return: True if password is correct, False otherwise.
        :rtype: bool
        :raises QueryError: raise :class:`QueryError`
        """
        # verifying the password
        res = user._check_password(password)
        self.logger.debug("Verify user %s password: %s" % (user, res))
        return res

    @query
    def verify_user_secret(self, user, secret):
        """Verify user secret.

        :param user: Orm User instance
        :param secret: Secret to verify
        :return: True if secret is correct, False otherwise.
        :rtype: bool
        :raises QueryError: raise :class:`QueryError`
        """
        # verifying the secret
        res = user._check_secret(secret)
        self.logger.debug("Verify user %s secret: %s" % (user, res))
        return res

    @transaction
    def add_user(
        self,
        objid,
        name: str,
        active=True,
        password=None,
        desc="",
        expiry_date=None,
        is_generic=False,
        is_admin=False,
        email=None,
        taxcode=None,
        ldap=None,
    ):
        """Add user.

        :param objid: authorization id
        :param name: name of the user
        :param active: set if user is active [default=True]
        :param password: user password [optional]
        :param desc: user desc [default='']
        :param expiry_date: user expiry date [default=365 days]. Set using a
                datetime object
        :param is_generic: if True create a private role for the user [default=False]
        :param is_admin: if True assign super admin role [default=False]
        :param email: email [optional]
        :return: :class:`User`
        :raises TransactionError: raise :class:`TransactionError`
        """
        if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", name):
            raise Exception("Name is not correct. Name syntax is <name>@<domain>")

        i_at = name.index("@")
        domain = name[i_at:]
        domains = ["@local", "@portal", "@domnt.csi.it", "@fornitori.nivola"]
        if domain not in domains:
            raise Exception("Name is not correct. Domain not valid")

        if email is not None:
            from beecell.sendmail import check_email

            if not check_email(email):
                raise Exception("Email is not valid")
        else:
            # ???
            email = name

        if taxcode is not None:
            from beecell.checks import check_tax_code

            if not check_tax_code(taxcode):
                raise Exception("Taxcode is not correct")

        if ldap is not None:
            if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("Ldap is not correct. Ldap syntax is <name>@<domain>")

        user = self.add_entity(
            User,
            objid,
            name,
            active=active,
            password=password,
            desc=desc,
            expiry_date=expiry_date,
            email=email,
            taxcode=taxcode,
            ldap=ldap,
        )

        # create user role
        objid = id_gen()
        name = "User%sRole" % user.id
        desc = "User %s private role" % name
        expiry_date = datetime(2099, 12, 31)
        role_user = self.add_role(objid, name, desc)

        if is_generic is True:
            # objid = id_gen()
            # name = 'User%sRole' % user.id
            # desc = 'User %s private role' % name
            # role = self.add_role(objid, name, desc)

            # append role to user
            self.append_user_role(user, role_user, expiry_date=expiry_date)
            role = self.get_entity(Role, "Guest")
            self.append_user_role(user, role, expiry_date=expiry_date)
            self.logger.debug("Create base user")
        elif is_admin is True:
            # append role to user
            role = self.get_entity(Role, "ApiSuperadmin")
            self.append_user_role(user, role)
            self.append_user_role(user, role_user, expiry_date=expiry_date)
            self.logger.debug("Create system user")

        return user

    def update_user(self, *args, **kvargs):
        """Update user. Extend :function:`update_entity`

        :param int oid: entity id. [optional]
        :param name: name of the user
        :param active: set if user is active [optional]
        :param password: user password [optional]
        :param desc: user desc [optional]
        :param expiry_date: user expiry date. Set using a datetime object [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        email = kvargs.get("email", None)
        taxcode = kvargs.get("taxcode", None)
        ldap = kvargs.get("ldap", None)

        if email is not None:
            from beecell.sendmail import check_email

            if not check_email(email):
                raise Exception("Email is not valid")

        if taxcode is not None:
            from beecell.checks import check_tax_code

            if not check_tax_code(taxcode):
                raise Exception("Taxcode is not correct")

        if ldap is not None:
            if not match("[a-zA-z0-9\.]+@[a-zA-z0-9\.]+", ldap):
                raise Exception("Ldap is not correct. Ldap syntax is <name>@<domain>")

        # generate new salt, and hash a password
        password = kvargs.get("password", None)
        if password is not None:
            password = password.encode("utf-8")
            kvargs["password"] = bcrypt.hashpw(password, bcrypt.gensalt(14))

        res = self.update_entity(User, *args, **kvargs)
        return res

    @transaction
    def remove_user(self, *args, **kvargs):
        """Remove user.

        :param int oid: entity id. [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get user roles
        rus = session.query(RoleUser).filter(RoleUser.user_id == kvargs["oid"]).all()

        # remove roles from user if it exists
        for ru in rus:
            session.delete(ru)
        session.flush()

        # remove internal role
        name = "User%sRole" % kvargs["oid"]
        try:
            role = self.get_entity(Role, name)
            if role is not None:
                self.remove_role(oid=role.id)
        except QueryError:
            pass

        # remove user
        res = self.remove_entity(User, oid=kvargs["oid"])

        return res

    @transaction
    def expire_users(self, expiry_date):
        """Disable a user that is expired.

        :param expiry_date: expiry date used to disable user
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        user = session.query(User).filter(User.expiry_date <= expiry_date)
        user.update({"active": False})
        res = [u.id for u in user.all()]
        self.logger.debug("Disable exipred users: %s" % res)
        return res

    @transaction
    def set_user_secret(self, oid):
        """Set user last login date.

        :param oid: user id, name or uuid
        :param last_login: last_login date
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        user = self.get_user(oid)
        secret = random_password(length=100)
        res = self.update_entity(User, oid=user.id, secret=secret)
        self.logger.debug("Update user %s secret" % oid)
        return res

    @transaction
    def set_user_last_login(self, oid):
        """Set user last login date.

        :param oid: user id, name or uuid
        :param last_login: last_login date
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        date = datetime.today()
        user = self.get_user(oid)
        res = self.update_entity(User, oid=user.id, last_login=date)
        self.logger.debug("Update user %s last login date: %s" % (oid, date))
        return res

    @transaction
    def append_user_role(self, user, role, expiry_date=None):
        """Append a role to an user

        :param user: User instance
        :param role: Role instance
        :param expiry_date: role association expiry date [default=365 days]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # append role to user if it doesn't already appended
        ru = session.query(RoleUser).filter_by(user_id=user.id).filter_by(role_id=role.id)
        if ru.first() is not None:
            self.logger.warn("Role %s already exists in user %s" % (role, user))
            return False
        else:
            if expiry_date is None:
                expiry_date = datetime.today() + timedelta(days=365)
            ru = RoleUser(user.id, role.id, expiry_date)
            session.add(ru)
            session.flush()
            self.logger.debug("Append user %s role: %s" % (user, role))
            return role.id

    @transaction
    def remove_user_role(self, user, role):
        """Remove role from user

        :param user: User instance
        :param role: Role instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # remove role from user if it exists
        ru = session.query(RoleUser).filter_by(user_id=user.id).filter_by(role_id=role.id).first()
        if ru is not None:
            session.delete(ru)
            self.logger.debug("Remove user %s role: %s" % (user, role))
            return role.id
        else:
            self.logger.warn("Role %s doesn't exists in user %s" % (role, user))
            return False

    @transaction
    def remove_expired_user_role(self, expiry_date):
        """Remove roles from users where association is expired

        :param user: User instance
        :param role: Role instance
        :param expiry_date: role association expiry date. Set using a datetime object
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # remove role from user if it exists
        rus = session.query(RoleUser).filter(RoleUser.expiry_date <= expiry_date).all()
        for ru in rus:
            session.delete(ru)
        res = [(u.role_id, u.user_id) for u in rus]
        self.logger.debug("Remove expired roles from users: %s" % (res))
        return res

    @transaction
    def set_user_attribute(self, user, name, value=None, desc=None, new_name=None):
        """Append an attribute to a user

        :param user: User instance
        :param name: attribute name
        :param value: attribute value
        :param desc: attribute desc
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        attrib = session.query(UserAttribute).filter_by(user_id=user.id).filter_by(name=name)
        item = attrib.first()
        if item is not None:
            data = {}
            if new_name is not None:
                data["name"] = new_name
            if value is not None:
                data["value"] = value
            if desc is not None:
                data["desc"] = desc
            attrib.update(data)
            self.logger.debug("Update user %s attribute: %s" % (user.name, item))
            attrib = item
        else:
            attrib = UserAttribute(user.id, name, value, desc)
            session.add(attrib)
            session.flush()
            self.logger.debug("Append user %s attribute: %s" % (user.name, attrib))
        return attrib

    @transaction
    def remove_user_attribute(self, user, name):
        """Remove an attribute from a user

        :param user: User instance
        :param name: attribute name
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # remove attribute from user if it exists
        attrib = session.query(UserAttribute).filter_by(user_id=user.id).filter_by(name=name).first()
        if attrib is not None:
            session.delete(attrib)
            self.logger.debug("Remove user %s attribute: %s" % (user.name, attrib))
            return True
        else:
            self.logger.error("Attribute %s doesn" "t exists for user %s" % (name, user.name))
            raise ModelError("Attribute %s doesn" "t exists for user %s" % (name, user.name))
