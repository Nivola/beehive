'''
Created on Aug 18, 2017

@eventor: darkbk
'''
import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException,\
    ConflictException

oid = None

tests = [
    u'test_get_event_types',
    u'test_get_event_entities',
    
    u'test_get_events',
    # u'test_get_events_by_type',
    # u'test_get_events_by_objtype',
    # u'test_get_events_by_objdef',
    # u'test_get_events_by_objid',
    # u'test_get_events_by_date',
    # u'test_get_events_by_source',
    # u'test_get_events_by_data',
    # u'test_get_event_by_id',
    # u'test_get_event_by_eventid'
]


class EventTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
    
    def test_get_event_types(self):
        self.call(u'event', u'/v1.0/events/types', u'get', 
                  **self.users[u'admin'])

    def test_get_event_entities(self):
        self.call(u'event', u'/v1.0/events/entities', u'get', 
                  **self.users[u'admin'])
        
    def test_get_events(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'page':1},
                  **self.users[u'admin'])        
        
    def test_get_events_by_type(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'type':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_objtype(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'objtype':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_objdef(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'objdef':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_objid(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'objid':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_date(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'date':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_source(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'source':u'internal'},
                  **self.users[u'admin'])
        
    def test_get_events_by_data(self):
        self.call(u'event', u'/v1.0/events', u'get',
                  query={u'data':u'internal'},
                  **self.users[u'admin'])        
        
    def test_get_event_by_id(self):
        self.call(u'event', u'/v1.0/events/{oid}', u'get',
                  params={u'oid':4}, 
                  **self.users[u'admin'])
        
    def test_get_event_by_eventid(self):
        self.call(u'event', u'/v1.0/events/{oid}', u'get',
                  params={u'oid':4}, 
                  **self.users[u'admin'])


if __name__ == u'__main__':
    runtest(EventTestCase, tests)  