'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate
from beedrones.openstack.client import OpenstackManager

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
    headers = [u'id', u'name']
    
    class Meta:
        label = 'openstack.platform.images'
        aliases = ['images']
        aliases_only = True         
        description = "Openstack Image management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.image
        
class OpenstackPlatformFlavorController(OpenstackPlatformControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'openstack.platform.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Openstack Flavor management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.flavor
        
class OpenstackPlatformServerController(OpenstackPlatformControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'openstack.platform.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Openstack Server management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.server
        
class OpenstackPlatformVolumeController(OpenstackPlatformControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'openstack.platform.volumes'
        aliases = ['volumes']
        aliases_only = True         
        description = "Openstack Volume management"

    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.volume

class OpenstackPlatformHeatStackController(OpenstackPlatformControllerChild):
    headers = [u'id', u'project', u'stack_name', u'stack_owner', 
               u'stack_status', u'stack_name', u'creation_time']
    
    class Meta:
        label = 'openstack.platform.heat'
        aliases = ['heat']
        aliases_only = True         
        description = "Openstack Heat Stack management"
        
    def _ext_parse_args(self):
        OpenstackPlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.heat
        
    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(hide=True)
    def list(self):
        pass

    @expose(hide=True)
    def get(self):
        pass
    
    @expose(hide=True)
    def delete(self):
        pass      
        
    @expose(aliases=[u'stack-list [field=..]'], aliases_only=True)
    #@expose()
    def stack_list(self):
        """List heat stacks
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.stacks_list(**params)
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

    @expose(aliases=[u'stack-get <name> <oid>'], aliases_only=True)
    def get_stack(self):
        """Get heat stack by id
        """        
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.stacks_details(name, oid)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)
        
    @expose(aliases=[u'stack-preview <name>'], aliases_only=True)
    def stack_preview(self):
        """Get heat stack preview
        """        
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        obj = self.entity_class.stacks_preview(name, **params)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)        
    
    @expose(aliases=[u'stack-create <name> ..'], aliases_only=True)
    def stack_create(self):
        """Create heat stacks
        """
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.stacks_create(name, **params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=self.headers)    
    
    @expose(aliases=[u'stack-update <name> <oid> ..'], aliases_only=True)
    def stack_update(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stacks_update(name, oid, **params)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'stack-update-preview <name> <oid> ..'], aliases_only=True)
    def stack_update_preview(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stacks_update_preview(name, oid, **params)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'stack-delete <name> <oid>'], aliases_only=True)
    def stack_delete(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.stacks_delete(name, oid)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

openstack_platform_controller_handlers = [
    OpenstackPlatformController,
    OpenstackPlatformProjectController,
    OpenstackPlatformNetworkController,
    OpenstackPlatformSubnetController,
    OpenstackPlatformPortController,
    OpenstackPlatformFloatingIpController,
    OpenstackPlatformRouterController,
    OpenstackPlatformSecurityGroupController,
    OpenstackPlatformImageController,
    OpenstackPlatformFlavorController,
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

class OpenstackControllerChild(ApiController):
    uri = u'/v1.0/openstacks'
    subsystem = u'resource'
    
    class Meta:
        stacked_on = 'openstack'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*')),            
            ( ['-O', '--orchestrator'],
              dict(action='store', help='Openstack orchestrator id') ),
        ]

    def _ext_parse_args(self):
        ApiController._ext_parse_args(self)
        
        self.cid = self.app.pargs.orchestrator
        if self.cid is None:
            raise Exception(u'Orchestrator id must be specified')  

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri % self.cid
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, other_headers=self.headers, key=self._meta.aliases[0])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self, oid):
        oid = self.get_arg(name=u'id')
        uri = self.uri % self.cid + u'/' + oid
        res = self._call(uri, u'GET')
        self.logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, other_headers=self.headers, key=self._meta.aliases[0])
    
    @expose(aliases=[u'add <file data>'], aliases_only=True)
    def add(self, data):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri % self.cid
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))     
        self.result(res)

    @expose(aliases=[u'update <id> <file data>'], aliases_only=True)
    def update(self, oid, *args):
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri % self.cid + u'/' + oid
        res = self._call(uri, u'UPDATE', data=data)
        self.logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))     
        self.result(res)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    def delete(self, oid):
        oid = self.get_arg(name=u'id')
        uri = self.uri % self.cid + u'/' + oid
        res = self._call(uri, u'DELETE')
        self.logger.info(u'Delete %s: %s' % (self._meta.aliases[0], oid))     
        self.result(res)
        
class OpenstackProjectController(OpenstackControllerChild):
    uri = u'/v1.0/openstacks/%s/projects'
    headers = [u'id', u'parent_id', u'domain_id', u'name', u'enabled']
    
    class Meta:
        label = 'openstack.beehive.projects'
        aliases = ['projects']
        aliases_only = True        
        description = "Openstack Project management"

class OpenstackNetworkController(OpenstackControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'provider:segmentation_id', 
               u'router:external', u'shared', u'provider:network_type']
    
    class Meta:
        label = 'openstack.beehive.networks'
        aliases = ['networks']
        aliases_only = True
        description = "Openstack Network management"

class OpenstackSubnetController(OpenstackControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'subnet_id', u'cidr', 
               u'enable_dhcp']
    
    class Meta:
        label = 'openstack.beehive.subnets'
        aliases = ['subnets']
        aliases_only = True         
        description = "Openstack Subnet management"
        
class OpenstackPortController(OpenstackControllerChild):
    headers = [u'id', u'tenant_id', u'port_id', u'security_groups', 
               u'mac_address', u'status', u'device_owner']
    
    class Meta:
        label = 'openstack.beehive.ports'
        aliases = ['ports']
        aliases_only = True         
        description = "Openstack Port management"     
        
class OpenstackFloatingIpController(OpenstackControllerChild):
    headers = [u'id', u'tenant_id', u'status', u'floating_ip_address',
               u'fixed_ip_address']
    
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
    headers = [u'id', u'tenant_id', u'name', u'ha', u'status']
    
    class Meta:
        label = 'openstack.beehive.routers'
        aliases = ['routers']
        aliases_only = True         
        description = "Openstack Router management"
        
class OpenstackSecurityGroupController(OpenstackControllerChild):
    headers = [u'id', u'tenant_id', u'name']
    
    class Meta:
        label = 'openstack.beehive.security_groups'
        aliases = ['security_groups']
        aliases_only = True         
        description = "Openstack SecurityGroup management"           
        
class OpenstackImageController(OpenstackControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'openstack.beehive.images'
        aliases = ['images']
        aliases_only = True         
        description = "Openstack Image management"
        
class OpenstackFlavorController(OpenstackControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'openstack.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Openstack Flavor management"
        
class OpenstackServerController(OpenstackControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'openstack.beehive.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Openstack Server management"
        
class OpenstackVolumeController(OpenstackControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'openstack.beehive.volumes'
        aliases = ['volumes']
        aliases_only = True         
        description = "Openstack Volume management"

class OpenstackHeatStackController(OpenstackControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'openstack.beehive.heat'
        aliases = ['heat']
        aliases_only = True         
        description = "Openstack Heat Stack management"
        
    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

    @expose(hide=True)
    def list(self):
        pass

    @expose(hide=True)
    def get(self):
        pass
    
    @expose(hide=True)
    def delete(self):
        pass      
        
    @expose(aliases=[u'stack-list [field=..]'], aliases_only=True)
    #@expose()
    def stack_list(self):
        """List heat stacks
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.stacks_list(**params)
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

    @expose(aliases=[u'stack-get <name> <oid>'], aliases_only=True)
    def get_stack(self):
        """Get heat stack by id
        """        
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.stacks_details(name, oid)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)
        
    @expose(aliases=[u'stack-preview <name>'], aliases_only=True)
    def stack_preview(self):
        """Get heat stack preview
        """        
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        obj = self.entity_class.stacks_preview(name, **params)
        #res = self.entity_class.data(obj)
        res = obj
        logger.info(res)
        self.result(res, details=True)        
    
    @expose(aliases=[u'stack-create <name> ..'], aliases_only=True)
    def stack_create(self):
        """Create heat stacks
        """
        name = self.get_arg(name=u'name')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.stacks_create(name, **params)
        res = []
        for obj in objs:
            res.append(obj)
        logger.info(res)
        self.result(res, headers=self.headers)    
    
    @expose(aliases=[u'stack-update <name> <oid> ..'], aliases_only=True)
    def stack_update(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stacks_update(name, oid, **params)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])
        
    @expose(aliases=[u'stack-update-preview <name> <oid> ..'], aliases_only=True)
    def stack_update_preview(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        res = self.entity_class.stacks_update_preview(name, oid, **params)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'stack-delete <name> <oid>'], aliases_only=True)
    def stack_delete(self):
        name = self.get_arg(name=u'name')
        oid = self.get_arg(name=u'id')
        res = self.entity_class.stacks_delete(name, oid)
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])      
        
openstack_controller_handlers = [
    OpenstackController,
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
    OpenstackHeatStackController
]
