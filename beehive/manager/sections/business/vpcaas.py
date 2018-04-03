"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
import urllib
import json

from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate, id_gen
from urllib import urlencode

 
logger = logging.getLogger(__name__)


class VPCaaServiceController(BaseController):
    class Meta:
        label = 'vpcaas'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Virtual Private Cloud Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
 
 
class VPCaaServiceControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'
 
    class Meta:
        stacked_on = 'vpcaas'
        stacked_type = 'nested'


class ImageServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'images'
        description = "Images service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all images by field: owner-id.N, image-id.N
        """
        dataSearch={}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'image-id.N'] = self.split_arg(u'image-id.N')   
        uri = u'%s/computeservices/image/describeimages' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True)).get(u'DescribeImagesResponse')\
            .get(u'imagesSet', [])
        headers = [u'id', u'name', u'state', u'type', u'account', u'platform']
        fields = [u'imageId', u'name', u'imageState', u'imageType', u'imageOwnerAlias', u'platform']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'create <name> <account> <type>'], aliases_only=True)
    @check_error
    def create(self):
        """Create an image
        """
        data = {
            u'ImageName': self.get_arg(name=u'name'),
            u'owner_id': self.get_arg(name=u'account'),
            u'ImageType': self.get_arg(name=u'type')
        }
        uri = u'%s/computeservices/image/createimage' % self.baseuri
        res = self._call(uri, u'POST', data={u'image': data}, timeout=600)
        logger.info(u'Add image: %s' % truncate(res))
        res = res.get(u'CreateImageResponse').get(u'imageSet')[0].get(u'imageId')
        res = {u'msg': u'Add image %s' % res}
        self.result(res, headers=[u'msg'])


class VMServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'vms'
        description = "Virtual Machine service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all virtual machine by field: owner-id.N, instance-id.N
        """
        
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'instance-id.N'] = self.split_arg(u'instance-id.N')       

        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True)).get(u'DescribeInstancesResponse')\
            .get(u'reservationSet')[0].get(u'instancesSet')
        headers = [u'id', u'name', u'type', u'state', u'launchTime', u'account', u'availabilityZone',
                   u'privateIp', u'image', u'subnet']
        fields = [u'instanceId', u'name', u'instanceType', u'instanceState.name', u'launchTime',
                  u'OwnerAlias', u'placement.availabilityZone', u'privateIpAddress', u'imageName',
                  u'subnetName']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'describe <id>'], aliases_only=True)
    @check_error
    def describe(self):
        """Get virtual machine
        """
        dataSearch = {u'instance-id.N': [self.get_arg(u'id')]}
        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True)) \
            .get(u'DescribeInstancesResponse') \
            .get(u'reservationSet')[0].get(u'instancesSet')[0]
        self.result(res, details=True, maxsize=40)

    @expose(aliases=[u'runinstance <name> <account> <subnet> <type> <image> <security group>'],
            aliases_only=True)
    @check_error
    def runinstance(self):
        """Create a virtual machine
        """
        data = {
            u'Name': self.get_arg(name=u'name'),
            u'owner_id': self.get_arg(name=u'account'),
            u'AdditionalInfo': u'',
            u'SubnetId': self.get_arg(name=u'subnet'),
            u'InstanceType': self.get_arg(name=u'type'),
            u'AdminPassword': u'myPwd$1',
            u'ImageId': self.get_arg(name=u'image'),
            u'SecurityGroupId_N': [self.get_arg(name=u'security group')],
        }
        uri = u'%s/computeservices/instance/runinstances' % self.baseuri
        res = self._call(uri, u'POST', data={u'instance': data}, timeout=600)
        logger.info(u'Add virtual machine instance: %s' % truncate(res))
        res = res.get(u'RunInstanceResponse').get(u'instancesSet')[0].get(u'instanceId')
        res = {u'msg': u'Add virtual machine %s' % res}
        self.result(res, headers=[u'msg'])


    @expose(aliases=[u'start [field=<id1, id2>] '], aliases_only=True)
    @check_error
    def start(self):
        """Start service instance by field
    - field: owner-id.N, instance-id.N
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'instance-id.N'] = self.split_arg(u'instance-id.N')       
        
        uri = u'%s/computeservices/instance/startinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'StartInstancesResponse')\
            .get(u'instancesSet', [])
        headers = [u'id', u'name', u'state',  u'currentState', u'previousState']
        fields = [u'id', u'name', u'state',  u'currentState', u'previousState']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'stop [field=<id1, id2>] force=true|false '], aliases_only=True)
    @check_error
    def stop(self):
        """Stop service instance by field
    - field: list of owner-id.N, instance-id.N
    - field: force is set to true forces the instances to stop (default is false) 
        """
        dataSearch = {}
        dataSearch[u'instance-id.N'] = self.split_arg(u'instance-id.N')
        dataSearch[u'Force'] = self.get_arg(default=False, name=u'Force', keyvalue=True)   
        
        uri = u'%s/computeservices/instance/stopinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'StopInstancesResponse')\
            .get(u'instancesSet', [])
        headers = [u'id', u'name', u'state',  u'currentState', u'previousState']
        fields = [u'id', u'name', u'state',  u'currentState', u'previousState']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'terminate <id> [recursive=false]'], aliases_only=True)
    @check_error
    def terminate(self):
        """Delete service instance
    - field: can be recursive
        """
        value = self.get_arg(name=u'id')
        data = {
            u'recursive': self.get_arg(name=u'recursive', default=False, keyvalue=True)
        }
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data=data)
        logger.info(res)
        res = {u'msg': u'Delete virtual machine %s' % value}
        self.result(res, headers=[u'msg'])

    @expose()
    @check_error
    def types(self):
        """List virtual machine types
        """
        data = urllib.urlencode({u'plugintype': u'ComputeInstance'})
        uri = u'%s/srvcatalogs/all/defs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        headers = [u'id', u'uuid', u'instance_type', u'version', u'status', u'active', u'creation']
        fields = [u'id', u'uuid', u'name', u'version', u'status', u'active', u'date.creation']
        self.result(res, key=u'servicedefs', headers=headers, fields=fields)


class VpcServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'vpcs'
        description = "Virtual network service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all vpcs by field: owner-id.N, vpc-id.N
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'vpc-id.N'] = self.split_arg(u'vpc-id.N')       
        
        uri = u'%s/computeservices/vpc/describevpcs' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'DescribeVpcsResponse')\
            .get(u'vpcSet', [])
        for item in res:
            item[u'cidr'] = [u'%s' % (i[u'cidrBlock']) for i in item[u'cidrBlockAssociationSet']]
            item[u'cidr'] = u', '.join(item[u'cidr'])
        headers = [u'id', u'name', u'state',  u'account', u'cidr']
        fields = [u'vpcId', u'name', u'state', u'vpcOwnerAlias', u'cidr']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'create <name> <account> <type>'], aliases_only=True)
    @check_error
    def create(self):
        """Create a vpc
        """
        data = {
            u'VpcName': self.get_arg(name=u'name'),
            u'owner_id': self.get_arg(name=u'account'),
            u'VpcType': self.get_arg(name=u'type')
        }
        uri = u'%s/computeservices/vpc/createvpc' % self.baseuri
        res = self._call(uri, u'POST', data={u'vpc': data}, timeout=600)
        logger.info(u'Add vpc: %s' % truncate(res))
        res = res.get(u'CreateVpcResponse').get(u'vpcSet')[0].get(u'vpcId')
        res = {u'msg': u'Add vpc %s' % res}
        self.result(res, headers=[u'msg'])


class SubnetServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'subnets'
        description = "Subnet service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all subnets by field: owner-id.N, subnet-id.N, vpc-id.N
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'subnet-id.N'] = self.split_arg(u'subnet-id.N') 
        dataSearch[u'vpc-id.N'] = self.split_arg(u'vpc-id.N')       

        uri = u'%s/computeservices/subnet/describesubnets' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'DescribeSubnetsResponse')\
            .get(u'subnetSet')
        headers = [u'id', u'name', u'state',  u'account', u'availabilityZone', u'vpc', u'cidr']
        fields = [u'subnetId', u'name', u'state', u'subnetOwnerAlias', u'availabilityZone', u'vpcName', u'cidrBlock']
        self.result(res, headers=headers, fields=fields, maxsize=40)

 
class SGroupServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'securitygroups'
        description = "Security groups service management" 

    @expose(aliases=[u'create <account> <definition> <name>'], aliases_only=True)
    @check_error
    def create_by_id(self):
        """Create service groups
        """
        account = self.get_arg(u'account')
        definition = self.get_arg(u'definition')
        name = self.get_arg(u'name')
        data = {
            u'serviceinst': {
                u'name': name,
                u'desc': name,
                u'account_id': account,
                u'service_def_id': definition,
                u'status': u'ACTIVE',
                u'bpmn_process_id': None,
                u'active': True,
                u'version': u'1.0'
            }
        }
        sg = self._call(u'/v1.0/nws/serviceinsts', u'post', data=data)

    @expose(aliases=[u'create <account> <definition> <name>'], aliases_only=True)
    @check_error
    def create(self):
        """Create service groups
        """
        account = self.get_arg(u'account')
        definition = self.get_arg(u'definition')
        name = self.get_arg(u'name')
        data = {
            u'serviceinst': {
                u'name': name,
                u'desc': name,
                u'account_id': account,
                u'service_def_id': definition,
                u'status': u'ACTIVE',
                u'bpmn_process_id': None,
                u'active': True,
                u'version': u'1.0'
            }
        }
        sg = self._call(u'/v1.0/nws/serviceinsts', u'post', data=data)

        # create config
        data = {
            u'instancecfg': {
                u'name': u'%s-conf' % name,
                u'desc': u'%s-conf' % name,
                u'service_instance_id': sg.get(u'uuid'),
                u'json_cfg': {
                },
            }
        }
        sg_config = self._call(u'/v1.0/nws/instancecfgs', u'post', data=data)

        res = {u'msg': u'Create security group %s' % name}
        self.result(res, headers={u'msg'}, maxsize=100)

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all service groups by field: owner-id.N, subnet-id.N, vpc-id.N
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'subnet-id.N'] = self.split_arg(u'subnet-id.N') 
        dataSearch[u'vpc-id.N'] = self.split_arg(u'vpc-id.N')       
                 
        uri = u'%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True))\
            .get(u'DescribeSecurityGroupsResponse').get(u'securityGroupInfo', [])
        for item in res:
            item[u'egress_rules'] = len(item[u'ipPermissionsEgress'])
            item[u'ingress_rules'] = len(item[u'ipPermissions'])
        headers = [u'id', u'name', u'state',  u'account', u'vpc', u'egress_rules', u'ingress_rules']
        fields = [u'groupId', u'groupName', u'state', u'sgOwnerAlias', u'vpcName', u'egress_rules', u'ingress_rules']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    def __format_rule(self, rules):
        for rule in rules:
            if rule[u'ipProtocol'] == u'-1':
                rule[u'ipProtocol'] = u'*'
            if rule.get(u'fromPort', None) is None or rule[u'fromPort'] == u'-1':
                rule[u'fromPort'] = u'*'
            if rule.get(u'toPort', None) is None or rule[u'toPort'] == u'-1':
                rule[u'toPort'] = u'*'
            if len(rule.get(u'groups', None)) > 0:
                group = rule[u'groups'][0]
                rule[u'groups'] = u'%s:%s' % (group[u'userName'], group[u'groupName'])
            else:
                rule[u'groups'] = u''
            if len(rule.get(u'ipRanges', None)) > 0:
                cidr = rule[u'ipRanges'][0]
                rule[u'ipRanges'] = u'%s' % cidr[u'cidrIp']
            else:
                rule[u'ipRanges'] = u''
        return rules

    @expose(aliases=[u'describe <id>'], aliases_only=True)
    @check_error
    def describe(self):
        """Get service group with rules
        """
        dataSearch = {u'GroupId.N': [self.get_arg(u'id')]}
        uri = u'%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True)) \
            .get(u'DescribeSecurityGroupsResponse').get(u'securityGroupInfo', [])[0]
        egress_rules = self.__format_rule(res.pop(u'ipPermissionsEgress'))
        ingress_rules = self.__format_rule(res.pop(u'ipPermissions'))
        fields = [u'groups', u'ipRanges', u'ipProtocol', u'fromPort', u'toPort']
        self.result(res, details=True, maxsize=40)
        self.app.print_output(u'Egress rules: ')
        self.result(egress_rules, headers=[u'toSecuritygroup', u'toCidr', u'protocol', u'fromPort', u'toPort'],
                    fields=fields, maxsize=60)
        self.app.print_output(u'Ingress rules: ')
        self.result(ingress_rules, headers=[u'fromSecuritygroup', u'fromCidr', u'protocol', u'fromPort', u'toPort'],
                    fields=fields, maxsize=60)


vpcaas_controller_handlers = [
    VPCaaServiceController,    
    VMServiceController,
    ImageServiceController,
    VpcServiceController,
    SubnetServiceController,
    SGroupServiceController
] 
