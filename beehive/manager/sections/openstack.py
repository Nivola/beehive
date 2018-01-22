"""
Created on Sep 27, 2017

@author: darkbk
"""
import requests
import sh
import logging
from cement.core.controller import expose
from gevent import sleep

from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate, id_gen
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


class OpenstackPlatformControllerChild(BaseController):
    headers = [u'id', u'name']
    entity_class = None
    
    class Meta:
        stacked_on = 'openstack.platform'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-O', '--orchestrator'], dict(action='store', help='Openstack platform reference label')),
            (['-p', '--project'], dict(action='store', help='Openstack current project')),
        ]

    @check_error
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)

        orchestrators = self.configs[u'environments'][self.env][u'orchestrators'].get(u'openstack')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Openstack platform label must be specified. '
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        project = self.app.pargs.project
        if project is None:
            project = conf.get(u'project')
        self.client = OpenstackManager(conf.get(u'uri'), default_region=conf.get(u'region'))
        self.client.authorize(conf.get(u'user'), conf.get(u'pwd'), project=project, domain=conf.get(u'domain'))


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
        res = self.client.identity.user.list(detail=True)
        logger.info(res)
        self.result(res, headers=self.headers)

    @expose()
    def compute_api(self):
        """Get compute api versions.
        """
        res = self.client.system.compute_api().get(u'versions', [])
        logger.debug('Get openstack compute services: %s' % (res))
        self.result(res, headers=[u'id', u'version', u'min_version', u'status', u'updated'])
    
    @expose()
    def compute_services(self):
        """Get compute service.
        """
        res = self.client.system.compute_services()
        logger.debug('Get openstack availability zone: %s' % (res))
        self.result(res, headers=[u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at'], maxsize=200)

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
                                  u'vcpus_used', u'memory_mb', u'free_ram_mb', u'local_gb', u'local_gb_used',
                                  u'free_disk_gb', u'current_workload',u'running_vms'], maxsize=200)
    
    @expose()
    def compute_hypervisors_statistics(self):
        """Get compute hypervisors statistics.
        """
        res = self.client.system.compute_hypervisors_statistics()
        logger.debug('Get openstack hypervisors statistics: %s' % (res))
        self.result(res, headers=["count", "vcpus_used", "local_gb_used", "memory_mb", "current_workload", "vcpus",
                                  "running_vms", "free_disk_gb", "disk_available_least", "local_gb", "free_ram_mb",
                                  "memory_mb_used"], maxsize=200)

    @expose()
    def compute_agents(self):
        """Get compute agents.
        Use guest agents to access files on the disk, configure networking, and 
    run other applications and scripts in the guest while it runs. This
    hypervisor-specific extension is not currently enabled for KVM. Use of
    guest agents is possible only if the underlying service provider uses
    the Xen driver.
        """
        res = self.client.system.compute_agents()
        logger.debug('Get openstack agents: %s' % (res))
        self.result(res, headers=[], maxsize=200)
    
    @expose()
    def storage_services(self):
        """Get storage service.
        """
        res = self.client.system.storage_services()
        logger.debug('Get openstack storage services: %s' % truncate(res))
        self.result(res, headers=[u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at'], maxsize=200)
    
    @expose()
    def network_agents(self):
        """Get network agents.
        """
        res = self.client.system.network_agents()
        logger.debug('Get openstack network agents: %s' % truncate(res))
        self.result(res, headers=[u'id', u'host', u'availability_zone', u'binary', u'agent_type', u'alive',
                                  u'started_at'], maxsize=200)
    
    @expose()
    def network_service_providers(self):
        """Get network service providers.
        """
        res = self.client.system.network_service_providers()
        logger.debug('Get openstack network service providers: %s' % truncate(res))
        self.result(res, headers=[u'service_type', u'name', u'default'], maxsize=200)
    
    @expose()
    def orchestrator_services(self):
        """Get heat services.
        """
        res = self.client.system.orchestrator_services()
        logger.debug('Get openstack orchestrator services: %s' % truncate(res))
        self.result(res, headers=[u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at'], maxsize=200)


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
        # params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.user.list(detail=True)
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose()
    def roles(self):
        # params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.client.identity.role.list(detail=False)
        logger.info(res)
        self.result(res, headers=[u'id', u'name'])
        
    @expose()
    def regions(self):
        # params = self.get_query_params(*self.app.pargs.extra_arguments)
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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformSubnetController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'network_id', u'cidr', u'enable_dhcp']
    
    class Meta:
        label = 'openstack.platform.subnets'
        aliases = ['subnets']
        aliases_only = True         
        description = "Openstack Subnet management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.subnet

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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformPortController(OpenstackPlatformControllerChild):
    headers = [u'id', u'tenant_id', u'network_id', u'fixed_ips.0.ip_address', u'mac_address', u'status',
               u'device_owner', u'created_at']
    
    class Meta:
        label = 'openstack.platform.ports'
        aliases = ['ports']
        aliases_only = True         
        description = "Openstack Port management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.port

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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        self.result(res, headers=[u'id', u'name', u'status', u'progress', u'created', u'minDisk', u'minRam',
                                  u'OS-EXT-IMG-SIZE:size'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get(oid)
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        self.result(res, headers=[u'id', u'name', u'ram', u'vcpus', u'swap', u'os-flavor-access:is_public',
                                  u'rxtx_factor', u'disk', u'OS-FLV-EXT-DATA:ephemeral', u'OS-FLV-DISABLED:disabled'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get(oid)
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get(oid)
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformVolumeController(OpenstackPlatformControllerChild):
    headers = [u'id', u'name', u'os-vol-tenant-attr:tenant_id', u'size', u'status', u'bootable',
               u'attachments.0.server_id']
    
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

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get(oid)
        res = obj
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


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
        self.result(outputs, headers=[u'key', u'value', u'desc', u'error'],
                    fields=[u'output_key', u'output_value', u'description', u'output_error'], maxsize=50)

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
        """Create heat stack
        """
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stack.create(name, **params)
        self.wait_stack_create(name, res[u'id'])
        logger.info(res)
        self.result(res, headers=self.headers)    

    @expose(aliases=[u'action <oid> <action>'], aliases_only=True)
    def action(self):
        """Execute heat stack action
        """
        oid = self.get_arg(name=u'oid')
        action = self.get_arg(name=u'action')
        stack = self.entity_class.stack.list(oid=oid)[0]
        res = self.entity_class.stack.action(stack[u'stack_name'], oid, action)
        logger.info(res)
        print(res)
        # self.wait_stack_create(name, res[u'id'])
        # logger.info(res)
        # self.result(res, headers=self.headers)

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


class OpenstackPlatformHeatSoftwareConfigController(OpenstackPlatformControllerChild):
    headers = [u'id', u'project', u'name', u'group', u'creation_time']

    class Meta:
        label = 'openstack.platform.software_config'
        aliases = ['software_configs']
        aliases_only = True
        description = "Openstack Heat Software Config management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.heat.software_config

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List heat software config
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        logger.info(objs)
        self.result(objs, headers=self.headers, maxsize=70)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get heat software config by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'create <file data>'], aliases_only=True)
    def add(self):
        """Create heat software config
        """
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        res = self.entity_class.create(**data).get(u'software_config', {})
        # self.wait_stack_create(name, res[u'id'])
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'group', ])

    @expose(aliases=[u'delete <oid>'], aliases_only=True)
    def delete(self):
        """Delete heat software config
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.delete(oid)
        res = {u'msg': u'Delete software config %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformHeatSoftwareDeploymentController(OpenstackPlatformControllerChild):
    headers = [u'id', u'action', u'server_id', u'config_id', u'creation_time', u'updated_time', u'status',
               u'status_reason']

    class Meta:
        label = 'openstack.platform.software_deployment'
        aliases = ['software_deployments']
        aliases_only = True
        description = "Openstack Heat Software Deployment management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.heat.software_deployment

    def wait_deployment_create(self, oid):
        res = self.entity_class.get(oid)
        status = res[u'status']

        while status not in [u'FAILED', u'COMPLETE']:
            logger.debug(status)
            sleep(1)
            res = self.entity_class.get(oid)
            status = res[u'status']
            print(u'.')
        if status == u'FAILED':
            print(res[u'status_reason'])

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List heat software deployment
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        logger.info(objs)
        self.result(objs, headers=self.headers, maxsize=70)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get heat software deployment by id
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'create <stack_id> <server_id> <config>'], aliases_only=True)
    @check_error
    def add(self):
        """Create heat software deployment
        """
        stack_id = self.get_arg(name=u'stack_id')
        server_id = self.get_arg(name=u'server_id')
        file_data = self.get_arg(name=u'config')
        data = self.load_config(file_data)

        sw_config_name = data[u'name'] + u'-' + id_gen()

        timeout = 3600
        container = stack_id
        method = u'PUT'
        key = id_gen()

        try:
            self.client.swift.container_read(container=container)
        except:
            self.client.swift.container_put(container=container)
        self.client.swift.generate_key(container=container, key=key)
        self.client.swift.object_put(container=container, c_object=sw_config_name)
        temp_url = self.client.swift.generate_temp_url(container=container, c_object=sw_config_name, timeout=timeout,
                                                       method=method, key=key)
        # print temp_url
        # print self.client.swift.container_read(container=container)
        # print self.client.swift.object_get(container=container, c_object=sw_config_name)

        data[u'inputs'].extend([
            {"type": "String", "name": "deploy_signal_transport", "value": "TEMP_URL_SIGNAL"},
            {"type": "String", "name": "deploy_signal_id", "value": temp_url},
            {"type": "String", "name": "deploy_signal_verb", "value": "PUT"},
            {"type": "String", "name": "deploy_stack_id", "value": stack_id}
        ])
        data[u'name'] = sw_config_name
        
        sw_config = self.client.heat.software_config.create(**data).get(u'software_config', {})

        action = u'CREATE'
        res = self.entity_class.create(sw_config[u'id'], server_id, action=action, status="IN_PROGRESS",
                                       status_reason="Deploy data available")
        res = res.get(u'software_deployment', {})
        # print res
        print u'stack: %s' % stack_id
        print u'Sw config name: %s' % sw_config_name
        print u'Sw config id: %s' % sw_config[u'id']
        print u'Sw deployment id: %s' % res[u'id']

        # obj = self.client.heat.stack.list(oid=stack_id)
        # obj = obj[0]
        # res1 = self.client.heat.stack.action(obj[u'stack_name'], stack_id, u'resume')
        # res = self.client.heat.stack.update(obj[u'stack_name'], stack_id)

        # self.wait_deployment_create(res[u'id'])
        logger.info(res)
        self.result(res, headers=[u'id', u'server_id', u'config_id', u'status', u'action'])

    @expose(aliases=[u'update <config> <oid>'], aliases_only=True)
    @check_error
    def update(self):
        """Update heat software deployment
        """
        # name = self.get_arg(name=u'name')
        config = self.get_arg(name=u'config')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.update(config, oid, **self.app.kvargs)
        res = {u'msg': u'Update software deployment %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <oid>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete heat software deployment
        """
        # name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.delete(oid)
        res = {u'msg': u'Delete software deployment %s' % oid}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformSwiftController(OpenstackPlatformControllerChild):
    headers = [u'id', u'action', u'server_id', u'config_id', u'creation_time', u'updated_time', u'status',
               u'status_reason']

    class Meta:
        label = 'openstack.platform.swift'
        aliases = ['swift']
        aliases_only = True
        description = "Openstack Swift management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.swift

    @expose()
    @check_error
    def containers(self):
        """List containers
        """
        res = self.entity_class.container_read()
        logger.debug(res)
        if self.format == u'text':
            for item in res:
                if isinstance(item, list):
                    self.result(item, headers=[u'name', u'count', u'last_modified', u'bytes'], maxsize=60)
                elif isinstance(item, dict):
                    self.result(item, details=True)
        else:
            self.result(res, details=True)

    @expose(aliases=[u'container <oid>'], aliases_only=True)
    @check_error
    def container(self):
        """Get container by name
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.container_read(container=oid)
        logger.debug(res)
        if self.format == u'text':
            for item in res:
                if isinstance(item, list):
                    self.result(item, headers=[u'name', u'hash', u'content_type', u'last_modified', u'bytes'],
                                maxsize=80)
                elif isinstance(item, dict):
                    self.result(item, details=True)
        else:
            self.result(res, details=True)

    @expose(aliases=[u'container_add <oid>'], aliases_only=True)
    @check_error
    def container_add(self):
        container = 'prova'
        res = self.entity_class.container_put(container=container, x_container_meta_name={'meta1': '', 'meta2': ''})
        logger.debug(res)

    @expose(aliases=[u'container_delete <oid>'], aliases_only=True)
    @check_error
    def container_delete(self):
        container = 'morbido'
        res = self.entity_class.container_delete(container=container)
        logger.debug(res)

    @expose(aliases=[u'object <container> <oid>'], aliases_only=True)
    @check_error
    def object(self):
        """Get object by name
        """
        container = self.get_arg(name=u'container')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.object_get(container=container, c_object=oid)
        logger.debug(res)
        if self.format == u'text':
            for item in res:
                if isinstance(item, list):
                    self.result(item, headers=[u'name', u'hash', u'content_type', u'last_modified', u'bytes'],
                                maxsize=80)
                elif isinstance(item, dict):
                    self.result(item, details=True)
        else:
            self.result(res, details=True)

    @expose(aliases=[u'object-delete <container> <oid>'], aliases_only=True)
    @check_error
    def object_delete(self):
        """Delete object by name
        """
        container = self.get_arg(name=u'container')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.object_delete(container=container, c_object=oid)
        msg = {u'msg': u'Delete object %s:%s' % (container, oid)}
        logger.debug(msg)
        self.result(msg, headers=[u'msg'])


class OpenstackPlatformManilaController(OpenstackPlatformControllerChild):
    class Meta:
        label = 'openstack.platform.manila'
        aliases = ['manila']
        aliases_only = True
        description = "Openstack Manila management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila

    @expose()
    @check_error
    def api(self):
        """List manila api versions
        """
        res = self.entity_class.api()
        logger.debug(res)
        self.result(res, headers=[u'id', u'version', u'min_version', u'status', u'updated'])

    @expose()
    @check_error
    def limits(self):
        """List manila limits
        """
        res = self.entity_class.limits()
        logger.debug(res)
        self.result(res, details=True)

    @expose()
    @check_error
    def services(self):
        """List manila api services
        """
        res = self.entity_class.services()
        logger.debug(res)
        self.result(res, headers=[u'id', u'state', u'host', u'status', u'zone', u'binary', u'updated_at'])


class OpenstackPlatformManilaChildController(OpenstackPlatformControllerChild):
    class Meta:
        stacked_on = 'openstack.platform.manila'
        stacked_type = 'nested'


class OpenstackPlatformManilaShareController(OpenstackPlatformManilaChildController):
    class Meta:
        label = 'openstack.platform.manila.share'
        aliases = ['shares']
        aliases_only = True
        description = "Openstack Manila Share management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila.share

    @expose(aliases=[u'list [key=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List manila shares
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.list(details=True, **params)
        logger.debug(res)
        self.result(res, headers=[u'id', u'name', u'project_id', u'size', u'created_at', u'share_type', u'share_proto',
                                  u'status', u'is_public'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get manila share by id
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'add <name> <size> <proto> <share_type>'], aliases_only=True)
    @check_error
    def add(self):
        """Add manila share
    - name: share name
    - size: share in GB
    - proto: share protocol (NFS, CIFS, GlusterFS, HDFS, or CephFS. CephFS)
    - share_type: share type
        """
        name = self.get_arg(name=u'name')
        size = self.get_arg(name=u'size')
        proto = self.get_arg(name=u'proto')
        share_type = self.get_arg(name=u'share_type')
        res = self.entity_class.create(proto, size, name=name, description=name, share_type=share_type,
                                       is_public=False, availability_zone=u'nova')
        res = {u'msg': u'Create manila share %s' % (name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id> [force=true]'], aliases_only=True)
    def delete(self):
        """Delete manila share
    - force: if true force delete
        """
        oid = self.get_arg(name=u'id')
        force = self.get_arg(name=u'force', default=False, keyvalue=True)
        if force is True:
            res = self.entity_class.action.force_delete(oid)
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete manila share %s' % (oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'grant-list <id>'], aliases_only=True)
    def grant_list(self):
        """List manila share <id> access list
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.action.list_access(oid)
        logger.info(res)
        self.result(res, headers=[u'id', u'access_type', u'access_level', u'state', u'access_to'])

    @expose(aliases=[u'grant-add <id> <level> <type> <to>'], aliases_only=True)
    def grant_add(self):
        """Add manila share <id> access grant
    - level: The access level to the share. To grant or deny access to a share:
        - rw: Read and write (RW) access.
        - ro: Read-only (RO) access.
    - type: The access rule type. Valid values are:
        - ip: Authenticates an instance through its IP address.
        - cert: Authenticates an instance through a TLS certificate.
        - user: Authenticates by a user or group name.
    - to: The value that defines the access. The back end grants or denies the access to it. Valid values are:
        - ip: A valid format is XX.XX.XX.XX or XX.XX.XX.XX/XX. For example 0.0.0.0/0.
        - cert: Specify the TLS identity as the IDENTKEY. A valid value is any string up to 64 characters long in the
                common name (CN) of the certificate. The meaning of a string depends on its interpretation.
        - user: A valid value is an alphanumeric string that can contain some special characters and is from 4 to 32
                characters long.
        """
        oid = self.get_arg(name=u'id')
        access_level = self.get_arg(name=u'access_level')
        access_type = self.get_arg(name=u'access_type')
        access_to = self.get_arg(name=u'access_to')
        res = self.entity_class.action.grant_access(oid, access_level, access_type, access_to)
        logger.info(res)
        self.result(res, headers=[u'id', u'access_type', u'access_level', u'state', u'access_to'])

    @expose(aliases=[u'grant-remove <id> <access_id>'], aliases_only=True)
    def grant_remove(self):
        """Remove manila share <id> access grant
        """
        oid = self.get_arg(name=u'id')
        access_id = self.get_arg(name=u'access_id')
        res = self.entity_class.action.revoke_access(oid, access_id)
        res = {u'msg': u'Revoke access %s to share %s' % (oid, access_id)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'reset-status <id> <status>'], aliases_only=True)
    def reset_status(self):
        """Reset manila share <id> status
    - status: The share access status, which is new, error, active
        """
        oid = self.get_arg(name=u'id')
        access_id = self.get_arg(name=u'access_id')
        res = self.entity_class.action.reset_status(oid, access_id)
        res = {u'msg': u'Reset status of share %s to %s' % (oid, status)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'size-extend <id> <new_size>'], aliases_only=True)
    def size_extend(self):
        """Reset manila share <id> status
    - new_size: New size of the share, in GBs.
        """
        oid = self.get_arg(name=u'id')
        new_size = self.get_arg(name=u'new_size')
        res = self.entity_class.action.extend(oid, new_size)
        res = {u'msg': u'Extend share %s to %s' % (oid, new_size)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'size-shrink <id> <new_size>'], aliases_only=True)
    def size_shrink(self):
        """Reset manila share <id> status
    - new_size: New size of the share, in GBs.
        """
        oid = self.get_arg(name=u'id')
        new_size = self.get_arg(name=u'new_size')
        res = self.entity_class.action.shrink(oid, new_size)
        res = {u'msg': u'Shrink share %s to %s' % (oid, new_size)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'revert-to-snapshot <id> <snapshot_id>'], aliases_only=True)
    def revert_to_snapshot(self):
        """Reset manila share <id> status
    - snapshot_id: New size of the share, in GBs.
        """
        oid = self.get_arg(name=u'id')
        snapshot_id = self.get_arg(name=u'snapshot_id')
        res = self.entity_class.action.revert(oid, snapshot_id)
        res = {u'msg': u'Revert share %s to snapshot_id %s' % (oid, snapshot_id)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformManilaShareSnapshotController(OpenstackPlatformManilaChildController):
    class Meta:
        label = 'openstack.platform.manila.share_snapshot'
        aliases = ['snapshots']
        aliases_only = True
        description = "Openstack Manila Share Snapshots management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila.share.snapshot

    @expose(aliases=[u'list [key=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List manila share snapshots
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.list(details=True, **params)
        logger.debug(res)
        self.result(res, headers=[u'id', u'name', u'project_id', u'size', u'created_at', u'share_type', u'share_proto',
                                  u'export_location'], maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get manila share snapshot by id
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'add <share_id> <name>'], aliases_only=True)
    @check_error
    def add(self):
        """Add manila share snapshot
    - name: share name
    - share_id: id of the share
        """
        share_id = self.get_arg(name=u'share_id')
        name = self.get_arg(name=u'name')
        res = self.entity_class.create(share_id, name=name)
        res = {u'msg': u'Create %s %s' % (self.entity_class, name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformManilaShareTypeController(OpenstackPlatformManilaChildController):
    class Meta:
        label = 'openstack.platform.manila.share_types'
        aliases = ['types']
        aliases_only = True
        description = "Openstack Manila Share Type management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila.share_type

    @expose(aliases=[u'list [default=true/false]'], aliases_only=True)
    @check_error
    def list(self):
        """List manila share types
    - default=true list default share types
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.list(**params)
        logger.debug(res)
        self.result(res, headers=[u'id', u'name', u'access', u'backend'], fields=[u'id', u'name',
                    u'os-share-type-access:is_public', u'extra_specs.share_backend_name'], maxsize=60)

    @expose(aliases=[u'extra-spec <id>'], aliases_only=True)
    @check_error
    def extra_spec(self):
        """Get manila share type extra spec by id
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get_extra_spec(oid)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'access <id>'], aliases_only=True)
    @check_error
    def access(self):
        """Get manila share type access by id. If share type access is True this command return error.
        """
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get_access(oid)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'add <name> [key=value]'], aliases_only=True)
    @check_error
    def add(self):
        """Creates a share type
    - name: The share type name.
    - desc: (Optional) The description of the share type.
    - is_public: (Optional) Indicates whether is publicly accessible. Default is false.
    - replication_type: (Optional) The share replication type.
    - driver_handles_share_servers: (Optional) An extra specification that defines the driver mode for share server, or
    storage, life cycle management. The Shared File Systems service creates a share server for the export of shares.
    This value is true when the share driver manages, or handles, the share server life cycle. This value is false when
    an administrator rather than a share driver manages the storage life cycle.
    - mount_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their capability to mount
    share snapshots.
    - revert_to_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their capability to
    revert shares to snapshots.
    - create_share_from_snapshot_support: (Optional) Boolean extra spec used for filtering of back ends by their
    capability to create shares from snapshots.
    - snapshot_support: (Optional) An extra specification that filters back ends by whether they do or do not support
    share snapshots.
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc', default=name, keyvalue=True)
        is_public = self.get_arg(name=u'is_public', default=False, keyvalue=True)
        replication_type = self.get_arg(name=u'replication_type', default=None, keyvalue=True)
        driver_handles_share_servers = self.get_arg(name=u'driver_handles_share_servers', default=None, keyvalue=True)
        mount_snapshot_support = self.get_arg(name=u'mount_snapshot_support', default=None, keyvalue=True)
        revert_to_snapshot_support = self.get_arg(name=u'revert_to_snapshot_support', default=None, keyvalue=True)
        create_share_from_snapshot_support = self.get_arg(name=u'create_share_from_snapshot_support', default=None,
                                                          keyvalue=True)
        snapshot_support = self.get_arg(name=u'snapshot_support', default=None, keyvalue=True)
        res = self.entity_class.create(name, desc=desc, is_public=is_public, replication_type=replication_type,
                                       driver_handles_share_servers=driver_handles_share_servers,
                                       mount_snapshot_support=mount_snapshot_support,
                                       revert_to_snapshot_support=revert_to_snapshot_support,
                                       create_share_from_snapshot_support=create_share_from_snapshot_support,
                                       snapshot_support=snapshot_support)
        res = {u'msg': u'Create %s %s' % (self.entity_class, name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete %s %s' % (self.entity_class, oid)}
        logger.info(res)
        self.result(res, headers=[u'msg'])


class OpenstackPlatformManilaStoragePoolController(OpenstackPlatformManilaChildController):
    class Meta:
        label = 'openstack.platform.manila.storage_pool'
        aliases = ['storage_pools']
        aliases_only = True
        description = "Openstack Manila storage Pool management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila.storage_pool

    @expose(aliases=[u'list [key=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List manila storage pools
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.list(details=True, **params)
        logger.debug(res)
        self.result(res, headers=[u'name', u'pool', u'backend', u'host'], maxsize=60)


class OpenstackPlatformManilaQuotaSetController(OpenstackPlatformManilaChildController):
    class Meta:
        label = 'openstack.platform.manila.quota_set'
        aliases = ['quota_set']
        aliases_only = True
        description = "Openstack Manila Quota Set management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.manila.quota_set

    @expose(aliases=[u'get-default <project_id>'], aliases_only=True)
    @check_error
    def get_default(self):
        """List manila default quota set per project
        """
        project_id = self.get_arg(name=u'project_id')
        res = self.entity_class.get_default(project_id)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'get <project_id>'], aliases_only=True)
    @check_error
    def get(self):
        """List manila quota set per project
        """
        project_id = self.get_arg(name=u'project_id')
        res = self.entity_class.get(project_id)
        logger.debug(res)
        self.result(res, details=True)

    @expose(aliases=[u'update <project_id> [key=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update manila quota set per project
    - gigabytes: The number of gigabytes for the tenant.
    - snapshots: The number of snapshots for the tenant.
    - snapshot_gigabytes: The number of gigabytes for the snapshots for the tenant.
    - shares: The number of shares for the tenant.
    - share_networks: The number of share networks for the tenant.
    - share_groups: The number of share groups allowed for each tenant or user.
    - share_group_snapshots: The number of share group snapshots allowed for each tenant or user.
    - share_type: The name or UUID of the share type. If you specify this parameter in the URI, you show, update, or
    delete quotas for this share type.
        """
        project_id = self.get_arg(name=u'project_id')
        gigabytes = self.get_arg(name=u'gigabytes', default=None, keyvalue=True)
        snapshots = self.get_arg(name=u'snapshots', default=None, keyvalue=True)
        snapshot_gigabytes = self.get_arg(name=u'snapshot_gigabytes', default=None, keyvalue=True)
        shares = self.get_arg(name=u'shares', default=None, keyvalue=True)
        share_networks = self.get_arg(name=u'share_networks', default=None, keyvalue=True)
        share_groups = self.get_arg(name=u'share_groups', default=None, keyvalue=True)
        share_group_snapshots = self.get_arg(name=u'share_group_snapshots', default=None, keyvalue=True)
        share_type = self.get_arg(name=u'share_type', default=None, keyvalue=True)
        res = self.entity_class.update(project_id, snapshots=snapshots, snapshot_gigabytes=snapshot_gigabytes,
                                       shares=shares, share_networks=share_networks, share_groups=share_groups,
                                       share_group_snapshots=share_group_snapshots, share_type=share_type,
                                       gigabytes=gigabytes)
        logger.debug(res)
        self.result(res, details=True)


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
    OpenstackPlatformHeatStackController,
    OpenstackPlatformHeatSoftwareConfigController,
    OpenstackPlatformHeatSoftwareDeploymentController,
    OpenstackPlatformSwiftController,
    OpenstackPlatformManilaController,
    OpenstackPlatformManilaShareController,
    OpenstackPlatformManilaShareSnapshotController,
    OpenstackPlatformManilaShareTypeController,
    OpenstackPlatformManilaStoragePoolController,
    OpenstackPlatformManilaQuotaSetController
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


class OpenstackControllerChild(ResourceEntityController):
    uri = u'/v1.0/openstacks'
    subsystem = u'resource'
    headers = [u'id', u'uuid', u'name', u'parent.name', u'container.name', u'ext_id', u'state']
    
    class Meta:
        stacked_on = 'openstack'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
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
        self.result(res, headers=self.headers, key=self._meta.aliases[0], maxsize=40)

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
            allocation_pools = item.get(u'details').get(u'allocation_pools', [])
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
    headers = [u'id', u'uuid', u'container.name', u'parent.name', u'name', u'state',
               u'ext_id']
    
    class Meta:
        label = 'openstack.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Openstack Flavor management"


class OpenstackServerController(OpenstackControllerChild):
    uri = u'/v1.0/openstack/servers'
    headers = [u'id', u'parent.name', u'container.name', u'name', u'state', u'details.state', u'details.ip_address',
               u'details.hostname', u'details.cpu', u'details.memory', u'details.disk']
    
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
        res = self._call(uri, u'GET')
        res = res.get(u'server', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        detail = res.get(u'details')
        volumes = detail.pop(u'volumes', [])
        networks = detail.pop(u'networks', [])
        flavor = detail.pop(u'flavor', [])
        security_groups = detail.pop(u'security_groups', [])
        self.result(res, details=True)
        self.app.print_output(u'flavor:')
        self.result(flavor, headers=[u'id', u'memory', u'cpu'])
        self.app.print_output(u'volumes:')
        self.result(volumes, headers=[u'id', u'name', u'format', u'bootable', u'storage', u'mode', u'type', u'size'])
        self.app.print_output(u'networks:')
        self.result(networks, headers=[u'net_id', u'name', u'port_id', u'mac_addr', u'port_state',
                                       u'fixed_ips.0.ip_address'])
        self.app.print_output(u'security_groups:')
        self.result(security_groups, headers=[u'uuid', u'name'])
        
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
        self.result(details, details=True, maxsize=800)
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

    @expose(aliases=[u'internal-resources <id>'], aliases_only=True)
    def internal_resources(self):
        """Get openstack stack internal resources
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/internal_resources'
        res = self._call(uri, u'GET').get(u'stack_resources', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'status', u'type', u'creation', u'required_by'],
                    fields=[u'physical_resource_id', u'resource_name', u'resource_status', u'resource_type',
                            u'creation_time', u'required_by'], maxsize=40)

    @expose(aliases=[u'resources <id>'], aliases_only=True)
    def resources(self):
        """Get openstack stack resources
        """
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/resources'
        res = self._call(uri, u'GET').get(u'resources', {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        logger.info(res)
        self.result(res, headers=[u'id', u'definition', u'name', u'container', u'parent', u'state',
                                  u'date.creation', u'ext_id'],
                    fields=[u'id', u'__meta__.definition', u'name', u'container.name', u'parent.name', u'state',
                            u'date.creation', u'ext_id'], maxsize=40)

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
