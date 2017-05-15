"""
Created on Apr 28, 2017

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
        login_ip = get_value(data, u'login-ip', None, exception=True)
        
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
        resp = controller.simple_http_login(name, domain, password, login_ip)    
        return resp
    
class SimpleHttpAuthApi(ApiView):
    """Simple http authentication API
    """
    @staticmethod
    def register_api(module):
        base = u'simplehttp'
        rules = [
            (u'%s/login/domains' % base, u'GET', ListDomains, {u'secure':False}),
            (u'%s/login' % base, u'POST', Login, {u'secure':False})
        ]
        
        ApiView.register_api(module, rules)    
    
    