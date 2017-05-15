'''
Created on Jan 28, 2015

@author: darkbk
'''
from .controller import CatalogController
from .view import CatalogAPI
from beehive.common.apimanager import ApiModule

class CatalogModule(ApiModule):
    """Catalog Module. This module depends by Auth Module and does not work 
    without it. Good deploy of this module is in server instance with Auth 
    Module.
    """
    def __init__(self, api_manger):
        self.name = u'CatalogModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [CatalogAPI]
        self.controller = CatalogController(self)

    def get_controller(self):
        return self.controller