'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)


class OrganizationHierarchyController(BaseController):
    class Meta:
        label = 'business_hierarchy'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Organization Hierarchy management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class OrganizationHierarchyControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'business_hierarchy'
        stacked_type = 'nested'


class OrganizationController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'organizations'
        description = "Organization management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all organizations by field: tags, type, objid, name, ext_id,
    container, attribute, parent, state
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/organizations' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'organizations',
                    headers=[u'id', u'uuid', u'name', u'org_type', u'ext_anag_id'], maxsize=30)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get organization by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'organization', details=True)

    @expose(aliases=[u'add <container> <resclass> <name> [ext_id=..] '\
                     u'[parent=..] [attribute=..] [tags=..]'],
            aliases_only=True)
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
        uri = u'%s/resources' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Add resource: %s' % truncate(res))
        res = {u'msg': u'Add resource %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    def update(self):
        """Add resource
    - oid: id or uuid of the resource
    - field: can be name, desc, ext_id, active, attribute, state
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'resource': params
        }
        uri = u'%s/resources/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update resource %s with data %s' % (oid, params))
        res = {u'msg': u'Update resource %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete resource
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/resources/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)

        res = {u'msg': u'Delete resource %s' % value}
        self.result(res, headers=[u'msg'])


class DivisionController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'divisions'
        description = "Divisions management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all divisions by field: tags, type, objid, name, ext_id,
    container, attribute, parent, state
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/divisions' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'divisions',
                    headers=[u'id', u'uuid', u'name'], maxsize=30)

        
organization_controller_handlers = [
    OrganizationHierarchyController,
    OrganizationController,
    DivisionController,
]        