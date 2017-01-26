'''
Created on Apr 7, 2014

@author: darkbk
'''
import ujson as json
import binascii
from urllib import unquote_plus
from datetime import datetime
#from flask.views import MethodView, View
from flask import request
from Crypto.PublicKey import RSA
from Crypto import Random
#from beehive.main import app
#from beehive.module import Resource
#from beehive.module import ObjectManager, ObjectManagerError
from beehive.module.auth.controller import AuthError 
#from beehive.module import UserManager, UserManagerError
#from beehive.module import RoleManager, RoleManagerError
from beehive.common.apimanager import MethodView
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import operation
from beecell.simple import id_gen, get_value
import re

class LoginAPI(MethodView):
    """**LoginAPI**
    
    Login a user to cloudapi.
    
    *Headers*:
    
    *Uri*:
    
    * ``/api/auth/login/domain``, **GET**, Get authentication domains::
    
        *Return*::
        
            {'status':'ok', 
             'api':<http path>,
             'operation':u'GET',
             'data':<http request data>,
             u'response': [[u'comune.torino.it', u'LdapAuth'],
                           [u'domnt.csi.it', u'LdapAuth'],
                           [u'clskdom.lab', u'LdapAuth'],
                           [u'regione.piemonte.it', u'LdapAuth'],
                           [u'provincia.torino.it', u'LdapAuth'],
                           [u'local', u'DatabaseAuth']]} 
    
    * ``/api/auth/login``, **POST**, Login user::
    
        {'user':..,
         'password':..,
         'login_ip':..}

    *Return*::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':{'uid':.., 
                     'user':.., 
                     'timestamp':.., 
                     'pubkey':.., 
                     'seckey':..}}
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}
         
    *Error type*::
    
         1001, 'Input parameter error'
         1002, 'Username is not provided'
         1003, 'Password is not provided'
         1004, 'Domain is not provided'
         1005, 'Invalid credentials'
         1006, 'User is disabled'
         1007, 'Password is expired'
         1008, 'Connection error'
         1010, 'Domain error'
         1010, Undefined
    """
    def get(self, par1, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()
            operation.transaction = id_gen()
            manager = module.get_controller()

            if par1 == 'domain':
                auth_providers = module.authentication_manager.auth_providers
                resp = []
                for domain, auth_provider in auth_providers.iteritems():
                    resp.append([domain, auth_provider.__class__.__name__])
                
                self.logger.debug("Get authentication providers: %s" % resp)
            elif re.match('[A-Za-z0-9]+', par1) is not None:
                resp = manager.exist_identity(par1)
            else:
                raise ApiManagerError('Operation is not supported')

        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    def post(self, module=None):
        try:
            data = json.loads(request.data)
            name_domain = data[u'user'].split(u'@')
            name = name_domain[0]
            password = data[u'password']
            login_ip = get_value(data, u'login_ip', request.environ['REMOTE_ADDR'])
            try:
                domain = name_domain[1]
            except:
                domain = None

            #login_ip = request.environ['REMOTE_ADDR'] #data['login_ip']
        except:
            return self.get_error('ApiManagerError', 400, 'Authentication parameter error')
        
        try:
            # open database session.
            dbsession = module.get_session()    
            
            innerperms = [(1, 1, 'auth', 'objects', 'ObjectContainer', '*', 1, '*'),
                          (1, 1, 'auth', 'role', 'RoleContainer', '*', 1, '*'),
                          (1, 1, 'auth', 'user', 'UserContainer', '*', 1, '*')]
            operation.perms = innerperms     
            controller = module.get_controller()
            res = controller.login(name, domain, password, login_ip)
        except (ApiManagerError) as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 405, str(e))
        finally:
            operation.perms = None
            module.release_session(dbsession)

        return self.get_response(res)
    
    def put(self, par1, module=None):
        res = ''
        if par1 == 'refresh':
            try:
                uid, sign, data = self._get_token()
            except:
                return self.get_error('ApiManagerError', 1001, 'Input parameter error')
                    
            # refresh user permisssions
            try:
                # open database session.
                dbsession = module.get_session()
                
                controller = module.get_controller()
                res = controller.refresh_user(uid, sign, data)
            except ApiManagerError as e:
                return self.get_error('ApiManagerError', e.code, e.value)
            except Exception as e:
                return self.get_error('Exception', 9000, str(e))
            finally:
                operation.perms = None
                module.release_session(dbsession)

        return self.get_response(res)   
    
    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/login/'
        api_view = LoginAPI.as_view('login_api')

        # view methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module, 'secure':False})

        # update methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['PUT'],
                         defaults={'module':module})

        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module, 'secure':False})

class LogoutAPI(MethodView):
    """**LogoutAPI**
    
    Logout a user from cloudapi.
    
    *Headers*:
    
    * **uid** : id of the client identity.
    * **sign**: request signature. Used by server to identify verify client identity.
    * **Accept**: response mime type. Supported: json, bson, xml
    
    *Uri*:
    
    * ``/api/auth/logout``, **POST**, Logout identity

    *Return*::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':{'uid':.., 
                     'user':.., 
                     'timestamp':.., 
                     'pubkey':.., 
                     'seckey':..}}
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}
                 
    """
    def post(self, module=None):
        try:
            uid, sign, data = self._get_token()
        except ApiManagerError as ex:
            return self.get_error('ApiManagerError', ex.code, ex.value)

        # get user permissions from system
        try:
            controller = module.get_controller()
            res = controller.logout(uid, sign, data)
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        

        return self.get_response(res)   

    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/logout/'
        api_view = LogoutAPI.as_view('logout_api')
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module, 'secure':False})

class IdentityAPI(MethodView):
    """**IdentityAPI**
    
    Identity api. Use to get and remove identity on cloudapi.
    
    *Headers*:
    
    * **uid** : id of the client identity.
    * **sign**: request signature. Used by server to identify verify client identity.
    * **Accept**: response mime type. Supported: json, bson, xml
    
    *Uri*:
    
    * ``/api/auth/identity/``, **GET**
    * ``/api/auth/identity/<oid>/``, **GET**
    
    *Return*::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':}
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}
         
    """
    decorators = []
    
    def get(self, identity_id=None, module=None):
        """"""
        controller = module.get_controller()
        try:
            if identity_id is None:                
                res = controller.get_identities()
            else:
                data = controller.get_identity(identity_id)
                res = {'uid':data['uid'], 'user':data['user'].email,
                       'timestamp':data['timestamp'], 'ttl':data['ttl'], 
                       'ip':data['ip']}
     
        except ApiManagerError as ex:
            return self.get_error('ApiManagerError', ex.code, ex.value)

        return self.get_response(res)

    def post(self, module=None):
        """"""
        data = json.loads(request.data)
        return self.get_error('NotImplementedError', 10000, '')

    def delete(self, identity_id, module=None):
        """"""
        controller = module.get_controller()
        try:
            res = controller.remove_identity(identity_id)
        except ApiManagerError as ex:
            return self.get_error('ApiManagerError', ex.code, ex.value)

        return self.get_response(res)

    def put(self, user_id, module=None):
        """"""
        return self.get_error('NotImplementedError', 10000, '')

    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/identity/'
        api_view = IdentityAPI.as_view('identity_api')

        # view methods
        app.add_url_rule(api, view_func=api_view, methods=['GET'],
                         defaults={'module':module})
        app.add_url_rule(api+'<identity_id>/', 
                         view_func=api_view, 
                         methods=['GET'],
                         defaults={'module':module})
        app.add_url_rule(api+'<identity_id>/<par1>/', 
                         view_func=api_view, 
                         methods=['GET'],
                         defaults={'module':module})        
        
        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module})
        
        # update methods
        app.add_url_rule(api+'<oid>', view_func=api_view, methods=['PUT'],
                         defaults={'module':module})
        
        # delete methods
        app.add_url_rule(api+'<identity_id>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module})

class ObjectAPI(MethodView):
    """**ObjectAPI**
    
    Object api. Use to query auth objects, types and actions.
    
    *Headers*:
    
    * **uid** : id of the client identity.
    * **sign**: request signature. Used by server to identify verify client identity.
    * **Accept**: response mime type. Supported: json, bson, xml
    
    *Uri*:

    * ``/api/auth/object/``, **GET**, Get all objects
    * ``/api/auth/object/V:*.*.*.*/``, **GET**, Get objects by unique id
    * ``/api/auth/object/T:auth/``, **GET**, Get objects by type
    * ``/api/auth/object/D:cloudstack.org.grp.volume/``, **GET**, Get objects by definition
    * ``/api/auth/object/perm/``, **GET**, Get all permissions
    * ``/api/auth/object/perm/<id>``, **GET**, Get permission by id <id>
    * ``/api/auth/object/``, **POST**, Add objects::
    
        [(objtype, definition, objid), (objtype, definition, objid)]

    * ``/api/auth/object/<id>/``, **DELETE**, Delete object by <id>
    * ``/api/auth/object/type/``, **GET**, Get types
    * ``/api/auth/object/type/T:resource/``, **GET**, Get type by type    
    * ``/api/auth/object/type/D:orchestrator.org.area.prova/``, **GET**, Get type by definition
    * ``/api/auth/object/type/``, **POST**, Add objects::
    
        [('resource', 'orchestrator.org.area.prova', 'ProvaClass')]

    * ``/api/auth/object/typ/<id>/``, **DELETE**, Delete object type by <id>
    * ``/api/auth/object/action/``, **GET**, Get object actions

    *Return*::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':}
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}
          
    """
    def get(self, par1, par2, par3, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()    
            
            operation.transaction = id_gen()
            controller = module.get_controller()
            manager = controller.objects
            
            if par2 == None:
                # get all objects
                if par1 == None:
                    resp = manager.get()
                    self.logger.debug("Get objects: %s" % len(resp))

                # get object by objid
                elif par1[0:2] == 'I:':
                    objid = par1[2:].replace('_', '//')
                    resp = manager.get(objid=objid)
                    self.logger.debug("Get objects: %s" % len(resp))

                # get object by type
                elif par1[0:2] == 'T:':
                    objtype = par1[2:]
                    resp = manager.get(objtype=objtype)
                    self.logger.debug("Get objects: %s" % len(resp))

                # get object by definition
                elif par1[0:2] == 'D:':
                    objdef = par1[2:]
                    resp = manager.get(objdef=objdef)
                    self.logger.debug("Get objects: %s" % len(resp))
                
                # get object types
                elif par1 == 'type':
                    resp = manager.get_type()
                    self.logger.debug("Get types: %s" % len(resp))
                 
                # get object actions
                elif par1 == 'action':
                    resp = manager.get_action()
                    self.logger.debug("Get actions: %s" % len(resp))

                # get object permissions
                elif par1 == 'perm':
                    resp = manager.get_permission()
                    self.logger.debug("Get permissions: %s" % len(resp))
                    
                # get object by id
                else:
                    resp = manager.get(oid=par1)
                    self.logger.debug("Get objects: %s" % len(resp))       

            # get resource by type, definition and objid
            elif par1[0:2] == 'T:' and par2[0:2] == 'D:' and par3[0:2] == 'I:':
                objtype = par1[2:]
                objdef = par2[2:]
                objid = par3[2:].replace('_', '//')
                resp = manager.get(objtype=objtype, objdef=objdef, objid=objid)
            
            # get resource types by value
            elif par1 == 'type' and par2[0:2] == 'T:': 
                objtype = par2[2:]
                resp = manager.get_type(objtype=objtype)
                self.logger.debug("Get types: %s" % len(resp))
            elif par1 == 'type' and par2[0:2] == 'D:': 
                objdef = par2[2:]
                resp = manager.get_type(objdef=objdef)
                self.logger.debug("Get types: %s" % len(resp))
                
            # get resource permissions
            elif par1 == 'perm':
                if type(par2) is int:
                    resp = manager.get_permission(permission_id=par2)
                else:
                    objid = None
                    objtype = None
                    objdef = None
                    pars = par2.split('+')
                    # get resource type
                    if pars[0][2:] != '': objtype = pars[0][2:]
                    # get resource definition
                    if pars[1][2:] != '': objdef = pars[1][2:]
                    # get resource objid
                    if pars[2][2:] != '': objid = pars[2][2:].replace('_', '//')
                    self.logger.debug("Permission filter: %s, %s, %s" % (objtype, objdef, objid))
                    resp = manager.get_permissions_with_roles(objid=objid, 
                                                              objtype=objtype, 
                                                              objdef=objdef)    
                
                self.logger.debug("Get permissions: %s" % len(resp))
                
            else:
                raise ApiManagerError('Operation is not supported')
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)

    def post(self, par1, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()    

            operation.transaction = id_gen()
            perms = operation.perms
            controller = module.get_controller()
            manager = controller.objects
            
            data = json.loads(request.data)

            # add new resource
            if par1 == None:
                # (objtype, objdef, objid)
                resp = manager.add(data)
                self.logger.debug("Add object %s: %s" % (data, resp))
                                
            # add new resource type
            elif par1 == 'type':
                # (type, objdef, class)
                resp = manager.add_types(data)
                self.logger.debug("Add object type %s: %s" % (data, resp))
            else:
                raise ApiManagerError('Operation is not supported')
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    def delete(self, par1, par2, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()    

            operation.transaction = id_gen()
            perms = operation.perms
            controller = module.get_controller()
            manager = controller.objects
            
            resp = {'operation':'delete', 'type':None, 'data':None, 'response':None}
            
            # remove resource
            if par2 == None:
                resp = manager.remove(oid=par1)
                self.logger.debug("Remove resource %s: %s" % (par1, resp))            
            
            # remove resource type
            elif par1 == 'type':
                resp = manager.remove_type(oid=par2)
                self.logger.debug("Remove resource type %s: %s" % (par2, resp)) 
  
            else:
                raise ApiManagerError('Operation is not supported')
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)

    def put(self, objs, par1, par2):
        """"""
        return self.get_error('NotImplementedError', 2000, '')
    
    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/object/'
        api_view = ObjectAPI.as_view('object_api')

        # view methods
        app.add_url_rule(api, view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par1':None,
                                   'par2':None,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par2':None,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/<par3>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module})        
        
        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module, 
                                   'par1':None})
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['POST'],
                         defaults={'module':module})
        
        # update methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['PUT'],
                         defaults={'module':module})
        
        # delete methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module, 
                                   'par2':None})
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module})
        
class UserAPI(MethodView):
    """**UserAPI**
    
    User api. Use to query auth user.
    
    *Headers*:
    
    * *uid* : id of the client identity.
    * *sign*: request signature. Used by server to identify verify client identity.
    * *Accept*: response mime type. Supported: json, bson, xml
    
    *Uri*:

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
         
    *Return*::
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}         
         
    """
    def get(self, par1, par2, par3, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()
            operation.transaction = id_gen()
            manager = module.get_controller()
            
            # get all users
            if par1 == None:
                users = manager.get_users()
                resp = []
                for user in users:
                    resp.append(user.info())
                
                self.logger.debug("Get users: %s" % resp)

            elif par1 == 'domain':
                auth_providers = module.authentication_manager.auth_providers
                resp = []
                for domain, auth_provider in auth_providers.iteritems():
                    resp.append([domain, auth_provider.__class__.__name__])
                
                self.logger.debug("Get authentication providers: %s" % resp)

            elif par2 == None:
                # get user
                if type(par1) is int: 
                    user = manager.get_users(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    user = manager.get_users(name=par1)[0]
                try: 
                    perms = user.get_permissions()
                except:
                    perms = []
                try: 
                    groups = user.get_groups()
                except:
                    groups = []
                try: 
                    roles = user.get_roles()
                except:
                    roles = []
                    
                resp = user.info()
                resp['perms'] = perms
                resp['groups'] = groups
                resp['roles'] = roles

                self.logger.debug("Get user: %s" % len(resp))

            # get user attributes
            elif par2 == 'attribute':
                # get user
                if type(par1) is int: 
                    user = manager.get_users(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    user = manager.get_users(name=par1)[0]
                resp = user.get_attribs()
            
            # get user roles
            elif par2 == 'role':
                # get user
                if type(par1) is int: 
                    user = manager.get_users(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    user = manager.get_users(name=par1)[0]
                resp = user.get_roles()

            # get user permissions
            elif par2 == 'perm':
                # get user
                if type(par1) is int: 
                    user = manager.get_users(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    user = manager.get_users(name=par1)[0]
                resp = user.get_permissions()
                
            # get user groups
            elif par2 == 'role':
                # get user
                if type(par1) is int: 
                    user = manager.get_users(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    user = manager.get_users(name=par1)[0]
                resp = user.get_groups()          
            
                # verify user authorization
                '''
                elif par2 == 'can':
                    name = par1
                    obj_type, action = par3.split(':')
                    resp = {'operation':'can', 'user':par1, 'type':obj_type, 
                            'action':action, 'values':None}
                    resp['values'] = manager.can(action, obj_type, name=par1)
                    
                    self.logger.debug("Can user %s %s %s: %s" % (par1, action, obj_type, resp))
                '''
            else:
                raise ApiManagerError('Operation is not supported')

        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    def post(self, module=None):
        """
        if generic is True generate generic user else generate custom user
        :param data: {'username':, 'usertype':, 'active':True, 
                      'password':None, 'description':'', 'attribute':'', 
                      'generic':True}
        """
        try:
            # open database session.
            dbsession = module.get_session()
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            # get request data
            data = json.loads(request.data)

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

            self.logger.debug("Add user %s: %s" % (data, resp))
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(True)

    def delete(self, par1, par2, par3, module=None):
        """
        :param par1: user name
        """
        try:
            # open database session.
            dbsession = module.get_session()
            operation.transaction = id_gen()
            controller = module.get_controller()
            # get user
            if type(par1) is int: 
                user = controller.get_users(oid=par1)[0]
            elif type(par1) is str or type(par1) is unicode: 
                user = controller.get_users(name=par1)[0]
            
            if par2 == 'attribute':
                resp = user.remove_attribute(par3)
                self.logger.debug("Delete user %s attribute %s" % (par1, par3))
            else:
                # delete user
                resp = user.delete()
                self.logger.debug("Delete user %s: %s" % (par1, resp))
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)

    def put(self, par1, par2, module=None):
        """
        :param data: {'new_name':, 'new_type':, 
                      'new_description':, 'new_profile':, 'new_attribute':,
                      'new_active':, 'new_password':, 
                      'role':{'append':, 'remove':}}
        """
        try:
            # open database session.
            dbsession = module.get_session()
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            data = json.loads(request.data)
            # get user
            if type(par1) is int: 
                user = controller.get_users(oid=par1)[0]
            elif type(par1) is str or type(par1) is unicode: 
                user = controller.get_users(name=par1)[0]
            resp = {'update':None, 'role.append':[], 'role.remove':[]}
            
            if par2 is None:
                # append, remove role
                if 'role' in data:
                    # append role
                    if 'append' in data['role']:
                        for role in data['role']['append']:
                            res = user.append_role(role)
                            resp['role.append'].append(res)
                
                    # remove role
                    if 'remove' in data['role']:
                        for role in data['role']['remove']:
                            res = user.remove_role(role)
                            resp['role.append'].append(res)
                
                # create user
                for item in ['new_name', 'new_storetype', 'new_description', 
                             'new_active', 'new_password']:
                    if not item in data:
                        data[item] = None
                  
                res = user.update(new_name=data['new_name'],
                                  new_storetype=data['new_storetype'],
                                  new_description=data['new_description'],
                                  new_active=data['new_active'], 
                                  new_password=data['new_password'])
            
                if data['new_name'] is not None:
                    new_name = "%sRole" % data['new_name'].split('@')[0]
                    new_description = 'User %s private role' % data['new_name']
                else:
                    new_name = None
                    new_description = None
                
                try:
                    role = controller.get_roles("%sRole" % par1.split('@')[0])[0]
                    role.update(new_name=new_name, new_description=new_description)
                except:
                    self.logger.warning('Role %s does not exists' % new_name)
                
                resp['update'] = res                 
                
                self.logger.debug("Update user %s: %s" % (par1, resp))
            
            elif par2 == 'attribute':
                if 'new_name' in data: new_name = data['new_name']
                else: new_name = None                  
                if 'value' in data: value = data['value']
                else: value = None               
                if 'desc' in data: desc = data['desc']
                else: desc = None
                attr = user.set_attribute(data['name'], value=value, 
                                          desc=desc, new_name=new_name)
                resp = (attr.name, attr.value, attr.desc)

        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/user/'
        api_view = UserAPI.as_view('user_api')
        
        # view methods
        app.add_url_rule(api, view_func=api_view, methods=['GET'],
                         defaults={'module':module,
                                   'par1':None,
                                   'par2':None,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par2':None,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/<par3>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module})
        
        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module})
        
        # update methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['PUT'],
                         defaults={'module':module,
                                   'par2':None})
        # update methods
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['PUT'],
                         defaults={'module':module})        
        
        # delete methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module,
                                   'par2':None,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module,
                                   'par3':None})
        app.add_url_rule(api+'<par1>/<par2>/<par3>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module})
        
class RoleAPI(MethodView):
    """**RoleAPI**
    
    Role api. Use to query auth role.
    
    *Headers*:
    
    * *uid* : id of the client identity.
    * *sign*: request signature. Used by server to identify verify client identity.
    * *Accept*: response mime type. Supported: json, bson, xml
    
    *Uri*:

    * ``/auth/role/``, **GET**, Get all roles
    * ``/auth/role/<name>/``, **GET**, Get role
    * ``/auth/role/``, **POST**, Create new role::
    
        {'status':'ok', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'response':{'username':, 
                     'description':''}}
         
    * ``/auth/role/<name>/``, **PUT**, Update user::
    
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
    
    * ``/auth/role/<name>/``, **DELETE**, Delete user
    
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
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>,
         'operation':<http method>,
         'data':<http request data>,
         'exception':<exception>,
         'code':<error code>, 
         'msg':<error data>}         
         
    """
    decorators = []

    def get(self, par1, par2, module=None):
        """"""
        try:
            # open database session.
            dbsession = module.get_session()    
            
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            # get all roles
            if par1 == None:
                roles = controller.get_roles()
                resp = []
                for role in roles:
                    resp.append(role.info())
                
                self.logger.debug("Get roles: %s" % resp)
            
            # get role
            elif par2 == None:
                # get role
                if type(par1) is int: 
                    role = controller.get_roles(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    role = controller.get_roles(name=par1)[0]
                resp = role.info()

                self.logger.debug("Get role: %s" % resp)
                
            # get role permissions
            elif par2 == 'perm':
                # get role
                if type(par1) is int:
                    role = controller.get_roles(oid=par1)[0]
                elif type(par1) is str or type(par1) is unicode: 
                    role = controller.get_roles(name=par1)[0]
                
                resp = role.get_permissions()

                self.logger.debug("Get role permissions: %s" % resp)           
                
            # get user with certain role
            elif par2 == 'user':
                users = controller.get_users(role=par1)
                resp = []
                for user in users:
                    resp.append(user.info())
                
                self.logger.debug("Get users with role %s: %s" % (resp, par1))
            else:
                raise ApiManagerError('Operation is not supported')

        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    def post(self, module=None):
        """
        :param data: {'name':.., 'description':.., 'type':.., 'value':..}
        type and value are optional. Use when you want to create role with
        predefined permissions.
        type = admin.cloudapi, value = [<api_id>] - cloudapi admin role
        type = admin.orchestrator, value = [<api_id>, <orch_id>] - cloudapi orchestrator admin role
        type = admin.org, value = [<api_id>, <orch_id>] - cloudapi organization admin role
        type = admin.area, value = [<api_id>, <orch_id>, <org_id>, <area_id>] - cloudapi area admin role
        type = app, value = [<api_id>] - app system role nologin        
        """
        try:
            # open database session.
            dbsession = module.get_session()    
            
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            # get request data
            data = json.loads(request.data)

            # create role with default permissions
            if 'type' in data.keys() and 'value' in data.keys():
                # app system role
                if data['type'] == 'app':
                    resp = controller.add_app_role(data['name'])
            # create role without default permissions
            else:
                resp = controller.add_role(data['name'], data['description'])
            
            self.logger.debug("Add role %s: %s" % (data, resp))
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(True)

    def delete(self, par1, module=None):
        """
        :param par1: user name
        """
        try:
            # open database session.
            dbsession = module.get_session()    
            
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            # delete user
            if type(par1) is int: 
                role = controller.get_roles(oid=par1)[0]
            elif type(par1) is str or type(par1) is unicode: 
                role = controller.get_roles(name=par1)[0]            
            
            resp = role.delete()
            self.logger.debug("Delete role %s: %s" % (par1, resp))
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)

    def put(self, par1, module=None):
        """
        :param data: {'new_name':, 'new_description':,
                      'perm':{'append':[(0, 0, "resource", "cloudstack.org.grp.vm", "", 0, "cs1.*.*.*", "use")], 
                              'remove':[]}}
        """
        try:
            # open database session.
            dbsession = module.get_session()    
            
            operation.transaction = id_gen()
            controller = module.get_controller()
            
            # get request data
            data = json.loads(request.data)
            if type(par1) is int: 
                role = controller.get_roles(oid=par1)[0]
            elif type(par1) is str or type(par1) is unicode: 
                role = controller.get_roles(name=par1)[0]
            resp = {'update':None, 'perm.append':[], 'perm.remove':[]}
            
            # append, remove role
            if 'perm' in data:
                # append role
                if 'append' in data['perm']:
                    perms = []
                    for perm in data['perm']['append']:
                        perms.append(perm)
                    res = role.append_permissions(perms)
                    resp['perm.append'].append(res)
            
                # remove role
                if 'remove' in data['perm']:
                    perms = []
                    for perm in data['perm']['remove']:
                        perms.append(perm)
                    res = role.remove_permissions(perms)
                    resp['perm.remove'].append(res)
            
            # create user
            for item in ['new_name', 'new_description']:
                if not item in data:
                    data[item] = None
            
            res = role.update(new_name=data['new_name'], 
                              new_description=data['new_description'])
            
            resp['update'] = res                  
            
            self.logger.debug("Update role %s: %s" % (par1, resp))
        except ApiManagerError as e:
            return self.get_error('ApiManagerError', e.code, e.value)
        except Exception as e:
            return self.get_error('Exception', 9000, str(e))        
        finally:
            module.release_session(dbsession)

        return self.get_response(resp)
    
    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/auth/role/'
        api_view = RoleAPI.as_view('role_api')
        
        # view methods
        app.add_url_rule(api, view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par1':None,
                                   'par2':None})
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module, 
                                   'par2':None})
        app.add_url_rule(api+'<par1>/<par2>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module})
        
        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module})
        
        # update methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['PUT'],
                         defaults={'module':module})
        
        # delete methods
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['DELETE'],
                         defaults={'module':module})