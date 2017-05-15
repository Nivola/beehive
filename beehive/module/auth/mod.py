from .controller import AuthenticationManager
from .controller import AuthController
from .views import AuthorizationAPI, SimpleHttpAuthApi, KeyAuthApi
from beehive.common.apimanager import ApiModule

class AuthModule(ApiModule):
    """Beehive Authorization Module
    """
    def __init__(self, api_manger):
        self.name = u'AuthModule'
        
        ApiModule.__init__(self, api_manger, self.name)
         
        self.apis = [AuthorizationAPI, SimpleHttpAuthApi, KeyAuthApi]
        self.authentication_manager = AuthenticationManager(api_manger.auth_providers)
        self.controller = AuthController(self)

    def get_controller(self):
        return self.controller

    def set_authentication_providers(self, auth_providers):
        self.authentication_manager.auth_providers = auth_providers