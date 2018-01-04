"""
Created on Dec 11, 2017

@author: darkbk
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate
from beehive.manager.sections.resource import ResourceEntityController

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
        
        
# class ProviderControllerChild(ApiController):
class ProviderControllerChild(ResourceEntityController):
    subsystem = u'resource'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'provider'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def __get_key(self):
        return self._meta.aliases[0].rstrip(u's')

    def get_resource(self, oid):
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
        for i in [u'__meta__', u'ext_id', u'active']:
            res.pop(i, None)
        main_info = []
        c = res.pop(u'container')
        '''date = c.pop(u'date')
        c.update({u'type': u'container',
                  u'created': date.pop(u'creation'),
                  u'modified': date.pop(u'modified'),
                  u'expiry': date.pop(u'expiry')})'''
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
        self.result(main_info, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created', u'modified',
                                        u'expiry'])
        return res

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
        res = self.get_resource(oid)
        self.result(res, details=True)
    
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

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        attributes = res.get(u'attributes', [])
        orchestrators = attributes.pop(u'orchestrators', [])
        limits = attributes.pop(u'limits', [])
        self.result(res, details=True)
        self.app.print_output(u'orchestrators:')
        self.result(orchestrators, headers=[u'id', u'type', u'tag', u'config'], maxsize=200)
        self.app.print_output(u'limits:')
        self.result(limits, details=True)


class ProviderSiteNetworkController(ProviderControllerChild):
    uri = u'/v1.0/provider/site_networks'

    class Meta:
        label = 'provider.beehive.site_networks'
        aliases = ['site_networks']
        aliases_only = True
        description = "Provider site network management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        attributes = res.get(u'attributes', [])
        configs = attributes.get(u'configs', [])
        subnets = configs.pop(u'subnets', [])
        self.result(res, details=True)
        self.app.print_output(u'subnets:')
        self.result(subnets, headers=[u'cidr', u'gateway', u'enable_dhcp', u'dns_nameservers', u'allocation_pools'],
                    maxsize=200)


class ProviderComputeZoneController(ProviderControllerChild):
    uri = u'/v1.0/provider/compute_zones'

    class Meta:
        label = 'provider.beehive.compute_zones'
        aliases = ['compute_zones']
        aliases_only = True
        description = "Provider compute zone management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        attributes = res.get(u'attributes', [])
        quotas = attributes.pop(u'quota', [])
        availability_zones = res.pop(u'availability_zones', [])
        self.result(res, details=True)
        for i in availability_zones:
            i[u'type'] = u'availability_zones'
        self.result(availability_zones, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                                 u'modified', u'expiry'],
                    fields=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                            u'date.expiry'], maxsize=200)
        self.app.print_output(u'quotas:')
        self.result(quotas, details=True)


class ProviderComputeFlavorController(ProviderControllerChild):
    uri = u'/v1.0/provider/flavors'

    class Meta:
        label = 'provider.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True
        description = "Provider compute flavor management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)


class ProviderComputeImageController(ProviderControllerChild):
    uri = u'/v1.0/provider/images'

    class Meta:
        label = 'provider.beehive.images'
        aliases = ['images']
        aliases_only = True
        description = "Provider compute image management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)


class ProviderComputeVpcController(ProviderControllerChild):
    uri = u'/v1.0/provider/vpcs'

    class Meta:
        label = 'provider.beehive.vpcs'
        aliases = ['vpcs']
        aliases_only = True
        description = "Provider compute vpc management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)
        '''attributes = res.get(u'attributes', [])
        quotas = attributes.pop(u'quota', [])
        availability_zones = res.pop(u'availability_zones', [])
        self.result(res, details=True)
        for i in availability_zones:
            i[u'type'] = u'availability_zones'
        self.result(availability_zones, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                                 u'modified', u'expiry'],
                    fields=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                            u'date.expiry'], maxsize=200)
        self.app.print_output(u'quotas:')
        self.result(quotas, details=True)'''


class ProviderComputeSecurityGroupController(ProviderControllerChild):
    uri = u'/v1.0/provider/security_groups'

    class Meta:
        label = 'provider.beehive.security_groups'
        aliases = ['security_groups']
        aliases_only = True
        description = "Provider compute security group management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)


class ProviderComputeComputeRuleController(ProviderControllerChild):
    uri = u'/v1.0/provider/rules'

    class Meta:
        label = 'provider.beehive.rules'
        aliases = ['rules']
        aliases_only = True
        description = "Provider compute rule management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        attributes = res.get(u'attributes', [])
        configs = attributes.pop(u'configs', [])
        source = configs.pop(u'source', [])
        dest = configs.pop(u'destination', [])
        service = configs.pop(u'service', [])
        rules = res.pop(u'rules', [])
        self.result(res, details=True)
        fromto = []
        if not isinstance(source, list):
            source = [source]
        for i in source:
            i[u'fromto'] = u'source'
        fromto.extend(source)
        if not isinstance(dest, list):
            dest = [dest]
        for i in dest:
            i[u'fromto'] = u'destination'
        fromto.extend(dest)
        self.app.print_output(u'rules:')
        self.result(rules, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                    u'modified', u'expiry'],
                    fields=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                            u'date.expiry'], maxsize=200)
        self.app.print_output(u'Source / Destination:')
        self.result(fromto, headers=[u'fromto', u'type', u'value'], maxsize=200)
        self.app.print_output(u'service:')
        self.result(service, headers=[u'protocol', u'port'], maxsize=200)


class ProviderComputeComputeInstanceController(ProviderControllerChild):
    uri = u'/v1.0/provider/instances'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.instances'
        aliases = ['instances']
        aliases_only = True
        description = "Provider compute instance management"

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
        res = self.get_resource(oid)
        flavor = res.pop(u'flavor')
        image = res.pop(u'image')
        vpcs = res.pop(u'vpcs')
        sgs = res.pop(u'security_groups')
        self.result(res, details=True)
        self.output(u'Flavor:')
        self.result(flavor, headers=[u'vcpus', u'memory', u'disk', u'disk_iops', u'bandwidth'])
        self.output(u'Image:')
        self.result(image, headers=[u'os', u'os_ver'])
        self.output(u'Security groups:')
        self.result(sgs, headers=[u'uuid', u'name'])
        self.output(u'Networks:')
        self.result(vpcs, headers=[u'uuid', u'name', u'cidr', u'gateway', u'fixed_ip.ip'])


class ProviderComputeComputeStackController(ProviderControllerChild):
    uri = u'/v1.0/provider/stacks'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.stacks'
        aliases = ['stacks']
        aliases_only = True
        description = "Provider compute stack management"

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
        res = self.get_resource(oid)
        stacks = res.pop(u'stacks')
        self.result(res, details=True)
        stack_res = []
        for i in stacks:
            i[u'type'] = u'stack'
            stack_res.append(i)
            for s in i.pop(u'resources', []):
                s[u'type'] = u'stack_resource' # s[u'__meta__'][u'definition']
                stack_res.append(s)
        self.result(stack_res, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                        u'modified', u'expiry'],
                    fields=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                            u'date.expiry'], maxsize=35)
        '''stacks = res.pop(u'stacks')
        image = res.pop(u'image')
        vpcs = res.pop(u'vpcs')
        sgs = res.pop(u'security_groups')
        
        self.output(u'Flavor:')
        self.result(flavor, headers=[u'vcpus', u'memory', u'disk', u'disk_iops', u'bandwidth'])
        self.output(u'Image:')
        self.result(image, headers=[u'os', u'os_ver'])
        self.output(u'Security groups:')
        self.result(sgs, headers=[u'uuid', u'name'])
        self.output(u'Networks:')
        self.result(vpcs, headers=[u'uuid', u'name', u'cidr', u'gateway', u'fixed_ip.ip'])'''


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
    ProviderComputeComputeStackController,
]        