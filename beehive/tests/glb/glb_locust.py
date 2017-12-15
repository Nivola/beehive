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
            logging.getLogger(u'beehive'),
            logging.getLogger(u'beedrones'),
            logging.getLogger(u'beecell'),
            logging.getLogger(u'beehive_resource'),
            logging.getLogger(u'beehive_service'),
        ]
        LoggerHelper.simple_handler(loggers, logging.DEBUG)

    def __read_config_file(self, file_config):
        f = open(file_config, u'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    def __load_config(self):
        # load config
        try:
            # config = self.load_config(u'%s/params.json' % path)
            home = os.path.expanduser(u'~')
            config = self.__read_config_file(u'%s/beehive.json' % home)
            logger.info(u'get beehive test configuration')
        except Exception as ex:
            err = u'Error loading config file beehive.json. Search in user home. %s' % ex
            logger.error(err)
            raise Exception(err)

        env = config.get(u'env')
        # current_schema = config.get(u'schema')
        cfg = config.get(env)
        self.test_config = cfg

        # endpoints
        self.endpoints = cfg.get(u'endpoints')

        # get users
        self.users = cfg.get(u'users')

    def __create_client(self):
        try:
            endpoints = [self.endpoints.get(self.test_config[u'default-endpoint'])]
            user = self.users.get(u'admin')
            self.user_name = user.get(u'user')
            self.pwd = user.get(u'pwd')
            self.ip = user.get(u'ip')
            self.catalog_id = user.get(u'catalog')
            self.authtype = user.get(u'auth')
            # self.beeclient = BeehiveApiClient(endpoints, authtype, self.user_name, self.pwd, self.catalog_id)
        except:
            logger.error(u'', exc_info=1)
        # self.beeclient.load_catalog()
        # if uid is not None:
        #    self.beeclient.uid = uid
        #    self.beeclient.seckey = seckey

    def __create_token(self):
        if self.authtype == u'keyauth':
            data = {u'user': self.user_name, u'password': self.pwd, u'login-ip': self.ip}
            response = self.client.post(u'/v1.0/keyauth/token', json=data)
            res = response.json()
            logger.info(u'Login user %s with token: %s' % (self.user_name, res[u'access_token']))
            self.uid = res[u'access_token']
            self.seckey = res[u'seckey']

    def get_headers(self, path):
        headers = {u'Cache-Control': u'no-store', u'Pragma': u'no-cache', u'Accept': u'application/json'}
        if self.authtype == u'keyauth':
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

            headers.update({u'uid': self.uid, u'sign': signature64})
        elif self.api_authtype == u'oauth2':
            headers.update({u'Authorization': u'Bearer %s' % self.uid})
        elif self.api_authtype == u'simplehttp':
            auth = b64encode(u'%s:%s' % (self.user_name, self.pwd))
            headers.update({u'Authorization': u'Basic %s' % auth})
        return headers

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        self.pid = current_process().ident

        # self.__setup_logging()
        self.__load_config()
        self.__create_client()
        self.__create_token()

    def log_task(self, response, path, method):
        status = u'KO'
        if response.status_code in [200, 201, 202, 204]:
            status = u'OK'
        logger.info(u'User: %s - Status: %s - Remote: %s - Uri: %s - Method: %s' %
                    (id(self), status, response.headers.get(u'remote-server', None), path, method))

    # @task(1)
    def ping(self):
        response = self.client.get(u'/v1.0/server/ping')

    @task(1)
    def validate_token(self):
        path = u'/v1.0/auth/tokens/%s' % self.uid
        method = u'get'
        response = self.client.get(path, headers=self.get_headers(path), name=u'/v1.0/auth/tokens/<id>')
        self.log_task(response, path, method)

    @task(1)
    def get_catalog(self):
        path = u'/v1.0/directory/catalogs/%s' % self.catalog_id
        method = u'get'
        response = self.client.get(path, headers=self.get_headers(path))
        self.log_task(response, path, method)

    @task(1)
    def get_resources(self):
        path = u'/v1.0/resources'
        method = u'get'
        response = self.client.get(path, headers=self.get_headers(path))
        self.log_task(response, path, method)


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
