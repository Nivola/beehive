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
from beehive.manager import ApiManager, ComponentManager
import sys
import abc

logger = logging.getLogger(__name__)

class Actions(object):
    """
    """
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
    
    def doc(self):
        return """
        %ss list [filters]
        %ss get <id>
        %ss add <file data in json>
        %ss update <id> <field>=<value>    field: name, desc, geo_area
        %ss delete <id>    
        """ % (self.name, self.name, self.name, self.name, self.name)
    
    def list(self, *args):
        data = self.parent.format_http_get_query_params(*args)
        uri = u'%s/%ss/' % (self.parent.baseuri, self.name)
        res = self.parent._call(uri, u'GET', data=data)
        self.parent.logger.info(u'Get %s: %s' % (self.name, 
                                          self.parent.pp.pformat(res)))
        self.parent.result(res)

    def get(self, oid):
        uri = u'%s/%ss/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'GET')
        self.parent.logger.info(u'Get %s: %s' % (self.name, 
                                          self.parent.pp.pformat(res)))
        self.parent.result(res)
    
    def add(self, data):
        data = self.parent.load_config(data)
        uri = u'%s/%ss/' % (self.parent.baseuri, self.name)
        res = self.parent._call(uri, u'POST', data=data)
        self.parent.logger.info(u'Add %s: %s' % (self.name, 
                                          self.parent.pp.pformat(res)))
        self.parent.result(res)

    def update(self, oid, *args):
        #data = self.load_config_file(args.pop(0)) 
        
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        
        data = {
            u'sites':val
        }
        uri = u'%s/%5s/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'PUT', data=data)
        self.parent.logger.info(u'Update %s: %s' % (self.name, 
                                             self.parent.pp.pformat(res)))
        self.parent.result(res)

    def delete(self, oid):
        uri = u'%s/%ss/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'DELETE')
        self.parent.logger.info(u'Delete %s: %s' % (self.name, oid))
        self.parent.result(res)
    
    def register(self):
        res = {
            u'%ss.list' % self.name: self.list,
            u'%ss.get' % self.name: self.get,
            u'%ss.add' % self.name: self.add,
            u'%ss.update' % self.name: self.update,
            u'%ss.delete' % self.name: self.delete
        }
        self.parent.add_actions(res)

class ProviderManager(ApiManager):
    """
    CMD: 
        provider    
    
    PARAMs:  
    """
    __metaclass__ = abc.ABCMeta
    
    class_names = {
        u'region',
        u'site',
        u'site-network',
        u'gateway',
        u'super-zone',
        u'availability-zone',
        u'vpc',
        u'security-group',
        u'rule',
    }

    def __init__(self, auth_config, env, frmt=u'json', containerid=None):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/providers/%s' % containerid
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
        
        self.__actions = {}
        
        for class_name in self.class_names:
            Actions(self, class_name).register()
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)
        
doc = ProviderManager.__doc__
for class_name in ProviderManager.class_names:
    doc += Actions(None, class_name).doc()
ProviderManager.__doc__ = doc
