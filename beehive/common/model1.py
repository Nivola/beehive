'''
Created on May 26, 2017

@author: darkbk
'''
import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from beehive.common.data import operation, query, transaction
from beecell.simple import truncate
from beecell.db import ModelError
from beecell.perf import watch
from datetime import datetime

Base = declarative_base()

logger = logging.getLogger(__name__)

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
    