"""
Created on Nov 20, 2017

@author: darkbk
"""

import logging
import urllib
import json

from cement.core.controller import expose
from urllib import urlencode
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
   
     
    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all share file system instances by field: accounts, id, size, page
    - field: accounts, id, size, page
        - accounts: list of account id comma separated
        - id: file system id
        - name: file system name
        - size: number of records
        - page: number of page
        """   
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')  
        data_search[u'CreationToken'] = self.split_arg(u'name') 
        data_search[u'FileSystemId'] = self.split_arg(u'id')
        data_search[u'MaxItems'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Marker'] = self.get_arg(name=u'page', default=0, keyvalue=True)
        page = data_search.get(u'Marker')
        
        uri = u'%s/storageservices/efs/describefilesystems' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        
        total = res.get(u'nvl-fileSystemTotal')
        res = res.get(u'FileSystems', [])
  
        resp = {
            u'count': len(res),
            u'page': page,
            u'total': total,
            u'sort': {u'field': u'date.creation', u'order': u'desc'},
            u'instances': res
        } 
 
        headers = [u'id', u'name', u'status',  u'date.creation', 
                   u'account', u'num.targets', u'size(bytes)',  ]
        fields = [u'FileSystemId',  u'CreationToken',  u'LifeCycleState',  u'CreationTime',
                   u'OwnerId', u'NumberOfMountTargets',  u'SizeInBytes.Value']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)


    @expose(aliases=[u'add <name> <account> <size> <type> '],
            aliases_only=True)
    @check_error
    def add(self):
        """Create share file system instance
        """

        data = {
                u'CreationToken': self.get_arg(name=u'name'), 
                u'owner_id' : self.get_account(self.get_arg(name=u'account')),
#                 u'Nvl-Owner-Id' : self.get_account(self.get_arg(name=u'account')),               
                u'Nvl-FileSystem-Size' : self.get_arg(name=u'size'),
                u'Nvl-FileSystem-Type': self.get_arg(name=u'type')

        }   
        uri = u'%s/storageservices/efs' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'extend-size <oid> <new_size>'], aliases_only=True)
    @check_error
    def extend_size(self):
        """Extend file system share size
    - oid: id or uuid of the file system share instance
    - new_size:  new size to assign
        """
        oid = self.get_arg(name=u'oid')
        params = {
            u'new_size' : self.get_arg(name=u'new_size'),
        }
        uri = u'%s/storageservices/efs/%s/extend' % (self.baseuri, oid)
        self._call(uri, u'PUT', data={u'share': params})
        logger.info(u'Update file system share with data oid=%s params=%s' % (oid, params))
        res = {u'msg': u'Update file system share with data oid=%s params=%s' % (oid, params)}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'shrink-size <oid> <new_size>'], aliases_only=True)
    @check_error
    def shrink_size(self):
        """Update file system share size
    - oid: id or uuid of the file system share instance
    - new_size:  new size to assign
        """
        oid = self.get_arg(name=u'oid')
        params = {
            u'new_size' : self.get_arg(name=u'new_size'),
        }
        uri = u'%s/storageservices/efs/%s/shrink' % (self.baseuri, oid)
        self._call(uri, u'PUT', data={u'share': params})
        logger.info(u'Update file system share with data oid=%s params=%s' % (oid, params))
        res = {u'msg': u'Update file system share with data oid=%s params=%s' % (oid, params)}
        self.result(res, headers=[u'msg'])
         
    @expose(aliases=[u'update <oid> [field=value]'], aliases_only=True)
    @check_error
    def update(self):
        """Update file system share
    - oid: id or uuid of the file system share instance
    - field: can be name, desc
        """
        oid = self.get_arg(name=u'oid')
        params = {
            u'name' : self.get_arg(name=u'name', default=None, keyvalue=True),
            u'desc' : self.get_arg(name=u'desc', default=None, keyvalue=True),
        }
        uri = u'%s/storageservices/efs/%s' % (self.baseuri, oid)
        self._call(uri, u'PUT', data={u'share': params})
        logger.info(u'Update file system share with data oid=%s params=%s' % (oid, params))
        res = {u'msg': u'Update file system share with data oid=%s params=%s' % (oid, params)}
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
        res = {u'msg': u'Delete file system share instance %s' % uuid}
        self.result(res, headers=[u'msg'])
 
    @expose(aliases=[u'target-list [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def target_list(self):
        """Lists all target mounted on a file system instance by field: owner-id.N, instance_id, 
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'owner-id.N')
        data_search[u'FileSystemId'] = self.split_arg(u'instance_id')
        data_search[u'MaxItems'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Marker'] = self.get_arg(name=u'page', default=0, keyvalue=True)
        page = data_search.get(u'Marker')

        uri = u'%s/storageservices/efs/describemounttargets' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        total = res.get(u'nvl-fileSystemTargetTotal')
        res = res.get(u'MountTargets', [])
        
        resp = {
            u'count': len(res),
            u'page': page,
            u'total': total,
            u'sort': {u'field': u'date.creation', u'order': u'desc'},
            u'instances': res
        } 
        
        
        headers = [u'id', u'name', u'status',  u'date.creation', 
                   u'account', u'target', u'proto', u'subnet', u'network', u'ipaddress', u'size(bytes)']
        fields = [u'FileSystemId',  u'CreationToken',  u'LifeCycleState',  u'CreationTime',
                   u'OwnerId', u'MountTargetId', u'nvl_shareProto', u'SubnetId', u'NetworkInterfaceId', u'IpAddress', u'SizeInBytes.Value' ]
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'target-add <id> <subnet>'],
            aliases_only=True)
    @check_error
    def target_add(self):
        """Create mount target to file system share instance
        """

        data = {
                u'FileSystemId': self.get_arg(name=u'id'), 
#                 u'owner_id' : self.get_account(self.get_arg(name=u'account')),
#                 u'Nvl-Owner-Id' : self.get_account(self.get_arg(name=u'account')),   
                u'SubnetId': self.get_arg(name=u'subnet')

        }   
        uri = u'%s/storageservices/efs/createmounttarget' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Mount target to storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Mount target to storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'target-delete <id>'], aliases_only=True)
    @check_error
    def target_delete(self):
        """Delete mount target file system share instance
            id: id or uuid of the file system share instance
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/storageservices/efs/deletemounttarget' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'Nvl-FileSystemId': uuid})
        # TODO MANAGEMENT RESPONSE
        logger.info(u'Delete storage efs share instance: %s' % res)
        res = {u'msg': u'Delete share file system instance %s' % uuid}
        self.result(res, headers=[u'msg'])
 
 
    @expose(aliases=[u'grant-add <id> <access_level> <access_type> <access_to>'],
            aliases_only=True)
    @check_error
    def grant_add(self):
        """Create file system grant
        """

        uuid =  self.get_arg(name=u'id')
        data = { 
            u'access_level' : self.get_arg(name=u'access_level'),
            u'access_type' : self.get_arg(name=u'access_type'),
            u'access_to' : self.get_arg(name=u'access_to'),
        } 
        uri = u'%s/storageservices/efs/%s/grants' % (self.baseuri, uuid)
        res = self._call(uri, u'POST', data={u'share_grant': data}, timeout=600)
        logger.info(u'Add grant to storage efs instance share: %s' % truncate(res))
        res = {u'msg': u'Add grant to storage efs instance share %s' % res}
        self.result(res, headers=[u'msg'])
    
    # TODO MANAGEMENT cli delete_grant command
    @expose(aliases=[u'grant-delete <id> <access_id>'], aliases_only=True)
    @check_error
    def grant_delete(self):
        """Delete grant file system instance
        """

        uuid = self.get_arg(name=u'id')
        access_id = self.get_arg(name=u'access_id')
        data_search = {u'share_grant': {u'access_id': access_id}} 
        uri = u'%s/storageservices/efs/%s/grants' % (self.baseuri, uuid)
        res = self._call(uri, u'DELETE', data=data_search)

        logger.info(u'Delete storage efs share grant: %s' % res)
        res = {u'msg': u'Delete share file system share grant %s' % uuid}
        self.result(res, headers=[u'msg'])

    # TODO MANAGEMENT cli delete_grant command        
    @expose(aliases=[u'grant-list <id>'], aliases_only=True)
    @check_error
    def grant_list(self):
        """List all grants for a share file system instances
        """
        uuid = self.get_arg(name=u'id')
        data_search = {}
        uri = u'%s/storageservices/efs/%s/grants' % (self.baseuri, uuid)
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search))
        filesystem = res.get(u'FileSystem',[])
        headers = [u'id', u'name', u'status',  u'date.creation', 
                   u'account', u'num.targets', u'size(bytes)',  ]
        fields = [u'FileSystemId',  u'CreationToken',  u'LifeCycleState',  u'CreationTime',
                   u'OwnerId', u'NumberOfMountTargets', u'SizeInBytes.Value']
        self.result(filesystem, headers=headers, fields=fields)  
        self.app.print_output(u'Grants:')
        grants = res.get(u'grants', [])            
        self.result(grants, headers=[u'id', u'state', u'level',  u'type', u'to'],
                        fields=[u'id', u'state', u'access_level',  u'access_type', u'access_to'], maxsize=200, table_style=u'simple')
           
staas_controller_handlers = [
    STaaServiceController,
    STaaServiceEFSController,
]         