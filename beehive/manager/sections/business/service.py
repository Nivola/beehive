"""
Created on Sep 27, 2017
 
@author: darkbk
"""
import os
import logging
import urllib

from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from beecell.simple import truncate, format_date
import json
from urllib import urlencode
from beehive.manager.sections.business import ConnectionHelper
from datetime import datetime, timedelta

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

    @expose()
    @check_error
    def plugin_types(self):
        """List all plugin_types
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/servicetypes/plugintypes' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'plugintypes', headers=[u'id', u'name', u'objclass'], maxsize=200)

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
        headers = [u'id', u'uuid', u'name', u'version', u'plugintype', u'status', u'flag_container', u'objclass',
                   u'active', u'date.creation']
        self.result(res, key=u'servicetypes', headers=headers)
 
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
    
    @expose(aliases=[u'add <name> <objclass> [field=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Add service type <name> <objclass>
    - field: can be version, container, status
        """
        name = self.get_arg(name=u'name')
        objclass = self.get_arg(name=u'objclass')
        version = self.get_arg(name=u'version', default=u'v1.0', keyvalue=True)
        flag_container = self.get_arg(name=u'container', default=False, keyvalue=True)
        status = self.get_arg(name=u'status', default=u'ACTIVE', keyvalue=True)
        data = {
            u'servicetype': {
                u'name': name,
                u'version': version,
                u'desc': name,
                u'objclass': objclass,
                u'flag_container': flag_container,
                u'status': status,
                u'template_cfg': u'{{}}'
            }
        }
        uri = u'%s/servicetypes' % self.baseuri
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

    @expose(aliases=[u'set', u'set typeoid=<id|uuid|name> method=<met> [name=<name>] [desc=<description>] '
                             u'[process=<key>] [template=@<templatefile>|<template>] '], aliases_only=True)
    @check_error
    def setval(self):
        # , st_uuid, template, name, ):
        typeid = None
        typeoid = self.get_arg(name=u'typeoid', keyvalue=True)
        method = self.get_arg(name=u'method', keyvalue=True)
        # http://{{nws}}/v1.0/nws/servicetypes?name=limits.6d0216b6db7c1cad41d6
        if method is None:
            raise Exception(u'Param method is not defined')
        if typeoid is not None:
            uri = u'%s/servicetypes/%s' % (self.baseuri, typeoid)
            res = self._call(uri, u'GET').get(u'servicetype', {})
            typeid = res.get("id",typeid) 
            if typeid is None:
                raise Exception(u'Could not found a type whose oid is %s' % (typeoid))

        uri = u'%s/serviceprocesses' % self.baseuri
        res = self._call(uri, u'GET', data=u'service_type_id=%s&method_key=%s' % (typeid, method)).get(u'serviceprocesses', [])

        if len(res) >= 1:
            prev=res[0] 
            name = self.get_arg(name=u'name', keyvalue=True, default=prev['method_key'])
            desc = self.get_arg(name=u'desc', keyvalue=True, default=prev['desc'])
            process = self.get_arg(name=u'process', keyvalue=True, default=prev['process_key'])
            template = self.get_arg(name=u'template', keyvalue=True, default=prev['template'])
        else:
            prev=None
            name = self.get_arg(name=u'name', keyvalue=True, default='proc')
            desc = self.get_arg(name=u'desc', keyvalue=True, default='description-%s'%(name))
            process = self.get_arg(name=u'process', keyvalue=True, default='invalid_key')
            template = self.get_arg(name=u'template', keyvalue=True, default="{}")

        if template[0] == '@':
            filename = template[1:]
            if os.path.isfile(filename):
                f = open(filename, 'r')
                template = f.read()
                f.close()
            else:
                raise Exception(u'Jinja template %s is not a file' % filename)

        data = {
            u'serviceprocess':{
                u'name':name,
                u'desc':desc,
                u'service_type_id':str(typeid),
                u'method_key':method,
                u'process_key':process,
                u'template':template
            }
        }
        if prev == None:
            uri = u'%s/serviceprocesses' % self.baseuri
            res = self._call(uri, u'POST', data=data)
            logger.info(res)
            self.result(res)
        else:
            uri = u'%s/serviceprocesses/%s' % (self.baseuri, prev['uuid'])
            res = self._call(uri, u'PUT', data=data)
            logger.info(res)
            self.result(res)


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
        headers = [u'id', u'uuid', u'name', u'version', u'status', u'type', u'active', u'is_default', u'date']
        fields = [u'id', u'uuid', u'name', u'version', u'status', u'service_type_id', u'active', u'is_default',
                  u'date.creation']
        self.result(res, key=u'servicedefs', headers=headers, fields=fields)
 
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
  
    @expose(aliases=[u'add <service_type> <name> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service definition
    - service_type_id: id or uuid of the service type
    - name: name of the service definition
    - field: Identify optional params. Can be: desc, parent_id, priority, status, version, active
        """
        service_type_id = self.get_arg(name=u'service_type')
        name = self.get_arg(name=u'name')
        params = self.get_arg(name=u'params')
        version = self.get_arg(name=u'version', default=u'v1.0', keyvalue=True)
        desc = self.get_arg(name=u'desc', default=name, keyvalue=True)
        status = self.get_arg(name=u'status', default=u'ACTIVE', keyvalue=True)
        parent_id = self.get_arg(name=u'parent', default=None, keyvalue=True)
        priority = self.get_arg(name=u'priority', default=0, keyvalue=True)

        print self.app.kvargs
        # read params from file
        if params.find(u'@') >= 0:
            params = self.load_config(params.replace(u'@', u''))
        else:
            params = json.loads(params)

        data = {
            u'servicedef': {
                u'name': name,
                u'version': version,
                u'desc': desc,
                u'status': status,
                u'service_type_id': service_type_id,
                u'parent_id': parent_id,
                u'priority': priority,
            }
        }
        uri = u'%s/servicedefs' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service definition: %s' % truncate(res))
        resp = {u'msg': u'Add service definition %s' % res[u'uuid']}

        data = {
            u'servicecfg': {
                u'name': u'%s-config' % name,
                u'desc': u'%s-config' % name,
                u'service_definition_id': res[u'uuid'],
                u'params': params,
                u'params_type': u'JSON',
                u'version': version
            }
        }
        uri = u'%s/servicecfgs' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add service definition config: %s' % truncate(res))

        self.result(resp, headers=[u'msg'])
 
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
 
    @expose(aliases=[u'delete <id> [recursive=..]'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service definition
        """
        value = self.get_arg(name=u'id')
        data = {
            u'recursive': self.get_arg(name=u'recursive', default=True, keyvalue=True)
        }
        uri = u'%s/servicedefs/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data=data)
        logger.info(res)
        res = {u'msg': u'Delete servicedefinition %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'config <id>'], aliases_only=True)
    @check_error
    def config(self):
        """List service definition configuration
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/servicecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=u'service_definition_id=%s' % value).get(u'servicecfgs', [{}])[0]
        logger.info(res)
        params = res.pop(u'params', [])
        self.result(res, details=True)
        self.output(u'Params:')
        self.result(params, details=True)
 

class ServiceDefinitionCostController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'unitcosts'
        stacked_on = 'defs'
        stacked_type = 'nested'
        description = "Service type unitary cost management [TODO]"


# class ServiceDefinitionConfigController(ApiController):
#     baseuri = u'/v1.0/nws'
#     subsystem = u'service'
#
#     class Meta:
#         label = 'configs'
#         stacked_on = 'defs'
#         stacked_type = 'nested'
#         description = "Service definition config management"
#
#     @expose(aliases=[u'list <id>'], aliases_only=True)
#     @check_error
#     def list(self):
#         """List all service definition configuration by field:
#         name, id, uuid, objid, version, status,
#         service_definition_id, params, params_type,
#         filter_creation_date_stop, filter_modification_date_start,
#         filter_modification_date_stop, filter_expiry_date_start,
#         filter_expiry_date_stop
#         """
#         value = self.get_arg(name=u'id')
#         data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
#         uri = u'%s/servicecfgs' % self.baseuri
#         res = self._call(uri, u'GET', data=u'service_definition_id=%s' % value)
#         logger.info(res)
#         headers = [u'id', u'uuid', u'name', u'version', u'params_type', u'params', u'active', u'date.creation']
#         self.result(res, key=u'servicecfgs', headers=headers)
#
#     @expose(aliases=[u'get <id>'], aliases_only=True)
#     @check_error
#     def get(self):
#         """Get  service definition configuration  by value id or uuid
#         """
#         value = self.get_arg(name=u'id')
#         uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
#         res = self._call(uri, u'GET')
#         logger.info(res)
#         self.result(res, key=u'servicecfg', details=True)
#
#     @expose(aliases=[u'add <service_definition_id> <name> [desc=..] [params=..] [params_type=..] [status=..] '
#                      u'[version=..] [active=..]'], aliases_only=True)
#     @check_error
#     def add(self):
#         """Add service definition configuration <service_definition_id> <name> <params>
#          - service_definition_id: id or uuid of the service definition
#          - field: can be desc, params, params_type, status, version, active
#         """
#         service_definition_id = self.get_arg(name=u'service_definition_id')
#         name = self.get_arg(name=u'name')
#
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         data ={
#             u'servicecfg':{
#                 u'name':name,
#                 u'version': params.get(u'version', u'1.0'),
#                 u'desc': params.get(u'desc', None),
#                 u'status': params.get(u'status', u'DRAFT'),
#                 u'active': params.get(u'active', False),
#                 u'service_definition_id' : service_definition_id,
#                 u'params':params.get(u'params', u'{}'),
#                 u'params_type':params.get(u'params', u'json')
#
#             }
#         }
#         uri = u'%s/servicecfgs' % (self.baseuri)
#         res = self._call(uri, u'POST', data=data)
#         logger.info(u'Add service definition cfg: %s' % truncate(res))
#         res = {u'msg': u'Add service definition cfg %s' % res}
#         self.result(res, headers=[u'msg'])
#
#     @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
#     @check_error
#     def update(self):
#         """Update service definition configuration
#         - oid: id or uuid of the servicedef
#         - field: can be name, version, desc, params, params_type, status, active
#         """
#         oid = self.get_arg(name=u'oid')
#         params = self.get_query_params(*self.app.pargs.extra_arguments)
#         data = {
#             u'servicecfg': params
#         }
#         uri = u'%s/servicecfgs/%s' % (self.baseuri, oid)
#         self._call(uri, u'PUT', data=data)
#         logger.info(u'Update service definition cfgs %s with data %s' % (oid, params))
#         res = {u'msg': u'Update service definition cfgs %s with data %s' % (oid, params)}
#         self.result(res, headers=[u'msg'])
#
#     @expose(aliases=[u'delete <id>'], aliases_only=True)
#     @check_error
#     def delete(self):
#         """Delete service definition configuration
#         """
#         value = self.get_arg(name=u'id')
#         uri = u'%s/servicecfgs/%s' % (self.baseuri, value)
#         res = self._call(uri, u'DELETE')
#         logger.info(res)
#         res = {u'msg': u'Delete service definition cfgs %s' % value}
#         self.result(res, headers=[u'msg'])


class ServiceCatalogController(ServiceControllerChild):
    class Meta:
        label = 'service.catalogs'
        aliases = ['catalogs']
        aliases_only = True
        description = "Service catalog management"

        # role_template = [
        #     {
        #         u'name': u'CatalogAdminRole-%s',
        #         u'perms': [
        #             {u'subsystem': u'service', u'type': u'ServiceCatalog', u'objid': u'<objid>', u'action': u'*'},
        #         ],
        #         u'perm_tmpls': [
        #             {u'subsystem': u'service', u'type': u'ServiceType.ServiceDefinition', u'objid': u'<objid>',
        #              u'action': u'view'}
        #         ]
        #     },
        #     {
        #         u'name': u'CatalogViewerRole-%s',
        #         u'perms': [
        #             {u'subsystem': u'service', u'type': u'ServiceCatalog', u'objid': u'<objid>', u'action': u'view'},
        #         ]
        #     }
        # ]

    # @expose(aliases=[u'roles <catalog>'], aliases_only=True)
    # @check_error
    # def roles(self):
    #     """Get catalog roles
    #     """
    #     catalog_id = self.get_arg(name=u'catalog')
    #     catalog_id = ConnectionHelper.get_catalog(self, catalog_id).get(u'id')
    #     roles = ConnectionHelper.get_roles(self, u'Catalog%' + u'Role-%s' % catalog_id)
    #
    # @expose(aliases=[u'add-user <catalog> <type> <user>'], aliases_only=True)
    # @check_error
    # def add_user(self):
    #     """Set catalog roles
    # - type: role type. Admin or Viewer
    #     """
    #     catalog_id = self.get_arg(name=u'catalog')
    #     catalog_id = ConnectionHelper.get_catalog(self, catalog_id).get(u'id')
    #     role_type = self.get_arg(name=u'role type. Admin or Viewer')
    #     user = self.get_arg(name=u'user')
    #     ConnectionHelper.set_role(self, u'Catalog%sRole-%s' % (role_type, catalog_id), user)
    #
    # @expose(aliases=[u'del-user <catalog> <type> <user>'], aliases_only=True)
    # @check_error
    # def del_user(self):
    #     """Unset catalog roles
    # - type: role type. Admin or Viewer
    #     """
    #     catalog_id = self.get_arg(name=u'catalog')
    #     catalog_id = ConnectionHelper.get_catalog(self, catalog_id).get(u'id')
    #     role_type = self.get_arg(name=u'role type. Admin or Viewer')
    #     user = self.get_arg(name=u'user')
    #     ConnectionHelper.set_role(self, u'Catalog%sRole-%s' % (role_type, catalog_id), user, op=u'remove')
    #
    # @expose(aliases=[u'refresh <catalog>'], aliases_only=True)
    # @check_error
    # def refresh(self):
    #     """Refresh catalog roles
    #     """
    #     catalog_id = self.get_arg(name=u'catalog')
    #     catalog_id = ConnectionHelper.get_catalog(self, catalog_id).get(u'id')
    #
    #     # get catalog
    #     uri = u'%s/srvcatalogs/%s' % (self.baseuri, catalog_id)
    #     catalog = self._call(uri, u'GET').get(u'catalog')
    #     catalog_objid = catalog[u'__meta__'][u'objid']
    #
    #     # get catalog defs
    #     uri = u'%s/srvcatalogs/%s/defs' % (self.baseuri, catalog_id)
    #     defs = self._call(uri, u'GET', data=u'size=100').get(u'servicedefs')
    #     defs_objid = []
    #     for definition in defs:
    #         defs_objid.append(definition[u'__meta__'][u'objid'])
    #
    #     # add roles
    #     for role in self._meta.role_template:
    #         name = role.get(u'name') % catalog_id
    #         perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), catalog_objid)
    #         if role.get(u'perm_tmpls', None) is not None:
    #             perm_tmpl = role.get(u'perm_tmpls')[0]
    #             for def_objid in defs_objid:
    #                 perm = ConnectionHelper.set_perms_objid([perm_tmpl], def_objid)
    #                 perms.extend(perm)
    #         ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'roles <catalog>'], aliases_only=True)
    @check_error
    def roles(self):
        """Get catalog roles
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'roles', headers=[u'name', u'desc'], maxsize=200)

    @expose(aliases=[u'users <catalog>'], aliases_only=True)
    @check_error
    def users(self):
        """Get catalog users
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/srvcatalogs/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'users', headers=[u'name', u'role'], maxsize=200)

    @expose(aliases=[u'users-add <catalog> <role> <user>'], aliases_only=True)
    @check_error
    def users_add(self):
        """Add catalog role to a user
        """
        value = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')
        user = self.get_arg(name=u'user')
        data = {
            u'user': {
                u'user_id': user,
                u'role': role
            }
        }
        uri = u'%s/srvcatalogs/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'POST', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

    @expose(aliases=[u'users-del <catalog> <role> <user>'], aliases_only=True)
    @check_error
    def users_del(self):
        """Remove catalog role from a user
        """
        value = self.get_arg(name=u'id')
        role = self.get_arg(name=u'role')
        user = self.get_arg(name=u'user')
        data = {
            u'user': {
                u'user_id': user,
                u'role': role
            }
        }
        uri = u'%s/srvcatalogs/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

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

    @expose(aliases=[u'add <name> [desc=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add service catalog
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

    @expose(aliases=[u'refresh <id> [field=value]'], aliases_only=True)
    @check_error
    def refresh(self):
        """Refresh catalog
    - id: id or uuid of the catalog
        """
        oid = self.get_arg(name=u'id')
        data = {
            u'catalog': {
            }
        }
        uri = u'%s/srvcatalogs/%s' % (self.baseuri, oid)
        self._call(uri, u'PATCH', data=data, timeout=600)
        logger.info(u'Refresh catalog %s' % (oid))
        res = {u'msg': u'Refresh catalog %s' % (oid)}
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

    @expose(aliases=[u'defs <catalog> [field=value]'], aliases_only=True)
    @check_error
    def defs(self):
        """List all service definitions linked to service catalog
        """
        """
    - field = plugintype, flag_container
        - plugintype=.. filter by plugin type
        - flag_container=true select only container type
        """
        catalog_id = self.get_arg(name=u'catalog')
        catalog_id = ConnectionHelper.get_catalog(self, catalog_id).get(u'id')
        data = urllib.urlencode(self.app.kvargs)
        # data = urllib.urlencode({u'flag_container': True})
        uri = u'%s/srvcatalogs/%s/defs' % (self.baseuri, catalog_id)
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'servicedefs', headers=[u'id', u'uuid', u'name', u'version', u'status',
                    u'service_type_id', u'active', u'date.creation'])

    @expose(aliases=[u'def-add <id> <def_ids>'], aliases_only=True)
    @check_error
    def def_add(self):
        """Add service definition to a service catalog
    - def_ids: comma separated service definition ids
        """
        value = self.get_arg(name=u'id')
        definitions = self.get_arg(name=u'definitions')
        data = {
            u'definitions': {
                u'oids': definitions.split(u',')
            }
        }
        uri = u'%s/srvcatalogs/%s/defs' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        msg = u'Add service definitions %s to catalog %s' % (definitions, value)
        logger.info(msg)
        self.result({u'msg': msg}, headers=[u'msg'])


class ServiceInstanceController(ServiceControllerChild):
    fields = [u'id', u'uuid', u'name', u'version', u'account_id', u'service_definition_id', u'status', u'active',
              u'resource_uuid', u'is_container', u'parent.name', u'date.creation']
    headers = [u'id', u'uuid', u'name', u'version', u'account', u'definition', u'status', u'active', u'resource',
               u'is_container', u'parent', u'creation']

    class Meta:
        label = 'insts'
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
        self.result(res, key=u'serviceinsts', headers=self.headers, fields=self.fields)
 
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
 
    @expose(aliases=[u'delete <id> [recursive]'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service instance
        - field: can be recursive
        """
        value = self.get_arg(name=u'id')
        data = {
            u'recursive': self.get_arg(name=u'recursive', default=True, keyvalue=True)
        }
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data=data, timeout=180)
        logger.info(res)
        res = {u'msg': u'Delete service instance %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-tag <id> <tags>'], aliases_only=True)
    @check_error
    def add_tags(self):
        """Add service instance tags
    - tags: comma separated list of tags
        """
        value = self.get_arg(name=u'id')
        tags = self.get_arg(name=u'tags').split(u',')
        data = {
            u'serviceinst': {
                u'tags': {
                    u'cmd': u'add',
                    u'values': tags
                }
            }
        }
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg': u'Add service %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'del-tag <id> <tags>'], aliases_only=True)
    @check_error
    def del_tags(self):
        """Delete service instance tags
    - tags: comma separated list of tags
        """
        value = self.get_arg(name=u'id')
        tags = self.get_arg(name=u'tags').split(u',')
        data = {
            u'serviceinst': {
                u'tags': {
                    u'cmd': u'delete',
                    u'values': tags
                }
            }
        }
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg': u'Delete service %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'linked <id>'], aliases_only=True)
    @check_error
    def linked(self):
        """Get linked service instances
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/serviceinsts/%s/linked' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'serviceinsts', headers=self.headers, fields=self.fields)

    @expose(aliases=[u'config <id>'], aliases_only=True)
    @check_error
    def config(self):
        """Get service instance configuration  by value id or uuid
    - id : config id
        """
        value = self.get_arg(name=u'id')
        self.app.kvargs[u'service_instance_id'] = value
        data = urllib.urlencode(self.app.kvargs)
        uri = u'%s/instancecfgs' % self.baseuri
        res = self._call(uri, u'GET', data=data).get(u'instancecfgs')
        logger.info(res)
        if len(res) > 0:
            self.result(res[0].get(u'json_cfg'), details=True)


class ServiceInstanceConfigController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'instance.configs'
        aliases = ['configs']
        aliases_only = True
        stacked_on = 'insts'
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


class ServiceInstanceTaskController(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'instance.task'
        aliases = ['task']
        aliases_only = True
        stacked_on = 'instances'
        stacked_type = 'nested'
        description = "Service instance tasks management"

    @expose(aliases=[u'list <id> '], aliases_only=True)
    @check_error
    def list(self):
        """List tasks for service .
        """
        ### TODO /serviceinsts/<oid>/task/<taskid>
        instid = self.get_arg()
        # self.app.kvargs[u'service_instance_id'] = value
        # data = urllib.urlencode(self.app.kvargs)
        # data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/serviceinsts/%s/task' % (self.baseuri, instid)
        # res = self._call(uri, u'GET', data=data)
        res = self._call(uri, u'GET')
        logger.info(u'Get service instances tasks: %s' % truncate(res))
        self.result(res, key=u'tasks', headers=[u'instance_id', u'task_id', u'execution_id', u'task_name', u'due_date', u'created'])

    @expose(aliases=[u'get <id> <taskid>'], aliases_only=True)
    @check_error
    def get(self):
        """Get detail for task
        - id : service instance id
        - taskid : task id
        """
        instid = self.get_arg(name=u'id')
        taskid = self.get_arg(name=u'taskid')
        uri = u'%s/serviceinsts/%s/task/%s' % (self.baseuri, instid, taskid)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'variables', headers=res.get("variables", {}).keys())

    @expose(aliases=[u'complete <id> <taskid> [var1=vla1 .. varn=valn]'], aliases_only=True)
    @check_error
    def complete(self):
        """ complete task
        - id service id
        - taskid task id
        - variables json value to set"")
        """
        instid = self.get_arg(name=u'id')
        taskid = self.get_arg(name=u'taskid')
        data= self.app.kvargs
        uri = u'%s/serviceinsts/%s/task/%s' % (self.baseuri, instid, taskid)
        res = self._call(uri, u'POST', data=data)
        self.result(res)


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


class ServiceLinkController(ServiceControllerChild):
    fields = [u'id', u'name', u'active', u'details.type', u'details.start_service.id', u'details.end_service.id',
              u'details.attributes', u'date.creation', u'date.modified']
    headers = [u'id', u'name', u'type', u'start', u'end', u'attributes', u'creation', u'modified']

    class Meta:
        label = 'inst-links'
        aliases = ['links']
        aliases_only = True
        description = "Link management"

    @expose(aliases=[u'add <account> <name> <type> <start> <end>'], aliases_only=True)
    @check_error
    def add(self):
        """Add link <name> of type <type> from service <start> to service <end>
        """
        account = self.get_arg(name=u'account')
        name = self.get_arg(name=u'name')
        type = self.get_arg(name=u'type')
        start_service = self.get_arg(name=u'start')
        end_service = self.get_arg(name=u'end')
        data = {
            u'link': {
                u'account': account,
                u'type': type,
                u'name': name,
                u'attributes': {},
                u'start_service': start_service,
                u'end_service': end_service,
            }
        }
        uri = u'%s/links' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg': u'Add link %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose()
    @check_error
    def count(self):
        """Count all link
        """
        uri = u'%s/links/count' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg': u'Links count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self, *args):
        """List all links by field: type, service, tags
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/links' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'links', headers=self.headers, fields=self.fields)

    @expose(aliases=[u'get <value>'], aliases_only=True)
    @check_error
    def get(self):
        """Get link by value or id
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'link', headers=self.link_headers, details=True)

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

    @expose(aliases=[u'update <value> [name=..] [type=..] [start=..] [end=..]'], aliases_only=True)
    @check_error
    def update(self):
        """Update link with some optional fields
        """
        value = self.get_arg(name=u'value')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'link': {
                u'type': params.get(u'type', None),
                u'name': params.get(u'name', None),
                u'attributes': None,
                u'start_service': params.get(u'start', None),
                u'end_service': params.get(u'end', None),
            }
        }
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg': u'Update link %s' % value}
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
        res = {u'msg': u'Delete link %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-tag <id> <tag>'], aliases_only=True)
    @check_error
    def add_tag(self):
        """Add service link tag
        """
        value = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')
        data = {
            u'service': {
                u'tags': {
                    u'cmd': u'add',
                    u'values': [tag]
                }
            }
        }
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg': u'Add service link %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete-tag <id> <tag>'], aliases_only=True)
    @check_error
    def delete_tag(self):
        """Delete service link tag
        """
        value = self.get_arg(name=u'id')
        tag = self.get_arg(name=u'tag')
        data = {
            u'service': {
                u'tags': {
                    u'cmd': u'delete',
                    u'values': [tag]
                }
            }
        }
        uri = u'%s/links/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        res = {u'msg': u'Delete service link %s tag %s' % (value, value)}
        self.result(res, headers=[u'msg'])


class ServiceTagController(ServiceControllerChild):
    tag_headers = [u'id', u'name', u'date.creation', u'date.modified', u'services', u'links']

    class Meta:
        label = 'instances.tags'
        aliases = ['tags']
        aliases_only = True
        description = "Tag management"

    @expose(aliases=[u'add <account> <value>'], aliases_only=True)
    @check_error
    def add(self):
        """Add tag <value>
        """
        account = self.get_arg(name=u'account')
        value = self.get_arg(name=u'value')
        data = {
            u'tag': {
                u'account': account,
                u'value': value
            }
        }
        uri = u'%s/tags' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg': u'Add tag %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose()
    @check_error
    def count(self):
        """Count all tag
        """
        uri = u'%s/tags/count' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg': u'Tags count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self, *args):
        """List all tags by field: value, service, link
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/tags' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'tags', headers=self.tag_headers)

    @expose(aliases=[u'get <value>'], aliases_only=True)
    @check_error
    def get(self):
        """Get tag by value or id
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/tags/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'tag', headers=self.tag_headers,
                    details=True)
        # if self.format == u'table':
        #    self.result(res[u'tag'], key=u'services', headers=
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
            u'tag': {
                u'value': new_value
            }
        }
        uri = u'%s/tags/%s' % (self.baseuri, value)
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg': u'Update tag %s' % value}
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
        res = {u'msg': u'Delete tag %s' % value}
        self.result(res, headers=[u'msg'])


class ServiceMetricsController(ServiceControllerChild):
    class Meta:
        label = 'service.metrics'
        aliases = ['metrics']
        aliases_only = True
        description = "Service metric management"
    
    @expose(aliases=[u'types [field=value]'], aliases_only=True)
    @check_error
    def types(self):
        """List all service metric type by field:
        name, group_name, metric_type, measure_unit
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/services/metricstypes' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'metric_types', headers=[u'id', u'name', u'group_name', u'metric_type', u'measure_unit'])
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service metric by field:
            day, id, value, metric_num, u'instance', u'metric_type',  u'job_id'
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        header_field = {
            u'id':u'id', 
            u'date': u'creation_date',
            u'num': u'metric_num',
            u'type': u'metric_type',
            u'value': u'value',
            u'instance': u'service_instance_id',
            u'job_id': u'job_id'
        }
        data = self.get_query_params(*self.app.pargs.extra_arguments)
        for k in header_field:
            par = params.get(k, None)
            if par is not None:
                data.pop(k)
                data[header_field[k]]=par
                
        uri = u'%s/services/metrics' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data))
        logger.info(res)
        self.result(res, key=u'metrics', 
                    headers=[u'id', u'date',          u'num',        u'type',        u'value', u'instance',             u'job_id'],
                    fields= [u'id', u'date.creation', u'metric_num', u'metric_type', u'value', u'service_instance_id',  u'job_id'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service catalog by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/services/metrics/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'metric', 
                    headers=[u'id', u'day',           u'num',        u'type',        u'value', u'platform', u'instance',             u'job_id'],
                    fields= [u'id', u'date.creation', u'metric_num', u'metric_type', u'value', u'platform', u'service_instance_id',  u'job_id'])
    
    @expose(aliases=[u'acquire [field=..]'], aliases_only=True)
    @check_error
    def acquire(self):
        """ Acquire metric
    - field: can be account_oid, metric_type_id, instance_oid
        """
        account_oid = self.get_arg(name=u'account_oid', keyvalue=True)
        metric_type_id = self.get_arg(name=u'metric_type_id', keyvalue=True)
        instance_oid = self.get_arg(name=u'instance_oid', keyvalue=True)
        
        data = {
            u'acquire_metric':{
                u'metric_type_id': metric_type_id,
                u'account_oid': account_oid,
                u'service_instance_oid': instance_oid
            }
        }
       
        uri = u'%s/services/metrics/acquire' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Acquire metric : %s' % truncate(res))
        res = {u'msg': u'Acquire metric task %s' % res}
        self.result(res, headers=[u'msg'], maxsize=80)



class ServiceMetricCostsController(ServiceControllerChild):
    class Meta:
        label = 'service.costs'
        aliases = ['costs']
        aliases_only = True
        description = "Service metric management"
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service metric by field:
            id, type, num, u'instance', u'account',  u'job_id', pricelist, date_start, date_end
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        # = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        
        header_field = {
            u'id':u'id', 
            u'type': u'metric_type_name',
            u'num': u'metric_num',
            u'instance': u'instance_oid',
            u'account': u'account_oid',
            u'job_id': u'job_id',
            u'pricelist': u'pricelist_id',
            u'date_start': u'extraction_date_start',
            u'date_end': u'extraction_date_end',
            u'tme_unit': u'time_unit'
        }
        data = self.get_query_params(*self.app.pargs.extra_arguments)
        for k in header_field:
            par = params.get(k, None)
            if par is not None:
                if k.startswith(u'date_'):
                    y, m, g = par.split(u'-')
                    data.pop(k)
                    data[header_field[k]] = datetime(int(y), int(m), int(g))
                else: 
                    data[header_field[k]] = par
                
        uri = u'%s/services/cost_views' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data))
        
        self.result(res, key=u'metric_cost', 
                    headers=[u'id'       , u'eval_date'      , u'type'     , u'value', u'num'       , u'instance'   , u'account',    u'job_id', u'price'        , u'price_iva', u'pricelist'   , u'time_unit'],
                    fields= [u'metric_id', u'extraction_date', u'type_name', u'value', u'metric_num', u'instance_id', u'account_id', u'job_id', u'price_not_iva', u'price_iva', u'pricelist_id', u'time_unit'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service catalog by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/services/cost_views/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)

        self.result(res, key=u'metric_cost', 
                    headers=[u'id'       , u'eval_date'      , u'type'     , u'value', u'num'       , u'platform'     , u'instance'   , u'account',    u'job_id', u'price'        , u'price_iva', u'pricelist'   , u'time_unit'],
                    fields= [u'metric_id', u'extraction_date', u'type_name', u'value', u'metric_num', u'platform_name', u'instance_id', u'account_id', u'job_id', u'price_not_iva', u'price_iva', u'pricelist_id', u'time_unit'])


class ServiceAggregateCostsController(ServiceControllerChild):
    class Meta:
        label = 'service.aggregate_costs'
        aliases = ['aggr_costs']
        aliases_only = True
        description = "Service Aggregate cost management"
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all service metric by field:
            day, id, value, metric_num, platform, u'instance', u'metric_type',  u'job_id'
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        header_field = {
            u'id':u'id', 
            u'type_id': u'metric_type_id',
            u'instance': u'instance_oid',
            u'aggr_type': u'aggregation_type',
            u'period': u'period',
            u'job_id': u'job_id',
            u'date_start': u'evaluation_date_start',
            u'date_end': u'evaluation_date_end',
        }
        data = {}
        for k in header_field:
            par = params.get(k, None)
            if par is not None:
                if k.startswith(u'date_'):
                    g, m, y = par.split(u'-')
                    data[header_field[k]] = datetime(int(y), int(m), int(g))
                else: 
                    data[header_field[k]] = par
                
        uri = u'%s/services/aggregatecosts' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data))
        self.result(res, key=u'aggregate_cost', 
                    headers=[u'id', u'type_id',  u'cost'        , u'cost_iva', u'instance',            u'aggr_type'       , u'period', u'job_id', u'date'],
                    fields= [u'id', u'type_id',  u'cost_not_iva', u'cost_iva', u'service_instance_id', u'aggregation_type', u'period', u'job_id', u'evaluation_date'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service catalog by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/services/aggregatecosts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)

        self.result(res, key=u'aggregate_cost', 
                    headers=[u'id', u'type_id', u'cost'        , u'cost_iva', u'instance',            u'aggr_type'       , u'period', u'job_id', u'date'],
                    fields= [u'id', u'type_id', u'cost_not_iva', u'cost_iva', u'service_instance_id', u'aggregation_type', u'period', u'job_id', u'evaluation_date'])

    @expose(aliases=[u'add <metric_type_id> <cost_iva> <cost_not_iva> <instance_oid> <aggr_type> <period> <job_id> [field=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Add aggregate cost 
    - field: can be date
        """
        metric_type_id = self.get_arg(name=u'metric_type_id')
        cost_iva = self.get_arg(name=u'cost_iva')
        cost_not_iva = self.get_arg(name=u'cost_not_iva')
        instance_oid = self.get_arg(name=u'instance_oid')
        aggregation_type = self.get_arg(name=u'aggr_type')
        period = self.get_arg(name=u'period')
        job_id = self.get_arg(name=u'job_id', keyvalue=True)
        evaluation_date = self.get_arg(name=u'date', default=format_date(datetime.today()), keyvalue=True)
        
        data = {
            u'aggregate_cost':{
#                 u'platform_id':platform_id,
                u'metric_type_id': metric_type_id,
                u'cost_iva': cost_iva,
                u'cost_not_iva': cost_not_iva,
                u'service_instance_oid': instance_oid,
                u'aggregation_type': aggregation_type,
                u'period': period,
                u'job_id': job_id,
                u'evaluation_date':evaluation_date
            }
        }
       
        uri = u'%s/services/aggregatecosts' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add aggregate cost: %s' % truncate(res))
        res = {u'msg': u'Add ggregate cost %s' % res}
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'batch_delete [field=..]'], aliases_only=True)
    @check_error
    def batch_delete(self):
        """Batch Delete aggregate costs
    - field: can be type_id, instance, aggr_type, period, job_id, date_start, date_end, limit
            
        """
#         value = self.get_arg(name=u'id')
        data = {
            u'aggregate_cost':{ 
                u'metric_type_id': self.get_arg(name=u'type_id', keyvalue=True), 
                u'service_instance_id': self.get_arg(name=u'instance', keyvalue=True), 
                u'aggregation_type': self.get_arg(name=u'aggr_type', keyvalue=True),
                u'period': self.get_arg(name=u'period', keyvalue=True),
                u'job_id': self.get_arg(name=u'job_id', keyvalue=True),
                u'limit': self.get_arg(name=u'limit', default=1000, keyvalue=True),
                u'evaluation_date_start':self.get_arg(name=u'date_start', keyvalue=True),
                u'evaluation_date_end':self.get_arg(name=u'date_end', keyvalue=True)
            }
        }
        
        uri = u'%s/services/aggregatecosts' % (self.baseuri)
        res = self._call(uri, u'DELETE', data=data)
        logger.info(res)
        res = {u'msg': u'Delete n. %s aggregation costs' % res.get(u'deleted')}
        self.result(res, headers=[u'msg'])
    
    
    @expose(aliases=[u'aggregate aggr_type period [field=..]'], aliases_only=True)
    @check_error
    def aggregate(self):
        """Generate Aggregate cost with aggr_type={\'daily\', \'monthly\'} period={\'yyyy-mm-dd\', \'yyyy-mm\'}
    - field: can be account_oid, metric_type_id, instance_oid, overwrite
        """
        aggregation_type = self.get_arg(name=u'aggr_type')
        period = self.get_arg(name=u'period')
        account_oid = self.get_arg(name=u'account_oid', keyvalue=True)
        metric_type_id = self.get_arg(name=u'metric_type_id', keyvalue=True)
        overwrite = self.get_arg(name=u'overwrite', keyvalue=True)
        instance_oid = self.get_arg(name=u'instance_oid', keyvalue=True)
        
        data = {
            u'aggregate_cost':{
                u'aggregation_type': aggregation_type,
                u'period': period,
                u'metric_type_id': metric_type_id,
                u'account_oid': account_oid,
                u'service_instance_oid': instance_oid,
                u'overwrite': overwrite
            }
        }
       
        uri = u'%s/services/aggregatecosts/generate' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Aggregate cost: %s' % truncate(res))
        res = {u'msg': u'Aggregate task %s' % res}
        self.result(res, headers=[u'msg'], maxsize=80)
    
service_controller_handlers = [
    ServiceController,
    ServiceTypeController,
    ServiceCostParamController,
    ServiceTypeProcessController,
    ServiceDefinitionController,
    # ServiceDefinitionConfigController,
    ServiceDefinitionCostController,
    # ServiceLinkDefinitionController,
    ServiceInstanceController,
    ServiceInstanceConfigController,
    ServiceInstanceTaskController, 
    ###########
    ServiceLinkInstanceController,
    ServiceInstanceConsumeController,
    # ServiceInstanteCostController,
    # ServiceAggregateCostController,
    ServiceCatalogController,
    ServiceLinkController,
    ServiceTagController,
    ServiceMetricsController,
    ServiceMetricCostsController,
    ServiceAggregateCostsController
]

