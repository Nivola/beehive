'''
Created on Jun 16, 2017

@author: darkbk
'''
import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase
import logging
from beecell.logger.helper import LoggerHelper
from beecell.simple import parse_redis_uri
import pprint
import redis
import gevent

class SimpleEventConsumer(object):
    def __init__(self, redis_uri, redis_channel):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        self.redis_uri = redis_uri
        self.redis_channel = redis_channel     
        
        # set redis manager
        host, port, db = parse_redis_uri(redis_uri)
        self.redis = redis.StrictRedis(
            host=host, port=int(port), db=int(db))
        
        self.pp = pprint.PrettyPrinter(indent=2)

    def start_subscriber(self):
        """
        """
        channel = self.redis.pubsub()
        channel.subscribe(self.redis_channel)

        self.logger.info(u'Start event consumer on redis channel %s:%s' % 
                        (self.redis_uri, self.redis_channel))
        while True:
            try:
                msg = channel.get_message()
                if msg and msg[u'type'] == u'message':
                    # get event data
                    data = json.loads(msg[u'data'])
                    #self.logger.debug(data)
                    etype = data[u'type']
                    data = data[u'data']
                    if etype == u'API':
                        op = data[u'op']
                        self.logger.debug(u'%s %s [%s] - %s' % (
                            data[u'opid'], op[u'path'], op[u'method'], 
                            data[u'elapsed']))
                    elif etype == u'JOB':
                        self.logger.debug(u'%s %s - %s.%s - %s' % (
                            data[u'opid'], data[u'op'], 
                            data[u'task'].split(u'.')[-1], 
                            data[u'taskid'], data[u'response']))
                    elif etype == u'CMD':
                        self.logger.debug(u'%s %s - %s - %s' % (
                            data[u'opid'], data[u'op'], data[u'response'], 
                            data[u'elapsed']))
                    
                gevent.sleep(0.05)  # be nice to the system :) 0.05
            except (gevent.Greenlet.GreenletExit, Exception) as ex:
                self.logger.error(u'Error receiving message: %s', exc_info=1)                 
                    
        self.logger.info(u'Stop event consumer on redis channel %s:%s' % 
                         (self.redis_uri, self.redis_channel)) 

class SimpleEventConsumerCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
        # start event consumer
        redis_uri = self.redis_uri
        redis_channel = u'beehive.event.sub'
        self.consumer = SimpleEventConsumer(redis_uri, redis_channel)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)
    
    #
    # simplehttp
    #
    def test_start_consumer(self):
        # internal logger
        logger = logging.getLogger(u'__main__')   
        
        logger_level = logging.DEBUG
        loggers = [logger]
        frmt = "%(asctime)s - %(message)s"
        LoggerHelper.simple_handler(loggers, logger_level, frmt=frmt, formatter=None)
        logger.info(u'START')
        self.consumer.start_subscriber()
        
def test_suite():
    tests = [
        u'test_start_consumer'
    ]
    return unittest.TestSuite(map(SimpleEventConsumerCase, tests))

if __name__ == u'__main__':
    runtest(test_suite())  
          