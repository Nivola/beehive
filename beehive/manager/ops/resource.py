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
    SECTION: 
        resource
        
    PARAMS:
        resources list <field>=<value>    field: name
                                                 active
                                                 type
                                                 container
                                                 creation-date
                                                 modification-date
                                                 attribute
                                                 parent-id
                                                 type-filter
                                                 tags
            Ex. type-filter=%folder.server% name=tst-b%
                type=vsphere.datacenter
        resources types
        resources get <id|uuid>
        resources tree <id|uuid>
        resources perms <id|uuid>
        resources roles <id|uuid>
        resources add 
        resources delete <id|uuid>
        resources tag-add <id|uuid> <tag>
        resources tag-delete <id|uuid> <tag>
        resources tags <id|uuid>    
    
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
        tags get <tag>
        tags count 
        tags occurrences 
        tags perms <tag>
        tags add <value>
        tags update  <value> <new_value>
        tags delete <value>
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
            
            u'resources.list': self.get_resources,
            u'resources.types': self.get_resource_types,
            u'resources.get': self.get_resource,
            u'resources.tree': self.get_resource_tree,
            u'resources.count': self.get_resource_rescount,
            u'resources.perms': self.get_resource_perms,
            u'resources.roles': self.get_resource_roles,
            u'resources.add': self.add_resource,
            u'resources.delete': self.delete_resource,
            u'resources.tag-add': self.add_resource_tag,
            u'resources.tag-delete': self.delete_resource_tag,
            u'resources.tags': self.get_resource_tag,
            u'resources.links': self.get_resource_links,
            u'resources.linked': self.get_resource_linked,
            
            u'tags.list': self.test_get_tags,
            u'tags.get': self.test_get_tag,
            u'tags.count': self.test_count_tags,
            u'tags.occurrences': self.test_get_tags_occurrences,
            u'tags.perms': self.test_get_tag_perms,
            u'tags.add': self.test_add_tags,
            u'tags.update': self.test_update_tag,
            u'tags.delete': self.test_delete_tag,
            
            u'links.list': self.test_get_links,
            u'links.get': self.test_get_tag,
            u'links.count': self.test_count_links,
            u'links.perms': self.test_get_tag_perms,
            u'links.add': self.test_add_links,
            u'links.update': self.test_update_link,
            u'links.delete': self.test_delete_link,            
        }
        return actions
    
    #
    # resources
    #
    def get_resources(self, *args):
        data = self.format_http_get_query_params(*args)
        uri = u'%s/resources/' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get resources: %s' % res)
        self.result(res)
    
    def get_resource_types(self, tags=None):
        uri = u'%s/resources/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource types: %s' % res)
        self.result(res)

    def get_resource(self, value):
        uri = u'%s/resources/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource: %s' % res)
        self.result(res)
    
    def __print_tree(self, resource, space=u'   '):
        for child in resource.get(u'children', []):
            relation = child.get(u'relation')
            if relation is None:
                print u'%s=> [%s] %s - %s' % (space, child.get(u'type'),
                                              child.get(u'name'), 
                                              child.get(u'id'))
            else:
                print u'%s--%s--> [%s] %s - %s' % (space, relation, 
                                                   child.get(u'type'),
                                                   child.get(u'name'), 
                                                   child.get(u'id'))
            self.__print_tree(child, space=space+u'   ')
    
    def get_resource_tree(self, value):
        uri = u'%s/resources/%s/tree/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource tree: %s' % res)
        if self.format == u'text':
            res = res[u'resource-tree']
            print u'[%s] %s - %s' % (res.get(u'type'), 
                                     res.get(u'name'), 
                                     res.get(u'id'))
            self.__print_tree(res)
        else:
            self.result(res)        
    
    def get_resource_rescount(self, value):
        uri = u'%s/resources/%s/count/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource count: %s' % res)
        self.result(res)
    
    def get_resource_perms(self, value):
        uri = u'%s/resources/%s/perms/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource perms: %s' % res)
        self.result(res)
        
    def get_resource_roles(self, value):
        uri = u'%s/resources/%s/roles/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource roles: %s' % res)
        self.result(res)  
    
    def add_resource(self, ctype, name, conn):
        conn = self.load_config(conn)
        data = {
            u'resources':{
                u'type':ctype, 
                u'name':name, 
                u'conn':conn
            }
        }
        uri = u'%s/resources/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add resource: %s' % res)
        self.result(res)
        
    def delete_resource(self, oid):
        uri = u'%s/resources/%s/' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete resource: %s' % oid)
        self.result(True)

    def get_resource_tag(self, oid):
        uri = u'%s/resources/%s/tags/' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.result(res)
        
    def add_resource_tag(self, oid, tag):
        data = {
            u'resource-tags':{
                u'cmd':u'add',
                u'value':tag
            }
        }
        uri = u'%s/resources/%s/tags/' % (self.baseuri, oid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)
        
    def delete_resource_tag(self, oid, tag):
        data = {
            u'resource-tags':{
                u'cmd':u'remove',
                u'value':tag
            }
        }
        uri = u'%s/resources/%s/tags/' % (self.baseuri, oid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)    
    
    def get_resource_links(self, oid):
        uri = u'%s/resources/%s/links/' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.result(res)
        
    def get_resource_linked(self, oid):
        uri = u'%s/resources/%s/linked/' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.result(res)
    
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
        self.result(res)

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
        
    #
    # links
    #
    def test_add_links(self, value):
        data = {
            u'resource-links':{
                u'value':value
            }
        }
        uri = u'%s/resource-links/' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        self.result(res)

    def test_count_links(self):
        uri = u'%s/resource-links/count/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def test_get_links_occurrences(self):
        uri = u'%s/resource-links/occurrences/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def test_get_links(self):
        uri = u'%s/resource-links/' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def test_get_link(self, value):
        uri = u'%s/resource-links/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def test_get_link_perms(self, value):
        uri = u'%s/resource-links/%s/perms/' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res[u'perms'])
        
    def test_update_link(self, value, new_value):
        data = {
            u'resource-links':{
                u'value':new_value
            }
        }
        uri = u'%s/resource-links/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def test_delete_link(self, value):
        uri = u'%s/resource-links/%s/' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        self.logger.info(res)
        self.result(res)

        
        