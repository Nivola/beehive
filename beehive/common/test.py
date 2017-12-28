'''
Created on May 15, 2017

@author: darkbk
'''
import os

import gevent.monkey
from beehive.common.apiclient import BeehiveApiClient
from beehive.common.log import ColorFormatter

# from _random import Random
# os.environ['GEVENT_RESOLVER'] = 'ares'
# os.environ['GEVENTARES_SERVERS'] = 'ares'
# import beecell.server.gevent_ssl
gevent.monkey.patch_all()

import logging
import unittest
import pprint
import time
import json
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

seckey = None
token = None

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
    validatation_active = False
    validation_active = False

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

        # load config
        try:
            # config = self.load_config(u'%s/params.json' % path)
            home = os.path.expanduser(u'~')
            config = self.load_config(u'%s/beehive.json' % home)
            logger.info(u'get beehive test configuration')
        except Exception as ex:
            raise Exception(u'Error loading config file beehive.json. Search in user home. %s' % ex)
        
        env = config.get(u'env')
        current_schema = config.get(u'schema')
        cfg = config.get(env)
        self.test_config = cfg
        
        # endpoints
        self.endpoints = cfg.get(u'endpoints')
            
        # redis connection
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
        self.auth_client = BeehiveApiClient([], u'keyauth', None, None)
        
        # create api endpoint
        self.api = {}
        self.schema = {}
        for subsystem, endpoint in self.endpoints.items():
            self.api[subsystem] = RemoteClient(endpoint, keyfile=keyfile, certfile=certfile)
            # self.logger.info(u'Load swagger schema from %s' % endpoint)
            # self.schema[subsystem] = self.validate_swagger_schema(endpoint)

    @classmethod
    def tearDownClass(cls):
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
        
    def setUp(self):
        logger.log(70, u'========== %s ==========' % self.id()[9:])
        logging.getLogger(u'beehive.test.run').log(70, u'========== %s ==========' % self.id()[9:])
        self.start = time.time()
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logger.log(70, u'========== %s ========== : %ss' % (self.id()[9:], elapsed))
        logging.getLogger(u'beehive.test.run').log(70, u'========== %s ========== : %ss' % (self.id()[9:], elapsed))
    
    def open_mysql_session(self, db_uri):
        engine = create_engine(db_uri)
        
        """
        engine = create_engine(app.db_uri,
                               pool_size=10, 
                               max_overflow=10,
                               pool_recycle=3600)
        """
        db_session = sessionmaker(bind=engine, 
                                  autocommit=False, 
                                  autoflush=False)
        return db_session
    
    def create_keyauth_token(self, user, pwd):
        global token, seckey
        data = {u'user': user, u'password': pwd}
        headers = {u'Content-Type':u'application/json'}
        endpoint = self.endpoints[u'auth']
        uri = u'/v1.0/keyauth/token'
        response = requests.request(u'post', endpoint + uri, 
                                    data=json.dumps(data), headers=headers,
                                    timeout=5, verify=False)
        res = response.json()
        token = res[u'access_token']
        seckey = res[u'seckey']
    
    #@classmethod
    def validate_swagger_schema(self, endpoint):
        start = time.time()
        schema_uri = u'%s/apispec_1.json' % endpoint
        schema = load(schema_uri)
        logger.info(u'Load swagger schema from %s: %ss' % (endpoint, 
                                                           time.time()-start))
        return schema    
    
    def get_schema(self, subsystem, endpoint):
        if self.validatation_active is True or self.validation_active is True:
            schema = self.schema.get(subsystem, None)
            if schema is None:
                self.logger.info(u'Load swagger schema from %s' % endpoint)
                schema = self.validate_swagger_schema(endpoint)
                self.schema[subsystem] = schema
            return schema
        return None
    
    def validate_response(self, resp_content_type, schema, path, method, response, runlog):
        validate = True
        if self.validatation_active is True or self.validation_active is True:
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
    
    def call(self, subsystem, path, method, params=None, headers=None,
             user=None, pwd=None, auth=None, data=None, query=None, runlog=True,
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
            #schema = self.schema[subsystem]
            schema = self.get_schema(subsystem, endpoint)
            if u'Content-Type' not in headers:
                headers[u'Content-Type'] = u'application/json'            
    
            if user is not None and auth == u'simplehttp':
                cred = HTTPBasicAuth(user, pwd)
                logger.debug(u'Make simple http authentication: %s' % 
                             time.time()-start)
            elif user is not None and auth == u'keyauth':
                if token is None:
                    self.create_keyauth_token(user, pwd)
                    logger.debug(u'Create keyauth token: %s - %s' % 
                                 (token, time.time()-start))
                sign = self.auth_client.sign_request(seckey, uri)
                headers.update({u'uid':token, u'sign':sign})
            
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
            response = requests.request(method, endpoint + uri, auth=cred, 
                                   params=query, data=data, headers=headers,
                                   timeout=10, verify=False)
            
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
                    logger.debug(self.pp.pformat(res))
                elif resp_content_type.find(u'application/xml') >= 0:
                    #res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                elif resp_content_type.find(u'text/xml') >= 0:
                    #res = xmltodict.parse(response.text, dict_constructor=dict)
                    res = response.text
                else:
                    res = response.text
            
            if runlog is True:
                self.runlogger.info(u'response data:    %s' % response.text)
            
            # validate with swagger schema
            validate = self.validate_response(resp_content_type, schema, 
                path, method, response, runlog)
        except:
            logger.error(u'', exc_info=1)
            if runlog is True:
                self.runlogger.error(u'', exc_info=1)
            raise
        
        logger.debug(u'call elapsed: %s' % (time.time()-start))
        self.assertEqual(validate, True)
        return res
    
    '''
    def invoke(self, api, path, method, data=u'', headers={}, filter=None,
               auth_method=u'keyauth', credentials=None):
        """Invoke api 
    
        """
        global uid, seckey
        base_headers =  {u'Accept':u'application/json'}
        if auth_method == u'keyauth':
            sign = self.auth_client.sign_request(seckey, path)
            base_headers.update({u'uid':uid, u'sign':sign})
        elif auth_method == u'simplehttp':
            base_headers.update({
                u'Authorization':u'Basic %s' % b64encode(credentials.encode(u'utf-8'))
            })
        
        base_headers.update(headers)
        if filter is not None:
            if isinstance(filter, dict):
                filter = urllib.urlencode(filter)
            path = u'%s?%s' % (path, filter)
        if isinstance(data, dict):
            data = json.dumps(data)
        
        self.runlogger.info(u'path: %s' % path)
        self.runlogger.info(u'method: %s' % method)
        self.runlogger.info(u'data: %s' % data)
        self.runlogger.info(u'headers: %s' % base_headers)
        res = self.api[api].run_http_request2(path, method, data=data, 
                                              headers=base_headers)
        self.runlogger.info(u'res: %s' % res)
        return res
        #if res is not None:
        #    return res[u'response']

    def invoke_no_sign(self, api, path, method, data=u'', headers={}, filter=None):
        """Invoke api without sign"""
        base_headers =  {u'Accept':u'application/json'}
        base_headers.update(headers)
        if isinstance(data, dict):
            data = json.dumps(data)
        if filter is not None:
            if isinstance(filter, dict):
                filter = urllib.urlencode(filter)
            path = u'%s?%s' % (path, filter)
            
        self.runlogger.info(u'path: %s' % path)
        self.runlogger.info(u'method: %s' % method)
        self.runlogger.info(u'data: %s' % data)
        self.runlogger.info(u'headers: %s' % base_headers)
        res = self.api[api].run_http_request2(path, method, data=data, 
                                              headers=base_headers)
        self.runlogger.info(u'res: %s' % res)
        return res  '''

    '''
    #
    # keyauth
    #
    def test_get_keyauth_token(self):
        global uid, seckey
        data = {u'user':self.user, 
                u'password':self.pwd, 
                u'login-ip':self.ip}
        path = u'/v1.0/keyauth/login'
        base_headers = {u'Accept':u'application/json'}
        res = self.invoke_no_sign(u'auth', path, u'POST', data=data, 
                                  headers=base_headers, filter=None)
        print res
        uid = res[u'access_token']
        seckey = res[u'seckey']

    #
    # simplehttp
    #
    def test_simple_http_login(self):
        global uid, seckey   
        user = u'%s:%s' % (self.user, self.pwd)
        path = u'/v1.0/simplehttp/login'
        base_headers = {u'Accept':u'application/json',}
        data = {u'user':self.user, 
                u'password':self.pwd, 
                u'login-ip':self.ip}
        res = self.api[u'auth'].run_http_request2(path, u'POST', 
                                                  data=json.dumps(data), 
                                                  headers=base_headers)
        res = res[u'response']
        uid = None
        seckey = None'''


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


def runtest(testcase_class, tests):
    log_file = u'/tmp/test.log'
    watch_file = u'/tmp/test.watch'
    run_file = u'/tmp/test.run'
    
    logging.captureWarnings(True)    
    
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
    loggers = [
        logging.getLogger(u'beecell.perf'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, watch_file, frmt=u'%(message)s', formatter=ColorFormatter)
    
    loggers = [
        logging.getLogger(u'beehive.test.run'),
    ]
    LoggerHelper.file_handler(loggers, logging.INFO, run_file, frmt=u'%(message)s', formatter=ColorFormatter)
    
    # run test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(unittest.TestSuite(map(testcase_class, tests)))