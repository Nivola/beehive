'''
Created on Jan 26, 2017

@author: darkbk
'''
from re import match
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError

class UserApiView(ApiView):
    """
    * ``/auth/user/``, **GET**, Get all users
    * ``/auth/user/<name>/``, **GET**, Get user
    * ``/auth/user/<name>/role/``, **GET**, Get user roles
    * ``/auth/user/<name>/perm/``, **GET**, Get user permissions
    * ``/auth/user/<name>/group/``, **GET**, Get user groups
    * ``/auth/user/``, **POST**, Create new user::

        *Return*::
        
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':{'username':, 
                     'usertype':, 
                     'profile':, 
                     'active':True, 
                     'password':None, 
                     'description':'', 
                     'attribute':''}}
         
    * ``/auth/user/<name>/``, **PUT**, Update user::
    
        *Return*::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':{'new_name':, 
                     'new_type':, 
                     'new_description':, 
                     'new_profile':, 
                     'new_attribute':,
                     'new_active':, 
                     'new_password':, 
                     'role':{'append':, 'remove':}}}
    
    * ``/auth/user/<name>/``, **DELETE**, Delete user    
    """
    def get_user(self, controller, oid):
        # get user by id
        if match('[0-9]+', str(oid)):
            user = controller.get_users(oid=oid)
        # get user by value
        else:
            user = controller.get_users(name=oid)        
        
        if len(user) == 0:
            raise ApiManagerError(u'User %s not found' % oid, code=404)
        return user[0]

#
# user api
#
class ListUsers(UserApiView):
    """List users
    """
    def dispatch(self, controller, name, data, *args, **kwargs):
        users = controller.get_users(app=name)
        res = [r.info() for r in users]
        resp = {u'users':res,
                u'count':len(res)}
        return resp

class GetUser(UserApiView):
    """Get user
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        res = user.detail()
        resp = {u'user':res}        
        return resp
    
class GetUserRoles(UserApiView):
    """Get user roles
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        res = user.get_roles()
        resp = {u'user_roles':res}        
        return resp
    
class GetUserPerms(UserApiView):
    """Get user perms
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        res = user.get_permissions()
        resp = {u'user_perms':res}        
        return resp
    
class GetUserGroups(UserApiView):
    """Get user groups
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        res = user.get_groups()
        resp = {u'user_groups':res}        
        return resp
    
class GetUserAttribs(UserApiView):
    """Get user groups
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        res = user.get_attribs()
        resp = {u'user_attribs':res}        
        return resp    
    
class CreateUser(UserApiView):
    """Create User

    {
        u'user':{
            u'username':, 
            u'usertype':, 
            u'active':True, 
            u'password':None, 
            u'description':'', 
            u'attribute':'', 
            u'generic':True
        }
    }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'user', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        zone = get_value(data, u'zone', None, exception=True)
        
        
        # create user
        password = None
        if 'password' in data:
            password = data['password']
        if 'generic' in data and data['generic'] == True:
            resp = controller.add_generic_user(data['username'], 
                                               data['storetype'], 
                                               password=password, 
                                               description=data['description'])
        elif 'system' in data and data['system'] == True:
            resp = controller.add_system_user(data['username'],
                                              password=password, 
                                              description=data['description'])                
        else:
            resp = controller.add_user(data['username'], 
                                       data['storetype'],
                                       data['systype'],
                                       active=data['active'], 
                                       password=data['password'], 
                                       description=data['description'])
        
        resp = controller.add_user(name, desc, zone)
        return (resp, 201)

class UpdateUser(UserApiView):
    """Update user
    """            
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        data = get_value(data, u'user', None, exception=True)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        zone = get_value(data, u'zone', None)
        resp = user.update(new_name=name, new_desc=desc, new_zone=zone)
        return resp
    
class DeleteUser(UserApiView):
    """Delete user
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        resp = user.delete()
        return (resp, 204)

class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'users', u'GET', ListUsers, {}),
            (u'user/<oid>', u'GET', GetUser, {}),
            (u'user/<oid>/roles', u'GET', GetUserRoles, {}),
            (u'user/<oid>/perms', u'GET', GetUserPerms, {}),
            (u'user/<oid>/groups', u'GET', GetUserGroups, {}),
            (u'user/<oid>/attributes', u'GET', GetUserAttribs, {}),
            (u'user', u'POST', CreateUser, {}),
            (u'user/<oid>', u'PUT', UpdateUser, {}),
            (u'user/<oid>', u'DELETE', DeleteUser, {})
        ]

        ApiView.register_api(module, rules)