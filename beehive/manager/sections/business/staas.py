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
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N')
        dataSearch[u'CreationToken'] = self.split_arg(u'name') 
        dataSearch[u'FileSystemId'] = self.split_arg(u'instance_id')
        
        uri = u'%s/storageservices/efs/describefilesystems' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = res.get(u'FileSystems', [])
 
        headers = [u'id', u'name', u'status',  u'date.creation', 
                   u'account', u'NumberOfMountTargets', u'SizeInBytes',  ]
        fields = [u'FileSystemId',  u'CreationToken',  u'LifeCycleState',  u'CreationTime',
                   u'OwnerId', u'NumberOfMountTargets', u'SizeInBytes.Value']
        self.result(res, headers=headers, fields=fields, maxsize=40)


    @expose(aliases=[u'create <name> <account> [field=..]'],
            aliases_only=True)
    @check_error
    def create(self):
        """Create share file system instance
    - field: can be type
        """

        data = {
                u'CreationToken': self.get_arg(name=u'name'), 
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
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
 
    @expose(aliases=[u'describes-target [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes_target(self):
        """Lists all target mounted on a file system instance by field: owner_id, instance_id
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N')
        dataSearch[u'FileSystemId'] = self.split_arg(u'instance_id')
        
        uri = u'%s/storageservices/efs/describemounttargets' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = res.get(u'MountTargets', [])
 
        headers = [u'id', u'name', u'status',  u'date.creation', 
                   u'account', u'target', u'subnet', u'network', u'ipaddress' ]
        fields = [u'FileSystemId',  u'CreationToken',  u'LifeCycleState',  u'CreationTime',
                   u'OwnerId', u'MountTargetId', u'SubnetId', u'NetworkInterfaceId', u'IpAddress' ]
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'create-target <name> <account> [field=..]'],
            aliases_only=True)
    @check_error
    def create_target(self):
        """Create mount target file system instance
    - field: can be type
        """

        data = {
                u'CreationToken': self.get_arg(name=u'name'), 
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
                u'type': self.get_arg(name=u'type', default=__SRV_DEFAULT_STORAGE_EFS_SERVICE_DEF__, keyvalue=True)

        }   
        uri = u'%s/storageservices/efs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete-target <id>'], aliases_only=True)
    @check_error
    def delete_target(self):
        """Delete mount target file system instance
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/storageservices/efs/deletefilesystem' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'FileSystemId': uuid})
        # TODO MANAGEMENT RESPONSE
        logger.info(u'Delete storage efs share instance: %s' % res)
        res = {u'msg': u'Delete share file system instance %s' % uuid}
        self.result(res, headers=[u'msg'])
 
           
staas_controller_handlers = [
    STaaServiceController,
#     STaaServiceControllerChild,
    STaaServiceEFSController,
]         