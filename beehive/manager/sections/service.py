'''
Created on Sep 27, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class ServiceController(BaseController):
    class Meta:
        label = 'service'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Service management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Service management", hide=True)
    def default(self):
        self.app.args.print_help()
        
class ServiceControllerChild(ApiController):
    cataloguri = u'/v1.0/services'
    subsystem = u'service'
    
    cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                   u'date.creation', u'date.modified']
    end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                   u'service', u'active', 
                   u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'service'
        stacked_type = 'nested'
        
class ServiceInternalController(ServiceControllerChild):    
    class Meta:
        label = 'services'
        description = "Service management"
        
    @expose(help="Service management", hide=True)
    def default(self):
        self.app.args.print_help()        
        
service_controller_handlers = [
    ServiceController,
    ServiceInternalController
]        