'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)


class DirectoryController(BaseController):
    class Meta:
        label = 'directory'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Directory Service management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class DirectoryControllerChild(ApiController):
    cataloguri = u'/v1.0/directory'
    subsystem = u'auth'
    
    cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                   u'date.creation', u'date.modified']
    end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                   u'service', u'active', 
                   u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'directory'
        stacked_type = 'nested'


class CatalogController(DirectoryControllerChild):
    class Meta:
        label = 'catalogs'
        description = "Catalog management"
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List catalog 
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/catalogs' % (self.cataloguri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get catalogs: %s' % res)  
        self.result(res, key=u'catalogs', headers=self.cat_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get catalog by id
        """
        catalog_id = self.get_arg(name=u'id')
        uri = u'%s/catalogs/%s' % (self.cataloguri, catalog_id)
        res = self._call(uri, u'GET')
        logger.info(u'Get catalog: %s' % res)
        services = res.get(u'catalog').pop(u'services')
        self.result(res, key=u'catalog', headers=self.cat_headers, details=True)
        self.app.print_output(u'services:')        
        self.result(services, headers=[u'service', u'endpoints'])
    
    @expose(aliases=[u'add <name> <zone>'], aliases_only=True)
    @check_error
    def add(self):
        """Add catalog <name>
        """
        name = self.get_arg(name=u'name')
        zone = self.get_arg(name=u'zone')
        res = self.client.create_catalog(name, zone)
        logger.info(u'Add catalog: %s' % truncate(res))
        res = {u'msg':u'Add catalog %s' % res}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete catalog by id
        """        
        catalog_id = self.get_arg(name=u'id')
        res = self.client.delete_catalog(catalog_id)
        logger.info(u'Delete catalog: %s' % truncate(res))
        res = {u'msg':u'Delete catalog %s' % res}
        self.result(res, headers=[u'msg'])        


class EndpointController(DirectoryControllerChild):    
    class Meta:
        label = 'endpoints'
        description = "Endpoint management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List endpoints
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/endpoints' % (self.cataloguri)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get endpoints: %s' % res)  
        self.result(res, key=u'endpoints', headers=self.end_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get endpoint by id
        """
        endpoint_id = self.get_arg(name=u'id')
        uri = u'%s/endpoints/%s' % (self.cataloguri, endpoint_id)
        res = self._call(uri, u'GET')
        logger.info(u'Get endpoint: %s' % res)
        self.result(res, key=u'endpoint', headers=self.end_headers, details=True)
        
    @expose(aliases=[u'add <name> <catalog-id> <service> <uri>'], aliases_only=True)
    @check_error
    def add(self):
        """Add catalog endpoint <name>
    - service : service name like auth, resource
    - uri : http://localhost:3030
        """
        name = self.get_arg(name=u'name')
        catalog = self.get_arg(name=u'catalog-id')
        service = self.get_arg(name=u'service')
        uri = self.get_arg(name=u'uri')      
        # if endpoint exist update it else create new one
        try:
            res = self.client.get_endpoint(name)
            res = self.client.update_endpoint(name, catalog_id=catalog, name=name, service=service, uri=uri)
        except Exception as ex:
            logger.error(ex, exc_info=1)
            res = self.client.create_endpoint(catalog, name, service, uri)
        logger.info(u'Add endpoint: %s' % truncate(res))
        res = {u'msg':u'Add catalog endpoint %s' % res}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Get endpoint by id
        """
        endpoint_id = self.get_arg(name=u'id')        
        res = self.client.delete_endpoint(endpoint_id)
        logger.info(u'Delete endpoint: %s' % truncate(res))
        res = {u'msg':u'Delete catalog endpoint %s' % res}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'ping <id>'], aliases_only=True)
    @check_error
    def ping(self):
        """Get endpoint by id
        """
        endpoint_id = self.get_arg(name=u'id')        
        endpoint = self.client.get_endpoint(endpoint_id).get(u'endpoint').get(u'endpoint')
        res = self.client.ping(endpoint=endpoint)
        
        logger.info(u'Ping endpoint %s: %s' % (endpoint, truncate(res)))
        self.result({u'endpoint':endpoint, u'ping':res}, headers=[u'endpoint', u'ping'])
        
    @expose(aliases=[u'pings <catalog-id>'], aliases_only=True)
    @check_error
    def pings(self):
        """Get endpoints by catalog
        """
        catalog_id = self.get_arg(name=u'catalog-id')        
        services = []
        catalog = self.client.get_catalog(catalog_id)
        for v in catalog.get(u'services', {}):
            for v1 in v.get(u'endpoints', []):
                res = self.client.ping(endpoint=v1)
                services.append({u'service':v[u'service'], u'endpoint':v1, u'ping':res})
                logger.info(u'Ping endpoint %s: %s' % (v1, truncate(res)))
        self.result(services, headers=[u'service', u'endpoint', u'ping'])         


catalog_controller_handlers = [
    DirectoryController,
    CatalogController,
    EndpointController
]                   
