"""
Created on Nov 20, 2017

@author: darkbk
"""

import logging

from beehive.manager.util.controller import BaseController, ApiController



class STaaServiceController(BaseController):
    class Meta:
        label = 'staas'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Storage as a Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
class StaaServiceControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'staas'
 
    class Meta:
        stacked_on = 'staas'
        stacked_type = 'nested'
     
      
staas_controller_handlers = [
    STaaServiceController,
]         