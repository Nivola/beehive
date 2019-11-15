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
    'test_ping',
    'test_create_keyauth_token',
    'test_validate_token',
    #'test_get_catalog',


    #'test_create_catalog',
    #'test_delete_catalog',

    #'test_get_endpoints',
    #'test_get_endpoint',
    #'test_create_endpoint',
    #'test_delete_endpoint',

    'test_list_resources',

    # 'test_add_resourcecontainer',
    # 'test_add_resource1',
    # 'test_add_resource2',
    # 'test_add_resource3',
    # 'test_get_resources',
    # 'test_get_resources_by_name',
    # 'test_get_resources_by_container',
    # 'test_delete_resource2',
    # 'test_delete_resource1',
    # 'test_delete_resource3',
    # 'test_delete_resourcecontainer',

    #'test_logout',
]


class BeehiveGlbTestCase(BeehiveTestCase):
    """
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        global uid, seckey
        endpoints = [self.endpoints.get(self.test_config['default-endpoint'])]
        user = self.users.get('admin')
        self.user_name = user.get('user')
        self.pwd = user.get('pwd')
        self.ip = user.get('ip')
        self.catalog_id = user.get('catalog')
        authtype = user.get('auth')
        self.client = BeehiveApiClient(endpoints, authtype, self.user_name, self.pwd, None, self.catalog_id)
        #self.client.load_catalog()
        if uid is not None:
            self.client.uid = uid
            self.client.seckey = seckey
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def get_job_state(self, jobid):
        try:
            res = self.call('resource', '/v1.0/worker/tasks/{oid}', 'get', params={'oid': jobid}, runlog=False,
                            **self.users['admin'])
            job = res.get('task_instance')
            state = job.get('status')
            logger.debug('Get job %s state: %s' % (jobid, state))
            if state == 'FAILURE':
                for err in job.get('traceback', []):
                    self.runlogger.error(err.rstrip())
            return state
        except (NotFoundException, Exception):
            return 'EXPUNGED'

    def wait_resource(self, uuid, delta=1, accepted_state='ACTIVE'):
        """Wait resource
        """
        self.runlogger.info('wait for:         %s' % uuid)
        state = self.get_resource_state(uuid)
        while state not in ['ACTIVE', 'ERROR', 'EXPUNGED']:
            self.runlogger.info('.')
            sleep(delta)
            state = self.get_resource_state(uuid)
        self.assertEqual(state, accepted_state)

    def wait_job(self, jobid, delta=1, accepted_state='SUCCESS'):
        """Wait resource
        """
        self.runlogger.info('wait for:         %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in ['SUCCESS', 'FAILURE']:
            self.runlogger.info('.')
            sleep(delta)
            state = self.get_job_state(jobid)
        self.assertEqual(state, accepted_state)


    def test_ping(self):
        res = self.client.ping(subsystem='auth')
        self.logger.info(self.pp.pformat(res))

    def test_create_keyauth_token(self):
        global uid, seckey      
        res = self.client.create_token(api_user=self.user_name, api_user_pwd=self.pwd, login_ip=self.ip)
        uid = res['access_token']
        seckey = res['seckey']
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
        res = self.client.invoke('resource', '/v1.0/resources', 'GET', '')
        self.logger.info(self.pp.pformat(res))

    def test_add_resourcecontainer(self):
        data = {
            'resourcecontainer': {
                'type': 'Dummy',
                'name': 'test-container',
                'desc': 'test container',
                'conn': {}
            }
        }
        self.call('resource', '/v1.0/resourcecontainers', 'post', data=data, **self.users['admin'])

    def test_get_resourcecontainers(self):
        self.call('resource', '/v1.0/resourcecontainers', 'get',
                  **self.users['admin'])

    def test_delete_resourcecontainer(self):
        self.call('resource', '/v1.0/resourcecontainers/{oid}', 'delete',
                  params={'oid': 'test-container'},
                  **self.users['admin'])

    def test_add_resource1(self):
        data = {
            'resource': {
                'container': 'test-container',
                'resclass': 'beehive_resource.plugins.dummy.controller.DummySyncResource',
                'name': 'resource-prova1',
                'desc': 'resource prova1',
                'ext_id': '123'
            }
        }
        self.call('resource', '/v1.0/resources', 'post', data=data,
                  **self.users['admin'])

    def test_add_resource2(self):
        data = {
            'resource': {
                'container': 'test-container',
                'resclass': 'beehive_resource.plugins.dummy.controller.DummySyncChildResource',
                'name': 'resource-prova2',
                'desc': 'resource prova2',
                'ext_id': '1234',
                'parent': 'resource-prova1'
            }
        }
        self.call('resource', '/v1.0/resources', 'post', data=data,
                  **self.users['admin'])

    def test_add_resource3(self):
        data = {
            'resource': {
                'container': 'test-container',
                'resclass': 'beehive_resource.plugins.dummy.controller.DummyAsyncResource',
                'name': 'resource-prova3',
                'desc': 'resource prova3'
            }
        }
        res = self.call('resource', '/v1.0/resources', 'post', data=data,
                        **self.users['admin'])
        self.wait_resource(res['uuid'], delta=1)

    def test_get_resources(self):
        global oid
        res = self.call('resource', '/v1.0/resources', 'get',
                        **self.users['admin'])
        oid = res['resources'][0]['uuid']

    def test_get_resources_by_name(self):
        self.call('resource', '/v1.0/resources', 'get',
                  query={'name': '%prova%'},
                  **self.users['admin'])

    def test_get_resources_by_container(self):
        self.call('resource', '/v1.0/resources', 'get',
                  query={'container': 'test-container'},
                  **self.users['admin'])

    def test_delete_resource1(self):
        self.call('resource', '/v1.0/resources/{oid}', 'delete',
                  params={'oid': 'resource-prova1'},
                  **self.users['admin'])

    def test_delete_resource2(self):
        self.call('resource', '/v1.0/resources/{oid}', 'delete',
                  params={'oid': 'resource-prova2'},
                  **self.users['admin'])

    def test_delete_resource3(self):
        res = self.call('resource', '/v1.0/resources/{oid}', 'delete',
                        params={'oid': 'resource-prova3'},
                        **self.users['admin'])
        self.wait_job(res['jobid'], delta=1)


if __name__ == '__main__':
    runtest(BeehiveGlbTestCase, tests)