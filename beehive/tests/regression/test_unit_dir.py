# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
from beecell.remote import ConflictException
from beehive.common.test import runtest, assert_exception
from beehive.tests.module.auth.view import AuthTestCase
from beehive.tests.module.event.view import EventTestCase
from beehive.tests.module.basic.view import BaseTestCase
from beehive.tests.module.catalog.view import CatalogTestCase
from beehive.tests.module.scheduler.view import SchedulerAPITestCase

tests_dir = [
    u'test_add_catalog',
    u'test_add_catalog_twice',
    u'test_get_catalogs',
    u'test_get_catalogs_by_zone',
    u'test_get_catalog',
    u'test_get_catalog_perms',
    u'test_get_catalog_by_name',
    u'test_update_catalog',

    u'test_add_endpoint',
    u'test_add_endpoint_twice',
    u'test_get_endpoints',
    u'test_filter_endpoints',
    u'test_get_endpoint',
    u'test_update_endpoint',
    u'test_delete_endpoint',

    u'test_delete_catalog',
]


class TestCase(CatalogTestCase):
    validation_active = False

    def setUp(self):
        CatalogTestCase.setUp(self)
        self.module = u'auth'
        self.module_prefix = u'nas'
        self.endpoint_service = u'auth'

    #
    # catalogs
    #
    def test_add_catalog(self):
        data = {
            u'catalog': {
                u'name': u'beehive',
                u'desc': u'beehive catalog',
                u'zone': u'internal'
            }
        }
        self.post(u'/v1.0/ncs//catalogs', data=data)

    @assert_exception(ConflictException)
    def test_add_catalog_twice(self):
        data = {
            u'catalog': {
                u'name': u'beehive',
                u'desc': u'beehive catalog',
                u'zone': u'internal'
            }
        }
        self.post(u'/v1.0/ncs//catalogs', data=data)

    def test_get_catalogs(self):
        res = self.get(u'/v1.0/ncs//catalogs')
        global oid
        oid = res[u'catalogs'][-1][u'id']

    def test_get_catalogs_by_zone(self):
        self.get(u'/v1.0/ncs//catalogs', query={u'zone': u'internal'})

    def test_get_catalog(self):
        global oid
        self.get(u'/v1.0/ncs//catalogs/{oid}', params={u'oid': oid})

    def test_get_catalog_perms(self):
        global oid
        self.get(u'/v1.0/ncs//catalogs/{oid}/perms', params={u'oid': oid})

    def test_get_catalog_by_name(self):
        self.get(u'/v1.0/ncs//catalogs/{oid}', params={u'oid': u'beehive-internal-podto1'})

    def test_update_catalog(self):
        data = {
            u'catalog': {
                u'name': u'beehive',
                u'desc': u'beehive catalog1',
                u'zone': u'internal1'
            }
        }
        self.put(u'/v1.0/ncs//catalogs/{oid}', params={u'oid': u'beehive'}, data=data)

    def test_delete_catalog(self):
        self.delete(u'/v1.0/ncs//catalogs/{oid}', params={u'oid': u'beehive'})

    #
    # endpoints
    #
    def test_add_endpoint(self):
        data = {
            u'endpoint': {
                u'catalog': u'beehive',
                u'name': u'endpoint-prova',
                u'desc': u'Authorization endpoint 01',
                u'service': u'auth',
                u'uri': u'http://localhost:6060/v1.0/auth/',
                u'active': True
            }
        }
        self.post(u'/v1.0/ncs//endpoints', data=data)

    @assert_exception(ConflictException)
    def test_add_endpoint_twice(self):
        data = {
            u'endpoint': {
                u'catalog': u'beehive',
                u'name': u'endpoint-prova',
                u'desc': u'Authorization endpoint 01',
                u'service': u'auth',
                u'uri': u'http://localhost:6060/v1.0/auth/',
                u'active': True
            }
        }
        self.post(u'/v1.0/ncs//endpoints', data=data)

    def test_get_endpoints(self):
        self.get(u'/v1.0/ncs//endpoints')

    def test_filter_endpoints(self):
        self.get(u'/v1.0/ncs//endpoints', query={u'service': u'auth', u'catalog': u'beehive'})

    def test_get_endpoint(self):
        self.get(u'/v1.0/ncs//endpoints/{oid}', params={u'oid': u'endpoint-prova'})

    def test_update_endpoint(self):
        data = {
            u'endpoint': {
                u'name': u'endpoint-prova',
                u'desc': u'Authorization endpoint 02',
                u'service': u'auth',
                u'uri': u'http://localhost:6060/v1.0/auth/',
                u'active': True
            }
        }
        self.put(u'/v1.0/ncs//endpoints/{oid}', params={u'oid': u'endpoint-prova'}, data=data)

    def test_delete_endpoint(self):
        self.delete(u'/v1.0/ncs//endpoints/{oid}', params={u'oid': u'endpoint-prova'})


tests = []
for test_plans in [
    tests_dir
]:
    tests.extend(test_plans)


def run(args):
    runtest(TestCase, tests, args)


if __name__ == u'__main__':
    run()
