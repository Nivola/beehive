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

logger = logging.getLogger(__name__)

class ResourceManager(ApiManager):
    """
    CMD: 
        resource
        
    PARAMS:
        containers list
        containers types
        containers get <id>
        containers ping <id>
        containers perms <id>
        containers roles <id>
        containers add vsphere tst-vecenter-01 \{\"vcenter\":\{\"host\":\"tst-vcenter.tstsddc.csi.it\",\"user\":\"administrator@tstsddc.csi.it\",\"pwd\":\"cs1\$topix\",\"port\":443,\"timeout\":5,\"verified\":false\},\"nsx\":\{\"host\":\"tst-nsxmanager.tstsddc.csi.it\",\"port\":443,\"user\":\"admin\",\"pwd\":\"Cs1\$topix\",\"verified\":false,\"timeout\":5\}\}
        containers add openstack tst-opstk-redhat-01 \{\"api\":\{\"user\":\"admin\",\"project\":\"admin\",\"domain\":\"default\",\"uri\":\"http://10.102.184.200:5000/v3\",\"timeout\":5,\"pwd\":\"8fAwzAJAHQFMcJfrntpapzDpC\",\"region\":\"regionOne\"\}\}
        containers delete <id>
        containers tag-add <id> <tag>
        containers tag-delete <id> <tag>
        containers tags <id>
        
        tags list
        tag get <tag>
        tags count 
        tags occurrences 
        tag perms <tag>
        tag add <value>
        tag update  <value> <new_value>
        tag delete <value>
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0'
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'containers.list': self.get_resource_containers,
            u'containers.types': self.get_resource_container_types,
            u'containers.get': self.get_resource_container,
            u'containers.count': self.get_resource_container_rescount,
            u'containers.perms': self.get_resource_container_perms,
            u'containers.roles': self.get_resource_container_roles,
            u'containers.ping': self.ping_container,
            u'containers.add': self.add_resource_container,
            u'containers.delete': self.delete_resource_container,
            u'containers.tag-add': self.add_container_tag,
            u'containers.tag-delete': self.delete_container_tag,
            u'containers.tags': self.get_container_tag,
            
            u'tags.list': self.test_get_tags,
            u'tags.get': self.test_get_tag,
            u'tags.count': self.test_count_tags,
            u'tags.occurrences': self.test_get_tags_occurrences,
            u'tags.perms': self.test_get_tag_perms,
            u'tags.add': self.test_add_tags,
            u'tags.update': self.test_update_tag,
            u'tags.delete': self.test_delete_tag,
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
        self.result(res)
    
    def get_resource_container_types(self, tags=None):
        uri = u'%s/containers/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container types: %s' % res)
        self.result(res)

    def get_resource_container(self, value):
        uri = u'%s/containers/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container: %s' % res)
        self.result(res)
    
    def get_resource_container_rescount(self, value):
        uri = u'%s/containers/%s/count/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container resource count: %s' % res)
        self.result(res)
    
    def get_resource_container_perms(self, value):
        uri = u'%s/containers/%s/perms/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container perms: %s' % res)
        self.result(res)
        
    def get_resource_container_roles(self, value):
        uri = u'%s/containers/%s/roles/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource container roles: %s' % res)
        self.result(res)            
    
    def ping_container(self, contid):
        uri = u'%s/containers/%s/ping/' % (self.baseuri, contid)  
        res = self._call(uri, u'GET')      
        self.logger.info(u'Ping container %s: %s' % (contid, res))
        self.result(res)      
    
    def add_resource_container(self, ctype, name, conn):
        conn = self.load_config(conn)
        data = {
            u'containers':{
                u'type':ctype, 
                u'name':name, 
                u'conn':conn
            }
        }
        uri = u'%s/containers/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add resource container: %s' % res)
        self.result(res)
        
    def delete_resource_container(self, oid):
        uri = u'%s/containers/%s/' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete resource container: %s' % oid)
        self.result(True)

    def get_container_tag(self, contid):
        uri = u'%s/containers/%s/tags/' % (self.baseuri, contid)        
        res = self._call(uri, u'GET')
        self.result(res)
        
    def add_container_tag(self, contid, tag):
        data = {
            u'resource-tags':{
                u'cmd':u'add',
                u'value':tag
            }
        }
        uri = u'%s/containers/%s/tags/' % (self.baseuri, contid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)
        
    def delete_container_tag(self, contid, tag):
        data = {
            u'resource-tags':{
                u'cmd':u'remove',
                u'value':tag
            }
        }
        uri = u'%s/containers/%s/tags/' % (self.baseuri, contid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)

    #
    # tags
    #
    def test_add_tags(self, value):
        data = {
            u'resource-tags':{
                u'value':value
            }
        }
        uri = u'%s/resource-tags/' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        self.result({u'tags-id':res})

    def test_count_tags(self):
        uri = u'%s/resource-tags/count/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def test_get_tags_occurrences(self):
        uri = u'%s/resource-tags/occurrences/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def test_get_tags(self):
        uri = u'%s/resource-tags/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def test_get_tag(self, value):
        uri = u'%s/resource-tags/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def test_get_tag_perms(self, value):
        uri = u'%s/resource-tags/%s/perms/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res[u'perms'])
        
    def test_update_tag(self, value, new_value):
        data = {
            u'resource-tags':{
                u'value':new_value
            }
        }
        uri = u'%s/resource-tags/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def test_delete_tag(self, value):
        uri = u'%s/resource-tags/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        self.logger.info(res)
        self.result(res)
        