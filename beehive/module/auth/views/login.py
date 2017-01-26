'''
Created on Jan 26, 2017

@author: darkbk
'''
from re import match
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError
from beehive.common.data import operation
from flask import request

class LoginApiView(ApiView):
    def get_identity(self, controller, oid):
        obj = controller.get_identities(oid)
        if len(obj) == 0:
            raise ApiManagerError(u'Indentity %s not found' % oid, code=404)
        return obj[0]

#
# login api
#
class ListDomains(LoginApiView):
    """ """
    def dispatch(self, controller, data, name, *args, **kwargs):
        auth_providers = controller.module.authentication_manager.auth_providers
        res = []
        for domain, auth_provider in auth_providers.iteritems():
            res.append([domain, auth_provider.__class__.__name__])
        resp = {u'domains':res,
                u'count':len(res)}
        return resp

class VerifyIdentity(LoginApiView):
    """ """
    def dispatch(self, controller, data, uid, *args, **kwargs):
        resp = controller.exist_identity(uid)    
        return resp
    
class Login(LoginApiView):
    """
    """
    def dispatch(self, controller, data, *args, **kwargs):
        user = get_value(data, u'user', None, exception=True)
        password = get_value(data, u'password', None, exception=True)
        login_ip = get_value(data, u'login_ip', request.environ[u'REMOTE_ADDR'])
        name_domain = user.split(u'@')
        name = name_domain[0]
        try:
            domain = name_domain[1]
        except:
            domain = u'local'
        
        innerperms = [(1, 1, 'auth', 'objects', 'ObjectContainer', '*', 1, '*'),
                      (1, 1, 'auth', 'role', 'RoleContainer', '*', 1, '*'),
                      (1, 1, 'auth', 'user', 'UserContainer', '*', 1, '*')]
        operation.perms = innerperms
        resp = controller.login(name, domain, password, login_ip)
        return (resp, 201)

class RefreshIdentity(LoginApiView):
    """
    """            
    def dispatch(self, controller, data, *args, **kwargs):
        uid, sign, data = self._get_token()
        resp = controller.refresh_user(uid, sign, data)
        return resp
    
class Logout(LoginApiView):
    """
    """
    def dispatch(self, controller, data, *args, **kwargs):
        uid, sign, data = self._get_token()
        resp = controller.logout(uid, sign, data)
        return (resp, 204)

#
# identity api
#
class ListIdentities(LoginApiView):
    """ """
    def dispatch(self, controller, data, *args, **kwargs):
        res = controller.get_identities()
        resp = {u'identities':res,
                u'count':len(res)}
        return resp

class GetIdentity(LoginApiView):
    """ """
    def dispatch(self, controller, data, uid, *args, **kwargs):
        data = self.get_identity(controller, uid)
        res = {u'uid':data[u'uid'], u'user':data[u'user'].email,
               u'timestamp':data[u'timestamp'], u'ttl':data[u'ttl'], 
               u'ip':data[u'ip']}        
        resp = {u'identity':res}
        return resp

class DeleteIdentity(LoginApiView):
    """
    """
    def dispatch(self, controller, data, uid, *args, **kwargs):
        resp = controller.remove_identity(uid)
        return (resp, 204)

class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'auth/login/domain', u'GET', ListDomains, {u'secure':False}),
            (u'auth/login', u'POST', Login, {u'secure':False}),
            (u'auth/login/<uid>', u'GET', VerifyIdentity, {}),
            (u'auth/login/refresh', u'PUT', RefreshIdentity, {}),
            (u'auth/logout', u'PUT', Logout, {}),
            
            (u'auth/identities', u'GET', ListIdentities, {}),
            (u'auth/identity/<uid>', u'GET', GetIdentity, {}),
            (u'auth/identity/<uid>', u'DELETE', DeleteIdentity, {})
        ]

        ApiView.register_api(module, rules)
