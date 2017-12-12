'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate
from beecell.remote import NotFoundException
from time import sleep

logger = logging.getLogger(__name__)


class ServiceController(BaseController):
    class Meta:
        label = 'business_service'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Service management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class ServiceControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'business_service'
        stacked_type = 'nested'

    def get_service_state(self, uuid):
        try:
            res = self._call(u'/v1.0/service/%s' % uuid, u'GET')
            state = res.get(u'service').get(u'state')
            logger.debug(u'Get service %s state: %s' % (uuid, state))
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'

    def wait_service(self, uuid, delta=1):
        """Wait service
        """
        logger.debug(u'wait for service: %s' % uuid)
        state = self.get_service_state(uuid)
        while state not in [u'ACTIVE', u'ERROR', u'EXPUNGED']:
            logger.info(u'.')
            print((u'.'))
            sleep(delta)
            state = self.get_service_state(uuid)


class ServiceTypeController(ServiceControllerChild):
    class Meta:
        label = 'types'
        description = "Service type management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all resources by field: tags, type, objid, name, ext_id,
    container, attribute, parent, state
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicetype' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicetypes', headers=[u'id', u'uuid', u'name', u'version', u'status'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get resource by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicetype/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicetype', details=True)

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


class ServiceInternalController(ServiceControllerChild):
    class Meta:
        label = 'services'
        description = "Service management"
        
    @expose(help="Service management", hide=True)
    def default(self):
        self.app.args.print_help()        


service_controller_handlers = [
    ServiceController,
    ServiceTypeController,
]        