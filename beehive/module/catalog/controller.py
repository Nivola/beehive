# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beecell.simple import truncate, id_gen
from beecell.db import ModelError, QueryError, TransactionError
from beehive.common.apimanager import ApiManagerError
from beehive.module.catalog.model import CatalogDbManager, \
    Catalog as ModelCatalog, CatalogEndpoint as ModelEndpoint
from beehive.common.controller.authorization import BaseAuthController, AuthObject
from beehive.common.data import trace, operation


class CatalogController(BaseAuthController):
    """Catalog Module controller.

    :param module: ApiModule instance
    """
    version = 'v1.0'
    
    def __init__(self, module):
        BaseAuthController.__init__(self, module)
        
        self.manager = CatalogDbManager()
        self.child_classes = [Catalog]

    @trace(entity='Catalog', op='insert')
    def add_catalog(self, name=None, desc=None, zone=None):
        """Add catalog

        :param name: name
        :param desc: description
        :param zone: zone
        :return:
        """
        # check authorization
        self.check_authorization(Catalog.objtype, Catalog.objdef, None, 'insert')
        
        try:
            # create catalog reference
            objid = id_gen()

            res = self.manager.add(objid, name, desc, zone)
            
            # create object and permission
            Catalog(self, oid=res.id).register_object([objid], desc=desc)

            return res.uuid
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    def count_all_catalogs(self):
        """Get all catalogs count"""
        return self.manager.count_entities(ModelCatalog)

    def count_all_catalog_services(self):
        """Get all catalog services count"""
        return self.manager.count_entities(ModelEndpoint)

    @trace(entity='Catalog', op='view')
    def get_catalog(self, oid):
        """Get single catalog.

        :param oid: entity model id, name or uuid         
        :return: Catalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_entity(Catalog, ModelCatalog, oid)

    @trace(entity='Catalog', op='view')
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
        
        res, total = self.get_paginated_entities(Catalog, get_entities, *args, **kvargs)
        return res, total            
        
    @trace(entity='CatalogEndpoint', op='view')
    def get_endpoint(self, oid):
        """Get single catalog endpoint.

        :param oid: entity model id or name or uuid         
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        endpoint = self.get_entity(CatalogEndpoint, ModelEndpoint, oid)
        catalog = self.manager.get_entity(ModelCatalog, endpoint.model.catalog_id)
        endpoint.set_catalog(catalog.uuid, catalog.name)
        
        return endpoint
        
    @trace(entity='CatalogEndpoint', op='view')
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
            # get filter catalog
            catalog = kvargs.pop('catalog', None)
            if catalog is not None:
                kvargs['catalog'] = self.get_catalog(catalog).oid
            
            entities, total = self.manager.get_endpoints(*args, **kvargs)
            
            return entities, total
        
        def customize(entities, *args, **kvargs):
            tags = []
            if operation.authorize is True:
                # verify permissions for catalogs
                objs = self.can('view', Catalog.objtype, definition=Catalog.objdef)
                objs = objs.get(Catalog.objdef.lower())

                # create permission tags
                for p in objs:
                    tags.append(self.manager.hash_from_permission(Catalog.objdef, p))
                kvargs['tags'] = tags
            else:
                kvargs['with_perm_tag'] = False
                self.logger.debug('Auhtorization disabled for command')

            # make catalog index
            catalogs, total = self.manager.get(**kvargs)
            catalogs_idx = {i.id: Catalog(self, oid=i.id, objid=i.objid, name=i.name, desc=i.desc, active=True,
                                          model=i) for i in catalogs}
            
            # set parent catalog
            for entity in entities:
                cat = catalogs_idx[entity.model.catalog_id]
                entity.set_catalog(cat.uuid, cat.name)
        
        res, total = self.get_paginated_entities(CatalogEndpoint, get_entities, customize=customize, *args, **kvargs)

        return res, total 


class Catalog(AuthObject):
    """Catalog class"""
    module = 'CatalogModule'
    objtype = 'directory'
    objdef = 'Catalog'
    objuri = 'catalog'
    objdesc = 'dir/Catalog'
    
    def __init__(self, *args, **kvargs):
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
        info = AuthObject.info(self)
        info.update({'zone': self.zone})
        return info

    def detail(self):
        """Get object extended info
        
        :return: Dictionary with object detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = self.info()
        services = {}
        endpoints, total = self.controller.get_endpoints(catalog=self.oid)
        for item in endpoints:
            try:
                services[item.service].append(item.endpoint)
            except:
                services[item.service] = [item.endpoint]
        info['services'] = [{'service': k, 'endpoints': v} for k, v in services.items()]
        return info

    @trace(op='insert')
    def add_endpoint(self, name=None, desc=None, service=None, uri=None, active=True):
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
        self.controller.check_authorization(CatalogEndpoint.objtype, CatalogEndpoint.objdef, self.objid, 'insert')
        
        try:
            # create catalog endpoint reference
            objid = b'%s//%s' % (self.objid, id_gen())
            res = self.manager.add_endpoint(objid, name, service, desc, self.oid, uri, active)
            
            # create object and permission
            CatalogEndpoint(self.controller, oid=res.id).register_object(objid.split('//'), desc=desc)
            
            self.logger.debug('Add catalog endpoint: %s' % truncate(res))
            return res.uuid
        except (QueryError, TransactionError, ModelError) as ex:      
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)


class CatalogEndpoint(AuthObject):
    """Catalog endpoint class"""
    module = 'CatalogModule'
    objtype = 'directory'
    objdef = 'Catalog.Endpoint'
    objuri = 'dir/endpoint'
    objdesc = 'Catalog endpoint'
    
    def __init__(self, *args, **kvargs):
        AuthObject.__init__(self, *args, **kvargs)
        
        self.catalog = None

        if self.model is not None:
            self.endpoint = self.model.uri
            self.service = self.model.service

        self.update_object = self.manager.update_endpoint
        self.delete_object = self.manager.delete_endpoint

    def set_catalog(self, uuid, name):
        """Set catalog

        :param uuid: catalog uuid
        :param name: catalog name
        :return:
        """
        self.catalog = {
            'name': name,
            'uuid': uuid,
        }

    def info(self):
        """Get object info
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        info = AuthObject.info(self)
        info.update({
            'catalog': self.catalog,
            'service': self.model.service,
            'endpoint': self.model.uri
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
