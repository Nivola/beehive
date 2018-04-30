"""
Created on Sep 27, 2017

@author: darkbk
"""
import json
import logging
from base64 import b64encode
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
        label = 'vsphere_platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Vsphere Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class VspherePlatformControllerChild(BaseController):
    headers = [u'id', u'name']
    entity_class = None
    
    class Meta:
        stacked_on = 'vsphere_platform'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-O', '--orchestrator'], dict(action='store', help='Vsphere platform reference label')),
        ]

    @check_error
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)
        
        orchestrators = self.configs[u'environments'][self.env][u'orchestrators'].get(u'vsphere')
        label = self.app.pargs.orchestrator
        if label is None:
            label = orchestrators.keys()[0]
            # raise Exception(u'Vsphere platform label must be specified. Valid label are: %s' %
            #                 u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)
        
        self.client = VsphereManager(conf.get(u'vcenter'), conf.get(u'nsx'), key=self.key)

    def wait_task(self, task):
        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            logger.info(task.info.state)
            print(u'*')
            sleep(1)
            
        if task.info.state in [vim.TaskInfo.State.error]:
            logger.error(task.info.error.msg)
            self.app.print_error(task.info.error.msg)
        if task.info.state in [vim.TaskInfo.State.success]:
            logger.info(u'Completed')
            self.app.print_output(u'Completed')


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
    @check_error
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id': o[u'obj']._moId,
                u'name': o[u'name'],
            })
        logger.info(res)
        self.result(res, headers=self.headers)


class VspherePlatformClusterController(VspherePlatformControllerChild):
    headers = [u'id', u'name', u'parent']
    
    class Meta:
        label = 'vsphere.platform.clusters'
        aliases = ['clusters']
        aliases_only = True        
        description = "Vsphere Cluster management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.cluster
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id': o[u'obj']._moId,
                u'name': o[u'name'],
                u'parent': o[u'parent']._moId
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose(aliases=[u'host-list [field=value]'], aliases_only=True)
    @check_error
    def host_list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.host.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id': o[u'obj']._moId,
                u'name': o[u'name'],
                u'parent': o[u'parent']._moId
            })
        logger.info(res)
        self.result(res, headers=self.headers)
        
    @expose(aliases=[u'respool-list [field=value]'], aliases_only=True)
    @check_error
    def respool_list(self):
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.resource_pool.list(**params)
        res = []
        for o in objs:
            print o[u'parent']._moId
            res.append({
                u'id': o[u'obj']._moId,
                u'name': o[u'name'],
                u'parent': o[u'parent']._moId
            })
        logger.info(res)
        self.result(res, headers=self.headers)

    @expose(aliases=[u'servers <cluster_id>'], aliases_only=True)
    @check_error
    def servers(self):
        cluster_id = self.get_arg(name=u'cluster_id')
        objs = self.entity_class.get_servers(cluster_id)
        res = []
        for o in objs:
            res.append(self.entity_class.info(o))
        headers = [u'id', u'parent', u'name', u'os', u'state', u'ip_address', u'hostname', u'cpu', u'ram', u'template']
        logger.info(res)
        self.result(res, headers=headers)


class VspherePlatformDatastoreController(VspherePlatformControllerChild):
    headers = [u'id', u'name', u'overallStatus', u'accessible', u'capacity', u'url', u'freeSpace', u'maxFileSize',
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
    @check_error
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
                u'capacity':float(o[u'summary.capacity'])/1073741824,
                u'url':o[u'summary.url'], 
                u'freeSpace':float(o[u'summary.freeSpace'])/1073741824,
                u'maxFileSize':float(o[u'info.maxFileSize'])/1073741824,
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
    @check_error
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
    @check_error
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
        stacked_on = 'vsphere_platform'
        stacked_type = 'nested'
        label = 'vsphere.platform.network'
        aliases = ['network']
        aliases_only = True
        description = "Vsphere Network management"


class VspherePlatformNetworkChildController(VspherePlatformControllerChild):
    class Meta:
        stacked_on = 'vsphere.platform.network'
        stacked_type = 'nested'

    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network


class VspherePlatformNetworkDvsController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.dvs'
        aliases = ['dvss']
        aliases_only = True
        description = "Vsphere Network Dvs management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list_distributed_virtual_switches()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_distributed_virtual_switch(obj))        
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get_distributed_virtual_switch(oid)
        res = self.entity_class.detail_distributed_virtual_switch(res)
        logger.info(res)
        self.result(res, details=True)


class VspherePlatformNetworkDvpController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.dvpg'
        aliases = ['dvpgs']
        aliases_only = True
        description = "Vsphere Network Dvpg management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list_networks()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_network(obj))        
        logger.info(res)
        self.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get_network(oid)
        res = self.entity_class.detail_network(network)
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        obj = self.entity_class.get_network(oid)
        task = self.entity_class.remove_network(obj)
        self.wait_task(task)
        res = {u'msg':u'Delete dvpg %s' % (oid)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'servers <id>'], aliases_only=True)
    @check_error
    def servers(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get_network_servers(oid)
        logger.info(res)
        servers = []
        for item in res:
            servers.append(self.client.server.info(item))
        headers = [u'id', u'parent', u'name', u'os', u'state', u'ip_address', u'hostname', u'cpu', u'ram', u'template']
        self.result(servers, headers=headers)


class VspherePlatformNetworkSecurityGroupController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.sg'
        aliases = ['sgs']
        aliases_only = True
        description = "Vsphere Network Security group management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.sg
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name'], maxsize=200)
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.get(oid)
        print res
        members = res.pop(u'member', [])
        self.result(res, details=True)
        print(u'Members:')
        self.result(members, headers=[u'objectId', u'name', u'objectTypeName'])
    
    @expose(aliases=[u'delete <id> [force=false]'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        force = self.get_arg(name=u'force', keyvalue=True, default=False)
        res = self.entity_class.delete(oid, force)
        res = {u'msg': u'Delete security-group %s' % (oid)}
        self.result(res, headers=[u'msg'])    
    
    @expose(aliases=[u'del-member <id> <member>'], aliases_only=True)
    @check_error
    def del_member(self):
        oid = self.get_arg(name=u'id')
        member = self.get_arg(name=u'member')
        res = self.entity_class.delete_member(oid, member)
        logger.info(res)
        res = {u'msg': u'Delete security-group %s member %s' % (oid, member)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-member <id> <member>'], aliases_only=True)
    @check_error
    def add_member(self):
        oid = self.get_arg(name=u'id')
        member = self.get_arg(name=u'member')
        res = self.entity_class.add_member(oid, member)
        logger.info(res)
        res = {u'msg': u'Add security-group %s member %s' % (oid, member)}
        self.result(res, headers=[u'msg'])


class VspherePlatformNetworkDfwController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.dfw'
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
    @check_error
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
    @check_error
    def rules(self):
        section = self.get_arg(name=u'section')
        rule = self.get_arg(default=None)
        if rule is None:
            res = self.entity_class.get_layer3_section(sectionid=section)
            
            rules = res.pop(u'rule', [])
            if isinstance(rules, dict):
                rules = [rules]
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
            self.result(services, headers=[u'protocol', u'subProtocol', u'destinationPort', u'protocolName'])

    @expose(aliases=[u'section-delete <section>'], aliases_only=True)
    @check_error
    def section_delete(self):
        section = self.get_arg(name=u'section')
        res = self.entity_class.delete_section(section)
        logger.info(res)
        res = {u'msg':u'Delete section %s' % (section)}
        self.result(res, headers=[u'msg'])
    
    @expose(aliases=[u'rule-delete <section> <rule>'], aliases_only=True)
    @check_error
    def rule_delete(self, section, rule):
        section = self.get_arg(name=u'section')
        rule = self.get_arg(name=u'rule')
        res = self.entity_class.delete_rule(section, rule)
        logger.info(res)
        res = {u'msg':u'Delete section %s rule %s' % (section, rule)}
        self.result(res, headers=[u'msg'])
    
    @expose()
    @check_error
    def exclusions(self):
        res = self.entity_class.get_exclusion_list()
        res = res.get(u'excludeMember', [])
        resp = []
        for item in res:
            resp.append(item[u'member'])
        logger.info(res)
        self.result(resp, headers=[u'objectId', u'name', u'scope.name', u'objectTypeName', u'revision'])


class VspherePlatformNetworkLgController(VspherePlatformNetworkChildController):
    headers = [u'objectId', u'name']
    
    class Meta:
        label = 'vsphere.platform.network.lg'
        aliases = ['lgs']
        aliases_only = True
        description = "Vsphere Network Nsx Logical Switch management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.lg
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)


class VspherePlatformNetworkIppoolController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.ippool'
        aliases = ['ippools']
        aliases_only = True
        description = "Vsphere Network Nsx Ippool management"

    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)

        self.entity_class = self.client.network.nsx.ippool

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))
        logger.info(res)
        headers = [u'objectId', u'name', u'dnsSuffix', u'gateway', u'startAddress',
                   u'endAddress', u'totalAddressCount', u'usedAddressCount']
        fields = [u'objectId', u'name', u'dnsSuffix', u'gateway', u'ipRanges.ipRangeDto.startAddress',
                  u'ipRanges.ipRangeDto.endAddress', u'totalAddressCount', u'usedAddressCount']
        self.result(res, headers=headers, fields=fields)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'add <name> <startip> <stopip> <gw> <dns1> <dns2> [prefix=24] [dnssuffix=domain.local]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Add new ippool
        """
        name = self.get_arg(name=u'name')
        startip = self.get_arg(name=u'startip')
        stopip = self.get_arg(name=u'stopip')
        gw = self.get_arg(name=u'gw')
        dns1 = self.get_arg(name=u'dns1')
        dns2 = self.get_arg(name=u'dns2')
        prefix = self.get_arg(name=u'prefix', keyvalue=True, default=24)
        dnssuffix = self.get_arg(name=u'dnssuffix', keyvalue=True, default=u'domain.local')
        res = self.entity_class.create(name, prefix=prefix, gateway=gw, dnssuffix=dnssuffix, dns1=dns1, dns2=dns2,
                                       startip=startip, stopip=stopip)
        res = {u'msg': u'Add ipset %s' % name}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'update <ippool> [field=..]'],
            aliases_only=True)
    @check_error
    def update(self):
        """Update ippool
    - field: name, startip, stopip gw dns1, dns2, prefix, dnssuffix
        """
        oid = self.get_arg(name=u'ippool id')
        name = self.get_arg(name=u'name', keyvalue=True, default=None)
        startip = self.get_arg(name=u'startip', keyvalue=True, default=None)
        stopip = self.get_arg(name=u'stopip', keyvalue=True, default=None)
        gw = self.get_arg(name=u'gw', keyvalue=True, default=None)
        dns1 = self.get_arg(name=u'dns1', keyvalue=True, default=None)
        dns2 = self.get_arg(name=u'dns2', keyvalue=True, default=None)
        prefix = self.get_arg(name=u'prefix', keyvalue=True, default=None)
        dnssuffix = self.get_arg(name=u'dnssuffix', keyvalue=True, default=None)
        res = self.entity_class.update(oid, name=name, prefix=prefix, gateway=gw, dnssuffix=dnssuffix, dns1=dns1,
                                       dns2=dns2, startip=startip, stopip=stopip)
        res = {u'msg': u'Update ipset %s' % name}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg': u'Delete ipset %s' % (oid)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'ip-allocated <id>'], aliases_only=True)
    @check_error
    def ip_allocated(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.allocations(oid)
        logger.info(res)
        headers = [u'id', u'ipAddress', u'gateway', u'dnsSuffix', u'prefixLength', u'subnetId', u'dnsServer1',
                   u'dnsServer2']
        self.result(res, headers=headers)

    @expose(aliases=[u'ip-allocate <id> [ip=..]'], aliases_only=True)
    @check_error
    def ip_allocate(self):
        oid = self.get_arg(name=u'id')
        ip = self.get_arg(name=u'ip', default=None, keyvalue=True)
        res = self.entity_class.allocate(oid, static_ip=ip)
        logger.info(res)
        self.result(res, details=True)

    @expose(aliases=[u'ip-release <id> <ip>'], aliases_only=True)
    @check_error
    def ip_release(self):
        oid = self.get_arg(name=u'id')
        ip = self.get_arg(name=u'ip')
        res = self.entity_class.release(oid, ip)
        logger.info(res)
        self.result(res, details=True)


class VspherePlatformNetworkIpsetController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.ipset'
        aliases = ['ipsets']
        aliases_only = True
        description = "Vsphere Network Nsx Ipset management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.ipset
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name', u'value'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)
        
    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        res = {u'msg':u'Delete ipset %s' % (oid)}
        self.result(res, headers=[u'msg'])


class VspherePlatformNetworkEdgeController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.edge'
        aliases = ['edges']
        aliases_only = True
        description = "Vsphere Network Nsx Edge management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.edge
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        headers = [u'id', u'name', u'type', u'status', u'state', u'datacenter']
        fields = [u'objectId', u'name', u'edgeType', u'edgeStatus', u'state', u'datacenterName']
        self.result(res, headers=headers, fields=fields, maxsize=200)
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)        

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        res = self.entity_class.delete(oid)
        logger.info(res)
        self.result(res, details=True)


class VspherePlatformNetworkDlrController(VspherePlatformNetworkChildController):
    class Meta:
        label = 'vsphere.platform.network.dlr'
        aliases = ['dlrs']
        aliases_only = True
        description = "Vsphere Network Nsx Dlr management"
        
    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.network.nsx.dlr
        
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        objs = self.entity_class.list()
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))        
        logger.info(res)
        self.result(res, headers=[u'objectId', u'name', u'value'])
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        self.result(res, details=True)


class VspherePlatformServerController(VspherePlatformControllerChild):
    headers = [u'id', u'parent', u'name', u'os', u'state', u'ip_address', u'hostname',
               u'cpu', u'ram', u'disk', u'template']
    
    class Meta:
        label = 'vsphere.platform.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Vsphere Server management"

    def _ext_parse_args(self):
        VspherePlatformControllerChild._ext_parse_args(self)
        
        self.entity_class = self.client.server
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List servers
    - field can be: name, uuid, ipaddress, dnsname, morid, template
    - template=true list only template
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append(self.entity_class.info(o))
            '''{
                u'id':o[u'obj']._moId, 
                u'parent':o[u'parent']._moId, 
                u'name':truncate(o[u'name'], 30),
                u'os':o.get(u'config.guestFullName', None),
                u'state':o.get(u'runtime.powerState', None),
                u'ip':o.get(u'guest.ipAddress', u''),
                u'hostname':o.get(u'guest.hostName', u''),
                u'cpu':o.get(u'config.hardware.numCPU', None),
                u'ram':o.get(u'config.hardware.memoryMB', None),
                u'template':o.get(u'config.template', None)
            })'''
        logger.info(res)
        self.result(res, headers=self.headers, maxsize=30)
        
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        network = self.entity_class.get(oid)
        res = self.entity_class.detail(network)
        logger.info(res)
        volumes = res.pop(u'volumes')
        networks = res.pop(u'networks')
        self.result(res, details=True)
        print(u'Networks')
        self.result(networks, headers=[u'name', u'mac_addr', u'dns', u'fixed_ips', u'net_id', u'port_state'])
        print(u'Volumes')
        self.result(volumes, headers=[u'id', u'name', u'storage', u'size', u'type', u'bootable', u'format', u'mode'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.remove(server)        
        self.wait_task(task)

    @expose(aliases=[u'console <id>'], aliases_only=True)
    @check_error
    def console(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.remote_console(server)
        self.result(res, details=True)
  
    @expose(aliases=[u'guest-info <id>'], aliases_only=True)
    @check_error
    def guest_info(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        #data = self.entity_class.hardware.get_original_devices(server, 
        #                    dev_type=u'vim.vm.device.VirtualVmxnet3')[0].macAddress
        res = self.entity_class.guest_info(server)
        self.result(res, details=True)
    
    @expose(aliases=[u'ssh-copy-id <id> <user> <pwd> <pub-key>'], aliases_only=True)
    @check_error
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
    @check_error
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
    @check_error
    def ssh(self):
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        pwd = self.get_arg(name=u'pwd')
        cmd = self.get_arg(name=u'cmd')
        server = self.entity_class.get_by_morid(oid)
        data = self.entity_class.data(server)
        client = RemoteClient({u'host': data[u'networks'][0][u'fixed_ips'], u'port': 22})
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
    @check_error
    def start(self):
        oid = self.get_arg(name=u'id')
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.start(server)        
        self.wait_task(task)
    
    @expose(aliases=[u'stop <id>'], aliases_only=True)
    @check_error
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
    VspherePlatformNetworkIppoolController,
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


class VsphereControllerChild(ApiController):
    subsystem = u'resource'
    headers = [u'id', u'uuid', u'parent.name', u'container.name', u'name', u'state', u'ext_id']
    fields = None
    
    class Meta:
        stacked_on = 'vsphere'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def _ext_parse_args(self):
        ApiController._ext_parse_args(self)
    
    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        if self.fields is None:
            self.fields = self.headers
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.aliases[0], maxsize=100)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET')
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, key=self._meta.aliases[0][:-1], details=True)
    
    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        if u'jobid' in res:
            self.wait_job(res[u'jobid'])
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))     
        self.result(res)

    @expose(aliases=[u'update <id> <file data>'], aliases_only=True)
    @check_error
    def update(self):
        oid = self.get_arg(name=u'id')
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'UPDATE', data=data)
        if u'jobid' in res:
            self.wait_job(res[u'jobid'])
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))     
        self.result(res)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'DELETE')
        if u'jobid' in res:
            self.wait_job(res[u'jobid'])
        logger.info(u'Delete %s: %s' % (self._meta.aliases[0], oid))     
        self.result(res)


class VsphereDatacenterController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/datacenters'
    headers = [u'id', u'uuid', u'parent', u'name', u'state', u'ext_id']

    class Meta:
        label = 'vsphere.beehive.datacenters'
        aliases = ['datacenters']
        aliases_only = True
        description = "Vsphere datacenter management"


class VsphereFolderController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/folders'
    
    class Meta:
        label = 'vsphere.beehive.folders'
        aliases = ['folders']
        aliases_only = True        
        description = "Vsphere Folder management"


class VsphereDatastoreController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/datastores'
    headers = [u'id', u'uuid', u'parent.name', u'container.name', u'name', u'state', u'details.accessible',
               u'details.maintenanceMode', u'details.freespace', u'details.type']

    class Meta:
        label = 'vsphere.beehive.datastores'
        aliases = ['datastores']
        aliases_only = True
        description = "Vsphere Datastore management"


class VsphereClusterController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/clusters'

    class Meta:
        label = 'vsphere.beehive.clusters'
        aliases = ['clusters']
        aliases_only = True
        description = "Vsphere Cluster management"

    @expose(aliases=[u'host-list [field=value]'], aliases_only=True)
    @check_error
    def host_list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'/v1.0/nrs/vsphere/hosts'
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=self.headers, key=u'hosts')

    @expose(aliases=[u'respool-list [field=value]'], aliases_only=True)
    @check_error
    def respool_list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'/v1.0/nrs/vsphere/resource_pools'
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res, headers=self.headers, key=u'resource_pools')


class VsphereNetworkController(VsphereControllerChild):   
    class Meta:
        label = 'vsphere.beehive.network'
        aliases = ['network']
        aliases_only = True
        description = "Vsphere Network management"


class VsphereNetworkChildController(VsphereControllerChild):
    class Meta:
        stacked_on = 'vsphere.beehive.network'
        stacked_type = 'nested'

    def _ext_parse_args(self):
        VsphereControllerChild._ext_parse_args(self)


class VsphereNetworkDvsController(VsphereNetworkChildController):
    uri = u'/v1.0/nrs/vsphere/network/dvss'

    class Meta:
        label = 'vsphere.beehive.network.dvs'
        aliases = ['dvss']
        aliases_only = True
        description = "Vsphere Network distributed virtual switch management"


class VsphereNetworkDvpgController(VsphereNetworkChildController):
    uri = u'/v1.0/nrs/vsphere/network/dvpgs'

    class Meta:
        label = 'vsphere.beehive.network.dvpg'
        aliases = ['dvpgs']
        aliases_only = True
        description = "Vsphere Network distributed virtual port group management"


class VsphereNetworkNsxController(VsphereNetworkChildController):
    uri = u'/v1.0/nrs/vsphere/network/nsxs'
    
    class Meta:
        label = 'vsphere.beehive.network.nsx'
        aliases = ['nsxs']
        aliases_only = True
        description = "Vsphere Network Nsx Manager management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET')
        logger.debug(u'Get nsx managers: %s' % (truncate(res)))
        self.result(res.get(u'nsxs'), headers=self.headers)
        
    @expose(aliases=[u'transport-zones <id>'], aliases_only=True)
    @check_error
    def transport_zones(self):
        # data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/%s/transport_zones' % oid
        res = self._call(uri, u'GET')
        logger.debug(u'Get nsx transport zones: %s' % (truncate(res)))
        self.result(res.get(u'nsx_transport_zones'), headers=[u'id', u'name'])

        
class VsphereSecurityGroupController(VsphereNetworkChildController):
    uri = u'/v1.0/nrs/vsphere/network/nsx_security_groups'
    headers = [u'id', u'parent.name', u'container.name', u'name', u'state', u'date.creation']
    
    class Meta:
        label = 'vsphere.beehive.security_groups'
        aliases = ['nsx_security_groups']
        aliases_only = True         
        description = "Vsphere SecurityGroup management"


class VsphereServerController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/servers'
    baseuri = u'/v1.0/nrs'
    headers = [u'id', u'parent', u'container', u'name', u'state', u'runstate', u'ip-address',
               u'hostname', u'cpu', u'ram', u'disk', u'is-template']
    fields = [u'id', u'parent.name', u'container.name', u'name', u'state', u'details.state', u'details.ip_address',
              u'details.hostname', u'details.cpu', u'details.ram', u'details.disk', u'details.template']

    class Meta:
        label = 'vsphere.beehive.servers'
        aliases = ['servers']
        aliases_only = True         
        description = "Vsphere Server management"

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.uri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        if self.fields is None:
            self.fields = self.headers
        self.result(res, headers=self.headers, fields=self.fields, key=self._meta.aliases[0], maxsize=30)

    @expose(aliases=[u'add <file data>'], aliases_only=True)
    @check_error
    def add(self):
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)
        if u'pubkey' in data.get(u'server'):
            data[u'server'][u'user_data'] = b64encode(json.dumps({u'pubkey': data.get(u'server').get(u'pubkey')}))
        uri = self.uri
        res = self._call(uri, u'POST', data=data)
        self.wait_job(res[u'jobid'])
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        self.result(res)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid
        res = self._call(uri, u'GET').get(self._meta.aliases[0][:-1], {})
        logger.info(u'Get %s: %s' % (self._meta.aliases[0], truncate(res)))
        details = res.pop(u'details')
        volumes = details.pop(u'volumes')
        networks = details.pop(u'networks')
        flavor = details.pop(u'flavor')
        tools = details.pop(u'vsphere:tools')
        self.result(res, details=True)
        self.output(u'Details:')
        self.result(details, details=True)
        self.output(u'Guest Tools')
        self.result(tools, headers=[u'status', u'version'])
        self.output(u'Flavor')
        self.result(flavor, headers=[u'id', u'cpu', u'memory'])
        self.output(u'Networks')
        self.result(networks, headers=[u'name', u'mac_addr', u'dns', u'fixed_ips', u'net_id', u'port_state'])
        self.output(u'Volumes')
        self.result(volumes, headers=[u'id', u'name', u'storage', u'size', u'type', u'bootable', u'format', u'mode'],
                    maxsize=100)

    @expose(aliases=[u'hardware <id>'], aliases_only=True)
    @check_error
    def hardware(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/hw'
        res = self._call(uri, u'GET').get(u'server_hardware', {})
        logger.info(u'Get server hardware: %s' % truncate(res))
        file_layout = res.pop(u'file_layout')
        files = file_layout.pop(u'files')
        other = res.pop(u'other')
        network = res.pop(u'network')
        storage = res.pop(u'storage')
        controllers = other.pop(u'controllers')
        pci = other.pop(u'pci')
        input_devices = other.pop(u'input_devices')
        self.result(res, details=True)
        self.output(u'network:')
        self.result(network, headers=[u'type', u'name', u'key', u'connected', u'network.name', u'network.dvs',
                                      u'network.vlan', u'macaddress'])
        self.output(u'storage:')
        self.result(storage, headers=[u'type', u'name', u'size', u'datastore.file_name', u'datastore.disk_mode',
                                      u'datastore.write_through'], maxsize=200)
        self.output(u'file layout:')
        self.result(file_layout, details=True)
        self.result(files, headers=[u'accessible', u'name', u'uniqueSize', u'key', u'type', u'size'], maxsize=200)
        self.output(u'controllers:')
        self.result(controllers, headers=[u'type', u'name', u'key'])
        self.output(u'pci:')
        self.result(pci, headers=[u'type', u'name', u'key'])
        self.output(u'input devices:')
        self.result(input_devices, headers=[u'type', u'name', u'key'])

    @expose(aliases=[u'console <id>'], aliases_only=True)
    @check_error
    def console(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/console'
        res = self._call(uri, u'GET').get(u'server_console', {})
        logger.info(u'Get server console: %s' % truncate(res))
        self.result(res, details=True)

    @expose(aliases=[u'runtime <id>'], aliases_only=True)
    @check_error
    def runtime(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/runtime'
        res = self._call(uri, u'GET').get(u'server_runtime', {})
        logger.info(u'Get server runtime: %s' % truncate(res))
        resp = []
        resp.append(res.get(u'resource_pool'))
        resp.append(res.get(u'host'))
        self.result(resp, headers=[u'type', u'id', u'uuid', u'name', u'state'],
                    fields=[u'__meta__.definition', u'id', u'uuid', u'name', u'state'])

    @expose(aliases=[u'stats <id>'], aliases_only=True)
    @check_error
    def stats(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/stats'
        res = self._call(uri, u'GET').get(u'server_stats', {})
        logger.info(u'Get server stats: %s' % truncate(res))
        self.result(res, details=True)

    @expose(aliases=[u'guest <id>'], aliases_only=True)
    @check_error
    def guest(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/guest'
        res = self._call(uri, u'GET').get(u'server_guest', {})
        logger.info(u'Get server guest: %s' % truncate(res))
        guest = res.pop(u'guest')
        tools = res.pop(u'tools')
        disk = res.pop(u'disk')
        nics = res.pop(u'nics')
        ip_stack = res.pop(u'ip_stack')
        self.result(res, details=True)
        self.output(u'Guest:')
        self.result(guest, details=True)
        self.output(u'tools:')
        self.result(tools, details=True)
        self.output(u'disks:')
        self.result(disk, headers=[u'diskPath', u'capacity', u'free_space'], maxsize=100)
        self.output(u'nics:')
        self.result(nics, headers=[u'netbios_config', u'network', u'dnsConfig', u'connected', u'ip_config',
                                   u'mac_address', u'device_config_id'])
        self.output(u'ip_stacks:')
        for item in ip_stack:
            self.result(item.get(u'dns_config'), headers=[u'dhcp', u'search_domain', u'hostname', u'ip_address',
                                                          u'domainname'])
            self.result(item.get(u'ip_route_config'), headers=[u'network', u'gateway'])

    # @expose(aliases=[u'snapshots <id>'], aliases_only=True)
    # @check_error
    # def snapshots(self):
    #     oid = self.get_arg(name=u'id')
    #     uri = self.uri + u'/' + oid + u'/snapshots'
    #     res = self._call(uri, u'GET').get(self._meta.aliases[0][:-1], {})
    #     logger.info(u'Get server snapshots: %s' % truncate(res))
    #     self.result(res, details=True)

    @expose(aliases=[u'security-groups <id>'], aliases_only=True)
    @check_error
    def security_groups(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/security_groups'
        res = self._call(uri, u'GET').get(u'server_security_groups', {})
        logger.info(u'Get server security_groups: %s' % truncate(res))
        self.result(res, headers=[u'id', u'uuid', u'name', u'state'])


class VsphereFlavorController(VsphereControllerChild):
    uri = u'/v1.0/nrs/vsphere/flavors'
    headers = [u'id', u'parent', u'container', u'name', u'state', u'vcpus', u'ram', u'version', u'guest_id']
    fields = [u'id', u'parent.name', u'container.name', u'name', u'state', u'details.vcpus', u'details.ram',
              u'details.version', u'details.guest_id']

    class Meta:
        label = 'vsphere.beehive.flavors'
        aliases = ['flavors']
        aliases_only = True
        description = "Vsphere Flavor management"

    @expose(aliases=[u'add <container> <name> <datacenter>, <vcpus> <ram> [field=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new flavor
    - field: core_x_socket, guest_id, version
        """
        container = self.get_arg(name=u'container')
        name = self.get_arg(name=u'name')
        datacenter = self.get_arg(name=u'datacenter')
        core_x_socket = self.get_arg(name=u'core_x_socket', keyvalue=True, default=1)
        vcpus = self.get_arg(name=u'vcpus')
        guest_id = self.get_arg(name=u'version', keyvalue=True, default=u'centos64Guest')
        ram = self.get_arg(name=u'ram')
        version = self.get_arg(name=u'version', keyvalue=True, default=u'vmx-11')
        data = {
            u'container': container,
            u'name': name,
            u'desc': name,
            u'datacenter': datacenter,
            u'core_x_socket': core_x_socket,
            u'vcpus': vcpus,
            u'guest_id': guest_id,
            u'ram': ram,
            u'version': version,
        }
        uri = self.uri
        res = self._call(uri, u'POST', data={u'flavor': data})
        logger.info(u'Add %s: %s' % (self._meta.aliases[0], truncate(res)))
        msg = {u'msg': u'Add %s: %s' % (self._meta.aliases[0], truncate(res))}
        self.result(msg, headers=[u'msg'])

    @expose(aliases=[u'datastores <id>'], aliases_only=True)
    @check_error
    def datastores(self):
        oid = self.get_arg(name=u'id')
        uri = self.uri + u'/' + oid + u'/datastores'
        res = self._call(uri, u'GET').get(u'datastores', [])
        logger.info(u'Get flavor datastores: %s' % truncate(res))
        self.result(res, headers=[u'id', u'uuid', u'name', u'state', u'tag'])

    @expose(aliases=[u'datastore-add <id> <datastore> <tag>'], aliases_only=True)
    @check_error
    def datastore_add(self):
        """Add datastore to flavor
        """
        oid = self.get_arg(name=u'id')
        datastore = self.get_arg(name=u'datastore')
        tag = self.get_arg(name=u'tag')
        uri = self.uri + u'/' + oid + u'/datastores'
        data = {
            u'datastore': {
                u'uuid': datastore,
                u'tag': tag
            }
        }
        res = self._call(uri, u'POST', data)
        logger.info(u'Add datastore %s to flavor' % datastore)
        msg = {u'msg': u'Add datastore %s to flavor' % datastore}
        self.result(msg, headers=[u'msg'])

    @expose(aliases=[u'datastore-del <id> <datastore>'], aliases_only=True)
    @check_error
    def datastore_del(self):
        """Remove datastore from flavor
        """
        oid = self.get_arg(name=u'id')
        datastore = self.get_arg(name=u'datastore')
        uri = self.uri + u'/' + oid + u'/datastores'
        data = {
            u'datastore': {
                u'uuid': datastore
            }
        }
        res = self._call(uri, u'DELETE', data)
        logger.info(u'Remove datastore %s from flavor' % datastore)
        msg = {u'msg': u'Remove datastore %s from flavor' % datastore}
        self.result(msg, headers=[u'msg'])


vsphere_controller_handlers = [
    VsphereController,
    VsphereDatacenterController,
    VsphereFolderController,
    VsphereDatastoreController,
    VsphereClusterController,
    VsphereNetworkController,
    VsphereNetworkDvsController,
    VsphereNetworkDvpgController,
    VsphereNetworkNsxController,
    
    VsphereSecurityGroupController,

    VsphereServerController,
    VsphereFlavorController,
]
