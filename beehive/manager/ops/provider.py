'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager
import sys

logger = logging.getLogger(__name__)

class ProviderManager(ApiManager):
    """
    CMD: 
        provider    
    
    PARAMs:
        regions list
        regions get <id>
        regions add <name> <desc> <geo_area>
        regions update <id> <field>=<value>    field: name, desc, geo_area
        regions delete <id>    
    """
    def __init__(self, auth_config, env, frmt=u'json', containerid=None):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/providers/%s' % containerid
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            
            u'sites.list': self.list_sites,
            u'sites.get': self.get_sites,
            u'sites.add': self.add_sites,
            u'sites.update': self.update_sites,
            u'sites.delete': self.delete_sites,            
            
            u'regions.list': self.list_regions,
            u'regions.get': self.get_regions,
            u'regions.add': self.add_regions,
            u'regions.update': self.update_regions,
            u'regions.delete': self.delete_regions
        }
        return actions    
    
    #
    # sites
    #
    def list_sites(self):
        uri = u'%s/sites/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get sites: %s' % self.pp.pformat(res))
        self.result(res)

    def get_sites(self, oid):
        uri = u'%s/sites/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get site: %s' % self.pp.pformat(res))
        self.result(res)
    
    def add_sites(self, data):
        data = self.load_config(data)
        uri = u'%s/sites/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add site: %s' % self.pp.pformat(res))
        self.result(res)
    
    def update_sites(self, oid, *args):
        #data = self.load_config_file(args.pop(0)) 
        
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        
        data = {
            u'sites':val
        }
        uri = u'%s/sites/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update site: %s' % self.pp.pformat(res))
        self.result(res)
        
    def delete_sites(self, oid):
        uri = u'%s/sites/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete site: %s' % oid)
        self.result(res)    
    
    #
    # regions
    #
    def list_regions(self):
        uri = u'%s/regions/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get regions: %s' % self.pp.pformat(res))
        self.result(res)

    def get_regions(self, oid):
        uri = u'%s/regions/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get region: %s' % self.pp.pformat(res))
        self.result(res)
    
    def add_regions(self, name, desc, geo_area):
        #data = self.load_config_file(args.pop(0)) 
        
        data = {
            u'regions':{
                u'name':name,
                u'desc':desc,
                u'geo-area':geo_area,
                u'coords':None,
            }
        }
        uri = u'%s/regions/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add region: %s' % self.pp.pformat(res))
        self.result(res)
    
    def update_regions(self, oid, *args):
        #data = self.load_config_file(args.pop(0)) 
        
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        
        data = {
            u'regions':val
        }
        uri = u'%s/regions/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update region: %s' % self.pp.pformat(res))
        self.result(res)
        
    def delete_regions(self, oid):
        uri = u'%s/regions/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete region: %s' % oid)
        self.result(res)
