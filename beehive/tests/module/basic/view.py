# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beehive.common.test import runtest, BeehiveTestCase

tests = [
    "test_ping"
    #'test_info',
]


class BaseTestCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance."""

    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = "auth"
        self.module_prefix = "nas"
        self.endpoint_service = "auth"

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_ping(self):
        self.get("/v1.0/server/ping")

    def test_info(self):
        self.get("/v1.0/server")


def run(args):
    runtest(BaseTestCase, tests, args)


if __name__ == "__main__":
    run({})
