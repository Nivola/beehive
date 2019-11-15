# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import ujson as json
import logging
from re import match
from six import b
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import create_engine, exc
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import distinct, desc
from beecell.simple import truncate
from beehive.common.data import query
from beehive.common.model import AbstractDbManager, PaginatedQueryGenerator
from beecell.db import ModelError

Base = declarative_base()

logger = logging.getLogger(__name__)


class DbEvent(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    event_id = Column(String(40))
    type = Column(String(150))
    objid = Column(String(400))
    objdef = Column(String(500))
    objtype = Column(String(45))
    creation = Column(DATETIME(fsp=6))
    data = Column(String(5000), nullable=True)
    source = Column(String(200), nullable=True)
    dest = Column(String(500), nullable=True)
    
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
        return "<DbEvent event_id=%s, type=%s, objid=%s, data=%s)>" % (\
                    self.event_id, self.type, self.objid, self.data)


class EventDbManager(AbstractDbManager):
    """
    """
    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table"
        statements in raw SQL."""
        AbstractDbManager.create_table(db_uri)
        
        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=1;")
            Base.metadata.create_all(engine)
            logger.info('Create tables on : %s' % (db_uri))
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        AbstractDbManager.remove_table(db_uri)
        
        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=0;")
            Base.metadata.drop_all(engine)
            logger.info('Remove tables from : %s' % (db_uri))
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)    
    
    @query
    def get_types(self):
        """Get event types. 
        
        :raise QueryError: if query return error
        """
        session = self.get_session()
        query = session.query(distinct(DbEvent.type)).all()
        res = [i[0] for i in query]
        
        if len(res) == 0:
            self.logger.error('No event types found')
            raise SQLAlchemyError('No event types found')            
        
        self.logger.debug('Get event types: %s' % truncate(res))
        
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
            self.logger.error('No entity definitions found')
            raise SQLAlchemyError('No entity definitions found')            
        
        self.logger.debug('Get entity definitions: %s' % truncate(res))
        
        return res    

    def get_event(self, oid):
        """Method used by authentication manager
        
        :param oid: can be db id or event_id
        :return: DbEvent instance
        """
        session = self.get_session()
        
        # get obj by uuid
        if match('[0-9a-z]+', b(oid)):
            query = session.query(DbEvent).filter_by(event_id=oid)
        # get obj by id
        elif match('[0-9]+', b(oid)):
            query = session.query(DbEvent).filter_by(id=oid)

        entity = query.first()
        
        if entity is None:
            msg = 'No event found'
            self.logger.error(msg)
            raise ModelError(msg, code=404)
                 
        self.logger.debug('Get event: %s' % (truncate(entity)))
        return entity

    @query
    def get_events(self, tags=[], page=0, size=10, order='DESC', field='id', with_perm_tag=None, *args, **kvargs):
        """Get events with some permission tags
        
        :param type: event type [optional]
        :param objid: objid [optional]
        :param objtype: objtype [optional]
        :param objdef: objdef [optional]
        :param data: event data [optional]
        :param source: event source [optional]
        :param dest: event destinatiaion [optional]
        :param datefrom: event data from. Ex. '2015-3-9-15-23-56' [optional]
        :param dateto: event data to. Ex. '2015-3-9-15-23-56' [optional]
        :param tags: list of permission tags
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param args: custom params
        :param kvargs: custom params
        :param with_perm_tag: if False disable authorization
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        query = PaginatedQueryGenerator(DbEvent, self.get_session(), with_perm_tag=with_perm_tag)

        # set filters
        query.add_relative_filter('AND t3.type = :type', 'type', kvargs)
        query.add_relative_filter('AND t3.objid like :objid', 'objid', kvargs)
        query.add_relative_filter('AND t3.objtype like :objtype', 'objtype', kvargs)
        query.add_relative_filter('AND t3.objdef like :objdef', 'objdef', kvargs)
        query.add_relative_filter('AND t3.data like :data', 'data', kvargs)
        query.add_relative_filter('AND t3.source like :source', 'source', kvargs)
        query.add_relative_filter('AND t3.dest like :dest', 'dest', kvargs)
        query.add_relative_filter('AND t3.creation >= :datefrom', 'datefrom', kvargs)
        query.add_relative_filter('AND t3.creation <= :dateto', 'dateto', kvargs)

        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, *args, **kvargs)
        return res

    '''
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
        '''

    def add(self, eventid, etype, objid, objdef, objtype, creation, data, source, dest):
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
        res = None

        # add event
        if objid is not None:
            data = truncate(json.dumps(data), size=4000)
            res = self.add_entity(DbEvent, eventid, etype, objid, objdef, objtype, creation, data, json.dumps(source),
                                  json.dumps(dest))

            # add permtag
            ids = self.get_all_valid_objids(objid.split('//'))
            for i in ids:
                perm = '%s-%s' % (objdef.lower(), i)
                tag = self.hash_from_permission(objdef.lower(), i)
                self.add_perm_tag(tag, perm, res.id, 'event')
        
        return res
