# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import sys
from beehive.common.test import runtest, BeehiveTestCase

tests = [  
    'test_ping',
    'test_info',

    ## 'test_processes',
    ## 'test_workers',
    ## 'test_configs'
    ## 'test_uwsgi_configs',
    ## 'test_reload',
]


class BaseTestCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'
        self.endpoint_service = u'auth'
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping(self):
        res = self.get(u'/v1.0/nrs/entities/{oid}')
        data = ''
        uri = '/v1.0/server/ping'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res))

    def test_info(self):
        data = ''
        uri = '/v1.0/server'
        res = self.call(self.module, uri, 'GET', data=data)
        self.logger.debug(self.pp.pformat(res))


def run(args):
    runtest(BaseTestCase, tests, args)


if __name__ == u'__main__':
    run({})
