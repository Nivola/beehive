'''
Created on Dec 31, 2014

@author: darkbk
'''
from beehive.common.apimanager import ApiModule
from beehive.module.event.view import EventAPI
from beehive.module.event.controller import EventController

class EventModule(ApiModule):
    """Event Beehive Module
    """
    def __init__(self, api_manger):
        self.name = u'EventModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [EventAPI]
        self.controller = EventController(self)

    def get_controller(self):
        return self.controller