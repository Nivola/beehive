'''
Created on Jan 25, 2014

@author: darkbk
'''
import logging
import pandas as pd
import datetime
from passlib.hash import sha256_crypt
from beehive.common.data import transaction, query, operation
from beehive.common.data import QueryError
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

Base = declarative_base()

logger = logging.getLogger(__name__)

# Many-to-Many Relationship among users and system roles
role_user = Table('roles_users', Base.metadata,
    Column('user_id', Integer(), ForeignKey('user.id')),
    Column('role_id', Integer(), ForeignKey('role.id')))

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

# Systems roles
class Role(Base):
    __tablename__ = 'role'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    objid = Column(String(400), unique = True)
    name = Column(String(80), unique=True)
    description = Column(String(255))
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())    
    permission = relationship('SysObjectPermission', secondary=role_permission,
                              backref=backref('role', lazy='dynamic'))

    def __init__(self, objid, name, permission, description= ''):
        self.objid = objid
        self.name = name
        self.description = description
        self.permission = permission

        self.creation_date = datetime.datetime.today()
        self.modification_date = self.creation_date        
    
    def __repr__(self):
        return "<Role id='%s' name='%s' desc='%s')>" % (
                    self.id, self.name, self.description)

# Systems roles
class UserAttribute(Base):
    __tablename__ = 'user_attribute'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    name = Column(String(30))
    value = Column(String(100))    
    desc = Column(String(255))
    user_id = Column(Integer(), ForeignKey('user.id'))

    def __init__(self, user, name, value, desc=''):
        """
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
        return "<UserAttribute id='%s' user='%s' name='%s' value='%s'>" % (
                    self.id, self.user_id, self.name, self.value)

# Ldap users or groups
class User(Base):
    """User
    
    :param type: can be DBUSER, LDAPUSER 
    """
    __tablename__ = 'user'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    objid = Column(String(400), unique = True)
    name = Column(String(50), unique=True)
    description = Column(String(255))
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    password = Column(String(150))
    role = relationship('Role', secondary=role_user,
                        backref=backref('user', lazy='dynamic'))
    attrib = relationship("UserAttribute")
    active = Column(Boolean())

    def __init__(self, objid, username, roles, active=True, 
                       password=None, description=''):
        self.objid = objid
        self.name = username
        self.role = roles
        self.active = active
        self.description = description
        
        self.creation_date = datetime.datetime.today()
        self.modification_date = self.creation_date
        
        if password is not None:
            # generate new salt, and hash a password 
            self.password = sha256_crypt.encrypt(password)
    
    def __repr__(self):
        return "<User id='%s' name='%s' desc='%s' active='%s'>" % (
                    self.id, self.name, self.description, self.active)

    @watch
    def _check_password(self, password):
        # verifying the password
        res = sha256_crypt.verify(password, self.password)
        return res

class Group(Base):
    __tablename__ = 'group'
    __table_args__ = {'mysql_engine':'InnoDB'}    
        
    id = Column(Integer(), primary_key=True)
    objid = Column(String(400), unique = True)
    name = Column(String(80), unique=True)
    description = Column(String(255))
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())     
    member = relationship('User', secondary=group_user,
                          backref=backref('group', lazy='dynamic'))
    role = relationship('Role', secondary=role_group,
                        backref=backref('group', lazy='dynamic'))    
    
    #init member value to an empty list when creating a group
    def __init__(self, objid, name, member=[], role=[], description=None):
        self.objid = objid
        self.name = name
        self.description = description
        self.member = member
        self.role = role
        
        self.creation_date = datetime.datetime.today()
        self.modification_date = self.creation_date        
    
    def __repr__(self):
        return "<Group id='%s' name='%s' desc='%s'>" % (
                    self.id, self.name, self.description)

# System object types
class SysObjectType(Base):
    __tablename__ = 'sysobject_type'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    objtype = Column(String(100))
    objdef = Column(String(100))
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
        return "<SysObjectType id='%s' type='%s' def='%s'>" % (
                    self.id, self.objtype, self.objdef)

# System objects
class SysObject(Base):
    __tablename__ = 'sysobject'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    objid = Column(String(100), default='')
    desc = Column(String(100), default='')
    type_id = Column(Integer(), ForeignKey('sysobject_type.id'))
    type = relationship("SysObjectType", backref="sysobject")
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())    

    def __init__(self, otype, objid, desc=''):
        self.objid = objid
        self.type = otype
        self.desc = desc
        self.creation_date = datetime.datetime.today()
        self.modification_date = self.creation_date        
    
    def __repr__(self):
        return "<SysObject id='%s' type='%s' def='%s' objid='%s'>" % (
                    self.id, self.type.objtype, self.type.objdef, self.objid)

# System object actions
class SysObjectAction(Base):
    __tablename__ = 'sysobject_action'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    value = Column(String(20), unique=True)
    
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return "<SysObjectAction id='%s' value='%s'>" % (self.id, self.value)

# System object permissions
class SysObjectPermission(Base):
    __tablename__ = 'sysobject_permission'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    obj_id = Column(Integer(), ForeignKey('sysobject.id'))
    obj = relationship("SysObject")
    action_id = Column(Integer(), ForeignKey('sysobject_action.id'))
    action = relationship("SysObjectAction")

    def __init__(self, obj, action):
        self.obj = obj
        self.action = action
        
    def __repr__(self):
        return "<SysObjectPermission id='%s' type='%s' def='%s' objid='%s' action='%s'>" % (
                    self.id, self.obj.type.objtype, self.obj.type.objdef, 
                    self.obj.objid, self.action.value)

class AuthDbManager(AbstractAuthDbManager):
    """
    Ogni oggetto che verra utilizzato nel sistema di autorizzazzione e' formato 
    dalla tupla (tipo, valore, descrizione). 
    Es. 
        (*, *, *) identifica tutti i tipi di oggetti di qualsiasi valore
        (cloudapi, *, '') identifica tutti gli oggetti che sono messi a 
                          disposizione da cloudapi
        (cloudapi.orchestrator, *, '') identifica tutti gli oggetti che sono 
                                       messi a disposizione da tutti gli 
                                       orchestrator di cloudapi
                                       
        (orchestrator.tenant, *, '') identifica tutti i tenant che sono 
                                     messi a disposizione da tutti gli 
                                     orchestrator di cloudapi
        (orchestrator.tenant, clsk43_1.*, '') identifica tutti i tenant che sono 
                                              messi a disposizione dall'orchestrator 
                                              clsk43_1
        (orchestrator.tenant, clsk43_1.4u3929nd2b, '') identifica il tenant 4u3929nd2b
                                                       che e' messo a disposizione 
                                                       dall'orchestrator clsk43_1
                                                       
        (orchestrator.template, *, '') identifica tutti i template che sono 
                                       messi a disposizione da tutti gli 
                                       orchestrator di cloudapi
        (orchestrator.template, clsk43_1.*, '') identifica tutti i template che sono 
                                                messi a disposizione dall'orchestrator 
                                                clsk43_1
        (orchestrator.template, clsk43_1.4u3929nd2b, '') identifica il template 4u3929nd2b
                                      .add_object_types([obj_type])                   che e' messo a disposizione 
                                                         dall'orchestrator clsk43_1                                                       

        (orchestrator.vm, *, '') identifica tutte le vm che sono messe a 
                                 disposizione da tutti gli orchestrator di cloudapi
        (orchestrator.vm, clsk43_1.*, '') identifica tutte le vm che sono messe 
                                          a disposizione dall'orchestrator clsk43_1
        (orchestrator.vm, clsk43_1.div1.*, '') identifica tutte le vm che sono messe 
                                               a disposizione dall'orchestrator clsk43_1
                                               e dal contenitore div1
        (orchestrator.vm, clsk43_1.div1.div2.*, '') identifica tutte le vm che sono messe 
                                                    a disposizione dall'orchestrator clsk43_1
                                                    e dal contenitore div1.div2
        (orchestrator.vm, clsk43_1.t356sww8, '') identifica tutte la vm con id
                                                 t356sww8 che e' messa a disposizione 
                                                 dall'orchestrator clsk43_1. 
                                                 Il contenitore e' trascurabile al
                                                 fine dell'autorizzazione in questo
                                                 caso.                                                                                                
    """

    def __init__(self, session=None):
        """ """
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)        
        
        self._session = session

    def __del__(self):
        pass

    def __repr__(self):
        return "<AuthDbManager id='%s'>" % id(self)

    def get_session(self):
        if self._session is None:
            return operation.session
        else:
            return self._session

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.create_all(engine)
            logger.info('Create auth tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise AuthDbManagerError(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.drop_all(engine)
            logger.info('Remove auth tables from : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise AuthDbManagerError(e)

    def set_initial_data(self):
        """Set initial data.
        """
        @transaction(self.get_session())
        def func(session):
            # object actions
            actions = ['*', 'view', 'insert', 'update', 'delete', 'use']
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
    def get_object_type(self, oid=None, objtype=None, objdef=None):
        """Get system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: SysObjectType corresponding to oid or value. If no param are 
                 specified return all the system object types. 
        :rtype: list of :class:`SysObjectType`
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        if oid is not None:  
            ot = session.query(SysObjectType).filter_by(id=oid).all()
        elif objtype is not None or objdef is not None:
            ot = session.query(SysObjectType)
            if objtype is not None:
                ot = ot.filter_by(objtype=objtype)
            if objdef is not None:
                ot = ot.filter_by(objdef=objdef)
            ot = ot.all()
        else:
            ot = session.query(SysObjectType).all()
            
        if len(ot) <= 0:
            raise ModelError('No object types found')             
            
        self.logger.debug('Get object types: %s' % truncate(ot))
        return ot

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
            ot = session.query(SysObjectType).filter_by(objtype=objtype)\
                                             .filter_by(objdef=objdef)\
                                             .first()
            if ot is None:
                record = SysObjectType(objtype, objdef, u'')
                data.append(record)
        session.add_all(data)
        session.flush()
        
        self.logger.debug('Add object types: %s' % data)
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

    @transaction
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
        
        self.logger.debug('Count objects: %s' % res)
        return res
    
    @query
    def get_object(self, oid=None, objid=None, objtype=None):
        """Get system object filtering by id, by name or by type.

        **Examples**::
        
            manager.get_objects(oid='123242')
            manager.get_objects(value='', type="cloudstack.vm")
            manager.get_objects(value=clsk42_01.ROOT/CSI.')
            
        :param oid: System object id [optional]
        :type oid: str or None
        :param objid: Total or partial objid [optional]
        :param objtype: SysObjectType instance [optional]
        :return: one SysObject or a list of SysObject
        :rtype: :class:`SysObject` or list of :class:`SysObject`
        :raises QueryError: raise :class:`.decorator.QueryError` if query return error
        
        .. versionadded:: 0.0
        """
        session = self.get_session()
        sql = ["SELECT t1.id as id, t1.objid as objid, t2.objtype as objtype, t2.objdef as objdef",
               "FROM sysobject t1, sysobject_type t2", 
               "WHERE t1.type_id=t2.id "]
                
        params = {}
        if oid is not None:
            sql.append('AND t1.id LIKE :id')
            params['id'] = oid
        if objid is not None:
            sql.append('AND t1.objid LIKE :objid')
            params['objid'] = "%"+objid+"%"
        if objtype is not None:
            sql.append('AND t2.objtype LIKE :objtype AND t2.objdef LIKE :objdef')
            params['objtype'] = objtype.objtype
            params['objdef'] = objtype.objdef
                
        res = session.query(SysObject)\
                     .from_statement(text(" ".join(sql))).params(params).all()
                     
        if len(res) <= 0:
            self.logger.error("No objects (%s, %s, %s) found" % (oid, objid, objtype))
            raise ModelError("No objects (%s, %s, %s) found" % (oid, objid, objtype))
                     
        self.logger.debug('Get objects: %s' % truncate(res))
        return res

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
        for obj in objs:
            # verify if object already exists
            sysobj = session.query(SysObject).filter_by(objid=obj[1]). \
                             filter_by(type=obj[0]).first()
            if sysobj is not None:
                self.logger.error("Object %s already exists" % sysobj)
                raise ModelError('Object %s already exists' % sysobj, code=409)
            
            # add object
            sysobj = SysObject(obj[0], obj[1], desc=obj[2])
            session.add(sysobj)
            session.flush()
            self.logger.debug('Add system object: %s' % sysobj)
            
            # add permissions
            for action in actions: 
                perm = SysObjectPermission(sysobj, action)
                session.add(perm)
            self.logger.debug('Add system object %s permissions' % sysobj.id)
        
        return object

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
               "t2.objclass as objclass, t3.id as aid, t3.value as action",
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
                                 objdef_filter=None, action=None):
        """Get system object permisssion.
        
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :param objdef_filter str: Part of object definition [optional]
        :param action str: Object action [optional]
        :return: list of SysObjectPermission.
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid,",
               "t2.objtype as objtype, t2.objdef as objdef,", 
               "t2.objclass as objclass, t3.id as aid, t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4",
               "WHERE t4.obj_id=t1.id AND t4.action_id=t3.id",
               "AND t1.type_id=t2.id"]
                
        params = {}
        if objid is not None:
            sql.append('AND t1.objid LIKE :objid')
            params['objid'] = objid
        if objid_filter is not None:
            sql.append('AND t1.objid LIKE :objid')
            params['objid'] = '%'+objid_filter+'%'
        if objtype is not None:
            sql.append('AND t2.objtype LIKE :objtype')
            params['objtype'] = objtype
        if objdef is not None:
            sql.append('AND t2.objdef LIKE :objdef')
            params['objdef'] = objdef
        if objdef_filter is not None:
            sql.append('AND t2.objdef LIKE :objdef')
            params['objdef'] = '%'+objdef_filter+'%'                
        if action is not None:
            sql.append('AND t3.value LIKE :action')
            params['action'] = action
        
        res = session.query(SysObjectPermission). \
                      from_statement(text(" ".join(sql))).params(params).all()
        
        if len(res) <= 0:
            self.logger.error("No permissions found")
            raise ModelError("No permissions found")                           
                     
        self.logger.debug('Get object permissions: %s' % truncate(res))
        return res

    #
    # Role manipulation methods
    #
    @query
    def count_role(self):
        """Coint system object.
        """   
        session = self.get_session()
        res = session.query(func.count(Role.id))
        
        self.logger.debug('Count roles: %s' % res)
        return res    
    
    @query
    def get_role(self, oid=None, objid=None, name=None):
        """Get role with certain name. If name is not specified return all the 
        roles.
        
        :param id:
        :param objid
        :param name: name of the role [Optional]
        :return: List of role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if oid is not None:
            role = session.query(Role).filter_by(id=oid).all()
        elif objid is not None:
            role = session.query(Role).filter_by(objid=objid).all()
        elif name is not None:
            role = session.query(Role).filter_by(name=name).all()
        else:
            role = session.query(Role).all()
            
        self.logger.debug('Get roles: %s' % truncate(role))
        return role
    
    @query
    def get_role_permissions(self, name):
        """Get role permissions.
        user_type
        
        :param name: name of the role
        :return: list of object with the following fields:
                 (id, oid, value, type, aid, action)
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()  
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid, ",
               "t2.objtype as objtype, t2.objdef as objdef, t3.id as aid,"
               "t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4,"
               "role t5, role_permission t6",
               "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and",
               "t1.type_id=t2.id and t6.role_id = t5.id and",
               "t6.permission_id=t4.id and t5.name=:role_name"]

        query = session.query(SysObjectPermission).\
                from_statement(text(" ".join(sql))).\
                params(role_name=name).all()
        
        self.logger.debug('Get role %s permissions: %s' % (name, truncate(query)))
        return query

    @query
    def get_role_permissions2(self, name):
        """Get role permissions.
        user_type
        
        :param name: name of the role
        :return: list of object with the following fields:
                 (id, oid, value, type, aid, action)
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()  
        sql = ["SELECT t4.id as id, t1.id as oid, t1.objid as objid, ",
               "t2.objtype as objtype, t2.objdef as objdef, t2.objclass as objclass, ",
               "t3.id as aid, t3.value as action",
               "FROM sysobject t1, sysobject_type t2,",
               "sysobject_action t3, sysobject_permission t4,"
               "role t5, role_permission t6",
               "WHERE t4.obj_id=t1.id and t4.action_id=t3.id and",
               "t1.type_id=t2.id and t6.role_id = t5.id and",
               "t6.permission_id=t4.id and t5.name=:role_name"]

        query = session.query('id', 'oid', 'objtype', 'objdef', 
                              'objclass', 'objid', 'aid', 'action').\
                from_statement(text(" ".join(sql))).\
                params(role_name=name).all()

        self.logger.debug('Get role %s permissions: %s' % (name, truncate(query)))
        return query

    @query
    def get_permission_roles(self, perm):
        """Get roles related to a permission
        
        :param perm: permission
        :return: List of permissions
        :rtype: list
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        roles = perm.role.all()

        if len(roles) <= 0:
            self.logger.error('No role found for permissions %s' % (perm))
            raise ModelError('No role found for permissions %s' % (perm))

        self.logger.debug('Get permission %s roles: %s' % (perm, roles))
        return roles
        
    @transaction
    def add_role(self, objid, name, description):
        """Add a role.
        
        :param name: role name
        :param description: role descriptionuser_type
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()       
        data = Role(objid, name, [], description=description)
        session.add(data)
        session.flush()
        self.logger.debug('Add role : %s' % (data))
        return data

    @transaction
    def update_role(self, oid=None, objid=None, name=None, new_name=None, 
                    new_description=None):
        """Update a role.
        
        :param oid: role id [optional] 
        :param objid: role objid [optional] 
        :param name: role name [optional] 
        :param new_name: new role name [optional] 
        :param new_description: new role description [optional]
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
        if new_description  is not None:
            data['description'] = new_description
        if new_name is not None or new_description is not None:
            data['modification_date'] = datetime.datetime.today()
            role.update(data)
        
        self.logger.debug('Update role %s with data %s' % (name, data))
        return True
    
    @transaction
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
            raise ModelError('No role found')

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
        for perm in perms:
            # append permission to role if it doesn't already exists
            if role not in perm.role:
                role.permission.append(perm)
            else:
                self.logger.error('Permission %s already exists in role %s' % (
                    perm, role))
        
        self.logger.debug('Append to role %s permissions: %s' % (role, perms))
        return True
    
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
        for perm in perms:
            # remove permission from role
            #if len(perm.role.all()) > 0:
            role.permission.remove(perm)
            
        self.logger.debug('Remove from role %s permissions: %s' % (role, perms))
        return True

    #
    # Group manipulation methods
    #
    @query
    def count_group(self):
        """Count groups.
        """   
        session = self.get_session()
        res = session.query(func.count(Group.id))
        
        self.logger.debug('Count groups: %s' % res)
        return res        
    
    @query
    def get_group(self, name=None):
        """Get group with certain name. If name is not specified return all the 
        groups.
        
        :param name: name of the group [Optional]
        :return: Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        if name is not None:
            group = session.query(Group).filter_by(name=name).all()
        else:
            group = session.query(Group).all()
            
        self.logger.debug('Get groups : %s' % truncate(group))
        return group
        
    @query
    def get_group_roles(self, group):
        """Get group roles.
        
        :param group: Orm Group istance
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()         
        # get user roles
        roles = group.role
        self.logger.debug('Get group %s roles : %s' % (group, roles))
        return roles

    @query
    def get_role_groups(self, role):
        """Get role groups.
        
        :param role: Orm Role istance
        :return: List of Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()  
        # get role users
        groups = role.group.all()
        self.logger.debug('Get role %s groups : %s' % (role, groups))
        return groups

    @query
    def get_group_members(self, group):
        """Get group members.
        
        :param group: Orm Group istance
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        # get user members
        member = group.member
        self.logger.debug('Get group %s members : %s' % (group, member))
        return member
        
    @query
    def get_user_groups(self, user):
        """Get role groups.
        
        :param role: Orm Role istance
        :return: List of Group instances
        :rtype: list of :class:`Group`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session() 
        # get users groups
        group = user.group.all()
        self.logger.debug('Get user %s groups : %s' % (user, group))
        return group
        
    @query
    def get_group_permissions(self, group):
        """Get group permissions.
        
        :param group: Orm Group istance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        perms = pd.Series()

        # get user permissions
        for role in group.role:
            role_perms = self.get_role_permissions(name=role.name)
            for role_perm in role_perms:
                try:
                    perms[str(role_perm.id)]
                except KeyError:
                    perms.set_value(str(role_perm.id), role_perm)
        
        self.logger.debug('Get group %s perms : %s' % (group, truncate(perms)))
        return perms
    
    @query
    def get_group_permissions2(self, group):
        """Get group permissions.
        
        :param group: Orm Group istance
        :return: Pandas Series of SysObjectPermission
        :rtype: list of tuple
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        #perms = pd.Series()
        perms = []

        # get user permissions
        for role in group.role:
            perms.extend(self.get_role_permissions(name=role.name))
        
        self.logger.debug('Get group %s perms : %s' % (group, truncate(perms)))
        return perms    
    
    @transaction
    def add_group(self, objid, name, description='', members=[], roles=[]):
        """Add group.
        
        :param objid: group objid
        :param name: name of the group
        :param members: List with User instances. [Optional]
        :param roles: List with Role instances. [Optional]
        :param description: User description. [Optional]
        :return: True if password is correct
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()     
        data = Group(objid, name, member=members, role=roles, 
                     description=description)    
        session.add(data)
        session.flush()
        self.logger.debug('Add group: %s' % (data))
        return data
        
    @transaction
    def update_group(self, name=None, new_name=None, new_description=None):
        """Update a group.
        
        :param name: name of the group
        :param new_name: new user name [optional]
        :param description: User description. [Optional]
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
            session.query(Group).filter_by(name=name).update(data)
        
        self.logger.debug('Update group %s with data : %s' % (name, data))
        return True
        
    @transaction
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
        
        return True
         
    @transaction
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
            raise ModelError('Role %s already exists in group %s' % (role, group), code=409)
        else:
            group.role.append(role)
            self.logger.debug('Append group %s role : %s' % (group, role))
            return True
        
    @transaction
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
            self.logger.debug('Remove group %s role : %s' % (group, role))
            return True
        else:
            raise ModelError('Role %s doesn''t exist in group %s' % (role, group))
        
    @transaction
    def append_group_member(self, group, user):
        """Append a role to an group
        
        :param group: Group instance
        :param user: User instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # append role to user if it doesn't already appended
        if user.group.filter_by(name=group.name).first():
            self.logger.error('User %s already exists in group %s' % (user, group))
            raise ModelError('User %s already exists in group %s' % (user, group), code=409)
        else:
            group.member.append(user)
            self.logger.debug('Append user %s role : %s' % (group, user))
            return True

    @transaction
    def remove_group_memeber(self, group, user):
        """Remove role from group
 
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
            self.logger.debug('Remove group %s user : %s' % (group, user))
            return True
        else:
            self.logger.error('User %s doesn''t exist in group %s' % (user, group))
            raise ModelError('User %s doesn''t exist in group %s' % (user, group))

    #
    # User manipulation methods
    #
    @query
    def count_user(self):
        """Coint user.
        """   
        session = self.get_session()
        res = session.query(func.count(User.id))
        
        self.logger.debug('Count users: %s' % res)
        return res        
    
    @query
    def get_user(self, name=None, oid=None, objid=None):
        """Get user with certain name. If name is not specified return all the 
        users.
        
        :param oid: user id [optional]
        :param objid: user objid [optional]
        :param name: name of the user [Optional]
        :return: User instances
        :rtype: :class:`User`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        if oid is not None:
            user = session.query(User).filter_by(id=oid).all()
        elif objid is not None:
            user = session.query(User).filter_by(objid=objid).all()
        elif name is not None:
            user = session.query(User).filter_by(name=name).all()
        else:
            user = session.query(User).all()
        
        self.logger.debug('Get users: %s' % truncate(user))
        return user

    @query
    def get_user_roles(self, user):
        """Get user roles.
        
        :param user: Orm User istance
        :return: List of Role instances
        :rtype: list of :class:`Role`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()       
        # get user roles
        roles = user.role
        
        self.logger.debug('Get user %s roles: %s' % (user, truncate(roles)))
        return roles
    
    @query
    def get_role_users(self, role):
        """Get role users.
        
        :param role: Orm Role istance
        :return: List of User instances
        :rtype: list of :class:`User`
        :raises QueryError: raise :class:`QueryError`          
        """
        session = self.get_session()
        # get role users
        users = role.user.all()
        
        self.logger.debug('Get role %s users: %s' % (role, users))
        return users
        
    @query
    def get_user_permissions(self, user):
        """Get user permissions.
        
        :param user: Orm User istance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        perms = pd.Series()

        # get user permissions from user roles
        for role in user.role:
            role_perms = self.get_role_permissions(name=role.name)
            for role_perm in role_perms:
                try:
                    perms[str(role_perm.id)]
                except KeyError:
                    perms.set_value(str(role_perm.id), role_perm)

        # get user permissions from user groups
        for group in user.group:
            group_perms = self.get_group_permissions(group)
            for group_perm in group_perms:
                try:
                    perms[str(group_perm.id)]
                except KeyError:
                    perms.set_value(str(group_perm.id), group_perm)

        #self.logger.debug('Get user %s perms: %s' % (user, perms))
        return perms
        
    @query
    def get_user_permissions2(self, user):
        """Get user permissions.
        
        :param user: Orm User istance
        :return: Pandas Series of SysObjectPermission
        :rtype: pands.Series
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        #perms = pd.Series()
        perms = []

        # get user permissions from user roles
        for role in user.role:
            perms.extend(self.get_role_permissions2(name=role.name))

        # get user permissions from user groups
        for group in user.group:
            perms.extend(self.get_group_permissions2(group))

        #self.logger.debug('Get user %s perms: %s' % (user, perms))
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
        
        self.logger.debug('Verify user %s password: %s' % (user, res))
        return res

    @transaction
    def add_user(self, objid, username, roles, active=True, 
                       password=None, description=''):
        """Add user.
        
        :param objid:
        :param username: name of the user
        :param usertype: type of the user. Can be DBUSER, LDAPUSER
        :param roles: List with Role instances
        :param active: User status. If True user is active [Default=True]
        :param description: User description. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # verify if object already exists
        user = session.query(User).filter_by(name=username).first()
        if user is not None:
            self.logger.error(u'User %s already exists' % user)
            raise ModelError(u'User %s already exists' % user, code=409)  
        
        data = User(objid, username, roles, active=active, 
                    password=password, description=description)
        session.add(data)
        session.flush()
        self.logger.debug('Add user: %s' % (data))
        return data

    @transaction
    def update_user(self, oid=None, objid=None, name=None, new_name=None, 
                          new_type=None, new_description=None,
                          new_active=None, new_password=None):
        """Update a user.
        
        :param username: user name
        :param new_name: new user name [optional]
        :param new_type: new type of the user. Can be DBUSER, LDAPUSER [optional]
        :param new_description: new user description [optional]
        :param new_profile: new user profile [optional]
        :param new_active: new user status [optional]
        :param new_password: new user password [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        if oid is not None:
            user = session.query(User).filter_by(id=oid)
        elif objid is not None:
            user = session.query(User).filter_by(objid=objid)
        elif name is not None:
            user = session.query(User).filter_by(name=name)        
          
        data = {}
        if new_name is not None: 
            data['name'] = new_name
        if new_type is not None: 
            data['type'] = new_type                
        if new_description is not None: 
            data['description'] = new_description
        if new_active is not None:  
            data['active'] = new_active                
        if new_password is not None: 
            data['password'] = sha256_crypt.encrypt(new_password)
                            
        if user.first() is not None:
            data['modification_date'] = datetime.datetime.today()
            user.update(data)
            
        self.logger.debug('Update user %s|%s|%s with data: %s' % 
                          (oid, objid, name, data))
        return True
    
    @transaction
    def remove_user(self, user_id=None, username=None):
        """Remove a user. Specify at least user id or user name.
        
        :param user_id: id of the user [optional]
        :param username: name of user [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if user_id is not None:  
            user = session.query(User).filter_by(id=user_id).first()
        elif username is not None:
            user = session.query(User).filter_by(name=username).first()
        
        if user is None:
            self.logger.error('User %s/%s does not exist' % (user_id, username))
            raise ModelError('User %s/%s does not exist' % (user_id, username))
        
        # delete object type
        session.delete(user)
        
        self.logger.debug('Remove user: %s' % (user))
        return True
        
    @transaction
    def append_user_role(self, user, role):
        """Append a role to an user
        
        :param user: User instance
        :param role: Role instance
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # append role to user if it doesn't already appended
        if role.user.filter_by(name=user.name).first():
            self.logger.error('Role %s already exists in user %s' % (role, user))
            raise ModelError('Role %s already exists in user %s' % (role, user), code=409)
        else:
            user.role.append(role)
            self.logger.debug('Append user %s role: %s' % (user, role))
            return True
    
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
        if role.user.filter_by(name=user.name).first():
            user.role.remove(role)
            self.logger.debug('Remove user %s role: %s' % (user, role))
            return True
        else:
            self.logger.error('Role %s doesn''t exists in user %s' % (role, user))
            raise ModelError('Role %s doesn''t exists in user %s' % (role, user))
        
    @transaction
    def set_user_attribute(self, user, name, value=None, desc=None, new_name=None):
        """Append an attribute to a user
        
        :param user: User instance
        :param name: attribute name
        :param value: attribute value
        :param desc: attribute description
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
            self.logger.debug('Update user %s attribute: %s' % (user, item))
            attrib = item
        else:
            attrib = UserAttribute(user.id, name, value, desc)
            session.add(attrib)
            session.flush()
            self.logger.debug('Append user %s attribute: %s' % (user, attrib))
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
        attrib = session.query(UserAttribute).filter_by(user_id=user.id)\
                                             .filter_by(name=name).first()        
        if attrib is not None:
            session.delete(attrib)
            self.logger.debug('Remove user %s attribute: %s' % (user, attrib))
            return True
        else:
            self.logger.error('Attribute %s doesn''t exists for user %s' % 
                              (name, user))
            raise ModelError('Attribute %s doesn''t exists for user %s' % 
                                  (attrib, user))