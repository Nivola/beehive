import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from beehive.common.data import operation, query, netsted_transaction
from beecell.simple import truncate
from beecell.db import ModelError
from beecell.perf import watch
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, Index, DateTime
from sqlalchemy.sql import text
import hashlib
from uuid import uuid4
from re import match
from sqlalchemy.dialects import mysql

Base = declarative_base()

logger = logging.getLogger(__name__)

class ApiObject(object):
    """User
    
    :param type: can be DBUSER, LDAPUSER 
    """
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())
    
    def __init__(self, objid, name, desc=u'', active=True):
        self.uuid = str(uuid4())
        self.objid = objid
        self.name = name
        self.desc = desc
        self.active = active
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date
        
    def __repr__(self):
        return u"<%s id=%s uuid=%s obid=%s name=%s active=%s>" % (
                    self.__class__.__name__, self.id, self.uuid, self.objid, 
                    self.name, self.active)      

class PermTag(Base):
    __tablename__ = u'perm_tag'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    value = Column(String(100), unique = True)
    explain = Column(String(400))
    creation_date = Column(DateTime())
    
    def __init__(self, value, explain=None):
        """Create new permission tag
        
        :param value: tag value
        """
        self.creation_date = datetime.today()
        self.value = value
        self.explain = explain
    
    def __repr__(self):
        return u'<PermTag(%s, %s)>' % (self.value, self.explain)
    
class PermTagEntity(Base):
    __tablename__ = u'perm_tag_entity'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    tag = Column(Integer)
    entity = Column(Integer)
    type = Column(String(200))
    
    __table_args__ = (
        Index(u'idx_tag_entity', u'tag', u'entity', unique=True),
    )    
    
    def __init__(self, tag, entity, type):
        """Create new permission tag entity association
        
        :param tag: tag id
        :param entity: entity id
        :param type: entity type
        """
        self.tag = tag
        self.entity = entity
        self.type = type
    
    def __repr__(self):
        return u'<PermTagEntity(%s, %s, %s, %s)>' % (self.id, self.tag, 
                                                     self.entity, self.type)

class PaginatedQueryGenerator(object):
    def __init__(self, entity, session):
        """Use this class to generate and configure query with pagination
        and filtering based on tagged entity.
        Base table : perm_tag t1, perm_tag_entity t2, {entitytable} t3
        
        :param entity: entity
        """
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)         
        
        self.session = session
        self.entity = entity
        self.other_tables = []
        self.other_filters = []
        self.base_fields = [
            u'id', u'uuid', u'objid', u'name', u'desc', 
            u'active', u'creation_date', u'modification_date', 
            u'expiry_date'
        ]
    
    def set_pagination(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Set pagiantion params
        
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        """
        self.page = page
        self.size = size
        self.order = order
        self.field = field
        self.start = str(size * page)
        self.end = str(size * (page + 1))
    
    def add_table(self, table, alias):
        """Append table to query
        
        :param str table: table name
        :param str alias: table alias
        """
        self.other_tables.append([table, alias])
    
    def add_filter(self, sqlfilter):
        """Append filter to query
        
        :param str sqlfilter: sql filter like 'AND t3.id=101'
        """
        self.other_filters.append(sqlfilter)
        
    def add_fields(self, fields):
        """Add fields that you espect query returns
        
        :param list fields: list of fields to add to those returned by query
        """
        self.base_fields.extend(fields)            
    
    def base_stmp(self, count=False):
        """
        """
        fields = u't3.*'
        if count is True:
            fields = u'count(t3.id) as count'
        
        sql = [
            u'SELECT {fields}',
            u'FROM perm_tag t1, perm_tag_entity t2, {table} t3'
        ]
        # append other tables
        for table in self.other_tables:
            sql.append(u', %s %s' % (table[0], table[1]))
        
        # set base where
        sql.extend([
            u'WHERE t3.id=t2.entity AND t2.tag=t1.id',
            u'AND t1.value IN :tags'
        ])
        
        # add filters
        for sqlfilter in self.other_filters:
            sql.append(sqlfilter)            
        
        # set group by and limit
        if count is False:
            sql.extend([
                u'GROUP BY {field}',
                u'ORDER BY {field} {order}',
                u'LIMIT {start},{end}'
            ])

        # format query
        stmp = u' '.join(sql)
        stmp = stmp.format(table=self.entity.__tablename__, fields=fields,
            field=self.field, order=self.order, start=self.start, 
            end=self.end)
        return text(stmp)
    
    def run(self, tags, *args, **kvargs):
        """Make query
        
        :param list tags: list of permission tags
        """
        if tags is None or len(tags) == 0:
            tags = [u'']    
        
        # count all records
        stmp = self.base_stmp(count=True)
        total = self.session.query(u'count').\
                from_statement(stmp).\
                params(tags=tags, **kvargs).first()[0]
        
        # make query
        stmp = self.base_stmp()

        query = self.session.query(self.entity).\
                from_statement(stmp).\
                params(tags=tags, **kvargs)
        #self.logger.warn(u'stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        query = query.all()
        
        self.logger.debug(u'Get %ss (total:%s): %s' % 
                          (self.entity, total, truncate(query)))
        return query, total

class AbstractDbManager(object):
    """Abstarct db manager
    """
    def __init__(self, session=None):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)        
        
        self._session = session

    def __del__(self):
        pass

    def __repr__(self):
        return u"<%s id='%s'>" % (self.__class__.__name__, id(self))

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
            logger.info(u'Create tables on : %s' % (db_uri))
            del engine
        except exc.DBAPIError, e:
            raise Exception(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.drop_all(engine)
            logger.info(u'Remove tables from : %s' % (db_uri))
            del engine
        except exc.DBAPIError, e:
            raise Exception(e)

    @staticmethod
    def set_initial_data(self):
        """Set initial data.
        """
        pass
    
    def print_stmp(self, stmp):
        """
        """
        self.logger.debug(u'stmp: %s' % stmp.statement.compile(dialect=mysql.dialect()))
    
    @query
    def count_entities(self, entityclass):
        """Get model entity count.
        
        :return: entity count
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(entityclass).count()
            
        self.logger.debug(u'Count %s: %s' % (entityclass.__name__, res))
        return res    
    
    def query_entities(self, entityclass, session, oid=None, objid=None, 
                       uuid=None, name=None, *args, **kvargs):
        """Get model entities query
        
        :param entityclass: entity model class
        :param session: db session
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :return: list of entityclass
        :raises ModelError: raise :class:`ModelError`      
        """
        #session = self.get_session()
        if oid is not None:
            query = session.query(entityclass).filter_by(id=oid)
        elif objid is not None:  
            query = session.query(entityclass).filter_by(objid=objid)
        elif uuid is not None:  
            query = session.query(entityclass).filter_by(uuid=uuid)
        elif name is not None:
            query = session.query(entityclass).filter_by(name=name)            
        else:
            query = session.query(entityclass)
        
        entity = query.first()
        
        if entity is None:
            msg = u'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)
                 
        self.logger.debug(u'Get %s: %s' % (entityclass.__name__, truncate(entity)))
        return entity
    
    @query
    def get_entity(self, entityclass, oid):
        """Parse oid and get entity entity by name or by model id or by uuid
        
        :param entityclass: entity model class
        :param oid: entity model id or name or uuid        
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'\
                 u'[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            entity = self.query_entities(entityclass, session, uuid=oid)
        # get obj by id
        elif match(u'[0-9]+', str(oid)):
            entity = self.query_entities(entityclass, session, oid=oid)
        # get obj by name
        else:
            entity = self.query_entities(entityclass, session, name=oid)
        return entity
    
    @query
    def get_entities(self, entityclass, filters, *args, **kvargs):
        """Get model entities
        
        :param entityclass: entity model class
        :param filters: entity model filters function. Return qury with 
            additional filter
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :param args: custom params
        :param kvargs: custom params         
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        query = self.query_entities(entityclass, session, *args, **kvargs)
        query = filters(query, *args, **kvargs)

        # make query
        res = query.all()
        self.logger.debug(u'Get %s: %s' % (entityclass.__name__, truncate(res)))
        return res 
    
    '''
    @query
    def get_paginated_entities(self, entityclass, filters, page=0, size=10,
                               order=u'DESC', field=u'id', *args, **kvargs):
        """Get model entities using pagination
        
        :param entityclass: entity model class
        :param filters: entity model filters function
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :param args: custom params
        :param kvargs: custom params 
        :param page: entities list page to show [default=0]
        :param size: number of entities to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        query = self.query_entities(entityclass, session, *args, **kvargs)
        query = filters(query, *args, **kvargs)       
        
        # get total
        total = query.count()
        
        # paginate query
        start = size * page
        end = size * (page + 1)
        res = query.order_by(u'%s %s' % (field, order))[start:end]
        self.logger.debug(u'Get %s (%s, %s): %s' % (entityclass.__name__, 
                                                    args, kvargs, truncate(res)))
        return res, total
    '''
    
    @query
    def get_paginated_entities(self, entity, tags=[], page=0, size=10, 
            order=u'DESC', field=u'id', filters=[], other_fields=[], 
            *args, **kvargs):
        """Get entities associated with some permission tags
        
        :param filters: sql filters to apply [optional]
        :param other_fields: other fields to return [optional]
        :param args: custom params
        :param kvargs: custom params        
        :param entity: entity
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
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        
        query = PaginatedQueryGenerator(entity, session)
        # set filters
        if u'name' in kvargs:
            query.add_filter(u'AND t3.name=:name')        
        if u'active' in kvargs:
            query.add_filter(u'AND t3.active=:active')
        if u'creation_date' in kvargs:
            query.add_filter(u'AND t3.creation_date=:creation_date')
        if u'modification_date' in kvargs:
            query.add_filter(u'AND t3.modification_date=:modification_date') 
        #if u'expiry_date' in kvargs:
        #    query.add_filter(u'AND expiry_date=:expiry_date') 
        for item in filters:
            query.add_filter(item)
        query.add_fields(other_fields)
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, *args, **kvargs)
        return res
    
    @netsted_transaction
    def add_entity(self, entityclass, *args, **kvargs):
        """Add an entity.
        
        :param entityclass: entity model class
        :param value str: entity value.
        :param desc str: desc
        :return: new entity
        :rtype: Oauth2entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        # create entity
        record = entityclass(*args, **kvargs)
        session.add(record)
        session.flush()
        
        self.logger.debug(u'Add %s: %s' % (entityclass, record))
        return record
    
    @netsted_transaction
    def update_entity(self, entityclass, *args, **kvargs):
        """Update entity.

        :param entityclass: entity model class
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :param kvargs str: date to update. [optional]
        :return: entity
        :raises TransactionError: raise :class:`TransactionError`        
        """        
        session = self.get_session()
        
        # get entity
        query = self.query_entities(entityclass, session, **kvargs)
        kvargs.pop(u'oid', None)
        kvargs.pop(u'uuid', None)
        kvargs.pop(u'objid', None)
        #kvargs.pop(u'name', None)
        
        for k,v in kvargs.items():
            if v is None:
                kvargs.pop(k)
        
        # create data dict with update
        entity = query
        kvargs[u'modification_date'] = datetime.today()
        res = entity.update(kvargs)
            
        self.logger.debug(u'Update %s %s with data: %s' % 
                          (entityclass.__name__, entity.first().id, kvargs))
        return entity.first().id
    
    @netsted_transaction
    def remove_entity(self, entityclass, *args, **kvargs):
        """Remove entity.
        
        :param entityclass: entity model class
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :return: entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        query = self.query_entities(entityclass, session, **kvargs)
        
        # delete entity
        entity = query.first()
        session.delete(entity)
        
        self.logger.debug(u'Remove %s %s' % (entityclass.__name__, entity.id))
        return entity.id
    
    #
    # permission tag
    #
    def hash_from_permission(self, objdef, objid):
        """Get hash from entity permission (objdef, objid)
        
        :param objdef: enitity permission object type definition
        :param objid: enitity permission object id
        """
        perm = u'%s-%s' % (objdef, objid)
        tag = hashlib.md5(perm).hexdigest()
        return tag
    
    @netsted_transaction
    def add_perm_tag(self, tag, explain, entity, type, *args, **kvargs):
        """Add permission tag and entity association.
        
        :param tag: tag
        :param explain: tag explain
        :param entity: entity id
        :param type: entity type
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        try:
            # create tag
            tagrecord = PermTag(tag, explain=explain)
            session.add(tagrecord)
            session.flush()
            self.logger.debug(u'Add tag %s' % (tagrecord))
        except:
            # get tag already created
            self.logger.warn(u'Tag %s already exists' % (tagrecord))
            session.rollback()
            tagrecord = session.query(PermTag).filter_by(value=tag).first()

        # create tag entity association
        try:
            record = PermTagEntity(tagrecord.id, entity, type)
            session.add(record)
            #session.flush()
            self.logger.debug(u'Add tag %s entity %s association' % (tag, entity))
        except:
            self.logger.debug(u'Tag %s entity %s association already exists' % (tag, entity))
        
        return record
    
    @netsted_transaction
    def delete_perm_tag(self, entity, type):
        """Remove permission tag entity association.
        
        :param entity: entity id
        :param type: entity type
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        # create tag entity association
        items = session.query(PermTagEntity)\
                       .filter_by(entity=entity)\
                       .filter_by(type=type).all()
        for item in items:
            session.delete(item)
        self.logger.debug(u'Delete tag entity %s.%s association' % (entity, type))
        
        # TODO: remove unused tag
        
        return True
    