'''
Created on Dec 31, 2014

@author: darkbk
'''
from .controller import EventController
from .view import EventAPI
from beehive.common.apimanager import ApiModule, ApiManagerError

class EventModule(ApiModule):
    def __init__(self, api_manger):
        """ """
        self.name = u'EventModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [EventAPI]
        self.controller = EventController(self)

    def get_controller(self):
        return self.controller