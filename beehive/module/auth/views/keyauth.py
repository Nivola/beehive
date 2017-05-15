"""
Created on Jan 12, 2017

@author: darkbk
"""
from flask import request
from beecell.simple import get_value, str2bool, get_remote_ip
from beehive.common.apimanager import ApiView, ApiManagerError
from beehive.common.data import operation

#
# login, logout
#
class ListDomains(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        auth_providers = controller.module.authentication_manager.auth_providers
        res = []
        for domain, auth_provider in auth_providers.iteritems():
            res.append([domain, auth_provider.__class__.__name__])
        resp = {u'domains':res,
                u'count':len(res)}
        return resp

class Login(ApiView):
    """
     data: {u'user':.., u'password':.., u'login-ip':..}    
    """
    def dispatch(self, controller, data, *args, **kwargs):
        user = get_value(data, u'user', None, exception=True)
        password = get_value(data, u'password', None, exception=True)
        login_ip = get_value(data, u'login-ip', get_remote_ip(request))
        
        try:
            name_domain = user.split(u'@')
            name = name_domain[0]
            try:
                domain = name_domain[1]
            except:
                domain = u'local'
        except:
            ApiManagerError(u'User must be <user>@<domain>')

        innerperms = [
            (1, 1, u'auth', u'objects', u'ObjectContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'role', u'RoleContainer', u'*', 1, u'*'),
            (1, 1, u'auth', u'user', u'UserContainer', u'*', 1, u'*')]
        operation.perms = innerperms     
        res = controller.login(name, domain, password, login_ip)
        resp = res       
        return resp
    
class LoginExists(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.exist_identity(oid)
        return {u'token':oid, u'exist':resp}    

class LoginRefresh(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        uid, sign, data = self.get_current_identity()
        # refresh user permisssions
        res = controller.refresh_user(uid, sign, data)
        resp = res      
        return resp        

class Logout(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        uid, sign, data = self.get_current_identity()
        res = controller.logout(uid, sign, data)
        resp = res      
        return resp

#
# identity
#
class ListIdentities(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        res = controller.get_identities()
        resp = {u'identities':res,
                u'count':len(res)}
        return resp

class GetIdentity(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        data = controller.get_identity(oid)
        res = {
            u'uid':data[u'uid'], 
            u'user':data[u'user'][u'name'],
            u'timestamp':data[u'timestamp'], 
            u'ttl':data[u'ttl'], 
            u'ip':data[u'ip']}
        resp = {u'identity':res}        
        return resp

class DeleteIdentity(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.remove_identity(oid)
        return (resp, 204)

class KeyAuthApi(ApiView):
    """Asymmetric key authentication API
    """
    @staticmethod
    def register_api(module):
        base = u'keyauth'
        rules = [
            (u'%s/login/domains' % base, u'GET', ListDomains, {u'secure':False}),
            (u'%s/login' % base, u'POST', Login, {u'secure':False}),
            (u'%s/login/refresh' % base, u'PUT', LoginRefresh, {}),
            (u'%s/login/<oid>' % base, u'GET', LoginExists, {}),
            (u'%s/logout' % base, u'DELETE', Logout, {}),
            
            (u'%s/identities' % base, u'GET', ListIdentities, {}),
            (u'%s/identities/<oid>' % base, u'GET', GetIdentity, {}),
            (u'%s/identities/<oid>' % base, u'DELETE', DeleteIdentity, {})
        ]
        
        ApiView.register_api(module, rules)