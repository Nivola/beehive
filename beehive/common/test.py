'''
Created on May 15, 2017

@author: darkbk
'''
import os
#from _random import Random
#os.environ['GEVENT_RESOLVER'] = 'ares'
#os.environ['GEVENTARES_SERVERS'] = 'ares'

import beecell.server.gevent_ssl

import gevent.monkey
from beehive.common.log import ColorFormatter
from beehive.common.apiclient import BeehiveApiClient
gevent.monkey.patch_all()

import logging
import unittest
import pprint
import time
import json
import urllib
import redis
import re
from beecell.logger import LoggerHelper
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from beecell.test.runner import TextTestRunner
from beecell.remote import RemoteClient, ServerErrorException,\
    UnsupporteMediaTypeException, ConflictException, TimeoutException,\
    NotAcceptableException, MethodNotAllowedException, NotFoundException,\
    ForbiddenException, BadRequestException, UnauthorizedException
from base64 import b64encode
import requests
from beecell.swagger import ApiValidator
from flex.core import load
from requests.auth import HTTPBasicAuth
from requests import Request, Session

seckey = None
uid = None

logger = logging.getLogger(__name__)

class BeehiveTestCase(unittest.TestCase):
    logger = logging.getLogger(u'beehive.test.log')
    runlogger = logging.getLogger(u'beehive.test.run')
    pp = pprint.PrettyPrinter(width=200)
    
    #credentials = u'%s:%s' % (user1, pwd1)

    @classmethod
    def setUpClass(cls):
        logger.info(u'########## Testplan %s - START ##########' % cls.__name__)
        logging.getLogger(u'beehive.test.run')\
            .info(u'########## Testplan %s - START ##########' % cls.__name__)
        self = cls

        # ssl
        path = os.path.dirname(__file__).replace(u'beehive/common', u'beehive/tests')
        pos = path.find(u'tests')
        path = path[:pos+6]
        #keyfile = u'%s/ssl/nginx.key' % path
        #certfile = u'%s/ssl/nginx.key' % path
        keyfile = None
        certfile = None

        # load config
        config = self.load_config(u'%s/params.json' % path)
        
        env = config.get(u'env')
        current_user = config.get(u'user')
        current_schema = config.get(u'schema')
        cfg = config.get(env)
        # endpoints
        self.endpoints = cfg.get(u'endpoints')
            
        # redis connection
        self.redis_uri = cfg.get(u'redis-uri')
        rhost, rport, db = self.redis_uri.split(u';')
        self.redis = redis.StrictRedis(host=rhost, port=int(rport), db=int(db))
        
        # celery broker
        self.broker = cfg.get(u'broker')
        
        # mysql connection
        self.db_uri = cfg.get(u'db-uris').get(current_schema)   
        
        # get users
        self.users = cfg.get(u'users')
        
        # create auth client
        self.auth_client = BeehiveApiClient([], u'keyauth', None, None)
        
        # create api endpoint
        self.api = {}
        self.schema = {}
        for subsystem,endpoint in self.endpoints.items():
            self.api[subsystem] = RemoteClient(endpoint, 
                                               keyfile=keyfile, 
                                               certfile=certfile)
            self.schema[subsystem] = self.validate_swagger_schema(endpoint)

    @classmethod
    def tearDownClass(cls):
        logger.info(u'########## Testplan %s - STOP ##########' % cls.__name__)
        logging.getLogger(u'beehive.test.run')\
            .info(u'########## Testplan %s - STOP ##########' % cls.__name__) 

    @classmethod
    def load_config(cls, file_config):
        f = open(file_config, u'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    @classmethod
    def validate_swagger_schema(cls, endpoint):
        schema_uri = u'%s/apispec_1.json' % endpoint
        schema = load(schema_uri)
        logger.info(u'Load swagger schema from %s' % endpoint)
        return schema
        
    def setUp(self):
        logger.info(u'========== %s ==========' % self.id()[9:])
        logging.getLogger(u'beehive.test.run')\
            .info(u'========== %s ==========' % self.id()[9:])            
        self.start = time.time()
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logger.info(u'========== %s ========== : %ss\n' % (self.id()[9:], elapsed))
        logging.getLogger(u'beehive.test.run')\
            .info(u'========== %s ========== : %ss\n' % (self.id()[9:], elapsed))            
    
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
    
    def call(self, subsystem, path, method, params={}, headers={},
             user=None, pwd=None, data={}, *args, **kvargs):
        validate = False
        res = None

        try:
            auth = None
            uri = path.format(**params)
            data = json.dumps(data)
    
            endpoint = self.endpoints[subsystem]
            schema = self.schema[subsystem]
            headers[u'Content-Type'] = u'application/json'
    
            self.runlogger.info(u'endpoint: %s' % endpoint)
            self.runlogger.info(u'path: %s' % uri)
            self.runlogger.info(u'method: %s' % method)
            self.runlogger.info(u'params: %s' % params)
            self.runlogger.info(u'data: %s' % data)
            self.runlogger.info(u'headers: %s' % headers)
    
            if user is not None:
                auth = HTTPBasicAuth(user, pwd)
            s = Session()
            req = Request(method, endpoint + uri, auth=auth, data=data, 
                          headers=headers)
            prepped = s.prepare_request(req)
            response = s.send(prepped,
                stream=None,
                verify=False,
                proxies=None,
                cert=None,
                timeout=5
            )
            self.runlogger.info(u'response code: %s' % response.status_code)            
            
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
                res = response.json()
            
            self.runlogger.info(u'response: %s' % response.text)            
            
            # validate with swagger schema
            validator = ApiValidator(schema, path, method)
            validate = validator.validate(response)
            self.runlogger.info(u'validate: %s' % validate) 
        except:
            logger.error(u'', exc_info=1)
            self.runlogger.error(u'', exc_info=1)
            raise
        
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
        seckey = None

def runtest(testcase_class, tests):
    log_file = u'/tmp/test.log'
    watch_file = u'/tmp/test.watch'
    run_file = u'/tmp/test.run'
    
    logging.captureWarnings(True)    
    
    #setting logger
    #frmt = "%(asctime)s - %(levelname)s - %(process)s:%(thread)s - %(message)s"
    frmt = u'%(asctime)s - %(levelname)s - %(message)s'
    loggers = [
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beehive_resource'),
        logging.getLogger(u'beecell'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, log_file, frmt=frmt, 
                              formatter=ColorFormatter)
    loggers = [
        logging.getLogger(u'beecell.perf'),
    ]
    LoggerHelper.file_handler(loggers, logging.DEBUG, watch_file, 
                              frmt=u'%(message)s', formatter=ColorFormatter)
    
    loggers = [
        logging.getLogger(u'beehive.test.run'),
    ]
    LoggerHelper.file_handler(loggers, logging.INFO, run_file, 
                              frmt=u'%(message)s', formatter=ColorFormatter)    
    
    # run test suite
    #alltests = unittest.TestSuite(suite)
    #alltests = suite
    #print alltests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(unittest.TestSuite(map(testcase_class, tests)))
    #suite.run()
        
        