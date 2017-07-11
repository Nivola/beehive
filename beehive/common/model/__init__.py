import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from beehive.common.data import operation, query, transaction
from beecell.simple import truncate
from beecell.db import ModelError
from beecell.perf import watch
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, Index
from sqlalchemy.sql import text
import hashlib

Base = declarative_base()

logger = logging.getLogger(__name__)

class PermTag(Base):
    __tablename__ = u'perm_tag'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    value = Column(String(100), unique = True)
    explain = Column(String(400))
    
    def __init__(self, value, explain=None):
        """Create new permission tag
        
        :param value: tag value
        """
        self.value = value
        self.explain = explain
    
    def __repr__(self):
        return u'<PermTag(%s, %s)>' % (self.id, self.value)
    
class PermTagEntity(Base):
    __tablename__ = u'perm_tag_entity'
    __table_args__ = {u'mysql_engine':u'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    tag = Column(Integer)
    entity = Column(Integer)
    table = Column(String(50))
    
    __table_args__ = (
        Index(u'idx_tag_entity', u'tag', u'entity', unique=True),
    )    
    
    def __init__(self, tag, entity, table):
        """Create new permission tag entity association
        
        :param tag: tag id
        :param entity: entity id
        :param table: entity table
        """
        self.tag = tag
        self.entity = entity
        self.table = table
    
    def __repr__(self):
        return u'<PermTagEntity(%s, %s, %s, %s)>' % (self.id, self.tag, 
                                                     self.entity, self.table)

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
    
    @query
    def count_entites(self, entityclass):
        """Get model entity count.
        
        :return: entity count
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(entityclass).count()
            
        self.logger.debug(u'Count %s: %s' % (entityclass.__name__, res))
        return res    
    
    @watch
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
        session = self.get_session()
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
        return query
    
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
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
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
        
        # get paginator fields
        #page = kvargs.get(u'page', None)
        #size = kvargs.get(u'size', None)
        #order = kvargs.get(u'order', None)
        #field = kvargs.get(u'field', None)  
        
        # paginate query
        start = size * page
        end = size * (page + 1)
        res = query.order_by(u'%s %s' % (field, order))[start:end]
        self.logger.debug(u'Get %s (%s, %s): %s' % (entityclass.__name__, 
                                                    args, kvargs, truncate(res)))
        return res, total    
    
    @transaction
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
    
    @transaction
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
    
    @transaction
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
    
    @transaction
    def add_perm_tag(self, tag, explain, entity, table, *args, **kvargs):
        """Add permission tag and entity association.
        
        :param tag: tag
        :param explain: tag explain
        :param entity: entity id
        :param table: entity table
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
            record = PermTagEntity(tagrecord.id, entity, table)
            session.add(record)
            #session.flush()
            self.logger.debug(u'Add tag %s entity %s association' % (tag, entity))
        except:
            self.logger.debug(u'Tag %s entity %s association already exists' % (tag, entity))
        
        return record
    
    @query
    def get_tagged_entities(self, entityclass, tags, efilter=u'', 
                            page=0, size=10, order=u'DESC', field=u'id', 
                            *args, **kvargs):
        """Get entities associated with some permission tags
        
        :param entityclass: entity model class
        :param args: custom params
        :param kvargs: custom params         
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        
        sql = [u'SELECT t3.*',
               u'FROM perm_tag t1, perm_tag_entity t2, %s t3',
               u'WHERE t3.id=t2.entity AND t2.tag=t1.id',
               u'AND t1.value IN :tags',
               efilter,
               u'GROUP BY id',
               u'ORDER BY %s %s']
        smtp = text(u' '.join(sql) % (entityclass, field, order))

        query = session.query(u'id', u'uuid', u'objid', u'name', u'ext_id', 
                              u'desc', u'attribute', u'creation_date', 
                              u'modification_date', u'type_id', u'container_id', 
                              u'active', u'parent_id').\
                from_statement(smtp).\
                params(tags=tags)
        
        #query = self.query_entities(entityclass, session, *args, **kvargs)
        #query = filters(query, *args, **kvargs)

        # make query
        start = size * page
        end = size * (page + 1)

        total = query.count()    
        res = query[start:end]
        self.logger.debug(u'Get %ss: %s' % (entityclass, truncate(res)))
        return res

    
    