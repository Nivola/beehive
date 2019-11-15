# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from beehive.common.test import runtest
from beehive.tests.module.auth.view import AuthTestCase
from beehive.tests.module.event.view import EventTestCase
from beehive.tests.module.basic.view import BaseTestCase
from beehive.tests.module.catalog.view import CatalogTestCase
from beehive.tests.module.scheduler.view import SchedulerAPITestCase


tests_event = [
    # 'test_get_event_types',
    # 'test_get_event_entities',

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


class TestCase(EventTestCase):
    validation_active = False

    def setUp(self):
        EventTestCase.setUp(self)
        self.module = 'event'
        self.module_prefix = 'nes'
        self.endpoint_service = 'event'

    def test_get_event_types(self):
        self.get('/v1.0/nes/events/types')

    def test_get_event_entities(self):
        self.get('/v1.0/nes/events/entities')

    def test_get_events(self):
        self.get('/v1.0/nes/events', query={'page': 1})

    def test_get_events_by_type(self):
        self.get('/v1.0/nes/events', query={'type': 'internal'})

    def test_get_events_by_objtype(self):
        self.get('/v1.0/nes/events', query={'objtype': 'internal'})

    def test_get_events_by_objdef(self):
        self.get('/v1.0/nes/events', query={'objdef': 'internal'})

    def test_get_events_by_objid(self):
        self.get('/v1.0/nes/events', query={'objid': 'internal'})

    def test_get_events_by_date(self):
        self.get('/v1.0/nes/events', query={'date': 'internal'})

    def test_get_events_by_source(self):
        self.get('/v1.0/nes/events', query={'source': 'internal'})

    def test_get_events_by_data(self):
        self.get('/v1.0/nes/events', query={'data': 'internal'})

    def test_get_event_by_id(self):
        self.get('/v1.0/nes/events/{oid}', params={'oid': 4})

    def test_get_event_by_eventid(self):
        self.get('/v1.0/nes/events/{oid}', params={'oid': 4})


tests = []
for test_plans in [
    tests_event
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == '__main__':
    run()
