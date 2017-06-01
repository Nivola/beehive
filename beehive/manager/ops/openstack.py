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
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class Actions(object):
    """
    """
    def __init__(self, parent, name, other_headers):
        self.parent = parent
        self.name = name
        self.headers = other_headers
    
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
        self.parent.logger.info(u'Get %s: %s' % (self.name, truncate(res)))
        self.parent.result(res, other_headers=self.headers, key=self.name+u's')

    def get(self, oid):
        uri = u'%s/%ss/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'GET')
        self.parent.logger.info(u'Get %s: %s' % (self.name, truncate(res)))
        self.parent.result(res, other_headers=self.headers, key=self.name)
    
    def add(self, data):
        data = self.parent.load_config(data)
        uri = u'%s/%ss/' % (self.parent.baseuri, self.name)
        res = self.parent._call(uri, u'POST', data=data)
        self.parent.logger.info(u'Add %s: %s' % (self.name, truncate(res)))
        if self.parent.format == u'table':
            self.parent.format = u'yaml'        
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
        self.parent.logger.info(u'Update %s: %s' % (self.name, truncate(res)))
        self.parent.result(res)

    def delete(self, oid):
        uri = u'%s/%ss/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'DELETE')
        self.parent.logger.info(u'Delete %s: %s' % (self.name, oid))
        if self.parent.format == u'table':
            self.parent.format = u'yaml'        
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

class OpenstackManager(ApiManager):
    """
    SECTION: 
        openstack    
    
    PARAMs:
        <ENTITY> list [filters: <field>=<value>]   field: name, tags, ext_id, parent_id
        <ENTITY> get <id>
        <ENTITY> add <file data in json>
        <ENTITY> update <id> <field>=<value>    field: name, desc, geo_area
        <ENTITY> delete <id>
        
    ENTITY:
        domains
        projects
        servers
        volumes
        networks
        ports
        flavors
        images
    """
    __metaclass__ = abc.ABCMeta
    
    class_names = [
        (u'domain', []),
        (u'project', []),
        (u'server', []),
        (u'volume', []),
        (u'network', []),
        (u'port', []),
        (u'flavor', []),
        (u'image', []),
    ]

    def __init__(self, auth_config, env, frmt=u'json', containerid=None):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/openstacks/%s' % containerid
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
        
        self.__actions = {}
        
        for class_name, other_headers in self.class_names:
            Actions(self, class_name, other_headers).register()
    
    @staticmethod
    def get_params(args):
        try: cid = int(args.pop(0))
        except:
            raise Exception(u'ERROR : Orchestrator id is missing')
        return {u'containerid':cid}    
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)
        
'''
doc = OpenstackManager.__doc__
for class_name in OpenstackManager.class_names:
    doc += Actions(None, class_name).doc()
OpenstackManager.__doc__ = doc'''
