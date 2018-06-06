'''
Created on 05 giu 2018
 
@author: fabrizio
'''
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from cement.core.controller import expose
import logging
import urllib
 
logger = logging.getLogger(__name__)
 
class SshController(BaseController):
    class Meta:
        label = 'ssh'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "SSH Service management"
        arguments = []
  
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
         
class SshControllerChild(ApiController):
    baseuri = u'/v1.0/gas'
    subsystem = u'ssh'
  
    class Meta:
        stacked_on = 'ssh'
        stacked_type = 'nested'
         
class SshGroupController(SshControllerChild):
    class Meta:
        label = 'ssh-groups'
        description = "Ssh groups management"  
         
    @expose(aliases=[u'list '], aliases_only=True)
    @check_error
    def list(self):
        '''List all sshgroup'''
         
#         data_search = {}
        uri = u'%s/sshgroups' % self.baseuri
#         res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = self._call(uri, u'GET')
        self.result(res, details=True) 
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshgroup by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshgroups/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshgroup', details=True)  
         
    @expose(aliases=[u'sshgroup-add <name> [desc=..] [attribute=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new ssh group 
             
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc', keyvalue=True, default=u'')
        attribute = self.get_arg(name=u'attribute', keyvalue=True, default=u'')
        data = {
            u'sshgroup': {
                u'name': name,
                u'desc': desc,
                u'attribute': attribute
            }
        }
        uri = u'%s/sshgroups' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)
         
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get sshgroup permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshgroups/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=None)
        logger.info(u'Get sshgroup perms: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)
        
class SshNodeController(SshControllerChild):
    class Meta:
        label = 'ssh-nodes'
        description = "Ssh nodes management"  
         
    @expose(aliases=[u'list <group_oid>'], aliases_only=True)
    @check_error
    def list(self):
        '''List all sshnode
            - group_oid
        '''
        group_oid = self.get_arg(name=u'group_oid')
        data = {
            u'group_oid': group_oid
             }   
        logger.warn(u'_____________1________________')
        logger.warn(group_oid)
        logger.warn(data)
#         data_search = {}
        uri = u'%s/sshnodes' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        #res = self._call(uri, u'GET', data=data)
        self.result(res, details=True) 
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshnode by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshnodes/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshnode', details=True)  
         
    @expose(aliases=[u'sshnode-add <name> <group_oid> <node_type> <ip_address>[desc=..] [attribute=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new ssh node 
             -name
             -group_oid
             -node_type
             -ip_address
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc', keyvalue=True, default=u'')
        attribute = self.get_arg(name=u'attribute', keyvalue=True, default=u'')
        group_oid = self.get_arg(name=u'group_oid')
        node_type = self.get_arg(name=u'node_type')
        ip_address = self.get_arg(name=u'ip_address')
        data = {
            u'sshnode': {
                u'name': name,
                u'desc': desc,
                u'attribute': attribute,
                u'group_oid': group_oid,
                u'node_type': node_type,
                u'ip_address': ip_address
            }
        }
        uri = u'%s/sshnodes' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)
         
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get sshnode permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshnodes/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=None)
        logger.info(u'Get sshnode perms: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)
        
 
ssh_controller_handlers = [
    SshController,
    SshGroupController,
    SshNodeController
    ]
 
 
 
 
 
 
 
 


