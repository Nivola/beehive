'''
Created on Dec 9, 2013

@author: darkbk
'''
import os
#from _random import Random
#os.environ['GEVENT_RESOLVER'] = 'ares'
#os.environ['GEVENTARES_SERVERS'] = 'ares'

import beecell.server.gevent_ssl

import gevent.monkey
gevent.monkey.patch_all()

import cProfile
import logging
import unittest
import pprint
import time
import json
import urllib, urllib2
import httplib
import redis
from beecell.logger import LoggerHelper
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from beecell.test.runner import TextTestRunner
from beecell.remote import RemoteClient

seckey = None
uid = None

class CloudapiTestCase(unittest.TestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """    
    logger = logging.getLogger('gibbon.test')
    pp = pprint.PrettyPrinter(width=200)
    
    #
    # mysql connection
    #
    #db_uri = "mysql+pymysql://cloudapi:cloudapi@localhost:3306/cloudapi"
    #db_uri = "mysql+pymysql://cloudapi2:cloudapi2@localhost:3306/cloudapi2"
    #db_uri = "mysql+pymysql://cloudapi:cloudapi@10.102.90.203:3308/cloudapi"
    db_uri = "mysql+pymysql://cloudapi:cloudapi@10.102.160.240:3306/cloudapi"     
    #api_url = "http://172.16.0.3:5000/api"
    #api_url = "http://158.102.160.234:5000/api"
    
    #
    # postgres connection
    #    
    cmdb_uri = 'postgresql+psycopg2://pastext:pent4ho@vm-cmdbuild.csi.it:5432/cmdbprod'
    
    #
    # cloudapi connection
    #        
    #self.proto = 'https'
    proto = 'https'
    proto = 'http'
    #host = '158.102.160.234'
    #host = '172.16.0.19'
    #host = 'localhost'
    host = '10.102.47.208'
    #host = '172.25.5.39'
    host = '10.102.160.240'
    host = '10.102.145.141'
    #port = 8443
    port = 6062
    #port = 
    auth_port = 6060
    #auth_port = 1443
    #port = 3443
    
    server = {'auth':{'proto':'http', 'host':'10.102.160.240', 'port':6060, 'path':''},
              'core':{'proto':'http', 'host':'10.102.160.240', 'port':6061, 'path':''},
              'resource':{'proto':'http', 'host':'10.102.160.240', 'port':60602, 'path':''},
              'tenant':{'proto':'http', 'host':'10.102.160.240', 'port':6064, 'path':''},
              'resource2':{'proto':'http', 'host':'10.102.160.12', 'port':6062, 'path':''},              
              'service':{'proto':'http', 'host':'10.102.160.240', 'port':6063, 'path':''},
              'monitor':{'proto':'http', 'host':'10.102.160.240', 'port':6065, 'path':''}}
    
    '''server = {'auth':{'proto':'https', 'host':'10.102.145.141', 'port':1443, 'path':''},
              'core':{'proto':'http', 'host':'10.102.145.141', 'port':6061, 'path':''},
              'resource':{'proto':'https', 'host':'10.102.145.141', 'port':3443, 'path':''},
              'resource2':{'proto':'http', 'host':'10.102.160.12', 'port':6060, 'path':''},              
              'service':{'proto':'http', 'host':'10.102.160.240', 'port':6063, 'path':''},
              'monitor':{'proto':'http', 'host':'10.102.160.240', 'port':6065, 'path':''}}    
    '''
    
    user = 'admin@local'
    pwd = 'testlab'
    ip = '158.102.160.234'
    
    #
    # redis connection
    #        
    #redis_uri = '10.102.47.208;6379;0'
    redis_uri = 'localhost;6379;0'
    rhost, rport, db = redis_uri.split(";")
    redis = redis.StrictRedis(host=rhost, port=int(rport), db=int(db))
    
    #
    # cloudapi event consumer
    #
    #self.event_host = '158.102.160.234'
    event_host = '172.16.0.16'
    event_port = 5500    
    
    #
    # cloudstack connection
    #
    '''
    clsk_conn = {
        'api':('http://172.16.0.19:8080/client/api',
               'OkeTG2ntyuim408elcgNzOxA5xUUky67zJDbq7sfB_gdKEtMihu_YVohmgetfVgCGQFq13rT0dJmNeFHuJWAFw',
               '4HVJYDkcRBjBoyXHy4GJTxF7NBWDFWNpsS7f82o-UdVwBehxPiNAqdCcv7e1slpqJ4uvNowhdoeTqOYHfowqLA',
               5),
        'db':('172.16.0.19', '3406', 'cloud', 'cloud', 'testlab', 5),
        'zone':'zona_kvm_01'}
    '''
    clsk_conn = {
        'api':('http://10.102.90.209:8080/client/api',
               'OkeTG2ntyuim408elcgNzOxA5xUUky67zJDbq7sfB_gdKEtMihu_YVohmgetfVgCGQFq13rT0dJmNeFHuJWAFw',
               '4HVJYDkcRBjBoyXHy4GJTxF7NBWDFWNpsS7f82o-UdVwBehxPiNAqdCcv7e1slpqJ4uvNowhdoeTqOYHfowqLA',
              5),
        'db':('10.102.90.209', '3306', 'cloud', 'cloud', 'testlab', 5),
        'zone':'zona_kvm_01'}    

    @classmethod
    def setUpClass(cls):
        pass
        #cls._connection = createExpensiveConnectionObject()

    @classmethod
    def tearDownClass(cls):
        pass
        #cls._connection.destroy()

    def setUp(self):
        logging.getLogger('gibbon.test').info('========== %s ==========' % self.id()[9:])
        self.start = time.time()
        
        # ssl
        path = os.path.dirname(__file__)
        pos = path.find('tests')
        path = path[:pos+6]
        keyfile = "%s/ssl/nginx.key" % path
        certfile = "%s/ssl/nginx.crt" % path
        keyfile = None
        certfile = None
        
        self.api = {'auth':RemoteClient(self.server['auth'], keyfile=keyfile, certfile=certfile),
                    'core':RemoteClient(self.server['core'], keyfile=keyfile, certfile=certfile),
                    'resource':RemoteClient(self.server['resource'], keyfile=keyfile, certfile=certfile),
                    'tenant':RemoteClient(self.server['tenant'], keyfile=keyfile, certfile=certfile),
                    'resource2':RemoteClient(self.server['resource2'], keyfile=keyfile, certfile=certfile),                    
                    'service':RemoteClient(self.server['service'], keyfile=keyfile, certfile=certfile),
                    'monitor':RemoteClient(self.server['monitor'], keyfile=keyfile, certfile=certfile)}
        
    def tearDown(self):
        elapsed = round(time.time() - self.start, 4)
        logging.getLogger('gibbon.test').info("========== %s ========== : %ss\n" % 
                                         (self.id()[9:], elapsed))
    
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
    
    def invoke(self, api, path, method, data=u'', headers={}, filter=None):
        """Invoke api """
        sign = self.auth_client.sign_request(seckey, path)      
        base_headers =  {u'Accept':u'json',
                         u'uid':uid,
                         u'sign':sign}
        base_headers.update(headers)
        if filter is not None:
            path = u'%s?%s' % (path, filter)
        res = self.api[api].run_http_request2(path, method, data=data, 
                                              headers=base_headers)
        return res[u'response']

    def test_login(self):
        global uid, seckey   
        data = {u'user':self.user, u'password':self.pwd}
        path = u'/api/auth/login/'
        base_headers = {u'Accept':u'json'}
        res = self.api[u'auth'].run_http_request2(path, u'POST', 
                                                  data=json.dumps(data), 
                                                  headers=base_headers)        
        res = res[u'response']
        uid = res[u'uid']
        seckey = res[u'seckey']

    def test_logout(self):
        global uid, seckey, contid
        sign = self.auth_client.sign_request(seckey, '/api/auth/logout/')
        self.invoke(u'auth', u'/api/auth/logout/', u'POST', data='')

def run_test(suite):
    log_file = '/tmp/test.log'
    data_file = '/tmp/data.log'
    watch_file = '/tmp/test.watch'
    
    logging.captureWarnings(True)    
    
    #setting logger
    #frmt = "%(asctime)s - %(levelname)s - %(process)s:%(thread)s - %(message)s"
    frmt = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger('gibbon.test')
    LoggerHelper.setup_file_handler(logger, logging.DEBUG, log_file, frmt=frmt)

    severLogger = logging.getLogger('gibboncloudapi')
    LoggerHelper.setup_file_handler(severLogger, logging.DEBUG, log_file, frmt=frmt)
    
    severLogger = logging.getLogger('beecell')
    LoggerHelper.setup_file_handler(severLogger, logging.DEBUG, log_file, frmt=frmt)
    
    frmt = "%(asctime)s - %(process)s:%(thread)s - %(message)s"
    severLogger = logging.getLogger('gibboncloudapi.transaction')
    LoggerHelper.setup_file_handler(severLogger, logging.DEBUG, data_file, frmt=frmt)

    severLogger = logging.getLogger('beecell.perf')
    LoggerHelper.setup_file_handler(severLogger, logging.DEBUG, watch_file, frmt='%(message)s')
    
    # run test suite
    alltests = unittest.TestSuite(suite)
    #print alltests
    TextTestRunner(verbosity=2).run(alltests)






"""
def run_unit_test(class_test, unit_test):
    test = class_test(unit_test)
    TextTestRunner(verbosity=2).run(test)

def run_test(class_test, suite):
    set_logging()   
    #run_test([test_suite()])
    for item in suite:
        greenlet = gevent.spawn(run_unit_test, class_test, item)
        greenlet.join()
"""

#if __name__ == '__main__':
# start profile over test suite
#cProfile.run('run_test()', 'log/test.profile')
#p = pstats.Stats('log/test.profile')