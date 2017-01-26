from .controller import AuthenticationManager
from .controller import AuthController
from .view import LoginAPI, LogoutAPI, IdentityAPI, ObjectAPI, UserAPI, RoleAPI
from beehive.common.apimanager import ApiModule, ApiManagerError

class AuthModule(ApiModule):
    """"""
    
    def __init__(self, api_manger):
        """ """
        self.name = u'AuthModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        #AuthRPC(self).register_rpc_function()
         
        self.apis = [LoginAPI, LogoutAPI, IdentityAPI, ObjectAPI, UserAPI, RoleAPI]
        self.authentication_manager = AuthenticationManager(api_manger.auth_providers)
        self.controller = AuthController(self)

    def get_controller(self):
        return self.controller    

    def set_authentication_providers(self, auth_providers):
        self.authentication_manager.auth_providers = auth_providers