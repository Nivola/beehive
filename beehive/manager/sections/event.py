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


class EventController(BaseController):
    class Meta:
        label = 'event'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Event Service management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class EventControllerChild(ApiController):
    cataloguri = u'/v1.0/events'
    subsystem = u'event'
    
    cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                   u'date.creation', u'date.modified']
    end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                   u'service', u'active', 
                   u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'event'
        stacked_type = 'nested'


class EventInternalController(EventControllerChild):    
    class Meta:
        label = 'events'
        description = "Catalog management"


event_controller_handlers = [
    EventController,
    EventInternalController
]        