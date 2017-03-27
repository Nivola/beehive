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

logger = logging.getLogger(__name__)

class Actions(object):
    """
    """
    def __init__(self, parent, name, entity_class):
        self.parent = parent
        self.name = name
        self.entity_class = entity_class
    
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
        
        """ % (self.name, self.name, self.name, self.name, self.name)
    
    def list(self, *args):
        objs = self.entity_class.list(**self.get_args(args))
        res = []
        for obj in objs:
            res.append(self.entity_class.data(obj))
        self.parent.result(res)

    def get(self, oid):
        obj = self.entity_class.get(oid)
        res = self.entity_class.data(obj)
        self.parent.result(res)
    
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
        uri = u'%s/%ss/%s/' % (self.parent.baseuri, self.name, oid)
        res = self.parent._call(uri, u'DELETE')
        self.parent.logger.info(u'Delete %s: %s' % (self.name, oid))
        self.parent.result(res)
    
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
        data = self.entity_class.hardware.get_original_devices(server, 
                            dev_type=u'vim.vm.device.VirtualVmxnet3')[0].macAddress
        print data
        res = self.entity_class.guest_info(server)
        self.parent.result(res)        
    
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
        self.parent.result(res)        
    
    def setup_ssh_key(self, oid, pwd):
        key = u'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDpN36RMjBNpQ9lTvbdMjbkU6OyytX78RXKiVNMBU07vBx6REwGWgytg+8rG1pqFAuo6U3lR1q25dpPDQtK8Dad68MPHFydfv0WAYOG6Y02j/pQKJDGPhbeSYS0XF4F/z4UxY6cXB8UdzkUSKtIg93YCTkzbQY6+APOY/K9q1b2ZxTEEBDQgWenZw4McmSbaS+AYwmigSJb5sFMexJRKZCdXESgQcSmUkQFiXRQNJMlgPZBnIcbGlu5UA9G5owLM6LT11bPQPrROqmhcSGoQtYq83RGNX5Kgwe00pqeo/G+SUtcQRp5JtWIE9bLeaXRIhZuInrbP0rmHyCQhBeZDCPr1mw2YDZV9Fbb08/qwbq1UYuUzRXxXroX1F7/mztyXQt7o4AjXWpeyBccR0nkAyZcanOvvJJvoIwLoDqbsZaqCldQJCvtb1WNX9ukce5ToW1y80Rcf1GZrrXRTs2cAbubUkxYQaLQQApVnGIJelR9BlvR7xsmfQ5Y5wodeLfEgqw2hNzJEeKKHs5xnpcgG9iXVvW1Tr0Gf+UsY0UIogZ6BCstfR59lPAt1IRaYVCvgHsHm4hmr0yMvUwGHroztrja50XHp9h0z/EWAt56nioOJcOTloAIpAI05z4Z985bYWgFk8j/1LkEDKH9buq5mHLwN69O7JPN8XaDxBq9xqSP9w== sergio.tonani@csi.it'
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_ssh_key(server, u'root', pwd, key)
        self.parent.result(res)
        
    def setup_ssh_pwd(self, oid, pwd, newpwd):
        newpwd = u'prova'
        server = self.entity_class.get_by_morid(oid)
        res = self.entity_class.guest_setup_admin_apssword(server, u'root', pwd, 
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
    
    def register(self):
        res = {
            u'%ss.console' % self.name: self.get_console,
            u'%ss.cmd' % self.name: self.exec_command,
            u'%ss.guest' % self.name: self.get_guest,
            u'%ss.sshkey' % self.name: self.setup_ssh_key,
            u'%ss.pwd' % self.name: self.setup_ssh_pwd,
            u'%ss.net' % self.name: self.setup_network,
        }
        self.parent.add_actions(res)

class NativeVsphereManager(ApiManager):
    """
    SECTION: 
        native.vsphere    
    
    PARAMs:  
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
        
        self.entities = {
            (u'server', self.client.server),
        }        
        
        for entity in self.entities:
            Actions(self, entity[0], entity[1]).register()
        
        # custom actions
        ServerActions(self, u'server', self.client.server).register()
        
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)

        
#doc = NativeVsphereManager.__doc__
#for entity in NativeVsphereManager.entities:
#    doc += Actions(None, entity).doc()
#NativeVsphereManager.__doc__ = doc
