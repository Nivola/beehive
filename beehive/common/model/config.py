'''
Created on Jan 31, 2014

@author: darkbk
'''
import logging
from datetime import datetime
from beehive.common.data import transaction, query, operation
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from beehive.common.model import AbstractDbManager

Base = declarative_base()

logger = logging.getLogger(__name__)

class ConfigProp(Base):
    """Model mapping for configuration table
    """
    __tablename__ = 'configuration'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    app = Column(String(30), nullable=False, unique=False)
    group = Column(String(30), nullable=False, unique=False)
    name = Column(String(30), nullable=False, unique=True)
    value = Column(String(3000), nullable=True)
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    
    def __init__(self, app, group, name, value):
        self.app = app
        self.group = group
        self.name = name
        self.value = value
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date

    def __repr__(self):
        return "ConfigProp(%s, %s, %s, %s, %s)" % (self.id, self.app, self.group, 
                                                 self.name, self.value)

class ConfigDbManagerError(Exception): pass
class ConfigDbManager(AbstractDbManager):
    """Db Manager used to manage configuration tables
    """
    def __init__(self, session=None):
        AbstractDbManager.__init__(self, session)
        
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
        
    @transaction
    def set_initial_data(self):
        session = self.get_session()
        # set host type
        """
        data = [HostType('vSphere-vCenter'),
                HostType('vSphere-esxi'),
                HostType('qemu-kvm'),
                HostType('xen'),
                HostType('hyperv'),
                HostType('cloudstack-mgmt'),]
        """
        data = []
        session.add_all(data)

    @query    
    def get(self, app=None, group=None, oid=None, name=None):
        """Get configuration properties.
        
        :param app: property app [optional]
        :param group: property group [optional]
        :param oid: property id [optional]
        :param name: property name [optional]
        :return: list of :class:`ConfigProp`
        :raises: :class:`gibbonutil.db.QueryError`
        """           
        session = self.get_session()
        if oid is not None:
            prop = session.query(ConfigProp).filter_by(id=oid).all()
        elif name is not None:
            prop = session.query(ConfigProp).filter_by(name=name).all()
        elif app is not None or group is not None:
            query = session.query(ConfigProp)
            if app is not None:
                query = query.filter_by(app=app)
            if group is not None:
                query = query.filter_by(group=group)
            prop = query.all()
        else:
            prop = session.query(ConfigProp).all()
            
        if len(prop) == 0:
            self.logger.warn(u'No properties (app=%s, group=%s, '\
                             u'oid=%s, name=%s) found' % 
                             (app, group, oid, name)) 
            raise SQLAlchemyError(u'No properties (app=%s, group=%s, '\
                                  u'oid=%s, name=%s) found' % 
                                  (app, group, oid, name))
            
        self.logger.debug(u'Get properties: %s' % prop)
        return prop
        
    @transaction
    def add(self, app, group, name, value):
        """Add new property.

        :param app: app name
        :param group: group name       
        :param name: property name
        :param value: property value
        :return: :class:`ConfigProp`
        :raises: :class:`gibbonutil.db.TransactionError`
        """        
        session = self.get_session()
        prop = ConfigProp(app, group, name, value)
        session.add(prop)
        session.flush()
        
        self.logger.debug('Add property: %s' % prop)
        return prop
    
    @transaction
    def update(self, name, value):
        """Update property.

        :param name: property name
        :param value: property value
        :return: :class:`ConfigProp`
        :raises: :class:`gibbonutil.db.TransactionError`
        """        
        session = self.get_session()
        modification_date = datetime.today()
        res = session.query(ConfigProp).filter_by(name=name)\
                                       .update({"value":value,
                                                "modification_date":modification_date})
            
        self.logger.debug('Set property "%s:%s"' % (name, value))
        return res
        
    @transaction
    def delete(self, oid=None, name=None):
        """Delete property.

        :param oid: property id
        :param name: property name
        :param value: property value
        :return: delete response
        :raises: :class:`gibbonutil.db.TransactionError`
        """        
        session = self.get_session()
        if oid is not None:
            prop = session.query(ConfigProp).filter_by(id=oid).first()
        elif name is not None:
            prop = session.query(ConfigProp).filter_by(name=name).first()
        else:
            self.logger.error("Specify at least oid or name")
            raise SQLAlchemyError("Specify at least oid or name")

        if prop is None:
            self.logger.error("No property found")
            raise SQLAlchemyError("No property found")  
        
        res = session.delete(prop)
            
        self.logger.debug('Delete property: %s' % prop)
        return res