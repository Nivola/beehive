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
import json
 
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
# 
#     def get_service_state(self, uuid):
#         try:
#             res = self._call(u'/v1.0/service/%s' % uuid, u'GET')
#             state = res.get(u'service').get(u'state')
#             logger.debug(u'Get service %s state: %s' % (uuid, state))
#             return state
#         except (NotFoundException, Exception):
#             return u'EXPUNGED'
# 
#     def wait_service(self, uuid, delta=1):
#         """Wait service
#         """
#         logger.debug(u'wait for service: %s' % uuid)
#         state = self.get_service_state(uuid)
#         while state not in [u'ACTIVE', u'ERROR', u'EXPUNGED']:
#             logger.info(u'.')
#             print((u'.'))
#             sleep(delta)
#             state = self.get_service_state(uuid)
 
 
class ServiceTypeController(ServiceControllerChild):
    class Meta:
        label = 'types'
        description = "Service type management"
 
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'servicetypes', headers=[u'id', u'uuid', u'name', u'version', u'status', u'flag_container', u'objclass', u'active', u'date' ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get service type by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicetypes/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicetype', details=True)
 

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service type permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicetypes/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get servicetype perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)         
    
    @expose(aliases=[u'add <name> <version> [flag_container=..] [objclass=..] '\
                     u'[active=..] [status=..] '],
            aliases_only=True)      
    def add(self):
        """Add service type <name> <version>
         - field: can be desc, objclass, flag_container, status, active 
        """
        name = self.get_arg(name=u'name')
        version = self.get_arg(name=u'version')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'servicetype':{
                u'name':name, 
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
    def delete(self):
        """Delete servicetype
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicetypes/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service type %s' % value}
        self.result(res, headers=[u'msg'])
 
class ServiceCostParamController(ServiceControllerChild):
    class Meta:
        label = 'types.costs'
        description = "Service type cost management"
  
 
class ServiceControllerDefinitionChild(ServiceControllerChild):
    class Meta:
        stacked_on = 'business_service'
        stacked_type = 'nested' 
 
class ServiceDefinitionController(ServiceControllerChild):
    class Meta:
        label = 'definitions'
        description = "Service definition management"
 
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'servicedefs', headers=[u'id', u'uuid', u'name', u'version', u'status', u'flag_container', u'objclass', u'active', u'date' ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get service definition by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicedefs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicedef', details=True)
 
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service definition permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicedefs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get servicedefinition perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
  
    @expose(aliases=[u'add <service_type_id> <name>  '\
                      u'[desc=..] [priority=..] [status=..] [version=..] [active=..] '],
            aliases_only=True)    
    def add(self):
        """Add service definition <service_type_id> <name> <version> 
         - service_type_id: id or uuid of the service type
         - field: can be desc, priority, status, active
        """
        service_type_id = self.get_arg(name=u'service_type_id')
        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'servicedef':{
                u'name':name, 
                u'version': params.get(u'version', u'1.0'),
                u'desc': params.get(u'desc', None),
                u'status': params.get(u'status', u'DRAFT'),
                u'active': params.get(u'active', False),
                u'service_type_id' : service_type_id,
                u'parent_id' : params.get(u'parent_id', None),
                u'priority' : params.get(u'priority', None),
            }
        }
        uri = u'%s/servicedefs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add servicedefinition: %s' % truncate(res))
        res = {u'msg': u'Add servicedefinition %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
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
    def delete(self):
        """Delete service definition
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicedefs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete servicedefinition %s' % value}
        self.result(res, headers=[u'msg'])
 
 
class ServiceInternalController(ServiceControllerChild):
    class Meta:
        label = 'services'
        description = "Service management"
         
    @expose(help="Service management", hide=True)
    def default(self):
        self.app.args.print_help()        
 
class ServiceLinkDefinitionController(ServiceControllerChild):
    class Meta:
        label = 'definitions.links'
        description = "Service definition link management"

# TODO cli commands to manage  ServiceCostController
# TODO ServiceCost ?  
class ServiceCostController(ServiceControllerChild):
    class Meta:
        label = 'definitions.costs'
        description = "Service definition cost management"

class ServiceConfigController(ServiceControllerChild):
    class Meta:
        label = 'definitions.configs'
        description = "Service definition configuration management"        

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all service definition configuration by field: 
        name, id, uuid, objid, version, status,
        service_definition_id, params, params_type,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicecfgs', headers=[u'id', u'uuid', u'name', u'version', u'service_definition_id', u'params', u'params_type',u'status',  u'active', u'date',  ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get  service definition configuration  by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'servicecfg', details=True)
     
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service definition configuration permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicecfgs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service definition cfgs perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
 
    @expose(aliases=[u'add <service_definition_id> <name> '\
                      u'[desc=..] [params=..][params_type=..][status=..] [version=..][active=..] '],
            aliases_only=True)   
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
    def delete(self):
        """Delete service definition configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service definition cfgs %s' % value}
        self.result(res, headers=[u'msg'])


class ServiceInstanceController(ServiceControllerChild):
    class Meta:
        label = 'instances'
        description = "Service instance management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all service instance by field: 
        name, id, uuid, objid, version, status,
        account_id, service_definition_id, bpmn_process_id, resource_uuid
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
  
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinsts' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'serviceinsts', headers=[u'id', u'uuid', u'name', u'version', u'status', u'flag_container', u'objclass', u'active', u'date' ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get service instance by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'serviceinst', details=True)
 
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service instance permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinsts/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service instance perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
  
    @expose(aliases=[u'add <service_definition_id> <account_id> <name>  '\
                      u'[desc=..] [bpmn_process_id=..] [status=..] [version=..] [active=..] '],
            aliases_only=True)    
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
    def delete(self):
        """Delete service instance
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service instance %s' % value}
        self.result(res, headers=[u'msg'])
 

class ServiceInstanceConfigController(ServiceControllerChild):
    class Meta:
        label = 'instances.configs'
        description = "Service instance configuration management"
 

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all service configuration by field: 
        name, id, uuid, objid, version, status, service_instance_id,
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/instancecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'instancecfgs', headers=[u'id', u'uuid', u'name', u'version', u'service_instance_id',u'status',  u'active', u'date', ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get  service instance configuration  by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/instancecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'instancecfg', details=True)
     
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service instance configuration permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/instancecfgs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service instance cfgs perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
 
    @expose(aliases=[u'add <service_instance_id> <name> '\
                      u'[desc=..] [json_cfg=..][active=..]'],
            aliases_only=True)   
    def add(self):
        """Add service instance configuration <service_instance_id> <name> 
         - service_instance_id: id or uuid of the service instance
         - field: can be desc, json_cfg, active
        """
        service_instance_id = self.get_arg(name=u'service_instance_id')
        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
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
    def update(self):
        """Update service instance configuration
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
    def delete(self):
        """Delete service instance configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/instancecfgs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service instancecfgs cfgs %s' % value}
        self.result(res, headers=[u'msg'])
 
  
class ServiceLinkInstanceController(ServiceControllerChild):
    class Meta:
        label = 'instances.links'
        description = "Service instance link management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all service instance link by field: 
        name, id, uuid, objid, version, status, 
        attributes, start_service_id, end_service_id, priority
        filter_creation_date_stop, filter_modification_date_start,
        filter_modification_date_stop, filter_expiry_date_start,
        filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinstlinks' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'instancelinks', headers=[u'id', u'uuid', u'name', u'start_service_id', u'end_service_id', u'priority', u'version',u'status',  u'active', u'date', ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get service instance link by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinstlinks/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'instancelink', details=True)
     
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service instance link permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinstlinks/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service instance link perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
 
    @expose(aliases=[u'add <start_service_id> <end_service_id> '\
                      u' [name=..] [desc=..] [priority=..] [attributes=..] '],
            aliases_only=True)   
    def add(self):
        """Add service instance link <start_service_id> <end_service_id>
         - start_service_id: id or uuid of the service instance 
         - end_service_id: id or uuid of the service instance 
         - field: can be name, desc, priority, attributes
        """
        start_service_id = self.get_arg(name=u'start_service_id')
        end_service_id = self.get_arg(name=u'end_service_id')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'instancelink':{
                u'name':params.get(u'name', u''), 
                u'desc': params.get(u'desc', u''),
                u'start_service_id' : start_service_id,
                u'end_service_id' : end_service_id,
                u'priority':params.get(u'priority', 0),
                u'attributes':params.get(u'attributes', u''),
            }
        }    
        uri = u'%s/serviceinstlinks' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service instance link: %s' % truncate(res))
        res = {u'msg': u'Add service instance link %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    def update(self):
        """Update service instance link
        - oid: id or uuid of the service instance link
         - field: can be name, desc, priority, attributes, version, active
        """
        oid = self.get_arg(name=u'oid')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'instancelink': params
        }
        uri = u'%s/serviceinstlinks/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update service instance link %s with data %s' % (oid, params))
        res = {u'msg': u'Update service instance link %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete service instance configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinstlinks/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service instance link %s' % value}
        self.result(res, headers=[u'msg'])

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
       
class ServiceCatalogController(ServiceControllerChild):
    class Meta:
        label = 'servicecatalogs'
        description = "Service catalog management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'catalogs', headers=[u'id', u'uuid', u'name', u'version', u'status', u'flag_container', u'objclass', u'active', u'date' ])
 
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get service catalog by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'catalog', details=True)
 
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get service catalog permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/srvcatalogs/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get service catalog perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)    
  
    @expose(aliases=[u'add <name>  '\
                      u'[desc=..] '],
            aliases_only=True)    
    def add(self):
        """Add service catalogo <name>  
         - service_type_id: id or uuid of the service type
         - field: can be desc
        """

        name = self.get_arg(name=u'name')

        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data ={
            u'catalog':{
                u'name':name, 
                u'desc': params.get(u'desc', None),
            }
        }
        uri = u'%s/srvcatalogs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service catalog: %s' % truncate(res))
        res = {u'msg': u'Add service catalog %s' % res}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
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
    def delete(self):
        """Delete service catalog
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
#         jobid = res.get(u'jobid', None)
#         if jobid is not None:
#             self.wait_job(jobid)
 
        res = {u'msg': u'Delete service catalog %s' % value}
        self.result(res, headers=[u'msg'])
       
 
service_controller_handlers = [
    ServiceController,
    ServiceTypeController,
    ServiceCostParamController,
    ServiceDefinitionController,
    ServiceConfigController,
    ServiceCostController,
#     ServiceLinkDefinitionController,
    ServiceInstanceController,
    ServiceInstanceConfigController,
    ServiceLinkInstanceController,
#     ServiceInstanteCostController,
#     ServiceAggregateCostController,    
    ServiceCatalogController,
    
]        