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

    # def __add_role(self, account_id):
    #     # get account
    #     uri = u'%s/organizations/%s' % (self.baseuri, account_id)
    #     account = self._call(uri, u'GET').get(u'account')
    #     account_objid = account[u'__meta__'][u'objid']
    #
    #     # add roles
    #     for role in self._meta.role_template:
    #         name = role.get(u'name') % account_id
    #         perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), account_objid)
    #         ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'roles <account>'], aliases_only=True)
    @check_error
    def roles(self):
        """Get organization roles
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'roles', headers=[u'name', u'desc'], maxsize=200)

    @expose(aliases=[u'users <account>'], aliases_only=True)
    @check_error
    def users(self):
        """Get organization users
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'users', headers=[u'name', u'role'], maxsize=200)

    @expose(aliases=[u'users-add <organization> <role> <user>'], aliases_only=True)
    @check_error
    def users_add(self):
        """Add organization role to a user
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
        uri = u'%s/organizations/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'POST', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

    @expose(aliases=[u'users-del <organization> <role> <user>'], aliases_only=True)
    @check_error
    def users_del(self):
        """Remove organization role from a user
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
        uri = u'%s/organizations/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

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
        headers = [u'id', u'uuid', u'name', u'type', u'divisions', u'anagrafica', u'status', u'date']
        fields = [u'id', u'uuid', u'name', u'org_type', u'divisions', u'ext_anag_id', u'status', u'date.creation']
        self.result(res, key=u'organizations', headers=headers, fields=fields, maxsize=40)

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

    @expose(aliases=[u'refresh <id> [field=value]'], aliases_only=True)
    @check_error
    def refresh(self):
        """Refresh organization
    - id: id or uuid of the organization
        """
        oid = self.get_arg(name=u'id')

        data = {
            u'organization': {
            }
        }
        uri = u'%s/organizations/%s' % (self.baseuri, oid)
        self._call(uri, u'PATCH', data=data, timeout=600)
        logger.info(u'Refresh organization %s' % (oid))
        res = {u'msg': u'Refresh organization %s' % (oid)}
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
        """Get pricelist by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/pricelists/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'price_list', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get pricelist permissions by id, uuid or name
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

    # def __add_role(self, account_id):
    #     # get account
    #     uri = u'%s/divisions/%s' % (self.baseuri, account_id)
    #     account = self._call(uri, u'GET').get(u'account')
    #     account_objid = account[u'__meta__'][u'objid']
    #
    #     # add roles
    #     for role in self._meta.role_template:
    #         name = role.get(u'name') % account_id
    #         perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), account_objid)
    #         ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'roles <account>'], aliases_only=True)
    @check_error
    def roles(self):
        """Get division roles
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'roles', headers=[u'name', u'desc'], maxsize=200)

    @expose(aliases=[u'users <account>'], aliases_only=True)
    @check_error
    def users(self):
        """Get division users
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'users', headers=[u'name', u'role'], maxsize=200)

    @expose(aliases=[u'users-add <division> <role> <user>'], aliases_only=True)
    @check_error
    def users_add(self):
        """Add division role to a user
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
        uri = u'%s/divisions/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'POST', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

    @expose(aliases=[u'users-del <division> <role> <user>'], aliases_only=True)
    @check_error
    def users_del(self):
        """Remove division role from a user
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
        uri = u'%s/divisions/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

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
        headers = [u'id', u'uuid', u'name', u'organization', u'accounts', u'contact', u'email', u'postaladdress',
                   u'status', u'date']
        fields = [u'id', u'uuid', u'name', u'organization_name', u'accounts', u'contact', u'email', u'postaladdress',
                  u'status', u'date.creation']
        self.result(res, key=u'divisions', headers=headers, fields=fields, maxsize=40)

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

    @expose(aliases=[u'refresh <id> [field=value]'], aliases_only=True)
    @check_error
    def refresh(self):
        """Refresh division
    - id: id or uuid of the division
        """
        oid = self.get_arg(name=u'id')

        data = {
            u'division': {
            }
        }
        uri = u'%s/divisions/%s' % (self.baseuri, oid)
        self._call(uri, u'PATCH', data=data, timeout=600)
        logger.info(u'Refresh division %s' % (oid))
        res = {u'msg': u'Refresh division %s' % (oid)}
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
        default_services = {
            u'prod': [
                {u'type': u'ComputeService',
                 u'name': u'ComputeService',
                 u'template': u'compute.medium.sync'},
                {u'type': u'DatabaseService',
                 u'name': u'DatabaseService',
                 u'template': u'database.medium.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'AppEngineService',
                 u'name': u'AppEngineService',
                 u'template': u'appengine.medium.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeImage',
                 u'name': u'Centos7.2',
                 u'template': u'Centos7.2.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeImage',
                 u'name': u'Centos6.9',
                 u'template': u'Centos6.9.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeImage',
                 u'name': u'Centos7.2-Oracle',
                 u'template': u'Centos7.2-Oracle.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeVPC',
                 u'name': u'VpcBE',
                 u'template': u'VpcBE.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetBE-torino01',
                 u'params': {u'vpc': u'VpcBE', u'zone': u'SiteTorino01', u'cidr': u'10.138.128.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcBE'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetBE-torino02',
                 u'params': {u'vpc': u'VpcBE', u'zone': u'SiteTorino02', u'cidr': u'10.138.160.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcBE'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetBE-vercelli01',
                 u'params': {u'vpc': u'VpcBE', u'zone': u'SiteVercelli01', u'cidr': u'10.138.192.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcBE'}},
                {u'type': u'ComputeSecurityGroup',
                 u'name': u'SecurityGroupBE',
                 u'params': {u'vpc': u'VpcBE'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcBE'}},
                {u'type': u'ComputeVPC',
                 u'name': u'VpcWEB',
                 u'template': u'VpcWEB.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetWEB-torino01',
                 u'params': {u'vpc': u'VpcWEB', u'zone': u'SiteTorino01', u'cidr': u'10.138.136.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcWEB'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetWEB-torino02',
                 u'params': {u'vpc': u'VpcWEB', u'zone': u'SiteTorino02', u'cidr': u'10.138.168.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcWEB'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetWEB-vercelli01',
                 u'params': {u'vpc': u'VpcWEB', u'zone': u'SiteVercelli01', u'cidr': u'10.138.200.0/21'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcWEB'}},
                {u'type': u'ComputeSecurityGroup',
                 u'name': u'SecurityGroupWEB',
                 u'params': {u'vpc': u'VpcWEB'},
                 u'template': u'SecurityGroupWEB.sync',
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcWEB'}},
                {u'type': u'ComputeVPC',
                 u'name': u'VpcInternet',
                 u'template': u'VpcInternet.sync',
                 u'require': {u'type': u'ComputeService', u'name': u'ComputeService'}},
                {u'type': u'ComputeSubnet',
                 u'name': u'SubnetInternet-torino01',
                 u'params': {u'vpc': u'VpcInternet', u'zone': u'SiteTorino01', u'cidr': u'84.240.190.0/24'},
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcInternet'}},
                {u'type': u'ComputeSecurityGroup',
                 u'name': u'SecurityGroupInternet',
                 u'params': {u'vpc': u'VpcInternet'},
                 u'template': u'SecurityGroupWEB.sync',
                 u'require': {u'type': u'ComputeVPC', u'name': u'VpcInternet'}}
            ],
            u'test': [
                {"type": "ComputeService", "name": "ComputeService", "template": "compute.medium.sync"},
                {"type": "DatabaseService", "name": "DatabaseService", "template": "database.medium.sync",
                 "require": {"type": "ComputeService", "name": "ComputeService"}},
                {"type": "ComputeImage", "name": "Centos7.2", "template": "Centos7.2.sync",
                 "require": {"type": "ComputeService", "name": "ComputeService"}},
                {"type": "ComputeVPC", "name": "VpcBE", "template": "VpcBE.sync",
                 "require": {"type": "ComputeService", "name": "ComputeService"}},
                {"type": "ComputeSubnet", "name": "SubnetBE-torino01",
                 "params": {"vpc": "VpcBE", "zone": "SiteTorino01", "cidr": "10.102.185.0/24"},
                 "require": {"type": "ComputeVPC", "name": "VpcBE"}},
                {"type": "ComputeSecurityGroup", "name": "SecurityGroupBE", "params": {"vpc": "VpcBE"},
                 "require": {"type": "ComputeVPC", "name": "VpcBE"}}
            ]
        }
        default_methods = {
            u'image': ConnectionHelper.create_image,
            u'vpc': ConnectionHelper.create_vpc,
            u'sg': ConnectionHelper.create_sg,
            u'subnet': ConnectionHelper.create_subnet,
        }
    #
    # def __add_role(self, account_id):
    #     # get account
    #     uri = u'%s/accounts/%s' % (self.baseuri, account_id)
    #     account = self._call(uri, u'GET').get(u'account')
    #     account_objid = account[u'__meta__'][u'objid']
    #
    #     # add roles
    #     for role in self._meta.role_template:
    #         name = role.get(u'name') % account_id
    #         perms = ConnectionHelper.set_perms_objid(role.get(u'perms'), account_objid)
    #         ConnectionHelper.add_role(self, name, name, perms)

    @expose(aliases=[u'roles <account>'], aliases_only=True)
    @check_error
    def roles(self):
        """Get account roles
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s/roles' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'roles', headers=[u'name', u'desc'], maxsize=200)

    @expose(aliases=[u'users <account>'], aliases_only=True)
    @check_error
    def users(self):
        """Get account users
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'users', headers=[u'name', u'role'], maxsize=200)

    @expose(aliases=[u'users-add <account> <role> <user>'], aliases_only=True)
    @check_error
    def users_add(self):
        """Add account role to a user
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
        uri = u'%s/accounts/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'POST', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

    @expose(aliases=[u'users-del <account> <role> <user>'], aliases_only=True)
    @check_error
    def users_del(self):
        """Remove account role from a user
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
        uri = u'%s/accounts/%s/users' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)

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
        headers = [u'id', u'uuid', u'name', u'division', u'contact', u'core services', u'base services',
                   u'status', u'date']
        fields = [u'id', u'uuid', u'name', u'division_name', u'contact', u'services.core', u'services.base',
                  u'status', u'date.creation']
        self.result(res, key=u'accounts', headers=headers, fields=fields, maxsize=40)

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
  
    @expose(aliases=[u'tasks <id>'], aliases_only=True)
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
    - template: use test, prod as key or a json file with @ in head of the name
        """
        name = self.get_arg(name=u'name')
        division_id = self.get_arg(name=u'division_id')
        template = self.get_arg(name=u'template', keyvalue=True, default=u'')
        params = self.get_query_params(*self.app.pargs.extra_arguments)

        services = []
        if template.find(u'@') == 0:
            services = self.load_config(template[1:len(template)])
        else:
            services = self._meta.default_services.get(template, [])

        data = {
            u'account': {
                u'name': name,
                u'desc': params.get(u'desc', None),
                u'division_id': division_id,
                u'contact': params.get(u'contact', None),
                u'email': params.get(u'email', None),
                u'note': params.get(u'note', None),
                u'email_support': params.get(u'email_support', None),
                u'email_support_link': params.get(u'email_support_link', None),
                u'services': services
            }  
         }        
        uri = u'%s/accounts' % self.baseuri
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add account: %s' % truncate(res))
        res = {u'msg': u'Add account %s' % res[u'uuid']}
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

    @expose(aliases=[u'refresh <id> [field=value]'], aliases_only=True)
    @check_error
    def refresh(self):
        """Refresh account
    - id: id or uuid of the account
    - template: use test, prod as key or a json file with @ in head of the name
        """
        oid = self.get_arg(name=u'id')
        template = self.get_arg(name=u'template', keyvalue=True, default=u'')

        if template.find(u'@') == 0:
            services = self.load_config(template[1:len(template)])
        else:
            services = self._meta.default_services.get(template, [])

        data = {
            u'account': {
                u'services': services
            }
        }
        uri = u'%s/accounts/%s' % (self.baseuri, oid)
        self._call(uri, u'PATCH', data=data, timeout=600)
        logger.info(u'Refresh account %s' % (oid))
        res = {u'msg': u'Refresh account %s' % (oid)}
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

    # def __add_core_service(self, account_id, plugintype):
    #     """Add container core service instance
    #
    #     :param account_id: account id
    #     :param plugintype: can be ComputeService, DatabaseService
    #     """
    #     uri_internal = {
    #         u'ComputeService': u'computeservices',
    #         u'DatabaseService': u'databaseservices',
    #     }
    #
    #     # check service already exists
    #     data = urllib.urlencode({u'plugintype': plugintype, u'account_id': account_id, u'flag_container': True})
    #     uri = u'%s/serviceinsts' % self.baseuri
    #     service_inst = self._call(uri, u'GET', data=data).get(u'serviceinsts', [])
    #
    #     if len(service_inst) > 0:
    #         logger.info(u'Service instance container %s already exists' % plugintype)
    #         res = {u'msg': u'Service instance container %s already exists' % plugintype}
    #         self.result(res, headers=[u'msg'])
    #         return
    #
    #     # get service def
    #     data = urllib.urlencode({u'plugintype': plugintype})
    #     uri = u'%s/servicedefs' % self.baseuri
    #     service_def = self._call(uri, u'GET', data=data).get(u'servicedefs', [])
    #     if len(service_def) < 1:
    #         raise Exception(u'You can not create %s' % plugintype)
    #     else:
    #         service_def = service_def[0]
    #
    #     service_definition_id = service_def.get(u'uuid')
    #     name = u'%s-%s' % (plugintype, account_id)
    #
    #     # create instance
    #     data = {
    #         u'serviceinst': {
    #             u'name': name,
    #             u'desc': u'Account %s %s' % (account_id, plugintype),
    #             u'account_id': account_id,
    #             u'service_def_id': service_definition_id,
    #             u'params_resource': u'',
    #             u'version': u'1.0'
    #         }
    #     }
    #     uri = u'%s/%s' % (self.baseuri, uri_internal.get(plugintype))
    #     res = self._call(uri, u'POST', data=data, timeout=600)
    #     logger.info(u'Add service instance container: %s' % plugintype)
    #     res = {u'msg': u'Add service instance %s' % res}
    #     self.result(res, headers=[u'msg'])
    #
    # def __add_default_services(self, account_id):
    #     """Add default compute service child instances
    #
    #     :param account_id: account id
    #     """
    #     for item in self._meta.default_data:
    #         item[u'account'] = account_id
    #         type = item.pop(u'type')
    #         if not ConnectionHelper.service_instance_exist(self, type, u'%s-%s' % (item[u'name'], account_id)):
    #             func = self._meta.default_methods.get(type)
    #             func(self, **item)
    #
    # @expose(aliases=[u'add-core-service <account_id> <type>'], aliases_only=True)
    # @check_error
    # def add_core_service(self):
    #     """Add container core service instance
    # - type : can be ComputeService, DatabaseService
    #     """
    #     account_id = self.get_arg(name=u'account_id')
    #     plugintype = self.get_arg(name=u'type')
    #     self.__add_core_service(account_id, plugintype)
    #
    # @expose(aliases=[u'add-default-services <account_id>'], aliases_only=True)
    # @check_error
    # def add_default_services(self):
    #     """Add default compute service child instances
    #     """
    #     account_id = self.get_arg(name=u'account_id')
    #     self.__add_default_services(account_id)

    @expose(aliases=[u'services-delete <service_id>'], aliases_only=True)
    @check_error
    def services_delete(self):
        """Delete service instance
        """
        value = self.get_arg(name=u'service_id')
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data={u'recursive': True}, timeout=600)
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
        self.app.kvargs[u'account_id'] = self.get_arg(name=u'account')
        all = self.get_arg(name=u'all', keyvalue=True, default=False)
        if all is False:
            self.app.kvargs[u'flag_container'] = True
        data = urllib.urlencode(self.app.kvargs)
        ConnectionHelper.get_service_instances(self, data)


class AccountTemplateController(AuthorityControllerChild):
    class Meta:
        label = u'templates'
        # aliases = ['account-templates']
        # aliases_only = True

        description = "Account Templates management"

    @expose()
    @check_error
    def list(self):
        """List all accounts templates
        """
        # data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/accounttemplates' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(res)
        headers = [u"id", u"uuid", u"name", u"desc", u"is_default", u"default_service_types", u"services"]
        fields = [u"id", u"uuid", u"name", u"desc", u"is_default", u"default_service_types", u"services"]
        self.result(res, key=u'accounts_templates', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'add <name>'], aliases_only=True)
    @check_error
    def add(self):
        """Add account template <name>
        if name has is like @<name> then  name shal be a configuration file
        in json or yaml format.
        - field: can be desc, is_default, default_service_types, services
        """
        name = self.get_arg(name=u'name')

        if name.find(u'@') == 0:
            params = self.load_config(name[1:len(name)])
            name = params.get(u'name', 'anonimo')
        else:
            params = self.get_query_params(*self.app.pargs.extra_arguments)

        data = {
            u'account_template': {
                u'name': name,
                u'desc': params.get(u'desc', None),
                u'is_default': params.get(u'is_default', False),
                u'version': params.get(u'version', '1.0'),
                u'default_service_types': params.get(u'default_service_types', []),
                u'services': params.get(u'services', None),
            }
        }

        uri = u'%s/accounttemplates' % self.baseuri
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add account templatew: %s' % truncate(res))
        res = {u'msg': u'Add account template %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete account template
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounttemplates/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete account tempate %s' % value}
        self.result(res, headers=[u'msg'])



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
    AccountTemplateController,
    SubwalletController,
    WalletController,
    AgreementController,
    ConsumeController,
]
