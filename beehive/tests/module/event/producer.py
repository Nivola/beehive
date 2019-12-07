# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.event import EventProducerRedis
from beehive.common.test import BeehiveTestCase, runtest

tests = [
    'test_send_event',
    'test_get_event'
]


class EventProducerTestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = 'event'
        self.module_prefix = 'nes'
        self.endpoint_service = 'event'

        redis_uri = 'redis://localhost:6379/0'
        redis_channel = 'beehive.event'
        self.client = EventProducerRedis(redis_uri, redis_channel)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
        
    def test_send_event(self):
        event_type = 'prova'
        objtype = 'test'
        source = {
            'user': 'admin',
            'ip': 'localhost',
            'identity': 'uid'
        }
        dest = {
            'ip': 'localhost',
            'port': 6060,
            'objid': 123,
            'objtype': objtype,
            'objdef': 'test1'}
        data = {'key': 'value'}
        self.client.send_sync(event_type, data, source, dest)

    def test_get_event(self):
        self.get('/v1.0/nes/events', query={'type': 'prova'})


def run(args):
    runtest(EventProducerTestCase, tests, args)


if __name__ == '__main__':
    run({})
