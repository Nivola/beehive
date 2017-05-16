'''
Created on May 3, 2017

@author: darkbk
'''
from beehive.common.apimanager import ApiModule
from beehive.module.oauth2.view import Oauth2Api
from beehive.module.auth.controller import AuthenticationManager
from beehive.module.oauth2.controller import Oauth2Controller

class Oauth2Module(ApiModule):
    """Oauth2 Beehive Module
    """
    def __init__(self, api_manger):
        self.name = u'Oauth2Module'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        #AuthRPC(self).register_rpc_function()
         
        self.apis = [Oauth2Api]
        self.authentication_manager = AuthenticationManager(api_manger.auth_providers)
        self.controller = Oauth2Controller(self)

    def get_controller(self):
        return self.controller

    def set_authentication_providers(self, auth_providers):
        self.authentication_manager.auth_providers = auth_providers