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
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True)).get(u'DescribeInstancesResponse').get(u'reservationSet')[0].get(u'instancesSet')
        self.result(res,
            headers=[u'instanceId',u'instanceType',u'instanceState', u'launchTime',u'hypervisor',  
                        u'availabilityZone',u'privateIp',u'imageId',u'vpcId',u'subnetId'],
            fields=[u'instanceId',u'instanceType',u'instanceState.name',u'launchTime',u'hypervisor',
                        u'placement.availabilityZone',u'privateIpAddress',u'imageId', u'vpcId',
                        u'subnetId'],
            maxsize=40)

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

    @expose(aliases=[u'terminate <id> [force=true/false]'], aliases_only=True)
    @check_error
    def terminate(self):
        """Delete a virtual machine
        """
        value = self.get_arg(name=u'id')
        force = self.get_arg(name=u'force', default=False, keyvalue=True)
        uri = u'%s/serviceinsts/%s' % (self.baseuri, value)
        # workaround to delete resource
        # res = self._call(uri, u'GET')



        res = self._call(uri, u'DELETE')
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

    @expose(aliases=[u'describe <id>'], aliases_only=True)
    @check_error
    def describe(self):
        """Get service group with rules
        """
        dataSearch = {}
        dataSearch[u'GroupId_N'] = [self.get_arg(u'id')]
        print urllib.urlencode(dataSearch, doseq=True)

        uri = u'%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True)) \
            .get(u'DescribeSecurityGroupsResponse').get(u'securityGroupInfo', [])
        for item in res:
            item[u'egress_rules'] = len(item[u'ipPermissionsEgress'])
            item[u'ingress_rules'] = len(item[u'ipPermissions'])
        headers = [u'id', u'name', u'state', u'account', u'vpc', u'egress_rules', u'ingress_rules']
        fields = [u'groupId', u'groupName', u'state', u'sgOwnerAlias', u'vpcName', u'egress_rules', u'ingress_rules']
        self.result(res, headers=headers, fields=fields, maxsize=40)
      
       
vpcaas_controller_handlers = [
    VPCaaServiceController,    
    VMServiceController,
    ImageServiceController,
    VpcServiceController,
    SubnetServiceController,
    SGroupServiceController
] 
