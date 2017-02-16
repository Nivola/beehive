'''
Usage: manage.py [OPTION]... provider <provider_id> [PARAMs]...

Tenant api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    
PARAMS:
    regions list
    regions get <id>
    regions add <name> <desc> <geo_area>
    regions update <id> <field>=<value>    field: name, desc, geo_area
    regions delete <id>

Exit status:
 0  if OK,
 1  if problems occurred

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
    def __init__(self, auth_config, containerid):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/providers/%s' % containerid
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'regions.list': self.list_regions,
            u'regions.get': self.get_regions,
            u'regions.add': self.add_regions,
            u'regions.update': self.update_regions,
            u'regions.delete': self.delete_regions,
            

        }
        return actions    
    
    #
    # regions
    #
    def list_regions(self):
        uri = u'%s/regions/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get regions: %s' % self.pp.pformat(res))
        self.msg = res[u'regions']
        return res[u'regions']

    def get_regions(self, oid):
        uri = u'%s/regions/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get region: %s' % self.pp.pformat(res))
        self.msg = res[u'regions']
        return res[u'regions']
    
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
        self.msg = u'Add region: %s' % self.pp.pformat(res)
        return res
    
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
        self.msg = u'Update region: %s' % self.pp.pformat(res)
        return res    
        
    def delete_regions(self, oid):
        uri = u'%s/regions/%s/' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete region: %s' % oid)
        self.msg = u'Delete region: %s' % oid

def provider_main(auth_config, format, opts, args):
    """
    
    :param auth_config: {u'pwd': u'..', 
                         u'endpoint': u'http://10.102.160.240:6060/api/', 
                         u'user': u'admin@local'}
    """
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print __doc__
            return 0
    
    try:
        args[1]
    except:
        print __doc__
        return 0
    
    containerid = args.pop(0)
    
    client = ProviderManager(auth_config, containerid)
    
    actions = client.actions()
    
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else:
        raise Exception(u'Tenant entity and/or command are not correct')
        return 1
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Tenant entity and/or command are not correct')
        return 1
            
    if format == u'text':
        for i in res:
            pass
    else:
        print(u'Tenant response:')
        print(u'')
        if isinstance(client.msg, dict) or isinstance(client.msg, list):
            client.pp.pprint(client.msg)
        else:
            print(client.msg)
        
    return 0