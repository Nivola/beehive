# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from beehive.common.model import AbstractDbManager, BaseEntity
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()
from beehive.common.model.authorization import Base

logger = logging.getLogger(__name__)


class Catalog(Base, BaseEntity):
    __tablename__ = 'catalog'
    
    zone = Column(String(50), nullable=False)
    
    def __init__(self, objid, name, desc, zone, active=True):
        BaseEntity.__init__(self, objid, name, desc, active)

        self.zone = zone


class CatalogEndpoint(Base, BaseEntity):
    __tablename__ = 'catalog_endpoint'

    catalog_id = Column(Integer(), ForeignKey('catalog.id'))
    catalog = relationship("Catalog")
    service = Column(String(30), nullable=False)
    uri = Column(String(100), nullable=False)
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    
    def __init__(self, objid, name, service, desc, catalog, uri, active=True):
        BaseEntity.__init__(self, objid, name, desc, active)
        
        self.service = service
        self.desc = desc
        self.catalog_id = catalog
        self.uri = uri

    def __repr__(self):
        return '<CatalogEndpoint id=%s, uuid=%s, obid=%s, name=%s, service=%s, catalog=%s, active=%s, >' % (
            self.id, self.uuid, self.objid, self.name, self.service, self.catalog, self.active)


class CatalogDbManager(AbstractDbManager):
    """Catalog db manager

    :param session: sqlalchemy session
    """

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table" statements in raw SQL

        :param db_uri: db uri
        """
        try:
            engine = create_engine(db_uri)
            engine.execute('SET FOREIGN_KEY_CHECKS=1;')
            Base.metadata.create_all(engine)
            logger.info('Create tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    @staticmethod
    def remove_table(db_uri):
        """Remove all tables in the engine. This is equivalent to "Drop Table" statements in raw SQL

        :param db_uri: db uri
        """
        try:
            engine = create_engine(db_uri)
            engine.execute('SET FOREIGN_KEY_CHECKS=0;')
            Base.metadata.drop_all(engine)
            logger.info('Remove tables from : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    #
    # catalog
    #
    def get(self, *args, **kvargs):
        """Get catalog.
        
        :param tags: list of permission tags
        :param name: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param expiry_date: expiry_date [optional]
        :param zone: catalog zone. Value like internal or external [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of Catalog     
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if 'zone' in kvargs and kvargs.get('zone') is not None:
            filters = ['AND zone=:zone']
        
        res, total = self.get_paginated_entities(Catalog, filters=filters, *args, **kvargs)
        return res, total
    
    def add(self, objid, name, desc, zone):
        """Add catalog.

        :param objid: authorization id
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
        :param name: catalog name [optional]
        :param desc: catalog description [optional]
        :param zone: catalog zone. Value like internal or external
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(Catalog, *args, **kvargs)
        return res  
    
    def delete(self, *args, **kvargs):
        """Remove catalog.
        :param int oid: entity id. [optional]
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(Catalog, *args, **kvargs)
        return res
    
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
        :param catalog: catalog id [optional]
        :param service: service name [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of :class:`CatalogEndpoint`            
        :raises QueryError: raise :class:`QueryError`
        """
        filters = []
        if 'service' in kvargs and kvargs.get('service') is not None:
            filters.append('AND service=:service')
        if 'catalog' in kvargs and kvargs.get('catalog') is not None:
            filters.append('AND catalog_id=:catalog')        
        
        res, total = self.get_paginated_entities(CatalogEndpoint, filters=filters, *args, **kvargs)
        return res, total    
        
    def add_endpoint(self, objid, name, service, desc, catalog, uri, active=True):
        """Add endpoint.
  
        :param objid: endpoint objid
        :param name: endpoint name
        :param service: service
        :param desc: endpoint description
        :param catalog: instance of Catalog
        :param uri: endpoint uri
        :param active: endpoint state: True or False
        :return: :class:`CatalogEndpoint`
        :raises TransactionError: raise :class:`TransactionError`
        """        
        res = self.add_entity(CatalogEndpoint, objid, name, service, desc, catalog, uri, active)
        return res
    
    def update_endpoint(self, *args, **kvargs):
        """Update catalog endpoint.

        :param int oid: entity id. [optional]
        :param name: endpoint name [optional]
        :param desc: endpoint description [optional]
        :param service: service service [optional]
        :param uri: endpoint uri [optional]
        :param active: endpoint active [optional]
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.update_entity(CatalogEndpoint, *args, **kvargs)
        return res  
    
    def delete_endpoint(self, *args, **kvargs):
        """Remove catalog endpoint.

        :param int oid: entity id. [optional]
        :return: :class:`Catalog`
        :raises TransactionError: raise :class:`TransactionError`
        """
        res = self.remove_entity(CatalogEndpoint, *args, **kvargs)
        return res        
