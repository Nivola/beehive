'''
Created on Sep 27, 2017

@author: darkbk
'''
import requests
import sh
import logging
from cement.core.controller import expose
from gevent import sleep

from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate
from beedrones.openstack.client import OpenstackManager
from beehive.manager.sections.resource import ResourceEntityController
from paramiko.client import SSHClient, MissingHostKeyPolicy

logger = logging.getLogger(__name__)

#
# openstack native platform
#
class OpenstackPlatformController(BaseController):
    class Meta:
        label = 'openstack.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Openstack Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Openstack Platform management", hide=True)
    def default(self):
        self.app.args.print_help()


class OpenstackPlatformControllerChild(BaseController):
    headers = [u'id', u'name']
    entity_class = None
    
    class Meta:
        stacked_on = 'openstack.platform'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*')),            
            ( ['-O', '--orchestrator'],
              dict(action='store', help='Openstack platform reference label') ),
        ]
        
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)
        
        orchestrators = self.configs.get(u'orchestrators').get(u'openstack')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Openstack platform label must be specified. '\
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)
            
        self.client = OpenstackManager(conf.get(u'uri'), 
                                       default_region=conf.get(u'region'))
        self.client.authorize(conf.get(u'user'), conf.get(u'pwd'), 
                              project=conf.get(u'project'), 
                              domain=conf.get(u'domain'))

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=self.headers)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get(oid)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)
    
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg':u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformSystemController(OpenstackPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']
    
    class Meta:
        label = 'openstack.platform.system'
        aliases = ['system']
        aliases_only = True        
        description = "Openstack System management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
    @expose()
    def users(self):
        #params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.user.list(detail=True)
        logger.info(res)
        self.result(res, headers=self.headers)

    @expose()
    def compute_api(self):
        """Get compute api versions.
        """
        res = self.client.system.compute_api().get(u'versions', [])
        logger.debug('Get openstack compute services: %s' % (res))
        self.result(res, headers=[u'id', u'version', u'min_version',
                                  u'status', u'updated'])
    
    @expose()
    def compute_services(self):
        """Get compute service.
        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/os-services'
        res = self.compute.call(path, 'GET', data='', 
                                token=self.manager.identity.token)
        self.logger.debug('Get openstack compute services: %s' % truncate(res))
        return res[0]['services']
    
    @expose()
    def compute_zones(self):
        """Get compute availability zones.
        """
        res = self.client.system.compute_zones()
        resp = []
        for item in res:
            resp.append({u'state': item[u'zoneState'][u'available'],
                         u'hosts': u','.join(item[u'hosts'].keys()),
                         u'name': item[u'zoneName']})
        logger.debug('Get openstack availability zone: %s' % (res))
        self.result(resp, headers=[u'name', u'hosts', u'state'], maxsize=200)    
    
    @expose()
    def compute_hosts(self):
        """Get physical hosts.
        """
        res = self.client.system.compute_hosts()
        logger.debug('Get openstack hosts: %s' % (res))
        self.result(res, headers=[u'service', u'host_name', u'zone'], maxsize=200)
    
    @expose()
    def compute_host_aggregates(self):
        """Get compute host aggregates.
        """
        res = self.client.system.compute_host_aggregates()
        print res
        logger.debug('Get openstack hypervisors: %s' % (res))
        self.result(res, headers=[u'service', u'host_name', u'zone'], maxsize=200)
    
    @expose()
    def compute_server_groups(self):
        """Get compute server groups.
        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        res = self.client.system.compute_server_groups()
        print res
        logger.debug('Get openstack hypervisors: %s' % (res))
        self.result(res, headers=[u'service', u'host_name', u'zone'], maxsize=200)

    @expose()
    def compute_hypervisors(self):
        """Displays extra statistical information from the machine that hosts 
        the hypervisor through the API for the hypervisor (XenAPI or KVM/libvirt).
        """
        res = self.client.system.compute_hypervisors()
        logger.debug('Get openstack hypervisors: %s' % (res))
        self.result(res, headers=[u'id', u'hypervisor_hostname', u'host_ip', u'status', u'state', u'vcpus',
                                  u'vcpus_used', u'memory_mb', u'free_ram_mb',u'local_gb', u'local_gb_used',
                                  u'free_disk_gb', u'current_workload',u'running_vms'], maxsize=200)
    
    @expose()
    def compute_hypervisors_statistics(self):
        """Get compute hypervisors statistics.
        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/os-hypervisors/statistics'
        res = self.compute.call(path, 'GET', data='',token=self.manager.identity.token)
        self.logger.debug('Get openstack hypervisors statistics: %s' % truncate(res))
        return res[0]['hypervisor_statistics']
    
    @expose()
    def compute_agents(self):
        """Get compute agents.
        Use guest agents to access files on the disk, configure networking, and 
        run other applications and scripts in the guest while it runs. This 
        hypervisor-specific extension is not currently enabled for KVM. Use of 
        guest agents is possible only if the underlying service provider uses 
        the Xen driver.  
        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/os-agents'
        res = self.compute.call(path, 'GET', data='', token=self.manager.identity.token)
        self.logger.debug('Get openstack compute agents: %s' % truncate(res))
        return res[0]['agents']    
    
    @expose()
    def storage_services(self):
        """Get storage service.  
        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/os-services'
        res = self.blockstore.call(path, 'GET', data='', token=self.manager.identity.token)
        self.logger.debug('Get openstack storage services: %s' % truncate(res))
        return res[0]['services']
    
    @expose()
    def network_agents(self):
        """Get network agents.
        
        :return:
           [...,
            {u'admin_state_up': True,
              u'agent_type': u'Metadata agent',
              u'alive': True,
              u'binary': u'neutron-metadata-agent',
              u'configurations': {u'log_agent_heartbeats': False, u'metadata_proxy_socket': u'/var/lib/neutron/metadata_proxy', u'nova_metadata_ip': u'ctrl-liberty.nuvolacsi.it', u'nova_metadata_port': 8775},
              u'created_at': u'2015-12-22 14:33:59',
              u'description': None,
              u'heartbeat_timestamp': u'2016-05-08 16:21:55',
              u'host': u'ctrl-liberty2.nuvolacsi.it',
              u'id': u'e6c1e736-d25c-45e8-a475-126a13a07332',
              u'started_at': u'2016-04-29 21:31:22',
              u'topic': u'N/A'},
             {u'admin_state_up': True,
              u'agent_type': u'Linux bridge agent',
              u'alive': True,
              u'binary': u'neutron-linuxbridge-agent',
              u'configurations': {u'bridge_mappings': {},
                                  u'devices': 21,
                                  u'interface_mappings': {u'netall': u'enp10s0f1', u'public': u'enp10s0f1.62'},
                                  u'l2_population': True,
                                  u'tunnel_types': [u'vxlan'],
                                  u'tunneling_ip': u'192.168.205.69'},
              u'created_at': u'2015-12-22 14:33:59',
              u'description': None,
              u'heartbeat_timestamp': u'2016-05-08 16:21:55',
              u'host': u'ctrl-liberty2.nuvolacsi.it',
              u'id': u'eb1010c4-ad95-4d8c-b377-6fce6a78141e',
              u'started_at': u'2016-04-29 21:31:22',
              u'topic': u'N/A'}]
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/v2.0/agents'
        res = self.network.call(path, 'GET', data='', token=self.manager.identity.token)
        self.logger.debug('Get openstack network agents: %s' % truncate(res))
        return res[0]['agents']
    
    @expose()
    def network_service_providers(self):
        """Get network service providers.
        
        :return: [{u'default': True, 
                   u'name': u'haproxy', 
                   u'service_type': u'LOADBALANCER'}]
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path = '/v2.0/service-providers'
        res = self.network.call(path, 'GET', data='', token=self.manager.identity.token)
        self.logger.debug('Get openstack network service providers: %s' % 
                          truncate(res))
        return res[0]['service_providers']
    
    @expose()
    def orchestrator_services(self):
        """Get heat services.
        
        :return: Ex.
              [{u'binary': u'heat-engine',
                u'created_at': u'2016-04-29T20:52:52.000000',
                u'deleted_at': None,
                u'engine_id': u'c1942356-3cf2-4e45-af5e-75334d7e6263',
                u'host': u'ctrl-liberty2.nuvolacsi.it',
                u'hostname': u'ctrl-liberty2.nuvolacsi.it',
                u'id': u'07cf7fbc-22c3-4091-823c-12e297a0cc51',
                u'report_interval': 60,
                u'status': u'up',
                u'topic': u'engine',
                u'updated_at': u'2016-05-09T12:19:55.000000'},
               {u'binary': u'heat-engine',
                u'created_at': u'2016-04-29T20:52:52.000000',
                u'deleted_at': None,
                u'engine_id': u'd7316fa6-2e82-4fe0-94d2-09cbb5ad1bc6',
                u'host': u'ctrl-liberty2.nuvolacsi.it',
                u'hostname': u'ctrl-liberty2.nuvolacsi.it',
                u'id': u'0a40b1ef-91e8-4f63-8c0b-861dbbfdcf31',
                u'report_interval': 60,
                u'status': u'up',
                u'topic': u'engine',
                u'updated_at': u'2016-05-09T12:19:58.000000'},..,]        
        :raises OpenstackError: raise :class:`.OpenstackError`
        """
        path="/services"
        res = self.heat.call(path, 'GET', data='', token=self.manager.identity.token)
        self.logger.debug('Get openstack orchestrator services: %s' % \
                          truncate(res))
        return res[0]['services']


class OpenstackPlatformKeystoneController(OpenstackPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']
    
    class Meta:
        label = 'openstack.platform.keystone'
        aliases = ['keystone']
        aliases_only = True        
        description = "Openstack Keystone management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
    @expose()
    def users(self):
        #params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.user.list(detail=True)
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose()
    def roles(self):
        #params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.role.list(detail=False)
        logger.info(res)
        self.result(res, headers=[u'id', u'name'])
        
    @expose()
    def regions(self):
        #params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.get_regions()
        logger.info(res)
        self.result(res, headers=[u'id', u'parent_region_id', u'description'])         


class OpenstackPlatformProjectController(OpenstackPlatformControllerChild):
    headers = [u'id', u'parent_id', u'domain_id', u'name', u'enabled']
    
    class Meta:
        label = 'openstack.platform.projects'
        aliases = ['projects']
        aliases_only = True        
        description = "Openstack Project management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.project


class OpenstackPlatformNetworkController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'provider:segmentation_id', 
               u'router:external', u'shared', u'provider:network_type']
    
    class Meta:
        label = 'openstack.platform.networks'
        aliases = ['networks']
        aliases_only = True
        description = "Openstack Network management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network


class OpenstackPlatformSubnetController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'subnet_id', u'cidr', 
               u'enable_dhcp']
    
    class Meta:
        label = 'openstack.platform.subnets'
        aliases = ['subnets']
        aliases_only = True         
        description = "Openstack Subnet management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.subnet


class OpenstackPlatformPortController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'port_id', u'security_groups', 
               u'mac_address', u'status', u'device_owner']
    
    class Meta:
        label = 'openstack.platform.ports'
        aliases = ['ports']
        aliases_only = True         
        description = "Openstack Port management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.port        


class OpenstackPlatformFloatingIpController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'status', u'floating_ip_address',
               u'fixed_ip_address']
    
    class Meta:
        label = 'openstack.platform.floatingips'
        aliases = ['floatingips']
        aliases_only = True         
        description = "Openstack FloatingIp management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.ip


class OpenstackPlatformRouterController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'ha', u'status']
    
    class Meta:
        label = 'openstack.platform.routers'
        aliases = ['routers']
        aliases_only = True         
        description = "Openstack Router management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.router


class OpenstackPlatformSecurityGroupController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name']
    
    class Meta:
        label = 'openstack.platform.security_groups'
        aliases = ['security_groups']
        aliases_only = True         
        description = "Openstack SecurityGroup management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.security_group             


class OpenstackPlatformImageController(OpenstackPlatformControllerChild):
    class Meta:
        label = 'openstack.platform.images'
        aliases = ['images']
        aliases_only = True         
        description = "Openstack Image management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.image
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(detail=True, **params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'status', u'progress',
                                  u'created', u'minDisk', u'minRam',
                                  u'OS-EXT-IMG-SIZE:size'])        


class OpenstackPlatformFlavorController(OpenstackPlatformControllerChild):
    class Meta:
        label = 'openstack.platform.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Openstack Flavor management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.flavor
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(detail=True, **params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'ram', u'vcpus', u'swap',
            u'os-flavor-access:is_public', u'rxtx_factor', u'disk', 
            u'OS-FLV-EXT-DATA:ephemeral', u'OS-FLV-DISABLED:disabled'])


class OpenstackPlatformKeyPairController(OpenstackPlatformControllerChild):
    headers = [u'name', u'public_key', u'fingerprint']

    class Meta:
        label = 'openstack.platform.keypairs'
        aliases = ['keypairs']
        aliases_only = True
        description = "Openstack KeyPair management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.keypair


class OpenstackPlatformServerController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'status', u'flavor.id', u'OS-EXT-SRV-ATTR:host', u'created']
    
    class Meta:
        label = 'openstack.platform.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Openstack Server management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.server

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(detail=True, **params)
        res = []
        for obj in objs:
            res.append(obj)
        self.result(res, headers=self.headers, maxsize=40)


class OpenstackPlatformVolumeController(OpenstackPlatformControllerChild):
    headers = [u'id', u'name', u'os-vol-tenant-attr:tenant_id', u'size', 
               u'status', u'bootable']
    
    class Meta:
        label = 'openstack.platform.volumes'
        aliases = ['volumes']
        aliases_only = True         
        description = "Openstack Volume management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.volume
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(detail=True, **params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=self.headers)        


class OpenstackPlatformHeatStackController(OpenstackPlatformControllerChild):
    headers = [u'id', u'project', u'stack_name', u'stack_owner', u'stack_status', u'creation_time']
    
    class Meta:
        label = 'openstack.platform.stack'
        aliases = ['stacks']
        aliases_only = True         
        description = "Openstack Heat Stack management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.heat

    def wait_stack_create(self, name, oid):
        res = self.client.heat.stack.get(stack_name=name, oid=oid)
        status = res[u'stack_status']

        while status == u'CREATE_IN_PROGRESS':
            self.logger.debug(status)
            sleep(1)
            res = self.client.heat.stack.get(stack_name=name, oid=oid)
            status = res[u'stack_status']
            print status

    def wait_stack_delete(self, name, oid):
        res = self.client.heat.stack.get(stack_name=name, oid=oid)
        status = res[u'stack_status']

        while status == u'DELETE_IN_PROGRESS':
            logger.debug(status)
            sleep(1)
            res = self.client.heat.stack.get(stack_name=name, oid=oid)
            status = res[u'stack_status']
            print(u'.')

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    def list(self):
        """List heat stacks
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.stack.list(**params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=self.headers)

    '''
    @expose(aliases=[u'stack-find <name>'], aliases_only=True)
    def stack_find(self):
        """Find heat stack by name
        """        
        name = self.get_arg(name=u'name')
        obj = self.entity_class.stacks_find(stack_name=name)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)'''

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get heat stack by id
        """        
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.get(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        parameters = [{u'parameter': item, u'value': val} for item, val in res.pop(u'parameters').items()]
        outputs = res.pop(u'outputs')
        self.result(res, details=True, maxsize=800)
        self.app.print_output(u'parameters:')
        self.result(parameters, headers=[u'parameter', u'value'], maxsize=800)
        self.app.print_output(u'outputs:')
        self.result(outputs, headers=[u'key', u'value', u'desc'],
                    fields=[u'output_key', u'output_value', u'description'], maxsize=100)

    @expose(aliases=[u'template <id>'], aliases_only=True)
    def template(self):
        """Get heat stack template by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.template(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        self.result(res, details=True, maxsize=800)

    @expose()
    def template_versions(self):
        """Get available template versions
        """
        res = self.entity_class.template.versions().get(u'template_versions')
        logger.info(res)
        self.result(res, headers=[u'version', u'type', u'aliases'])

    @expose(aliases=[u'template-functions <template>'], aliases_only=True)
    def template_functions(self):
        """Get available template functions
        """
        template = self.get_arg(name=u'template')
        res = self.entity_class.template.functions(template).get(u'template_functions')
        logger.info(res)
        self.result(res, headers=[u'functions', u'description'], maxsize=200)

    @expose(aliases=[u'template-validate <template-uri>'], aliases_only=True)
    def template_validate(self):
        """Get available template functions
        """
        template_uri = self.get_arg(name=u'template-uri')
        rq = requests.get(template_uri, timeout=5, verify=False)
        if rq.status_code == 200:
            template = rq.content
            res = self.entity_class.template.validate(template=template, environment={})
            logger.info(res)
            self.result(res, format=u'yaml')
        else:
            self.app.print_error(u'No response from uri found')

    @expose(aliases=[u'environment <id>'], aliases_only=True)
    def environment(self):
        """Get heat stack environment by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.environment(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        self.result(res, details=True, maxsize=800)

    @expose(aliases=[u'files <id>'], aliases_only=True)
    def files(self):
        """Get heat stack files by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.files(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        self.result(res, details=True, maxsize=800)

    @expose(aliases=[u'outputs <id>'], aliases_only=True)
    def outputs(self):
        """Get heat stack outputs by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.outputs(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        self.result(res, details=True, maxsize=800)

    @expose(aliases=[u'output <id> <key>'], aliases_only=True)
    def output(self):
        """Get heat stack output by id and key
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        key = self.get_arg(name=u'key')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.outputs(stack_name=stack[u'stack_name'], oid=oid, output_key=key)
        logger.info(res)
        self.result(res, details=True, maxsize=800)

    @expose(aliases=[u'resources <id>'], aliases_only=True)
    def resources(self):
        """Get heat stack resources by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.resource.list(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'status', u'type', u'creation', u'required_by'],
                    fields=[u'physical_resource_id', u'resource_name', u'resource_status', u'resource_type',
                            u'creation_time', u'required_by'], maxsize=40)

    @expose()
    def resource_types(self):
        """Get heat stack resources types
        """
        res = self.entity_class.stack.resource.list_types().get(u'resource_types')
        logger.info(res)
        self.result(res, headers=[u'type'], maxsize=100)

    @expose(aliases=[u'resource-type <type>'], aliases_only=True)
    def resource_type(self):
        """Get heat stack resources types. Use with format json and yaml.
        """
        name = self.get_arg(name=u'type')
        res = self.entity_class.stack.resource.get_type(resource_type=name)
        logger.info(res)
        self.result(res, headers=[u'type'], maxsize=100)

    @expose(aliases=[u'resource-type-template <type>'], aliases_only=True)
    def resource_type_template(self):
        """Get heat stack resources types. Use with format json and yaml.
        """
        name = self.get_arg(name=u'type')
        res = self.entity_class.stack.resource.get_type_template(resource_type=name, template_type='hot')
        logger.info(res)
        self.result(res, headers=[u'type'], maxsize=100)

    @expose(aliases=[u'events <id>'], aliases_only=True)
    def events(self):
        """Get heat stack events by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.event.list(stack_name=stack[u'stack_name'], oid=oid)
        logger.info(res)
        print res
        self.result(res, headers=[u'id', u'name', u'resource_id', u'status', u'status_reason', u'event_time'],
                    fields=[u'id', u'resource_name', u'physical_resource_id', u'resource_status',
                            u'resource_status_reason', u'event_time'], maxsize=40)

    @expose(aliases=[u'preview <name>'], aliases_only=True)
    def preview(self):
        """Get heat stack preview
        """        
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        obj = self.entity_class.stack.preview(name, **params)
        # res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)        
    
    @expose(aliases=[u'create <name> ..'], aliases_only=True)
    def create(self):
        """Create heat stacks
        """
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stack.create(name, **params)
        self.wait_stack_create(name, res[u'id'])
        logger.info(res)
        self.result(res, headers=self.headers)    
    
    @expose(aliases=[u'update <name> <oid> ..'], aliases_only=True)
    def update(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stack.update(name, oid, **params)
        res = {u'msg': u'Update stack %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'update-preview <name> <oid> ..'], aliases_only=True)
    def update_preview(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stack.update_preview(name, oid, **params)
        res = {u'msg': u'Update preview stack %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'delete <name> <oid>'], aliases_only=True)
    def delete(self):
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.stack.list(oid=oid)
        if len(obj) <= 0:
            self.app.print_error(u'Stack %s not found' % oid)
            return
        obj = obj[0]
        self.entity_class.stack.delete(obj[u'stack_name'], oid)
        self.wait_stack_delete(obj[u'stack_name'], oid)
        res = {u'msg': u'Delete stack %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])


openstack_platform_controller_handlers = [
    OpenstackPlatformController,
    OpenstackPlatformSystemController,
    OpenstackPlatformKeystoneController,
    OpenstackPlatformProjectController,
    OpenstackPlatformNetworkController,
    OpenstackPlatformSubnetController,
    OpenstackPlatformPortController,
    OpenstackPlatformFloatingIpController,
    OpenstackPlatformRouterController,
    OpenstackPlatformSecurityGroupController,
    OpenstackPlatformImageController,
    OpenstackPlatformFlavorController,
    OpenstackPlatformKeyPairController,
    OpenstackPlatformServerController,
    OpenstackPlatformVolumeController,
    OpenstackPlatformHeatStackController
]


#
# openstack orchestrator
#
class OpenstackController(BaseController):
    class Meta:
        label = 'openstack'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Beehive Openstack Orchestrator Wrapper management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Beehive Openstack Orchestrator Wrapper management", hide=True)
    def default(self):
        self.app.args.print_help()


class OpenstackControllerChild(ResourceEntityController):
    uri = u'/v1.0/openstacks'
    subsystem = u'resource'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'container.name', u'ext_id', u'state']
    
    class Meta:
        stacked_on = 'openstack'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def _ext_parse_args(self):
        ApiController._ext_parse_args(self)
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List openstack items
        """        
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, key=self._meta.aliases[0])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get openstack item
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


class OpenstackDomainController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/domains'
    
    class Meta:
        label = 'openstack.beehive.domains'
        aliases = ['domains']
        aliases_only = True        
        description = "Openstack Domain management"


class OpenstackProjectController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/projects'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'container.name',
               u'ext_id', u'details.level']
    
    class Meta:
        label = 'openstack.beehive.projects'
        aliases = ['projects']
        aliases_only = True        
        description = "Openstack Project management"


class OpenstackNetworkController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/networks'
    headers = [u'id', u'parent.name', u'container.name', u'name', u'details.segmentation_id', u'details.external',
               u'details.shared', u'details.provider_network_type']
    
    class Meta:
        label = 'openstack.beehive.networks'
        aliases = ['networks']
        aliases_only = True
        description = "Openstack Network management"


class OpenstackSubnetController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/subnets'
    headers = [u'id', u'parent', u'container', u'name', u'cidr', u'allocation_pools', u'gateway_ip']
    
    class Meta:
        label = 'openstack.beehive.subnets'
        aliases = ['subnets']
        aliases_only = True
        description = "Openstack Subnet management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List openstack items
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        resp = []
        for item in res.get(u'subnets'):
            allocation_pools = item.get(u'details').get(u'allocation_pools')
            allocation_pools = [u'%s - %s' % (a[u'start'], a[u'end']) for a in allocation_pools]
            resp.append({
                u'id': item.get(u'id'),
                u'parent': item.get(u'parent', {}).get(u'name'),
                u'container': item.get(u'container', {}).get(u'name'),
                u'name': item.get(u'name'),
                u'cidr': item.get(u'details').get(u'cidr'),
                u'allocation_pools': allocation_pools,
                u'gateway_ip': item.get(u'details').get(u'gateway_ip')
            })
        res[self._meta.aliases[0]] = resp
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], res))
        self.result(res, headers=self.headers, key=self._meta.aliases[0], key_separator=u'|')


class OpenstackPortController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/ports'
    headers = [u'id',  u'container.name', u'parent.name', u'name', u'details.device_owner', u'details.mac_address',
               u'details.fixed_ips.0.ip_address']
    
    class Meta:
        label = 'openstack.beehive.ports'
        aliases = ['ports']
        aliases_only = True         
        description = "Openstack Port management"     


class OpenstackFloatingIpController(OpenstackControllerChild):
    headers = [u'id',  u'container.name', u'parent.name', u'name']
    
    class Meta:
        label = 'openstack.beehive.floatingips'
        aliases = ['floatingips']
        aliases_only = True         
        description = "Openstack FloatingIp management"
        
    @check_error
    def _ext_parse_args(self):
        OpenstackControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.ip


class OpenstackRouterController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/routers'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', u'details.enable_snat',
               u'details.external_network.name', u'details.external_ips.0.ip_address']
    
    class Meta:
        label = 'openstack.beehive.routers'
        aliases = ['routers']
        aliases_only = True         
        description = "Openstack Router management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get openstack item
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET')
        key = self._meta.aliases[0].rstrip(u's')
        res = res.get(key)
        logger.info(u'Get %s: %s' % (key, truncate(res)))
        details = res.pop(u'details')
        external_net = details.get(u'external_network')
        external_ips = details.get(u'external_ips')
        self.result(res, details=True)
        self.app.print_output(u'External network:')
        self.result(external_net, headers=[u'uuid', u'name', u'state'])
        self.app.print_output(u'External ip:')
        self.result(external_ips, headers=[u'subnet_id', u'ip_address'])

        # get internal ports
        uri = self.uri + u'/' + oid + u'/ports'
        ports = self._call(uri, u'GET').get(u'router_ports', [])
        self.app.print_output(u'Internal ports:')
        self.result(ports, headers=[u'id', u'name', u'state', u'details.network.name', u'details.device_owner',
                                    u'details.mac_address', u'details.device.name', u'details.fixed_ips.0.ip_address'],
                    maxsize=30)


class OpenstackSecurityGroupController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/security_groups'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', u'ext_id']
    
    class Meta:
        label = 'openstack.beehive.security_groups'
        aliases = ['security_groups']
        aliases_only = True         
        description = "Openstack SecurityGroup management"           
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get openstack item
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET').get(u'security_group', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        rules = res.get(u'details').pop(u'rules')
        self.result(res, details=True)
        print(u'rules:')
        self.result(rules, headers=[u'id', u'direction', u'protocol', 
            u'ethertype', u'remote_ip_prefix', u'remote_group.name', 
            u'remote_group.id', u'port_range_min', u'port_range_max'])     


class OpenstackImageController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/images'
    headers = [u'id', u'container.name', u'name',
               u'details.size', u'details.minDisk', u'details.minRam', 
               u'details.progress', u'details.status', u'details.metadata'] 
    
    class Meta:
        label = 'openstack.beehive.images'
        aliases = ['images']
        aliases_only = True         
        description = "Openstack Image management"


class OpenstackFlavorController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/flavors'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', 
               u'ext_id']
    
    class Meta:
        label = 'openstack.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Openstack Flavor management"


class OpenstackServerController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/servers'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', 
               u'ext_id', u'details.state']
    
    class Meta:
        label = 'openstack.beehive.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Openstack Server management"
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get openstack item
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET').get(u'server', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        detail = res.get(u'details')
        volumes = detail.pop(u'volumes', [])
        networks = detail.pop(u'networks', [])
        flavor = detail.pop(u'flavor', [])
        self.result(res, details=True)
        self.app.print_output(u'flavor:')
        self.result(flavor, headers=[u'id', u'memory', u'cpu'])
        self.app.print_output(u'volumes:')
        self.result(volumes, headers=[u'id', u'name', u'format', u'bootable', u'storage', u'mode', u'type', u'size'])
        self.app.print_output(u'networks:')
        self.result(networks, headers=[u'net_id', u'name', u'port_id', u'mac_addr', u'port_state',
                                       u'fixed_ips.0.ip_address'])
        
    @expose(aliases=[u'actions <id>'], aliases_only=True)
    def actions(self):
        """Get openstack server actions
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/actions'
        res = self._call(uri, u'GET').get(u'server_actions', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=[u'action', u'request_id', u'message'])    

    @expose(aliases=[u'runtime <id>'], aliases_only=True)
    def runtime(self):
        """Get openstack server actions
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/runtime'
        res = self._call(uri, u'GET').get(u'server_runtime', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=[u'action', u'request_id', u'message'], 
                    details=True) 
        
    @expose(aliases=[u'stats <id>'], aliases_only=True)
    def stats(self):
        """Get openstack server stats
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/stats'
        res = self._call(uri, u'GET').get(u'server_stats', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=[u'action', u'request_id', u'message'], 
                    details=True)         
        
    @expose(aliases=[u'metadata <id>'], aliases_only=True)
    def metadata(self):
        """Get openstack server metadata
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/metadata'
        res = self._call(uri, u'GET').get(u'server_metadata', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=[u'action', u'request_id', u'message'])         
        
    @expose(aliases=[u'security-groups <id>'], aliases_only=True)
    def security_groups(self):
        """Get openstack server sgs
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/security_groups'
        res = self._call(uri, u'GET').get(u'server_security_groups', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=[u'id', u'uuid', u'name', u'ext_id', u'state'])         
        
    @expose(aliases=[u'console <id>'], aliases_only=True)
    def console(self):
        """Get openstack server console
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/console'
        res = self._call(uri, u'GET').get(u'server_console', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result([res], headers=[u'type', u'url'], 
                    maxsize=400)
        sh.firefox(res.get(u'url'))

    @expose(aliases=[u'ssh <id> <user>'], aliases_only=True)
    def ssh(self):
        """Get openstack server console
        """
        oid = self.get_arg(name=u'id')
        pkey = self.get_arg(name=u'pkey')
        port = 22
        user = u'root'
        pwd = u'cs1$topix'
        
        # get server
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET').get(u'server', {})
        logger.info(u'Get server: %s' % (truncate(res)))
        ipaddress = res[u'details'][u'networks'][0][u'fixed_ips'][0][u'ip_address']    
        ipaddress = u'10.102.184.69'
        # open ssh client
        client = SSHClient()
        client.set_missing_host_key_policy(MissingHostKeyPolicy())
        client.connect(ipaddress, port, username=user, password=pwd, look_for_keys=False, compress=True)
        #timeout=None, #allow_agent=True,
        
        channel = client.invoke_shell(term=u'vt100', width=80, height=24, width_pixels=500, height_pixels=400)
        channel.send('ls\n')
        output=channel.recv(2024)
        print(output)
        
    @expose(aliases=[u'stop <id>'], aliases_only=True)
    def stop(self):
        """Stop openstack server
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/action'
        data = {u'server_action':{u'stop':True}}
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Stop server %s' % (oid))
        self.result({u'msg': u'Stop server %s' % (oid)}, headers=[u'msg'], maxsize=400)
        self.wait_job(res[u'jobid'])
        
    @expose(aliases=[u'start <id>'], aliases_only=True)
    def start(self):
        """start openstack server
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/action'
        data = {u'server_action':{u'start':True}}
        res = self._call(uri, u'PUT', data=data)
        logger.info(u'Start server %s' % (oid))
        self.result({u'msg': u'Start server %s' % (oid)}, headers=[u'msg'], maxsize=400)
        self.wait_job(res[u'jobid'])         


class OpenstackVolumeController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/volumes'
    headers = [u'id', u'container.name', u'parent.name', u'name']
    
    class Meta:
        label = 'openstack.beehive.volumes'
        aliases = ['volumes']
        aliases_only = True         
        description = "Openstack Volume management"


class OpenstackHeatStackController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/stacks'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', u'ext_id']
    
    class Meta:
        label = 'openstack.beehive.heat.stack'
        aliases = ['stacks']
        aliases_only = True         
        description = "Openstack Heat Stack management"

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get openstack stack
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET').get(u'stack', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        details = res.pop(u'details')
        parameters = [{u'parameter': item, u'value': val} for item, val in details.pop(u'parameters').items()]
        files = details.pop(u'files', {})
        outputs = details.pop(u'outputs')
        self.result(res, details=True, maxsize=800)
        self.app.print_output(u'parameters:')
        self.result(parameters, headers=[u'parameter', u'value'], maxsize=800)
        self.app.print_output(u'files:')
        self.result(files, headers=[u'file', u'content'], maxsize=800)
        self.app.print_output(u'outputs:')
        self.result(outputs, headers=[u'key', u'value', u'desc'],
                    fields=[u'output_key', u'output_value', u'description'], maxsize=100)

    @expose(aliases=[u'template <id>'], aliases_only=True)
    def template(self):
        """Get openstack stack template
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/template'
        res = self._call(uri, u'GET').get(u'stack_template', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        self.result(res, format=u'yaml')

    @expose(aliases=[u'resources <id>'], aliases_only=True)
    def resources(self):
        """Get openstack stack resources
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/resources'
        res = self._call(uri, u'GET').get(u'stack_resources', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'status', u'type', u'creation', u'required_by'],
                    fields=[u'physical_resource_id', u'resource_name', u'resource_status', u'resource_type',
                            u'creation_time', u'required_by'], maxsize=40)

    @expose(aliases=[u'events <id>'], aliases_only=True)
    def events(self):
        """Get heat stack events by id
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/events'
        res = self._call(uri, u'GET').get(u'stack_events', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'resource_id', u'status', u'status_reason', u'event_time'],
                    fields=[u'id', u'resource_name', u'physical_resource_id', u'resource_status',
                            u'resource_status_reason', u'event_time'], maxsize=40)


class OpenstackHeatStackTemplateController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/stack-templates'
    headers = [u'id', u'container.name', u'parent.name', u'name', u'state', u'ext_id']

    class Meta:
        label = 'openstack.beehive.heat.template'
        aliases = ['templates']
        aliases_only = True
        description = "Openstack Heat Stack template management"

    @expose(aliases=[u'versions <orchestrator>'], aliases_only=True)
    def versions(self):
        """Get openstack orchestrator heat template versions
        """
        orchestrator = self.get_arg(name=u'orchestrator')
        uri = self.uri
        res = self._call(uri, u'GET', data=u'container=%s' % orchestrator).get(u'template_versions', {})
        logger.info(u'Get template versions: %s' % truncate(res))
        self.result(res, headers=[u'version', u'type', u'aliases'])

    @expose(aliases=[u'template <orchestrator> <template>'], aliases_only=True)
    def functions(self):
        """Get openstack stack template functions
        """
        orchestrator = self.get_arg(name=u'orchestrator')
        template = self.get_arg(name=u'template')
        uri = u'/v1.0/openstack/stack-template-functions'
        res = self._call(uri, u'GET', data=u'container=%s&template=%s' % (orchestrator, template))\
                  .get(u'template_functions', {})
        logger.info(u'Get template functions: %s' % truncate(res))
        self.result(res, headers=[u'functions', u'description'], maxsize=200)

    @expose(aliases=[u'validate <orchestrator> <template-uri>'], aliases_only=True)
    def validate(self):
        """Get openstack stack template functions
        """
        orchestrator = self.get_arg(name=u'orchestrator')
        template = self.get_arg(name=u'template-uri')
        data = {
            u'stack_template': {
                u'container': orchestrator,
                u'template_uri': template
            }
        }
        uri = u'/v1.0/openstack/stack-template-validate'
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Validate template: %s' % truncate(res))
        if res:
            res[u'uri'] = template
        self.result(res, headers=[u'uri', u'validate'], maxsize=200)


openstack_controller_handlers = [
    OpenstackController,
    OpenstackDomainController,
    OpenstackProjectController,
    OpenstackNetworkController,
    OpenstackSubnetController,
    OpenstackPortController,
    OpenstackFloatingIpController,
    OpenstackRouterController,
    OpenstackSecurityGroupController,
    OpenstackImageController,
    OpenstackFlavorController,
    OpenstackServerController,
    OpenstackVolumeController,
    OpenstackHeatStackController,
    OpenstackHeatStackTemplateController
]
