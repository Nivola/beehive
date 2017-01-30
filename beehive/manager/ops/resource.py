'''
Usage: manage.py [OPTION]... resource [PARAMs]...

Resource api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    
PARAMS:
    containers list
    container get <id>
    container add vsphere tst-vecenter-01 \{\"vcenter\":\{\"host\":\"tst-vcenter.tstsddc.csi.it\",\"user\":\"administrator@tstsddc.csi.it\",\"pwd\":\"cs1\$topix\",\"port\":443,\"timeout\":5,\"verified\":false\},\"nsx\":\{\"host\":\"tst-nsxmanager.tstsddc.csi.it\",\"port\":443,\"user\":\"admin\",\"pwd\":\"Cs1\$topix\",\"verified\":false,\"timeout\":5\}\}
    container delete <id>

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

class ResourceManager(ApiManager):
    def __init__(self, auth_config):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/resource'
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'containers.list': self.get_resource_containers,
            u'container_types.list': self.get_resource_container_types,
            u'container.get': self.get_resource_container,
            u'container.count': self.get_resource_container_rescount,
            u'container.perms': self.get_resource_container_perms,
            u'container.add': self.add_resource_container,
            u'container.delete': self.delete_resource_container,
            
            u'tags.list': self.test_get_tags,
            u'tag.get': self.test_get_tag,
            u'tags.count': self.test_count_tags,
            u'tags.occurrences': self.test_get_tags_occurrences,
            u'tag.perms': self.test_get_tag_perms,
            u'tag.list': self.test_get_tags,
            u'tag.add': self.test_add_tags,
            u'tag.update': self.test_update_tag,
            u'tag.delete': self.test_delete_tag,
        }
        return actions    
    
    #
    # resource containers
    #
    def get_resource_containers(self, tags=None):
        uri = u'%s/containers/' % self.baseuri
        if tags is not None:
            headers = {u'tags':tags}
        else:
            headers = None
        res = self._call(uri, u'GET', headers=headers)
        self.logger.info(u'Get resource containers: %s' % res)
        self.msg = res[u'containers']
        return res
    
    def get_resource_container_types(self, tags=None):
        uri = u'%s/container/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container types: %s' % res)
        self.msg = res[u'container_types']
        return res    

    def get_resource_container(self, value):
        uri = u'%s/container/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container: %s' % res)
        self.msg = res[u'container']
        return res
    
    def get_resource_container_rescount(self, value):
        uri = u'%s/container/%s/count/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container resource count: %s' % res)
        self.msg = res
        return res
    
    def get_resource_container_perms(self, value):
        uri = u'%s/container/%s/perms/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container perms: %s' % res)
        self.msg = res[u'perms']
        return res      
    
    def add_resource_container(self, ctype, name, conn):
        self.logger.debug(conn)
        data = {
            u'container':{
                u'type':ctype, 
                u'name':name, 
                u'conn':json.loads(conn)   
            }
        }
        uri = u'%s/container/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add resource container: %s' % res)
        self.msg = u'Add resource container: %s' % res
        return res
        
    def delete_resource_container(self, oid):
        uri = u'%s/container/%s/' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete resource container: %s' % oid)
        self.msg = u'Delete resource container: %s' % oid

    #
    # tags
    #
    def test_add_tags(self, value):
        data = {
            u'tag':{
                u'value':value
            }
        }
        uri = u'%s/tag/' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)

    def test_count_tags(self):
        uri = u'%s/tags/count/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        
    def test_get_tags_occurrences(self):
        uri = u'%s/tags/occurrences/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)        

    def test_get_tags(self):
        uri = u'%s/tags/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res[u'tags']
        
    def test_get_tag(self, value):
        uri = u'%s/tag/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res[u'tags']

    def test_get_tag_perms(self, value):
        uri = u'%s/tag/%s/perms/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.msg = res[u'perms']
        
    def test_update_tag(self, value, new_value):
        data = {
            u'tag':{
                u'value':new_value
            }
        }
        uri = u'%s/tag/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        
    def test_delete_tag(self, value):
        data = ''
        uri = u'%s/tag/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        self.logger.info(res)
        self.msg = u'Delete tag: %s' % value

def resource_main(auth_config, format, opts, args):
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
    
    client = ResourceManager(auth_config)
    
    actions = client.actions()
    
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else: 
        raise Exception(u'Resource entity and/or command are not correct')
        return 1
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Resource entity and/or command are not correct')
        return 1
            
    if format == u'text':
        for i in res:
            pass
    else:
        print(u'Resource response:')
        print(u'')
        if isinstance(client.msg, dict) or isinstance(client.msg, list):
            client.pp.pprint(client.msg)
        else:
            print(client.msg)
        
    return 0