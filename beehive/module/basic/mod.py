from .view import BaseAPI
from .controller import BaiscController
from beehive.common.apimanager import ApiModule

class BasicModule(ApiModule):
    """Beehive Basic Module
    """
    def __init__(self, api_manger):
        self.name = u'BasicModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [BaseAPI]
        self.controller = BaiscController(self)

    def get_controller(self):
        return self.controller