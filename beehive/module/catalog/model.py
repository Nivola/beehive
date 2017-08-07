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
from beehive.common.data import operation, netsted_transaction, query
from beehive.common.model import Base, AbstractDbManager, ApiObject

#Base = declarative_base()

logger = logging.getLogger(__name__)

class Catalog(Base, ApiObject):
    __tablename__ = 'catalog'
    
    desc = Column(String(50), nullable=False)
    zone = Column(String(50), nullable=False)
    
    def __init__(self, objid, name, desc, zone, active=True):
        ApiObject.__init__(self, objid, name, desc, active)

        self.zone = zone

    def __repr__(self):
        return "Catalog(%s, %s)" % (self.id, self.name)

class CatalogEndpoint(Base, ApiObject):
    __tablename__ = 'catalog_endpoint'

    catalog_id = Column(Integer(), ForeignKey('catalog.id'))
    catalog = relationship("Catalog")
    service = Column(String(30), nullable=False)
    uri = Column(String(100), nullable=False)
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    
    def __init__(self, objid, name, service, desc, catalog, uri, active=True):
        ApiObject.__init__(self, objid, name, desc, active)
        
        self.service = service
        self.desc = desc
        self.catalog_id = catalog
        self.uri = uri

    def __repr__(self):
        return u'CatalogEndpoint(%s, %s, %s, %s)' % \
                (self.id, self.name, self.service, self.catalog)

class CatalogDbManager(AbstractDbManager):
    """
    """

    #
    # catalog
    #
    def get(self, *args, **kvargs):
        """Get catalog.
        
        Raise QueryError if query return error.
        
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
        :return: list of Catalog     
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if u'zone' in kvargs:
            filters = [u'AND zone=:zone']
        
        res, total = self.get_paginated_entities(Catalog, filters=filters, 
                                                 *args, **kvargs)     
        return res
        #return res, total
    
    def add(self, objid, name, desc, zone):
        """Add catalog.
  
        :param name: catalog name
        :param desc: catalog description
        :param zone: catalog zone. Value like internal or external
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.add_entity(Catalog, objid, name, desc, zone)
        return res
        
    def update(self, *args, **kvargs):
        """Update catalog.

        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name [optional]
        :param new_name: catalog name [optional]
        :param new_desc: catalog description [optional]
        :param new_zone: catalog zone. Value like internal or external
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Catalog, *args, **kvargs)
        return res  
    
    def remove(self, *args, **kvargs):
        """Remove catalog.
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name [optional]
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Catalog, *args, **kvargs)
        return res    
    
    '''
    @netsted_transaction
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
    
    @netsted_transaction
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
        
    @netsted_transaction
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
    '''
    
    #
    # CatalogEndpoint
    #
    def get_endpoints(self, *args, **kvargs):
        """Get endpoints.
        
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
        :return: list of :class:`CatalogEndpoint`            
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if u'service' in kvargs:
            filters.append(u'AND service=:service')
        if u'catalog' in kvargs:
            filters.append(u'AND catalog_id=:catalog')        
        
        res, total = self.get_paginated_entities(CatalogEndpoint, filters=filters, 
                                                 *args, **kvargs)     
        return res
        #return res, total    
        
    def add_endpoint(self, objid, name, service, desc, catalog, uri, active=True):
        """Add endpoint.
  
        :param objid: endpoint objid
        :param name: endpoint name
        :param service: service service
        :param desc: endpoint description
        :param catalog: instance of Catalog
        :param uri: endpoint uri
        :param active: endpoint state: True or False
        :return: :class:`CatalogEndpoint`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        res = self.add_entity(CatalogEndpoint, objid, name, service, desc, 
                              catalog, uri, active)
        return res
    
    '''
    @netsted_transaction
    def update_endpoint(self, oid=None, name=None, new_name=None, new_desc=None, 
                       new_service=None, new_catalog=None, new_uri=None, 
                       new_active=None, new_objid=None):
        """Update endpoint.

        :param oid: endpoint id [optional]
        :param name: endpoint name [optional]
        :param new_name: endpoint name [optional]
        :param new_desc: endpoint description [optional]
        :param new_service: service service [optional]
        :param new_catalog: endpoint catalog id [optional]
        :param new_uri: endpoint uri [optional]
        :param new_active: endpoint active [optional]
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
        if new_active is not None:
            data['active'] = new_active
        res = obj.update(data)
            
        self.logger.debug('Update endpoint %s, %s : %s' % (oid, name, data))
        return res
        
    @netsted_transaction
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
        return res    '''
    