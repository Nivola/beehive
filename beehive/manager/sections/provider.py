"""
Created on Dec 11, 2017

@author: darkbk
"""
import logging
import sh
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from beecell.simple import truncate, getkey
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
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.aliases[0], res[u'uuid'])}
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
        logger.info(u'Update %s: %s' % (self._meta.aliases[0], truncate(res)))
        res = {u'msg': u'Upd %s %s' % (self._meta.aliases[0], res[u'uuid'])}
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
        logger.info(u'Delete %s: %s' % (self._meta.aliases[0], oid))
        res = {u'msg': u'Del %s %s' % (self._meta.aliases[0], res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderRegionController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/regions'

    class Meta:
        label = 'provider.beehive.regions'
        aliases = ['regions']
        aliases_only = True
        description = "Provider region management"


class ProviderSiteController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/sites'

    class Meta:
        label = 'provider.beehive.sites'
        aliases = ['sites']
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


class ProviderSiteNetworkController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/site_networks'

    class Meta:
        label = 'provider.beehive.site_networks'
        aliases = ['site_networks']
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
            self.result(subnets, headers=[u'cidr', u'gateway', u'enable_dhcp', u'dns_nameservers', u'allocation_pools'],
                        maxsize=200)

        self.get_resource(oid, format_result=format_result)


class ProviderComputeZoneController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/compute_zones'

    class Meta:
        label = 'provider.beehive.compute_zones'
        aliases = ['compute_zones']
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
        """Get provider item
        """
        oid = self.get_arg(name=u'id')

        def format_result(data):
            attributes = data.get(u'attributes', [])
            quotas = attributes.pop(u'quota', [])
            availability_zones = data.pop(u'availability_zones', [])
            for i in availability_zones:
                i[u'type'] = u'availability_zones'
            self.result(availability_zones, headers=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'created',
                                                     u'modified', u'expiry'],
                        fields=[u'type', u'id', u'uuid', u'name', u'desc', u'state', u'date.creation', u'date.modified',
                                u'date.expiry'], maxsize=200)
            self.app.print_output(u'quotas:')
            self.result(quotas, details=True)

        self.get_resource(oid, format_result=format_result)


class ProviderComputeFlavorController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/flavors'

    class Meta:
        label = 'provider.beehive.flavors'
        aliases = ['flavors']
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
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        res = {u'msg': u'Add %s %s' % (self._meta.aliases[0], res[u'uuid'])}
        self.result(res, headers=[u'msg'])


class ProviderComputeVpcController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/vpcs'

    class Meta:
        label = 'provider.beehive.vpcs'
        aliases = ['vpcs']
        aliases_only = True
        description = "Provider compute vpc management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
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
    uri = u'/v1.0/nrs/provider/security_groups'

    class Meta:
        label = 'provider.beehive.security_groups'
        aliases = ['security_groups']
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


class ProviderComputeComputeRuleController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/rules'

    class Meta:
        label = 'provider.beehive.rules'
        aliases = ['rules']
        aliases_only = True
        description = "Provider compute rule management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
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
    uri = u'/v1.0/nrs/provider/instances'
    fields = [u'id', u'name', u'parent.name', u'availability_zone.name', u'attributes.type', u'state',
              u'date.creation', u'image_desc', u'vpcs.0.name', u'flavor.vcpus', u'flavor.memory', u'flavor.disk',
              u'vpcs.0.fixed_ip.ip']
    headers = [u'id', u'name', u'parent', u'av_zone', u'type', u'state', u'creation', u'image',
               u'vpc', u'vcpus', u'memory', u'disk', u'ip']

    class Meta:
        label = 'provider.beehive.instances'
        aliases = ['instances']
        aliases_only = True
        description = "Provider compute instance management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List provider instances
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data).get(self._meta.aliases[0], [])
        for item in res:
            image = item.get(u'image', {})
            item[u'image_desc'] = u'%s %s' % (image.get(u'os', u''), image.get(u'os_ver', u''))
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, fields=self.fields)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get provider instance
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


class ProviderComputeComputeStackController(ProviderControllerChild):
    uri = u'/v1.0/nrs/provider/stacks'
    headers = [u'id', u'uuid', u'name', u'parent', u'state', u'creation']
    headers = [u'id', u'uuid', u'name', u'parent.name', u'state', u'date.creation', u'date.modified']

    class Meta:
        label = 'provider.beehive.stacks'
        aliases = ['stacks']
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
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, key=self._meta.aliases[0])

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
        """Get provider item
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