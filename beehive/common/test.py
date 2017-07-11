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
from beecell.logger import LoggerHelper
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from beecell.test.runner import TextTestRunner
from beecell.remote import RemoteClient
from base64 import b64encode

seckey = None
uid = None

class BeehiveTestCase(unittest.TestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """    
    logger = logging.getLogger(u'beehive.test')
    pp = pprint.PrettyPrinter(width=200)
    
    #credentials = u'%s:%s' % (user1, pwd1)

    @classmethod
    def setUpClass(cls):
        pass
        #cls._connection = createExpensiveConnectionObject()

    @classmethod
    def tearDownClass(cls):
        pass
        #cls._connection.destroy()

    def load_config(self, file_config):
        f = open(file_config, u'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config

    def setUp(self):
        logging.getLogger(u'beehive.test')\
               .info(u'========== %s ==========' % self.id()[9:])
        self.start = time.time()
        
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
        #for k,v in self.load_config():
        #    setattr(self, k, v)
        
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
        self.user = self.users.get(current_user).get(u'user')
        self.pwd = self.users.get(current_user).get(u'pwd')
        self.ip = self.users.get(current_user).get(u'ip')        
        
        # create auth client
        self.auth_client = BeehiveApiClient([], u'keyauth', None, None)
        
        # create api endpoint
        self.api = {}
        for subsystem,endpoint in self.endpoints.items():
            self.api[subsystem] = RemoteClient(endpoint, 
                                               keyfile=keyfile, 
                                               certfile=certfile)
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logging.getLogger(u'beehive.test')\
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
            
        res = self.api[api].run_http_request2(path, method, data=data, 
                                              headers=base_headers)
        if res is not None:
            return res[u'response']

    def invoke_no_sign(self, api, path, method, data=u'', headers={}, filter=None):
        """Invoke api without sign"""
        base_headers =  {u'Accept':u'application/json'}
        base_headers.update(headers)
        if filter is not None:
            if isinstance(filter, dict):
                filter = urllib.urlencode(filter)
            path = u'%s?%s' % (path, filter)
        res = self.api[api].run_http_request2(path, method, data=data, 
                                              headers=base_headers)
        return res[u'response']    

    #
    # keyauth
    #
    def test_login(self):
        global uid, seckey   
        data = {u'user':self.user, 
                u'password':self.pwd, 
                u'login_ip':self.ip}
        path = u'/v1.0/keyauth/login/'
        base_headers = {u'Accept':u'application/json'}
        res = self.api[u'auth'].run_http_request2(path, u'POST', 
                                                  data=json.dumps(data), 
                                                  headers=base_headers)
        #self.logger.info(json.dumps(res, indent=4)) 
        res = res[u'response']
        uid = res[u'uid']
        seckey = res[u'seckey']

    def test_logout(self):
        self.invoke(u'auth', u'/v1.0/keyauth/logout/', u'DELETE', data='')

    #
    # simplehttp
    #
    def test_simple_http_login(self):
        global uid, seckey   
        user = u'%s:%s' % (self.user, self.pwd)
        path = u'/v1.0/simplehttp/login/'
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

def runtest(suite):
    log_file = u'/tmp/test.log'
    watch_file = u'/tmp/test.watch'
    
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
    
    # run test suite
    #alltests = unittest.TestSuite(suite)
    alltests = suite
    #print alltests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(alltests)
    #suite.run()
        
        