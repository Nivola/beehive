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
        self.module = 'auth'
        self.module_prefix = 'nas'
        self.endpoint_service = 'auth'
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping(self):
        self.get('/v1.0/server/ping')

    def test_info(self):
        self.get('/v1.0/server')


def run(args):
    runtest(BaseTestCase, tests, args)


if __name__ == '__main__':
    run({})
