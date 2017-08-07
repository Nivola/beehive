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
    pass
    '''def get_catalog(self, controller, oid):
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
        return service[0]'''
        
#
# catalog
#
class ListCatalogs(CatalogApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        List catalogs
        Call this api to list all the existing catalogs
        ---
        deprecated: false
        tags:
          - Catalog api
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          408:
            $ref: "#/responses/Timeout"
          415:
            $ref: "#/responses/UnsupportedMediaType"
          default: 
            $ref: "#/responses/Default" 
          200:
            description: Catalogs list
            schema:
              type: object
              required: [catalogs, count]
              properties:
                count:
                  type: integer
                  example: 1
                catalogs:
                  type: array
                  items:
                    type: object
                    required: [id, objid, name, desc, date, type, definition, active, uri, zone]
                    properties:
                      id:
                        type: integer
                        example: 1
                      objid:
                        type: string
                        example: 396587362
                      name:
                        type: string
                        example: beehive
                      desc:
                        type: string
                        example: beehive
                      active:
                        type: boolean
                        example: true
                      type:
                        type: string
                        example: directory
                      definition:
                        type: string
                        example: catalog
                      uri:
                        type: string
                        example: /v1.0/catalog/1
                      zone:
                        type: string
                        example: internal
        """            
        headers = request.headers
        name = get_attrib(headers, u'name', None)
        catalogs = controller.get_catalogs(name=name)
        res = [r.info() for r in catalogs]
        resp = {u'catalogs':res,
                u'count':len(res)}
        return resp

class GetCatalog(CatalogApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        catalog = self.controller.get_catalog(oid)
        res = catalog.detail()
        resp = {u'catalog':res}        
        return resp
              
class GetCatalogPerms(CatalogApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        res = catalog.authorization()
        resp = {u'perms':res,
                u'count':len(res)}        
        return resp

class CreateCatalog(CatalogApiView):
    """
    """
    def post(self, controller, data, *args, **kwargs):
        data = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        zone = get_value(data, u'zone', None, exception=True)
        
        resp = controller.add_catalog(name, desc, zone)
        return (resp, 201)

class UpdateCatalog(CatalogApiView):
    """ Update Catalog 
    """            
    def put(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        data = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        zone = get_value(data, u'zone', None)
        resp = catalog.update(name=name, desc=desc, zone=zone)
        return resp
    
class DeleteCatalog(CatalogApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        catalog = self.get_catalog(controller, oid)
        resp = catalog.delete()
        return (resp, 204)

#
# endpoint
#
class ListEndpoints(CatalogApiView):
    def get(self, controller, data, *args, **kwargs):
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
    def get(self, controller, data, oid, *args, **kwargs):      
        endpoint = self.controller.get_endpoint(oid)
        res = endpoint.detail()
        resp = {u'endpoint':res}        
        return resp
              
class GetEndpointPerms(CatalogApiView):
    def get(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        res = endpoint.authorization()
        resp = {u'perms':res,
                u'count':len(res)}        
        return resp

class CreateEndpoint(CatalogApiView):
    """
    """
    def post(self, controller, data, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        service = get_value(data, u'service', None, exception=True)
        uri = get_value(data, u'uri', None, exception=True)
        active = get_value(data, u'active', True)
        catalog_obj = self.get_catalog(controller, catalog)
        resp = catalog_obj.add_endpoint(name, desc, service, uri, active)
        return (resp, 201)

class UpdateEndpoint(CatalogApiView):
    """ Update Endpoint 
    """            
    def update(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'endpoint', None, exception=True)
        catalog = get_value(data, u'catalog', None)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        service = get_value(data, u'service', None)
        uri = get_value(data, u'uri', None)
        active = get_value(data, u'active', None)
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.update(name=name, desc=desc, 
                               service=service, uri=uri,
                               active=active, catalog=catalog)
        return resp
    
class DeleteEndpoint(CatalogApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        endpoint = self.get_endpoint(controller, oid)
        resp = endpoint.delete()
        return (resp, 204)

class CatalogAPI(ApiView):
    """CatalogAPI
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'catalogs', u'GET', ListCatalogs, {}),
            (u'catalog/<oid>', u'GET', GetCatalog, {}),
            #('catalog/<oid>/<zone>', 'GET', FilterCatalog, {}),
            (u'catalog/<oid>/perms', u'GET', GetCatalogPerms, {}),
            (u'catalog', u'POST', CreateCatalog, {}),
            (u'catalog/<oid>', u'PUT', UpdateCatalog, {}),
            (u'catalog/<oid>', u'DELETE', DeleteCatalog, {}),
            #('catalog/<oid>/services', 'GET', GetCatalogServices, {}),

            (u'catalog/endpoints', u'GET', ListEndpoints, {}),
            (u'catalog/endpoint/<oid>', u'GET', GetEndpoint, {}),
            (u'catalog/endpoint/<oid>/perms', u'GET', GetEndpointPerms, {}),
            (u'catalog/endpoint', u'POST', CreateEndpoint, {}),
            (u'catalog/endpoint/<oid>', u'PUT', UpdateEndpoint, {}),
            (u'catalog/endpoint/<oid>', u'DELETE', DeleteEndpoint, {}),
        ]

        ApiView.register_api(module, rules)