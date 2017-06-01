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
from pygments.formatters import Terminal256Formatter
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Token
from pygments.style import Style
from pygments import format

logger = logging.getLogger(__name__)

class ListStyle(Style):
    default_style = ''
    styles = {
        Token.Text.Whitespace: u'#fff',
        Token.Name: u'bold #ffcc66',
        Token.Literal.String: u'#fff',
        Token.Literal.Number: u'#0099ff',
        Token.Operator: u'#ff3300' 
    }

class Actions(object):
    """
    """
    def __init__(self, parent, name, other_headers):
        self.parent = parent
        self.name = name
        self.headers = other_headers
    
    def doc(self):
        return """
        %ss list [filters: <field>=<value>]   field: name, tags, ext_id, parent_id
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
        
        if self.parent.format == u'text':
            res.pop(u'count')
            
            def print_dict(data):
                for k,v in data.items():
                    yield (Token.Name, u'  %s' % k)
                    yield (Token.Text.Whitespace, u' : ')
                    yield (Token.Literal.String, u'%s' % v)
            
            def create_data():
                for item in res.values()[0]:
                    for key in [u'id', u'uuid', u'name']:
                        yield (Token.Name, u'  %-10s' % key)
                        yield (Token.Text.Whitespace, u' : ')
                        yield (Token.Literal.String, u'%s\n' % item.get(key))
                        
                    yield (Token.Name, u'  %-10s' % u'parent')
                    yield (Token.Text.Whitespace, u' : ')
                    yield (Token.Literal.String, u'%s\n' % item.get(u'parent_name'))
                    
                    configs = item.get(u'attributes').pop(u'configs')
                    yield (Token.Name, u'  %-10s' % u'configs')
                    if len(configs.keys()) == 0:
                        yield (Token.Text.Whitespace, u' : ')
                        yield (Token.Literal.Number, u'Empty\n')
                    else:
                        yield (Token.Text.Whitespace, u' :\n')
                    for k,v in configs.items():
                        yield (Token.Name, u'   - %-12s' % k)
                        yield (Token.Text.Whitespace, u' : ')
                        yield (Token.Literal.String, u'%s\n' % v)
                        
                    attribs = item.get(u'attributes')
                    yield (Token.Name, u'  %-10s' % u'attribs')
                    if len(attribs.keys()) == 0:
                        yield (Token.Text.Whitespace, u' : ')
                        yield (Token.Literal.Number, u'Empty\n')
                    else:
                        yield (Token.Text.Whitespace, u' :\n')
                    for k,v in attribs.items():
                        yield (Token.Name, u'   - %-12s' % k)
                        yield (Token.Text.Whitespace, u' : ')
                        yield (Token.Literal.String, u'%s\n' % v)                        

                    yield (Token.Text.Whitespace, u' ===========================\n')
                    
            data = format(create_data(), Terminal256Formatter(style=ListStyle))
            print(data)
        else:
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

class InstanceActions(Actions):
    """
    """
    def list(self, *args):
        data = self.parent.format_http_get_query_params(*args)
        uri = u'%s/%ss/' % (self.parent.baseuri, self.name)
        res = self.parent._call(uri, u'GET', data=data)
        self.parent.logger.info(u'Get %s: %s' % (self.name, truncate(res)))
        if self.format == u'table':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__tabularprint(data)        
        self.parent.result(res)
        
    def register(self):
        res = {
        }
        self.parent.add_actions(res)        

class ProviderManager(ApiManager):
    """
    SECTION: 
        provider    
    
    PARAMs:
        <ENTITY> list [filters: <field>=<value>]   field: name, tags, ext_id, parent_id
        <ENTITY> get <id>
        <ENTITY> add <file data in json>
        <ENTITY> update <id> <field>=<value>    field: name, desc, geo_area
        <ENTITY> delete <id>
        
    ENTITY:
        regions
        sites
        site-networks
        gateways
        super-zones
        availability-zones
        vpcs
        security-groups
        rules
        images
        flavors
        instances
    """
    __metaclass__ = abc.ABCMeta
    
    class_names = [
        (u'region', []),
        (u'site', []),
        (u'site-network', []),
        (u'gateway', []),
        (u'super-zone', []),
        (u'availability-zone', []),
        (u'vpc', []),
        (u'security-group', []),
        (u'rule', []),
        (u'image', []),
        (u'flavor', []),
        (u'instance', [u'networks.0.ip', u'flavor.vcpus', u'flavor.memory'])
    ]

    def __init__(self, auth_config, env, frmt=u'json', containerid=None):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/providers/%s' % containerid
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
        
        self.__actions = {}
        
        for class_name, other_headers in self.class_names:
            Actions(self, class_name, other_headers).register()
            
        # custom actions
        #InstanceActions(self, u'instance').register()            
    
    @staticmethod
    def get_params(args):
        try: cid = int(args.pop(0))
        except:
            raise Exception(u'ERROR : Provider id is missing')
        return {u'containerid':cid}
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)
        
#doc = ProviderManager.__doc__
#for class_name in ProviderManager.class_names:
#    doc += Actions(None, class_name).doc()
#ProviderManager.__doc__ = doc
