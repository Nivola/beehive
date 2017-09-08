'''
Created on Mar 24, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager, ComponentManager
import sys
from beecell.simple import truncate
from re import match

logger = logging.getLogger(__name__)

class CatalogManager(ApiManager):
    """
    SECTION: 
        auth
        
    PARAMS:
        catalogs list
        catalogs get <id>
        catalogs add <name> <zone>
        catalogs delete <id>
        
        endpoints list
        endpoints get <endpoint_id>
        endpoints add <name> <catalog_id> <subsystem> <uri=http://localhost:3030>
        endpoints delete <endpoint_id>
        endpoints ping <endpoint_id>
        endpoints pings <catalog_id>
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.cataloguri = u'/v1.0/directory'
        self.subsystem = u'auth'
        self.logger = logger
        self.msg = None
        
        self.cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                            u'date.creation', u'date.modified']
        self.end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                            u'service', u'active', 
                            u'date.creation', u'date.modified']
                            
    def actions(self):
        actions = {
            u'catalogs.list': self.get_catalogs,
            u'catalogs.get': self.get_catalog,
            u'catalogs.add': self.add_catalog,
            u'catalogs.delete': self.delete_catalog,
           
            u'endpoints.list': self.get_endpoints,
            u'endpoints.get': self.get_endpoint,
            u'endpoints.add': self.add_endpoint,
            u'endpoints.delete': self.delete_endpoint,
            u'endpoints.ping': self.ping_endpoint,
            u'endpoints.pings': self.ping_endpoints
        }
        return actions

    #
    # catalogs
    #
    def get_catalogs(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/catalogs' % (self.cataloguri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get catalogs: %s' % res)  
        self.result(res, key=u'catalogs', headers=self.cat_headers)
    
    def get_catalog(self, catalog_id):
        uri = u'%s/catalogs/%s' % (self.cataloguri, catalog_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get catalog: %s' % res)
        self.result(res, key=u'catalog', headers=self.cat_headers, details=True)
        
    def add_catalog(self, name, zone):
        res = self.client.create_catalog(name, zone)
        self.logger.info(u'Add catalog: %s' % truncate(res))
        res = {u'msg':u'Add catalog %s' % res}
        self.result(res, headers=[u'msg'])
        
    def delete_catalog(self, catalog_id):
        res = self.client.delete_catalog(catalog_id)
        self.logger.info(u'Delete catalog: %s' % truncate(res))
        res = {u'msg':u'Delete catalog %s' % res}
        self.result(res, headers=[u'msg'])
    
    #
    # endpoints
    #    
    def get_endpoints(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/endpoints' % (self.cataloguri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get endpoints: %s' % res)  
        self.result(res, key=u'endpoints', headers=self.end_headers)
    
    def get_endpoint(self, endpoint_id):
        uri = u'%s/endpoints/%s' % (self.cataloguri, endpoint_id)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get endpoint: %s' % res)
        self.result(res, key=u'endpoint', headers=self.end_headers, details=True)
        
    def add_endpoint(self, name, catalog, service, uri):
        # if endpoint exist update it else create new one
        try:
            res = self.client.get_endpoint(name)
            res = self.client.update_endpoint(name, catalog_id=catalog, 
                                              name=name, 
                                              service=service, uri=uri)
        except Exception as ex:
            logger.error(ex, exc_info=1)
            res = self.client.create_endpoint(catalog, name, service, uri)
        self.logger.info(u'Add endpoint: %s' % truncate(res))
        res = {u'msg':u'Add catalog endpoint %s' % res}
        self.result(res, headers=[u'msg'])
        
    def delete_endpoint(self, endpoint_id):
        res = self.client.delete_endpoint(endpoint_id)
        self.logger.info(u'Delete endpoint: %s' % truncate(res))
        res = {u'msg':u'Delete catalog endpoint %s' % res}
        self.result(res, headers=[u'msg'])
        
    def ping_endpoint(self, endpoint_id):
        endpoint = self.client.get_endpoint(endpoint_id).get(u'endpoint')\
                                                        .get(u'endpoint')
        res = self.client.ping(endpoint=endpoint)
        
        self.logger.info(u'Ping endpoint %s: %s' % (endpoint, truncate(res)))
        self.result({u'endpoint':endpoint, u'ping':res}, 
                    headers=[u'endpoint', u'ping'])
        
    def ping_endpoints(self, catalog_id):
        services = []
        catalog = self.client.get_catalog(catalog_id)
        for v in catalog.get(u'services', {}):
            for v1 in v.get(u'endpoints', []):
                res = self.client.ping(endpoint=v1)
                services.append({u'service':v[u'service'], 
                                 u'endpoint':v1, 
                                 u'ping':res})
                self.logger.info(u'Ping endpoint %s: %s' % (v1, truncate(res)))
        self.result(services, headers=[u'service', u'endpoint', u'ping'])        
         