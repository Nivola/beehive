"""
Created on 05 giu 2018
 
@author: fabrizio
"""
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
        """List all sshgroup"""
        uri = u'%s/sshgroups' % self.baseuri
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshgroups',
                    headers=[u'id', u'name', u'date'],
                    fields=[u'uuid', u'name', u'date.creation'])
     
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

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete sshgroup by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshgroups/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE')
        logger.info(u'Delete sshgroup %s' % value)
        msg = {u'msg': u'Delete sshgroup %s' % value}
        self.result(msg, headers=[u'msg'])

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

    @expose(aliases=[u'node-add <group> <node>'], aliases_only=True)
    @check_error
    def node_add(self):
        """Add node to group

        """
        group = self.get_arg(name=u'group')
        node = self.get_arg(name=u'node')
        data = {
            u'sshnode': node
        }
        uri = u'%s/sshgroups/%s/sshnode' % (self.baseuri, group)
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        msg = {u'msg': u'Add node %s to group %s' % (node, group)}
        self.result(msg, headers=[u'msg'], maxsize=200)

    @expose(aliases=[u'node-del <group> <node>'], aliases_only=True)
    @check_error
    def node_del(self):
        """Delete node from group

        """
        group = self.get_arg(name=u'group')
        node = self.get_arg(name=u'node')
        data = {
            u'sshnode': node
        }
        uri = u'%s/sshgroups/%s/sshnode' % (self.baseuri, group)
        res = self._call(uri, u'DELETE', data=data)
        logger.info(res)
        msg = {u'msg': u'Delete node %s from group %s' % (node, group)}
        self.result(msg, headers=[u'msg'], maxsize=200)


class SshNodeController(SshControllerChild):
    class Meta:
        label = 'ssh.nodes'
        aliases = ['nodes']
        aliases_only = True
        description = "Ssh nodes management"
         
    @expose(aliases=[u'list [group=..] [ip_address=..] [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List all sshnode
    - field can be: group_id, ip_address, page, size, id, order
        """
        group_oid = self.get_arg(name=u'group', keyvalue=True, default=None)
        ip_address = self.get_arg(name=u'ip_address', keyvalue=True, default=None)
        data = self.get_list_default_arg()
        if group_oid is not None:
            data[u'group_id'] = group_oid
        if ip_address is not None:
            data[u'ip_address'] = ip_address

        uri = u'%s/sshnodes' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        self.result(res, key=u'sshnodes',
                    headers=[u'id', u'name', u'desc', u'ip_address', u'date'],
                    fields=[u'uuid', u'name', u'desc', u'ip_address', u'date.creation'])
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshnode by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshnodes/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET').get(u'sshnode', {})
        if self.format in [u'text', u'table']:
            users = res.pop(u'users', [])
            groups = res.pop(u'groups', [])
            self.result(res, details=True)

            self.output(u'Groups:')
            self.result(groups, headers=[u'id', u'name'])

            self.output(u'Users:')
            self.result(users, headers=[u'id', u'name'])
        else:
            self.result(res, details=True)
         
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

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete sshnode by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshnodes/%s' % (self.baseuri, value)
        res = self._call(uri, u'DELETE', data=u'')
        logger.info(u'Delete sshnode: %s' % res)
        msg = {u'msg': u'Delete sshnode: %s' % value}
        self.result(msg, headers=[u'msg'])

    @expose(aliases=[u'perms <id>'], aliases_only=True)
    @check_error
    def perms(self):
        """Get sshnode permissions by id, uuid or name
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshnodes/%s/perms' % (self.baseuri, value)
        res = self._call(uri, u'GET', data=u'')
        logger.info(u'Get sshnode perms: %s' % res)
        self.result(res, key=u'perms', headers=self.perm_headers)

    @expose(aliases=[u'connect [id=..] [name=..] [ip=..] [user=..]'], aliases_only=True)
    @check_error
    def connect(self):
        """Opens ssh connection to node
        """
        host_name = self.get_arg(name=u'name', default=None, keyvalue=True)
        host_ip = self.get_arg(name=u'ip', default=None, keyvalue=True)
        host_id = self.get_arg(name=u'id', default=None, keyvalue=True)
        user = self.get_arg(name=u'user', default=None, keyvalue=True, required=True)

        if host_name is None and host_ip is None and host_id is None:
            raise Exception(u'At node ip address or name or id is required')

        self.ssh2node(host_id=host_id, host_ip=host_ip, host_name=host_name, user=user)

    @expose(aliases=[u'actions [node=..] [field=..]'], aliases_only=True)
    @check_error
    def actions(self):
        """List sshnode actions
    - field can be: group_id, ip_address, page, size, id, order
        """
        node = self.get_arg(name=u'node', keyvalue=True, default=u'*')
        datefrom = self.get_arg(name=u'datefrom', keyvalue=True, default=None)
        dateto = self.get_arg(name=u'dateto', keyvalue=True, default=None)
        data = self.get_list_default_arg()
        if datefrom is not None:
            data[u'datefrom'] = datefrom
        if dateto is not None:
            data[u'dateto'] = dateto
        uri = u'%s/sshnodes/%s/actions' % (self.baseuri, node)
        res = self._call(uri, u'GET', data=urllib.urlencode(data))
        self.result(res, key=u'actions',
                    headers=[u'id', u'date', u'user', u'user-ip', u'action-id', u'action', u'elapsed', u'node-name',
                             u'node-user', u'status'],
                    fields=[u'id', u'date', u'user.user', u'user.ip', u'action_id', u'action', u'elapsed', u'node_name',
                            u'node_user.name', u'status'])


class SshUserController(SshControllerChild):
    class Meta:
        label = 'ssh.users'
        aliases = ['users']
        aliases_only = True
        description = "Ssh users management"  
         
    @expose(aliases=[u'list [node=..] [username=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all sshuser
            - node_oid
        """
        node = self.get_arg(name=u'node', keyvalue=True, default=None)
        username = self.get_arg(name=u'username', keyvalue=True, default=None)
        data = self.get_list_default_arg()
        if node is not None:
            data[u'node'] = node
        if username is not None:
            data[u'username'] = username

        uri = u'%s/sshusers' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        self.result(res, key=u'sshusers',
                    headers=[u'id', u'name', u'date', u'node'],
                    fields=[u'uuid', u'username', u'date.creation', u'node_name'])
     
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
        """List all sshkey"""
         
        user_oid = self.get_arg(name=u'user_oid', keyvalue=True, default=None)
        data = u''
        if user_oid is not None:
            data = {
                u'user_oid': user_oid
            }

        uri = u'%s/sshkeys' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        self.result(res, key=u'sshkeys',
                    headers=[u'id', u'name', u'desc', u'date', u'pub_key'],
                    fields=[u'uuid', u'name', u'desc', u'date.creation', u'pub_key'])
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get sshkey by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/sshkeys/%s' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.result(res, key=u'sshkey', details=True)
         
    @expose(aliases=[u'add <name> <priv_key> [pub_key=..] [desc=..] [attribute=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Add new ssh key 
         -name
         -priv_key
         -pub_key
        """
        name = self.get_arg(name=u'name')
        priv_key = self.get_arg(name=u'priv_key')
        pub_key = self.get_arg(name=u'pub_key', keyvalue=True, default=None)
        desc = self.get_arg(name=u'desc', keyvalue=True, default=u'')
        attribute = self.get_arg(name=u'attribute', keyvalue=True, default=u'')
        priv_key = self.load_file(priv_key)
        if pub_key is not None:
            pub_key = self.load_file(pub_key)
        else:
            pub_key = u''
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
 
 
 
 
 
 
 
 


