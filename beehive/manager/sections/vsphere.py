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
from beedrones.vsphere.client import VsphereManager
from pyVmomi import vim

logger = logging.getLogger(__name__)

#
# vsphere native platform
#
class VspherePlatformController(BaseController):
    class Meta:
        label = 'vsphere.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Vsphere Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Vsphere Platform management", hide=True)
    def default(self):
        self.app.args.print_help()

class VspherePlatformControllerChild(BaseController):
    headers = [u'id', u'name']
    entity_class = None
    
    class Meta:
        stacked_on = 'vsphere.platform'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*')),            
            ( ['-O', '--orchestrator'],
              dict(action='store', help='Vsphere platform reference label') ),
        ]
        
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)
        
        orchestrators = self.configs.get(u'orchestrators').get(u'vsphere')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Vsphere platform label must be specified. '\
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)
            
        self.client = VsphereManager(conf.get(u'vcenter'), conf.get(u'nsx'))

    def wait_task(self, task):
        while task.info.state not in [vim.TaskInfo.State.success,
                                      vim.TaskInfo.State.error]:
            logger.info(task.info.state)
            print(u'*')
            sleep(1)
            
        if task.info.state in [vim.TaskInfo.State.error]:
            logger.error(task.info.error.msg)
        if task.info.state in [vim.TaskInfo.State.success]:
            logger.info(u'Completed')

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
        res = {u'msg':u'Delete %s %s' % (oid, self.name)}
        logger.info(res)
        self.result(res, headers=[u'msg'])

class VspherePlatformDatacenterController(VspherePlatformControllerChild):
    headers = [u'obj', u'name']
    
    class Meta:
        label = 'vsphere.platform.datacenters'
        aliases = ['datacenters']
        aliases_only = True        
        description = "Vsphere Datacenter management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.datacenter

class VspherePlatformFolderController(VspherePlatformControllerChild):
    headers = [u'obj', u'parent', u'name', u'overallStatus']
    
    class Meta:
        label = 'vsphere.platform.folders'
        aliases = ['folders']
        aliases_only = True        
        description = "Vsphere Folder management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.folder

class VspherePlatformNetworkController(VspherePlatformControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'provider:segmentation_id', 
               u'router:external', u'shared', u'provider:network_type']
    
    class Meta:
        label = 'vsphere.platform.networks'
        aliases = ['networks']
        aliases_only = True
        description = "Vsphere Network management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network

class VspherePlatformSecurityGroupController(VspherePlatformControllerChild):
    headers = [u'id', u'name', u'os', u'memory', u'cpu', u'state', u'template', 
               u'hostname', u'ip_address', u'disk']
    
    class Meta:
        label = 'vsphere.platform.security_groups'
        aliases = ['security_groups']
        aliases_only = True         
        description = "Vsphere SecurityGroup management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.security_group             
        
class VspherePlatformServerController(VspherePlatformControllerChild):
    headers = [u'id', u'parent', u'name', u'os', u'state', u'ip', u'hostname',
               u'cpu', u'ram', u'template']
    
    class Meta:
        label = 'vsphere.platform.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Vsphere Server management"

    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.server
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId, 
                u'parent':o[u'parent']._moId, 
                u'name':truncate(o[u'name'], 30),
                u'os':o[u'config.guestFullName'],
                u'state':o[u'runtime.powerState'],
                u'ip':o.get(u'guest.ipAddress', u''),
                u'hostname':o.get(u'guest.hostName', u''),
                u'cpu':o[u'config.hardware.numCPU'],
                u'ram':o[u'config.hardware.memoryMB'],
                u'template':o[u'config.template']
            })
        logger.info(res)
        self.result(res, headers=self.headers)        
        
class VspherePlatformHeatStackController(VspherePlatformControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'vsphere.platform.heat'
        aliases = ['heat']
        aliases_only = True         
        description = "Vsphere Heat Stack management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
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

vsphere_platform_controller_handlers = [
    VspherePlatformController,
    VspherePlatformDatacenterController,
    VspherePlatformFolderController,
    VspherePlatformNetworkController,
    VspherePlatformServerController,
]

#
# vsphere orchestrator
#
class VsphereController(BaseController):
    class Meta:
        label = 'vsphere'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Beehive Vsphere Orchestrator Wrapper management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Beehive Vsphere Orchestrator Wrapper management", hide=True)
    def default(self):
        self.app.args.print_help()

class VsphereControllerChild(ApiController):
    uri = u'/v1.0/vspheres'
    subsystem = u'resource'
    
    class Meta:
        stacked_on = 'vsphere'
        stacked_type = 'nested'
        arguments = [
            ( ['extra_arguments'], dict(action='store', nargs='*')),            
            ( ['-O', '--orchestrator'],
              dict(action='store', help='Vsphere orchestrator id') ),
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
        
class VsphereFolderController(VsphereControllerChild):
    uri = u'/v1.0/vspheres/%s/folders'
    headers = [u'id', u'parent_id', u'domain_id', u'name', u'enabled']
    
    class Meta:
        label = 'vsphere.beehive.folders'
        aliases = ['folders']
        aliases_only = True        
        description = "Vsphere Folder management"

class VsphereNetworkController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'provider:segmentation_id', 
               u'router:external', u'shared', u'provider:network_type']
    
    class Meta:
        label = 'vsphere.beehive.networks'
        aliases = ['networks']
        aliases_only = True
        description = "Vsphere Network management"

class VsphereSubnetController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'subnet_id', u'cidr', 
               u'enable_dhcp']
    
    class Meta:
        label = 'vsphere.beehive.subnets'
        aliases = ['subnets']
        aliases_only = True         
        description = "Vsphere Subnet management"
        
class VspherePortController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'port_id', u'security_groups', 
               u'mac_address', u'status', u'device_owner']
    
    class Meta:
        label = 'vsphere.beehive.ports'
        aliases = ['ports']
        aliases_only = True         
        description = "Vsphere Port management"     
        
class VsphereFloatingIpController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'status', u'floating_ip_address',
               u'fixed_ip_address']
    
    class Meta:
        label = 'vsphere.beehive.floatingips'
        aliases = ['floatingips']
        aliases_only = True         
        description = "Vsphere FloatingIp management"
        
    @check_error
    def _ext_parse_args(self):
        VsphereControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.ip
       
class VsphereRouterController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'name', u'ha', u'status']
    
    class Meta:
        label = 'vsphere.beehive.routers'
        aliases = ['routers']
        aliases_only = True         
        description = "Vsphere Router management"
        
class VsphereSecurityGroupController(VsphereControllerChild):
    headers = [u'id', u'tenant_id', u'name']
    
    class Meta:
        label = 'vsphere.beehive.security_groups'
        aliases = ['security_groups']
        aliases_only = True         
        description = "Vsphere SecurityGroup management"           
        
class VsphereImageController(VsphereControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'vsphere.beehive.images'
        aliases = ['images']
        aliases_only = True         
        description = "Vsphere Image management"
        
class VsphereFlavorController(VsphereControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'vsphere.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True         
        description = "Vsphere Flavor management"
        
class VsphereServerController(VsphereControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'vsphere.beehive.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Vsphere Server management"
        
class VsphereVolumeController(VsphereControllerChild):
    headers = [u'id', u'parent_id', u'name']
    
    class Meta:
        label = 'vsphere.beehive.volumes'
        aliases = ['volumes']
        aliases_only = True         
        description = "Vsphere Volume management"

vsphere_controller_handlers = [
    VsphereController,
    VsphereFolderController,
    VsphereNetworkController,
    VsphereSubnetController,
    VspherePortController,
    VsphereFloatingIpController,
    VsphereRouterController,
    VsphereSecurityGroupController,
    VsphereImageController,
    VsphereFlavorController,
    VsphereServerController,
    VsphereVolumeController
]
