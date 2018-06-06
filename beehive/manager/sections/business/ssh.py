'''
Created on 05 giu 2018
 
@author: fabrizio
'''
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from cement.core.controller import expose
import logging
 
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
         
    @expose(aliases=[u'list [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def list(self):
        '''List all accounts'''
         
#         data_search = {}
        uri = u'%s/sshgroups' % self.baseuri
#         res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = self._call(uri, u'GET', data=None)
        return res
     
    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get account by value or id
        """
        value = self.get_arg(name=u'id')
        uri = u'%s/ssh/%s' % (self.baseuri, value)
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
 
ssh_controller_handlers = [
    SshController,
    SshGroupController
    ]
 
 
 
 
 
 
 
 


