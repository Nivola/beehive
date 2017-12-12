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
        """List all organizations by field: id, uuid, name, org_type, ext_anag_id,
    attributes, hasvat, partner, referent, email, legalemail, postaladdress
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/organizations' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'organizations',
                    headers=[u'id', u'uuid', u'name', u'org_type', u'ext_anag_id'], maxsize=30)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get organization by value uuid or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s' % (self.baseuri, value)
        logger.info(uri)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'organization', details=True)


    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get organization permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/organizations/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get organization perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
 
    @expose(aliases=[u'add <name> <org_type> [desc=..] '\
                     u'[ext_anag_id=..] [attributes=..] [hasvat=..]'\
                     u'[partner=..] [referent=..] [email=..]'\
                     u'[legalemail=..] [postaladdress=..]'],
            aliases_only=True)
    def add(self):
        """Add organization <name> <org_type>
            - field: can be desc, ext_anag_id, attributes, hasvat, partner, referent, email, legaemail, postaladdress 
        """
        name = self.get_arg(name=u'name')
        org_type = self.get_arg(name=u'org_type')        
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'organization':{
#             u'name':name.split(u'=')[1],
            u'name':name,
            u'desc':params.get(u'desc', None),
#             u'org_type':org_type.split(u'=')[1],
            u'org_type':org_type,
            u'ext_anag_id':params.get(u'ext_anag_id',None),
            u'attributes':params.get(u'attributes',None),
#             u'attribute': params.get(u'attribute', {}),
            u'hasvat':params.get(u'hasvat',None),
            u'partner':params.get(u'partner',None),
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
    def update(self):
        """Update organization
    - id: id or uuid of the organization
    - field: can be name, desc, org_type, ext_anag_id, active, attributes, hasvat,partner (name surname), referent (name surname), email, legalemail, postaladdress
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'organization': params
        }
        uri = u'%s/organizations/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update organization %s with data %s' % (oid, params))
        res = {u'msg': u'Update resource %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete organization
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/organizations/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete organization %s' % value}
        self.result(res, headers=[u'msg'])


class DivisionController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'divisions'
        description = "Divisions management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'divisions',
                        headers=[u'id', u'uuid', u'name', 
                             u'organization_id', u'contact', u'email', 
                             u'postaladdress', u'active', u'date'], 
                        maxsize=30)

    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get division by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'division', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get division permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/divisions/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get division perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
 
    @expose(aliases=[u'add <name> <org_type> [desc=..] '\
                     u'[ext_anag_id=..] [attributes=..] [hasvat=..]'\
                     u'[partner=..] [referent=..] [email=..]'\
                     u'[legalemail=..] [postaladdress=..]'],
            aliases_only=True)
    def add(self):
        """Add division <name> <organization_id>
            - field: can be desc, contact, email, postaladdress 
        """
        name = self.get_arg(name=u'name')
        organization_id = self.get_arg(name=u'organization_id')        
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'division':{
#                 u'name':name.split(u'=')[1],
                u'name':name,
                u'desc':params.get(u'desc', None),
#                 u'organization_id':organization_id.split(u'=')[1],
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
    def update(self):
        """Update division
            - id: id or uuid of the division
            - field: can be name, desc, email, postaladdress, active
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'division': params
        }
        uri = u'%s/divisions/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update division %s with data %s' % (oid, params))
        res = {u'msg': u'Update division %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete division
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/divisions/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete division %s' % value}
        self.result(res, headers=[u'msg'])


class DivisionControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'business_hierarchy.divisions'
        stacked_type = 'nested'

class AccountController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'accounts'
        description = "Accounts management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'accounts',
                        headers=[u'id', u'uuid', u'name', 
                            u'division_id', u'contact', u'email',
                            u'email_support', u'email_support_link',
                            u'active', u'date'], 
                        maxsize=30)

    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get account by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'account', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get account permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/accounts/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get account perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <name> <division_id> [desc=..] '\
                     u'[note=..] [contact=..] [email=..]'\
                     u'[email_support=..] [email_support_link=..]'],
            aliases_only=True)
    def add(self):
        """Add account <name> <division_id>
            - field: can be desc, contact, email, postaladdress 
        """
        name = self.get_arg(name=u'name')
        division_id = self.get_arg(name=u'division_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        data = {
            u'account':{
#                 u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
#                 u'division_id':division_id.split(u'=')[1],
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
    def update(self):
        """Update account
            - id: id or uuid of the account
            - field: can be name, desc, email, contact, active, note, email_support, email_support_link
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'account': params
        }
        uri = u'%s/accounts/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update account %s with data %s' % (oid, params))
        res = {u'msg': u'Update account %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete account
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/accounts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete account %s' % value}
        self.result(res, headers=[u'msg'])

class SubwalletController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'subwallets'
        description = "Subwallets management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'subwallets',
                        headers=[u'id', u'uuid', u'name', 
                            u'wallet_id', u'account_id, 'u'amount', u'agreement_date',
                            u'active', u'date'], 
                        maxsize=30)

    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get subwallet by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/subwallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'subwallet', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get subwallet permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/subwallets/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get subwallet perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <wallet_id> <account_id> [name=..]'\
                    u'[desc=..] [active=..] [evaluation_date=..]'\
                    u'[capital_total=..] [capital_used=..]'\
                     ],
            aliases_only=True)
    
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
#                 u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
#                 u'wallet_id':wallet_id.split(u'=')[1],    
#                 u'account_id':account_id.split(u'=')[1], 
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
    def update(self):
        """Update subwallet
            - id: id or uuid of the subwallet
            - field: can be name, desc, active, capital_total, capital_used, evaluation_date 
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'subwallet': params
        }
        uri = u'%s/subwallets/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update subwallet %s with data %s' % (oid, params))
        res = {u'msg': u'Update subwallet %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete subwallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/subwallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete subwallet %s' % value}
        self.result(res, headers=[u'msg'])

class WalletController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'wallets'
        description = "Wallets management"
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'wallets',
                        headers=[u'id', u'uuid', u'name', 
                            u'division_id', u'capital_total', u'capital_used', u'evaluation_date'
                            u'active', u'date'], 
                        maxsize=30)

    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get wallet by value id or uuid
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/wallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'wallet', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get wallet permissions by value id or uuid
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/wallets/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get wallet perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <division_id> [desc=..]'\
                    u'[name=..] [active=..] [evaluation_date=..]'\
                    u'[capital_total=..] [capital_used=..]'\
                     ],
            aliases_only=True)
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
#                 u'division_id':division_id.split(u'=')[1],          
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
    def update(self):
        """Update wallet
            - id: id or uuid of the wallet
            - field: can be name, desc, active, capital_total, capital_used, evaluation_date 
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'wallet': params
        }
        uri = u'%s/wallets/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update wallet %s with data %s' % (oid, params))
        res = {u'msg': u'Update wallet %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete wallet
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/wallets/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete wallet %s' % value}
        self.result(res, headers=[u'msg'])


class AgreementController(OrganizationHierarchyControllerChild):
    class Meta:
        label = 'agreements'
        description = "Agreements management"
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
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
        self.result(res, key=u'agreements',
                        headers=[u'id', u'uuid', u'name', 
                            u'wallet_id', u'amount', u'agreement_date',
                            u'active', u'date'], 
                        maxsize=30)

    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get agreement by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/agreements/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'agreement', details=True)

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    def perms(self):
        """Get agreement permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/agreements/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get agreement perms: %s' % truncate(res))
        self.result(res, key=u'perms', headers=self.perm_headers)
  
    @expose(aliases=[u'add <name> <wallet_id> [desc=..] '\
                     u'[amount=..] [agreement_date=..]'],
            aliases_only=True)
    def add(self):
        """Add agreement <name> <wallet_id>
            - field: can be desc, amount, agreement_date 
        """
        name = self.get_arg(name=u'name')
        wallet_id = self.get_arg(name=u'wallet_id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        
        data = {
            u'agreement':{
#                 u'name': name.split(u'=')[1],
                u'name': name,
                u'desc':params.get(u'desc', None),
#                 u'wallet_id':wallet_id.split(u'=')[1], 
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
    def update(self):
        """Update agreement
            - id: id or uuid of the agreement
            - field: can be name, desc, amount, agreement_date, active 
        """
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'agreement': params
        }
        uri = u'%s/agreements/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update agreement %s with data %s' % (oid, params))
        res = {u'msg': u'Update agreement %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        """Delete agreement
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/agreements/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg': u'Delete agreement %s' % value}
        self.result(res, headers=[u'msg'])

        
organization_controller_handlers = [
    OrganizationHierarchyController,
    OrganizationController,
    DivisionController,
    AccountController,
    SubwalletController,
    WalletController,
    AgreementController, 
]        