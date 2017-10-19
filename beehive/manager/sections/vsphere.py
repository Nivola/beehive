'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from time import sleep
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate
from beedrones.vsphere.client import VsphereManager
from pyVmomi import vim
from beecell.remote import RemoteClient

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

class VspherePlatformDatacenterController(VspherePlatformControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'vsphere.platform.datacenters'
        aliases = ['datacenters']
        aliases_only = True        
        description = "Vsphere Datacenter management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.datacenter
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'name':o[u'name'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
class VspherePlatformClusterController(VspherePlatformControllerChild):
    headers = [u'id', u'name']
    
    class Meta:
        label = 'vsphere.platform.clusters'
        aliases = ['clusters']
        aliases_only = True        
        description = "Vsphere Cluster management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.cluster
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'name':o[u'name'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose(aliases=[u'host-list [field=value]'], aliases_only=True)
    def host_list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.host.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'name':o[u'name'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose(aliases=[u'respool-list [field=value]'], aliases_only=True)
    def respool_list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.resource_pool.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'name':o[u'name'],
            })
        logger.info(res)
        self.result(res, headers=self.headers) 

class VspherePlatformDatastoreController(VspherePlatformControllerChild):
    headers = [u'id', u'name', u'overallStatus', u'accessible',
                 u'capacity', u'url', 
                 u'freeSpace', u'maxFileSize',
                 u'maintenanceMode', u'type']
    
    class Meta:
        label = 'vsphere.platform.datastores'
        aliases = ['datastores']
        aliases_only = True        
        description = "Vsphere Datastore management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.datastore
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'name':o[u'name'],
                u'overallStatus':o[u'overallStatus'],
                u'accessible':o[u'summary.accessible'],
                u'capacity':o[u'summary.capacity'],
                u'url':o[u'summary.url'], 
                u'freeSpace':o[u'summary.freeSpace'],
                u'maxFileSize':o[u'info.maxFileSize'],
                u'maintenanceMode':o[u'summary.maintenanceMode'],
                u'type':o[u'summary.type']    
            })
        logger.info(res)
        self.result(res, headers=self.headers)

class VspherePlatformFolderController(VspherePlatformControllerChild):
    headers = [u'id', u'parent', u'name', u'overallStatus']
    
    class Meta:
        label = 'vsphere.platform.folders'
        aliases = ['folders']
        aliases_only = True        
        description = "Vsphere Folder management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.folder
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'parent':o[u'parent']._moId,
                u'name':o[u'name'],
                u'overallStatus':o[u'overallStatus'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
class VspherePlatformVappController(VspherePlatformControllerChild):
    headers = [u'id', u'parent', u'name', u'overallStatus']
    
    class Meta:
        label = 'vsphere.platform.vapps'
        aliases = ['vapps']
        aliases_only = True        
        description = "Vsphere Vapp management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.vapp
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id':o[u'obj']._moId,
                u'parent':o[u'parent']._moId,
                u'name':o[u'name'],
                u'overallStatus':o[u'overallStatus'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)         

class VspherePlatformNetworkController(BaseController):
    class Meta:
        stacked_on = 'vsphere.platform'
        stacked_type = 'nested'
        label = 'vsphere.platform.network'
        aliases = ['network']
        aliases_only = True
        description = "Vsphere Network management"

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

class VspherePlatformNetworkChildController(VspherePlatformControllerChild):
    class Meta:
        stacked_on = 'vsphere.platform.network'
        stacked_type = 'nested'

    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network

class VspherePlatformNetworkDvsController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.dvs'
        aliases = ['dvss']
        aliases_only = True
        description = "Vsphere Network Dvs management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list_distributed_virtual_switches()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_distributed_virtual_switch(obj))        
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get_distributed_virtual_switch(oid)
        res = self.entity_class.detail_distributed_virtual_switch(res)
        logger.info(res)
        self.result(res, details=True)
        
class VspherePlatformNetworkDvpController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.dvpg'
        aliases = ['dvpgs']
        aliases_only = True
        description = "Vsphere Network Dvpg management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list_networks()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_network(obj))        
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get_network(oid)
        res = self.entity_class.detail_network(network)
        logger.info(res)
        self.result(res, details=True)

class VspherePlatformNetworkSecurityGroupController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.sg'
        aliases = ['sgs']
        aliases_only = True
        description = "Vsphere Network Security group management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.sg
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        rules = res.pop(u'member')
        self.result(res, details=True)
        print(u'Members:')
        self.result(rules, headers=[u'objectId', u'name', 
                                           u'objectTypeName'])
    
    @expose(aliases=[u'delete-member <id>'], aliases_only=True)
    def delete_member(self):
        oid = self.get_arg(name=u'id')
        member = self.get_arg(name=u'member')
        res = self.entity_class.delete_member(oid, member)
        logger.info(res)
        res = {u'msg':u'Delete security-group %s member %s' % (oid, member)}
        self.result(res, headers=[u'msg'])        
        
class VspherePlatformNetworkDfwController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.dfw'
        aliases = ['dfw']
        aliases_only = True
        description = "Vsphere Network Nsx Distributed Firewall management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.dfw   
        
    def __print_sections(self, data, stype):
        sections = data[stype][u'section']
        if type(sections) is not list: sections = [sections]
        for s in sections:
            rules = s.get(u'rule', [])
            if type(rules) is not list: rules = [rules]
            s[u'rules'] = len(rules)
        self.result(sections, headers=[u'id', u'type', u'timestamp', 
                                              u'generationNumber', u'name',
                                              u'rules'])

    def __set_rule_value(self, key, subkey, res):
        objs = res.pop(key, {}).pop(subkey, None)
        if objs is None:
            res[key] = u''  
        else: 
            res[key] = u'..'
        return res

    def __print_rule_datail(self, title, data):
        print(title)
        if type(data) is not list: data = [data]
        self.result(data, headers=[u'type', u'name', u'value'])  
    
    @expose()
    def sections(self):
        res = self.entity_class.get_config()
        
        data = [{u'key':u'contextId', u'value':res[u'contextId']},
                {u'key':u'timestamp', u'value':res[u'timestamp']},
                {u'key':u'generationNumber', u'value':res[u'generationNumber']}]
        self.result(data, headers=[u'key', u'value'])
        
        print(u'layer3Sections')
        self.__print_sections(res, u'layer3Sections')
        print(u'layer2Sections')
        self.__print_sections(res, u'layer2Sections')     
        print(u'layer3RedirectSections')
        self.__print_sections(res, u'layer3RedirectSections')      

    @expose(aliases=[u'rules <section> [rule]'], aliases_only=True)
    def rules(self):
        section = self.get_arg(name=u'section')
        rule = self.get_arg(default=None)
        if rule is None:
            res = self.entity_class.get_layer3_section(sectionid=section)
            
            rules = res.pop(u'rule', [])
            self.result([res], headers=[u'id', u'type', u'timestamp', 
                                               u'generationNumber', u'name'])
            
            print(u'Rules:')
            for r in rules:
                r = self.__set_rule_value(u'services', u'service', r)
                r = self.__set_rule_value(u'sources', u'source', r)
                r = self.__set_rule_value(u'destinations', u'destination', r)
                r = self.__set_rule_value(u'appliedToList', u'appliedTo', r)
            self.result(rules, headers=[u'id', u'disabled', u'logged', 
                                               u'name', u'direction', u'action', 
                                               u'packetType', u'sources', 
                                               u'destinations', u'services',
                                               u'appliedToList'])
        else:
            res = self.entity_class.get_rule(section, rule)
            #self.result(res, details=True)
            services = res.pop(u'services', {}).pop(u'service', [])
            sources = res.pop(u'sources', {}).pop(u'source', [])
            destinations = res.pop(u'destinations', {}).pop(u'destination', [])
            appliedToList = res.pop(u'appliedToList', {}).pop(u'appliedTo', [])
            
            self.result(res, headers=[u'id', u'disabled', u'logged', 
                                               u'name', u'direction', u'action', 
                                               u'packetType'])
            
            self.__print_rule_datail(u'sources', sources)
            self.__print_rule_datail(u'destinations', destinations)
            self.__print_rule_datail(u'appliedTo', appliedToList)
            print(u'services')
            if type(services) is not list: services = [services]
            self.result(services, headers=[u'protocol', u'subProtocol', 
                                                  u'destinationPort', 
                                                  u'protocolName']) 

    @expose(aliases=[u'section-delete <section>'], aliases_only=True)
    def section_delete(self):
        section = self.get_arg(name=u'section')
        res = self.entity_class.delete_section(section)
        logger.info(res)
        res = {u'msg':u'Delete section %s' % (section)}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'rule-delete <section> <rule>'], aliases_only=True)
    def rule_delete(self, section, rule):
        section = self.get_arg(name=u'section')
        rule = self.get_arg(name=u'rule')
        res = self.entity_class.delete_rule(section, rule)
        logger.info(res)
        res = {u'msg':u'Delete section %s rule %s' % (section, rule)}
        self.result(res, headers=[u'msg'])
    
    @expose()
    def exclusions(self):
        res = self.entity_class.get_exclusion_list()
        res = res.get(u'excludeMember', [])
        resp = []
        for item in res:
            resp.append(item[u'member'])
        logger.info(res)
        self.result(resp, headers=[u'objectId', u'name', u'scope.name',
                                          u'objectTypeName', u'revision'])        
        
class VspherePlatformNetworkLgController(VspherePlatformNetworkChildController):
    headers = [u'objectId', u'name']
    
    class Meta:
        label = 'vsphere.platform.networks.lg'
        aliases = ['lgs']
        aliases_only = True
        description = "Vsphere Network Nsx Logical Switch management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.lg
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)     
        
class VspherePlatformNetworkIpsetController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.ipset'
        aliases = ['ipsets']
        aliases_only = True
        description = "Vsphere Network Nsx Ipset management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.ipset
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name', u'value'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)           
        
class VspherePlatformNetworkEdgeController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.edge'
        aliases = ['edges']
        aliases_only = True
        description = "Vsphere Network Nsx Edge management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.edge
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)        
        
class VspherePlatformNetworkDlrController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.networks.dlr'
        aliases = ['dlrs']
        aliases_only = True
        description = "Vsphere Network Nsx Dlr management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.dlr
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name', u'value'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)

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
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        volumes = res.pop(u'volumes')
        networks = res.pop(u'networks')
        self.result(res, details=True)
        print(u'Networks')
        self.result(networks, headers=[u'name', u'mac_addr', u'dns', 
                                       u'fixed_ips', u'net_id', u'port_state'])
        print(u'Volumes')
        self.result(volumes, headers=[u'id', u'name', u'storage', u'size', 
                                       u'type', u'bootable', u'format', u'mode'])

    @expose(aliases=[u'console <id>'], aliases_only=True)
    def console(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.remote_console(server)
        self.result(res, delta=60, details=True)
  
    @expose(aliases=[u'guest-info <id>'], aliases_only=True)
    def guest_info(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        #data = self.entity_class.hardware.get_original_devices(server, 
        #                    dev_type=u'vim.vm.device.VirtualVmxnet3')[0].macAddress
        res = self.entity_class.guest_info(server)
        self.result(res, details=True)
    
    @expose(aliases=[u'ssh-copy-id <id> <user> <pwd> <pub-key>'], aliases_only=True)
    def ssh_copy_id(self, oid, pwd, ):
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        pwd = self.get_arg(name=u'pwd')
        pub_key = self.get_arg(name=u'pub-key')
        key = self.load_config(pub_key)
        #key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDpN36RMjBNpQ9lTvbdMjbkU6OyytX78RXKiVNMBU07vBx6REwGWgytg+8rG1pqFAuo6U3lR1q25dpPDQtK8Dad68MPHFydfv0WAYOG6Y02j/pQKJDGPhbeSYS0XF4F/z4UxY6cXB8UdzkUSKtIg93YCTkzbQY6+APOY/K9q1b2ZxTEEBDQgWenZw4McmSbaS+AYwmigSJb5sFMexJRKZCdXESgQcSmUkQFiXRQNJMlgPZBnIcbGlu5UA9G5owLM6LT11bPQPrROqmhcSGoQtYq83RGNX5Kgwe00pqeo/G+SUtcQRp5JtWIE9bLeaXRIhZuInrbP0rmHyCQhBeZDCPr1mw2YDZV9Fbb08/qwbq1UYuUzRXxXroX1F7/mztyXQt7o4AjXWpeyBccR0nkAyZcanOvvJJvoIwLoDqbsZaqCldQJCvtb1WNX9ukce5ToW1y80Rcf1GZrrXRTs2cAbubUkxYQaLQQApVnGIJelR9BlvR7xsmfQ5Y5wodeLfEgqw2hNzJEeKKHs5xnpcgG9iXVvW1Tr0Gf+UsY0UIogZ6BCstfR59lPAt1IRaYVCvgHsHm4hmr0yMvUwGHroztrja50XHp9h0z/EWAt56nioOJcOTloAIpAI05z4Z985bYWgFk8j/1LkEDKH9buq5mHLwN69O7JPN8XaDxBq9xqSP9w== sergio.tonani@csi.it'
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_ssh_key(server, user, pwd, key)
        self.result(res)
    
    @expose(aliases=[u'ssh-change-pwd <id> <user> <pwd> <new-pwd>'], aliases_only=True)
    def ssh_change_pwd(self, oid, pwd, newpwd):
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        pwd = self.get_arg(name=u'pwd')
        newpwd = self.get_arg(name=u'new pwd')
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_admin_password(server, user, pwd, 
                                                           newpwd)
        self.result(res)        
    
    def setup_network(self, oid, pwd, data):
        oid = self.get_arg(name=u'id')
        data = self.load_config(data)
        ipaddr = data.get(u'ipaddr')
        macaddr = data.get(u'macaddr')
        gw = data.get(u'gw')
        hostname = data.get(u'name')
        dns = data.get(u'dns')
        dns_search = data.get(u'dns-search')
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_network(server, pwd, ipaddr, 
                    macaddr, gw, hostname, dns, dns_search, 
                    conn_name=u'net01', user=u'root')
        self.result(res)
    
    @expose(aliases=[u'ssh <id> <user> <pwd> <cmd>'], aliases_only=True)
    def ssh(self):
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        pwd = self.get_arg(name=u'pwd')
        cmd = self.get_arg(name=u'cmd')
        server = self.entity_class.get_by_morid(oid)
        data = self.entity_class.data(server)
        client = RemoteClient({u'host':data[u'networks'][0][u'fixed_ips'],
                               u'port':22})
        res = client.run_ssh_command(cmd, user, pwd)
        print(u'')
        if res.get(u'stderr') != u'':
            print(u'Error')
            print(res.get(u'stderr'))
        else:
            for row in res.get(u'stdout'):
                self.output(row, color=u'GREENonBLACK')
        print(u'')
    
    #
    # action
    #
    @expose(aliases=[u'start <id>'], aliases_only=True)
    def start(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.start(server)        
        self.wait_task(task)
    
    @expose(aliases=[u'stop <id>'], aliases_only=True)
    def stop(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.stop(server)        
        self.wait_task(task)

vsphere_platform_controller_handlers = [
    VspherePlatformController,
    VspherePlatformDatacenterController,
    VspherePlatformClusterController,
    VspherePlatformDatastoreController,
    VspherePlatformFolderController,
    VspherePlatformVappController,
    VspherePlatformNetworkController,
    VspherePlatformNetworkDvsController,
    VspherePlatformNetworkDvpController,
    VspherePlatformNetworkSecurityGroupController,
    VspherePlatformNetworkDfwController,
    VspherePlatformNetworkLgController,
    VspherePlatformNetworkIpsetController,
    VspherePlatformNetworkEdgeController,
    VspherePlatformNetworkDlrController,
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
