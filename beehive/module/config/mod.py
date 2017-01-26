from .controller import ConfigController
from .view import ConfigAPI
from beehive.common.apimanager import ApiModule, ApiManagerError
try:
    from .rpc import *
except:
    pass

class ConfigModule(ApiModule):
    def __init__(self, api_manger):
        """ """
        self.name = 'ConfigModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [ConfigAPI]
        self.controller = ConfigController(self)

    def get_controller(self):
        return self.controller