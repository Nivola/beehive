"""
Created on Jan 12, 2017

@author: darkbk
"""
import logging
import time
import unittest
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, UnauthorizedException, \
    ConflictException, NotFoundException
from beehive.common.apiclient import BeehiveApiClient

logger = logging.getLogger(__name__)

uid = None
seckey = None

tests = [
    u'test_ping',
    u'test_create_keyauth_token',
    u'test_validate_token',
    #u'test_get_catalog',


    #u'test_create_catalog',
    #u'test_delete_catalog',

    #u'test_get_endpoints',
    #u'test_get_endpoint',
    #u'test_create_endpoint',
    #u'test_delete_endpoint',

    u'test_list_resources',

    # u'test_add_resourcecontainer',
    # u'test_add_resource1',
    # u'test_add_resource2',
    # u'test_add_resource3',
    # u'test_get_resources',
    # u'test_get_resources_by_name',
    # u'test_get_resources_by_container',
    # u'test_delete_resource2',
    # u'test_delete_resource1',
    # u'test_delete_resource3',
    # u'test_delete_resourcecontainer',

    #u'test_logout',
]


class BeehiveGlbTestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        global uid, seckey
        endpoints = [self.endpoints.get(self.test_config[u'default-endpoint'])]
        user = self.users.get(u'admin')
        self.user_name = user.get(u'user')
        self.pwd = user.get(u'pwd')
        self.ip = user.get(u'ip')
        self.catalog_id = user.get(u'catalog')
        authtype = user.get(u'auth')
        self.client = BeehiveApiClient(endpoints, authtype, self.user_name, self.pwd, self.catalog_id)
        #self.client.load_catalog()
        if uid is not None:
            self.client.uid = uid
            self.client.seckey = seckey
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def get_job_state(self, jobid):
        try:
            res = self.call(u'resource', u'/v1.0/worker/tasks/{oid}', u'get', params={u'oid': jobid}, runlog=False,
                            **self.users[u'admin'])
            job = res.get(u'task_instance')
            state = job.get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                for err in job.get(u'traceback', []):
                    self.runlogger.error(err.rstrip())
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'

    def wait_resource(self, uuid, delta=1, accepted_state=u'ACTIVE'):
        """Wait resource
        """
        self.runlogger.info(u'wait for:         %s' % uuid)
        state = self.get_resource_state(uuid)
        while state not in [u'ACTIVE', u'ERROR', u'EXPUNGED']:
            self.runlogger.info(u'.')
            sleep(delta)
            state = self.get_resource_state(uuid)
        self.assertEqual(state, accepted_state)

    def wait_job(self, jobid, delta=1, accepted_state=u'SUCCESS'):
        """Wait resource
        """
        self.runlogger.info(u'wait for:         %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in [u'SUCCESS', u'FAILURE']:
            self.runlogger.info(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)
        self.assertEqual(state, accepted_state)


    def test_ping(self):
        res = self.client.ping(subsystem=u'auth')
        self.logger.info(self.pp.pformat(res))

    def test_create_keyauth_token(self):
        global uid, seckey      
        res = self.client.create_token(api_user=self.user_name, api_user_pwd=self.pwd, login_ip=self.ip)
        uid = res[u'access_token']
        seckey = res[u'seckey']
        self.logger.info(self.client.endpoints)

    def test_validate_token(self):
        global uid, seckey
        res = self.client.exist(uid)
        self.logger.info(res)
        
    def test_get_catalog(self):
        res = self.client.get_catalog(self.catalog_id)
        self.logger.info(self.pp.pformat(res))        
        
    #
    # resources
    #
    def test_list_resources(self):
        global uid, seckey
        res = self.client.invoke(u'resource', u'/v1.0/resources', u'GET', u'')
        self.logger.info(self.pp.pformat(res))

    def test_add_resourcecontainer(self):
        data = {
            u'resourcecontainer': {
                u'type': u'Dummy',
                u'name': u'test-container',
                u'desc': u'test container',
                u'conn': {}
            }
        }
        self.call(u'resource', u'/v1.0/resourcecontainers', u'post', data=data, **self.users[u'admin'])

    def test_get_resourcecontainers(self):
        self.call(u'resource', u'/v1.0/resourcecontainers', u'get',
                  **self.users[u'admin'])

    def test_delete_resourcecontainer(self):
        self.call(u'resource', u'/v1.0/resourcecontainers/{oid}', u'delete',
                  params={u'oid': u'test-container'},
                  **self.users[u'admin'])

    def test_add_resource1(self):
        data = {
            u'resource': {
                u'container': u'test-container',
                u'resclass': u'beehive_resource.plugins.dummy.controller.DummySyncResource',
                u'name': u'resource-prova1',
                u'desc': u'resource prova1',
                u'ext_id': u'123'
            }
        }
        self.call(u'resource', u'/v1.0/resources', u'post', data=data,
                  **self.users[u'admin'])

    def test_add_resource2(self):
        data = {
            u'resource': {
                u'container': u'test-container',
                u'resclass': u'beehive_resource.plugins.dummy.controller.DummySyncChildResource',
                u'name': u'resource-prova2',
                u'desc': u'resource prova2',
                u'ext_id': u'1234',
                u'parent': u'resource-prova1'
            }
        }
        self.call(u'resource', u'/v1.0/resources', u'post', data=data,
                  **self.users[u'admin'])

    def test_add_resource3(self):
        data = {
            u'resource': {
                u'container': u'test-container',
                u'resclass': u'beehive_resource.plugins.dummy.controller.DummyAsyncResource',
                u'name': u'resource-prova3',
                u'desc': u'resource prova3'
            }
        }
        res = self.call(u'resource', u'/v1.0/resources', u'post', data=data,
                        **self.users[u'admin'])
        self.wait_resource(res[u'uuid'], delta=1)

    def test_get_resources(self):
        global oid
        res = self.call(u'resource', u'/v1.0/resources', u'get',
                        **self.users[u'admin'])
        oid = res[u'resources'][0][u'uuid']

    def test_get_resources_by_name(self):
        self.call(u'resource', u'/v1.0/resources', u'get',
                  query={u'name': u'%prova%'},
                  **self.users[u'admin'])

    def test_get_resources_by_container(self):
        self.call(u'resource', u'/v1.0/resources', u'get',
                  query={u'container': u'test-container'},
                  **self.users[u'admin'])

    def test_delete_resource1(self):
        self.call(u'resource', u'/v1.0/resources/{oid}', u'delete',
                  params={u'oid': u'resource-prova1'},
                  **self.users[u'admin'])

    def test_delete_resource2(self):
        self.call(u'resource', u'/v1.0/resources/{oid}', u'delete',
                  params={u'oid': u'resource-prova2'},
                  **self.users[u'admin'])

    def test_delete_resource3(self):
        res = self.call(u'resource', u'/v1.0/resources/{oid}', u'delete',
                        params={u'oid': u'resource-prova3'},
                        **self.users[u'admin'])
        self.wait_job(res[u'jobid'], delta=1)


if __name__ == u'__main__':
    runtest(BeehiveGlbTestCase, tests)