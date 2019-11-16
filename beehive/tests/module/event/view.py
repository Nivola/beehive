# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException,\
    ConflictException

oid = None

tests = [
    'test_get_event_types',
    'test_get_event_entities',
    
    'test_get_events',
    # 'test_get_events_by_type',
    # 'test_get_events_by_objtype',
    # 'test_get_events_by_objdef',
    # 'test_get_events_by_objid',
    # 'test_get_events_by_date',
    # 'test_get_events_by_source',
    # 'test_get_events_by_data',
    # 'test_get_event_by_id',
    # 'test_get_event_by_eventid'
]


class EventTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
    
    def test_get_event_types(self):
        self.call('event', '/v1.0/nes/events/types', 'get', 
                  **self.users['admin'])

    def test_get_event_entities(self):
        self.call('event', '/v1.0/nes/events/entities', 'get', 
                  **self.users['admin'])
        
    def test_get_events(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'page':1},
                  **self.users['admin'])        
        
    def test_get_events_by_type(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'type':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_objtype(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'objtype':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_objdef(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'objdef':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_objid(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'objid':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_date(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'date':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_source(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'source':'internal'},
                  **self.users['admin'])
        
    def test_get_events_by_data(self):
        self.call('event', '/v1.0/nes/events', 'get',
                  query={'data':'internal'},
                  **self.users['admin'])        
        
    def test_get_event_by_id(self):
        self.call('event', '/v1.0/nes/events/{oid}', 'get',
                  params={'oid':4}, 
                  **self.users['admin'])
        
    def test_get_event_by_eventid(self):
        self.call('event', '/v1.0/nes/events/{oid}', 'get',
                  params={'oid':4}, 
                  **self.users['admin'])


if __name__ == '__main__':
    runtest(EventTestCase, tests)  