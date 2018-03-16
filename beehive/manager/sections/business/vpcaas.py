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
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True)).get(u'DescribeImagesResponse').get(u'imagesSet',[])
        self.result(res, 
                    headers=[u'imageId', u'name', u'imageState', u'imageType'],
                    fields=[ u'imageId', u'name', u'imageState', u'imageType'],
                    maxsize=40)

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
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True)).get(u'DescribeInstancesResponse').get(u'reservationSet')
        self.result(res,
            headers=[u'instanceId',u'instanceType',u'instanceState', u'launchTime',u'hypervisor',  
                        u'availabilityZone',u'privateIpAddress',u'imageId',u'vpcId',u'subnetId', 
                        u'hypervisor',u'cidrBlockAssociationSet.0.cidrBlock'],
            fields=[u'instanceId',u'instanceType',u'instanceState.name',u'launchTime',u'hypervisor',
                        u'placement.availabilityZone',u'privateIpAddress',u'imageId', u'vpcId', 
                        u'subnetId',u'hypervisor',u'cidrBlockAssociationSet.0.cidrBlock'],
            maxsize=40)


#     @expose(aliases=[u'runinstance <owner_id> <InstanceType> <ImageId> [Name][AdditionalInfo][AdminPassword][SubnetId][SecurityGroupIds]'],
#             aliases_only=True)
#     @check_error
#     def runinstance(self):
#         """create VM instance <owner_id><InstanceType><ImageId>
#             - field: can be owner_id, Name, AdditionalInfo, InstanceType, AdminPassword, ImageId, SecurityGroupIds, SubnetId 
#         """
#         data = {
#             u'instance': {
#                 u'owner_id': self.get_arg(name=u'owner_id'),
#                 u'ImageId' : self.get_arg(name=u'ImageId'),
#                 u'InstanceType' : self.get_arg(name=u'InstanceType'),
#                 
#                 u'AdditionalInfo' : self.get_arg(name=u'AdditionalInfo', default=u'', keyvalue=True),             
#                 u'Name': self.get_arg(name=u'Name', default=u'default name instance'),
#                 u'AdminPassword' : self.get_arg(name=u'AdminPassword', default=u'myPwd$1', keyvalue=True),
#                 u'SecurityGroupId.N' : self.split_arg(u'SecurityGroupId_N'),
#                 u'SubnetId'  :   self.get_arg(name=u'SubnetId', default=None, keyvalue=True),    
#             }
#         }
#       
#         uri = u'%s/computeservices/instance/runinstances' % (self.baseuri)
#         res = self._call(uri, u'POST', data=data)
#         logger.info(u'Add virtual machine instance: %s' % truncate(res))
#         res = {u'msg': u'Add virtual machine instance %s' % res}
#         self.result(res, headers=[u'msg'])


    @expose(aliases=[u'runinstance [<file data>]'],
            aliases_only=True)
    @check_error
    def runinstance(self):
        """create VM instance
    - file data: json file with instance data set to create a VM
        """
        file_data = self.get_arg(name=u'data file')
        data = self.load_config(file_data)     
        uri = u'%s/computeservices/instance/runinstances' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add virtual machine instance: %s' % truncate(res))
        res = {u'msg': u'Add virtual machine instance %s' % res}
        self.result(res, headers=[u'msg'])


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
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'DescribeVpcsResponse').get(u'vpcSet', [])
        self.result(res,
                    headers=[u'vpcId', u'state', u'cidrBlock', u'cidrBlockAssociationSet.associationId'],
                    fields=[ u'vpcId',u'state',u'cidrBlockAssociationSet.0.cidrBlock',u'cidrBlockAssociationSet.0.associationId'],
                    maxsize=40)

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
        res = self._call(uri, u'GET', data=urlencode(dataSearch, doseq=True)).get(u'DescribeSubnetsResponse').get(u'subnetSet')       
        self.result(res,
            headers=[u'subnetId',u'state',u'availabilityZone',u'cidrBlock',u'vpcId',u'mapPublicIpOnLaunch',u'assignIpv6AddressOnCreation',u'defaultForAz'],
            fields=[ u'subnetId',u'state',u'availabilityZone',u'cidrBlock',u'vpcId',u'mapPublicIpOnLaunch',u'assignIpv6AddressOnCreation',u'defaultForAz'],
            maxsize=40)

 
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
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True)).get(u'DescribeSecurityGroupsResponse').get(u'securityGroupInfo', [])
        self.result(res, 
                    headers=[u'groupId',u'groupName',u'vpcId',u'ipPermissions.cidr', u'ipPermissionsEgress.cidr' ],
                    fields=[ u'groupId',u'groupName',u'vpcId',u'ipPermissions.0.ipRanges.0.cidrIp', u'ipPermissionsEgress.0.ipRanges.0.cidrIp'],
                    maxsize=40)        

      
       
vpcaas_controller_handlers = [
    VPCaaServiceController,    
    VMServiceController,
    ImageServiceController,
    VpcServiceController,
    SubnetServiceController,
    SGroupServiceController
] 
