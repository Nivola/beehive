"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from beecell.simple import get_value
from beecell.simple import get_attrib
from beehive.common.apimanager import ApiView, ApiManagerError

class CatalogApiView(ApiView):
    def get_catalog(self, controller, oid):
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            objs = controller.get_catalogs(uuid=oid)
        # get link by id
        elif match(u'[0-9]+', str(oid)):
            objs = controller.get_catalogs(oid=int(oid))
        # get obj by name
        else:
            objs = controller.get_catalogs(name=oid)
        if len(objs) == 0:
            raise ApiManagerError(u'Catalog %s not found' % oid, code=404)
        return objs[0]    

    def get_endpoint(self, controller, oid):
        # get link by id
        if match('[0-9]+', str(oid)):
            service = controller.get_endpoints(oid=int(oid))
        # get link by value
        else:
            service = controller.get_endpoints(name=oid)
        if len(service) == 0:
            raise ApiManagerError('Service %s not found' % oid, code=404)
        return service[0]
        
#
# catalog
#
class ListCatalogs(CatalogApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        headers = request.headers
        name = get_attrib(headers, u'name', None)
        catalogs = controller.get_catalogs(name=name)
        res = [r.info() for r in catalogs]
        resp = {u'catalogs':res,
                u'count':len(res)}
        return resp

class GetCatalog(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        res = catalog.detail()
        resp = {u'catalog':res}        
        return resp
              
class GetCatalogPerms(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        res = catalog.authorization()
        resp = {u'perms':res,
                u'count':len(res)}        
        return resp

class CreateCatalog(CatalogApiView):
    """
        {u'name':u'cloudapi', 
         u'desc':u'cloudapi catalog',
         u'zone':u'internal'}
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        zone = get_value(data, u'zone', None, exception=True)
        
        resp = controller.add_catalog(name, desc, zone)
        return (resp, 201)

class UpdateCatalog(CatalogApiView):
    """ Update Catalog 
    """            
    def dispatch(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        data = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        zone = get_value(data, u'zone', None)
        resp = catalog.update(new_name=name, new_desc=desc, new_zone=zone)
        return resp
    
class DeleteCatalog(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        resp = catalog.delete()
        return (resp, 204)

#
# service
#
class ListEndpoints(CatalogApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        headers = request.headers
        name = get_attrib(headers, u'name', None)
        service = get_attrib(headers, u'service', None)       
        catalog = get_attrib(headers, u'catalog', None)          
        endpoints = controller.get_endpoints(name=name, 
                                             service=service, 
                                             catalog_id=catalog)
        res = [r.info() for r in endpoints]
        resp = {u'endpoints':res,
                u'count':len(res)}
        return resp

class GetEndpoint(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        endpoint = self.get_endpoint(controller, oid)
        res = endpoint.detail()
        resp = {u'endpoint':res}        
        return resp
              
class GetEndpointPerms(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        res = endpoint.authorization()
        resp = {u'perms':res,
                u'count':len(res)}        
        return resp

class CreateEndpoint(CatalogApiView):
    """
        {
            u'endpoint':{
                u'name':u'auth-01', 
                u'desc':u'Authorization endpoint 01', 
                u'service':u'auth', 
                u'uri':u'http://localhost:6060/api/auth/', 
                u'enabled':True                   
            }
        }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        service = get_value(data, u'service', None, exception=True)
        uri = get_value(data, u'uri', None, exception=True)
        enabled = get_value(data, u'enabled', True)
        catalog_obj = self.get_catalog(controller, catalog)
        resp = catalog_obj.add_endpoint(name, desc, service, uri, enabled)
        return (resp, 201)

class UpdateEndpoint(CatalogApiView):
    """ Update Endpoint 
    """            
    def dispatch(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        service = get_value(data, u'service', None)
        uri = get_value(data, u'uri', None)
        enabled = get_value(data, u'enabled', None)
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.update(new_name=name, new_desc=desc, 
                               new_service=service, new_uri=uri,
                               new_enabled=enabled, new_catalog=catalog)
        return resp
    
class DeleteEndpoint(CatalogApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.delete()
        return (resp, 204)

class CatalogAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('catalogs', 'GET', ListCatalogs, {}),
            ('catalog/<oid>', 'GET', GetCatalog, {}),
            #('catalog/<oid>/<zone>', 'GET', FilterCatalog, {}),
            ('catalog/<oid>/perms', 'GET', GetCatalogPerms, {}),
            ('catalog', 'POST', CreateCatalog, {}),
            ('catalog/<oid>', 'PUT', UpdateCatalog, {}),
            ('catalog/<oid>', 'DELETE', DeleteCatalog, {}),
            #('catalog/<oid>/services', 'GET', GetCatalogServices, {}),

            ('catalog/endpoints', 'GET', ListEndpoints, {}),
            ('catalog/endpoint/<oid>', 'GET', GetEndpoint, {}),
            ('catalog/endpoint/<oid>/perms', 'GET', GetEndpointPerms, {}),
            ('catalog/endpoint', 'POST', CreateEndpoint, {}),
            ('catalog/endpoint/<oid>', 'PUT', UpdateEndpoint, {}),
            ('catalog/endpoint/<oid>', 'DELETE', DeleteEndpoint, {}),
        ]

        ApiView.register_api(module, rules)