'''
Created on Feb 2, 2017

@author: darkbk
'''
import sys
import os
import logging

sys.path.append(os.path.expanduser(u'~/workspace/git/beecell'))
sys.path.append(os.path.expanduser(u'~/workspace/git/beedrones'))
sys.path.append(os.path.expanduser(u'~/workspace/git/beehive'))

from beehive.common.event import SimpleEventConsumer
from beecell.logger.helper import LoggerHelper

loggers = [logging.getLogger(u'beehive')]
LoggerHelper.simple_handler(loggers, logging.DEBUG)

event_redis_uri = u'redis://10.102.184.51:6379/0'
event_redis_channel = u'beehive.event.sub'
SimpleEventConsumer(event_redis_uri, event_redis_channel).start_subscriber()