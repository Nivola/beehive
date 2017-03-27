'''
Created on Mar 24, 2017

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
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class AuthManager(ApiManager):
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
        self.logger.info(u'Get resources: %s' % truncate(res))
        self.result(res)
    
    def get_resource_types(self, tags=None):
        uri = u'%s/resources/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource types: %s' % truncate(res))
        self.result(res)    