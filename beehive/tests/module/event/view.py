# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException,\
    ConflictException

oid = None

tests = [
    'test_get_event_types',
    'test_get_event_entities',

    'test_get_events',
    'test_get_events_by_type',
    'test_get_events_by_objtype',
    'test_get_events_by_objdef',
    'test_get_events_by_objid',
    'test_get_events_by_date',
    'test_get_events_by_source',
    'test_get_events_by_data',
    'test_get_event_by_eventid'
]


class EventTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'event'
        self.module_prefix = 'nes'
        self.endpoint_service = 'event'

    def tearDown(self):
        BeehiveTestCase.tearDown(self)
    
    def test_get_event_types(self):
        self.get('/v1.0/nes/events/types')

    def test_get_event_entities(self):
        self.get('/v1.0/nes/events/entities')
        
    def test_get_events(self):
        global event_id, date
        res = self.get('/v1.0/nes/events', query={'page': 1})
        events = res.get('events', [])
        if len(events) > 0:
            event = events[0]
            event_id = event['event_id']
            date = event['date'][:-7]

    def test_get_events_by_type(self):
        self.get('/v1.0/nes/events', query={'type': 'API'})
        
    def test_get_events_by_objtype(self):
        self.get('/v1.0/nes/events', query={'objtype': 'auth'})
        
    def test_get_events_by_objdef(self):
        self.get('/v1.0/nes/events', query={'objtype': 'auth', 'objdef': 'Token'})
        
    def test_get_events_by_objid(self):
        self.get('/v1.0/nes/events', query={'objid': '*'})
        
    def test_get_events_by_date(self):
        global date
        self.get('/v1.0/nes/events', query={'date': date})
        
    def test_get_events_by_source(self):
        self.get('/v1.0/nes/events', query={'source': 'internal'})
        
    def test_get_events_by_data(self):
        self.get('/v1.0/nes/events', query={'data': "'op': {'method': 'POST'}"})
        
    def test_get_event_by_eventid(self):
        global event_id
        self.get('/v1.0/nes/events/{oid}', params={'oid': event_id})


def run(args):
    runtest(EventTestCase, tests, args)


if __name__ == '__main__':
    run({})
