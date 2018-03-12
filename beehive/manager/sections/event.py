"""
Created on Sep 27, 2017

@author: darkbk
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate
from beehive.manager.sections.scheduler import WorkerController, ScheduleController, TaskController

logger = logging.getLogger(__name__)


class EventController(BaseController):
    class Meta:
        label = 'audit'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Event Service management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class EventControllerChild(ApiController):
    baseuri = u'/v1.0/nes'
    subsystem = u'event'
    
    cat_headers = [u'id', u'uuid', u'name', u'zone', u'active', 
                   u'date.creation', u'date.modified']
    end_headers = [u'id', u'uuid', u'name', u'catalog.name', 
                   u'service', u'active', 
                   u'date.creation', u'date.modified']
    
    class Meta:
        stacked_on = 'audit'
        stacked_type = 'nested'
        
        
class EventWorkerController(EventControllerChild, WorkerController):
    class Meta:
        label = 'event.workers'
        aliases = ['workers']
        aliases_only = True
        description = "Worker management"


class EventTaskController(EventControllerChild, TaskController):
    class Meta:
        label = 'event.tasks'
        aliases = ['tasks']
        aliases_only = True
        description = "Task management"


class EventScheduleController(EventControllerChild, ScheduleController):
    class Meta:
        label = 'event.schedules'
        aliases = ['schedules']
        aliases_only = True
        description = "Schedule management"


class EventInternalController(EventControllerChild):
    baseuri = u'/v1.0/nes/events'
    headers = [u'event_id', u'type', u'date', u'data.op', u'data.opid', u'data.elapsed', u'data.response',
               u'source.user', u'source.ip']

    class Meta:
        label = 'events'
        description = "Event management"

    @expose()
    @check_error
    def types(self):
        """List event types
        """
        uri = u'%s/types' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(u'Get event types: %s' % truncate(res))
        self.result(res, key=u'event_types', headers=[u'event type'])

    @expose()
    @check_error
    def entities(self):
        """List event entities
        """
        uri = u'%s/entities' % self.baseuri
        res = self._call(uri, u'GET')
        logger.info(u'Get event entities: %s' % truncate(res))
        self.result(res, key=u'event_entities', headers=[u'event entity'])

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    @check_error
    def list(self):
        """List events. Possible fields are:
    - page     results are pagenated in page of default size = 10. To change page showed pass this param
    - size     use this to change number of evente returned per page
    - type     filter events by destination object type
    - data     filter events by some key in data
    - source   filter events by some key in source
    - dest     filter events by some key in dest
    - date     filter events by date.
    - datefrom filter events by start date. Ex. '2015-3-9-15-23-56'
    - dateto   filter events by end date. Ex. '2015-3-9-15-23-56'
    - objid    entity id
    - objtype  entity type
    - objdef   entity definition
        """
        data = self.format_http_get_query_params(*self.app.pargs.extra_arguments)
        uri = self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(u'Get events: %s' % truncate(res))
        self.result(res, key=u'events', headers=self.headers)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self, oid):
        """Get event by id"""
        uri = u'%s/%s' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        logger.info(u'Get event: %s' % truncate(res))
        self.result(res, key=u'event', headers=self.headers, details=True)


event_controller_handlers = [
    EventController,
    EventInternalController,
    EventWorkerController,
    EventScheduleController,
    EventTaskController
]        