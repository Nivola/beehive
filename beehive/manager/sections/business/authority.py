"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
import urllib

from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate
from beehive.manager.sections.business import ConnectionHelper

logger = logging.getLogger(__name__)


# class AuthorityController(BaseController):
#     class Meta:
#         label = 'authority'
#         stacked_on = 'business'
#         stacked_type = 'nested'
#         description = "Business Authority Management"
#         arguments = []
#
#     def _setup(self, base_app):
#         BaseController._setup(self, base_app)


class AuthorityControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'business'
        stacked_type = 'nested'


class OrganizationController(AuthorityControllerChild):
    class Meta:
        label = 'orgs'
        description = "Organization management"

        role_template = [
            {
                u'name': u'OrgAdminRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization',
                     u'objid': u'<objid>', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division',
                     u'objid': u'<objid>' + u'//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                     u'objid': u'<objid>' + u'//*//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                ],
            },
            {
                u'name': u'OrgViewerRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization',
                     u'objid': u'<objid>', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division',
                     u'objid': u'<objid>' + u'//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                ]
            }
        ]

    @expose(aliases=[u'get-roles <organization>'], aliases_only=True)
    @check_error
    def get_roles(self):
        """Get organization roles
        """
        organization_id = self.get_arg(name=u'organization')
        organization_id = ConnectionHelper.get_org(self, organization_id).get(u'id')
        ConnectionHelper.get_roles(self, u'Org%' + u'Role-%s' % organization_id)

    @expose(aliases=[u'set-role <organization> <type> <user>'], aliases_only=True)
    @check_error
    def set_role(self):
        """Get organization roles
    - type: role type. Admin or Viewer
        """
        organization_id = self.get_arg(name=u'organization')
        organization_id = ConnectionHelper.get_org(self, organization_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Org%sRole-%s' % (role_type, organization_id), user)

    @expose(aliases=[u'unset-role <organization> <type> <user>'], aliases_only=True)
    @check_error
    def unset_role(self):
        """Get organization roles
    - type: role type. Admin or Viewer
        """
        organization_id = self.get_arg(name=u'organization')
        organization_id = ConnectionHelper.get_org(self, organization_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Org%sRole-%s' % (role_type, organization_id), user, op=u'remove')

    @expose(aliases=[u'add-roles <organization>'], aliases_only=True)
    @check_error
    def add_roles(self):
        """Add organization roles
        """
        organization_id = self.get_arg(name=u'organization')
        organization_id = ConnectionHelper.get_org(self, organization_id).get(u'id')

        # get organization
        uri = u'%s/organizations/%s' % (self.baseuri, organization_id)
        organization = self._call(uri, u'GET').get(u'organization')
        organization_objid = organization[u'__meta__'][u'objid']

        # add roles
        for role in self._meta.role_template:
            name = role.get(u'name') % organization_id
            perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), organization_objid)
            ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all organizations by field: id, uuid, name, org_type, ext_anag_id,
    attributes, hasvat, partner, referent, email, legalemail, postaladdress
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/organizations' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'organizations',
                    headers=[u'id', u'uuid', u'name', u'org_type', u'ext_anag_id', u'active', u'date.creation'],
                    maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get organization by value uuid or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'organization', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get organization permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/organizations/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get organization perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
 
    @expose(aliases=[u'add <name> <org_type> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add organization <name> <org_type>
    - field: can be desc, ext_anag_id, attributes, hasvat, partner, referent, email, legaemail, postaladdress
        """
        name = self.get_arg(name=u'name')
        org_type = self.get_arg(name=u'org_type')        
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'organization':{
                # u'name':name.split(u'=')[1],
                u'name':name,
                u'desc':params.get(u'desc', None),
                # u'org_type':org_type.split(u'=')[1],
                u'org_type':org_type,
                u'ext_anag_id':params.get(u'ext_anag_id',None),
                u'attributes':params.get(u'attributes',None),
                # u'attribute': params.get(u'attribute', {}),
                u'hasvat':params.get(u'hasvat', False),
                u'partner':params.get(u'partner', False),
                u'referent':params.get(u'referent', None),
                u'email':params.get(u'email', None),
                u'legalemail':params.get(u'legalemail', None),
                u'postaladdress':params.get(u'postaladdress', None),
            }  
         }
        uri = u'%s/organizations' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add organization: %s' % truncate(res))
        res = {u'msg': u'Add organization %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update organization
    - id: id or uuid of the organization
    - field: can be name, desc, org_type, ext_anag_id, active, attributes, hasvat,partner (name surname),
      referent (name surname), email, legalemail, postaladdress
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'organization': params
        }
        uri = u'%s/organizations/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update organization %s with data %s' % (oid, params))
        res = {u'msg': u'Update resource %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete organization
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete organization %s' % value}
        self.result(res, headers=[u'msg'])


class PriceListController(AuthorityControllerChild):
    class Meta:
        label = 'prices'
        description = "PriceLists management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all pricelists by field: organization_id, name, objid,
        contact, email, postaladdress, active
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/pricelists' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'price_list', headers=[u'id', u'uuid', u'name', u'version', u'flag_default'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get division by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/pricelists/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'price_list', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get division permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/pricelists/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get pricelist perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)

    @expose(aliases=[u'add <name> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add pricelist.
    - field : can be desc, version, is_default
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc', default=name, keyvalue=True)
        version = self.get_arg(name=u'version', default=u'v1.0', keyvalue=True)
        flag_default = self.get_arg(name=u'is_default', default=False, keyvalue=True)
        data = {
            u'price_list': {
                u'name': name,
                u'desc': desc,
                u'version': version,
                u'flag_default': flag_default
            }
        }
        uri = u'%s/pricelists' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add pricelist: %s' % truncate(res))
        res = {u'msg': u'Add pricelist %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update pricelist
            - id: id or uuid of the pricelist
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'division': params
        }
        uri = u'%s/pricelists/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update pricelist %s with data %s' % (oid, params))
        res = {u'msg': u'Update pricelist %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete division
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/pricelists/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete pricelist %s' % value}
        self.result(res, headers=[u'msg'])


class DivisionController(AuthorityControllerChild):
    class Meta:
        label = 'divs'
        description = "Divisions management"

        role_template = [
            {
                u'name': u'DivAdminRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization.Division',
                     u'objid': u'<objid>', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>' + u'//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                ],
            },
            {
                u'name': u'DivViewerRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization.Division',
                     u'objid': u'<objid>', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>' + u'//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'view'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'view'},
                ]
            }
        ]

    @expose(aliases=[u'get-roles <division>'], aliases_only=True)
    @check_error
    def get_roles(self):
        """Get division roles
        """
        division_id = self.get_arg(name=u'division')
        division_id = ConnectionHelper.get_div(self, division_id).get(u'id')
        roles = ConnectionHelper.get_roles(self, u'Div%' + u'Role-%s' % division_id)

    @expose(aliases=[u'set-role <division> <type> <user>'], aliases_only=True)
    @check_error
    def set_role(self):
        """Get division roles
    - type: role type. Admin or Viewer
        """
        division_id = self.get_arg(name=u'division')
        division_id = ConnectionHelper.get_div(self, division_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Div%sRole-%s' % (role_type, division_id), user)

    @expose(aliases=[u'unset-role <division> <type> <user>'], aliases_only=True)
    @check_error
    def unset_role(self):
        """Get division roles
    - type: role type. Admin or Viewer
        """
        division_id = self.get_arg(name=u'division')
        division_id = ConnectionHelper.get_div(self, division_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Div%sRole-%s' % (role_type, division_id), user, op=u'remove')

    @expose(aliases=[u'add-roles <division>'], aliases_only=True)
    @check_error
    def add_roles(self):
        """Add division roles
        """
        division_id = self.get_arg(name=u'division')
        division_id = ConnectionHelper.get_div(self, division_id).get(u'id')

        # get division
        uri = u'%s/divisions/%s' % (self.baseuri, division_id)
        division = self._call(uri, u'GET').get(u'division')
        division_objid = division[u'__meta__'][u'objid']

        # add roles
        for role in self._meta.role_template:
            name = role.get(u'name') % division_id
            perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), division_objid)
            ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all divisions by field: organization_id, name, objid,
        contact, email, postaladdress, active
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """ 
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/divisions' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'divisions', headers=[u'id', u'uuid', u'name', u'organization_id', u'contact', u'email',
                    u'postaladdress', u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get division by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'division', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get division permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/divisions/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get division perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
 
    @expose(aliases=[u'add <name> <organization> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add division <name> <organization_id>
    - field: can be desc, contact, email, postaladdress
        """
        name = self.get_arg(name=u'name')
        organization_id = self.get_arg(name=u'organization_id')        
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'division':{
                # u'name':name.split(u'=')[1],
                u'name':name,
                u'desc':params.get(u'desc', None),
                # u'organization_id':organization_id.split(u'=')[1],
                u'organization_id':organization_id,
                u'contact':params.get(u'contact', None),
                u'email':params.get(u'email', None),
                u'postaladdress':params.get(u'postaladdress', None),
            }  
        }
        uri = u'%s/divisions' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add division: %s' % truncate(res))
        res = {u'msg': u'Add division %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update division
            - id: id or uuid of the division
            - field: can be name, desc, email, postaladdress, active
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'division': params
        }
        uri = u'%s/divisions/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update division %s with data %s' % (oid, params))
        res = {u'msg': u'Update division %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete division
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete division %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'wallet <id>'], aliases_only=True)
    @check_error
    @check_error
    def wallet(self):
        """Get division subwallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/wallets' % self.baseuri
        wallet = self._call(uri, u'GET', data=u'division_id=%s' % value).get(u'wallets')[0]
        logger.info(wallet)
        self.result(wallet, headers=[u'id', u'uuid', u'name', u'capital_total', u'capital_used', u'active',
                    u'date.creation'], maxsize=40)

        # get agreements
        self.app.pargs.extra_arguments.append(u'wallet_id=%s' % wallet[u'id'])
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/agreements' % self.baseuri
        res = self._call(uri, u'GET', data=data).get(u'agreements', [])
        logger.info(res)
        self.app.print_output(u'Agreements:')
        self.result(res, headers=[u'id', u'uuid', u'name', u'amount', u'agreement_date', u'active',
                    u'date.creation'], maxsize=40)

        # get consumes
        consumes = []
        uri = u'%s/subwallets' % self.baseuri
        subwallets = self._call(uri, u'GET', data=u'wallet_id=%s' % wallet[u'id']).get(u'subwallets')
        for subwallet in subwallets:
            uri = u'%s/consumes' % self.baseuri
            res = self._call(uri, u'GET', data=u'subwallet_id=%s' % subwallet[u'id']).get(u'consumes', [])
            for item in res:
                item[u'account_id'] = subwallet[u'account_id']
            consumes.extend(res)
        logger.info(consumes)
        self.app.print_output(u'Consumes:')
        self.result(consumes, headers=[u'id', u'uuid', u'name', u'account_id', u'amount', u'evaluation_date', u'active',
                                       u'date.creation'],
                    maxsize=40)

    @expose(aliases=[u'accounts <id>'], aliases_only=True)
    @check_error
    def accounts(self):
        """List all accounts by parent division
        """
        value = self.get_arg(name=u'id')
        data = u'division_id=%s' % value
        uri = u'%s/accounts' % self.baseuri
        accounts = self._call(uri, u'GET', data=data).get(u'accounts', [])

        # get subwallets
        for account in accounts:
            uri = u'%s/subwallets' % self.baseuri
            res = self._call(uri, u'GET', data=u'account_id=%s' % account[u'id']).get(u'subwallets')[0]
            account[u'capital_total'] = res[u'capital_total']
            account[u'capital_used'] = res[u'capital_used']

        logger.info(accounts)
        self.result(accounts, headers=[u'id', u'uuid', u'name', u'contact', u'email',
                    u'capital_total', u'capital_used', u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'consumes <id>'], aliases_only=True)
    @check_error
    def consumes(self):
        """List all consumes of the account
        """
        value = self.get_arg(name=u'id')
        # get subwallet
        uri = u'%s/subwallets' % self.baseuri
        subwallet = self._call(uri, u'GET', data=u'wallet_id=%s' % value).get(u'subwallets')[0]
        uri = u'%s/consumes' % self.baseuri
        res = self._call(uri, u'GET', data=u'subwallet_id=%s' % subwallet[u'id']).get(u'consumes', [])
        logger.info(res)
        self.result(res, headers=[u'id', u'uuid', u'name', u'amount', u'evaluation_date', u'active', u'date.creation'],
                    maxsize=40)


class AccountController(AuthorityControllerChild):
    class Meta:
        label = 'accounts'
        description = "Accounts management"
        role_template = [
            {
                u'name': u'AccountAdminRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceInstanceConfig',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*', u'action': u'*'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'*//*//*//*', u'action': u'view'},
                ],
            },
            {
                u'name': u'AccountViewerRole-%s',
                u'perms': [
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account',
                     u'objid': u'<objid>', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceInstance',
                     u'objid': u'<objid>' + u'//*', u'action': u'view'},
                    {u'subsystem': u'service',
                     u'type': u'Organization.Division.Account.ServiceInstance.ServiceLinkInst',
                     u'objid': u'<objid>' + u'//*//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceLink',
                     u'objid': u'<objid>' + u'//*', u'action': u'view'},
                    {u'subsystem': u'service', u'type': u'Organization.Division.Account.ServiceTag',
                     u'objid': u'<objid>' + u'//*', u'action': u'view'}
                ]
            }
        ]

        default_data = [
            {u'name': u'Centos7.2', u'template': u'Centos7.2Sync', u'type': u'image'},
            {u'name': u'Centos6.9', u'template': u'Centos6.9Sync', u'type': u'image'},
            {u'name': u'VpcBE', u'template': u'VpcBESync', u'type': u'vpc'},
            {u'name': u'SubnetBE-torino01', u'vpc': u'VpcBE', u'zone': u'SiteTorino01',
             u'cidr': u'10.138.128.0/21', u'type': u'subnet'},
            {u'name': u'SubnetBE-vercelli01', u'vpc': u'VpcBE', u'zone': u'SiteVercelli01', u'cidr': u'10.138.192.0/21',
             u'type': u'subnet'},
            {u'name': u'SecurityGroupBE', u'vpc': u'VpcBE', u'type': u'sg'},
            {u'name': u'VpcWEB', u'template': u'VpcWEBSync', u'type': u'vpc'},
            {u'name': u'SubnetWEB-torino01', u'vpc': u'VpcWEB', u'zone': u'SiteTorino01', u'cidr': u'10.138.136.0/21',
             u'type': u'subnet'},
            {u'name': u'SubnetWEB-vercelli01', u'vpc': u'VpcWEB', u'zone': u'SiteVercelli01',
             u'cidr': u'10.138.200.0/21', u'type': u'subnet'},
            {u'name': u'SecurityGroupWEB', u'vpc': u'VpcWEB', u'template': u'SecurityGroupWEBSync', u'type': u'sg'},
        ]
        default_methods = {
            u'image': ConnectionHelper.create_image,
            u'vpc': ConnectionHelper.create_vpc,
            u'sg': ConnectionHelper.create_sg,
            u'subnet': ConnectionHelper.create_subnet,
        }

    @expose(aliases=[u'get-roles <account>'], aliases_only=True)
    @check_error
    def get_roles(self):
        """Get account roles
        """
        account_id = self.get_arg(name=u'account')
        account_id = ConnectionHelper.get_account(self, account_id).get(u'id')
        roles = ConnectionHelper.get_roles(self, u'Account%' + u'Role-%s' % account_id)

    @expose(aliases=[u'set-role <account> <type> <user>'], aliases_only=True)
    @check_error
    def set_role(self):
        """Get account roles
    - type: role type. Admin or Viewer
        """
        account_id = self.get_arg(name=u'account')
        account_id = ConnectionHelper.get_account(self, account_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Account%sRole-%s' % (role_type, account_id), user)

    @expose(aliases=[u'unset-role <account> <type> <user>'], aliases_only=True)
    @check_error
    def unset_role(self):
        """Get account roles
    - type: role type. Admin or Viewer
        """
        account_id = self.get_arg(name=u'account')
        account_id = ConnectionHelper.get_account(self, account_id).get(u'id')
        role_type = self.get_arg(name=u'role type. Admin or Viewer')
        user = self.get_arg(name=u'user')
        ConnectionHelper.set_role(self, u'Account%sRole-%s' % (role_type, account_id), user, op=u'remove')

    @expose(aliases=[u'add-roles <account>'], aliases_only=True)
    @check_error
    def add_roles(self):
        """Add account roles
        """
        account_id = self.get_arg(name=u'account')
        account_id = ConnectionHelper.get_account(self, account_id).get(u'id')

        # get account
        uri = u'%s/accounts/%s' % (self.baseuri, account_id)
        account = self._call(uri, u'GET').get(u'account')
        account_objid = account[u'__meta__'][u'objid']

        # add roles
        for role in self._meta.role_template:
            name = role.get(u'name') % account_id
            perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), account_objid)
            ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all accounts by field: name, uuid, division_id,
        active, contact, email, email_support, email_support_link,
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """ 
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/accounts' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'accounts', headers=[u'id', u'uuid', u'name', u'division_name', u'contact', u'email',
                    u'email_support', u'email_support_link', u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get account by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'account', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get account permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/accounts/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get account perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'yaskss <id>'], aliases_only=True)
    @check_error
    def tasks(self):
        """Get account permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s/tasks' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(u'Get account tasks: %s' % truncate(res))
        self.result(res, key=u'tasks', headers=[u'instance_id', u'task_id', u'execution_id', u'task_name', u'due_date', u'created'])
  
    @expose(aliases=[u'add <name> <division_id> [field=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Add account <name> <division_id>
    - field: can be desc, contact, email, email_support, email_support_link, note
        """
        name = self.get_arg(name=u'name')
        division_id = self.get_arg(name=u'division_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        data = {
            u'account':{
                # u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
                #  u'division_id':division_id.split(u'=')[1],
                u'division_id':division_id,
                u'contact':params.get(u'contact', None),
                u'email':params.get(u'email', None),
                u'note':params.get(u'note', None), 
                u'email_support':params.get(u'email_support', None),
                u'email_support_link':params.get(u'email_support_link', None),
            }  
         }        
        uri = u'%s/accounts' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add account: %s' % truncate(res))
        res = {u'msg': u'Add account %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update account
            - id: id or uuid of the account
            - field: can be name, desc, email, contact, active, note, email_support, email_support_link
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'account': params
        }
        uri = u'%s/accounts/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update account %s with data %s' % (oid, params))
        res = {u'msg': u'Update account %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete account
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete account %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'wallet <id>'], aliases_only=True)
    @check_error
    def wallet(self):
        """Get account subwallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/subwallets' % self.baseuri
        res = self._call(uri, u'GET', data=u'account_id=%s' % value).get(u'subwallets')[0]
        logger.info(res)
        self.result(res, headers=[u'id', u'uuid', u'name', u'capital_total', u'capital_used', u'active',
                    u'date.creation'], maxsize=40)

    @expose(aliases=[u'consumes <id>'], aliases_only=True)
    @check_error
    def consumes(self):
        """List all consumes of the account
        """
        value = self.get_arg(name=u'id')
        # get subwallet
        uri = u'%s/subwallets' % self.baseuri
        subwallet = self._call(uri, u'GET', data=u'wallet_id=%s' % value).get(u'subwallets')[0]
        uri = u'%s/consumes' % self.baseuri
        res = self._call(uri, u'GET', data=u'subwallet_id=%s' % subwallet[u'id']).get(u'consumes', [])
        logger.info(res)
        self.result(res, headers=[u'id', u'uuid', u'name', u'amount', u'evaluation_date', u'active', u'date.creation'],
                    maxsize=40)

    @expose(aliases=[u'add-core-service <account_id> <type>'], aliases_only=True)
    @check_error
    def add_core_service(self):
        """Add container core service instance
    - type : can be ComputeService, DatabaseService
        """
        account_id = self.get_arg(name=u'account_id')
        plugintype = self.get_arg(name=u'type')

        uri_internal = {
            u'ComputeService': u'computeservices',
            u'DatabaseService': u'databaseservices',
        }

        # check service already exists
        data = urllib.urlencode({u'plugintype': plugintype, u'account_id': account_id, u'flag_container': True})
        uri = u'%s/serviceinsts' % self.baseuri
        service_inst = self._call(uri, u'GET', data=data).get(u'serviceinsts', [])

        if len(service_inst) > 0:
            logger.info(u'Service instance container %s already exists' % plugintype)
            res = {u'msg': u'Service instance container %s already exists' % plugintype}
            self.result(res, headers=[u'msg'])
            return

        # get service def
        data = urllib.urlencode({u'plugintype': plugintype})
        uri = u'%s/servicedefs' % self.baseuri
        service_def = self._call(uri, u'GET', data=data).get(u'servicedefs', [])[0]
        service_definition_id = service_def.get(u'uuid')
        name = u'%s-%s' % (plugintype, account_id)

        # create instance
        data = {
            u'serviceinst': {
                u'name': name,
                u'desc': u'Account %s %s' % (account_id, plugintype),
                u'account_id': account_id,
                u'service_def_id': service_definition_id,
                u'params_resource': u'',
                u'version': u'1.0'
            }
        }
        uri = u'%s/%s' % (self.baseuri, uri_internal.get(plugintype))
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add service instance container: %s' % plugintype)
        res = {u'msg': u'Add service instance %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-default-services <account_id>'], aliases_only=True)
    @check_error
    def add_default_services(self):
        """Add default compute service child instances

        :param account: account id
        :param data: dict with service data
        :return:
        """
        account_id = self.get_arg(name=u'account_id')

        for item in self._meta.default_data:
            item[u'account'] = account_id
            type = item.pop(u'type')
            if not ConnectionHelper.service_instance_exist(self, type, u'%s-%s' % (item[u'name'], account_id)):
                func = self._meta.default_methods.get(type)
                func(self, **item)

    @expose(aliases=[u'delete-service <service_id>'], aliases_only=True)
    @check_error
    def delete_service(self):
        """Delete service instance
        """
        value = self.get_arg(name=u'service_id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete service instance %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'services <account> [field=value]'], aliases_only=True)
    @check_error
    def services(self):
        """List service instances.
    - id : account id
    - field: all=true show all the core services with childs
        """
        self.app.kvargs[u'account_id'] = self.get_arg(name=u'id')
        self.app.kvargs[u'size'] = 100
        all = self.get_arg(name=u'all', keyvalue=True, default=False)
        if all is False:
            self.app.kvargs[u'flag_container'] = True
        data = urllib.urlencode(self.app.kvargs)
        ConnectionHelper.get_service_instances(self, data)

        # uri = u'%s/serviceinsts' % self.baseuri
        # res = self._call(uri, u'GET', data=data)
        # logger.info(res)
        # fields = [u'id', u'uuid', u'name', u'version', u'service_definition_id', u'status', u'active',
        #           u'resource_uuid', u'is_container', u'parent.name', u'date.creation']
        # headers = [u'id', u'uuid', u'name', u'version', u'definition', u'status', u'active', u'resource',
        #            u'is_container', u'parent', u'creation']
        # self.result(res, key=u'serviceinsts', headers=headers, fields=fields)


class SubwalletController(AuthorityControllerChild):
    class Meta:
        label = 'subwallets'
        description = "Subwallets management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all subwallets by field: name, uuid, account_id,
        active, capital_used_max_range, evaluation_date_start,evaluation_date_stop, 
        capital_total, capital_total_min_range, capital_total_max_range,
        capital_used, capital_used_min_range, capital_used_max_range,
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """

        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/subwallets' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'subwallets', headers=[u'id', u'uuid', u'name', u'account_id', u'wallet_id',
                    u'capital_total', u'capital_used', u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get subwallet by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/subwallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'subwallet', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get subwallet permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/subwallets/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get subwallet perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <wallet_id> <account_id> [name=..] [desc=..] [active=..] [evaluation_date=..] '
                     u'[capital_total=..] [capital_used=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add subwallet <wallet_id> <account_id>
            - field: can be name, desc, capital_total, capital_used, evaluation_date
        """
        name = self.get_arg(name=u'name')
        wallet_id = self.get_arg(name=u'wallet_id')
        account_id = self.get_arg(name=u'account_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
    
        data = {
            u'subwallet':{
                # u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
                #  u'wallet_id':wallet_id.split(u'=')[1],
                # u'account_id':account_id.split(u'=')[1],
                u'wallet_id':wallet_id,    
                u'account_id':account_id,         
                u'capital_total':params.get(u'capital_total', None),
                u'capital_used':params.get(u'capital_used', None),
                u'evaluation_date': params.get(u'evaluation_date', None)            
            }
        }

        uri = u'%s/subwallets' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add subwallet: %s' % truncate(res))
        res = {u'msg': u'Add subwallet %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update subwallet
            - id: id or uuid of the subwallet
            - field: can be name, desc, active, capital_total, capital_used, evaluation_date 
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'subwallet': params
        }
        uri = u'%s/subwallets/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update subwallet %s with data %s' % (oid, params))
        res = {u'msg': u'Update subwallet %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete subwallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/subwallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete subwallet %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'consumes <id> [field=value]'], aliases_only=True)
    @check_error
    def consumes(self):
        """List all consumes by subwallets and by field:
        """
        value = self.get_arg(name=u'id')
        self.app.pargs.extra_arguments.append(u'subwallet_id=%s' % value)
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/consumes' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'consumes', headers=[u'id', u'uuid', u'name', u'subwallet_id', u'amount',
                    u'evaluation_date', u'active', u'date.creation'], maxsize=40)


class WalletController(AuthorityControllerChild):
    class Meta:
        label = 'wallets'
        description = "Wallets management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all Wallets by field: name, uuid, division_id,
        active, capital_used_max_range, evaluation_date_start,evaluation_date_stop, 
        capital_total, capital_total_min_range, capital_total_max_range,
        capital_used, capital_used_min_range, capital_used_max_range
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """ 
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/wallets' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'wallets', headers=[u'id', u'uuid', u'name', u'division_id', u'capital_total',
                    u'capital_used', u'evaluation_date' u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get wallet by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/wallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'wallet', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get wallet permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/wallets/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get wallet perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <division_id> [desc=..] [name=..] [active=..] [evaluation_date=..] [capital_total=..] '
                     u'[capital_used=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add wallet <division_id>
            - field: can be name, desc, active, capital_total, capital_used, evaluation_date
        """
        division_id = self.get_arg(name=u'division_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
    
        data = {
            u'wallet':{
                u'name': params.get(u'name', None),
                u'desc':params.get(u'desc', None),   
                # u'division_id':division_id.split(u'=')[1],
                u'division_id': division_id,
                u'capital_total':params.get(u'capital_total', None),
                u'capital_used':params.get(u'capital_used', None),
                u'evaluation_date': params.get(u'evaluation_date', None)            
            }
        }

        uri = u'%s/wallets' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add wallet: %s' % truncate(res))
        res = {u'msg': u'Add wallet %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update wallet
            - id: id or uuid of the wallet
            - field: can be name, desc, active, capital_total, capital_used, evaluation_date 
        """
        oid = self.get_arg(name=u'id')
        print self.app.kvargs
        params = self.app.kvargs #self.app.kvargs
        data = {
            u'wallet': params
        }
        uri = u'%s/wallets/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update wallet %s with data %s' % (oid, params))
        res = {u'msg': u'Update wallet %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete wallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/wallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete wallet %s' % value}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'agreements <id> [field=value]'], aliases_only=True)
    @check_error
    def agreements(self):
        """List all agreements of the wallet
        """
        value = self.get_arg(name=u'id')
        self.app.pargs.extra_arguments.append(u'wallet_id=%s' % value)
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/agreements' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'agreements', headers=[u'id', u'uuid', u'name', u'amount', u'agreement_date', u'active',
                    u'date.creation'], maxsize=40)

    @expose(aliases=[u'subwallets <id> [field=value]'], aliases_only=True)
    @check_error
    def subwallets(self):
        """List all subwallets by parent wallet
        """
        value = self.get_arg(name=u'id')
        self.app.pargs.extra_arguments.append(u'wallet_id=%s' % value)
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/subwallets' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'subwallets', headers=[u'id', u'uuid', u'name', u'capital_total', u'capital_used',
                    u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'consumes <id> [field=value]'], aliases_only=True)
    @check_error
    def consumes(self):
        """List all consumes by wallet
        """
        value = self.get_arg(name=u'id')
        # get subwallets
        uri = u'%s/subwallets' % self.baseuri
        subwallets = self._call(uri, u'GET', data=u'wallet_id=%s' % value).get(u'subwallets', [])
        res = []
        for subwallet in subwallets:
            uri = u'%s/consumes' % self.baseuri
            consumes = self._call(uri, u'GET', data=u'subwallet_id=%s' % subwallet[u'id']).get(u'consumes', [])
            for consume in consumes:
                consume[u'account_id'] = subwallet[u'account_id']
            res.extend(consumes)
        logger.info(res)
        self.result(res, headers=[u'id', u'uuid', u'name', u'account_id', u'amount', u'evaluation_date', u'active',
                    u'date.creation'], maxsize=40)


class AgreementController(AuthorityControllerChild):
    class Meta:
        label = 'agreements'
        description = "Agreements management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all agreements by field: name, uuid, wallet_id,
        active, amount, amount_min_range, amount_max_range,
        agreement_date,agreement_date_start,agreement_date_stop,
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """ 
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/agreements' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'agreements', headers=[u'id', u'uuid', u'name', u'wallet_id', u'amount',
                    u'agreement_date', u'active', u'date.creation'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get agreement by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/agreements/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'agreement', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get agreement permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/agreements/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get agreement perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <name> <wallet_id> [desc=..] [amount=..] [agreement_date=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add agreement <name> <wallet_id>
            - field: can be desc, amount, agreement_date 
        """
        name = self.get_arg(name=u'name')
        wallet_id = self.get_arg(name=u'wallet_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        data = {
            u'agreement':{
                # u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
                # u'wallet_id':wallet_id.split(u'=')[1],
                u'wallet_id':wallet_id,                              
                u'amount':params.get(u'amount', None),
                u'agreement_date': params.get(u'agreement_date', None)            
            }
        }

        uri = u'%s/agreements' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add agreement: %s' % truncate(res))
        res = {u'msg': u'Add agreement %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <id> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update agreement
            - id: id or uuid of the agreement
            - field: can be name, desc, amount, agreement_date, active 
        """
        oid = self.get_arg(name=u'id')
        params = self.app.kvargs
        data = {
            u'agreement': params
        }
        uri = u'%s/agreements/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update agreement %s with data %s' % (oid, params))
        res = {u'msg': u'Update agreement %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete agreement
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/agreements/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete agreement %s' % value}
        self.result(res, headers=[u'msg'])


class ConsumeController(AuthorityControllerChild):
    class Meta:
        label = 'consumes'
        description = "Consumes management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all agreements by field: name, uuid, subwallet_id,
        active,
        filter_expired,filter_creation_date_start,filter_creation_date_stop,
        filter_modification_date_start, filter_modification_date_stop,
        filter_expiry_date_start,filter_expiry_date_stop
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/consumes' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'consumes', headers=[u'id', u'uuid', u'name', u'account_id', u'subwallet_id', u'amount',
                    u'evaluation_date', u'active', u'date.creation'], maxsize=40)


authority_controller_handlers = [
    # AuthorityController,
    OrganizationController,
    PriceListController,
    DivisionController,
    AccountController,
    SubwalletController,
    WalletController,
    AgreementController,
    ConsumeController,
]
