'''
Created on Sep 22, 2017

@author: darkbk
'''
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController

logger = logging.getLogger(__name__)

class AuthController(BaseController):
    class Meta:
        label = 'auth'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Authorization management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Authorization management", hide=True)
    def default(self):
        self.app.args.print_help()
        
class AuthControllerChild(ApiController):
    baseuri = u'/v1.0/keyauth'
    simplehttp_uri = u'/v1.0/simplehttp'
    authuri = u'/v1.0/auth'
    subsystem = u'auth'
    
    obj_headers = [u'id', u'objid', u'subsystem', u'type', u'desc']
    type_headers = [u'id', u'subsystem', u'type']
    act_headers = [u'id', u'value']
    perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', 
                         u'aid', u'action']
    user_headers = [u'id', u'uuid', u'name', u'active', 
                         u'date.creation', u'date.modified', u'date.expiry']
    role_headers = [u'id', u'uuid', u'name', u'active', 
                         u'date.creation', u'date.modified', u'date.expiry']
    group_headers = [u'id', u'uuid', u'name', u'active', 
                          u'date.creation', u'date.modified', u'date.expiry']    
    
    class Meta:
        stacked_on = 'auth'
        stacked_type = 'nested'
        
class UserController(AuthControllerChild):    
    class Meta:
        label = 'users'
        description = "User management"
        
    @expose(help="User management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'add <name> <password> [<expirydate>=dd-mm-yyyy] [<storetype>]'], 
            aliases_only=True)
    def add(self):
        """Add user <value>
        """
        name = self.get_arg(name=u'name')
        pwd = self.get_arg(name=u'pwd')
        expiry_date = self.get_arg(name=u'expiry_date')
        data = {
            u'user':{ 
                u'name':name,
                u'active':True,
                u'password':pwd, 
                u'desc':u'User %s' % name, 
                u'base':True,
                u'expirydate':expiry_date
            }
        }
        uri = u'%s/users' % self.baseuri        
        res = self._call(uri, u'POST', data=data)
        logger.info(res)
        res = {u'msg':u'Add user %s' % res[u'uuid']}
        self.result(res, headers=[u'msg'])

    @expose
    def count(self):
        """Count all user
        """        
        uri = u'%s/users/count' % self.baseuri        
        res = self._call(uri, u'GET')
        logger.info(res)
        res = {u'msg':u'Tags count %s' % res[u'count']}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        """List all users by field: page, size, order, field, role, group, expirydate
    - field can be: id, objid, uuid, name, description, creation_date, 
    modification_date, expiry_date, active
    - expirydate syntax: dd-mm-yyyy        
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/users' % self.baseuri        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'users', headers=self.user_headers)
    
    @expose(aliases=[u'get <id>'], aliases_only=True)
    def get(self):
        """Get user by value or id
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/users/%s' % (self.baseuri, value)        
        res = self._call(uri, u'GET')
        logger.info(res)
        self.result(res, key=u'user', headers=self.user_headers, 
                    details=True)

    @expose(aliases=[u'perms <value>'], aliases_only=True)
    def perms(self):
        """Get user permissions
        """
        value = self.get_arg(name=u'value')
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = u'%s/users/%s/perms' % (self.baseuri, value)        
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        self.result(res, key=u'perms', headers=self.perm_headers)
    
    @expose(aliases=[u'update <value> <new_value>'], aliases_only=True)
    def update(self):
        """Update user with new value
        """
        value = self.get_arg(name=u'value')
        new_value = self.get_arg(name=u'new value')
        data = {
            u'resourceuser':{
                u'value':new_value
            }
        }
        uri = u'%s/users/%s' % (self.baseuri, value)        
        res = self._call(uri, u'PUT', data=data)
        logger.info(res)
        res = {u'msg':u'Update user %s' % value}
        self.result(res, headers=[u'msg'])  
    
    @expose(aliases=[u'delete <value>'], aliases_only=True)
    def delete(self):
        """Delete user
        """
        value = self.get_arg(name=u'value')
        uri = u'%s/users/%s' % (self.baseuri, value)        
        res = self._call(uri, u'DELETE')
        logger.info(res)
        res = {u'msg':u'Delete user %s' % value}
        self.result(res, headers=[u'msg'])        
        
resource_controller_handlers = [
    AuthController,
    UserController,
    RoleController,
    GroupController,
    ObjectController
]                
        
        