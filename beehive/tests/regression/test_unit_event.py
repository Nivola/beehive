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
    # u'test_get_event_types',
    # u'test_get_event_entities',

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


class TestCase(EventTestCase):
    validation_active = False

    def setUp(self):
        EventTestCase.setUp(self)
        self.module = u'event'
        self.module_prefix = u'nes'
        self.endpoint_service = u'event'

    def test_get_event_types(self):
        self.get(u'/v1.0/nes/events/types')

    def test_get_event_entities(self):
        self.get(u'/v1.0/nes/events/entities')

    def test_get_events(self):
        self.get(u'/v1.0/nes/events', query={u'page': 1})

    def test_get_events_by_type(self):
        self.get(u'/v1.0/nes/events', query={u'type': u'internal'})

    def test_get_events_by_objtype(self):
        self.get(u'/v1.0/nes/events', query={u'objtype': u'internal'})

    def test_get_events_by_objdef(self):
        self.get(u'/v1.0/nes/events', query={u'objdef': u'internal'})

    def test_get_events_by_objid(self):
        self.get(u'/v1.0/nes/events', query={u'objid': u'internal'})

    def test_get_events_by_date(self):
        self.get(u'/v1.0/nes/events', query={u'date': u'internal'})

    def test_get_events_by_source(self):
        self.get(u'/v1.0/nes/events', query={u'source': u'internal'})

    def test_get_events_by_data(self):
        self.get(u'/v1.0/nes/events', query={u'data': u'internal'})

    def test_get_event_by_id(self):
        self.get(u'/v1.0/nes/events/{oid}', params={u'oid': 4})

    def test_get_event_by_eventid(self):
        self.get(u'/v1.0/nes/events/{oid}', params={u'oid': 4})


tests = []
for test_plans in [
    tests_event
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
