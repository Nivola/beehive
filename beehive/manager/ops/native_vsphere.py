'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager, ComponentManager
import sys
import abc
from beedrones.vsphere.client import VsphereManager
from beecell.simple import truncate
from time import sleep
from pyVmomi import vim
from beecell.remote import RemoteClient

logger = logging.getLogger(__name__)

class Actions(object):
    """
    """
    def __init__(self, parent, name, entity_class, headers=None):
        self.parent = parent
        self.name = name
        self.entity_class = entity_class
        self.headers = headers
    
    def get_args(self, args):
        res = {}
        for arg in args:
            k,v = arg.split(u'=')
            if v in [u'False', u'false']:
                v = False
            elif v in [u'True', u'true']:
                v = True
            res[k] = v
        return res
    
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
    
    '''
    def doc(self):
        return """
        %ss list [filters]
        %ss get <id>
        %ss add <file data in json>
        %ss update <id> <field>=<value>    field: name, desc, geo_area
        %ss delete <id>
        
        >>> {u'pubkey':u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDpN36RMjBNpQ9lTvbdMjbkU6OyytX78RXKiVNMBU07vBx6REwGWgytg+8rG1pqFAuo6U3lR1q25dpPDQtK8Dad68MPHFydfv0WAYOG6Y02j/pQKJDGPhbeSYS0XF4F/z4UxY6cXB8UdzkUSKtIg93YCTkzbQY6+APOY/K9q1b2ZxTEEBDQgWenZw4McmSbaS+AYwmigSJb5sFMexJRKZCdXESgQcSmUkQFiXRQNJMlgPZBnIcbGlu5UA9G5owLM6LT11bPQPrROqmhcSGoQtYq83RGNX5Kgwe00pqeo/G+SUtcQRp5JtWIE9bLeaXRIhZuInrbP0rmHyCQhBeZDCPr1mw2YDZV9Fbb08/qwbq1UYuUzRXxXroX1F7/mztyXQt7o4AjXWpeyBccR0nkAyZcanOvvJJvoIwLoDqbsZaqCldQJCvtb1WNX9ukce5ToW1y80Rcf1GZrrXRTs2cAbubUkxYQaLQQApVnGIJelR9BlvR7xsmfQ5Y5wodeLfEgqw2hNzJEeKKHs5xnpcgG9iXVvW1Tr0Gf+UsY0UIogZ6BCstfR59lPAt1IRaYVCvgHsHm4hmr0yMvUwGHroztrja50XHp9h0z/EWAt56nioOJcOTloAIpAI05z4Z985bYWgFk8j/1LkEDKH9buq5mHLwN69O7JPN8XaDxBq9xqSP9w== sergio.tonani@csi.it'}
        >>> import base64, json
        >>> c=base64.b64encode(json.dumps(a))
        >>> json.loads(base64.b64decode(c))        
        
        """ % (self.name, self.name, self.name, self.name, self.name)'''
    
    def list(self, *args):
        objs = self.entity_class.list(**self.get_args(args))
        res = []
        for obj in objs:
            res.append(self.entity_class.info(obj))
        logger.debug(res)
        self.parent.result(res, headers=self.headers)

    def get(self, oid):
        obj = self.entity_class.get(oid)
        res = self.entity_class.detail(obj)
        logger.debug(res)
        self.parent.result(res, details=True)
    
    def add(self, data):
        data = self.parent.load_config(data)
        uri = u'%s/%ss/' % (self.parent.baseuri, self.name)
        res = self.parent._call(uri, u'POST', data=data)
        self.parent.logger.info(u'Add %s: %s' % (self.name, 
                                          truncate(res)))
        self.parent.result(res)

    def update(self, oid, *args):
        #data = self.load_config_file(args.pop(0)) 
        
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        
        data = {
            u'sites':val
        }
        uri = u'%s/%5s/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'PUT', data=data)
        self.parent.logger.info(u'Update %s: %s' % (self.name, 
                                             truncate(res)))
        self.parent.result(res)

    def delete(self, oid):
        obj = self.entity_class.get(oid)
        task = self.entity_class.remove(obj)
        self.wait_task(task)
        res = {u'msg':u'Delete %s %s' % (self.name, oid)}
        self.parent.result(res, headers=[u'msg'])         
    
    def register(self):
        res = {
            u'%ss.list' % self.name: self.list,
            u'%ss.get' % self.name: self.get,
            u'%ss.add' % self.name: self.add,
            u'%ss.update' % self.name: self.update,
            u'%ss.delete' % self.name: self.delete
        }
        self.parent.add_actions(res)
        
class ServerActions(Actions):
    """
    """
    def get_console(self, oid, *args):
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.remote_console(server, **self.get_args(args))
        self.parent.result(res, delta=60)
    
    def get_guest(self, oid, *args):
        server = self.entity_class.get_by_morid(oid)
        #data = self.entity_class.hardware.get_original_devices(server, 
        #                    dev_type=u'vim.vm.device.VirtualVmxnet3')[0].macAddress
        res = self.entity_class.guest_info(server)
        self.parent.result(res, details=True)        
    
    """
    def exec_command(self, oid, pwd, *args):
        #nmcli con mod test-lab ipv4.dns "8.8.8.8 8.8.4.4"
        server = self.entity_class.get_by_morid(oid)
        conn_name = u'net01'
        #conn_name = u'ens160'
        dev_name = u"`nmcli dev status|grep ethernet|awk '{print $1}'`"
        ipaddr = u'10.102.184.55/24'
        macaddr = u'00:50:56:a1:55:4e'
        gw = u'10.102.184.1'
        dns = u'10.102.184.2'
        
        # delete connection with the same name
        params = u'con delete %s' % conn_name
        proc = self.entity_class.guest_execute_command(
                    server, u'root', pwd, path_to_program=u'/bin/nmcli',
                    program_arguments=params)        
        
        # create new connection
        #params = u'con add type ethernet con-name %s ifname %s ip4 %s gw4 %s' % (conn_name, dev_name, ipaddr, gw)
        params = u'con add type ethernet con-name %s ifname "*" mac %s ip4 %s gw4 %s' % (conn_name, macaddr, ipaddr, gw)
        proc = self.entity_class.guest_execute_command(
                    server, u'root', pwd, path_to_program=u'/bin/nmcli',
                    program_arguments=params)
        
        # setup dns
        params = u'con modify %s ipv4.dns "%s"' % (conn_name, dns)
        proc = self.entity_class.guest_execute_command(
                    server, u'root', pwd, path_to_program=u'/bin/nmcli',
                    program_arguments=params)
        '''
        # bring up interface
        params = u'con up %s %s ifname %s' % (conn_name, dev_name)
        proc = self.entity_class.guest_execute_command(
                    server, u'root', pwd, path_to_program=u'/bin/nmcli',
                    program_arguments=params)'''
        
        '''# bring up interface
        params = u'con down %s ifname "*" %s mac %s' % (conn_name, dev_name, macaddr)
        proc = self.entity_class.guest_execute_command(
                    server, u'root', pwd, path_to_program=u'/bin/nmcli',
                    program_arguments=params)    '''      
        
        #res = self.entity_class.guest_read_environment_variable(server,
        #                                                        u'root', pwd)
        res = proc
        self.parent.result(res)     """   
    
    def setup_ssh_key(self, oid, pwd):
        key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDpN36RMjBNpQ9lTvbdMjbkU6OyytX78RXKiVNMBU07vBx6REwGWgytg+8rG1pqFAuo6U3lR1q25dpPDQtK8Dad68MPHFydfv0WAYOG6Y02j/pQKJDGPhbeSYS0XF4F/z4UxY6cXB8UdzkUSKtIg93YCTkzbQY6+APOY/K9q1b2ZxTEEBDQgWenZw4McmSbaS+AYwmigSJb5sFMexJRKZCdXESgQcSmUkQFiXRQNJMlgPZBnIcbGlu5UA9G5owLM6LT11bPQPrROqmhcSGoQtYq83RGNX5Kgwe00pqeo/G+SUtcQRp5JtWIE9bLeaXRIhZuInrbP0rmHyCQhBeZDCPr1mw2YDZV9Fbb08/qwbq1UYuUzRXxXroX1F7/mztyXQt7o4AjXWpeyBccR0nkAyZcanOvvJJvoIwLoDqbsZaqCldQJCvtb1WNX9ukce5ToW1y80Rcf1GZrrXRTs2cAbubUkxYQaLQQApVnGIJelR9BlvR7xsmfQ5Y5wodeLfEgqw2hNzJEeKKHs5xnpcgG9iXVvW1Tr0Gf+UsY0UIogZ6BCstfR59lPAt1IRaYVCvgHsHm4hmr0yMvUwGHroztrja50XHp9h0z/EWAt56nioOJcOTloAIpAI05z4Z985bYWgFk8j/1LkEDKH9buq5mHLwN69O7JPN8XaDxBq9xqSP9w== sergio.tonani@csi.it'
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_ssh_key(server, u'root', pwd, key)
        self.parent.result(res)
        
    def setup_ssh_pwd(self, oid, pwd, newpwd):
        newpwd = u'prova'
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_admin_password(server, u'root', pwd, 
                                                           newpwd)
        self.parent.result(res)        
    
    def setup_network(self, oid, pwd, data):
        data = self.parent.load_config(data)
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
        self.parent.result(res)
    
    
    def run_ssh_command(self, oid, user, pwd, cmd):
        server = self.entity_class.get_by_morid(oid)
        data = self.entity_class.data(server)
        client = RemoteClient({u'host':data[u'networks'][0][u'fixed_ips'],
                               u'port':22})
        res = client.run_ssh_command(cmd, user, pwd)
        if res.get(u'stderr' != u''):
            print(u'Error')
            print(res.get(u'stderr'))
        else:
            for row in res.get(u'stdout'):
                print(row)
    
    #
    # action
    #
    def start(self, oid):
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.start(server)        
        self.wait_task(task)
    
    def stop(self, oid):
        server = self.entity_class.get_by_morid(oid)
        task = self.entity_class.stop(server)        
        self.wait_task(task)
    
    def register(self):
        res = {
            #u'%ss.console' % self.name: self.get_console,
            #u'%ss.cmd' % self.name: self.exec_command,
            u'%ss.guest' % self.name: self.get_guest,
            u'%ss.sshkey' % self.name: self.setup_ssh_key,
            u'%ss.pwd' % self.name: self.setup_ssh_pwd,
            u'%ss.net' % self.name: self.setup_network,
            
            u'%ss.cmd' % self.name: self.run_ssh_command,
            u'%ss.start' % self.name: self.start,
            u'%ss.stop' % self.name: self.stop,
        }
        self.parent.add_actions(res)

class NetworkActions(Actions):
    """
    """
    def list_dvs(self):
        objs = self.entity_class.list_distributed_virtual_switches()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_distributed_virtual_switch(obj))        
        logger.info(res)
        self.parent.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])

    def get_dvs(self, oid):
        res = self.entity_class.get_distributed_virtual_switch(oid)
        res = self.entity_class.detail_distributed_virtual_switch(res)
        logger.info(res)
        self.parent.result(res, details=True)
        
    def list_networks(self):
        objs = self.entity_class.list_networks()
        res = []
        for obj in objs:
            res.append(self.entity_class.info_network(obj))        
        logger.info(res)
        self.parent.result(res, headers=[u'id', u'name', u'parent',
                                         u'overallStatus'])
        
    def get_network(self, oid):
        network = self.entity_class.get_network(oid)
        res = self.entity_class.detail_network(network)
        logger.info(res)
        self.parent.result(res, details=True)
    
    '''
    def get_network_servers(self):
        servers = self.entity_class.get_network_servers('dvportgroup-127')
        self.logger.info(self.pp.pformat(servers))'''
    
    '''
    def test_create_network(self):
        name = 'L-dvpg-567_DCCTP-tst-FE-Rupar'
        desc= name
        vlan = 567
        dvs = self.entity_class.get_distributed_virtual_switch('dvs-74')
        numports = 24
        res = self.entity_class.create_distributed_port_group(name, desc, 
                                                              vlan, dvs, 
                                                              numports)
        self.logger.info(res)'''
        
    def delete_network(self, oid):
        network = self.entity_class.get_network(oid)
        res = self.entity_class.remove_network(network)
        logger.info(res)
        res = {u'msg':u'Delete network %s' % oid}
        self.parent.result(res, headers=[u'msg'])    
        
    def register(self):
        res = {
            u'dvss.list': self.list_dvs,
            u'dvss.get': self.get_dvs,
            u'networks.list': self.list_networks,
            u'networks.get': self.get_network,
            u'networks.delete': self.delete_network,
        }
        self.parent.add_actions(res)        

class SgActions(Actions):
    """
    """
    def get(self, oid):
        res = self.entity_class.get(oid)
        rules = res.pop(u'member')
        self.parent.result(res, details=True)
        print(u'Members:')
        self.parent.result(rules, headers=[u'objectId', u'name', 
                                           u'objectTypeName'])
    
    def delete_member(self, oid, member):
        res = self.entity_class.delete_member(oid, member)
        logger.info(res)
        res = {u'msg':u'Delete security-group %s member %s' % (oid, member)}
        self.parent.result(res, headers=[u'msg'])
    
    def register(self):
        res = {
            u'%ss.get' % self.name: self.get,
            u'%ss.delete-member' % self.name: self.delete_member,
        }
        self.parent.add_actions(res)
        
class DfwActions(Actions):
    """
    """
    def __print_sections(self, data, stype):
        sections = data[stype][u'section']
        if type(sections) is not list: sections = [sections]
        for s in sections:
            rules = s.get(u'rule', [])
            if type(rules) is not list: rules = [rules]
            s[u'rules'] = len(rules)
        self.parent.result(sections, headers=[u'@id', u'@type', u'@timestamp', 
                                              u'@generationNumber', u'@name',
                                              u'rules'])

    def get_sections(self):
        res = self.entity_class.get_config()
        
        data = [{u'key':u'contextId', u'value':res[u'contextId']},
                {u'key':u'@timestamp', u'value':res[u'@timestamp']},
                {u'key':u'generationNumber', u'value':res[u'generationNumber']}]
        self.parent.result(data, headers=[u'key', u'value'])
        
        print(u'layer3Sections')
        self.__print_sections(res, u'layer3Sections')
        print(u'layer2Sections')
        self.__print_sections(res, u'layer2Sections')     
        print(u'layer3RedirectSections')
        self.__print_sections(res, u'layer3RedirectSections')

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
        self.parent.result(data, headers=[u'type', u'name', u'value'])        

    def get_rules(self, section, rule=None):
        if rule is None:
            res = self.entity_class.get_layer3_section(sectionid=section)
            
            rules = res.pop(u'rule', [])
            self.parent.result([res], headers=[u'@id', u'@type', u'@timestamp', 
                                               u'@generationNumber', u'@name'])
            
            print(u'Rules:')
            for r in rules:
                r = self.__set_rule_value(u'services', u'service', r)
                r = self.__set_rule_value(u'sources', u'source', r)
                r = self.__set_rule_value(u'destinations', u'destination', r)
                r = self.__set_rule_value(u'appliedToList', u'appliedTo', r)
            self.parent.result(rules, headers=[u'@id', u'@disabled', u'@logged', 
                                               u'name', u'direction', u'action', 
                                               u'packetType', u'sources', 
                                               u'destinations', u'services',
                                               u'appliedToList'])
        else:
            res = self.entity_class.get_rule(section, rule)
            #self.parent.result(res, details=True)
            services = res.pop(u'services', {}).pop(u'service', [])
            sources = res.pop(u'sources', {}).pop(u'source', [])
            destinations = res.pop(u'destinations', {}).pop(u'destination', [])
            appliedToList = res.pop(u'appliedToList', {}).pop(u'appliedTo', [])
            
            self.parent.result(res, headers=[u'@id', u'@disabled', u'@logged', 
                                               u'name', u'direction', u'action', 
                                               u'packetType'])
            
            self.__print_rule_datail(u'sources', sources)
            self.__print_rule_datail(u'destinations', destinations)
            self.__print_rule_datail(u'appliedTo', appliedToList)
            print(u'services')
            if type(services) is not list: services = [services]
            self.parent.result(services, headers=[u'protocol', u'subProtocol', 
                                                  u'destinationPort', 
                                                  u'protocolName']) 

    def delete_section(self, section):
        res = self.entity_class.delete_section(section)
        logger.info(res)
        res = {u'msg':u'Delete section %s' % (section)}
        self.parent.result(res, headers=[u'msg'])
    
    def delete_rule(self, section, rule):
        res = self.entity_class.delete_rule(section, rule)
        logger.info(res)
        res = {u'msg':u'Delete section %s rule %s' % (section, rule)}
        self.parent.result(res, headers=[u'msg'])
        
    def get_exclusion_list(self):
        res = self.entity_class.get_exclusion_list()
        res = res.get(u'excludeMember', [])
        resp = []
        for item in res:
            resp.append(item[u'member'])
        logger.info(res)
        self.parent.result(resp, headers=[u'objectId', u'name', u'scope.name',
                                          u'objectTypeName', u'revision'])         
    
    def register(self):
        res = {
            u'%s.sections' % self.name: self.get_sections,
            u'%s.rules' % self.name: self.get_rules,
            u'%s.delete-section' % self.name: self.delete_section,
            u'%s.delete-rule' % self.name: self.delete_rule,
            u'%s.exclusion-list' % self.name: self.get_exclusion_list,
        }
        self.parent.add_actions(res)           

class NativeVsphereManager(ApiManager):
    """
    SECTION: 
        native.vsphere <orchestrator-id>
    
    PARAMs:
        datacenters list
        datacenters get <oid>
        
        folders list
        folders get <oid>
        folders delete <oid>
        
        vapps list
        vapps get <oid>
        
        dvss list
        dvss get <oid>
        networks list
        networks get <oid>
        
        clusters list
        clusters get <oid>
        hosts list
        hosts get <oid>
        rpools list
        rpools get <oid>
        
        datastores list
        datastores get <oid>        
    
        servers list                                 list severs
        servers get <oid>                            get server details
        servers guest <oid>                          get server guest tools info
        servers delete                               delete server
        servers cmd <oid> <usr> "<pwd>" "<command>"  run a command using ssh 
                                                     connection 
        servers start <oid>                          start server
        servers stop <oid>                           stop server
    
        nsx-lgs list                                 list nsx logical switches
        nsx-lgs get <oid>                            get nsx logical switch
        
        nsx-sgs list                                 list nsx security groups
        nsx-sgs get <oid>                            get nsx security group        
        nsx-sgs delete-member <oid> <member>         delete nsx security group member
        
        nsx-ipsets list                              list nsx ipsets
        nsx-ipsets get <oid>                         get nsx ipset
        
        nsx-dlrs list                                list nsx dlrs
        nsx-dlrs get <oid>                           get nsx ipset
        
        nsx-edges list                               list nsx edges
        nsx-edges get <oid>                          get nsx ipset
        
        nsx-dfw sections                             list dfw sections
        nsx-dfw rules <section> [<rule>]             list/get dfw rule(s)
        nsx-dfw delete-section <section>             delete dfw section
        nsx-dfw delete-rule <section> <rule>         list dfw sections
        nsx-dfw exclusion-list                       list dfw sections
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, auth_config, env, frmt=u'json', orchestrator_id=None):
        ApiManager.__init__(self, auth_config, env, frmt)

        conf = auth_config.get(u'orchestrators')\
                          .get(u'vsphere')\
                          .get(orchestrator_id)
        if conf is None:
            raise Exception(u'Orchestrator %s is not configured' % orchestrator_id)
            
        self.client = VsphereManager(conf.get(u'vcenter'), conf.get(u'nsx'))

        self.__actions = {}
        
        self.entities = [
            [u'datacenter', self.client.datacenter, [u'id', u'name']],
            [u'folder', self.client.folder, [u'id', u'name', u'type', u'parent']],
            [u'vapp', self.client.vapp, [u'id', u'name']],
            [u'cluster', self.client.cluster, [u'id', u'name']],
            [u'host', self.client.cluster.host, [u'id', u'name']],
            [u'rpool', self.client.cluster.resource_pool, [u'id', u'name']],
            [u'datastore', self.client.datastore, [u'id', u'name']],
            
            [u'server', self.client.server, [u'id', u'name', u'os', u'memory',
                                             u'cpu', u'state', u'template', 
                                             u'hostname', u'ip_address', 
                                             u'disk']],
                         
            [u'nsx-lg', self.client.network.nsx.lg, [u'objectId', u'tenantId']],
            [u'nsx-sg', self.client.network.nsx.sg, [u'objectId', u'name']],
            [u'nsx-ipset', self.client.network.nsx.ipset, [u'objectId', u'name',
                                                           u'value']],
            [u'nsx-dlr', self.client.network.nsx.dlr, [u'objectId', u'name']],
            [u'nsx-edge', self.client.network.nsx.edge, [u'objectId', u'name']],
        ]
        
        for entity in self.entities:
            Actions(self, entity[0], entity[1], entity[2]).register()
        
        # custom actions
        ServerActions(self, u'server', self.client.server).register()
        NetworkActions(self, u'network', self.client.network).register()
        SgActions(self, u'nsx-sg', self.client.network.nsx.sg).register()
        DfwActions(self, u'nsx-dfw', self.client.network.nsx.dfw).register()
        
    @staticmethod
    def get_params(args):
        try: cid = args.pop(0)
        except:
            raise Exception(u'ERROR : Vcenter id is missing')
        return {u'orchestrator_id':cid}    
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)

        
#doc = NativeVsphereManager.__doc__
#for entity in NativeVsphereManager.entities:
#    doc += Actions(None, entity).doc()
#NativeVsphereManager.__doc__ = doc
