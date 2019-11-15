#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import os
import sys
from six import b
import gevent.monkey
from beehive.common.apiclient import BeehiveApiClient
from beehive.common.log import ColorFormatter

# from _random import Random
# os.environ['GEVENT_RESOLVER'] = 'ares'
# os.environ['GEVENTARES_SERVERS'] = 'ares'
# import beecell.server.gevent_ssl
from beecell.simple import truncate, str2bool, dict_get

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

gevent.monkey.patch_all()

import logging
import unittest
import pprint
import time
import json
import yaml
import redis
import re
from beecell.logger import LoggerHelper
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from beecell.remote import RemoteClient, ServerErrorException,\
    UnsupporteMediaTypeException, ConflictException, TimeoutException,\
    NotAcceptableException, MethodNotAllowedException, NotFoundException,\
    ForbiddenException, BadRequestException, UnauthorizedException
import requests
from beecell.swagger import ApiValidator
from flex.core import load
from requests.auth import HTTPBasicAuth
from celery.utils.log import ColorFormatter as CeleryColorFormatter
from celery.utils.term import colored
from gevent import sleep
from dict_recursive_update import recursive_update
from multiprocessing import Process, Queue
from beecell.test.runner import TestRunner

seckey = None
token = None
result = {}
TIMEOUT = 'TIMEOUT'

logger = logging.getLogger(__name__)


def assert_exception(exception):
    def wrapper(fn):
        def decorated(self, *args, **kwargs):
            self.assertRaises(exception, fn, self, *args, **kwargs)
        return decorated
    return wrapper


class BeehiveTestCase(unittest.TestCase):
    logger = logging.getLogger('beehive.test.log')
    runlogger = logging.getLogger('beehive.test.run')
    pp = pprint.PrettyPrinter(width=200)
    logging.addLevelName(60, 'TESTPLAN')
    logging.addLevelName(70, 'TEST')

    # module = 'resource'
    # module_prefix = 'nrs'

    main_config_file = None
    main_fernet_file = None
    spec_config_file = None
    validation_active = False
    run_test_user = 'test1'

    @classmethod
    def setUpClass(cls):
        logger.log(60, '#################### Testplan %s - START ####################' % cls.__name__)
        logging.getLogger('beehive.test.run')\
            .log(60, '#################### Testplan %s - START ####################' % cls.__name__)
        self = cls

        # ssl
        path = os.path.dirname(__file__).replace('beehive/common', 'beehive/tests')
        pos = path.find('tests')
        path = path[:pos+6]
        keyfile = None
        certfile = None

        # load configs
        try:
            home = os.path.expanduser('~')
            if self.main_config_file is None:
                config_file = '%s/beehive.yml' % home
                self.main_config_file = config_file
            else:
                config_file = self.main_config_file
            config = self.load_file(config_file)
            logger.info('Get beehive test configuration: %s' % config_file)
        except Exception as ex:
            raise Exception('Error loading config file. Search in user home. %s' % ex)

        # load configs fernet key
        try:
            home = os.path.expanduser('~')
            if self.main_config_file is None:
                config_file = '%s/beehive.fernet' % home
                self.main_fernet_file = config_file
            else:
                config_file = self.main_config_file.replace('yml', 'fernet')
            fernet = self.load_file(config_file)
            logger.info('Get beehive test fernet key: %s' % config_file)
        except Exception as ex:
            raise Exception('Error loading fernet key file. Search in user home. %s' % ex)

        # load specific configs for a set of test
        try:
            if self.spec_config_file is not None:
                config2 = self.load_file(self.spec_config_file)
                recursive_update(config, config2)
                logger.info('Get beehive test specific configuration: %s' % self.spec_config_file)
        except Exception as ex:
            raise Exception('Error loading config file. Search in user home. %s' % ex)

        logger.info('Validation active: %s' % cls.validation_active)

        # print('Configurations:')
        # print('Main config file: %s' % cls.main_config_file)
        # print('Extra config file: %s' % cls.spec_config_file)
        # print('Validation active: %s' % cls.validation_active)
        # print('Test user: %s' % cls.run_test_user)
        # print('')
        # print('Tests:')

        # env = config.get('env', None)
        # if env is None:
        #     raise Exception('Test environment was not specified')
        # current_schema = config.get('schema')
        # cfg = config.get(env)
        cfg = config
        self.test_config = config.get('configs', {})
        if self.test_config.get('resource', None) is not None:
            for key in self.test_config.get('resource').keys():
                if 'configs' in cfg.keys() and 'resource' in cfg.get('configs').keys():
                    self.test_config.get('resource').get(key).update(cfg.get('configs').get('resource').get(key, {}))
            if 'configs' in cfg.keys() and 'container' in cfg.get('configs').keys():
                self.test_config.get('container').update(cfg.get('configs').get('container'))
        self.fernet = fernet

        # endpoints
        self.endpoints = cfg.get('endpoints')
        self.swagger_endpoints = cfg.get('swagger')
        logger.info('Endpoints: %s' % self.endpoints)
            
        # redis connection
        if cfg.get('redis') is not None:
            self.redis_uri = cfg.get('redis').get('uri')
            if self.redis_uri is not None and self.redis_uri != '':
                rhost, rport, db = self.redis_uri.split(';')
                self.redis = redis.StrictRedis(host=rhost, port=int(rport), db=int(db))
        
        # celery broker
        self.broker = cfg.get('broker')
        
        # mysql connection
        self.db_uris = cfg.get('db-uris')  
        
        # get users
        self.users = cfg.get('users')
        
        # create auth client
        self.auth_client = BeehiveApiClient([], 'keyauth', None, '', None)
        
        # create api endpoint
        self.api = {}
        self.schema = {}
        for subsystem, endpoint in self.endpoints.items():
            self.api[subsystem] = RemoteClient(endpoint, keyfile=keyfile, certfile=certfile)
            # self.logger.info('Load swagger schema from %s' % endpoint)
            # self.schema[subsystem] = self.validate_swagger_schema(endpoint)

        self.load_result()

        self.custom_headers = {}
        self.endpoit_service = 'auth'

    @classmethod
    def tearDownClass(cls):
        cls.store_result()
        logger.log(60, '#################### Testplan %s - STOP ####################' % cls.__name__)
        logging.getLogger('beehive.test.run')\
            .log(60, '#################### Testplan %s - STOP ####################' % cls.__name__)

    @classmethod
    def load_config(cls, file_config):
        f = open(file_config, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    @classmethod
    def load_file(cls, file_config):
        f = open(file_config, 'r')
        config = f.read()
        if file_config.find('.json') > 0:
            config = json.loads(config)
        elif file_config.find('.yml') > 0:
            config = yaml.load(config, Loader=Loader)
        f.close()
        return config

    @classmethod
    def store_result(cls):
        global result
        if len(result.keys()) > 0:
            f = open('/tmp/test.result', 'w')
            f.write(json.dumps(result))
            f.close()

    @classmethod
    def load_result(cls):
        global result
        try:
            f = open('/tmp/test.result', 'r')
            config = f.read()
            result = json.loads(config)
            f.close()
        except:
            result = {}

    def convert(self, data, separator='.'):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = self.convert(v, separator)

        elif isinstance(data, list):
            datal = []
            for v in data:
                datal.append(self.convert(v, separator))
            data = datal

        elif isinstance(data, str) or isinstance(data, unicode):
            if data.find('$REF$') == 0:
                data = dict_get(self.test_config, data.lstrip('$REF$'), separator)
                data = self.convert(data, separator)

        return data

    def conf(self, key, separator='.'):
        res = dict_get(self.test_config, key, separator)

        if isinstance(res, dict):
            for k, v in res.items():
                res[k] = self.convert(v, separator)

        elif isinstance(res, list):
            newres = []
            for v in res:
                newres.append(self.convert(v, separator))
            res = newres

        return res

    def set_result(self, key, value):
        global result
        result[key] = value

    def get_result(self, key):
        global result
        return result.get(key, None)

    def setUp(self):
        logger.log(70, '========== %s ==========' % self.id()[8:])
        logging.getLogger('beehive.test.run').log(70, '========== %s ==========' % self.id()[9:])
        self.start = time.time()
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logger.log(70, '========== %s ========== : %ss' % (self.id()[8:], elapsed))
        logging.getLogger('beehive.test.run').log(70, '========== %s ========== : %ss' % (self.id()[9:], elapsed))
    
    def open_mysql_session(self, db_uri):
        engine = create_engine(db_uri)
        # engine = create_engine(app.db_uri, pool_size=10, max_overflow=10, pool_recycle=3600)
        db_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        return db_session
    
    def create_keyauth_token(self, user, pwd, timeout=5):
        global token, seckey
        data = {'user': user, 'password': pwd}
        headers = {'Content-Type': 'application/json'}
        endpoint = self.endpoints['auth']
        uri = '/v1.0/nas/keyauth/token'
        self.logger.debug('Request token to: %s' % endpoint + uri)
        response = requests.request('post', endpoint + uri, data=json.dumps(data), headers=headers, timeout=timeout,
                                    verify=False)
        res = response.json()
        self.logger.debug('Respone token: %s' % res)
        if res.get('code', None) is not None:
            raise Exception(res.get('message', ''))
        token = res['access_token']
        seckey = res['seckey']
        self.logger.debug('Get access token to: %s' % token)

    def validate_swagger_schema(self, endpoint, timeout=5):
        start = time.time()
        schema_uri = endpoint
        response = requests.request('GET', schema_uri, timeout=timeout, verify=False)
        schema = load(response.text)
        logger.info('Load swagger schema from %s: %ss' % (endpoint, time.time()-start))
        return schema    
    
    def get_schema(self, subsystem, endpoint, timeout=5):
        if self.validation_active is True:
            schema = self.schema.get(subsystem, None)
            if schema is None:
                self.logger.info('Load swagger schema from %s' % endpoint)
                schema = self.validate_swagger_schema(endpoint, timeout=timeout)
                self.schema[subsystem] = schema
            return schema
        return None
    
    def validate_response(self, resp_content_type, schema, path, method, response, runlog):
        validate = True
        if self.validation_active is True:
            # validate with swagger schema
            if resp_content_type.find('application/json') >= 0:
                validator = ApiValidator(schema, path, method)
                validate = validator.validate(response)
                if runlog is True:
                    self.runlogger.info('validate:         %s' % validate)
            else:
                if runlog is True:
                    self.runlogger.warn('validation supported only for application/json')
                validate = True
        return validate
    
    def call(self, subsystem, path, method, params=None, headers=None, user=None, pwd=None, auth=None, data=None,
             query=None, runlog=True, timeout=10, oauth2_token=None, response_size=400, pretty_response=False,
             *args, **kvargs):
        global token, seckey

        start = time.time()
        validate = False
        res = None

        try:
            cred = None
            uri = path
            if params is not None:
                uri = path.format(**params)
            
            if data is not None:
                data = json.dumps(data)
    
            if headers is None:
                headers = {}
    
            endpoint = self.endpoints[subsystem]
            swagger_endpoint = self.swagger_endpoints[subsystem]
            # schema = self.schema[subsystem]
            schema = self.get_schema(subsystem, swagger_endpoint, timeout=timeout)
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'            

            if auth == 'oauth2' and oauth2_token is not None:
                headers.update({'Authorization': 'Bearer %s' % oauth2_token})
            elif user is not None and auth == 'simplehttp':
                cred = HTTPBasicAuth(user, pwd)
                logger.debug('Make simple http authentication: %s' % time.time()-start)
            elif user is not None and auth == 'keyauth':
                if token is None:
                    self.create_keyauth_token(user, pwd, timeout=timeout)
                    logger.debug('Create keyauth token: %s - %s' % (token, time.time()-start))
                sign = self.auth_client.sign_request(seckey, uri)
                headers.update({'uid': token, 'sign': sign})

            # reset start after authentication
            start = time.time()

            if runlog is True:
                self.runlogger.info('request endpoint: %s' % endpoint)
                self.runlogger.info('request path:     %s' % uri)
                self.runlogger.info('request method:   %s' % method)
                self.runlogger.info('request user:     %s' % user)
                self.runlogger.info('request auth:     %s' % auth)
                self.runlogger.info('request params:   %s' % params)
                self.runlogger.info('request query:    %s' % query)
                self.runlogger.info('request data:     %s' % data)            
                self.runlogger.info('request headers:  %s' % headers)

            # execute request
            response = requests.request(method, endpoint + uri, auth=cred, params=query, data=data, headers=headers,
                                        timeout=timeout, verify=False)
            logger.info('Call api: %s' % response.url)
            
            if runlog is True:
                self.runlogger.info('request url:      %s' % response.url)
                self.runlogger.info('response headers: %s' % response.headers)
                self.runlogger.info('response code:    %s' % response.status_code)
            resp_content_type = response.headers['content-type']
            
            # evaluate response status
            # BAD_REQUEST     400     HTTP/1.1, RFC 2616, Section 10.4.1
            if response.status_code == 400:
                res = response.json().get('message')
                raise BadRequestException(res)
      
            # UNAUTHORIZED           401     HTTP/1.1, RFC 2616, Section 10.4.2
            elif response.status_code == 401:
                res = response.json().get('message')  
                raise UnauthorizedException(res)
            
            # PAYMENT_REQUIRED       402     HTTP/1.1, RFC 2616, Section 10.4.3
            
            # FORBIDDEN              403     HTTP/1.1, RFC 2616, Section 10.4.4
            elif response.status_code == 403:
                res = response.json().get('message')      
                raise ForbiddenException(res)
            
            # NOT_FOUND              404     HTTP/1.1, RFC 2616, Section 10.4.5
            elif response.status_code == 404:
                res = response.json().get('message')        
                raise NotFoundException(res)
            
            # METHOD_NOT_ALLOWED     405     HTTP/1.1, RFC 2616, Section 10.4.6
            elif response.status_code == 405:
                res = response.json().get('message')    
                raise MethodNotAllowedException(res)
            
            # NOT_ACCEPTABLE         406     HTTP/1.1, RFC 2616, Section 10.4.7
            elif response.status_code == 406:
                res = response.json().get('message')       
                raise NotAcceptableException(res)
            
            # PROXY_AUTHENTICATION_REQUIRED     407     HTTP/1.1, RFC 2616, Section 10.4.8
            
            # REQUEST_TIMEOUT        408
            elif response.status_code == 408:
                raise TimeoutException('Timeout')
            
            # CONFLICT               409
            elif response.status_code == 409:
                res = response.json().get('message')    
                raise ConflictException(res)
            
            # UNSUPPORTED_MEDIA_TYPE 415
            elif response.status_code == 415:
                res = response.json().get('message')    
                raise UnsupporteMediaTypeException(res)
            
            # INTERNAL SERVER ERROR  500
            elif response.status_code == 500:
                raise ServerErrorException('Internal server error')
            
            # NO_CONTENT             204    HTTP/1.1, RFC 2616, Section 10.2.5            
            elif response.status_code == 204:
                res = None
                
            # OK                     200    HTTP/1.1, RFC 2616, Section 10.2.1
            # CREATED                201    HTTP/1.1, RFC 2616, Section 10.2.2
            # ACCEPTED               202    HTTP/1.1, RFC 2616, Section 10.2.3
            # NON_AUTHORITATIVE_INFORMATION    203    HTTP/1.1, RFC 2616, Section 10.2.4
            # RESET_CONTENT          205    HTTP/1.1, RFC 2616, Section 10.2.6
            # PARTIAL_CONTENT        206    HTTP/1.1, RFC 2616, Section 10.2.7
            # MULTI_STATUS           207    WEBDAV RFC 2518, Section 10.2
            elif re.match('20[0-9]+', str(response.status_code)):
                if resp_content_type.find('application/json') >= 0:
                    res = response.json()
                    if runlog is True:
                        logger.debug(self.pp.pformat(res))
                    else:
                        logger.debug(truncate(res))
                elif resp_content_type.find('application/xml') >= 0:
                    # res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                    if runlog is True:
                        logger.debug(res)
                    else:
                        logger.debug(truncate(res))
                elif resp_content_type.find('text/xml') >= 0:
                    # res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                else:
                    res = response.text
            
            if runlog is True:
                self.runlogger.info('response data:    %s' % truncate(response.text, size=response_size))
            if pretty_response is True:
                self.runlogger.debug(self.pp.pformat(res))
            
            # validate with swagger schema
            validate = self.validate_response(resp_content_type, schema, path, method, response, runlog)
        except:
            logger.error('', exc_info=1)
            if runlog is True:
                self.runlogger.error('', exc_info=1)
            raise
        
        logger.debug('Call api elapsed: %s' % (time.time()-start))
        self.assertEqual(validate, True)
        return res

    def get(self, uri, query=None, params=None, timeout=600, user=None, pretty_response=False, runlog=True):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, 'get', data='', query=query, timeout=timeout, params=params,
                        headers=self.custom_headers, pretty_response=pretty_response, runlog=runlog, **user)
        return res

    def post(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, 'post', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        if res is not None and 'jobid' in res:
            self.wait_job(res['jobid'])
        return res

    def put(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, 'put', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        if res is not None and 'jobid' in res:
            self.wait_job(res['jobid'])
        return res

    def patch(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, 'patch', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        if res is not None and 'jobid' in res:
            self.wait_job(res['jobid'])
        return res

    def delete(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, 'delete', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        if res is not None and 'jobid' in res:
            self.wait_job(res['jobid'])
        return res

    def get_job_state(self, jobid):
        try:
            res = self.call(self.module, '/v1.0/%s/worker/tasks/{oid}' % self.module_prefix, 'get', 
                            params={'oid': jobid}, runlog=False, **self.users[self.run_test_user])
            job = res.get('task_instance')
            state = job.get('status')
            logger.debug('Get job %s state: %s' % (jobid, state))
            if state == 'FAILURE':
                for err in job.get('traceback', []):
                    self.runlogger.error(err.rstrip())
            return state
        except (NotFoundException, Exception):
            return 'EXPUNGED'

    def wait_job(self, jobid, delta=3, accepted_state='SUCCESS', maxtime=600):
        """Wait resource
        """
        logger.info('wait for:         %s' % jobid)
        self.runlogger.info('wait for:         %s' % jobid)
        state = self.get_job_state(jobid)
        elapsed = 0
        while state not in ['SUCCESS', 'FAILURE']:
            self.runlogger.info('.')
            sleep(delta)
            state = self.get_job_state(jobid)
            if elapsed > maxtime and state != accepted_state:
                state = TIMEOUT
        self.assertEqual(state, accepted_state)

    def setup_param_for_runner(self, param):
        param = '%s-%s' % (param, self.index)
        return param


class ColorFormatter(CeleryColorFormatter):
    #: Loglevel -> Color mapping.
    COLORS = colored().names
    colors = {'DEBUG': COLORS['blue'],
              'WARNING': COLORS['yellow'],
              'WARN': COLORS['yellow'],
              'ERROR': COLORS['red'],
              'CRITICAL': COLORS['magenta'],
              'TEST': COLORS['green'],
              'TESTPLAN': COLORS['cyan']
    }


def configure_test(testcase_class, args={}, log_file_name='test'):
    home = os.path.expanduser('~')
    log_file = '%s/%s.log' % (home, log_file_name)
    watch_file = '%s/%s.watch' % (home, log_file_name)
    run_file = '%s/%s.run' % (home, log_file_name)

    logging.captureWarnings(True)

    loggers = [
        logging.getLogger('beecell.perf'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, watch_file, frmt='%(message)s', formatter=ColorFormatter)

    loggers = [
        logging.getLogger('beehive.test.run'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, run_file, frmt='%(message)s', formatter=ColorFormatter)

    # setting logger
    frmt = '%(asctime)s - %(levelname)s - %(message)s'
    loggers = [
        logging.getLogger('beehive'),
        logging.getLogger('beedrones'),
        logging.getLogger('beecell'),
        logging.getLogger('beehive_resource'),
        logging.getLogger('beehive_service'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, log_file, frmt=frmt, formatter=ColorFormatter)

    if args == {} and len(sys.argv[1:]) > 0:
        for item in sys.argv[1:]:
            k, v = item.split('=')
            args[k] = v

    # read external params
    testcase_class.main_config_file = args.get('conf', None)
    testcase_class.spec_config_file = args.get('exconf', None)
    testcase_class.validation_active = args.get('validate', False)
    testcase_class.run_test_user = args.get('user', 'test1')


def runtest(testcase_class, tests, args={}):
    """Run test. Accept as external input args:
    -
        main_config_file = None
    spec_config_file = None
    validation_active


    :param testcase_class:
    :param tests:
    :return:
    """
    configure_test(testcase_class, args=args)

    # run test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(unittest.TestSuite(map(testcase_class, tests)))


def runtest_parallel(testcase_class, tests, args={}):
    """Run test. Accept as external input args:
    -
        main_config_file = None
    spec_config_file = None
    validation_active


    :param testcase_class:
    :param tests:
    :return:
    """
    results = Queue()

    def run_test(index, results):
        # run test suite
        configure_test(testcase_class, args=args, log_file_name='test-runner-'+index)
        runner = TestRunner(verbosity=2, index=index)
        testcase_class.index = index
        result = runner.run(unittest.TestSuite(map(testcase_class, tests)))
        results.put([index, result])

    max_test = args.get('max', 2)
    indexes = range(0, max_test)

    procs = [Process(target=run_test, args=(b(i), results)) for i in indexes]

    print('\nExecution plan:')
    print('----------------------------------------------------------------------')
    for p in procs:
        p.start()

    for p in procs:
        p.join()

    print('\nExecution results:')
    print('----------------------------------------------------------------------')
    for i in indexes:
        TestRunner(index=i).print_result(results.get()[1])
