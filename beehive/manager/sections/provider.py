"""
Created on Dec 11, 2017

@author: darkbk
"""
import json
import logging
import urllib
from base64 import b64encode

import sh
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from beecell.simple import truncate, getkey, flatten_dict
from beehive.manager.sections.resource import ResourceEntityController
from beecell.paramiko_shell.shell import ParamikoShell

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
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation', u'modified']
    fields = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'provider'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def get_container(self):
        """Get container provider"""
        data = urllib.urlencode({u'container_type': u'Provider'})
        uri = u'%s/containers' % self.baseuri
        res = self._call(uri, u'GET', data=data)[u'resourcecontainers'][0][u'id']
        logger.info(u'Get resource container: %s' % truncate(res))
        return str(res)

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.alias, res))
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.alias)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)
    
    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'update <id> <file data>'], aliases_only=True)
    @check_error
    def update(self):
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'UPDATE', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Update %s: %s' % (self._meta.alias, truncate(res)))
        res = {u'msg': u'Upd %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'DELETE')
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Delete %s: %s' % (self._meta.alias, oid))
        res = {u'msg': u'Del %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderRegionController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/regions'

    class Meta:
        label = 'provider.beehive.regions'
        aliases = ['regions']
        alias = u'regions'
        aliases_only = True
        description = "Provider region management"


class ProviderSiteController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/sites'

    class Meta:
        label = 'provider.beehive.sites'
        aliases = ['sites']
        alias = u'sites'
        aliases_only = True
        description = "Provider site management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            orchestrators = attributes.pop(u'orchestrators', [])
            limits = attributes.pop(u'limits', [])
            self.app.print_output(u'orchestrators:')
            self.result(orchestrators, headers=[u'id', u'type', u'tag', u'config'], maxsize=200)
            self.app.print_output(u'limits:')
            self.result(limits, details=True)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'add-orchestrator <id> <file data>'], aliases_only=True)
    @check_error
    def add_orchestrator(self):
        """Add orchestrator
    - file data: json file
        """
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri + u'/%s/orchestrators' % oid
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Add orchestrator to site %s: %s' % (oid, truncate(res)))
        res = {u'msg': u'Add orchestrator to site %s: %s' % (oid, truncate(res))}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'del-orchestrator <id> <orchestrator>'], aliases_only=True)
    @check_error
    def del_orchestrator(self):
        """Delete orchestrator
    - orchestrator: orchestrator id
        """
        oid = self.get_arg(name=u'id')
        orchestrator = self.get_arg(name=u'orchestrator')
        data = {u'orchestrator': {u'id': orchestrator}}
        uri = self.uri + u'/%s/orchestrators' % oid
        res = self._call(uri, u'DELETE', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Delete orchestrator from site %s: %s' % (oid, truncate(res)))
        res = {u'msg': u'Delete orchestrator from site %s: %s' % (oid, truncate(res))}
        self.result(res, headers=[u'msg'])


class ProviderSiteNetworkController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/site_networks'

    class Meta:
        label = 'provider.beehive.site_networks'
        aliases = ['site-networks']
        alias = u'site_networks'
        aliases_only = True
        description = "Provider site network management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            configs = attributes.get(u'configs', [])
            subnets = configs.pop(u'subnets', [])
            # self.result(data, details=True)
            self.app.print_output(u'subnets:')
            self.result(subnets, headers=[u'cidr', u'gateway', u'router', u'allocable', u'enable_dhcp',
                                          u'dns_nameservers', u'allocation_pools'], maxsize=200)

        self.get_resource(oid, format_result=format_result)


class ProviderComputeZoneController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/compute_zones'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'availability_zones', u'creation', u'modified']
    fields = [u'id', u'uuid', u'name', u'parent.name', u'state', u'availability_zones', u'date.creation',
              u'date.modified']

    class Meta:
        label = 'provider.beehive.compute_zones'
        aliases = ['compute-zones']
        alias = u'compute_zones'
        aliases_only = True
        description = "Provider compute zone management"

    @expose(aliases=[u'add-site <id> <file data>'], aliases_only=True)
    @check_error
    def add_site(self):
        """Add site
    - file data: json file
        """
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri + u'/%s/sites' % oid
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Add site to compute zone %s: %s' % (oid, truncate(res)))
        res = {u'msg': u'Add site to compute zone %s: %s' % (oid, truncate(res))}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete-site <id> <site_id>'], aliases_only=True)
    @check_error
    def delete_site(self):
        """Delete site
        """
        oid = self.get_arg(name=u'id')
        site_id = self.get_arg(name=u'site id')
        data = {u'site': {u'id': site_id}}
        uri = self.uri + u'/%s/sites' % oid
        res = self._call(uri, u'DELETE', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid)
        logger.info(u'Remove site %s from compute zone %s' % (site_id, oid))
        res = {u'msg': u'Remove site %s from compute zone %s' % (site_id, oid)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider computes zone
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            quotas = attributes.pop(u'quota', [])
            availability_zones = data.pop(u'availability_zones', [])
            for i in availability_zones:
                i[u'type'] = u'availability_zones'
            headers = [u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created', u'modified', u'expiry']
            fields = [u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                      u'date.expiry']
            self.result(availability_zones, headers=headers, fields=fields, maxsize=200)
            self.app.print_output(u'quotas:')
            self.result(quotas, details=True)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'quotas <id>'], aliases_only=True)
    @check_error
    def quotas(self):
        """Get provider computes zone quotas
        """
        oid = self.get_arg(name=u'id')

        uri = u'%s/%s/quotas' % (self.uri, oid)
        res = self._call(uri, u'GET').get(u'quotas', [])
        logger.info(u'Get compute zone %s quotas: %s' % (oid, truncate(res)))
        self.result(res, headers=[u'quota', u'value', u'allocated', u'unit'])

    @expose(aliases=[u'quotas-default <id>'], aliases_only=True)
    @check_error
    def quotas_default(self):
        """Get provider computes zone quotas classes
        """
        oid = self.get_arg(name=u'id')

        uri = u'%s/%s/quotas/classes' % (self.uri, oid)
        res = self._call(uri, u'GET').get(u'quota_classes', [])
        logger.info(u'Get compute zone %s quotas classes: %s' % (oid, truncate(res)))
        self.result(res, headers=[u'quota', u'default', u'unit'])

    @expose(aliases=[u'quotas-check <id> <quotas>'], aliases_only=True)
    @check_error
    def quotas_check(self):
        """Check provider computes zone quotas
        """
        oid = self.get_arg(name=u'id')
        quotas = self.get_arg(name=u'quotas')

        uri = u'%s/%s/quotas/check' % (self.uri, oid)
        res = self._call(uri, u'PUT', {u'quotas': json.loads(quotas)}).get(u'quotas', [])
        logger.info(u'Quotas compute zone %s quotas classes: %s' % (oid, truncate(res)))
        self.result(res, headers=[u'quota', u'default', u'unit'])

    @expose(aliases=[u'metric <id>'], aliases_only=True)
    @check_error
    def metric(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        uri = self.uri + u'/' + oid + u'/metrics'
        res = self._call(uri, u'GET')
        
        self.result(res.get(u'compute_zone'), headers=[u'id', u'service_id',  u'date', u'key', u'value'],
                    fields=[u'id', u'service_uuid', u'extraction_date', u'metrics.key', u'metrics.value'])
        # TODO print di key e value delle metriche
        

class ProviderComputeFlavorController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/flavors'

    class Meta:
        label = 'provider.beehive.flavors'
        aliases = ['flavors']
        alias = u'flavors'
        aliases_only = True
        description = "Provider compute flavor management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            configs = attributes.pop(u'configs', [])
            flavors = data.pop(u'flavors', [])
            self.app.print_output(u'configs:')
            self.result(configs, details=True)

        self.get_resource(oid, format_result=format_result)


class ProviderComputeImageController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/images'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation', u'modified']
    fields = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.images'
        aliases = ['images']
        alias = u'images'
        aliases_only = True
        description = "Provider compute image management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.alias, res))
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.alias)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            configs = attributes.pop(u'configs', [])
            images = data.pop(u'images', [])
            self.app.print_output(u'configs:')
            self.result(configs, details=True)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        """Add image. To get a list of guestid:  http://www.fatpacket.com/blog/2016/12/vm-guestos-identifiers/
        """
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderComputeVpcController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/vpcs'

    class Meta:
        label = 'provider.beehive.vpcs'
        aliases = ['vpcs']
        alias = u'vpcs'
        aliases_only = True
        description = "Provider compute vpc management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            networks = data.pop(u'networks', [])
            for i in networks:
                i[u'subnets'] = []
                for subnet in i[u'attributes'][u'configs'][u'subnets']:
                    i[u'subnets'].append(subnet[u'cidr'])
            self.result(networks, headers=[u'id', u'name', u'reuse', u'state', u'subnets'],
                        fields=[u'id', u'name', u'reuse', u'state', u'subnets'], maxsize=200)

        self.get_resource(oid, format_result=format_result)


class ProviderComputeSecurityGroupController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/security_groups'

    class Meta:
        label = 'provider.beehive.security_groups'
        aliases = ['security-groups']
        alias = u'security_groups'
        aliases_only = True
        description = "Provider compute security group management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')
        res = self.get_resource(oid)
        self.result(res, details=True)

    @expose(aliases=[u'add <name> <vpc>'], aliases_only=True)
    @check_error
    def add(self):
        """Add security group
        """
        name = self.get_arg(name=u'name')
        data = {
            u'security_group': {
                u'container': self.get_container(),
                u'name': name,
                u'desc': name,
                u'vpc': self.get_arg(name=u'vpc')
            }
        }
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        self.wait_job(res[u'jobid'])
        res = {u'msg': u'Add %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderComputeRuleController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/rules'

    class Meta:
        label = 'provider.beehive.rules'
        aliases = ['rules']
        alias = u'rules'
        aliases_only = True
        description = "Provider compute rule management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
    - field: service, source, dest
    - service: can be <proto> or <proto>:<port>
    - proto: ca be  6 [tcp], 17 [udp], 1,<subproto> [icmp], * [all]. If use icmp specify also subprotocol (ex. 8
      for echo request). [default=*]
    - port: can be an integer between 0 and 65535 or a range with start and end in the same interval. Range format
      is <start>-<end>. Use * for all ports. [default=*]
    - source: rule source. Syntax <type>:<value>.
    - dest: rule destination. Syntax <type>:<value>.
    Source and destination type can be SecurityGroup, Cidr.
    Source and destination value can be security group id or uuid, cidr like 10.102.167.0/24.
        """
        data = {}
        source = self.get_arg(name=u'source', keyvalue=True, default=None)
        dest = self.get_arg(name=u'dest', keyvalue=True, default=None)
        service = self.get_arg(name=u'service', keyvalue=True, default=None)
        if source is not None:
            data[u'source'] = source
        if dest is not None:
            data[u'destination'] = dest
        if service is not None:
            data[u'service'] = service
        uri = self.uri
        res = self._call(uri, u'GET', data=urllib.urlencode(data))
        logger.info(u'Get %s: %s' % (self._meta.alias, res))
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.alias)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            configs = attributes.pop(u'configs', [])
            source = configs.pop(u'source', [])
            dest = configs.pop(u'destination', [])
            service = configs.pop(u'service', [])
            rules = data.pop(u'rules', [])
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
            self.app.print_output(u'Source / Destination:')
            self.result(fromto, headers=[u'fromto', u'type', u'value'], maxsize=200)
            self.app.print_output(u'service:')
            self.result(service, headers=[u'protocol', u'port'], maxsize=200)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'add <name> <compute_zone> <source> <dest> [proto=..] [port:..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add rule
    - proto: ca be  6 [tcp], 17 [udp], 1,<subprotocol> [icmp], * [all]. If use icmp specify also subprotocol (ex. 8
      for echo request). [default=*]
    - port: can be an integer between 0 and 65535 or a range with start and end in the same interval. Range format
      is <start>-<end>. Use * for all ports. [default=*]
    - source: rule source. Syntax <type>:<value>.
    - dest: rule destination. Syntax <type>:<value>.
    Source and destination type can be SecurityGroup, Cidr.
    Source and destination value can be security group id or uuid, cidr like 10.102.167.0/24.
        """
        name = self.get_arg(name=u'name')
        zone = self.get_arg(name=u'compute_zone')
        source = self.get_arg(name=u'source').split(u':')
        dest = self.get_arg(name=u'dest').split(u':')
        port = self.get_arg(name=u'port', default=u'*', keyvalue=True)
        proto = self.get_arg(name=u'proto', default=u'*', keyvalue=True)
        data = {
            u'rule': {
                u'container': self.get_container(),
                u'name': name,
                u'desc': name,
                u'compute_zone': zone,
                u'source': {
                    u'type': source[0],
                    u'value': source[1]
                },
                u'destination': {
                    u'type': dest[0],
                    u'value': dest[1]
                },
                u'service': {
                    u'port': port,
                    u'protocol': proto
                }
            }
        }
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        self.wait_job(res[u'jobid'])
        res = {u'msg': u'Add %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderComputeInstanceController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/instances'
    fields = [u'id', u'name', u'parent.name', u'availability_zone.name', u'hypervisor', u'state',
              u'date.creation', u'image_desc', u'vpcs.0.name', u'flavor.vcpus', u'flavor.memory', u'storage',
              u'vpcs.0.fixed_ip.ip']
    headers = [u'id', u'name', u'parent', u'av_zone', u'type', u'state', u'creation', u'image',
               u'vpc', u'vcpus', u'memory', u'disk', u'ip']

    class Meta:
        label = 'provider.beehive.instances'
        aliases = ['instances']
        alias = u'instances'
        aliases_only = True
        description = "Provider compute instance management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider instances
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        for item in res.get(u'instances'):
            image = item.get(u'image', {})
            item[u'image_desc'] = u'%s %s' % (image.get(u'os', u''), image.get(u'os_ver', u''))
            if len(item[u'storage']) > 0:
                item[u'storage'] = [i.get(u'volume_size', None) for i in item[u'storage']]
        logger.info(u'Get instances: %s' % truncate(res))
        self.result(res, headers=self.headers, fields=self.fields, key=u'instances')

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider instance
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            flavor = data.pop(u'flavor')
            image = data.pop(u'image')
            vpcs = data.pop(u'vpcs')
            sgs = data.pop(u'security_groups')
            storage = data.pop(u'storage')
            self.output(u'Flavor:')
            self.result(flavor, headers=[u'vcpus', u'memory', u'disk', u'disk_iops', u'bandwidth'])
            self.output(u'Image:')
            self.result(image, headers=[u'os', u'os_ver'])
            self.output(u'Security groups:')
            self.result(sgs, headers=[u'uuid', u'name'])
            self.output(u'Networks:')
            self.result(vpcs, headers=[u'uuid', u'name', u'cidr', u'gateway', u'fixed_ip.ip'])
            self.output(u'Storage:')
            self.result(storage, headers=[u'id', u'name', u'storage', u'format', u'bootable', u'mode', u'type', u'size'])

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        if u'pubkey' in data.get(u'instance'):
            data[u'instance'][u'user_data'] = b64encode(json.dumps({u'pubkey': data.get(u'instance').get(u'pubkey')}))
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        self.wait_job(res[u'jobid'])
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        self.result(res)

    @expose(aliases=[u'ssh <id> <user> [sshkey=..]'], aliases_only=True)
    @check_error
    def ssh(self):
        """Opens ssh connection over provider instance
        """
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        sshkey = self.get_arg(name=u'sshkey', default=None, keyvalue=True)
        uri = self.uri + u'/' + oid
        server = self._call(uri, u'GET').get(u'instance')
        fixed_ip = getkey(server, u'vpcs.0.fixed_ip.ip')

        client = ParamikoShell(fixed_ip, user, keyfile=sshkey)
        client.run()


class ProviderComputeStackController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/stacks'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation']
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.stacks'
        aliases = ['stacks']
        alias = u'stacks'
        aliases_only = True
        description = "Provider compute stack management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.alias, res))
        self.result(res, headers=self.headers, key=self._meta.alias)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            stacks = data.pop(u'stacks', [])
            resp = []
            for stack in stacks:
                self.app.print_output(u'Availability zone: %s' % stack.get(u'availability_zone'))
                availability_zone = stack.get(u'availability_zone')
                '''for output in stack.get(u'outputs'):
                    resp.append({u'availability_zone': availability_zone,
                                 u'key': output.get(u'output_key'),
                                 u'value': output.get(u'output_value'),
                                 u'desc': output.get(u'description'),
                                 u'error': output.get(u'output_error', None)})'''
                self.result(stack.get(u'outputs'), headers=[u'output_key', u'output_value', u'description',
                                                            u'output_error'],
                            table_style=u'simple', maxsize=40)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'resources <id>'], aliases_only=True)
    @check_error
    def resources(self):
        """Get provider stack resources
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/resources'
        res = self._call(uri, u'GET', data=u'').get(u'stack_resources')
        resp = []
        for item in res:
            self.app.print_output(u'Availability zone: %s' % item.get(u'availability_zone'))
            self.app.print_output(u'------------------------------------------')
            self.app.print_output(u'Resources')
            self.result(item.get(u'resources', []), headers=[u'availability_zone', u'id', u'uuid', u'name', u'type'],
                        fields=[u'id', u'uuid', u'name', u'__meta__.definition'], maxsize=200, table_style=u'simple')
            self.app.print_output(u'Internal Resources')
            self.result(item.get(u'internal_resources', []),
                        headers=[u'id', u'logical_id', u'name', u'type', u'creation', u'status', u'reason',
                                 u'required'],
                        fields=[u'physical_resource_id', u'logical_resource_id', u'resource_name', u'resource_type',
                                u'creation_time', u'resource_status', u'resource_status_reason',
                                u'required_by'], maxsize=40, table_style=u'simple')

    @expose(aliases=[u'outputs <id>'], aliases_only=True)
    @check_error
    def outputs(self):
        """Get provider stack outputs
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/outputs'
        res = self._call(uri, u'GET', data=u'').get(u'stack_outputs')
        for item in res:
            print(u'Availability zone: %s' % item.get(u'availability_zone'))
            for out in item.get(u'outputs'):
                print(u'----------------------------------------------------------')
                print(u'output_key: %s' % out.get(u'output_key', None))
                print(u'description: %s' % out.get(u'description', None))
                print(u'output_value: %s' % out.get(u'output_value', None))
                print(u'output_error: %s' % out.get(u'output_error', None))
                print(u'----------------------------------------------------------')


class ProviderComputeSqlStackController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/sql_stacks'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation']
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.sql_stacks'
        aliases = ['sql-stacks']
        alias = u'sql-stacks'
        aliases_only = True
        description = "Provider compute sql stack management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (u'stacks', res))
        self.result(res, headers=self.headers, key=u'sql_stacks')


class ProviderComputeAppEngineController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/app_engines'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'vpc', u'security_group', u'creation']
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'vpc.name', u'security_group.name',
               u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.app_engines'
        aliases = ['app-engines']
        alias = u'app-engines'
        aliases_only = True
        description = "Provider compute app engine management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (u'stacks', res))
        self.result(res, headers=self.headers, key=u'app_engines')

    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        jobid = res.get(u'jobid', None)
        if jobid is not None:
            self.wait_job(jobid, maxtime=600)
        logger.info(u'Add %s: %s' % (self._meta.alias, truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.alias, res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderComputeFileShareController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/shares'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation']
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.shares'
        aliases = ['shares']
        aliases_only = True
        description = "Provider compute file share management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.aliases[0])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            configs = attributes.pop(u'configs', [])
            shares = data.pop(u'shares', [])
            self.app.print_output(u'configs:')
            self.result(configs, details=True)

        self.get_resource(oid, format_result=format_result)

    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        """Add file share storage
        """
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.aliases[0], res[u'uuid'])}
        self.result(res, headers=[u'msg'])


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
    ProviderComputeRuleController,
    ProviderComputeInstanceController,
    ProviderComputeStackController,
    ProviderComputeSqlStackController,
    ProviderComputeAppEngineController,
    ProviderComputeFileShareController,
]        