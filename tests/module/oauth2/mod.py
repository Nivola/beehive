from gibboncloudapi.module.auth.controller import AuthenticationManager
from .controller import Oauth2Controller
from .view import Oauth2Api
from gibboncloudapi.module.base import ApiModule

class Oauth2Module(ApiModule):
    """"""
    
    def __init__(self, api_manger):
        """ """
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