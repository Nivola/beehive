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

    '''
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        # register childs
        for child in self.child_classes:
            child(self).init_object()
    '''

    '''
    @distributed_query
    def get_superadmin_permissions(self):
        """ """
        try:
            #perms = ApiModule.get_superadmin_permissions(self)
            perms = []
            for container_class in self.container_classes.values():
                container = container_class(self)
                perms.extend(container.get_superadmin_permissions())
            return perms
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    

    def set_superadmin_permissions(self):
        """ """
        try:
            self.set_admin_permissions(u'ApiSuperadmin', [])
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code) 

    def set_admin_permissions(self, role_name, args):
        """ """
        try:
            for item in self.classes:
                item(self).set_admin_permissions(role_name, args)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)            
    '''

    @trace(entity=u'Catalog', op=u'insert')
    def add_catalog(self, name, desc, zone):
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

        :param oid: entity model id or name or uuid         
        :return: Catalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_object(Catalog, ModelCatalog, oid) 

    @trace(entity=u'Catalog', op=u'view')
    def get_catalogs(self, oid=None, objid=None, name=None, zone=None):
        """Get containers.
        
        :param oid str: catalog id. [optional]
        :param objid str: catalog object id. [optional]
        :param name str: catalog name. [optional]
        :param zone: catalog zone. Value like internal or external
        :return: List of catalogs
        :rtype: list
        :raises ApiManagerError: if query empty return error. 
        """
        objs = self.can(u'view', Catalog.objtype, definition=Catalog.objdef)
        #opts = {u'oid':oid, u'objid':objid, u'name':name}
        
        try:
            catalogs = self.manager.get(oid=oid, objid=objid, name=name, zone=zone)
        except:
            catalogs = []
        
        try:
            res = []
            for i in catalogs:
                # check authorization
                objs_need = set(objs[Catalog.objdef.lower()])
                # create needs
                needs = self.get_needs([i.objid])
                # check if needs overlaps perms
                if self.has_needs(needs, objs_need):
                    obj = Catalog(self, oid=i.id, objid=i.objid, name=i.name, 
                                  desc=i.desc, active=True, model=i)
                    # append service   
                    res.append(obj)              
            
            self.logger.debug('Get catalogs: %s' % truncate(res))
            #Catalog(self).send_event(u'view', opts)            
            return res
        except QueryError as ex:
            #Catalog(self).send_event(u'view', opts, exception=ex)   
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
    @trace(entity=u'CatalogEndpoint', op=u'view')
    def get_endpoint(self, oid):
        """Get single catalog endpoint.

        :param oid: entity model id or name or uuid         
        :return: Group
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_object(CatalogEndpoint, ModelEndpoint, oid)         
        
    @trace(entity=u'CatalogEndpoint', op=u'view')
    def get_endpoints(self, oid=None, objid=None, name=None, service=None,
                      catalog_id=None):
        """Get endpoints.

        :param oid str: endpoint oid [optional]
        :param objid str: endpoint object id or part of this [optional]
        :param name str: endpoint name [optional]
        :param service str: endpoint service [optional]
        :param catalog_id str: endpoint catalog [optional]
        :return: List of endpoints
        :rtype: list of :class:`Resource`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """   
        objs = self.can(u'view', CatalogEndpoint.objtype, 
                        definition=CatalogEndpoint.objdef)
        objset = set(objs[CatalogEndpoint.objdef.lower()])
        
        try:
            try:
                endpoints = self.manager.get_endpoints(oid=oid, objid=objid, 
                                                       name=name, service=service, 
                                                       catalog=catalog_id)
                cat_idx = {i.id:Catalog(self, oid=i.id, objid=i.objid, name=i.name, 
                                        desc=i.desc, active=True, model=i) 
                           for i in self.manager.get()}
            except:
                endpoints = []
            
            res = []
            for i in endpoints:
                # create needs
                needs = self.get_needs(i.objid.split(u'//'))
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    catalog = cat_idx[i.catalog_id]
                    obj = CatalogEndpoint(self, catalog, oid=i.id, 
                                          objid=i.objid, name=i.name, 
                                          desc=i.desc, active=i.active, model=i)
                    # append endpoint   
                    res.append(obj)

            self.logger.debug('Get catalog endpoints: %s..' % str(res)[0:200])
            #Catalog(self).send_event(u'endpoint.view', opts)
            return res
        except QueryError as ex:
            #Catalog(self).send_event(u'endpoint.view', opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)        
        
class Catalog(AuthObject):
    objtype = u'directory'
    objdef = u'Catalog'
    objuri = u'catalog'
    objdesc = u'Catalog'
    
    def __init__(self, *args, **kvargs):
        """ """
        AuthObject.__init__(self, *args, **kvargs)

        #self.objuri = u'/%s/%s/%s' % (self.controller.version, self.objuri, self.oid)
        
        if self.model is not None:
            self.zone = self.model.zone
            
        # child classes
        self.child_classes = [CatalogEndpoint]

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

    '''
    @trace(op=u'update')
    def update(self, new_name=None, new_desc=None, new_zone=None):
        """Update catalog.

        :param new_name str: new container name. [optional]
        :param new_desc str: new description [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.    
        """
        # check authorization
        self.verify_permisssions(u'update')
        #opts = {u'name':self.name, u'new_name':new_name, u'new_desc':new_desc}
        
        try:
            res = self.manager.update(oid=self.oid, new_name=new_name, 
                                      new_desc=new_desc, new_zone=new_zone)

            self.logger.debug('Update container %s: %s' % (self.objid, res))
            
            #self.send_event(u'update', opts)            
            return res
        except (QueryError, TransactionError) as ex:
            #self.send_event(u'update', opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'delete')
    def delete(self):
        """Remove catalog.
        
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.verify_permisssions(u'delete')
        try:
            # create object and permission
            self.deregister_object([self.objid])
            
            res = self.manager.delete(oid=self.oid)
            self.logger.debug('Remove catalog %s' % self.name)
            #self.send_event(u'update', opts)        
            return self.oid
        except (TransactionError, QueryError) as ex:
            #self.send_event(u'update', opts, exception=ex)   
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    '''

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

    @trace(op=u'endpoints.view')
    def get_endpoints(self, oid=None, objid=None, name=None, service=None):
        """Get endpoints.

        :param oid str: endpoint oid [optional]
        :param objid str: endpoint object id or part of this [optional]
        :param name str: endpoint name [optional]
        :param service str: endpoint service [optional]
        :return: List of endpoints
        :rtype: list of :class:`Resource`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """   
        objs = self.controller.can(u'view', CatalogEndpoint.objtype, 
                                   definition=CatalogEndpoint.objdef)
        objset = set(objs[CatalogEndpoint.objdef.lower()])
        #opts = {u'oid':oid, u'objid':objid, u'name':name, 
        #        u'service':service, u'catalog':self.name}
        
        try:
            try:
                endpoints = self.manager.get_endpoints(oid=oid, objid=objid, 
                                                       name=name, service=service, 
                                                       catalog=self.oid)
            except:
                endpoints = []
            
            res = []
            for i in endpoints:
                # create needs
                needs = self.controller.get_needs(i.objid.split('//'))
                
                # check if needs overlaps perms
                if self.controller.has_needs(needs, objset) is True:
                    obj = CatalogEndpoint(self.controller, self, oid=i.id, 
                                         objid=i.objid, name=i.name, desc=i.desc, 
                                         active=i.active, model=i)
                    # append endpoint   
                    res.append(obj)

            self.logger.debug('Get catalog endpoints: %s..' % str(res)[0:200])
            #self.send_event(u'endpoint.view', opts) 
            return res
        except QueryError as ex:
            #self.send_event(u'endpoint.view', opts, exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    '''
    @watch
    def authorization(self):
        """Get catalog authorizations.
        
        :return: [(perm, roles), ...]
        :rtype: list
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')        
        
        try:
            # catalog permissions
            res = self.api_client.get_permissions(self.objtype, self.objdef, self.objid)            
            # catalog child permissions
            res.extend(self.api_client.get_permissions(self.objtype, 
                                                       CatalogEndpoint.objdef, 
                                                       self.objid+u'//*'))

            self.logger.debug('Get permissions for catalog %s: %s' % (self.oid, res))
            return res
        except (ApiManagerError), ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    '''

class CatalogEndpoint(AuthObject):
    objtype = u'directory'
    objdef = u'Catalog.Endpoint'
    objuri = u'endpoint'
    objdesc = u'Catalog endpoint'
    
    def __init__(self, controller, catalog=None, oid=None, objid=None, name=None, 
                 desc=None, active=None, model=None):
        """ """
        AuthObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                           desc=desc, active=active, model=model)
        
        self.catalog = catalog

        if self.model is not None:
            self.endpoint = self.model.uri
            self.service = self.model.service
            self.uuid = self.model.uuid
        
        if self.catalog is not None:
            self.objuri = u'%s/%s/%s' % (self.catalog.objuri, self.objuri, self.oid)
    
    def __repr__(self):
        return "<%s id=%s objid=%s name=%s catalog=%s>" % (
                    self.__class__.__name__, self.oid, self.objid,
                    self.name, self.catalog.name)

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
            u'uri':self.objuri, 
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

    '''
    @trace(op=u'update')
    def update(self, new_name=None, new_desc=None, new_service=None, new_uri=None,
               new_active=None, new_catalog=None):
        """Update catalog service.

        :param new_name str: new  name. [optional]
        :param new_desc str: new description [optional]
        :param new_active bool:  Status. If True is active [optional]
        :param new_uri str: new uri [optional]
        :param new_service str: new service [optional]
        :param new_catalog: endpoint catalog id [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.verify_permisssions(u'update')

        #opts = {u'oid':self.oid, u'name':new_name, u'desc':new_desc,
        #        u'uri':new_uri, u'service':new_service, u'active':new_active, 
        #        u'catalog':new_catalog}
        
        try:
            res = self.manager.update_endpoint(oid=self.oid, 
                                               new_name=new_name, 
                                               new_desc=new_desc, 
                                               new_service=new_service,
                                               new_uri=new_uri,
                                               new_catalog=new_catalog,
                                               new_active=new_active)         
            
            self.logger.debug('Update catalog %s service %s: %s' % 
                              (self.catalog.name, self.name, res))
            #self.send_event(u'update', opts)
            return res
        except TransactionError, ex:
            self.logger.error(ex, exc_info=1)
            #self.send_event(u'update', opts, exception=ex)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'delete')
    def delete(self):
        """Remove catalog service.     
        
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.verify_permisssions(u'delete')
        #opts = {u'oid':self.oid, u'catalog':self.name}

        try:
            # remove object and permission
            self.deregister_object(self.objid.split('//'))
            
            res = self.manager.delete_endpoint(oid=self.oid)
            self.logger.debug('Remove catalog %s endpoint %s' % 
                              (self.catalog.name, self.name))
            #self.send_event(u'update', opts)
            return self.oid
        except (TransactionError, QueryError), ex:
            self.logger.error(ex, exc_info=1)
            #self.send_event(u'update', opts, exception=ex)        
            raise ApiManagerError(ex, code=ex.code)
    '''

    '''
    def authorization(self):
        """Get catalog service authorizations       
        
        :return: [(perm, roles), ...]
        :rtype: list
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')
        
        try:
            # organization permissions
            res = self.api_client.get_permissions(self.objtype, self.objdef, 
                                                  self.objid)

            self.logger.debug(u'Get catalog service %s permissions %s: %s' % 
                              (self.name, self.oid, res))
            return res
        except (BeehiveApiClientError, Exception), ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    '''
                