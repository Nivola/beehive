'''
Created on Mar 2, 2015

@author: darkbk

https://learning-0mq-with-pyzmq.readthedocs.org/en/latest/
http://zeromq.github.io/pyzmq/
'''
import ujson as json
import logging
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import distinct, desc
from beecell.simple import truncate
from beehive.common.data import operation, query, transaction

Base = declarative_base()

logger = logging.getLogger(__name__)

class DbEvent(Base):
    __tablename__ = 'event'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(40))
    type = Column(String(150))
    objid = Column(String(400))
    objdef = Column(String(500))
    objtype = Column(String(45))
    creation = Column(DateTime())
    data = Column(String(5000), nullable=True)
    source = Column(String(200), nullable=True)
    dest = Column(String(200), nullable=True)
    
    def __init__(self, eventid, etype, objid, objdef, objtype, creation, data, 
                 source, dest):
        """
        :param eventid: event id
        :param etype: event type
        :param objid: event object id
        :param objdef: event object definition
        :param objtype: event object objtype
        :param creation: creation time
        :param data: operation data
        :param source: event source
        :param dest: event destionation
        """
        self.event_id = eventid
        self.type = etype
        self.objid = objid
        self.objdef = objdef
        self.objtype = objtype
        self.creation = creation
        self.data = data
        self.source = source
        self.dest = dest

    def __repr__(self):
        return "<DbEvent(%s, %s, %s, %s)>" % (self.event_id, self.type, 
                                              self.objid, self.data)

class EventDbManagerError(Exception): pass
class EventDbManager(object):
    """
    """
    def __init__(self, session=None):
        """ """
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)          
        
        self._session = session
    
    def __repr__(self):
        return "<EventDbManager id='%s'>" % id(self)
    
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
            logger.info('Create event tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise EventDbManagerError(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.drop_all(engine)
            logger.info('Remove event tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise EventDbManagerError(e)    
    
    def set_initial_data(self):
        pass

    @query
    def get_types(self):
        """Get event types. 
        
        :raise QueryError: if query return error
        """
        session = self.get_session()
        query = session.query(distinct(DbEvent.type)).all()
        res = [i[0] for i in query]
        
        if len(res) == 0:
            self.logger.error(u'No event types found')
            raise SQLAlchemyError(u'No event types found')            
        
        self.logger.debug(u'Get event types: %s' % truncate(res))
        
        return res
    
    @query
    def get_entity_definitions(self):
        """Get event entity definition. 
        
        :raise QueryError: if query return error
        """
        session = self.get_session()
        query = session.query(distinct(DbEvent.objdef)).all()
        res = [i[0].lower() for i in query]
        
        if len(res) == 0:
            self.logger.error(u'No entity definitions found')
            raise SQLAlchemyError(u'No entity definitions found')            
        
        self.logger.debug(u'Get entity definitions: %s' % truncate(res))
        
        return res    

    @query
    def gets(self, oid=None, etype=None, data=None, 
                   source=None, dest=None, datefrom=None, dateto=None,
                   page=0, size=10, objid=None, objdef=None, objtype=None):
        """Get events. 
        
        :param oid str: event oid [optional]
        :param etype str: list of event type [optional]
        :param data str: event data [optional]
        :param source str: event source [optional]
        :param dest str: event destinatiaion [optional]
        :param datefrom: event data from. Ex. '2015-3-9-15-23-56' [optional]
        :param dateto: event data to. Ex. '2015-3-9-15-23-56' [optional]
        :param page: event list page to show [default=0]
        :param size: number of event to show in list per page [default=0]
        :param objid str: entity id [optional]
        :param objtype str: entity type [optional]
        :param objdef str: entity definition [optional]
        :raise QueryError: if query return error
        """
        session = self.get_session()
        if oid is not None:
            query = session.query(DbEvent).filter_by(event_id=oid)
            count = query.count()
            res = query.all()
        else:
            query = session.query(DbEvent)
            if etype is not None:
                query = query.filter(DbEvent.type.in_(etype))
            if objid is not None:
                query = query.filter(DbEvent.objid.like(objid))
            if objtype is not None:
                query = query.filter(DbEvent.objtype.like(objtype))
            if objdef is not None:
                query = query.filter(DbEvent.objdef.like(objdef))
            if data is not None:
                query = query.filter(DbEvent.data.like('%'+data+'%'))
            if source is not None:
                query = query.filter(DbEvent.source.like('%'+source+'%'))
            if dest is not None:
                query = query.filter(DbEvent.dest.like('%'+dest+'%'))
            if datefrom is not None:
                query = query.filter(DbEvent.creation >= datefrom)
            if dateto is not None:
                query = query.filter(DbEvent.creation <= dateto)
            
            count = query.count()
            
            start = size * page
            end = size * (page+1)
            res = query.order_by(DbEvent.creation.desc())[start:end]
        
        self.logger.debug('Get events count: %s' % count)
        
        if count == 0:
            self.logger.error("No events found")
            raise SQLAlchemyError("No events found")            
        
        self.logger.debug('Get events: %s' % truncate(res))
        
        return count, res

    @transaction
    def add(self, eventid, etype, objid, objdef, objtype, creation, data, 
            source, dest):
        """Add new event.
        
        :param eventid: event id
        :param etype: event type
        :param objid: event object id
        :param objdef: event object definition
        :param objtype: event object objtype
        :param creation: creation time
        :param data: operation data
        :param source: event source
        :param dest: event destionation
        :raise TransactionError: if transaction return error
        """        
        session = self.get_session()
        e = DbEvent(eventid, etype, objid, objdef, objtype, creation, 
                    json.dumps(data), json.dumps(source), json.dumps(dest))
        session.add(e)
            
        self.logger.debug(u'Add event: %s' % truncate(e))
        return e