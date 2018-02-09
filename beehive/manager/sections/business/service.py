'''
Created on Sep 27, 2017
 
@author: darkbk
'''
import logging
import urllib

from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate
from beecell.remote import NotFoundException
from time import sleep
import json
 
logger = logging.getLogger(__name__)
 
 
class ServiceController(BaseController):
    class Meta:
        label = 'service'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Business Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
 
 
class ServiceControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'
 
    class Meta:
        stacked_on = 'service'
        stacked_type = 'nested'


class ServiceTypeController(ServiceControllerChild):
    class Meta:
        label = 'types'
        description = "Service type management"
 
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service type by field: 
        name, id, uuid, objid, flag_container, version, status,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicetypes' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicetypes', headers=[u'id', u'uuid', u'name', u'version', u'status',
                    u'flag_container', u'objclass', u'active', u'date.creation'])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service type by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicetypes/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicetype', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get service type permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicetypes/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get servicetype perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)         
    
    @expose(aliases=[u'add <name> <version> [flag_container=..] [objclass=..] [active=..] [status=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Add service type <name> <version>
         - field: can be desc, objclass, flag_container, status, active 
        """
        name = self.get_arg(name=u'name')
        version = self.get_arg(name=u'version')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'servicetype': {
                u'name': name,
                u'version': version,
                u'desc': params.get(u'desc', None),
                u'objclass': params.get(u'objclass', u''),
                u'flag_container': params.get(u'flag_container', None),
                u'status': params.get(u'status', u'DRAFT'),
                u'active': params.get(u'active', False),
            }
        }
        uri = u'%s/servicetypes' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service type: %s' % truncate(res))
        res = {u'msg': u'Add service type %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service type
        - oid: id or uuid of the service type
        - field: can be name, version, desc, objclass, flag_container, status, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'servicetype': params
        }
        uri = u'%s/servicetypes/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service type %s with data %s' % (oid, params))
        res = {u'msg': u'Update service type %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete servicetype
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicetypes/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service type %s' % value}
        self.result(res, headers=[u'msg'])


class ServiceCostParamController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'costs'
        stacked_on = 'types'
        stacked_type = 'nested'
        description = "Service type cost management"

    @expose(aliases=[u'list <oid>'], aliases_only=True)
    @check_error
    def list(self):
        """List all service type cost params
        """
        value = self.get_arg(name=u'oid')
        uri = u'%s/servicecostparams' % self.baseuri
        res = self._call(uri, u'GET', data=u'service_type_id=%s' % value)
        logger.info(res)
        self.result(res, key=u'servicecostparams', headers=[u'id', u'uuid', u'name', u'param_definition', u'param_unit',
                    u'active', u'date.creation'])


class ServiceTypeProcessController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'processes'
        stacked_on = 'types'
        stacked_type = 'nested'
        description = "Service type process management"

    @expose(aliases=[u'list <oid>'], aliases_only=True)
    @check_error
    def list(self):
        """List all service type process
        """
        value = self.get_arg(name=u'oid')
        uri = u'%s/serviceprocesses' % self.baseuri
        res = self._call(uri, u'GET', data=u'service_type_id=%s' % value).get(u'serviceprocesses', [])
        logger.info(res)
        self.result(res, headers=[u'id', u'uuid', u'name', u'method_key', u'process_key', u'active', u'date.creation'])


class ServiceDefinitionController(ServiceControllerChild):
    class Meta:
        label = 'defs'
        description = "Service definition management"
 
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service definitions by field: 
        name, id, uuid, objid, version, status,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicedefs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicedefs', headers=[u'id', u'uuid', u'name', u'version', u'status',
                    u'service_type_id', u'active', u'date.creation'])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service definition by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicedefs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicedef', details=True)

    @expose(aliases=[u'links <id>'], aliases_only=True)
    @check_error
    def links(self):
        """Get service definition links
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicedefs/%s/links' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.app.print_output(u'Service Links:')
        headers = [u'id', u'uuid', u'name', u'param_definition', u'param_unit', u'active', u'date.creation']
        self.result(res, key=u'service_links', headers=headers)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get service definition permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicedefs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get servicedefinition perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
  
    @expose(aliases=[u'add <service_type_id> <name> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service definition
    - service_type_id: id or uuid of the service type
    - name: name of the service definition
    - field: Identify optional params. Can be: desc, parent_id, priority, status, version, active
        """
        service_type_id = self.get_arg(name=u'service_type_id')
        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'servicedef':{
                u'name': name,
                u'version': params.get(u'version', u'1.0'),
                u'desc': params.get(u'desc', None),
                u'status': params.get(u'status', u'DRAFT'),
                u'active': params.get(u'active', False),
                u'service_type_id': service_type_id,
                u'parent_id': params.get(u'parent_id', None),
                u'priority': params.get(u'priority', None),
            }
        }
        uri = u'%s/servicedefs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add servicedefinition: %s' % truncate(res))
        res = {u'msg': u'Add servicedefinition %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service definition
        - oid: id or uuid of the servicedef
        - field: can be name, version, desc, status, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'servicedef': params
        }
        uri = u'%s/servicedefs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update servicedefinition %s with data %s' % (oid, params))
        res = {u'msg': u'Update servicedefinition %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service definition
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicedefs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete servicedefinition %s' % value}
        self.result(res, headers=[u'msg'])
 

class ServiceDefinitionCostController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'unitcosts'
        stacked_on = 'defs'
        stacked_type = 'nested'
        description = "Service type unitary cost management [TODO]"


class ServiceDefinitionConfigController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'configs'
        stacked_on = 'defs'
        stacked_type = 'nested'
        description = "Service definition config management"

    @expose(aliases=[u'list <id>'], aliases_only=True)
    @check_error
    def list(self):
        """List all service definition configuration by field:
        name, id, uuid, objid, version, status,
        service_definition_id, params, params_type,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=u'service_definition_id=%s' % value)
        logger.info(res)
        headers = [u'id', u'uuid', u'name', u'version', u'params_type', u'params', u'active', u'date.creation']
        self.result(res, key=u'servicecfgs', headers=headers)
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get  service definition configuration  by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicecfg', details=True)

    @expose(aliases=[u'add <service_definition_id> <name> [desc=..] [params=..] [params_type=..] [status=..] '
                     u'[version=..] [active=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service definition configuration <service_definition_id> <name> <params>
         - service_definition_id: id or uuid of the service definition
         - field: can be desc, params, params_type, status, version, active
        """
        service_definition_id = self.get_arg(name=u'service_definition_id')
        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'servicecfg':{
                u'name':name, 
                u'version': params.get(u'version', u'1.0'),
                u'desc': params.get(u'desc', None),
                u'status': params.get(u'status', u'DRAFT'),
                u'active': params.get(u'active', False),
                u'service_definition_id' : service_definition_id,
                u'params':params.get(u'params', u'{}'),
                u'params_type':params.get(u'params', u'json')

            }
        }     
        uri = u'%s/servicecfgs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service definition cfg: %s' % truncate(res))
        res = {u'msg': u'Add service definition cfg %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service definition configuration
        - oid: id or uuid of the servicedef
        - field: can be name, version, desc, params, params_type, status, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'servicecfg': params
        }
        uri = u'%s/servicecfgs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service definition cfgs %s with data %s' % (oid, params))
        res = {u'msg': u'Update service definition cfgs %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service definition configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service definition cfgs %s' % value}
        self.result(res, headers=[u'msg'])


class ServiceCatalogController(ServiceControllerChild):
    class Meta:
        label = 'service.catalogs'
        aliases = ['catalogs']
        aliases_only = True
        description = "Service catalog management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service catalog by field:
        name, id, uuid, objid, version, status,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/srvcatalogs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'catalogs', headers=[u'id', u'uuid', u'name', u'version', u'active', u'date.creation'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service catalog by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'catalog', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get service catalog permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = urllib.urlencode(self.app.kvargs)
        uri = u'%s/srvcatalogs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service catalog perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)

    @expose(aliases=[u'add <name>  [desc=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service catalogo <name>
         - service_type_id: id or uuid of the service type
         - field: can be desc
        """
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'catalog': {
                u'name': name,
                u'desc': params.get(u'desc', None),
            }
        }
        uri = u'%s/srvcatalogs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service catalog: %s' % truncate(res))
        res = {u'msg': u'Add service catalog %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service catalog
        - oid: id or uuid of the catalog
        - field: can be name, version, desc, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'catalog': params
        }
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service catalog %s with data %s' % (oid, params))
        res = {u'msg': u'Update service catalog %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service catalog
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service catalog %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'defs <id> [field=value]'], aliases_only=True)
    @check_error
    def defs(self):
        """List all service service definitions linked to service catalog
    - field = plugintype, flag_container
        - plugintype=.. filter by plugin type
        - flag_container=true select only container type
        """
        value = self.get_arg(name=u'id')
        data = urllib.urlencode(self.app.kvargs)
        uri = u'%s/srvcatalogs/%s/defs' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicedefs', headers=[u'id', u'uuid', u'name', u'version', u'status',
                    u'service_type_id', u'active', u'date.creation'])


class ServiceInstanceController(ServiceControllerChild):
    class Meta:
        label = 'instances'
        description = "Service instance management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List service instances.
    - field: name, id, uuid, objid, version, status, account_id, service_definition_id, bpmn_process_id, resource_uuid
             filter_creation_date_stop, filter_modification_date_start, filter_modification_date_stop,
             filter_expiry_date_start, filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinsts' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        fields = [u'id', u'uuid', u'name', u'version', u'account_id', u'service_definition_id', u'status', u'active',
                  u'resource_uuid', u'date.creation']
        headers = [u'id', u'uuid', u'name', u'version', u'account', u'definition', u'status', u'active', u'resource',
                   u'creation']
        self.result(res, key=u'serviceinsts', headers=headers, fields=fields)
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service instance by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'serviceinst', details=True)
 
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get service instance permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinsts/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service instance perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    

    @expose(aliases=[u'resource <id>'], aliases_only=True)
    @check_error
    def resource(self):
        """Get service instance linked resource
        """
        value = self.get_arg(name=u'id')
        uri = u'v1.0//serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'serviceinst', details=True)

    @expose(aliases=[u'add <service_definition_id> <account_id> <name> [desc=..] [bpmn_process_id=..] [status=..] '
                     u'[version=..] [active=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service instance <service_definition_id> <account_id> <name> <version> 
         - service_definition_id: id or uuid of the service definition
         - account_id: id or uuid of the account
         - field: can be desc, bpmn_process_id, status, active
        """
        service_definition_id = self.get_arg(name=u'service_definition_id')
        account_id = self.get_arg(name=u'account_id')
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'serviceinst':{
                u'name':name,
                u'account_id':account_id,
                u'service_def_id':service_definition_id,
                u'status': params.get(u'status',u'DRAFT'),
                u'bpmn_process_id':params.get(u'bpmn_process_id', None),
                u'active':False,
                u'version':params.get(u'version',u'1.0'),
            }
        }
                
        uri = u'%s/serviceinsts' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service instance: %s' % truncate(res))
        res = {u'msg': u'Add service instance %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service instance
    - oid: id or uuid of the service instance
    - field: can be name, version, desc, status, active,
        bpmn_process_id, resource_uuid,  
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'serviceinst': params
        }
        uri = u'%s/serviceinsts/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service instance %s with data %s' % (oid, params))
        res = {u'msg': u'Update service instance %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service instance
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service instance %s' % value}
        self.result(res, headers=[u'msg'])
 

class ServiceInstanceConfigController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'instance.configs'
        aliases = ['configs']
        aliases_only = True
        stacked_on = 'instances'
        stacked_type = 'nested'
        description = "Service instance configuration management"

    @expose(aliases=[u'list <id> [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List service instance configurations.
    - id : instance id
    - field : name, id, uuid, objid, version, status, service_instance_id, filter_creation_date_stop,
              filter_modification_date_start, filter_modification_date_stop, filter_expiry_date_start,
              filter_expiry_date_stop
        """
        value = self.get_arg(name=u'id')
        self.app.kvargs[u'service_instance_id'] = value
        data = urllib.urlencode(self.app.kvargs)
        uri = u'%s/instancecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        fields = [u'id', u'uuid', u'name', u'service_instance_id', u'json_cfg', u'active', u'date.creation']
        headers = [u'id', u'uuid', u'name', u'service', u'config', u'active', u'creation']
        self.result(res, key=u'instancecfgs', headers=headers, fields=fields)
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service instance configuration  by value id or uuid
    - id : config id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/instancecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'instancecfg', details=True)
     
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get service instance configuration permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/instancecfgs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service instance cfgs perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
 
    @expose(aliases=[u'add <service_instance_id> <name> [desc=..] [json_cfg=..][active=..]'], aliases_only=True)
    @check_error
    def add(self):
        """[TODO] Add service instance configuration <service_instance_id> <name>
         - service_instance_id: id or uuid of the service instance
         - field: can be desc, json_cfg, active
        """
        service_instance_id = self.get_arg(name=u'service_instance_id')
        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'instancecfg':{
                u'name':name,
                u'desc': params.get(u'desc', None),
                u'active': params.get(u'active', False),
                u'service_instance_id' : service_instance_id,
                u'json_cfg': json.loads(params.get(u'json_cfg', u'{}')),
            }
        }     
        uri = u'%s/instancecfgs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service instance cfg: %s' % truncate(res))
        res = {u'msg': u'Add service instance cfg %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """[TODO] Update service instance configuration
        - oid: id or uuid of the service instance
        - field: can be name, version, desc, json_cfg, status, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'instancecfg': params
        }
        uri = u'%s/instancecfgs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service instance cfgs %s with data %s' % (oid, params))
        res = {u'msg': u'Update service instance cfgs %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """[TODO] Delete service instance configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/instancecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service instancecfgs cfgs %s' % value}
        self.result(res, headers=[u'msg'])


class ServiceLinkInstanceController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'instance.links'
        aliases = ['links']
        aliases_only = True
        stacked_on = 'instances'
        stacked_type = 'nested'
        description = "Service instance links management"

    @expose(aliases=[u'list <id>'], aliases_only=True)
    @check_error
    def list(self):
        """List service instance links.
    - id : instance id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s/links' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=u'')
        logger.info(res)
        fields = [u'id', u'uuid', u'name', u'end_service_id', u'priority', u'version', u'active', u'date.creation']
        headers = [u'id', u'uuid', u'name', u'child_service', u'priority', u'version', u'active', u'creation']
        self.result(res, key=u'service_links', headers=headers, fields=fields)

    @expose(aliases=[u'update <id> <end_service_id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update service instance link
    - id: id or uuid of the service instance
    - end_service_id: id or uuid of the child service instance
    - field: can be name, desc, priority,
        """
        value = self.get_arg(name=u'id')
        self.app.kvargs[u'end_service_id'] = self.get_arg(name=u'end_service_id')
        data = {
            u'serviceinst': self.app.kvargs
        }
        uri = u'%s/serviceinsts/%s/link' % (self.baseuri, value)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service instance link %s with data %s' % (value, data))
        res = {u'msg': u'Update service instance link %s with data %s' % (value, data)}
        self.result(res, headers=[u'msg'])


class ServiceInstanceConsumeController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'instance.consumes'
        aliases = ['consumes']
        aliases_only = True
        stacked_on = 'instances'
        stacked_type = 'nested'
        description = "Service instance consume management"

    @expose(aliases=[u'list <id>'], aliases_only=True)
    @check_error
    def list(self):
        """List service instance links.
    - id : instance id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s/consumes' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=u'')
        logger.info(res)
        fields = [u'id', u'uuid', u'name', u'end_service_id', u'priority', u'version', u'active', u'date.creation']
        headers = [u'id', u'uuid', u'name', u'child_service', u'priority', u'version', u'active', u'creation']
        self.result(res, key=u'service_links', headers=headers, fields=fields)


# TODO cli commands to manage  ServiceInstanteCost   
class ServiceInstanteCostController(ServiceControllerChild):
    class Meta:
        label = 'instances.instantecosts'
        description = "Service instance instante cost management"


# TODO cli commands to manage  ServiceAggregateCost     
class ServiceAggregateCostController(ServiceControllerChild):
    class Meta:
        label = 'instances.aggregatecosts'
        description = "Service instance aggregate cost management"
       
 
service_controller_handlers = [
    ServiceController,
    ServiceTypeController,
    ServiceCostParamController,
    ServiceTypeProcessController,
    ServiceDefinitionController,
    ServiceDefinitionConfigController,
    ServiceDefinitionCostController,
    # ServiceLinkDefinitionController,
    ServiceInstanceController,
    ServiceInstanceConfigController,
    ServiceLinkInstanceController,
    ServiceInstanceConsumeController,
    # ServiceInstanteCostController,
    # ServiceAggregateCostController,
    ServiceCatalogController,
]        