'''
Created on Feb 2, 2017

@author: darkbk
'''
import logging
from beehive.common.event import SimpleEventConsumer
from beecell.logger.helper import LoggerHelper

loggers = [logging.getLogger(u'beehive')]
LoggerHelper.simple_handler(loggers, logging.DEBUG)

event_redis_uri = u'redis://10.102.184.51:6379/0'
event_redis_channel = u'beehive.event'
SimpleEventConsumer.start_subscriber(event_redis_uri, event_redis_channel)