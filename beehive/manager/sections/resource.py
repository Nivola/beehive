"""
Created on Sep 25, 2017

@author: darkbk
"""
import ujson as json
import logging
from urllib import urlencode

from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
import sys
from beecell.simple import truncate, str2bool
from pygments.formatters import Terminal256Formatter
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Token
from pygments.style import Style     
from pygments import format
from beehive.manager.util.controller import BaseController, ApiController, check_error
from cement.core.controller import expose
from time import sleep
from beecell.remote import NotFoundException
from time import time
from beehive.manager.sections.scheduler import WorkerController, ScheduleController, TaskController

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


class ResourceController(BaseController):
    class Meta:
        label = 'resource'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Resource management"
        arguments = []


class ResourceControllerChild(ApiController):
    baseuri = u'/v1.0/nrs'
    subsystem = u'resource'
    res_headers = [u'id', u'__meta__.definition', u'name', u'container.name', u'parent.name', u'state',
                   u'date.creation', u'ext_id']
    cont_headers = [u'id', u'category', u'__meta__.definition', u'name', u'active', u'state', u'date.creation',
                    u'date.modified', u'resources']
    tag_headers = [u'id', u'name', u'date.creation', u'date.modified', u'resources', u'containers', u'links']
    
    class Meta:
        stacked_on = 'resource'
        stacked_type = 'nested'

    @expose(aliases=[u'job <id>'], aliases_only=True)
    @check_error
    def job(self):
        """Get resource job
    - id : job id
        """
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
        res = self._call(uri, u'GET').get(u'task_instance')
        logger.info(res)
        resp = []
        resp.append(res)
        resp.extend(res.get(u'children'))
        self.result(resp, headers=[u'task_id', u'type', u'status', u'name', u'start_time', u'stop_time', u'elapsed'],
                    maxsize=100)

    @expose(aliases=[u'jobtrace <id>'], aliases_only=True)
    @check_error
    def jobtrace(self):
        """Get resource job trace
    - id : job id
        """
        task_id = self.get_arg(name=u'id')
        uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
        res = self._call(uri, u'GET').get(u'task_instance').get(u'trace')
        logger.info(res)
        resp = []
        for i in res:
            resp.append({u'timestamp': i[0], u'task': i[1], u'task id': i[2], u'msg': truncate(i[3], 150)})
        self.result(resp, headers=[u'timestamp', u'msg'], maxsize=200)


class ResourceWorkerController(ResourceControllerChild, WorkerController):
    class Meta:
        label = 'resource.workers'
        aliases = ['workers']
        aliases_only = True
        description = "Worker management"


class ResourceTaskController(ResourceControllerChild, TaskController):
    class Meta:
        label = 'resource.tasks'
        aliases = ['tasks']
        aliases_only = True
        description = "Task management"


class ResourceScheduleController(ResourceControllerChild, ScheduleController):
    class Meta:
        label = 'resource.schedules'
        aliases = ['schedules']
        aliases_only = True
        description = "Schedule management"


class ContainerController(ResourceControllerChild, WorkerController):
    class Meta:
        label = 'containers'
        description = "Container management"

    def get_job_state(self, jobid):
        try:
            res = self._call(u'%s/worker/tasks/%s' % (self.baseuri, jobid), u'GET')
            state = res.get(u'task_instance').get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                # print(res)
                self.app.print_error(res[u'task_instance'][u'traceback'][-1])
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'

    def wait_job(self, jobid, delta=1):
        """Wait resource
        """
        logger.debug(u'wait for job: %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in [u'SUCCESS', u'FAILURE']:
            logger.info(u'.')
            print(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)

    @expose(aliases=[u'list [status]'], aliases_only=True)
    @check_error
    def list(self, *args):
        """List containers by: tags
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/containers' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get resource containers: %s' % truncate(res))
        self.result(res, key=u'resourcecontainers', headers=self.cont_headers)
    
    @expose()
    @check_error
    def types(self):
        """List container types
        """        
        uri = u'%s/containers/types' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(u'Get resource resourcecontainer types: %s' % truncate(res))
        self.result(res, key=u'resourcecontainertypes', headers=[u'category', u'type'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get container by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/containers/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get resource resourcecontainer: %s' % truncate(res))
        self.result(res, key=u'resourcecontainer', headers=self.cont_headers, details=True)
    
    '''
    def get_resource_container_rescount(self, value):
        uri = u'%s/containers/%s/count' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get resource resourcecontainer resource count: %s' % truncate(res))
        self.result(res)'''
    
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get container permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        print data
        uri = u'%s/containers/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get resource resourcecontainer perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
        
    '''
    def get_resource_container_roles(self, value):
        uri = u'%s/containers/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get resource resourcecontainer roles: %s' % truncate(res))
        self.result(res)'''
    
    @expose(aliases=[u'ping <id>'], aliases_only=True)
    @check_error
    def ping(self):
        """Ping container by id, uuid or name
        """        
        contid = self.get_arg(name=u'id')
        uri = u'%s/containers/%s/ping' % (self.baseuri, contid)
        res = self._call(uri, u'GET')      
        logger.info(u'Ping resourcecontainer %s: %s' % (contid, res))
        self.result({u'resourcecontainer':contid, u'ping':res[u'ping']}, 
                    headers=[u'resourcecontainer', u'ping'])
        
    @expose()
    @check_error
    def pings(self):
        """Ping all containers
        """
        resp = []
        uri = u'%s/containers' % self.baseuri
        res = self._call(uri, u'GET')        
        for rc in res[u'resourcecontainers']:
            start = time()
            uri = u'%s/containers/%s/ping' % (self.baseuri, rc[u'id'])
            res = self._call(uri, u'GET')      
            logger.info(u'Ping resourcecontainer %s: %s' % (rc[u'id'], res))
            elapsed = time()-start
            resp.append({u'uuid':rc[u'uuid'],
                         u'name':rc[u'name'], 
                         u'ping':res[u'ping'],
                         u'category':rc[u'category'], 
                         u'type':rc[u'__meta__'][u'definition'],
                         u'elapsed':elapsed})
            
        self.result(resp, headers=[u'uuid', u'name', u'category', u'type', 
                                   u'ping', u'elapsed'])         
    
    @expose(aliases=[u'add <json config file>'], aliases_only=True)
    @check_error
    def add(self):
        """Add container
        """
        conf = self.load_config(self.get_arg(name=u'config file'))
        data = {
            u'resourcecontainer': conf
        }
        uri = u'%s/containers' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add resource resourcecontainer: %s' % res)
        res = {u'msg':u'Add resourcecontainer %s' % res}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete container by id, uuid or name
        """
        oid = self.get_arg(name=u'id')
        uri = u'%s/containers/%s' % (self.baseuri, oid)
        self._call(uri, u'DELETE')
        logger.info(u'Delete resource resourcecontainer: %s' % oid)
        res = {u'msg':u'Delete resource container %s' % oid}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'jobs <id>'], aliases_only=True)
    @check_error
    def jobs(self, *args):
        """List all container jobs
    - id : resource id
        """
        oid = self.get_arg(name=u'id')
        uri = u'%s/containers/%s/jobs' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get container jobs: %s' % truncate(res))
        self.result(res, key=u'containerjobs', headers=[u'job', u'name', u'timestamp'], maxsize=400)

    @expose(aliases=[u'add-tag <id> <tag>'], aliases_only=True)
    @check_error
    def add_tag(self):
        """Add container tag
        """
        contid = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')
        data = {
            u'resourcecontainer':{
                u'tags':{
                    u'cmd':u'add',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/containers/%s' % (self.baseuri, contid)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Add tag to resource container %s' % contid}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete-tag <id> <tag>'], aliases_only=True)
    @check_error
    def delete_tag(self):
        """Delete container tag
        """
        contid = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')        
        data = {
            u'resourcecontainer':{
                u'tags':{
                    u'cmd':u'remove',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/containers/%s' % (self.baseuri, contid)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Remove tag from resource container %s' % contid}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'discover-types <id>'], aliases_only=True)
    @check_error
    def discover_types(self):
        """discover container <class> resources
        """
        contid = self.get_arg(name=u'id')
        uri = u'%s/containers/%s/discover/types' % (self.baseuri, contid)
        res = self._call(uri, u'GET', data=u'').get(u'discover_types')
        self.result(res, headers=[u'resource class'], fields=[0], maxsize=200)
    
    @expose(aliases=[u'discover <id> [type]'], aliases_only=True)
    @check_error
    def discover(self):
        """Discover container
        """
        contid = self.get_arg(name=u'id')
        resclass = self.get_arg(default=None)
        uri = u'%s/containers/%s/discover' % (self.baseuri, contid)
        res = self._call(uri, u'GET', data=u'type=%s' % resclass).get(u'discover_resources')
        headers = [u'id', u'name', u'parent', u'type']
        
        print(u'New resources')
        self.result(res, key=u'new', headers=headers)
        print(u'Died resources')
        self.result(res, key=u'died', headers=headers)
        print(u'Changed resources')
        self.result(res, key=u'changed', headers=headers)

    @expose(aliases=[u'discover-all <id>'], aliases_only=True)
    @check_error
    def discover_all(self):
        """Discover container
        """
        contid = self.get_arg(name=u'id')

        # get types
        uri = u'%s/containers/%s/discover/types' % (self.baseuri, contid)
        types = self._call(uri, u'GET', data=u'').get(u'discover_types')

        res = {u'new': [], u'died': [], u'changed': []}
        for type in types:
            uri = u'%s/containers/%s/discover' % (self.baseuri, contid)
            parres = self._call(uri, u'GET', data=u'type=%s' % type).get(u'discover_resources')
            res[u'new'].extend(parres[u'new'])
            res[u'died'].extend(parres[u'died'])
            res[u'changed'].extend(parres[u'changed'])

        headers = [u'id', u'name', u'parent', u'type']

        print(u'New resources')
        self.result(res, key=u'new', headers=headers)
        print(u'Died resources')
        self.result(res, key=u'died', headers=headers)
        print(u'Changed resources')
        self.result(res, key=u'changed', headers=headers)

    @expose(aliases=[u'synchronize <id> <resclass>'], aliases_only=True)
    @check_error
    def synchronize(self):
        """Synchronize container <class> resources
        """
        contid = self.get_arg(name=u'id')
        resclass = self.get_arg(name=u'resclass')
        data = {
            u'synchronize': {
                u'types': resclass,
                u'new': True,
                u'died': True,
                u'changed': True
            }
        }
        uri = u'%s/containers/%s/discover' % (self.baseuri, contid)
        res = self._call(uri, u'PUT', data=data)
        self.result(res)
        jobid = res[u'jobid']
        self.wait_job(jobid, delta=1)

    @expose(aliases=[u'synchronize-all <id>'], aliases_only=True)
    @check_error
    def synchronize_all(self):
        """Synchronize container <class> resources
        """
        contid = self.get_arg(name=u'id')

        # get types
        uri = u'%s/containers/%s/discover/types' % (self.baseuri, contid)
        types = self._call(uri, u'GET', data=u'').get(u'discover_types')

        for type in types:
            self.app.print_output(u'Synchronize %s' % type)
            data = {
                u'synchronize': {
                    u'types': type,
                    u'new': True,
                    u'died': True,
                    u'changed': True
                }
            }
            uri = u'%s/containers/%s/discover' % (self.baseuri, contid)
            res = self._call(uri, u'PUT', data=data)
            self.result(res)
            jobid = res[u'jobid']
            self.wait_job(jobid, delta=1)



    '''
    @expose(aliases=[u'ping <id>'], aliases_only=True)
    def get_resource_container_resources_scheduler(self):
        global contid
        data = ''
        uri = u'%s/container/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'GET', data=data)    
    
    @expose(aliases=[u'ping <id>'], aliases_only=True)
    def create_resource_container_resources_scheduler(self):
        global contid
        data = json.dumps({u'minutes':5})
        uri = u'%s/container/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'POST', data=data)
    
    @expose(aliases=[u'ping <id>'], aliases_only=True)
    def remove_resource_container_resources_scheduler(self):
        global contid
        uri = u'%s/container/%s/discover/scheduler' % (self.baseuri, contid)        
        self.invoke(u'resource', uri, u'DELETE', data='')'''


class ResourceEntityController(ResourceControllerChild):    
    class Meta:
        label = 'entities'
        description = "Entity management"
        
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
                    yield (Token.Literal.String, u' [%s]' % child.get(u'state'))
                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
                print data
            else:
                def create_data():
                    yield (Token.Text.Whitespace, space)
                    yield (Token.Operator, u'--%s-->' % relation)
                    yield (Token.Operator, u' (%s) ' % child.get(u'container_name'))
                    yield (Token.Name, u'[%s] ' % child.get(u'type'))
                    yield (Token.Literal.String, child.get(u'name'))
                    yield (Token.Text.Whitespace, u' - ')
                    yield (Token.Literal.Number, str(child.get(u'id')))
                    yield (Token.Literal.String, u' [%s]' % child.get(u'state'))
                data = format(create_data(), Terminal256Formatter(style=TreeStyle))
                print data
            self.__print_tree(child, space=space+u'   ')

    def get_resource_state(self, uuid):
        try:
            res = self._call(u'%s/entities/%s' % (self.baseuri, uuid), u'GET')
            state = res.get(u'resource').get(u'state')
            logger.debug(u'Get resource %s state: %s' % (uuid, state))
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'
        
    def get_job_state(self, jobid):
        try:
            res = self._call(u'%s/worker/tasks/%s' % (self.baseuri, jobid), u'GET')
            state = res.get(u'task_instance').get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                self.app.print_error(res[u'task_instance'][u'traceback'][-1])
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'

    def wait_resource(self, uuid, delta=1):
        """Wait resource
        """
        logger.debug(u'Wait for resource: %s' % uuid)
        state = self.get_resource_state(uuid)
        while state not in [u'ACTIVE', u'ERROR', u'EXPUNGED']:
            logger.info(u'.')
            print(u'.')
            sleep(delta)
            state = self.get_resource_state(uuid)
    
    def wait_job(self, jobid, delta=1):
        """Wait resource
        """
        logger.debug(u'Wait for job: %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in [u'SUCCESS', u'FAILURE']:
            logger.info(u'.')
            print(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)

    def __get_key(self):
        return self._meta.aliases[0].rstrip(u's')

    def get_resource(self, oid, format_result=None):
        """Get resource

        **Parameters**:

            * **oid**: id of the resource

        **Return**:

            resource dict
        """
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET')
        key = self.__get_key()
        res = res.get(key)
        logger.info(u'Get %s: %s' % (key, truncate(res)))
        if self.format == u'text':
            for i in [u'__meta__', u'ext_id', u'active']:
                res.pop(i, None)
            main_info = []
            c = res.pop(u'container')
            c.update({u'type': u'container'})
            main_info.append(c)
            c = res.pop(u'parent')
            c.update({u'type': u'parent', u'desc': u'', u'state': u''})
            main_info.append(c)
            date = res.pop(u'date')
            main_info.append({u'id': res.pop(u'id'),
                              u'uuid': res.pop(u'uuid'),
                              u'name': res.pop(u'name'),
                              u'type': u'',
                              u'desc': res.pop(u'desc'),
                              u'state': res.pop(u'state'),
                              u'created': date.pop(u'creation'),
                              u'modified': date.pop(u'modified'),
                              u'expiry': date.pop(u'expiry')})
            self.result(main_info, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                            u'modified', u'expiry'], table_style=u'simple')

            if format_result is not None:
                format_result(res)

            self.app.print_output(u'Other infos:')
            self.result(res, details=True, table_style=u'simple')
        else:
            self.result(res, details=True)

    @expose(aliases=[u'add <container> <resclass> <name> [ext_id=..] [parent=..] [attribute=..] [tags=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Add resource <name>
        """
        container = self.get_arg(name=u'container')
        resclass = self.get_arg(name=u'resclass')
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'resource': {
                u'container': container,
                u'resclass': resclass,
                u'name': name,
                u'desc': u'Resource %s' % name,
                u'ext_id': params.get(u'ext_id', None),
                u'parent': params.get(u'parent', None),
                u'attribute': params.get(u'attribute', {}),
                u'tags': params.get(u'tags', None)
            }
        }
        uri = u'%s/entities' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)        
        logger.info(u'Add resource: %s' % truncate(res))
        res = {u'msg': u'Add resource %s' % res}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update resource
    - oid: id or uuid of the resource
    - field: can be name, desc, ext_id, active, attribute, state
        """
        oid = self.get_arg(name=u'oid')
        params = self.app.kvargs
        data = {
            u'resource': params
        }
        uri = u'%s/entities/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Update resource %s with data %s' % (oid, params))
        res = {u'msg': u'Update resource %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'reset <oid>'], aliases_only=True)
    @check_error
    def reset(self):
        """Reset resource setting ext_id to None
    - oid: id or uuid of the resource
        """
        oid = self.get_arg(name=u'oid')
        data = {
            u'resource': {u'ext_id': u''}
        }
        uri = u'%s/entities/%s' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Reset resource %s' % (oid))
        res = {u'msg': u'Reset resource %s' % (oid)}
        self.result(res, headers=[u'msg'])
    
    @expose()
    @check_error
    def count(self):
        """Count all resource
        """        
        uri = u'%s/entities/count' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg':u'Resources count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all resources by field: tags, type, objid, name, ext_id, 
    container, attribute, parent, state
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/entities' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'resources', headers=self.res_headers)
    
    @expose(aliases=[u'types [field=value]'], aliases_only=True)
    @check_error
    def types(self, *args):
        """List all resource types by field: type, subsystem
        """        
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/entities/types' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get resource types: %s' % truncate(res))
        self.result(res, key=u'resourcetypes', headers=[u'id', u'type', u'resclass'], maxsize=400)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get resource by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/entities/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'resource', headers=self.res_headers, details=True)
    
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get resource permissions
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/entities/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    @expose(aliases=[u'tree <id> [parent=true|false] [link=true|false]'], aliases_only=True)
    @check_error
    def tree(self):
        """Get resource tree
    - parent: if True show tree by parent - child
    - link: if True show tree by link relation
        """
        value = self.get_arg(name=u'id')
        # params = self.get_query_params(**self.app.kvargs)
        uri = u'%s/entities/%s/tree' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=urlencode(self.app.kvargs))
        logger.info(u'Get resource tree: %s' % res)
        # if self.format == u'text':
        res = res[u'resourcetree']

        def create_data():
            yield (Token.Name, u' [%s] ' % res.get(u'type'))
            yield (Token.Literal.String, res.get(u'name'))
            yield (Token.Text.Whitespace, u' - ')
            yield (Token.Literal.Number, str(res.get(u'id')))
            yield (Token.Literal.String, u' [%s]' % res.get(u'state'))
        data = format(create_data(), Terminal256Formatter(style=TreeStyle))
        print data
        self.__print_tree(res)

        '''import networkx as nx
        import networkx.readwrite.json_graph as graph
        options = {
            # 'node_color': 'black',
            # 'node_size': 100,
            'width': 1,
            'with_label': True,
            # 'arrows': True
        }
        # import matplotlib.pyplot as plt
        G = graph.tree_graph(res, attrs={'children': 'children', 'id': 'name', 'name':'name'})
        nx.draw_networkx(G, **options)'''

    @expose(aliases=[u'jobs <id>'], aliases_only=True)
    @check_error
    def jobs(self, *args):
        """List all resource jobs
    - id : resource id
        """
        oid = self.get_arg(name=u'id')
        uri = u'%s/entities/%s/jobs' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get resource jobs: %s' % truncate(res))
        self.result(res, key=u'resourcejobs', headers=[u'job', u'name', u'timestamp'], maxsize=400)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete resource
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/entities/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        res = {u'msg':u'Delete resource %s' % value}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'deletes <id1,id2>'], aliases_only=True)
    @check_error
    def deletes(self):
        """Delete resources id1, id2, ..
        """
        resp = []
        values = self.get_arg(name=u'id list')
        for value in values.split(u','):
            uri = u'%s/entities/%s' % (self.baseuri, value)
            res = self._call(uri, u'DELETE')
            logger.info(res)
            jobid = res.get(u'jobid', None)
            if jobid is not None:
                self.wait_job(jobid)
            resp.append(value)
        res = {u'msg':u'Delete resources %s' % u','.join(resp)}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'add-tag <id> <tag>'], aliases_only=True)
    @check_error
    def add_tag(self):
        """Add resource tag
        """        
        value = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')
        data = {
            u'resource':{
                u'tags':{
                    u'cmd':u'add',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/entities/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Add resource %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete-tag <id> <tag>'], aliases_only=True)
    @check_error
    def delete_tag(self):
        """Delete resource tag
        """          
        value = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')
        data = {
            u'resource':{
                u'tags':{
                    u'cmd':u'remove',
                    u'values':[tag]
                }
            }
        }
        uri = u'%s/entities/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg':u'Delete resource %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'linked <id>'], aliases_only=True)
    @check_error
    def linked(self):
        """Get linked resources
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/entities/%s/linked' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'resources', headers=self.res_headers)


class LinkController(ResourceControllerChild):
    fields = [u'id', u'name', u'active', u'details.type', u'details.start_resource.id', u'details.end_resource.id',
               u'details.attributes', u'date.creation', u'date.modified']
    headers = [u'id', u'name', u'type', u'start', u'end', u'attributes', u'creation', u'modified']

    class Meta:
        label = 'links'
        description = "Link management"

    @expose(aliases=[u'add <name> <type> <start> <end>'], aliases_only=True)
    @check_error
    def add(self):
        """Add link <name> of type <type> from resource <start> to resource <end>
        """
        name = self.get_arg(name=u'name')
        type = self.get_arg(name=u'type')
        start_resource = self.get_arg(name=u'start')
        end_resource = self.get_arg(name=u'end')
        data = {
            u'resourcelink':{
                u'type':type,
                u'name':name, 
                u'attributes':{}, 
                u'start_resource': start_resource,
                u'end_resource': end_resource,
            }
        }
        uri = u'%s/links' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add link %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])
    
    @expose()
    @check_error
    def count(self):
        """Count all link
        """        
        uri = u'%s/links/count' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg':u'Links count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self, *args):
        """List all links by field: type, resource, tags
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/links' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'resourcelinks', headers=self.headers, fields=self.fields)
    
    @expose(aliases=[u'get <value>'], aliases_only=True)
    @check_error
    def get(self):
        """Get link by value or id
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'resourcelink', headers=self.link_headers, 
                    details=True)
    
    @expose(aliases=[u'perms <value>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get link permissions
        """
        value = self.get_arg(name=u'value')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/links/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    @expose(aliases=[u'update <value> [name=..] [type=..] [start=..] [end=..]'], 
            aliases_only=True)
    @check_error
    def update(self):
        """Update link with some optional fields
        """
        value = self.get_arg(name=u'value')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'resourcelink':{
                u'type':params.get(u'type', None),
                u'name':params.get(u'name', None), 
                u'attributes':None, 
                u'start_resource':params.get(u'start', None), 
                u'end_resource':params.get(u'end', None), 
            }
        }
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update link %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <value>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete link
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete link %s' % value}
        self.result(res, headers=[u'msg'])       


class TagController(ResourceControllerChild):    
    class Meta:
        label = 'tags'
        description = "Tag management"

    @expose(aliases=[u'add <value>'], aliases_only=True)
    @check_error
    def add(self):
        """Add tag <value>
        """
        value = self.get_arg(name=u'value')
        data = {
            u'resourcetag': {
                u'value': value
            }
        }
        uri = u'%s/tags' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add tag %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose()
    @check_error
    def count(self):
        """Count all tag
        """        
        uri = u'%s/tags/count' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg':u'Tags count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self, *args):
        """List all tags by field: value, container, resource, link
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/tags' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'resourcetags', headers=self.tag_headers)
    
    @expose(aliases=[u'get <value>'], aliases_only=True)
    @check_error
    def get(self):
        """Get tag by value or id
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/tags/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'resourcetag', headers=self.tag_headers, 
                    details=True)
        #if self.format == u'table':
        #    self.result(res[u'resourcetag'], key=u'resources', headers=
        #                [u'id', u'uuid', u'definition', u'name'])

    @expose(aliases=[u'perms <value>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get tag permissions
        """
        value = self.get_arg(name=u'value')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/tags/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    @expose(aliases=[u'update <value> <new_value>'], aliases_only=True)
    @check_error
    def update(self):
        """Update tag with new value
        """
        value = self.get_arg(name=u'value')
        new_value = self.get_arg(name=u'new value')
        data = {
            u'resourcetag':{
                u'value':new_value
            }
        }
        uri = u'%s/tags/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update tag %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <value>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete tag
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/tags/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete tag %s' % value}
        self.result(res, headers=[u'msg'])        


resource_controller_handlers = [
    ResourceController,
    ContainerController,
    ResourceEntityController,
    LinkController,
    TagController,
    ResourceWorkerController,
    ResourceScheduleController,
    ResourceTaskController
]        
