'''
Created on Jan 16, 2014

@author: darkbk
'''
#from beecell.perf import watch
from beecell.simple import import_class, truncate, id_gen, str2uni
from beecell.db import ModelError, QueryError, TransactionError
from beehive.common.apiclient import BeehiveApiClientError
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beehive.module.catalog.model import CatalogDbManager, \
    Catalog as ModelCatalog, CatalogEndpoint as ModelEndpoint
from beehive.common.controller.authorization import BaseAuthController,\
    AuthObject
from beehive.common.data import trace

class CatalogController(BaseAuthController):
    """Catalog Module controller.
    """
    version = u'v1.0'
    
    def __init__(self, module):
        BaseAuthController.__init__(self, module)
        
        self.manager = CatalogDbManager()
        self.child_classes = [Catalog]
        
    def add_container_class(self, name, container_class):
        self.container_classes[name] = container_class

    def get_container_class(self, name):
        return self.container_classes[name]

    @trace(entity=u'Catalog', op=u'insert')
    def add_catalog(self, name=None, desc=None, zone=None):
        """ """
        # check authorization
        objs = self.can('insert', Catalog.objtype, definition=Catalog.objdef)
        if len(objs) > 0 and objs[Catalog.objdef.lower()][0].split('//')[-1] != '*':
            raise ApiManagerError('You need more privileges to add catalog', 
                                  code=2000)
        
        try:
            # create catalog reference
            objid = id_gen()
            catalog = Catalog(self, oid=None, objid=objid, name=name, desc=desc, 
                              active=True, model=None)
            
            res = self.manager.add(objid, name, desc, zone)
            catalog.oid = res.id
            
            # create object and permission
            catalog.register_object([objid], desc=desc)
            
            # create container admin role
            #catalog.add_admin_role(objid, desc)
            
            #Catalog(self).send_event(u'insert', {u'objid':objid, u'name':name})
            return catalog.oid
        except (QueryError, TransactionError) as ex:
            #Catalog(self).send_event(u'insert', {u'objid':objid, u'name':name},
            #                         exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    def count_all_catalogs(self):
        """Get all catalogs count"""
        return self.manager.count_entities(ModelCatalog)

    def count_all_catalog_services(self):
        """Get all catalog services count"""
        return self.manager.count_entities(ModelEndpoint)

    @trace(entity=u'Catalog', op=u'view')
    def get_catalog(self, oid):
        """Get single catalog.

        :param oid: entity model id, name or uuid         
        :return: Catalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Catalog, ModelCatalog, oid) 

    @trace(entity=u'Catalog', op=u'view')
    def get_catalogs(self, *args, **kvargs):
        """Get catalogs.
        
        :param zone: catalog zone. Value like internal or external
        :param name: name like [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: List of catalogs
        :raises ApiManagerError: if query empty return error. 
        """
        def get_entities(*args, **kvargs):
            entities, total = self.manager.get(*args, **kvargs)
            
            return entities, total                    
        
        res, total = self.get_paginated_entities(Catalog, get_entities, 
                                                *args, **kvargs)
        return res, total            
        
    @trace(entity=u'CatalogEndpoint', op=u'view')
    def get_endpoint(self, oid):
        """Get single catalog endpoint.

        :param oid: entity model id or name or uuid         
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(CatalogEndpoint, ModelEndpoint, oid)         
        
    @trace(entity=u'CatalogEndpoint', op=u'view')
    def get_endpoints(self, *args, **kvargs):
        """Get endpoints.

        :param service: endpoint service [optional]
        :param catalog: endpoint catalog [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: List of CatalogEndpoint
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """   
        def get_entities(*args, **kvargs):
            catalogs, total = self.manager.get(*args, **kvargs)
            entities, total = self.manager.get_endpoints(*args, **kvargs)
            catalogs_idx = {i.id:Catalog(self, oid=i.id, objid=i.objid, 
                                         name=i.name, desc=i.desc, active=True, 
                                         model=i) 
                            for i in catalogs}
            for entity in entities:
                entity.set_catalog(catalogs_idx[entity.model.catalog_id])
            
            return entities, total                    
        
        res, total = self.get_paginated_entities(CatalogEndpoint, get_entities, 
                                                 *args, **kvargs)
        return res, total 
        
class Catalog(AuthObject):
    objtype = u'directory'
    objdef = u'Catalog'
    objuri = u'catalog'
    objdesc = u'dir/Catalog'
    
    def __init__(self, *args, **kvargs):
        """ """
        AuthObject.__init__(self, *args, **kvargs)

        if self.model is not None:
            self.zone = self.model.zone
            
        # child classes
        self.child_classes = [CatalogEndpoint]
        
        self.update_object = self.manager.update
        self.delete_object = self.manager.delete

    def info(self):
        """Get object info
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        info.update({u'zone':self.zone})
        return info

    def detail(self):
        """Get object extended info
        
        :return: Dictionary with object detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        info[u'services'] = {}
        for item in self.get_endpoints():
            try:
                info[u'services'][item.service].append(item.endpoint)
            except:
                info[u'services'][item.service] = [item.endpoint]
        return info

    @trace(op=u'endpoints.insert')
    def add_endpoint(self, name, desc, service, uri, active=True):
        """Add endpoint.
        
        :param name: endpoint name
        :param desc: endpoint desc
        :param service: endpoint service
        :param uri: endpoint uri
        :param active: endpoint status
        :return: endpoint id
        :rtype: bool 
        :raises ApiManagerError: raise :class:`ApiManagerError`
        :raises ApiAuthorizationError: raise :class:`ApiAuthorizationError`
        """
        # check authorization
        self.controller.check_authorization(CatalogEndpoint.objtype, 
                                            CatalogEndpoint.objdef, 
                                            self.objid, u'insert')
        
        try:
            # create catalog endpoint reference
            objid = u'%s//%s' % (self.objid, id_gen())            
            res = self.manager.add_endpoint(objid, name, service, desc, self.oid, 
                                            uri, active)
            
            # create object and permission
            CatalogEndpoint(self.controller).register_object(
                objid.split(u'//'), desc=desc)
            
            self.logger.debug(u'Add catalog endpoint: %s' % truncate(res))
            return res.id
        except (QueryError, TransactionError, ModelError) as ex:      
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

class CatalogEndpoint(AuthObject):
    objtype = u'directory'
    objdef = u'Catalog.Endpoint'
    objuri = u'dir/endpoint'
    objdesc = u'Catalog endpoint'
    
    def __init__(self, *args, **kvargs):
        """ """
        AuthObject.__init__(self, *args, **kvargs)
        
        self.catalog = None

        if self.model is not None:
            self.endpoint = self.model.uri
            self.service = self.model.service

        self.update_object = self.manager.update_endpoint
        self.delete_object = self.manager.delete_endpoint

    def set_catalog(self, catalog):
        self.catalog = catalog

    def info(self):
        """Get object info
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        info.update({
            u'catalog':self.catalog.name, 
            u'catalog_id':self.catalog.oid,
            u'service':self.model.service,
            u'endpoint':self.model.uri            
        })
        return info

    def detail(self):
        """Get object extended info
        
        :return: Dictionary with object detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        return info
                