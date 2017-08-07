'''
Created on Jan 25, 2014

@author: darkbk
'''
import logging
import pandas as pd
import datetime
#from passlib.hash import sha256_crypt
import bcrypt
from beecell.auth import AuthDbManagerError, AbstractAuthDbManager
from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.sql import text
from beecell.perf import watch
from beecell.simple import truncate
from beecell.db import ModelError
from uuid import uuid4
from beehive.common.data import operation, query, netsted_transaction

#Base = declarative_base()

from beehive.common.model import Base, AbstractDbManager, ApiObject

logger = logging.getLogger(__name__)

# Many-to-Many Relationship among users and system roles
#role_user = Table('roles_users', Base.metadata,
#    Column('user_id', Integer(), ForeignKey('user.id')),
#    Column('role_id', Integer(), ForeignKey('role.id')))

# Many-to-Many Relationship among groups and system roles
role_group = Table('roles_groups', Base.metadata,
    Column('group_id', Integer(), ForeignKey('group.id')),
    Column('role_id', Integer(), ForeignKey('role.id')))

# Many-to-Many Relationship among groups and users
group_user = Table('groups_users', Base.metadata,
    Column('group_id', Integer, ForeignKey('group.id')),
    Column('user_id', Integer, ForeignKey('user.id')))

# Many-to-Many Relationship among system roles and objects permissions
role_permission = Table('role_permission', Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id')),
    Column('permission_id', Integer, ForeignKey('sysobject_permission.id'))
)

# Many-to-Many Relationship among system role_templates and policies
role_template_policy = Table('role_template_policy', Base.metadata,
    Column('role_template_id', Integer, ForeignKey('role_template.id')),
    Column('policy_id', Integer, ForeignKey('syspolicy.id'))
)

class RoleUser(Base):
    __tablename__ = u'roles_users'
    user_id = Column(Integer, ForeignKey(u'user.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey(u'role.id'), primary_key=True)
    expiry_date = Column(DateTime())
    user = relationship(u'User', back_populates=u'role')
    role = relationship(u'Role', back_populates=u'user')
    
    def __init__(self, user_id, role_id, expiry_date=None):
        """Create new user
        
        :param user_id: user id
        :param role_id: role id
        :param expiry_date: relation expiry date [default=365 days]. Set using a 
                datetime object
        """
        self.user_id = user_id
        self.role_id = role_id
        if expiry_date is None:
            expiry_date = datetime.datetime.today()+datetime.timedelta(days=365)
        self.expiry_date = expiry_date
    
    def __repr__(self):
        return u"<RoleUser user='%s' role='%s' expiry='%s'>" % (self.user_id,
                self.role_id, self.expiry_date)    

# Systems role templates
class RoleTemplate(Base, ApiObject):
    __tablename__ = u'role_template'

    policy = relationship(u'SysPolicy', secondary=role_template_policy,
                          backref=backref(u'role_template', lazy=u'dynamic'))

    def __init__(self, objid, name, policy, desc=u'', active=True):
        ApiObject.__init__(self, objid, name, desc, active)
        
        self.policy = policy 

# Systems roles
class Role(Base, ApiObject):
    __tablename__ = u'role'

    permission = relationship(u'SysObjectPermission', secondary=role_permission,
                              backref=backref(u'role', lazy=u'dynamic'))
    user = relationship(u'RoleUser', back_populates=u'role')
    template = Column(Integer())

    def __init__(self, objid, name, permission, desc=u'', active=True):
        ApiObject.__init__(self, objid, name, desc, active)
        
        self.permission = permission
    
    #def __repr__(self):
    #    return u"<Role id='%s' name='%s' desc='%s')>" % (
    #                self.id, self.name, self.desc)

# Systems roles
class UserAttribute(Base):
    __tablename__ = u'user_attribute'
    __table_args__ = {u'mysql_engine':u'InnoDB'}
        
    id = Column(Integer(), primary_key=True)    
    name = Column(String(30))
    value = Column(String(100))    
    desc = Column(String(255))
    user_id = Column(Integer(), ForeignKey(u'user.id'))

    def __init__(self, user, name, value, desc=u''):
        """Create a user attribute
        :param user: user id
        :param name: attribute name
        :param value: attribute value
        :param desc: attribute desc
        """
        self.user_id = user
        self.name = name
        self.value = value
        self.desc = desc
    
    def __repr__(self):
        return "<UserAttribute id=%s user=%s name=%s value=%s>" % (
                    self.id, self.user_id, self.name, self.value)

class User(Base, ApiObject):
    """User
    
    :param type: can be DBUSER, LDAPUSER 
    """
    __tablename__ = u'user'

    password = Column(String(150))
    role = relationship(u'RoleUser', back_populates=u'user')
    attrib = relationship(u'UserAttribute')

    def __init__(self, objid, name, active=True, password=None, 
                 desc=u'', expiry_date=None):
        """Create new user
        
        :param objid: authorization id
        :param username: name of the user
        :param active: set if user is active [default=True]
        :param password: user password [optional]
        :param desc: user desc [default='']
        :param expiry_date: user expiry date [default=365 days]. Set using a 
                datetime object
        """
        ApiObject.__init__(self, objid, name, desc, active)
        
        self.role = []
        
        if expiry_date is None:
            expiry_date = datetime.datetime.today()+datetime.timedelta(days=365)
        self.expiry_date = expiry_date
        
        if password is not None:
            # generate new salt, and hash a password 
            #self.password = sha256_crypt.encrypt(password)
            self.password = bcrypt.hashpw(str(password), bcrypt.gensalt(14))
    
    #def __repr__(self):
    #    return u"<User id='%s' name='%s' desc='%s' active='%s'>" % (
    #                self.id, self.name, self.desc, self.active)

    def _check_password(self, password):
        # verifying the password
        res = bcrypt.checkpw(str(password), str(self.password))
        #res = sha256_crypt.verify(password, self.password)
        return res

class Group(Base, ApiObject):
    __tablename__ = u'group'

    member = relationship(u'User', secondary=group_user,
                          backref=backref(u'group', lazy=u'dynamic'))
    role = relationship(u'Role', secondary=role_group,
                        backref=backref(u'group', lazy=u'dynamic'))    
    
    #init member value to an empty list when creating a group
    def __init__(self, objid, name, member=[], role=[], desc=None, active=True, 
                 expiry_date=None):
        ApiObject.__init__(self, objid, name, desc, active)
        
        self.member = member
        self.role = role
      
        if expiry_date is None:
            expiry_date = datetime.datetime.today()+datetime.timedelta(days=365)
        self.expiry_date = expiry_date      
    
    #def __repr__(self):
    #    return u"<Group id='%s' name='%s' desc='%s'>" % (
    #                self.id, self.name, self.desc)

# System object types
class SysObjectType(Base):
    __tablename__ = u'sysobject_type'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    objtype = Column(String(100))
    objdef = Column(String(200))
    objclass = Column(String(100))
    creation_date = Column(DateTime())

    def __init__(self, objtype, objdef, objclass):
        """
        :param objtype: object type. String like service, resource, container
        :param objdef: object defintition. String like vdcservice, cloudstack
        :param objclass: object class. String like Cloudstack
        """
        self.objtype = objtype
        self.objdef = objdef
        self.objclass = None
        self.creation_date = datetime.datetime.today()   
    
    def __repr__(self):
        return u"<SysObjectType id=%s type=%s def=%s>" % (
                    self.id, self.objtype, self.objdef)

# System objects
class SysObject(Base, ApiObject):
    __tablename__ = u'sysobject'

    name = Column(String(100))
    type_id = Column(Integer(), ForeignKey(u'sysobject_type.id'))
    type = relationship(u"SysObjectType", backref=u"sysobject") 

    def __init__(self, otype, objid, desc=u''):
        ApiObject.__init__(self, objid, u'', desc, True)
        
        self.type = otype     
    
    def __repr__(self):
        return u"<SysObject id=%s type=%s def=%s objid=%s>" % (
                    self.id, self.type.objtype, self.type.objdef, self.objid)

# System object actions
class SysObjectAction(Base):
    __tablename__ = u'sysobject_action'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    value = Column(String(20), unique=True)
    
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return u"<SysObjectAction id=%s value=%s>" % (self.id, self.value)

# System object permissions
class SysObjectPermission(Base):
    __tablename__ = u'sysobject_permission'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    obj_id = Column(Integer(), ForeignKey(u'sysobject.id'))
    obj = relationship(u'SysObject')
    action_id = Column(Integer(), ForeignKey(u'sysobject_action.id'))
    action = relationship(u'SysObjectAction')

    def __init__(self, obj, action):
        self.obj = obj
        self.action = action
        
    def __repr__(self):
        return u"<SysObjectPermission id=%s type=%s def=%s objid=%s action=%s>" % (
                    self.id, self.obj.type.objtype, self.obj.type.objdef, 
                    self.obj.objid, self.action.value)
        
# System object policy
class SysPolicy(Base):
    __tablename__ = u'syspolicy'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer(), ForeignKey(u'sysobject_type.id'))
    type = relationship(u"SysObjectType", backref=u"sysobject_type") 
    action_id = Column(Integer(), ForeignKey(u'sysobject_action.id'))
    action = relationship(u'SysObjectAction')

    def __init__(self, type, action):
        self.type = type
        self.action = action
        
    def __repr__(self):
        return u"<SysPolicy id=%s type=%s def=%s action=%s>" % (
                    self.id, self.type.objtype, self.type.objdef, 
                    self.action.value)        

class AuthDbManager(AbstractAuthDbManager, AbstractDbManager):
    """Authorization db manager                                                                                    
    """
    def __init__(self, session=None):
        AbstractDbManager.__init__(self, session)
        AbstractAuthDbManager.__init__(self, session)
    
    def set_initial_data(self):
        """Set initial data.
        """
        @netsted_transaction(self.get_session())
        def func(session):
            # object actions
            actions = [u'*', u'view', u'insert', u'update', u'delete', u'use']
            data = []
            for item in actions:
                data.append(SysObjectAction(item))
            session.add_all(data) 
            self.logger.debug(u'Add object actions: %s' % actions)
        return func()

    #
    # System Object Type manipulation methods
    #
    @query
    def get_object_type(self, oid=None, objtype=None, objdef=None,
                        page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :param page: type list page to show [default=0]
        :param size: number of types to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param size: sort field [default=id]           
        :return: SysObjectType corresponding to oid or value. If no param are 
                 specified return all the system object types.                
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
            ot = ot
        else:
            ot = session.query(SysObjectType)
            
        total = ot.count()
        
        start = size * page
        end = size * (page + 1)
        ot = ot.order_by(u'%s %s' % (field, order))[start:end]
        
        if len(ot) <= 0:
            raise ModelError('No object types found')             
            
        self.logger.debug('Get object types: %s' % truncate(ot))
        return ot, total

    @netsted_transaction
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
            ot = session.query(SysObjectType).filter_by(objtype=objtype)\
                                             .filter_by(objdef=objdef)\
                                             .first()
            if ot is None:
                record = SysObjectType(objtype, objdef, None)
                data.append(record)
        session.add_all(data)
        session.flush()
        
        self.logger.debug(u'Add object types: %s' % data)
        return data

    @netsted_transaction
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
            self.logger.debug('Remove object types: %s' % ots)
            return True                
        else:
            raise ModelError('No object types found')

    #
    # System Object Action manipulation methods
    #
    @query
    def get_object_action(self, oid=None, value=None):
        """Get system object action.
        
        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: SysObjectAction corresponding to oid or value. If no param are 
                 specified return all the system object actions.
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
        self.logger.debug('Get object action: %s' % truncate(oa))
        return oa

    @netsted_transaction
    def add_object_actions(self, items):
        """Add a list of system object actions.
        
        :param items: list of strings that define the action. 
                      Es. 'view', 'use', 'insert'
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        data = []
        for item in items:
            data.append(SysObjectAction(item))
        session.add_all(data)
        session.flush()
        self.logger.debug('Add object action: %s' % data)
        return data

    @netsted_transaction
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
            self.logger.debug('Delete action: %s' % ot)
            return True
        else: 
            return False

    #
    # System Object manipulation methods
    #
    @query
    def count_object(self):
        """Coint system object.
        """   
        session = self.get_session()
        res = session.query(func.count(SysObject.id))
        
        self.logger.debug(u'Count objects: %s' % res)
        return res
    
    @query
    def get_object(self, oid=None, objid=None, objtype=None, objdef=None, 
                   page=0, size=10, order=u'DESC', field=u'id'):
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
        
        .. versionadded:: 0.0
        """
        session = self.get_session()
        sqlcount = [u'SELECT count(t1.id) as count',
                    u'FROM sysobject t1, sysobject_type t2', 
                    u'WHERE t1.type_id=t2.id']                    
        sql = [u'SELECT t1.id as id, t1.objid as objid, t2.objtype as objtype, '
               u't2.objdef as objdef',
               u'FROM sysobject t1, sysobject_type t2', 
               u'WHERE t1.type_id=t2.id']
                
        params = {}
        if oid is not None:
            sql.append(u'AND t1.id LIKE :id')
            sqlcount.append(u'AND t1.id LIKE :id')
            params[u'id'] = oid
        if objid is not None:
            sql.append(u'AND t1.objid LIKE :objid')
            sqlcount.append(u'AND t1.objid LIKE :objid')
            params[u'objid'] = "%"+objid+"%"
        if objtype is not None:
            sql.append(u'AND t2.objtype LIKE :objtype')
            sqlcount.append(u'AND t2.objtype LIKE :objtype')
            params[u'objtype'] = "%"+objtype+"%"
        if objdef is not None:
            sql.append(u'AND t2.objdef LIKE :objdef')
            sqlcount.append(u'AND t2.objdef LIKE :objdef')
            params[u'objdef'] = "%"+objdef+"%"            
        
        # get total rows
        total = session.execute(u' '.join(sqlcount), params).fetchone()[0]
                
        offset = size * page
        sql.append(u'ORDER BY %s %s' % (field, order))
        sql.append(u'LIMIT %s OFFSET %s' % (size, offset))

        res = session.query(SysObject)\
                     .from_statement(text(u' '.join(sql)))\
                     .params(params).all()
                     
        if len(res) <= 0:
            self.logger.error(u'No objects (%s, %s, %s) found' % (oid, objid, objtype))
            raise ModelError(u'No objects (%s, %s, %s) found' % (oid, objid, objtype))
                     
        self.logger.debug(u'Get objects: %s' % truncate(res))
        return res, total

    @netsted_transaction
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
        for obj in objs:
            # verify if object already exists
            sysobj = session.query(SysObject).\
                             filter_by(objid=obj[1]). \
                             filter_by(type=obj[0]).first()
            if sysobj is not None:
                self.logger.error(u'Object %s already exists' % sysobj)
                raise ModelError(u'Object %s already exists' % sysobj, code=409)
            
            # add object
            sysobj = SysObject(obj[0], obj[1], desc=obj[2])
            session.add(sysobj)
            session.flush()
            self.logger.debug(u'Add system object: %s' % sysobj)
            
            # add permissions
            for action in actions: 
                perm = SysObjectPermission(sysobj, action)
                session.add(perm)
            self.logger.debug(u'Add system object %s permissions' % sysobj.id)
        
        return sysobj.id

    @netsted_transaction
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
        data = {'objid':new_objid, 'modification_date':datetime.datetime.today()}
        if oid is not None: 
            query = session.query(SysObject).filter_by(oid=oid)
        if objid is not None: 
            query = session.query(SysObject).filter_by(objid=objid)
        if objtype is not None:
            query = session.query(SysObject).filter_by(objtype=objtype)

        query.update(data)
        self.logger.debug('Update objects: %s' % data)
        return True

    @netsted_transaction
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
        sql = ["SELECT t1.id as id, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef",
               "FROM sysobject t1, sysobject_type t2", 
               "WHERE t1.type_id=t2.id "]
                
        params = {}
        if oid is not None:
            sql.append('AND t1.id LIKE :id')
            params['id'] = oid
        if objid is not None:
            sql.append('AND t1.objid LIKE :objid')
            params['objid'] = objid
        if objtype is not None:
            sql.append('AND t2.objtype LIKE :objtype AND t2.objdef LIKE :objdef')
            params['objtype'] = objtype.objtype
            params['objdef'] = objtype.objdef
                
        query = session.query(SysObject)\
                       .from_statement(text(" ".join(sql))).params(params).all()
                     
        if len(query) <= 0:
            self.logger.error("No objects found")
            raise ModelError("No objects found")
                    
        for item in query:
            # remove permissions
            perms = session.query(SysObjectPermission)\
                           .filter_by(obj_id=item.id).all()
            for perm in perms:
                session.delete(perm)                
            
            # remove object
            session.delete(item)
        self.logger.debug('Remove objects: %s' % query)
        return True

    #
    # System Object Permission manipulation methods
    #
    @query
    def get_permission_by_id(self, permission_id=None, object_id=None, 
                             action_id=None):
        """Get system object permisssion.
        
        :param permission_id: System Object Permission id [optional]
        :param object_id: System Object id [optional]
        :param action_id: System Object Action id [optional]
        :return: list of SysObjectPermissionue.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid, ",
               "t2.objtype as objtype, t2.objdef as objdef, ", 
               "t3.id as aid, t3.value as action",
               "FROM sysobject t1, sysobject_type t2, ",
               "sysobject_action t3, sysobject_permission t4",
               "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id ",
               "AND t1.type_id=t2.id "]
                
        params = {}
        if permission_id is not None:
            sql.append('AND t4.id=:permission_id ')
            params['permission_id'] = permission_id
        if object_id is not None:
            sql.append('AND t1.id=:object_id ')
            params['object_id'] = object_id           
        if action_id is not None:
            sql.append('AND t3.id=:action_id ')
            params['action_id'] = action_id
                     
        res = session.query(SysObjectPermission).\
                      from_statement(text(" ".join(sql))).params(params).all()

        if len(res) <= 0:
            self.logger.error("No permissions found")
            raise ModelError("No permissions found")                         
                     
        self.logger.debug('Get object permissions: %s' % truncate(res))
        return res
    
    @query
    def get_permission_by_object(self, objid=None, objid_filter=None, 
                                 objtype=None, objdef=None,
                                 objdef_filter=None, action=None,
                                 page=0, size=10, order=u'DESC', field=u'id'):
        """Get system object permisssion.
        
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :param objdef_filter str: Part of object definition [optional]
        :param action str: Object action [optional]
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]      
        :return: list of SysObjectPermission.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sqlcount = ["SELECT count(t4.id)",
                    "FROM sysobject t1, sysobject_type t2,",
                    "sysobject_action t3, sysobject_permission t4",
                    "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id",
                    "AND t1.type_id=t2.id"]        
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid,",
               "t2.objtype as objtype, t2.objdef as objdef,", 
               "t3.id as aid, t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4",
               "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id",
               "AND t1.type_id=t2.id"]
                
        params = {}
        if objid is not None:
            sql.append('AND t1.objid LIKE :objid')
            sqlcount.append('AND t1.objid LIKE :objid')
            params['objid'] = objid
        if objid_filter is not None:
            sql.append('AND t1.objid LIKE :objid')
            sqlcount.append('AND t1.objid LIKE :objid')
            params['objid'] = '%'+objid_filter+'%'
        if objtype is not None:
            sql.append('AND t2.objtype LIKE :objtype')
            sqlcount.append('AND t2.objtype LIKE :objtype')
            params['objtype'] = objtype
        if objdef is not None:
            sql.append('AND t2.objdef LIKE :objdef')
            sqlcount.append('AND t2.objdef LIKE :objdef')
            params['objdef'] = objdef
        if objdef_filter is not None:
            sql.append('AND t2.objdef LIKE :objdef')
            sqlcount.append('AND t2.objdef LIKE :objdef')
            params['objdef'] = '%'+objdef_filter+'%'                
        if action is not None:
            sql.append('AND t3.value LIKE :action')
            sqlcount.append('AND t3.value LIKE :action')
            params['action'] = action
        
        # get total rows
        total = session.execute(u' '.join(sqlcount), params).fetchone()[0]
                
        offset = size * page
        sql.append(u'ORDER BY %s %s' % (field, order))
        sql.append(u'LIMIT %s OFFSET %s' % (size, offset))        
        
        res = session.query(SysObjectPermission) \
                     .from_statement(text(" ".join(sql))) \
                     .params(params).all()
        
        if len(res) <= 0:
            self.logger.error("No permissions found")
            raise ModelError("No permissions found")                           
                     
        self.logger.debug('Get object permissions: %s' % truncate(res))
        return res, total

    #
    # Role manipulation methods
    #
    def get_roles(self, *args, **kvargs):
        """Get roles
        
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
        res, total = self.get_paginated_entities(Role, filters=filters, 
                                                 *args, **kvargs)     
        
        return res, total
    
    '''
    @query
    def get_role(self, oid=None, objid=None, name=None, uuid=None,
                 page=0, size=10, order=u'DESC', field=u'id'):
        """Get role with certain name. If name is not specified return all the 
        roles.
        
        :param id:
        :param objid:
        :param uuid:
        :param name: name of the role [Optional]
        :param page: object list page to show [default=0]
        :param size: number of object to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: List of role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if oid is not None:
            role = session.query(Role).filter_by(id=oid)
        elif objid is not None:
            role = session.query(Role).filter_by(objid=objid)
        elif uuid is not None:
            role = session.query(Role).filter_by(uuid=uuid)            
        elif name is not None:
            role = session.query(Role).filter_by(name=name)
        else:
            role = session.query(Role)

        total = role.count()
        
        start = size * page
        end = size * (page + 1)
        role = role.order_by(u'%s %s' % (field, order))[start:end]            
            
        self.logger.debug('Get roles: %s' % truncate(role))
        return role, total'''
    
    @query
    def get_role_permissions(self, names=None, page=0, size=10, order=u'DESC', 
                             field=u'id', *args, **kvargs):
        """Get role permissions.
        
        :param names: list of roles name
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: list of object with the following fields:
                 (id, oid, value, type, aid, action)
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sqlcount = [
            "SELECT count(t4.id)",
            "FROM sysobject t1, sysobject_type t2,",
            "sysobject_action t3, sysobject_permission t4,"
            "role t5, role_permission t6",
            "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and",
            "t1.type_id=t2.id and t6.role_id = t5.id and",
            "t6.permission_id=t4.id and t5.name IN :role_names"
        ]
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid, ",
               "t2.objtype as objtype, t2.objdef as objdef, t3.id as aid,"
               "t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4,"
               "role t5, role_permission t6",
               "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and",
               "t1.type_id=t2.id and t6.role_id = t5.id and",
               "t6.permission_id=t4.id and t5.name IN :role_names"]

        # get total rows
        total = session.execute(u' '.join(sqlcount), 
                                {u'role_names':names}).fetchone()[0]
                
        offset = size * page
        sql.append(u'ORDER BY %s %s' % (field, order))
        sql.append(u'LIMIT %s OFFSET %s' % (size, offset)) 

        query = session.query(SysObjectPermission).\
                from_statement(text(" ".join(sql))).\
                params(role_names=names).all()
        
        self.logger.debug(u'Get role %s permissions: %s' % 
                          (names, truncate(query)))
        return query, total

    @query
    def get_role_permissions2(self, names, *args, **kvargs):
        """Get role permissions.
        
        :param names: role name list
        :return: list of object with the following fields:
                 (id, oid, objtype, objdef, objid, aid, action)
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()  
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid, ",
               "t2.objtype as objtype, t2.objdef as objdef, ",
               "t3.id as aid, t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4,"
               "role t5, role_permission t6",
               "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and",
               "t1.type_id=t2.id and t6.role_id = t5.id and",
               "t6.permission_id=t4.id and t5.name IN :role_name"]

        #columns = ['id', 'oid', 'objtype', 'objdef', 'objclass', 'objid', 'aid', 'action']
        columns = [u'id', u'oid', u'objtype', u'objdef', u'objid', u'aid', 
                   u'action']
        query = session.query(*columns).\
                from_statement(text(" ".join(sql))).\
                params(role_name=names).all()

        self.logger.debug(u'Get role %s permissions: %s' % (names, 
                                                            truncate(query)))
        return query
        
    @query
    def get_permission_roles(self, perm,  page=0, size=10, order=u'DESC', 
                             field=u'id', *args, **kvargs):
        """Get roles related to a permission.
        
        :param perm: permission instance
        :param page: role list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]            
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        if perm is None:
            raise ModelError(u'Permission is not correct or does not exist')        
        
        session = self.get_session()
        total = perm.role.count()
        
        start = size * page
        end = size * (page + 1)
        roles = perm.role.order_by(u'%s %s' % (field, order))[start:end]        
        
        self.logger.debug('Get permission %s roles: %s' % (perm, truncate(roles)))
        return roles, total       
        
    def add_role(self, objid, name, desc):
        """Add a role.
        
        :param objid: role objid
        :param name: role name
        :param permissions: list of permission
        :param desc: role desc
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(Role, objid, name, [], desc=desc, active=True)
        return res

    def update_role(self, *args, **kvargs):
        """Update role. Extend :function:`update_entity`

        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :param desc: role desc. [optional]
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Role, *args, **kvargs)
        return res  
    
    def remove_role(self, *args, **kvargs):
        """Remove role.
        
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :raises TransactionError: raise :class:`TransactionError`        
        """
        res = self.remove_entity(Role, *args, **kvargs)
        return res

    '''
    @netsted_transaction
    def update_role(self, oid=None, objid=None, name=None, new_name=None, 
                    new_desc=None):
        """Update a role.
        
        :param oid: role id [optional] 
        :param objid: role objid [optional] 
        :param name: role name [optional] 
        :param new_name: new role name [optional] 
        :param new_desc: new role desc [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        if oid is not None:
            role = session.query(Role).filter_by(id=oid)
        elif objid is not None:
            role = session.query(Role).filter_by(objid=objid)
        elif name is not None:
            role = session.query(Role).filter_by(name=name)      
        
        if role.first() is None:
            self.logger.error("Role %s|%s|%s does not exist" % 
                              (oid, objid, name))
            raise ModelError("Role %s|%s|%s does not exist" % 
                                  (oid, objid, name))
        
        data = {}
        if new_name is not None: 
            data['name'] = new_name
        if new_desc  is not None:
            data['desc'] = new_desc
        if new_name is not None or new_description is not None:
            data['modification_date'] = datetime.datetime.today()
            role.update(data)
        
        self.logger.debug('Update role %s with data %s' % (name, data))
        return True
    
    @netsted_transaction
    def remove_role(self, role_id=None, name=None):
        """Remove a role. Specify at least role id or role name.
        
        :param role_id: id of the role [optional]
        :param name: name of role [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if role_id is not None:  
            role = session.query(Role).filter_by(id=role_id).first()
        elif name is not None:
            role = session.query(Role).filter_by(name=name).first()
        
        # delete object type
        if role is not None:
            session.delete(role)
            self.logger.debug('Remove role : %s' % (role))
            return True
        else:
            self.logger.error("No role found")
            raise ModelError('No role found')'''

    @netsted_transaction
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
            # append permission to role if it doesn't already exists
            if role not in perm.role:
                role.permission.append(perm)
                append_perms.append(perm.id)
            else:
                self.logger.warn(u'Permission %s already exists in role %s' % (
                    perm, role))
        
        self.logger.debug(u'Append to role %s permissions: %s' % (role, perms))
        return append_perms
    
    @netsted_transaction
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
            #if len(perm.role.all()) > 0:
            role.permission.remove(perm)
            remove_perms.append(perm.id)
            
        self.logger.debug('Remove from role %s permissions: %s' % (role, perms))
        return remove_perms

    #
    # Group manipulation methods
    #
    @query
    def count_group(self):
        """Count group.
        """
        return self.count_entites(User)      
    
    @watch
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
        res, total = self.get_paginated_entities(Group, filters=filters, 
                                                 *args, **kvargs)     
        
        return res, total
    
    '''
    @query
    def get_group(self, name=None, oid=None, objid=None, uuid=None,
                  page=0, size=10, order=u'DESC', field=u'id'):
        """Get group with certain name, oid or objid. If these fields are not 
        specified return all the groups.
        
        :param oid: group id [optional]
        :param objid: group objid [optional]
        :param uuid: group uuid [optional]
        :param name: name of the group [Optional]
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id] 
        :return: Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if oid is not None:
            group = session.query(Group).filter_by(id=oid)
        elif objid is not None:
            group = session.query(Group).filter_by(objid=objid)
        elif uuid is not None:
            group = session.query(Group).filter_by(uuid=uuid)            
        elif name is not None:
            group = session.query(Group).filter_by(name=name)
        else:
            group = session.query(Group)
        
        total = group.count()
        
        start = size * page
        end = size * (page + 1)
        group = group.order_by(u'%s %s' % (field, order))[start:end]
        
        self.logger.debug(u'Get groups: %s' % truncate(group))
        return group, total'''
        
    @query
    def get_group_roles(self, group,  page=0, size=10, order=u'DESC', 
                        field=u'id', *args, **kvargs):
        """Get roles of a group.
        
        :param group: Orm Group istance
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]            
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        
        start = size * page
        end = size * (page + 1)
        roles = session.query(Role).join(Group.role)\
                       .filter(Group.id == group.id)\
                       .order_by(u'role.%s %s' % (field, order))[start:end]        
        #roles = group.role.order_by(u'%s %s' % (field, order))[start:end]        
        
        self.logger.debug('Get group %s roles: %s' % (group, truncate(roles)))
        return roles, len(group.role)

    @query
    def get_role_groups(self, role, page=0, size=10, order=u'DESC', field=u'id', 
                        *args, **kvargs):
        """Get groups of a role.
        
        :param role: Orm Role istance
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`          
        """
        session = self.get_session()
        total = role.group.count()
        
        start = size * page
        end = size * (page + 1)
        groups = role.group.order_by(u'%s %s' % (field, order))[start:end]        
        
        self.logger.debug('Get role %s groups: %s' % (role, truncate(groups)))
        return groups, total

    @query
    def get_group_users(self, group, page=0, size=10, order=u'DESC', 
                          field=u'id', *args, **kvargs):
        """Get users of a group.
        
        :param group: Orm Group istance
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        #total = group.member.count()

        start = size * page
        end = size * (page + 1)
        members = session.query(User).join(User.group)\
                       .filter(Group.id == group.id)\
                       .order_by(u'user.%s %s' % (field, order))[start:end]        
        #members = group.member.order_by(u'%s %s' % (field, order))[start:end]         
        
        self.logger.debug('Get group %s members : %s' % (group, members))
        return members, len(group.member)
        
    @query
    def get_user_groups(self, user, page=0, size=10, order=u'DESC', field=u'id', 
                        *args, **kvargs):
        """Get groups of a user.
        
        :param user: Orm User istance
        :param page: groups list page to show [default=0]
        :param size: number of groups to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]               
        :return: List of Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        total = user.group.count()

        start = size * page
        end = size * (page + 1)
        groups = user.group.order_by(u'%s %s' % (field, order))[start:end]         

        self.logger.debug(u'Get user %s groups : %s' % (user, groups))
        return groups, total
        
    @query
    def get_group_permissions(self, group, page=0, size=10, order=u'DESC', 
                             field=u'id', *args, **kvargs):
        """Get group permissions.
        
        :param group: Orm Group istance
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
            raise ModelError(u'Group is not correct or does not exist')

        # get user permissions
        roles = []
        for role in group.role:
            roles.append(role.name)
        
        if len(roles) == 0:
            self.logger.warn(u'Group %s has no roles associated' % group.id)
            total = 0
            perms = []
        else:
            perms, total = self.get_role_permissions(names=roles, page=page, 
                                                     size=size, order=order, 
                                                     field=field)

        self.logger.debug(u'Get group %s perms : %s' % (group, truncate(perms)))
        return perms, total
    
    @query
    def get_group_permissions2(self, group, *args, **kvargs):
        """Get group permissions.
        
        :param group: Orm Group istance
        :return: Pandas Series of SysObjectPermission
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        
        if group is None:
            raise ModelError(u'Group is not correct or does not exist')        
        
        # get all group roles
        roles = []
        for role in group.role:
            roles.append(role.name)

        # get group permissions from group roles
        perms = self.get_role_permissions2(names=roles)
        
        self.logger.debug(u'Get group %s perms : %s' % (group, truncate(perms)))
        return perms    
    
    @netsted_transaction
    def add_group(self, objid, name, desc=u'', members=[], roles=[]):
        """Add group.
        
        :param objid: group objid
        :param name: name of the group
        :param members: List with User instances. [Optional]
        :param roles: List with Role instances. [Optional]
        :param desc: group desc. [Optional]
        :return: True if password is correct
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(Group, objid, name, member=members, role=roles, 
                              desc=desc, active=True, expiry_date=None)
        return res    
        
    def update_group(self, *args, **kvargs):
        """Update group. Extend :function:`update_entity`

        :param kvargs str: data to update. {u'name':, u'desc':, u'active':, 
            u'password':, u'expiry_date':}  
        """
        res = self.update_entity(Group, *args, **kvargs)
        return res  
    
    def remove_group(self, *args, **kvargs):
        """Remove group.
        """
        res = self.remove_entity(Group, *args, **kvargs)
        return res        
    
    '''
    @netsted_transaction
    def update_group(self, oid=None, new_name=None, new_desc=None):
        """Update a group.
        
        :param name: name of the group
        :param new_name: new user name [optional]
        :param desc: User description. [Optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session() 
        data = {}
        if new_name is not None: 
            data['name'] = new_name                
        if new_description is not None: 
            data['description'] = new_description
                            
        if len(data) > 0:
            data['modification_date'] = datetime.datetime.today()
            session.query(Group).filter_by(id=oid).update(data)
        
        self.logger.debug('Update group %s with data : %s' % (oid, data))
        return True
        
    @netsted_transaction
    def remove_group(self, group_id=None, name=None):
        """Remove a group. Specify at least group id or group name.
        
        :param group_id: id of the group [optional]
        :param name: name of group [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if group_id is not None:  
            group = session.query(Group).filter_by(id=group_id).first()
        elif name is not None:
            group = session.query(Group).filter_by(name=name).first()
        
        if not group:
            self.logger.error('No group found')
            raise ModelError('No group found')
        
        self.logger.debug('Remove group : %s' % (group))
        # delete object type
        session.delete(group)
        
        return True'''
         
    @netsted_transaction
    def append_group_role(self, group, role):
        """Append a role to an group
        
        :param group: Group instance
        :param role: Role instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # append role to user if it doesn't already appended
        if role.group.filter_by(name=group.name).first() is not None:
            self.logger.warn(u'Role %s already exists in group %s' % (role, group))
            return False
        else:
            group.role.append(role)
            self.logger.debug(u'Append group %s role : %s' % (group, role))
            return role.id
        
    @netsted_transaction
    def remove_group_role(self, group, role):
        """Remove role from group
 
        :param group: Group instance
        :param role: Role instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # remove role form user if it exists
        if role.group.filter_by(name=group.name).first():
            group.role.remove(role)
            self.logger.debug(u'Remove group %s role : %s' % (group, role))
            return role.id
        else:
            self.logger.warn(u'Role %s does not exist in group %s' % (role, group))
            return False
        
    @netsted_transaction
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
            self.logger.warn(u'User %s already exists in group %s' % (user, group))
            return False
        else:
            group.member.append(user)
            self.logger.debug(u'Append user %s role : %s' % (group, user))
            return user.id

    @netsted_transaction
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
            self.logger.debug(u'Remove group %s user : %s' % (group, user))
            return user.id
        else:
            self.logger.error(u'User %s doesn''t exist in group %s' % (user, group))
            return False

    #
    # User manipulation methods
    #
    def count_user(self):
        """Count user.
        """
        return self.count_entites(User)
    
    def get_users(self, *args, **kvargs):
        """Get users
        
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
        if u'expiry_date' in kvargs:
            filters.append(u'AND expiry_date>=:expiry_date')
        res, total = self.get_paginated_entities(User, filters=filters, 
                                                 *args, **kvargs)     
        
        return res, total
    
    '''
    @query
    def get_user(self, name=None, oid=None, objid=None, uuid=None, active=None,
                 expiry_date=None, page=0, size=10, order=u'DESC', field=u'id'):
        """Get user with certain name. If name is not specified return all the 
        users.
        
        :param oid: user id [optional]
        :param objid: user authorization id [optional]
        :param uuid: user uuid [optional]
        :param name: name of the user [Optional]
        :param active: user status [Optional]
        :param expiry_date: list user with expiry_date >= expiry_date [Optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: User instances
        :rtype: :class:`User`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        if oid is not None:
            user = session.query(User).filter_by(id=oid)
        elif objid is not None:
            user = session.query(User).filter_by(objid=objid)
        elif uuid is not None:
            user = session.query(User).filter_by(uuid=uuid)            
        elif name is not None:
            user = session.query(User).filter_by(name=name)
        elif active is not None:
            user = session.query(User).filter_by(active=active)            
        elif expiry_date is not None:
            user = session.query(User).filter_by(expiry_date>=expiry_date)            
        else:
            user = session.query(User)
        
        total = user.count()
        
        start = size * page
        end = size * (page + 1)
        user = user.order_by(u'%s %s' % (field, order))[start:end]
        
        self.logger.debug(u'Get users: %s' % truncate(user))
        return user, total'''

    @query
    def get_user_roles(self, user=None, page=0, size=10, order=u'DESC', 
                       field=u'id', *args, **kvargs):
        """Get roles of a user.
        
        :param user: Orm User istance
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]            
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        
        start = size * page
        end = size * (page + 1)

        roles = session.query(Role).join(RoleUser)\
                       .filter(RoleUser.user_id == user.id)\
                       .order_by(u'role.%s %s' % (field, order))[start:end]        

        self.logger.debug(u'Get user %s roles: %s' % (user, truncate(roles)))
        return roles, len(roles)
    
    @query
    def get_user_roles_with_expiry(self, user=None, page=0, size=10, order=u'DESC', 
                                   field=u'id', *args, **kvargs):
        """Get roles of a user with expiry date
        
        :param user: Orm User istance
        :param page: roles list page to show [default=0]
        :param size: number of roles to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]            
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        
        start = size * page
        end = size * (page + 1)

        roles = session.query(Role,RoleUser.expiry_date).join(RoleUser)\
                       .filter(RoleUser.user_id == user.id)\
                       .order_by(u'role.%s %s' % (field, order))[start:end]        

        self.logger.debug(u'Get user %s roles: %s' % (user, truncate(roles)))
        return roles, len(roles)    
    
    @query
    def get_role_users(self, role=None, page=0, size=10, order=u'DESC', field=u'id', 
                       *args, **kvargs):
        """Get role users.
        
        :param role: Orm Role istance
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`          
        """
        session = self.get_session()
        #total = role.user.count()
        
        start = size * page
        end = size * (page + 1)
        #users = session.query(User).join(Role.user)\
        #               .filter(Role.id == role.id)\
        #               .order_by(u'user.%s %s' % (field, order))[start:end]        
        #users = role.user.order_by(u'%s %s' % (field, order))[start:end]  
        users = session.query(User).join(RoleUser)\
                       .filter(RoleUser.role_id == role.id)\
                       .order_by(u'user.%s %s' % (field, order))[start:end] 
        
        self.logger.debug('Get role %s users: %s' % (role, truncate(users)))
        return users, len(users)
        
    @query
    def get_user_permissions(self, user, page=0, size=10, order=u'DESC', 
                             field=u'id', *args, **kvargs):
        """Get user permissions.
        
        :param user: Orm User istance
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
            raise ModelError(u'User is not correct or does not exist')

        # get user roles
        roles = []
        user_roles = session.query(Role)\
                            .join(RoleUser)\
                            .filter(RoleUser.user_id == user.id).all()      
        for role in user_roles:
            roles.append(role.name)
            
        # get user roles from user groups
        for group in user.group:
            for role in group.role:
                roles.append(role.name)       

        if len(roles) == 0:
            self.logger.warn(u'User %s has no roles associated' % user.id)
            total = 0
            perms = []
        else:
            perms, total = self.get_role_permissions(names=roles, page=page, 
                                                     size=size, order=order, 
                                                     field=field)
        
        self.logger.debug(u'Get user %s perms: %s' % (user.name, truncate(perms)))
        return perms, total
        
    @query
    def get_user_permissions2(self, user, *args, **kvargs):
        """Get user permissions.
        
        :param user: Orm User istance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        
        if user is None:
            raise ModelError(u'User is not correct or does not exist')
        
        # get all user roles
        roles = []
        user_roles = session.query(Role)\
                            .join(RoleUser)\
                            .filter(RoleUser.user_id == user.id).all()      
        for role in user_roles:
            roles.append(role.name)
        for group in user.group:
            for role in group.role:
                roles.append(role.name)

        # get user permissions from user roles
        perms = self.get_role_permissions2(names=roles)

        self.logger.debug(u'Get user %s perms: %s' % (user, truncate(perms)))
        return perms       
        
    @query
    def get_login_permissions(self, user, *args, **kvargs):
        """Get login user permissions.
        
        :param user: Orm User istance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        
        if user is None:
            raise ModelError(u'User is not correct or does not exist')
        
        # get all user roles
        roles = []
        user_roles = session.query(Role)\
                            .join(RoleUser)\
                            .filter(RoleUser.user_id == user.id).all()      
        for role in user_roles:
            roles.append(role.name)
        for group in user.group:
            for role in group.role:
                roles.append(role.name)

        # get user permissions from user roles
        sql = [u'SELECT t4.id as id, t1.id as oid, t1.objid as objid, ',
               u't2.objtype as objtype, t2.objdef as objdef, ',
               u't3.id as aid, t3.value as action',
               u'FROM sysobject t1, sysobject_type t2,',
               u'sysobject_action t3, sysobject_permission t4,',
               u'role t5, role_permission t6',
               u'WHERE t4.obj_id=t1.id and t4.action_id=t3.id and',
               u't1.type_id=t2.id and t6.role_id = t5.id and',
               u't6.permission_id=t4.id and t5.name IN :role_name']

        columns = [u'id', u'oid', u'objtype', u'objdef', u'objid', u'aid', 
                   u'action']
        perms = session.query(*columns).\
                from_statement(text(" ".join(sql))).\
                params(role_name=roles).all()

        self.logger.debug(u'Get user %s perms: %s' % (user, truncate(perms)))
        return perms
        
    @query
    def verify_user_password(self, user, password):
        """Verify user password.
        
        :param user: Orm User istance
        :param password: Password to verify
        :return: True if password is correct, False otherwise.
        :rtype: bool
        :raises QueryError: raise :class:`QueryError`      
        """
        # verifying the password
        res = user._check_password(password)
        
        self.logger.debug(u'Verify user %s password: %s' % (user, res))
        return res

    def add_user(self, objid, name, active=True, password=None, 
                 desc=u'', expiry_date=None):
        """Add user.
        
        :param objid: authorization id
        :param name: name of the user
        :param active: set if user is active [default=True]
        :param password: user password [optional]
        :param desc: user desc [default='']
        :param expiry_date: user expiry date [default=365 days]. Set using a 
                datetime object                      
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(User, objid, name, active=active, 
                              password=password, desc=desc, 
                              expiry_date=expiry_date)
        return res    
    
    def update_user(self, *args, **kvargs):
        """Update user. Extend :function:`update_entity`

        :param name: name of the user
        :param active: set if user is active [optional]
        :param password: user password [optional]
        :param desc: user desc [optional]
        :param expiry_date: user expiry date. Set using a datetime object 
            [optional]
        :param kvargs str: data to update. {u'name':, u'desc':, u'active':, 
            u'password':, u'expiry_date':}
        :raises TransactionError: raise :class:`TransactionError`
        """
        # generate new salt, and hash a password
        if u'password' in kvargs and kvargs[u'password'] != None:
            kvargs[u'password'] = bcrypt.hashpw(str(kvargs[u'password']), 
                                                bcrypt.gensalt(14))
        res = self.update_entity(User, *args, **kvargs)
        return res  
    
    def remove_user(self, *args, **kvargs):
        """Remove user.
        
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :raises TransactionError: raise :class:`TransactionError`  
        """
        res = self.remove_entity(User, *args, **kvargs)
        return res
    
    @netsted_transaction
    def expire_users(self, expiry_date):
        """Disable a user that is expired.
        
        :param expiry_date: expiry date used to disable user
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        user = session.query(User).filter(User.expiry_date<=expiry_date)
        user.update({u'active':False})
        res = [u.id for u in user.all()]
        self.logger.debug(u'Disable exipred users: %s' % (res))
        return res    
        
    @netsted_transaction
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
        ru = session.query(RoleUser).filter_by(user_id=user.id)\
                                    .filter_by(role_id=role.id)
        if ru.first() is not None:
            self.logger.warn(u'Role %s already exists in user %s' % (role, user))
            return False
        else:
            if expiry_date is None:
                expiry_date = datetime.datetime.today()+datetime.timedelta(days=365)
            ru = RoleUser(user.id, role.id, expiry_date)
            session.add(ru)
            session.flush()            
            self.logger.debug(u'Append user %s role: %s' % (user, role))
            return role.id
    
    @netsted_transaction
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
        ru = session.query(RoleUser).filter_by(user_id=user.id)\
                                    .filter_by(role_id=role.id).first()
        if ru is not None:
            session.delete(ru)
            self.logger.debug(u'Remove user %s role: %s' % (user, role))
            return role.id
        else:
            self.logger.warn(u'Role %s doesn''t exists in user %s' % (role, user))
            return False
        
    @netsted_transaction
    def remove_expired_user_role(self, expiry_date):
        """Remove roles from users where association is expired
 
        :param user: User instance
        :param role: Role instance
        :param expiry_date: role association expiry date. Set using a 
                datetime object
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        # remove role from user if it exists
        rus = session.query(RoleUser).filter(RoleUser.expiry_date<=expiry_date).all()
        for ru in rus:
            session.delete(ru)
        res = [(u.role_id, u.user_id) for u in rus]
        self.logger.debug(u'Remove expired roles from users: %s' % (res))
        return res
        
    @netsted_transaction
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
        
        attrib = session.query(UserAttribute).filter_by(user_id=user.id)\
                                             .filter_by(name=name)
        item = attrib.first()
        if item is not None:
            data = {}
            if new_name is not None:
                data['name'] = new_name
            if value is not None:
                data['value'] = value
            if desc is not None:
                data['desc'] = desc
            attrib.update(data)
            self.logger.debug('Update user %s attribute: %s' % (user.name, item))
            attrib = item
        else:
            attrib = UserAttribute(user.id, name, value, desc)
            session.add(attrib)
            session.flush()
            self.logger.debug('Append user %s attribute: %s' % (user.name, attrib))
        return attrib
    
    @netsted_transaction
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
        attrib = session.query(UserAttribute).filter_by(user_id=user.id)\
                                             .filter_by(name=name).first()        
        if attrib is not None:
            session.delete(attrib)
            self.logger.debug('Remove user %s attribute: %s' % (user.name, attrib))
            return True
        else:
            self.logger.error('Attribute %s doesn''t exists for user %s' % 
                              (name, user.name))
            raise ModelError('Attribute %s doesn''t exists for user %s' % 
                                  (name, user.name))