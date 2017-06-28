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
from beedrones.openstack.client import OpenstackManager
from beecell.simple import truncate
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
    
    def load_config_file(self, filename):
        """
        """
        f = open(filename, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config
    
    def doc(self):
        return """
        %ss list [filters]
        %ss get <id>
        %ss add <file data in json>
        %ss update <id> <field>=<value>    field: name, desc, geo_area
        %ss delete <id>
        """ % (self.name, self.name, self.name, self.name, self.name)
    
    def list(self, *args):
        objs = self.entity_class.list(**self.get_args(args))
        res = []
        for obj in objs:
            res.append(obj)
        self.parent.result(res, headers=self.headers)

    def get(self, oid):
        obj = self.entity_class.get(oid)
        #res = self.entity_class.data(obj)
        res = obj
        self.parent.result(res, details=True)
    
    '''
    def add(self, data_file):
        data = self.load_config_file(data_file)
        obj = self.entity_class.create(*data)
        res = obj
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
        self.parent.result(res)'''

    def delete(self, oid):
        res = self.entity_class.delete(oid)
        res = {u'msg':u'delete %s %s' % (oid, self.name)}
        self.parent.result(res, headers=[u'msg'])
    
    def register(self):
        res = {
            u'%ss.list' % self.name: self.list,
            u'%ss.get' % self.name: self.get,
            #u'%ss.add' % self.name: self.add,
            #u'%ss.update' % self.name: self.update,
            u'%ss.delete' % self.name: self.delete
        }
        self.parent.add_actions(res)
        
class ServerActions(Actions):
    """
    """
    def list(self):
        res = self.entity_class.list(detail=True)
        self.parent.result(res, headers=[u'id', u'tenant_id', u'name',
            u'OS-EXT-SRV-ATTR:instance_name', u'status'])
    
    def run_ssh_command(self, oid, user, pwd, cmd):
        server = self.entity_class.get(oid)
        ip = server[u'addresses'].values()[0][0][u'addr']
        client = RemoteClient({u'host':ip,
                               u'port':22})
        res = client.run_ssh_command(cmd, user, pwd)
        if res.get(u'stderr' != u''):
            print(u'Error')
            print(res.get(u'stderr'))
        else:
            for row in res.get(u'stdout'):
                print(row)    
    
    def start(self, oid):
        res = self.entity_class.start(oid)
        res = {u'msg':u'start %s %s' % (oid, self.name)}
        self.parent.result(res, headers=[u'msg'])
    
    def stop(self, oid):
        res = self.entity_class.stop(oid)
        res = {u'msg':u'stop %s %s' % (oid, self.name)}
        self.parent.result(res, headers=[u'msg'])
        
    def console(self, oid):
        res = self.entity_class.get_vnc_console(oid)
        self.parent.result(res, headers=[u'type', u'url'], maxsize=100)
        
    def metatdata(self, oid):
        res = self.entity_class.get_metadata(oid)
        resp = []
        for k,v in res.items():
            resp.append({u'key':k, u'value':v})
        self.parent.result(resp, headers=[u'key', u'value'], maxsize=100)        
        
    def actions(self, oid):
        res = self.entity_class.get_actions(oid)
        self.parent.result(res, headers=[u'start_time', u'request_id', 
                                         u'action', u'message'], maxsize=200)
    
    def register(self):
        res = {
            u'%ss.list' % self.name: self.list,
            u'%ss.cmd' % self.name: self.run_ssh_command,
            u'%ss.start' % self.name: self.start,
            u'%ss.stop' % self.name: self.stop,
            u'%ss.console' % self.name: self.console,
            u'%ss.metadata' % self.name: self.metatdata,
            u'%ss.actions' % self.name: self.actions,
        }
        self.parent.add_actions(res)
        
class VolumeActions(Actions):
    """
    """
    def list(self):
        res = self.entity_class.list(detail=True)
        for item in res:
            if len(item[u'attachments']) > 0:
                item[u'server'] = item[u'attachments'][0][u'server_id']
            else:
                item[u'server'] = None
        self.parent.result(res, headers=
           [u'id', u'os-vol-tenant-attr:tenant_id', u'name',
            u'status', u'size', u'bootable', u'server'])
    
    def register(self):
        res = {
            u'%ss.list' % self.name: self.list,
        }
        self.parent.add_actions(res)        
        
class SystemActions(Actions):
    """
    """
    def get_hosts(self, *args):
        res = self.entity_class.compute_hosts()
        self.parent.result(res)
    
    def get_compute_hypervisors(self, *args):
        res = self.entity_class.compute_hypervisors()
        self.parent.result(res)        
    
    def register(self):
        res = {
            u'%ss.hosts' % self.name: self.get_hosts,
            u'%ss.hypervisors' % self.name: self.get_compute_hypervisors,
        }
        self.parent.add_actions(res)
        
class SgActions(Actions):
    """
    """
    def list_logging(self, *args):
        res = self.entity_class.list_logging()
        self.parent.result(res)
    
    def get(self, oid):
        res = self.entity_class.get(oid)
        rules = res.pop(u'security_group_rules')
        self.parent.result(res, details=True)
        print(u'Rules:')
        self.parent.result(rules, headers=[u'id', u'direction', u'protocol',
                                           u'ethertype', u'remote_group_id',
                                           u'remote_ip_prefix', u'port_range_min',
                                           u'port_range_max'])
    
    def register(self):
        res = {
            u'%ss.log' % self.name: self.list_logging,
            u'%ss.get' % self.name: self.get,
        }
        self.parent.add_actions(res)        

class RouterActions(Actions):
    """
    """
    def delete_internal_interface(self, oid, subnet):
        res = self.entity_class.delete_internal_interface(oid, subnet)
        res = {u'msg':u'delete interface on subnet %s' % (subnet)}
        self.parent.result(res, headers=[u'msg'])
    
    def register(self):
        res = {
            u'%ss.delete-interface' % self.name: self.delete_internal_interface,
        }
        self.parent.add_actions(res)    

class NativeOpenstackManager(ApiManager):
    """
    SECTION: 
        native.openstack <orchestrator-id>   
    
    PARAMs:
        projects list
        projects get <oid>
        projects delete <oid>
    
        networks list
        networks get <oid>
        networks delete <oid>
        
        subnets list
        subnets get <oid>
        subnets delete <oid>
        
        ports list [network=]
        ports get <oid>
        ports delete <oid>
        
        floating-ips list
        floating-ips get <oid>
        
        routers list
        routers get <oid>
        routers delete <oid>
        routers delete-interface <oid> <subnet>      delete router internal interface
        
        images list
        images get <oid>
        
        flavors list
        flavors get <oid>
        
        security-groups list
        security-groups get <oid>
        security-groups delete <oid>
        
        servers list                                 list severs
        servers get <oid>                            get server details
        servers cmd <oid> <usr> "<pwd>" "<command>"  run a command using ssh 
                                                     connection 
        servers start <oid>                          start server
        servers stop <oid>                           stop server
        servers actions <oid>                        get server actions
        servers metadata <oid>                       get server metadata
        servers delete <oid>                         delete server
        
        volumes list
        volumes get <oid>
        volumes delete <oid>
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, auth_config, env, frmt=u'json', orchestrator_id=None):
        ApiManager.__init__(self, auth_config, env, frmt)

        conf = auth_config.get(u'orchestrators')\
                          .get(u'openstack')\
                          .get(orchestrator_id)
        if conf is None:
            raise Exception(u'Orchestrator %s is not configured' % orchestrator_id)
            
        self.client = OpenstackManager(conf.get(u'uri'), 
                                       default_region=conf.get(u'region'))
        self.client.authorize(conf.get(u'user'), conf.get(u'pwd'), 
                              project=conf.get(u'project'), 
                              domain=conf.get(u'domain'))        

        self.__actions = {}
        
        self.entities = [
            [u'project', self.client.project, 
             [u'id', u'parent_id', u'domain_id', u'name', u'enabled']],
            [u'network', self.client.network, 
             [u'id', u'tenant_id', u'name', u'provider:segmentation_id', 
              u'router:external', u'shared', u'provider:network_type']],
            [u'subnet', self.client.network.subnet, 
             [u'id', u'tenant_id', u'name', u'network_id', u'cidr', 
              u'enable_dhcp']],
            [u'port', self.client.network.port, 
             [u'id', u'tenant_id', u'network_id', u'security_groups', 
              u'mac_address', u'status', u'device_owner']],
            [u'floating-ip', self.client.network.ip, 
             [u'id', u'tenant_id', u'status', u'floating_ip_address',
              u'fixed_ip_address']],
            [u'router', self.client.network.router, 
             [u'id', u'tenant_id', u'name', u'ha', u'status']],
            [u'image', self.client.image, 
             [u'id', u'name']],
            [u'flavor', self.client.flavor, 
             [u'id', u'name']],
            [u'security-group', self.client.network.security_group, 
             [u'id', u'tenant_id', u'name']],
            [u'server', self.client.server, 
             [u'id', u'parent_id', u'name']],
            [u'volume', self.client.volume, 
             [u'id', u'parent_id', u'name']]
        ]
        
        for entity in self.entities:
            Actions(self, entity[0], entity[1], entity[2]).register()
        
        # custom actions
        ServerActions(self, u'server', self.client.server, []).register()
        VolumeActions(self, u'volume', self.client.volume, []).register()
        SystemActions(self, u'system', self.client.system,[]).register()
        SgActions(self, u'security-group', 
                  self.client.network.security_group, []).register()
        RouterActions(self, u'router', self.client.network.router,[]).register()
    
    @staticmethod
    def get_params(args):
        try: cid = args.pop(0)
        except:
            raise Exception(u'ERROR : Openstack id is missing')
        return {u'orchestrator_id':cid}     
    
    def actions(self):
        return self.__actions
    
    def add_actions(self, actions):
        self.__actions.update(actions)
