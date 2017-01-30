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
    def __init__(self, auth_config):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/tenant'
        self.subsystem = u'tenant'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'types.list': self.get_node_types,
            u'type.get': self.get_node_type,
            u'type.add': self.add_node_type,
            u'type.delete': self.delete_node_type,
            
            u'nodes.list': self.get_nodes,
            u'node.get': self.get_node,
            u'node.ping': self.ping_node,
            u'node.perms': self.get_node_permissions,
            u'node.add': self.add_node,
            u'node.update': self.update_node,
            u'node.delete': self.delete_node,
            u'node.tags': self.get_node_tag,
            u'node.add_tag': self.add_node_tag,
            u'node.del_tag': self.remove_node_tag,
            u'node.task': self.exec_node_task,
        }
        return actions    
    
    #
    # node types
    #
    def get_node_types(self):
        uri = u'%s/node/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get node types: %s' % self.pp.pformat(res))
        self.msg = res[u'node_types']
        return res[u'node_types']

    def get_node_type(self, value):
        uri = u'%s/node/type/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get node type: %s' % self.pp.pformat(res))
        self.msg = res[u'node_type']
        return res[u'node_type']
    
    def add_node_type(self, value, action, template):
        global oid
        data = {
            u'node_type':{
                u'value':value, 
                u'action':action, 
                u'template':template   
            }
        }
        uri = u'%s/node/type/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add node type: %s' % self.pp.pformat(res))
        self.msg = u'Add node type: %s' % self.pp.pformat(res)
        return res
        
    def delete_node_type(self, value):
        uri = u'%s/node/type/%s/' % (self.baseuri, value)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete node type: %s' % value)
        self.msg = u'Delete node type: %s' % value

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
    
    client = TenantManager(auth_config)
    
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