'''
Created on May 15, 2017

@author: darkbk
'''
import os
import sys

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
# from dict_recursive_update import recursive_update

seckey = None
token = None
result = {}

logger = logging.getLogger(__name__)


def assert_exception(exception):
    def wrapper(fn):
        def decorated(self, *args, **kwargs):
            self.assertRaises(exception, fn, self, *args, **kwargs)
        return decorated
    return wrapper


class BeehiveTestCase(unittest.TestCase):
    logger = logging.getLogger(u'beehive.test.log')
    runlogger = logging.getLogger(u'beehive.test.run')
    pp = pprint.PrettyPrinter(width=200)
    logging.addLevelName(60, u'TESTPLAN')
    logging.addLevelName(70, u'TEST')

    # module = u'resource'
    # module_prefix = u'nrs'

    main_config_file = None
    spec_config_file = None
    validation_active = False
    run_test_user = u'test1'

    @classmethod
    def setUpClass(cls):
        logger.log(60, u'#################### Testplan %s - START ####################' % cls.__name__)
        logging.getLogger(u'beehive.test.run')\
            .log(60, u'#################### Testplan %s - START ####################' % cls.__name__)
        self = cls

        # ssl
        path = os.path.dirname(__file__).replace(u'beehive/common', u'beehive/tests')
        pos = path.find(u'tests')
        path = path[:pos+6]
        keyfile = None
        certfile = None

        # load configs
        try:
            home = os.path.expanduser(u'~')
            if self.main_config_file is None:
                config_file = u'%s/beehive.yml' % home
                self.main_config_file = config_file
            else:
                config_file = self.main_config_file
            config = self.load_file(config_file)
            logger.info(u'Get beehive test configuration: %s' % config_file)
        except Exception as ex:
            raise Exception(u'Error loading config file. Search in user home. %s' % ex)

        # load specific configs for a set of test
        try:
            if self.spec_config_file is not None:
                config2 = self.load_file(self.spec_config_file)
                recursive_update(config, config2)
                logger.info(u'Get beehive test specific configuration: %s' % self.spec_config_file)
        except Exception as ex:
            raise Exception(u'Error loading config file. Search in user home. %s' % ex)

        logger.info(u'Validation active: %s' % cls.validation_active)

        print(u'Configurations:')
        print(u'Main config file: %s' % cls.main_config_file)
        print(u'Extra config file: %s' % cls.spec_config_file)
        print(u'Validation active: %s' % cls.validation_active)
        print(u'Test user: %s' % cls.run_test_user)
        print(u'')
        print(u'Tests:')

        # env = config.get(u'env', None)
        # if env is None:
        #     raise Exception(u'Test environment was not specified')
        # current_schema = config.get(u'schema')
        # cfg = config.get(env)
        cfg = config
        self.test_config = config.get(u'configs', {})
        for key in self.test_config.get(u'resource').keys():
            if u'configs' in cfg.keys() and u'resource' in cfg.get(u'configs').keys():
                self.test_config.get(u'resource').get(key).update(cfg.get(u'configs').get(u'resource').get(key, {}))
        if u'configs' in cfg.keys() and u'container' in cfg.get(u'configs').keys():
            self.test_config.get(u'container').update(cfg.get(u'configs').get(u'container'))

        # endpoints
        self.endpoints = cfg.get(u'endpoints')
        self.swagger_endpoints = cfg.get(u'swagger')
        logger.info(u'Endpoints: %s' % self.endpoints)
            
        # redis connection
        if cfg.get(u'redis') is not None:
            self.redis_uri = cfg.get(u'redis').get(u'uri')
            if self.redis_uri is not None and self.redis_uri != u'':
                rhost, rport, db = self.redis_uri.split(u';')
                self.redis = redis.StrictRedis(host=rhost, port=int(rport), db=int(db))
        
        # celery broker
        self.broker = cfg.get(u'broker')
        
        # mysql connection
        self.db_uris = cfg.get(u'db-uris')  
        
        # get users
        self.users = cfg.get(u'users')
        
        # create auth client
        self.auth_client = BeehiveApiClient([], u'keyauth', None, u'', None)
        
        # create api endpoint
        self.api = {}
        self.schema = {}
        for subsystem, endpoint in self.endpoints.items():
            self.api[subsystem] = RemoteClient(endpoint, keyfile=keyfile, certfile=certfile)
            # self.logger.info(u'Load swagger schema from %s' % endpoint)
            # self.schema[subsystem] = self.validate_swagger_schema(endpoint)

        self.load_result()

        self.custom_headers = {}
        self.endpoit_service = u'auth'

    @classmethod
    def tearDownClass(cls):
        cls.store_result()
        logger.log(60, u'#################### Testplan %s - STOP ####################' % cls.__name__)
        logging.getLogger(u'beehive.test.run')\
            .log(60, u'#################### Testplan %s - STOP ####################' % cls.__name__)

    @classmethod
    def load_config(cls, file_config):
        f = open(file_config, u'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    @classmethod
    def load_file(cls, file_config):
        f = open(file_config, u'r')
        config = f.read()
        if file_config.find(u'.json') > 0:
            config = json.loads(config)
        elif file_config.find(u'.yml') > 0:
            config = yaml.load(config, Loader=Loader)
        f.close()
        return config

    @classmethod
    def store_result(cls):
        global result
        if len(result.keys()) > 0:
            f = open(u'/tmp/test.result', u'w')
            f.write(json.dumps(result))
            f.close()

    @classmethod
    def load_result(cls):
        global result
        try:
            f = open(u'/tmp/test.result', u'r')
            config = f.read()
            result = json.loads(config)
            f.close()
        except:
            result = {}

    def convert(self, data, separator=u'.'):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = self.convert(v, separator)

        elif isinstance(data, list):
            datal = []
            for v in data:
                datal.append(self.convert(v, separator))
            data = datal

        elif isinstance(data, str) or isinstance(data, unicode):
            if data.find(u'$REF$') == 0:
                data = dict_get(self.test_config, data.lstrip(u'$REF$'), separator)

        return data

    def conf(self, key, separator=u'.'):
        res = dict_get(self.test_config, key, separator)
        if isinstance(res, dict):
            for k, v in res.items():
                res[k] = self.convert(v, separator)
        return res

    def set_result(self, key, value):
        global result
        result[key] = value

    def get_result(self, key):
        global result
        return result.get(key, None)

    def setUp(self):
        logger.log(70, u'========== %s ==========' % self.id()[8:])
        logging.getLogger(u'beehive.test.run').log(70, u'========== %s ==========' % self.id()[9:])
        self.start = time.time()
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logger.log(70, u'========== %s ========== : %ss' % (self.id()[8:], elapsed))
        logging.getLogger(u'beehive.test.run').log(70, u'========== %s ========== : %ss' % (self.id()[9:], elapsed))
    
    def open_mysql_session(self, db_uri):
        engine = create_engine(db_uri)
        # engine = create_engine(app.db_uri, pool_size=10, max_overflow=10, pool_recycle=3600)
        db_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        return db_session
    
    def create_keyauth_token(self, user, pwd, timeout=5):
        global token, seckey
        data = {u'user': user, u'password': pwd}
        headers = {u'Content-Type': u'application/json'}
        endpoint = self.endpoints[u'auth']
        uri = u'/v1.0/nas/keyauth/token'
        self.logger.debug(u'Request token to: %s' % endpoint + uri)
        response = requests.request(u'post', endpoint + uri, data=json.dumps(data), headers=headers, timeout=timeout,
                                    verify=False)
        res = response.json()
        token = res[u'access_token']
        seckey = res[u'seckey']
        self.logger.debug(u'Get access token to: %s' % token)

    def validate_swagger_schema(self, endpoint, timeout=5):
        start = time.time()
        schema_uri = endpoint
        response = requests.request(u'GET', schema_uri, timeout=timeout, verify=False)
        schema = load(response.text)
        logger.info(u'Load swagger schema from %s: %ss' % (endpoint, time.time()-start))
        return schema    
    
    def get_schema(self, subsystem, endpoint, timeout=5):
        if self.validation_active is True:
            schema = self.schema.get(subsystem, None)
            if schema is None:
                self.logger.info(u'Load swagger schema from %s' % endpoint)
                schema = self.validate_swagger_schema(endpoint, timeout=timeout)
                self.schema[subsystem] = schema
            return schema
        return None
    
    def validate_response(self, resp_content_type, schema, path, method, response, runlog):
        validate = True
        if self.validation_active is True:
            # validate with swagger schema
            if resp_content_type.find(u'application/json') >= 0:
                validator = ApiValidator(schema, path, method)
                validate = validator.validate(response)
                if runlog is True:
                    self.runlogger.info(u'validate:         %s' % validate)
            else:
                if runlog is True:
                    self.runlogger.warn(u'validation supported only for application/json')
                validate = True
        return validate
    
    def call(self, subsystem, path, method, params=None, headers=None, user=None, pwd=None, auth=None, data=None,
             query=None, runlog=True, timeout=10, oauth2_token=None, response_size=400, *args, **kvargs):
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
            if u'Content-Type' not in headers:
                headers[u'Content-Type'] = u'application/json'            

            if auth == u'oauth2' and oauth2_token is not None:
                headers.update({u'Authorization': u'Bearer %s' % oauth2_token})
            elif user is not None and auth == u'simplehttp':
                cred = HTTPBasicAuth(user, pwd)
                logger.debug(u'Make simple http authentication: %s' % time.time()-start)
            elif user is not None and auth == u'keyauth':
                if token is None:
                    self.create_keyauth_token(user, pwd, timeout=timeout)
                    logger.debug(u'Create keyauth token: %s - %s' % (token, time.time()-start))
                sign = self.auth_client.sign_request(seckey, uri)
                headers.update({u'uid': token, u'sign': sign})

            if runlog is True:
                self.runlogger.info(u'request endpoint: %s' % endpoint)
                self.runlogger.info(u'request path:     %s' % uri)
                self.runlogger.info(u'request method:   %s' % method)
                self.runlogger.info(u'request user:     %s' % user)
                self.runlogger.info(u'request auth:     %s' % auth)
                self.runlogger.info(u'request params:   %s' % params)
                self.runlogger.info(u'request query:    %s' % query)
                self.runlogger.info(u'request data:     %s' % data)            
                self.runlogger.info(u'request headers:  %s' % headers)

            # execute request
            response = requests.request(method, endpoint + uri, auth=cred, params=query, data=data, headers=headers,
                                        timeout=timeout, verify=False)
            self.runlogger.info(u'request url:      %s' % response.url)
            
            if runlog is True:
                self.runlogger.info(u'response headers: %s' % response.headers)
                self.runlogger.info(u'response code:    %s' % response.status_code)
            resp_content_type = response.headers[u'content-type']
            
            # evaluate response status
            # BAD_REQUEST     400     HTTP/1.1, RFC 2616, Section 10.4.1
            if response.status_code == 400:
                res = response.json().get(u'message')
                raise BadRequestException(res)
      
            # UNAUTHORIZED           401     HTTP/1.1, RFC 2616, Section 10.4.2
            elif response.status_code == 401:
                res = response.json().get(u'message')  
                raise UnauthorizedException(res)
            
            # PAYMENT_REQUIRED       402     HTTP/1.1, RFC 2616, Section 10.4.3
            
            # FORBIDDEN              403     HTTP/1.1, RFC 2616, Section 10.4.4
            elif response.status_code == 403:
                res = response.json().get(u'message')      
                raise ForbiddenException(res)
            
            # NOT_FOUND              404     HTTP/1.1, RFC 2616, Section 10.4.5
            elif response.status_code == 404:
                res = response.json().get(u'message')        
                raise NotFoundException(res)
            
            # METHOD_NOT_ALLOWED     405     HTTP/1.1, RFC 2616, Section 10.4.6
            elif response.status_code == 405:
                res = response.json().get(u'message')    
                raise MethodNotAllowedException(res)
            
            # NOT_ACCEPTABLE         406     HTTP/1.1, RFC 2616, Section 10.4.7
            elif response.status_code == 406:
                res = response.json().get(u'message')       
                raise NotAcceptableException(res)
            
            # PROXY_AUTHENTICATION_REQUIRED     407     HTTP/1.1, RFC 2616, Section 10.4.8
            
            # REQUEST_TIMEOUT        408
            elif response.status_code == 408:
                raise TimeoutException(u'Timeout')
            
            # CONFLICT               409
            elif response.status_code == 409:
                res = response.json().get(u'message')    
                raise ConflictException(res)
            
            # UNSUPPORTED_MEDIA_TYPE 415
            elif response.status_code == 415:
                res = response.json().get(u'message')    
                raise UnsupporteMediaTypeException(res)
            
            # INTERNAL SERVER ERROR  500
            elif response.status_code == 500:
                raise ServerErrorException(u'Internal server error')
            
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
            elif re.match(u'20[0-9]+', str(response.status_code)):
                if resp_content_type.find(u'application/json') >= 0:
                    res = response.json()
                    if runlog is True:
                        logger.debug(self.pp.pformat(res))
                    else:
                        logger.debug(truncate(res))
                elif resp_content_type.find(u'application/xml') >= 0:
                    # res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                    if runlog is True:
                        logger.debug(res)
                    else:
                        logger.debug(truncate(res))
                elif resp_content_type.find(u'text/xml') >= 0:
                    # res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                else:
                    res = response.text
            
            if runlog is True:
                self.runlogger.info(u'response data:    %s' % truncate(response.text, size=response_size))
            
            # validate with swagger schema
            validate = self.validate_response(resp_content_type, schema, path, method, response, runlog)
        except:
            logger.error(u'', exc_info=1)
            if runlog is True:
                self.runlogger.error(u'', exc_info=1)
            raise
        
        logger.debug(u'call elapsed: %s' % (time.time()-start))
        self.assertEqual(validate, True)
        return res

    def get(self, uri, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, u'get', data=u'', query=query, timeout=timeout, params=params,
                        headers=self.custom_headers, **user)
        return res

    def post(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, u'post', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        return res

    def put(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, u'put', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        return res

    def patch(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, u'patch', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        return res

    def delete(self, uri, data=None, query=None, params=None, timeout=600, user=None):
        if user is None:
            user = self.users[self.run_test_user]
        res = self.call(self.endpoint_service, uri, u'delete', data=data, query=query, params=params, timeout=timeout,
                        headers=self.custom_headers, **user)
        return res

    def get_job_state(self, jobid):
        try:
            res = self.call(self.module, u'/v1.0/%s/worker/tasks/{oid}' % self.module_prefix, u'get', 
                            params={u'oid': jobid}, runlog=False, **self.users[self.run_test_user])
            job = res.get(u'task_instance')
            state = job.get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                for err in job.get(u'traceback', []):
                    self.runlogger.error(err.rstrip())
            return state
        except (NotFoundException, Exception):
            return u'EXPUNGED'

    def wait_job(self, jobid, delta=3, accepted_state=u'SUCCESS'):
        """Wait resource
        """
        logger.info(u'wait for:         %s' % jobid)
        self.runlogger.info(u'wait for:         %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in [u'SUCCESS', u'FAILURE']:
            self.runlogger.info(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)
        self.assertEqual(state, accepted_state)


class ColorFormatter(CeleryColorFormatter):
    #: Loglevel -> Color mapping.
    COLORS = colored().names
    colors = {u'DEBUG': COLORS[u'blue'],
              u'WARNING': COLORS[u'yellow'],
              u'WARN': COLORS[u'yellow'],
              u'ERROR': COLORS[u'red'],
              u'CRITICAL': COLORS[u'magenta'],
              u'TEST': COLORS[u'green'],
              u'TESTPLAN': COLORS[u'cyan']
    }


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
    home = os.path.expanduser(u'~')
    log_file = home + u'/test.log'
    watch_file = home + u'/test.watch'
    run_file = home + u'/test.run'
    
    logging.captureWarnings(True)

    loggers = [
        logging.getLogger(u'beecell.perf'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, watch_file, frmt=u'%(message)s', formatter=ColorFormatter)

    loggers = [
        logging.getLogger(u'beehive.test.run'),
    ]
    LoggerHelper.file_handler(loggers, logging.INFO, run_file, frmt=u'%(message)s', formatter=ColorFormatter)

    # setting logger
    # frmt = "%(asctime)s - %(levelname)s - %(process)s:%(thread)s - %(message)s"
    frmt = u'%(asctime)s - %(levelname)s - %(message)s'
    loggers = [
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beedrones'),
        logging.getLogger(u'beecell'),
        logging.getLogger(u'beehive_resource'),
        logging.getLogger(u'beehive_service'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, log_file, frmt=frmt, formatter=ColorFormatter)

    try:
        testcase_class.spec_config_file = sys.argv[1]
    except:
        pass
    try:
        testcase_class.validation_active = str2bool(sys.argv[2])
    except:
        pass

    # read external params
    testcase_class.main_config_file = args.get(u'conf', None)
    testcase_class.spec_config_file = args.get(u'exconf', None)
    testcase_class.validation_active = args.get(u'validate', True)
    testcase_class.run_test_user = args.get(u'user', u'test1')

    # run test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(unittest.TestSuite(map(testcase_class, tests)))
