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
from beehive.manager.sections.business import SpecializedServiceControllerChild

logger = logging.getLogger(__name__)


__SRV_DEFAULT_STORAGE_EFS__ =  u'--DEFAULT--storage-efs--'


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


    @expose(aliases=[u'create <name> <account> <size> <type> '],
            aliases_only=True)
    @check_error
    def create(self):
        """Create share file system instance
    - field: can be type if is missing is used default value __SRV_DEFAULT_STORAGE_EFS__
        """

        data = {
                u'CreationToken': self.get_arg(name=u'name'), 
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
#                 u'Nvl-Owner-Id' : self.get_account(self.get_arg(name=u'account')),               
                u'Nvl-FileSystem-Size' : self.get_account(self.get_arg(name=u'size')),
                u'Nvl-FileSystem-Type': self.get_arg(name=u'type')

        }   
        uri = u'%s/storageservices/efs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])


 
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update file system share
    - oid: id or uuid of the file system share instance
    - field: can be name, desc, size
        """
        oid = self.get_arg(name=u'oid')
        params = {}
        params [u'name'] = self.get_arg(name=u'name', default=None, keyvalue=True)
        params [u'desc'] = self.get_arg(name=u'desc', default=None, keyvalue=True)
        params [u'size'] = self.get_arg(name=u'size', default=None, keyvalue=True)
        data = {
            u'share': params
        }
        uri = u'%s/storageservices/efs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data=data)
        logger.info(u'Update file system share %s with data %s' % (oid, params))
        res = {u'msg': u'Update file system share %s with data %s' % (oid, params)}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete share file system instance
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/storageservices/efs/deletefilesystem' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'FileSystemId': uuid}, timeout=300)
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

    @expose(aliases=[u'create-target <id> <subnet>'],
            aliases_only=True)
    @check_error
    def create_target(self):
        """Create mount target to file system share instance
        """

        data = {
                u'FileSystemId': self.get_arg(name=u'id'), 
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
#                 u'Nvl-Owner-Id' : self.get_account(self.get_arg(name=u'account')),   
                u'SubnetId': self.get_arg(name=u'subnet')

        }   
        uri = u'%s/storageservices/efs/createmounttarget' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Mount target to storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Mount target to storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete-target <id>'], aliases_only=True)
    @check_error
    def delete_target(self):
        """Delete mount target file system share instance
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/storageservices/efs/deletefilesystem' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'FileSystemId': uuid})
        # TODO MANAGEMENT RESPONSE
        logger.info(u'Delete storage efs share instance: %s' % res)
        res = {u'msg': u'Delete share file system instance %s' % uuid}
        self.result(res, headers=[u'msg'])
 
 
    @expose(aliases=[u'create-grant <id> <access_level> <access_type> <access_to>'],
            aliases_only=True)
    @check_error
    def create_grant(self):
        """Create file system grant
        """

        uuid =  self.get_arg(name=u'id')
        data = { 
            u'access_level' : self.get_arg(name=u'access_level'),
            u'access_type' : self.get_arg(name=u'access_type'),
            u'access_to' : self.get_arg(name=u'access_to'),
        } 
        uri = u'%s/storageservices/efs/%s/grant' % (self.baseuri, uuid)
        res = self._call(uri, u'POST', data={u'share_grant': data}, timeout=600)
        logger.info(u'Add grant to storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add grant to storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])
    
    # TODO MANAGEMENT cli delete_grant command
    @expose(aliases=[u'delete-grant <id> <access_id>'], aliases_only=True)
    @check_error
    def delete_grant(self):
        """Delete grant file system instance
        """

        uuid = self.get_arg(name=u'id')
        access_id = self.get_arg(name=u'access_id')
        data = {
            u'access_id': access_id
        } 
        uri = u'%s/storageservices/efs/%s/grant' % (self.baseuri, uuid)
        res = self._call(uri, u'DELETE', data={u'share_grant': data})
        # TODO MANAGEMENT RESPONSE
        logger.info(u'Delete storage efs share grant: %s' % res)
        res = {u'msg': u'Delete share file system share grant %s' % uuid}
        self.result(res, headers=[u'msg'])

    # TODO MANAGEMENT cli delete_grant command        
    @expose(aliases=[u'list-grant <id>'], aliases_only=True)
    @check_error
    def list_grant(self):
        """List all grants for a share file system instances by field: ???
        """
        uuid = self.get_arg(name=u'id')
        dataSearch = {}
        
        uri = u'%s/storageservices/efs/%s/grant' % (self.baseuri, uuid)
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = []
 
        headers = [ ]
        fields = []
        self.result(res, headers=headers, fields=fields, maxsize=40)        
           
staas_controller_handlers = [
    STaaServiceController,
#     STaaServiceControllerChild,
    STaaServiceEFSController,
]         