# -*- coding: utf-8 -*-
'''
Created on Nov 14, 2015

@author: darkbk
'''
from .view import SchedulerAPI, TaskAPI
from .controller import SchedulerController
from beehive.common.apimanager import ApiModule

class SchedulerModule(ApiModule):
    """Beehive Scheduler Module
    """
    def __init__(self, api_manger):
        self.name = u'SchedulerModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [SchedulerAPI, TaskAPI]
        self.api_plugins = {}
        self.controller = SchedulerController(self)

    def get_controller(self):
        return self.controller