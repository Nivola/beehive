"""
Created on Dec 11, 2017

@author: darkbk
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)


class ProviderController(BaseController):
    class Meta:
        label = 'provider'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Provider management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
        
class ProviderControllerChild(ApiController):
    subsystem = u'resource'
    
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'provider'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*'))
        ]

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, key=self._meta.aliases[0])
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET')
        key = self._meta.aliases[0].rstrip(u's')
        logger.info(u'Get %s: %s' % (key, truncate(res)))
        self.result(res, details=True, key=key)
    
    @expose(aliases=[u'add <file data>'], aliases_only=True)
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res)
    
    @expose(aliases=[u'update <id> <file data>'], aliases_only=True)
    def update(self):
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'UPDATE', data=data)
        logger.info(u'Update %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res)
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete %s: %s' % (self._meta.aliases[0], oid))
        self.result(res)


class ProviderRegionController(ProviderControllerChild):
    uri = u'/v1.0/provider/regions'

    class Meta:
        label = 'provider.beehive.regions'
        aliases = ['regions']
        aliases_only = True
        description = "Provider region management"


class ProviderSiteController(ProviderControllerChild):
    uri = u'/v1.0/provider/sites'

    class Meta:
        label = 'provider.beehive.sites'
        aliases = ['sites']
        aliases_only = True
        description = "Provider site management"


class ProviderSiteNetworkController(ProviderControllerChild):
    uri = u'/v1.0/provider/site_networks'

    class Meta:
        label = 'provider.beehive.site_networks'
        aliases = ['site_networks']
        aliases_only = True
        description = "Provider site network management"


class ProviderComputeZoneController(ProviderControllerChild):
    uri = u'/v1.0/provider/compute_zones'

    class Meta:
        label = 'provider.beehive.compute_zones'
        aliases = ['compute_zones']
        aliases_only = True
        description = "Provider compute zone management"


class ProviderComputeFlavorController(ProviderControllerChild):
    uri = u'/v1.0/provider/flavors'

    class Meta:
        label = 'provider.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True
        description = "Provider compute flavor management"


class ProviderComputeImageController(ProviderControllerChild):
    uri = u'/v1.0/provider/images'

    class Meta:
        label = 'provider.beehive.images'
        aliases = ['images']
        aliases_only = True
        description = "Provider compute image management"


class ProviderComputeVpcController(ProviderControllerChild):
    uri = u'/v1.0/provider/vpcs'

    class Meta:
        label = 'provider.beehive.vpcs'
        aliases = ['vpcs']
        aliases_only = True
        description = "Provider compute vpc management"


class ProviderComputeSecurityGroupController(ProviderControllerChild):
    uri = u'/v1.0/provider/security_groups'

    class Meta:
        label = 'provider.beehive.security_groups'
        aliases = ['security_groups']
        aliases_only = True
        description = "Provider compute security group management"


class ProviderComputeComputeRuleController(ProviderControllerChild):
    uri = u'/v1.0/provider/rules'

    class Meta:
        label = 'provider.beehive.rules'
        aliases = ['rules']
        aliases_only = True
        description = "Provider compute rule management"


class ProviderComputeComputeInstanceController(ProviderControllerChild):
    uri = u'/v1.0/provider/instances'

    class Meta:
        label = 'provider.beehive.instances'
        aliases = ['instances']
        aliases_only = True
        description = "Provider compute instance management"


provider_controller_handlers = [
    ProviderController,
    ProviderRegionController,
    ProviderSiteController,
    ProviderSiteNetworkController,
    ProviderComputeZoneController,
    ProviderComputeFlavorController,
    ProviderComputeImageController,
    ProviderComputeVpcController,
    ProviderComputeSecurityGroupController,
    ProviderComputeComputeRuleController,
    ProviderComputeComputeInstanceController,
]        