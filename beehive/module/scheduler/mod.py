'''
Created on Nov 14, 2015

@author: darkbk
'''
from beehive.common.apimanager import ApiModule, ApiManagerError
from .view import SchedulerAPI, TaskAPI
from .controller import SchedulerController

class SchedulerModule(ApiModule):
    def __init__(self, api_manger):
        """ """
        self.name = u'SchedulerModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [SchedulerAPI, TaskAPI]
        self.api_plugins = {}
        self.controller = SchedulerController(self)

    def get_controller(self):
        return self.controller