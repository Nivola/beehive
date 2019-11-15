"""
Created on Dec 15, 2017

@author: darkbk

ansible-playbook -i inventories/test-glb -l locust -t configure beehive-locust.yml
ansible-playbook -i inventories/test-glb -l locust -t sync beehive-locust.yml

cd /beehive

mono:
locust -f glb_locust.py --host=http://aa.glb.csi.it:80

distributed:
locust -f tests/glb/glb_locust.py --master --host=http://aa.glb.csi.it:80
locust -f tests/glb/glb_locust.py  --slave --host=http://aa.glb.csi.it:80
locust -f tests/glb/glb_locust.py --slave --master-host=158.102.160.234 --host=http://aa.glb.csi.it:80

opens http://127.0.0.1:8089
"""
import random
import ujson as json
import logging
import os
import gevent.monkey
gevent.monkey.patch_all()
from beecell.logger import LoggerHelper
from locust import HttpLocust, TaskSet, task
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Random import atfork
import binascii
from multiprocessing import current_process
from base64 import b64encode

logger = logging.getLogger(__name__)


class BaseTaskSet(TaskSet):
    def __setup_logging(self):
        loggers = [
            logging.getLogger('beehive'),
            logging.getLogger('beedrones'),
            logging.getLogger('beecell'),
            logging.getLogger('beehive_resource'),
            logging.getLogger('beehive_service'),
        ]
        LoggerHelper.simple_handler(loggers, logging.DEBUG)

    def __read_config_file(self, file_config):
        f = open(file_config, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    def __load_config(self):
        # load config
        try:
            # config = self.load_config('%s/params.json' % path)
            home = os.path.expanduser('~')
            config = self.__read_config_file('%s/beehive.json' % home)
            logger.info('get beehive test configuration')
        except Exception as ex:
            err = 'Error loading config file beehive.json. Search in user home. %s' % ex
            logger.error(err)
            raise Exception(err)

        env = config.get('env')
        # current_schema = config.get('schema')
        cfg = config.get(env)
        self.test_config = cfg

        # endpoints
        self.endpoints = cfg.get('endpoints')

        # get users
        self.users = cfg.get('users')

    def __create_client(self):
        try:
            endpoints = [self.endpoints.get(self.test_config['default-endpoint'])]
            user = self.users.get('admin')
            self.user_name = user.get('user')
            self.pwd = user.get('pwd')
            self.ip = user.get('ip')
            self.catalog_id = user.get('catalog')
            self.authtype = user.get('auth')
            # self.beeclient = BeehiveApiClient(endpoints, authtype, self.user_name, self.pwd, self.catalog_id)
        except:
            logger.error('', exc_info=1)
        # self.beeclient.load_catalog()
        # if uid is not None:
        #    self.beeclient.uid = uid
        #    self.beeclient.seckey = seckey

    def __create_token(self):
        if self.authtype == 'keyauth':
            data = {'user': self.user_name, 'password': self.pwd, 'login-ip': self.ip}
            response = self.client.post('/v1.0/keyauth/token', json=data)
            res = response.json()
            logger.info('Login user %s with token: %s' % (self.user_name, res['access_token']))
            self.uid = res['access_token']
            self.seckey = res['seckey']

    def get_headers(self, path):
        headers = {'Cache-Control': 'no-store', 'Pragma': 'no-cache', 'Accept': 'application/json'}
        if self.authtype == 'keyauth':
            if current_process().ident != self.pid:
                atfork()

            # import key
            seckey = binascii.a2b_base64(self.seckey)
            key = RSA.importKey(seckey)

            # create data hash
            hash_data = SHA256.new(path)

            # sign data
            signer = PKCS1_v1_5.new(key)
            signature = signer.sign(hash_data)

            # encode signature in base64
            signature64 = binascii.b2a_hex(signature)

            headers.update({'uid': self.uid, 'sign': signature64})
        elif self.api_authtype == 'oauth2':
            headers.update({'Authorization': 'Bearer %s' % self.uid})
        elif self.api_authtype == 'simplehttp':
            auth = b64encode('%s:%s' % (self.user_name, self.pwd))
            headers.update({'Authorization': 'Basic %s' % auth})
        return headers

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        self.pid = current_process().ident

        # self.__setup_logging()
        self.__load_config()
        self.__create_client()
        self.__create_token()

        self.resources = []

    def check_response(self, response):
        if response.status_code in [400, 401, 403, 404, 405, 406, 408, 409, 415]:
            response.failure(response.json().get('message'))

    def log_task(self, response, path, method):
        status = 'KO'
        if response.status_code in [200, 201, 202, 204]:
            status = 'OK'
        logger.info('User: %s - Status: %s - Remote: %s - Uri: %s - Method: %s' %
                    (id(self), status, response.headers.get('remote-server', None), path, method))
        self.check_response(response)

    # @task(1)
    def ping(self):
        response = self.client.get('/v1.0/server/ping')

    @task(1)
    def validate_token(self):
        path = '/v1.0/auth/tokens/%s' % self.uid
        method = 'get'
        response = self.client.get(path, headers=self.get_headers(path), name='/v1.0/auth/tokens/<id>')
        self.log_task(response, path, method)

    @task(1)
    def get_catalog(self):
        path = '/v1.0/directory/catalogs/%s' % self.catalog_id
        method = 'get'
        response = self.client.get(path, headers=self.get_headers(path))
        self.log_task(response, path, method)

    @task(3)
    def get_resources(self):
        path = '/v1.0/resources'
        method = 'get'
        response = self.client.get(path, headers=self.get_headers(path))
        self.log_task(response, path, method)

    @task(1)
    def add_resource1(self):
        path = '/v1.0/resources'
        method = 'post'
        name = 'resource-test-%s' % random.randint(1, 100000)
        data = {
            'resource': {
                'container': 'test-container',
                'resclass': 'beehive_resource.plugins.dummy.controller.DummySyncResource',
                'name': name,
                'desc': name,
                'ext_id': '123'
            }
        }
        response = self.client.post(path, json=data, headers=self.get_headers(path))
        self.log_task(response, path, method)
        self.resources.append(response.json()['uuid'])

    @task(3)
    def delete_resource1(self):
        # if len(self.resources) > 0:
        try:
            uuid = self.resources.pop()
            path = '/v1.0/resources/%s' % uuid
            method = 'delete'
            response = self.client.delete(path, headers=self.get_headers(path), name='/v1.0/resources/[uuid]')
            self.log_task(response, path, method)
        except IndexError:
            pass


class ApiTaskSet(BaseTaskSet):
    pass


class MyTaskSet(TaskSet):
    @task
    class SubTaskSet(TaskSet):
        @task
        def my_task(self):
            pass


class ApiUser(HttpLocust):
    task_set = ApiTaskSet
    min_wait = 5000
    max_wait = 10000
