'''
Created on Mar 2, 2015

@author: darkbk

https://learning-0mq-with-pyzmq.readthedocs.org/en/latest/
http://zeromq.github.io/pyzmq/
'''
from datetime import datetime
import logging
from beecell.simple import id_gen
from beehive.module.event.model import EventDbManager
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation
from beehive.common.data import TransactionError, QueryError
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT

from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue

from kombu import Connection
from kombu.utils.debug import setup_logging

class EventConsumerError(Exception): pass

class EventConsumerRedis(ConsumerMixin):
    def __init__(self, connection, api_manager):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        self.manager = EventDbManager()
        
        self.redis_uri = self.api_manager.redis_event_uri
        self.redis_channel = self.api_manager.redis_event_channel
        
        self.exchange = Exchange(self.redis_channel, type=u'direct')
        self.queue_name = u'%s.queue' % self.redis_channel
        self.routing_key = u'%s.key' % self.redis_channel
        self.queue = Queue(self.queue_name, self.exchange,
                           routing_key=self.routing_key)
 
    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=[u'pickle', u'json'],
                         callbacks=[self.store_event],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        self.logger.error(exc)
 
    def store_event(self, event, message):
        """Store event in db.
        
        :param event json: event to store
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()

            creation = datetime.fromtimestamp(event[u'creation'])
            etype = event[u'type']
            
            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS' 
            if etype == u'asyncop':
                status = event[u'data'][u'response'][0]
                if status not in [u'STARTED', u'FAILURE', u'SUCCESS']:
                    return None
                
            dest = event[u'dest']
            objid = dest.pop(u'objid')
            objdef = dest.pop(u'objdef')
            module = dest.pop(u'objtype')
            self.manager.add(event[u'id'], etype, 
                             objid, objdef, module,
                             creation, event[u'data'],
                             event[u'source'], dest)
            
            self.logger.debug(u'Store event : %s' % event[u'id'])
            
            message.ack()
        except (TransactionError, Exception) as ex:
            self.logger.error(u'Error storing event : %s' % ex, exc_info=True)
            raise EventConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
    
def start_event_consumer(params, log_path=None):
    """Start event consumer
    """
    # setup kombu logger
    #setup_logging(loglevel=u'DEBUG', loggers=[u''])
    
    # internal logger
    logger = logging.getLogger(u'beehive')   
    
    logger_level = logging.DEBUG
    if log_path is None:
        log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                        params[u'api_env'])
    logname = u'%s/%s.event.consumer' % (log_path, params[u'api_id'])
    logger_file = u'%s.log' % logname
    loggers = [logging.getLogger(), logger]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, logger_file)

    # performance logging
    loggers = [logging.getLogger(u'beecell.perf')]
    logname = u'%s/%s.watch' % (log_path, params[u'api_id'])
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, logger_file, 
                                      frmt=u'%(asctime)s - %(message)s')

    # setup api manager
    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    
    def terminate(*args):
        worker.should_stop = True 
    
    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)    
    
    with Connection(api_manager.redis_event_uri) as conn:
        try:
            worker = EventConsumerRedis(conn, api_manager)
            logger.info(u'Start event consumer')
            worker.run()
        except KeyboardInterrupt:
            logger.info(u'Stop event consumer')
            
    logger.info(u'Stop event consumer')
