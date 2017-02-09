'''
Usage: manage.py [OPTION]... monitor [PARAMs]...

Tenant api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    
PARAMS:
    types list
    type get prova
    type add beehive task.ping_cloudapi 'http://localhost:8080
    type delete beehive
    
    nodes list
    node get 51
    node ping 51
    node perms 6
    node add pippo pippo beehive {\"uri\":\"dddd\"} {}
    node delete <id>

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

class TenantManager(ApiManager):
    def __init__(self, auth_config, containerid):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/resource/tenant/%s' % containerid
        self.subsystem = u'tenant'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'clouddomains.list': self.get_cloud_domains,
            u'clouddomain.get': self.get_cloud_domain,
            u'clouddomain.add': self.add_cloud_domain,
            u'clouddomain.delete': self.delete_cloud_domain,
            

        }
        return actions    
    
    #
    # cloud domains
    #
    def get_cloud_domains(self):
        uri = u'%s/cloud_domains/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get cloud domains: %s' % self.pp.pformat(res))
        self.msg = res[u'cloud_domains']
        return res[u'cloud_domains']

    def get_cloud_domain(self, value):
        uri = u'%s/cloud_domain/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get cloud domain: %s' % self.pp.pformat(res))
        self.msg = res[u'cloud_domain']
        return res[u'cloud_domain']
    
    def add_cloud_domain(self, *args):
        data = self.load_config_file(args.pop(0)) 
        
        
        data = {
            u'cloud_domain':{
                u'value':value, 
                u'action':action, 
                u'template':template   
            }
        }
        uri = u'%s/cloud_domain/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add cloud domain: %s' % self.pp.pformat(res))
        self.msg = u'Add cloud domain: %s' % self.pp.pformat(res)
        return res
        
    def delete_cloud_domain(self, value):
        uri = u'%s/cloud_domain/%s/' % (self.baseuri, value)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete cloud domain: %s' % value)
        self.msg = u'Delete cloud domain: %s' % value

def tenant_main(auth_config, format, opts, args):
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
    
    client = TenantManager(auth_config, containerid)
    
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