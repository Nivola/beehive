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
from beecell.simple import truncate
from pygments.formatters import Terminal256Formatter
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Token
from pygments.style import Style     
from pygments import format

logger = logging.getLogger(__name__)

class TreeStyle(Style):
    default_style = ''
    styles = {
        Token.Text.Whitespace: u'#fff',
        Token.Name: u'bold #ffcc66',
        Token.Literal.String: u'#fff',
        Token.Literal.Number: u'#0099ff',
        Token.Operator: u'#ff3300' 
    } 

class ResourceManager(ApiManager):
    """
    SECTION: 
        resource
        
    PARAMS:
        resources list <field>=<value>    
            field: tags, type, objid, name, ext_id, container, attribute,
                   parent, state
            Ex. type=%folder.server%,vsphere.datacenter
        resources types
        resources get <id>
        resources tree <id>
        resources perms <id>
        resources roles <id>
        resources add 
        resources delete <id>
        resources tag-add <id> <tag>
        resources tag-delete <id> <tag>
        resources tags <id>
    
        containers list
        containers types
        containers get <id>
        containers ping <id>
        containers perms <id>
        containers add <type> <name> <conn.json>    
            create a new resource resourcecontainer type: vsphere, openstack, provider
        containers delete <id>                      delete a resource resourcecontainer
        containers tag-add <id> <tag>               add tag to a resource resourcecontainer
        containers tag-delete <id> <tag>            remove tag from a resource resourcecontainer
        containers tags <id>                        get tags of a resource resourcecontainer
        containers discover-classes <cid>           get resourcecontainer resource classes
        containers discover <cid> <class>           discover resourcecontainer <class> resources
        containers synchronize <cid> <class>        synchronize resourcecontainer <class> resources
        
        tags list <field>=<value>
            field: value, container, resource, link
        tags get <tag>
        tags count 
        tags occurrences 
        tags perms <tag>
        tags add <value>
        tags update <value> <new_value>
        tags delete <value>
        
        links list
        links count         
        links get <link_id>
        links tags <link_id> 
        links perms <link_id>
        links add <link_id>
        links update <link_id> <new_value>
        links delete <link_id>
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0'
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
        self.res_headers = [u'id', u'uuid', u'definition', u'name', u'container.name',
                            u'parent.name', u'active', u'state', u'date.creation',
                            u'date.modified']
        self.cont_headers = [u'id', u'uuid', u'category', u'definition', 
                             u'name', u'active', u'state', u'date.creation',
                             u'date.modified']
        self.tag_headers = [u'id', u'uuid', u'name', u'date.creation',
                             u'date.modified', u'resources', u'containers',
                             u'links']
        self.link_headers = [u'id', u'uuid', u'name', u'active', 
                             u'details.start_resource.id', 
                             u'details.end_resource.id',
                             u'details.attributes', u'date.creation',
                             u'date.modified']
    
    def actions(self):
        actions = {
            u'containers.list': self.get_resource_containers,
            u'containers.types': self.get_resource_container_types,
            u'containers.get': self.get_resource_container,
            #u'containers.count': self.get_resource_container_rescount,
            u'containers.perms': self.get_resource_container_perms,
            #u'containers.roles': self.get_resource_container_roles,
            u'containers.ping': self.ping_resource_container,
            u'containers.add': self.add_resource_container,
            u'containers.delete': self.delete_resource_container,
            u'containers.tag-add': self.add_resource_container_tag,
            u'containers.tag-delete': self.delete_resource_container_tag,
            u'containers.discover-classes':self.discover_resource_container_resource_classess,
            u'containers.discover':self.discover_resource_container_resources,
            u'containers.synchronize':self.synchronize_resource_container_resources,
            
            u'resources.list': self.get_resources,
            u'resources.types': self.get_resource_types,
            u'resources.get': self.get_resource,
            u'resources.tree': self.get_resource_tree,
            u'resources.count': self.get_resource_count,
            u'resources.perms': self.get_resource_perms,
            u'resources.add': self.add_resource,
            u'resources.delete': self.delete_resource,
            u'resources.tag-add': self.add_resource_tag,
            u'resources.tag-delete': self.delete_resource_tag,
            u'resources.links': self.get_resource_links,
            u'resources.linked': self.get_resource_linked,
            
            u'tags.list': self.test_get_tags,
            u'tags.get': self.test_get_tag,
            u'tags.count': self.test_count_tags,
            u'tags.perms': self.test_get_tag_perms,
            u'tags.add': self.test_add_tags,
            u'tags.update': self.test_update_tag,
            u'tags.delete': self.test_delete_tag,
            
            u'links.list': self.test_get_links,
            u'links.get': self.test_get_link,
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
        uri = u'%s/resources' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get resources: %s' % truncate(res))
        self.result(res, key=u'resources', headers=self.res_headers)
    
    def get_resource_types(self, *args):
        data = self.format_http_get_query_params(*args)
        uri = u'%s/resources/types' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get resource types: %s' % truncate(res))
        self.result(res, key=u'resourcetypes', headers=[u'id', u'type'], 
                    maxsize=400)

    def get_resource(self, value):
        uri = u'%s/resources/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource: %s' % truncate(res))
        self.result(res, key=u'resource', details=True)
    
    def __print_tree(self, resource, space=u'   '):
        for child in resource.get(u'children', []):
            relation = child.get(u'relation')
            if relation is None:
                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, u'=>')
                    yield (Token.Name, u' [%s] ' % child.get(u'type'))
                    yield (Token.Literal.String, child.get(u'name'))
                    yield (Token.Text.Whitespace, u' - ')
                    yield (Token.Literal.Number, str(child.get(u'id')))
                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
                print data
            else:
                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, u'--%s-->' % relation)
                    yield (Token.Name, u' [%s] ' % child.get(u'type'))
                    yield (Token.Literal.String, child.get(u'name'))
                    yield (Token.Text.Whitespace, u' - ')
                    yield (Token.Literal.Number, str(child.get(u'id')))
                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
                print data
            self.__print_tree(child, space=space+u'   ')
    
    def get_resource_tree(self, value):
        uri = u'%s/resources/%s/tree' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource tree: %s' % res)
        if self.format == u'text':
            res = res[u'resource-tree']
            def create_data():
                yield (Token.Name, u' [%s] ' % res.get(u'type'))
                yield (Token.Literal.String, res.get(u'name'))
                yield (Token.Text.Whitespace, u' - ')
                yield (Token.Literal.Number, str(res.get(u'id')))
            data = format(create_data(), Terminal256Formatter(style=TreeStyle))
            print data
            self.__print_tree(res)
        else:
            self.result(res)        
    
    def get_resource_count(self, value):
        uri = u'%s/resources/%s/count' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource count: %s' % truncate(res))
        self.result(res)
    
    def get_resource_perms(self, value):
        uri = u'%s/resources/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    def add_resource(self, container, resclass, name, *args):
        params = self.get_query_params(*args)
        print params
        data = {
            u'resource':{
                u'container':container,
                u'resclass':resclass,
                u'name':name, 
                u'desc':u'Resource %s' % name,
                u'ext_id':params.get(u'ext_id', None),
                u'parent':params.get(u'parent', None),
                u'attribute':params.get(u'attribute', {}),
                u'tags':params.get(u'tags', None) 
            }
        }
        uri = u'%s/resources' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add resource: %s' % truncate(res))
        res = {u'msg':u'Add resource %s' % res}
        self.result(res, headers=[u'msg'])
        
    def update_resource(self, resource_id, *args):
        params = self.get_query_params(*args)
        name = params.get(u'name', None)

        data = {
            u'resource':{
                u'name':params.get(u'name', None), 
                u'desc':params.get(u'desc', None),
                u'ext_id':params.get(u'ext_id', None),
                #u'parent':params.get(u'desc', None),
                u'attribute':params.get(u'attribute', None),
                u'state':params.get(u'state', None),
                u'active':params.get(u'active', None)             
            }
        }
        uri = u'%s/resources' % (self.baseuri)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(u'Update resource: %s' % resource_id)
        res = {u'msg':u'Update resource %s' % resource_id}
        self.result(res, headers=[u'msg'])    
        
    def delete_resource(self, oid):
        uri = u'%s/resources/%s' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete resource: %s' % oid)
        res = {u'msg':u'Delete resource %s' % oid}
        self.result(res, headers=[u'msg'])
        
    def add_resource_tag(self, oid, tag):
        data = {
            u'resource':{
                u'tags':{
                    u'cmd':u'add',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/resources/%s/tags' % (self.baseuri, oid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)
        
    def delete_resource_tag(self, oid, tag):
        data = {
            u'resource':{
                u'tags':{
                    u'cmd':u'remove',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/resources/%s/tags' % (self.baseuri, oid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)    
    
    def get_resource_links(self, oid):
        uri = u'%s/resources/%s/links' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.result(res)
        
    def get_resource_linked(self, oid):
        uri = u'%s/resources/%s/linked' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.result(res)
    
    #
    # resource resource_containers
    #
    def get_resource_containers(self, *args):
        data = self.format_http_get_query_params(*args)
        uri = u'%s/resourcecontainers' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get resource containers: %s' % truncate(res))
        self.result(res, key=u'resourcecontainers', headers=self.cont_headers)
    
    def get_resource_container_types(self, tags=None):
        uri = u'%s/resourcecontainers/types' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource resourcecontainer types: %s' % truncate(res))
        self.result(res, key=u'resourcecontainertypes', headers=[u'category', u'type'])

    def get_resource_container(self, value):
        uri = u'%s/resourcecontainers/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource resourcecontainer: %s' % truncate(res))
        self.result(res, key=u'resourcecontainer', headers=self.cont_headers, details=True)
    
    '''
    def get_resource_container_rescount(self, value):
        uri = u'%s/resourcecontainers/%s/count' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource resourcecontainer resource count: %s' % truncate(res))
        self.result(res)'''
    
    def get_resource_container_perms(self, value):
        uri = u'%s/resourcecontainers/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource resourcecontainer perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
        
    '''
    def get_resource_container_roles(self, value):
        uri = u'%s/resourcecontainers/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get resource resourcecontainer roles: %s' % truncate(res))
        self.result(res)'''
    
    def ping_resource_container(self, contid):
        uri = u'%s/resourcecontainers/%s/ping' % (self.baseuri, contid)  
        res = self._call(uri, u'GET')      
        self.logger.info(u'Ping resourcecontainer %s: %s' % (contid, res))
        self.result({u'resourcecontainer':contid, u'ping':res[u'ping']}, 
                    headers=[u'resourcecontainer', u'ping'])      
    
    def add_resource_container(self, ctype, name, conn):
        conn = self.load_config(conn)
        data = {
            u'resourcecontainer':{
                u'type':ctype, 
                u'name':name,
                u'desc':u'Container %s' % name,
                u'conn':conn
            }
        }
        uri = u'%s/resourcecontainers' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add resource resourcecontainer: %s' % res)
        res = {u'msg':u'Add resourcecontainer %s' % res}
        self.result(res, headers=[u'msg'])
        
    def delete_resource_container(self, oid):
        uri = u'%s/resourcecontainers/%s' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete resource resourcecontainer: %s' % oid)
        res = {u'msg':u'Delete resource container %s' % oid}
        self.result(res, headers=[u'msg'])

    def add_resource_container_tag(self, contid, tag):
        data = {
            u'resourcecontainer':{
                u'tags':{
                    u'cmd':u'add',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/resourcecontainers/%s' % (self.baseuri, contid)        
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Add tag to resource container %s' % contid}
        self.result(res, headers=[u'msg'])
        
    def delete_resource_container_tag(self, contid, tag):
        data = {
            u'resourcecontainer':{
                u'tags':{
                    u'cmd':u'remove',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/resourcecontainers/%s' % (self.baseuri, contid)        
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Remove tag from resource container %s' % contid}
        self.result(res, headers=[u'msg'])
        
    def discover_resource_container_resource_classess(self, contid):
        uri = u'%s/resourcecontainers/%s/discover/classes' % (self.baseuri, contid)        
        res = self._call(uri, u'GET', data=u'').get(u'discoverclasses')
        self.result(res, headers=[u'resource class'], fields=[0], maxsize=200)
        
    def discover_resource_container_resources(self, contid, resclass=None):
        uri = u'%s/resourcecontainers/%s/discover' % (self.baseuri, contid)        
        res = self._call(uri, u'GET', data=u'resclass=%s' % resclass)\
                  .get(u'discover').get(u'resources')
        headers = [u'id', u'name', u'parent', u'class']
        print(u'New resources')
        self.result(res, key=u'new', headers=headers)
        print(u'Died resources')
        self.result(res, key=u'died', headers=headers)
        print(u'Changed resources')
        self.result(res, key=u'changed', headers=headers)

    def synchronize_resource_container_resources(self, contid, resclass):     
        data = {
            u'discover':{
                u'resource_classes':resclass,
                u'new':True,
                u'died':True,
                u'changed':True
            }
        }
        uri = u'%s/resourcecontainers/%s/discover' % (self.baseuri, contid)        
        res = self._call(uri, u'PUT', data=data)
        self.result(res)

    def get_resource_container_resources_scheduler(self):
        global contid
        data = ''
        uri = u'%s/resourcecontainer/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'GET', data=data)    
    
    def create_resource_container_resources_scheduler(self):
        global contid
        data = json.dumps({u'minutes':5})
        uri = u'%s/resourcecontainer/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'POST', data=data)
        
    def remove_resource_container_resources_scheduler(self):
        global contid
        uri = u'%s/resourcecontainer/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'DELETE', data='')

    #
    # tags
    #
    def test_add_tags(self, value):
        data = {
            u'resourcetag':{
                u'value':value
            }
        }
        uri = u'%s/resourcetags' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        res = {u'msg':u'Add tag %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    def test_count_tags(self):
        uri = u'%s/resourcetags/count' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        res = {u'msg':u'Tags count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])

    def test_get_tags(self, *args):
        data = self.format_http_get_query_params(*args)
        uri = u'%s/resourcetags' % self.baseuri        
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        self.result(res, key=u'resourcetags', headers=self.tag_headers)
        
    def test_get_tag(self, value):
        uri = u'%s/resourcetags/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'resourcetag', headers=self.tag_headers, 
                    details=True)
        #if self.format == u'table':
        #    self.result(res[u'resourcetag'], key=u'resources', headers=
        #                [u'id', u'uuid', u'definition', u'name'])

    def test_get_tag_perms(self, value):
        uri = u'%s/resourcetags/%s/perms' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
        
    def test_update_tag(self, value, new_value):
        data = {
            u'resourcetag':{
                u'value':new_value
            }
        }
        uri = u'%s/resourcetags/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def test_delete_tag(self, value):
        uri = u'%s/resourcetags/%s' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        self.logger.info(res)
        res = {u'msg':u'Delete tag %s' % value}
        self.result(res, headers=[u'msg'])
        
    #
    # links
    #
    def test_add_links(self, value):
        data = {
            u'resourcelinks':{
                u'value':value
            }
        }
        uri = u'%s/resourcelinks' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        res = {u'msg':u'Add link %s' % res}
        self.result(res, headers=[u'msg'])

    def test_count_links(self):
        uri = u'%s/resourcelinks/count' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def test_get_links(self):
        uri = u'%s/resourcelinks' % self.baseuri        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'resourcelinks', headers=self.link_headers)
        
    def test_get_link(self, oid):
        uri = u'%s/resourcelinks/%s' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'resourcelink', headers=self.link_headers)

    def test_get_link_perms(self, oid):
        uri = u'%s/resourcelinks/%s/perms' % (self.baseuri, oid)        
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
        
    def test_update_link(self, value, new_value):
        data = {
            u'resourcelinks':{
                u'value':new_value
            }
        }
        uri = u'%s/resourcelinks/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def test_delete_link(self, value):
        uri = u'%s/resourcelinks/%s' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        self.logger.info(res)
        res = {u'msg':u'Delete link %s' % value}
        self.result(res, headers=[u'msg'])

        
        