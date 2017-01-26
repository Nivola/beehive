'''
Created on Jan 16, 2014

@author: darkbk
'''
from beehive.common.data import QueryError, TransactionError
from beehive.common.apimanager import ApiController, ApiObject, ApiManagerError
from beecell.perf import watch
from beecell.simple import import_class, truncate, id_gen, str2uni
from beehive.common.data import distributed_transaction, distributed_query
from beehive.module.auth.model import AuthDbManager
from .model import CatalogDbManager
from beecell.db import ModelError

class CatalogController(ApiController):
    """Catalog Module controller.
    """
    version = u'v1.0'
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.manager = CatalogDbManager()
        self.dbauth = AuthDbManager() # set to connect auth via db
        self.classes = [Catalog]
        
    def add_container_class(self, name, container_class):
        self.container_classes[name] = container_class

    def get_container_class(self, name):
        return self.container_classes[name]

    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """        
        # register containers
        for controller_class in self.classes:
            controller_class(self).init_object()

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
    '''

    @distributed_transaction
    def add_catalog(self, name, desc, zone):
        """ """
        # check authorization
        objs = self.can('insert', Catalog.objtype, definition=Catalog.objdef)
        if len(objs) > 0 and objs[Catalog.objdef][0].split('//')[-1] != '*':
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
            
            Catalog(self).event('catalog.add', 
                                {'objid':objid, 'name':name}, 
                                True)
            return catalog.oid
        except (QueryError, TransactionError) as ex:
            Catalog(self).event('catalog.add', 
                                {'objid':objid, 'name':name}, 
                                (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @distributed_query
    def count_all_catalogs(self):
        """Get all catalogs count"""
        return self.manager.count()

    @distributed_query
    def count_all_catalog_services(self):
        """Get all catalog services count"""
        return self.manager.count_services()

    @distributed_query
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
        
        try:
            catalogs = self.manager.get(oid=oid, objid=objid, name=name, zone=zone)
        except:
            catalogs = []
        
        try:
            res = []
            for i in catalogs:
                # check authorization
                objs_need = set(objs[Catalog.objdef])
                # create needs
                needs = self.get_needs([i.objid])
                # check if needs overlaps perms
                if self.has_needs(needs, objs_need):
                    obj = Catalog(self, oid=i.id, objid=i.objid, name=i.name, 
                                  desc=i.desc, active=True, model=i)
                    # append service   
                    res.append(obj)              
            
            self.logger.debug('Get catalogs: %s' % truncate(res))
            Catalog(self).event('catalog.view', 
                                {'oid':oid, 'objid':objid, 'name':name}, 
                                True)
            return res
        except QueryError as ex:
            Catalog(self).event('catalog.view', 
                                {'oid':oid, 'objid':objid, 'name':name}, 
                                (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
    @watch
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
        objs = self.can('view', CatalogEndpoint.objtype, 
                        definition=CatalogEndpoint.objdef)
        objset = set(objs[CatalogEndpoint.objdef])
        
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
                needs = self.get_needs(i.objid.split('//'))
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    catalog = cat_idx[i.catalog_id]
                    obj = CatalogEndpoint(self, catalog, oid=i.id, 
                                          objid=i.objid, name=i.name, 
                                          desc=i.desc, active=i.enabled, model=i)
                    # append endpoint   
                    res.append(obj)

            self.logger.debug('Get catalog endpoints: %s..' % str(res)[0:200])
            Catalog(self).event('catalog.endpoint.view', 
                                {'oid':oid, 'objid':objid, 'name':name, 
                                 'service':service, 'catalog':catalog_id},
                                True)
            return res
        except QueryError as ex:
            Catalog(self).event('catalog.endpoint.view', 
                                {'oid':oid, 'objid':objid, 'name':name, 
                                 'service':service, 'catalog':catalog_id},
                                (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)        
        
class Catalog(ApiObject):
    objtype = 'directory'
    objdef = 'catalog'
    objuri = 'catalog'
    objdesc = 'Catalog'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 active=None, model=None):
        """ """
        ApiObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                           desc=desc, active=active)
        self.catalog_classes = [CatalogEndpoint]
        self.model = model
        self.objuri = '/%s/%s/%s' % (self.controller.version, self.objuri, self.oid)
        
        if self.model is not None:
            self.zone = self.model.zone
    
    @property
    def dbauth(self):
        return self.controller.dbauth    
    
    @property
    def manager(self):
        return self.controller.manager

    @distributed_query
    def info(self):
        """Get system capabilities.
        
        :return: Dictionary with system capabilities.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """    
        creation_date = str2uni(self.model.creation_date.strftime("%d-%m-%y %H:%M:%S"))
        modification_date = str2uni(self.model.modification_date.strftime("%d-%m-%y %H:%M:%S"))
        return {u'id':self.oid, u'type':self.objtype, u'definition':self.objdef, 
                u'name':self.name, u'objid':self.objid, u'desc':self.desc, 
                u'uri':self.objuri, u'zone':self.zone, u'active':self.active, 
                u'date':{u'creation':creation_date,
                         u'modification':modification_date}}

    @distributed_query
    def detail(self):
        """Get system details.
        
        :return: Dictionary with system capabilities.
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

    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        ApiObject.init_object(self)
            
        # register catalog managed endpoints
        for catalog_class in self.catalog_classes:
            catalog_class(self.controller, self).init_object()
            
        # add full permissions to superadmin role
        #self.set_superadmin_permissions()

    def register_object(self, args, desc=''):
        """Register object types, objects and permissions related to module.
        
        :param args: 
        """
        ApiObject.register_object(self, args, desc=self.desc)
        
        # register catalog managed endpoints
        for catalog_class in self.catalog_classes:
            i = catalog_class.objdesc.index(' ')
            desc = "%s%s" % (self.desc, catalog_class.objdesc[i:])
            catalog_class(self.controller, self).register_object(args, desc=desc)           
            
    def deregister_object(self, args):
        """Deregister object types, objects and permissions related to module.
        
        :param args: 
        """
        ApiObject.deregister_object(self, args)
        
        # deregister catalog managed endpoints
        for catalog_class in self.catalog_classes:
            catalog_class(self.controller, self).deregister_object(args)

    def set_superadmin_permissions(self):
        """ """
        self._set_admin_permissions('ApiSuperadmin', [])

    def _set_admin_permissions(self, role, args):
        """ """
        try:
            role = self.dbauth.get_role(name=role)[0]
            perms = self.dbauth.get_permission_by_object(
                                    objid=self._get_value(self.objdef, args),
                                    objtype=None, 
                                    objdef=self.objdef,
                                    action='*')            
            
            # set container main permissions
            self.dbauth.append_role_permissions(role, perms)

            # set catalog child resources permissions
            for catalog_class in self.catalog_classes:
                res = catalog_class(self.controller, self)
                perms = self.dbauth.get_permission_by_object(
                                    objid=self._get_value(res.objdef, args),
                                    objtype=None, 
                                    objdef=res.objdef,
                                    action='*')                
                self.dbauth.append_role_permissions(role, perms)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def update(self, new_name=None, new_desc=None, new_zone=None):
        """Update catalog.

        :param new_name str: new container name. [optional]
        :param new_desc str: new description [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.    
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'update')
        
        try:
            res = self.manager.update(oid=self.oid, new_name=new_name, 
                                      new_desc=new_desc, new_zone=new_zone)

            self.logger.debug('Update container %s: %s' % (self.objid, res))
            
            self.event('%s.update' % self.objdef, 
                       {'name':self.name, 'new_name':new_name,
                        'new_desc':new_desc,}, 
                       True)
            return res
        except (QueryError, TransactionError) as ex:
            self.event('%s.update' % self.objdef, 
                       {'name':self.name, 'new_name':new_name,
                        'new_desc':new_desc}, 
                       (False, ex))             
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Remove catalog.
        
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'delete')

        # remove container admin role
        #self._remove_admin_role(self.objid)

        try:
            # create object and permission
            self.deregister_object([self.objid])
            
            res = self.manager.delete(oid=self.oid)
            self.logger.debug('Remove catalog %s' % self.name)
            self.event('%s.delete' % self.objdef, 
                       {'name':self.name}, 
                       True)            
            return self.oid
        except (TransactionError, QueryError) as ex:
            self.event('%s.delete' % self.objdef, 
                       {'name':self.name}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    def add_endpoint(self, name, desc, service, uri, enabled=True):
        """Add endpoint.
        
        :param endpoint: Service endpoint
        :return: True if success
        :rtype: bool 
        :raises ApiManagerError: raise :class:`ApiManagerError`
        :raises ApiAuthorizationError: raise :class:`ApiAuthorizationError`
        """
        # check authorization
        self.controller.check_authorization(CatalogEndpoint.objtype, 
                                            CatalogEndpoint.objdef, 
                                            self.objid, 'insert')
        
        try:
            # create catalog endpoint reference
            objid = "%s//%s" % (self.objid, id_gen())            
            res = self.manager.add_endpoint(objid, name, service, desc, self.oid, 
                                            uri, enabled)
            
            # create object and permission
            CatalogEndpoint(self.controller).register_object(objid.split('//'), 
                                                            desc=desc)
            
            self.logger.debug('Add catalog endpoint: %s' % truncate(res))
            self.event('catalog.endpoint.insert', 
                       {'objid':objid, 'name':name, 'service':service, 'uri':uri,
                        'enabled':enabled},
                       True)
            return res.id
        except (QueryError, TransactionError, ModelError) as ex:
            self.event('catalog.endpoint.insert', 
                       {'objid':objid, 'name':name, 'service':service, 'uri':uri,
                        'enabled':enabled},
                       True)            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
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
        objs = self.controller.can('view', CatalogEndpoint.objtype, 
                                   definition=CatalogEndpoint.objdef)
        objset = set(objs[CatalogEndpoint.objdef])
        
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
                                         active=i.enabled, model=i)
                    # append endpoint   
                    res.append(obj)

            self.logger.debug('Get catalog endpoints: %s..' % str(res)[0:200])
            self.event('catalog.endpoint.view', 
                       {'oid':oid, 'objid':objid, 'name':name, 
                        'service':service, 'catalog':self.name},
                       True)
            return res
        except QueryError as ex:
            self.event('catalog.endpoint.view', 
                       {'oid':oid, 'objid':objid, 'name':name, 
                        'service':service, 'catalog':self.name},
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def authorization(self):
        """Get catalog authorizations.
        
        :return: [(perm, roles), ...]
        :rtype: list
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'view')        
        
        try:
            # catalog permissions
            res = self.api_client.get_permissions(self.objtype, self.objdef, self.objid)            
            # catalog child permissions
            res.extend(self.api_client.get_permissions(self.objtype, 
                                                       CatalogEndpoint.objdef, 
                                                       self.objid+'//*'))

            self.logger.debug('Get permissions for catalog %s: %s' % (self.oid, res))
            return res
        except (ApiManagerError), ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)


class CatalogEndpoint(ApiObject):
    objtype = 'directory'
    objdef = 'catalog.endpoint'
    objuri = 'endpoint'
    objdesc = 'Catalog endpoint'
    
    def __init__(self, controller, catalog=None, oid=None, objid=None, name=None, 
                 desc=None, active=None, model=None):
        """ """
        ApiObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                           desc=desc, active=active)
        self.catalog = catalog
        self.model = model
        if self.model is not None:
            self.endpoint = self.model.uri
            self.service = self.model.service
        
        if self.catalog is not None:
            self.objuri = '%s/%s/%s' % (self.catalog.objuri, self.objuri, self.oid)
    
    def __repr__(self):
        return "<%s id='%s' objid='%s' name='%s' catalog='%s'>" % (
                    self.__class__.__name__, self.oid, self.objid,
                    self.name, self.catalog.name)

    @property
    def dbauth(self):
        return self.controller.dbauth
    
    @property
    def manager(self):
        return self.controller.manager
    
    @distributed_query
    def info(self):
        """Get endpoint infos.
        
        :return: Dictionary with system capabilities.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'view')
          
        creation_date = str2uni(self.model.creation_date.strftime("%d-%m-%y %H:%M:%S"))
        modification_date = str2uni(self.model.modification_date.strftime("%d-%m-%y %H:%M:%S"))   
        return {u'id':self.oid, u'type':self.objtype, u'definition':self.objdef, 
                u'name':self.name, u'objid':self.objid, u'desc':self.desc,
                u'catalog':self.catalog.name, u'catalog_id':self.catalog.oid,
                u'uri':self.objuri, u'service':self.model.service,
                u'endpoint':self.model.uri,
                u'active':self.active, u'date':{u'creation':creation_date,
                                                u'modification':modification_date}}
    
    @distributed_query
    def detail(self):
        """Get endpoint details.
        
        :return: Dictionary with system capabilities.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return self.info()

    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        ApiObject.init_object(self)

    @watch
    def update(self, new_name=None, new_desc=None, new_service=None, new_uri=None,
               new_enabled=None, new_catalog=None):
        """Update catalog service.

        :param new_name str: new  name. [optional]
        :param new_desc str: new description [optional]
        :param new_enabled bool:  Status. If True is active [optional]
        :param new_uri str: new uri [optional]
        :param new_service str: new service [optional]
        :param new_catalog: endpoint catalog id [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: if query empty return error.
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
        
        try:
            res = self.manager.update_endpoint(oid=self.oid, 
                                               new_name=new_name, 
                                               new_desc=new_desc, 
                                               new_service=new_service,
                                               new_uri=new_uri,
                                               new_catalog=new_catalog,
                                               new_enabled=new_enabled)         
            
            self.logger.debug('Update catalog %s service %s: %s' % 
                              (self.catalog.name, self.name, res))
            self.event('catalog.service.update', 
                       {'oid':self.oid, 'name':new_name, 'desc':new_desc,
                        'uri':new_uri, 'service':new_service, 'enabled':new_enabled, 
                        'catalog':new_catalog},
                       True)
            return res
        except TransactionError, ex:
            self.logger.error(ex, exc_info=1)
            self.event('catalog.service.update', 
                       {'oid':self.oid, 'name':new_name, 'desc':new_desc,
                        'uri':new_uri, 'service':new_service, 'enabled':new_enabled, 
                        'catalog':new_catalog},
                       (False, ex))            
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Remove catalog service.     
        
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'delete') 

        try:
            # remove object and permission
            self.deregister_object(self.objid.split('//'))
            
            res = self.manager.delete_endpoint(oid=self.oid)
            self.logger.debug('Remove catalog %s endpoint %s' % 
                              (self.catalog.name, self.name))
            self.event('catalog.endpoint.delete', 
                       {'oid':self.oid, 'catalog':self.name},
                       True)            
            return self.oid
        except (TransactionError, QueryError), ex:
            self.logger.error(ex, exc_info=1)
            self.event('catalog.endpoint.delete', 
                       {'oid':self.oid, 'catalog':self.name},
                       (False, ex))            
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def authorization(self):
        """Get catalog service authorizations       
        
        :return: [(perm, roles), ...]
        :rtype: list
        :raises ApiManagerError: if query empty return error.  
        """
        # check authorization
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'view')        
        
        try:
            # organization permissions
            res = self.api_client.get_permissions(self.objtype, self.objdef, 
                                                  self.objid)

            self.logger.debug('Get catalog service %s permissions %s: %s' % 
                              (self.name, self.oid, res))
            return res
        except (TransactionError, QueryError, Exception), ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)