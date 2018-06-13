'''
Created on 05 giu 2018
 
@author: fabrizio
'''
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from cement.core.controller import expose
import logging
import urllib
from base64 import b64encode
 
logger = logging.getLogger(__name__)


class SshController(BaseController):
    class Meta:
        label = 'ssh'
        stacked_on = 'base'
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
        label = 'ssh.groups'
        aliases = ['groups']
        aliases_only = True
        description = "Openstack System management"

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
         
    @expose(aliases=[u'add <name> [desc=..] [attribute=..]'], aliases_only=True)
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
        label = 'ssh.nodes'
        aliases = ['nodes']
        aliases_only = True
        description = "Ssh nodes management"
         
    @expose(aliases=[u'list [group_oid=..] [ip_address=..]'], aliases_only=True)
    @check_error
    def list(self):
        '''List all sshnode
            - group_oid
        '''
        group_oid = self.get_arg(name=u'group_oid', keyvalue=True, default=None)
        ip_address = self.get_arg(name=u'ip_address', keyvalue=True, default=None)
        if group_oid is not None:
            data = {u'group_oid': group_oid}
        if ip_address is not None:
            data = {u'ip_address': ip_address}

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
         
    @expose(aliases=[u'add <name> <group_oid> <node_type> <ip_address> [desc=..] [attribute=..]'], aliases_only=True)
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


class SshUserController(SshControllerChild):
    class Meta:
        label = 'ssh.users'
        aliases = ['users']
        aliases_only = True
        description = "Ssh users management"  
         
    @expose(aliases=[u'list <node_oid> [username=..]'], aliases_only=True)
    @check_error
    def list(self):
        '''List all sshuser
            - node_oid
        '''
        node_oid = self.get_arg(name=u'node_oid')
        username = self.get_arg(name=u'username', keyvalue=True, default=None)
        data = {
            u'node_oid': node_oid
        }
        if username is not None:
            data[u'username'] = username

#         data_search = {}
        uri = u'%s/sshusers' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        #res = self._call(uri, u'GET', data=data)
        self.result(res, details=True) 
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshuser by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshusers/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshuser', details=True)  
         
    @expose(aliases=[u'add <name> <node_oid> <key_oid> <username> <password>[desc=..] [attribute=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new ssh user 
             -name
             -node_oid
             -key_oid
             -username
             -password
        """
        name = self.get_arg(name=u'name')
        desc = self.get_arg(name=u'desc', keyvalue=True, default=u'')
        attribute = self.get_arg(name=u'attribute', keyvalue=True, default=u'')
        node_oid = self.get_arg(name=u'node_oid')
        key_oid = self.get_arg(name=u'key_oid')
        username = self.get_arg(name=u'username')
        password = self.get_arg(name=u'password')
        data = {
            u'sshuser': {
                u'name': name,
                u'desc': desc,
                u'attribute': attribute,
                u'node_oid': node_oid,
                u'key_oid': key_oid,
                u'username': username,
                u'password': password
            }
        }
        uri = u'%s/sshusers' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)
         
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get sshuser permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshusers/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=None)
        logger.info(u'Get sshuser perms: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)      
        
        
class SshKeyController(SshControllerChild):
    class Meta:
        label = 'ssh.keys'
        aliases = ['keys']
        aliases_only = True
        description = "Ssh keys management"  
         
    @expose(aliases=[u'list [user_oid=..]'], aliases_only=True)
    @check_error
    def list(self):
        '''List all sshkey'''
         
        user_oid = self.get_arg(name=u'user_oid', keyvalue=True, default=None)
        data = u''
        if user_oid is not None:
            data = {
                u'user_oid': user_oid
            }

        uri = u'%s/sshkeys' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
#         res = self._call(uri, u'GET')
        self.result(res, details=True) 
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshkey by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshkeys/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshkey', details=True)  
         
    @expose(aliases=[u'add <name> <priv_key> <pub_key> [desc=..] [attribute=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new ssh key 
         -name
         -priv_key
         -pub_key
        """
        name = self.get_arg(name=u'name')
        priv_key = self.get_arg(name=u'priv_key')
        pub_key = self.get_arg(name=u'pub_key')
        desc = self.get_arg(name=u'desc', keyvalue=True, default=u'')
        attribute = self.get_arg(name=u'attribute', keyvalue=True, default=u'')
        priv_key = self.load_file(priv_key)
        pub_key = self.load_file(pub_key)
        data = {
            u'sshkey': {
                u'name': name,
                u'priv_key': b64encode(priv_key),
                u'pub_key': b64encode(pub_key),
                u'desc': desc,
                u'attribute': attribute
            }
        }
        uri = u'%s/sshkeys' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        msg = {u'msg': res}
        self.result(msg, headers=[u'msg'], maxsize=200)
         
    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get sshkey permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshkeys/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=None)
        logger.info(u'Get sshkey perms: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)  
 
ssh_controller_handlers = [
        SshController,
        SshGroupController,
        SshNodeController,
        SshUserController,
        SshKeyController
    ]
 
 
 
 
 
 
 
 

