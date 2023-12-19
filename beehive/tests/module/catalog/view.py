# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, ConflictException

oid = None

tests_dir = [
    "test_add_catalog",
    "test_add_catalog_twice",
    "test_get_catalogs",
    "test_get_catalogs_by_zone",
    "test_get_catalog",
    "test_get_catalog_perms",
    "test_get_catalog_by_name",
    "test_update_catalog",
    "test_add_endpoint",
    "test_add_endpoint_twice",
    "test_get_endpoints",
    "test_filter_endpoints",
    "test_get_endpoint",
    "test_update_endpoint",
    "test_delete_endpoint",
    "test_delete_catalog",
]


class TestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = "auth"
        self.module_prefix = "nas"
        self.endpoint_service = "auth"

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # catalogs
    #
    def test_add_catalog(self):
        data = {
            "catalog": {
                "name": "beehive",
                "desc": "beehive catalog",
                "zone": "internal",
            }
        }
        self.post("/v1.0/ncs/catalogs", data=data)

    @assert_exception(ConflictException)
    def test_add_catalog_twice(self):
        data = {
            "catalog": {
                "name": "beehive",
                "desc": "beehive catalog",
                "zone": "internal",
            }
        }
        self.post("/v1.0/ncs/catalogs", data=data)

    def test_get_catalogs(self):
        res = self.get("/v1.0/ncs/catalogs")
        global oid
        oid = res["catalogs"][-1]["id"]

    def test_get_catalogs_by_zone(self):
        self.get("/v1.0/ncs/catalogs", query={"zone": "internal"})

    def test_get_catalog(self):
        global oid
        self.get("/v1.0/ncs/catalogs/{oid}", params={"oid": oid})

    def test_get_catalog_perms(self):
        global oid
        self.get("/v1.0/ncs/catalogs/{oid}/perms", params={"oid": oid})

    def test_get_catalog_by_name(self):
        self.get("/v1.0/ncs/catalogs/{oid}", params={"oid": "beehive-internal"})

    def test_update_catalog(self):
        data = {
            "catalog": {
                "name": "beehive",
                "desc": "beehive catalog1",
                "zone": "internal1",
            }
        }
        self.put("/v1.0/ncs/catalogs/{oid}", params={"oid": "beehive"}, data=data)

    def test_delete_catalog(self):
        self.delete("/v1.0/ncs/catalogs/{oid}", params={"oid": "beehive"})

    #
    # endpoints
    #
    def test_add_endpoint(self):
        data = {
            "endpoint": {
                "catalog": "beehive",
                "name": "endpoint-prova",
                "desc": "Authorization endpoint 01",
                "service": "auth",
                "uri": "http://localhost:6060/v1.0/auth/",
                "active": True,
            }
        }
        self.post("/v1.0/ncs/endpoints", data=data)

    @assert_exception(ConflictException)
    def test_add_endpoint_twice(self):
        data = {
            "endpoint": {
                "catalog": "beehive",
                "name": "endpoint-prova",
                "desc": "Authorization endpoint 01",
                "service": "auth",
                "uri": "http://localhost:6060/v1.0/auth/",
                "active": True,
            }
        }
        self.post("/v1.0/ncs/endpoints", data=data)

    def test_get_endpoints(self):
        self.get("/v1.0/ncs/endpoints")

    def test_filter_endpoints(self):
        self.get("/v1.0/ncs/endpoints", query={"service": "auth", "catalog": "beehive"})

    def test_get_endpoint(self):
        self.get("/v1.0/ncs/endpoints/{oid}", params={"oid": "endpoint-prova"})

    def test_update_endpoint(self):
        data = {
            "endpoint": {
                "name": "endpoint-prova",
                "desc": "Authorization endpoint 02",
                "service": "auth",
                "uri": "http://localhost:6060/v1.0/auth/",
                "active": True,
            }
        }
        self.put("/v1.0/ncs/endpoints/{oid}", params={"oid": "endpoint-prova"}, data=data)

    def test_delete_endpoint(self):
        self.delete("/v1.0/ncs/endpoints/{oid}", params={"oid": "endpoint-prova"})


tests = []
for test_plans in [tests_dir]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == "__main__":
    run({})
