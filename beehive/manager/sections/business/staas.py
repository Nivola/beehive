"""
Created on Nov 20, 2017

@author: darkbk
"""

import logging
import urllib
import json

from cement.core.controller import expose

from beehive.manager.util.controller import BaseController, ApiController, check_error
from beecell.simple import truncate
from beehive_service.service_util import __SRV_DEFAULT_STORAGE_EFS_SERVICE_DEF__
from beehive.manager.sections.business import SpecializedServiceControllerChild

logger = logging.getLogger(__name__)

class STaaServiceController(BaseController):
    class Meta:
        label = 'staas'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Storage as a Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
class STaaServiceControllerChild(SpecializedServiceControllerChild):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'
 
    class Meta:
        stacked_on = 'staas'
        stacked_type = 'nested'
   

class STaaServiceEFSController(STaaServiceControllerChild):
    class Meta:
        label = 'storage.efs'
        aliases = ['efs']
        aliases_only = True
        description = "Storage file system service management"
   
     
    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all share file system instances by field: owner_id, instance_id
        """
        dataSearch = {}
        dataSearch[u'owner_id_N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'CreationToken'] = self.arg(u'name') 
        dataSearch[u'FileSystemId'] = self.arg(u'instance_id')
        uri = u'%s/storageservices/efs/describefilesystems' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = res.get(u'FileSystems', [])
 
        headers = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size',  ]
        fields = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size', ]
        self.result(res, headers=headers, fields=fields, maxsize=40)


    @expose(aliases=[u'create <name> <account> [field=..]'],
            aliases_only=True)
    @check_error
    def create(self):
        """Create share file system instance
    - field: can be type
        """

        data = {
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
                u'CreationToken': self.get_arg(name=u'name'), 
                u'type': self.get_arg(name=u'type', default=__SRV_DEFAULT_STORAGE_EFS_SERVICE_DEF__, keyvalue=True)

        }   
        uri = u'%s/storageservices/efs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete share file system instance
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/storageservices/efs/deletefilesystem' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'FileSystemId': uuid})
        # TODO MANAGEMENT RESPONSE
        logger.info(u'Delete storage efs share instance: %s' % res)
        res = {u'msg': u'Delete share file system instance %s' % uuid}
        self.result(res, headers=[u'msg'])
 
 
 
    @expose(aliases=[u'describes_target [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes_target(self):
        """List all mount target for a share file system instances by field: owner_id, instance_id
        """
        dataSearch = {}
        dataSearch[u'owner_id'] = self.split_arg(u'owner_id') 
        dataSearch[u'CreationToken'] = self.split_arg(u'name') 
        dataSearch[u'FileSystemId'] = self.split_arg(u'instance_id')
        uri = u'%s/storageservices/efs/describemounttarget' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = res.get(u'MountTargetDescription', [])
 
        headers = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size',  ]
        fields = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size', ]
        self.result(res, headers=headers, fields=fields, maxsize=40) 
     

    @expose(aliases=[u'create_target <instance_id> <account> <subnet_id>'], aliases_only=True) 
    @check_error  
    def create_target(self):
        """Create mount file system target
        """

        data = {
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
                u'FileSystemId': self.get_arg(name=u'instance_id'), 
                u'SubnetId': self.get_arg(name=u'subnet_id')

        }   
        uri = u'%s/storageservices/efs/createmounttarget' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Mount target to instance share file system: %s' % truncate(res))
        
        
        res = res.get(u'FileSystems', [])
 
        headers = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size',  ]
        fields = [u'id', u'name', u'status', u'active', u'date.creation', u'AvailabilityZone',
                   u'IpAddress', u'NetworkInterfaceId', u'SubnetId', u'OwnerId',
                   u'MountTargetId', u'NumberOfMountTargets', u'Size', ]
        
        self.result(res, headers=headers, fields=fields, maxsize=40)          
        
    @expose(aliases=[u'delete_target <id>'], aliases_only=True)
    @check_error
    def delete_target(self):
        """Delete file system mount target
        """      

    pass
           
staas_controller_handlers = [
    STaaServiceController,
#     STaaServiceControllerChild,
    STaaServiceEFSController,
]         