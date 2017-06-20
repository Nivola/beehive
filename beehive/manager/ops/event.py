'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager
import sys
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class EventManager(ApiManager):
    """
    SECTION:
        event
    
    PARAMS:
        types list
        entities list
        events list <field>=<value>
        events get <event_id> 
        
        Possible fields are:
        - page     results are pagenated in page of default size = 10. To change page showed pass this param
        - size     use this to change number of evente returned per page
        - type     filter events by destination object type
        - data     filter events by some key in data
        - source   filter events by some key in source
        - datefrom filter events by start date. Ex. '2015-3-9-15-23-56'
        - dateto   filter events by end date. Ex. '2015-3-9-15-23-56'
        - objid    entity id 
        - objtype  entity type
        - objdef   entity definition 
    """
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        self.baseuri = u'/v1.0/events'
        self.subsystem = u'event'
        self.logger = logger
        self.msg = None
        self.headers = [
            #u'id',
            u'event_id',
            #u'objtype',
            #u'objdef',
            #u'objid',
            u'type',
            u'date',
            u'data.op',
            u'data.opid',
            u'data.elapsed',
            u'data.response',
            u'source.user',
            u'source.ip'
        ]
    
    def actions(self):
        actions = {
            u'types.list': self.get_types,
            u'entities.list': self.get_entities,
            u'events.list': self.get_events,
            u'events.get': self.get_event
        }
        return actions    
    
    #
    # node types
    #
    def get_types(self):
        uri = u'%s/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get event types: %s' % truncate(res))
        self.result(res, key=u'event-types', headers=[u'event type'])
        
    def get_entities(self):
        uri = u'%s/entities/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get event entities: %s' % truncate(res))
        self.result(res, key=u'event-entities', headers=[u'event entity'])        

    def get_events(self, *args):
        data = self.format_http_get_query_params(*args)
        params = self.get_query_params(*args)
        uri = u'%s/' % (self.baseuri)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(u'Get events: %s' % truncate(res))
        print(u'Page: %s' % res[u'page'])
        print(u'Count: %s' % res[u'count'])
        print(u'Total: %s' % res[u'total'])
        print(u'Order: %s %s' % (params.get(u'field', u'id'), 
                                 params.get(u'order', u'DESC')))        
        self.result(res, key=u'events', headers=self.headers)
    
    def get_event(self, oid):
        uri = u'%s/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get event: %s' % truncate(res))
        self.result(res, key=u'event', headers=self.headers, details=True)
