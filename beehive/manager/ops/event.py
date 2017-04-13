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
        events list
        events get <id> 
    """
    def __init__(self, auth_config):
        ApiManager.__init__(self, auth_config)
        self.baseuri = u'/v1.0/events'
        self.subsystem = u'event'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'types.list': self.get_types,
            u'events.list': self.get_events,
            u'events.get': self.get_event
        }
        return actions    
    
    #
    # node types
    #
    def get_types(self):
        uri = u'%s/events/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get event types: %s' % truncate(res))
        self.result(res)

    def get_events(self, value):
        uri = u'%s/events/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get events: %s' % truncate(res))
        self.result(res)
    
    def get_event(self, oid):
        uri = u'%s/events/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get event: %s' % truncate(res))
        self.result(res)
