'''
Created on Jan 31, 2014

@author: darkbk
'''
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from beecell.db import ModelError
from uuid import uuid4
from beehive.common.data import operation, transaction, query

Base = declarative_base()

logger = logging.getLogger(__name__)

class Catalog(Base):
    __tablename__ = 'catalog'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(30), unique=True, nullable=False)
    desc = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    
    def __init__(self, objid, name, desc, zone):
        self.uuid = str(uuid4())
        self.objid = objid
        self.name = name
        self.desc = desc
        self.zone = zone
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date

    def __repr__(self):
        return "Catalog(%s, %s)" % (self.id, self.name)

class CatalogEndpoint(Base):
    __tablename__ = 'catalog_endpoint'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique = True)
    objid = Column(String(400))
    catalog_id = Column(Integer(), ForeignKey('catalog.id'))
    catalog = relationship("Catalog")
    name = Column(String(50), nullable=False, unique=True)
    service = Column(String(30), nullable=False)
    desc = Column(String(100), nullable=False)
    uri = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False)
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    
    def __init__(self, objid, name, service, desc, catalog, uri, enabled=True):
        self.uuid = str(uuid4())
        self.objid = objid
        self.name = name
        self.service = service
        self.desc = desc
        self.catalog_id = catalog
        self.uri = uri
        self.enabled = enabled
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date

    def __repr__(self):
        return "service(%s, %s, %s, %s)" % (self.id, self.name, self.service, 
                                            self.catalog)

class CatalogDbManagerError(Exception): pass
class CatalogDbManager(object):
    """
    """
    logger = logging.getLogger('gibbon.cloudapi.db')
    
    def __init__(self, session=None):
        """ """
        self._session = session
    
    def __repr__(self):
        return "<CatalogDbManager id='%s'>" % id(self)
    
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
            logger.info('Create catalog tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise CatalogDbManagerError(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.drop_all(engine)
            logger.info('Remove catalog tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise CatalogDbManagerError(e)
        
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

    #
    # catalog
    #
    @query
    def count(self):
        """Get catalogs count.
        
        :rtype: int
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(Catalog).count()

        self.logger.debug('Get catalogs count: %s' % res)
        return res     
    
    @query    
    def get(self, oid=None, objid=None, uuid=None, name=None, zone=None):
        """Get catalog.
        
        Raise QueryError if query return error.
        
        :param oid: catalog id [optional]
        :param objid: catalog objid [optional]
        :param uuid: catalog uuid [optional]
        :param name: catalog name [optional]
        :param zone: catalog zone. Value like internal or external
        :return: list of :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """           
        session = self.get_session()
        query = session.query(Catalog)
        if oid is not None:
            query = query.filter_by(id=oid)
        if objid is not None:
            query = query.filter_by(objid=objid)
        if uuid is not None:
            query = query.filter_by(uuid=uuid)            
        if name is not None:
            query = query.filter_by(name=name)
        if zone is not None:
            query = query.filter_by(zone=zone)
        
        res = query.all()
        
        if len(res) == 0:
            self.logger.error(u'No catalogs found')
            raise SQLAlchemyError(u'No catalogs found')            
            
        self.logger.debug('Get catalogs: %s' % res)
        return res
        
    @transaction
    def add(self, objid, name, desc, zone):
        """Add catalog.
  
        :param name: catalog name
        :param desc: catalog description
        :param zone: catalog zone. Value like internal or external
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        cat = Catalog(objid, name, desc, zone)
        session.add(cat)
        session.flush()
        
        self.logger.debug('Add catalog: %s' % cat)
        return cat
    
    @transaction
    def update(self, oid=None, name=None, new_name=None, new_desc=None, 
               new_zone=None):
        """Update catalog.

        :param oid: catalog id [optional]
        :param name: catalog name [optional]
        :param new_name: catalog name [optional]
        :param new_desc: catalog description [optional]
        :param new_zone: catalog zone. Value like internal or external
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        if oid is not None:
            obj = session.query(Catalog).filter_by(id=oid)
        elif name is not None:
            obj = session.query(Catalog).filter_by(name=name)
        else:
            self.logger.error("Specify at least oid or name")
            raise SQLAlchemyError("Specify at least oid or name")        
        
        data = {'modification_date':datetime.today()}
        if new_name is not None:
            data['name'] = new_name
        if new_desc is not None:
            data['desc'] = new_desc
        if new_zone is not None:
            data['zone'] = new_zone          
        res = obj.update(data)
            
        self.logger.debug('Update catalog %s, %s : %s' % (oid, name, data))
        return res
        
    @transaction
    def delete(self, oid=None, name=None):
        """Delete catalog.

        :param oid: catalog id
        :param name: catalog name
        :return: delete response
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        if oid is not None:
            obj = session.query(Catalog).filter_by(id=oid).first()
        elif name is not None:
            obj = session.query(Catalog).filter_by(name=name).first()
        else:
            self.logger.error("Specify at least oid or name")
            raise SQLAlchemyError("Specify at least oid or name")

        if obj is None:
            self.logger.error("No catalog found")
            raise SQLAlchemyError("No catalog found")  
        
        res = session.delete(obj)
            
        self.logger.debug('Delete catalog: %s' % obj)
        return res
    
    #
    # CatalogEndpoint
    #
    @query
    def count_endpoint(self):
        """Get endpoint count.
        
        :rtype: int
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(CatalogEndpoint).count()

        self.logger.debug('Get endpoint count: %s' % res)
        return res    
    
    @query    
    def get_endpoints(self, oid=None, objid=None, name=None, service=None, 
                     catalog=None):
        """Get endpoint.
        
        Raise QueryError if query return error.
        
        :param oid: endpoint id [optional]
        :param objid: endpoint objid [optional]
        :param name: endpoint name [optional]
        :param service: service service [optional]
        :param catalog: endpoint catalog id [optional]        
        :return: list of :class:`CatalogEndpoint`
        :raises TransactionError: raise :class:`TransactionError`
        """           
        session = self.get_session()
        query = session.query(CatalogEndpoint)
        if oid is not None:
            query = query.filter_by(id=oid)
        if objid is not None:
            query = query.filter_by(objid=objid)
        if name is not None:
            query = query.filter_by(name=name)
        if service is not None:
            query = query.filter_by(service=service)
        if catalog is not None:
            query = query.filter_by(catalog_id=catalog)

        res = query.all()
            
        if len(res) == 0:
            self.logger.error("No endpoint found - (oid:%s, objid:%s, name:%s, service:%s, catalog:%s)" % 
                              (oid, objid, name, service, catalog)) 
            raise SQLAlchemyError("No endpoint found")            
            
        self.logger.debug('Get endpoint: %s' % res)
        return res
        
    @transaction
    def add_endpoint(self, objid, name, service, desc, catalog, uri, enabled=True):
        """Add endpoint.
  
        :param objid: endpoint objid
        :param name: endpoint name
        :param service: service service
        :param desc: endpoint description
        :param catalog: instance of Catalog
        :param uri: endpoint uri
        :param enabled: endpoint state: True or False
        :return: :class:`CatalogEndpoint`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        
        # verify if endpoint already exists
        res = session.query(CatalogEndpoint).filter_by(name=name).first()
        if res is not None:
            self.logger.error("Endpoint %s already exists" % res)
            raise ModelError('Endpoint %s already exists' % res, code=409)
        
        ser = CatalogEndpoint(objid, name, service, desc, catalog, uri, 
                              enabled=enabled)
        session.add(ser)
        session.flush()
        
        self.logger.debug('Add endpoint: %s' % ser)
        return ser
    
    @transaction
    def update_endpoint(self, oid=None, name=None, new_name=None, new_desc=None, 
                       new_service=None, new_catalog=None, new_uri=None, 
                       new_enabled=None, new_objid=None):
        """Update endpoint.

        :param oid: endpoint id [optional]
        :param name: endpoint name [optional]
        :param new_name: endpoint name [optional]
        :param new_desc: endpoint description [optional]
        :param new_service: service service [optional]
        :param new_catalog: endpoint catalog id [optional]
        :param new_uri: endpoint uri [optional]
        :param new_enabled: endpoint enabled [optional]
        :return: :class:`CatalogEndpoint`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        if oid is not None:
            obj = session.query(CatalogEndpoint).filter_by(id=oid)
        elif name is not None:
            obj = session.query(CatalogEndpoint).filter_by(name=name)
        else:
            self.logger.error("Specify at least oid or name")
            raise SQLAlchemyError("Specify at least oid or name")        
        
        data = {'modification_date':datetime.today()}
        if new_name is not None:
            data['name'] = new_name
        if new_desc is not None:
            data['desc'] = new_desc
        if new_service is not None:
            data['service'] = new_service
        if new_catalog is not None:
            data['catalog_id'] = new_catalog
        if new_uri is not None:
            data['uri'] = new_uri
        if new_enabled is not None:
            data['enabled'] = new_enabled
        res = obj.update(data)
            
        self.logger.debug('Update endpoint %s, %s : %s' % (oid, name, data))
        return res
        
    @transaction
    def delete_endpoint(self, oid=None, name=None):
        """Delete endpoint.

        :param oid: endpoint id
        :param name: endpoint name
        :return: delete response
        :raises TransactionError: raise :class:`TransactionError`
        """        
        session = self.get_session()
        if oid is not None:
            obj = session.query(CatalogEndpoint).filter_by(id=oid).first()
        elif name is not None:
            obj = session.query(CatalogEndpoint).filter_by(name=name).first()
        else:
            self.logger.error("Specify at least oid or name")
            raise SQLAlchemyError("Specify at least oid or name")

        if obj is None:
            self.logger.error("No endpoint found")
            raise SQLAlchemyError("No endpoint found")  
        
        res = session.delete(obj)
            
        self.logger.debug('Delete endpoint: %s' % obj)
        return res    
    