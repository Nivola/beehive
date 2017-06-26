'''
Created on jan 25, 2017

@author: darkbk
'''
import logging
from datetime import datetime
from copy import deepcopy
from beecell.simple import id_gen
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue
from kombu.pools import producers
from kombu import Connection, exceptions
from beehive.module.event.model import EventDbManager
from beehive.common.event import EventProducerRedis, Event
from beehive.common.data import operation
from beecell.db import TransactionError
from beehive.common.apimanager import ApiManager, ApiObject

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
        self.redis_exchange = self.api_manager.redis_event_exchange
        
        self.exchange = Exchange(self.redis_exchange, type=u'direct', 
                                 delivery_mode=1, durable=False)
        self.queue_name = u'%s.queue' % self.redis_exchange   
        self.routing_key = u'%s.key' % self.redis_exchange
        self.queue = Queue(self.queue_name, self.exchange,
                           routing_key=self.routing_key,
                           delivery_mode=1, durable=False)
        
        # subscriber
        #self.exchange_sub = Exchange(self.redis_exchange+u'.sub', type=u'topic',
        #                             delivery_mode=1)
        #self.queue_name_sub = u'%s.queue.sub' % self.redis_exchange   
        #self.routing_key_sub = u'%s.sub.key' % self.redis_exchange
        #self.queue_sub = Queue(self.queue_name_sub, self.exchange_sub,
        #                       routing_key=self.routing_key_sub)
        
        self.event_producer = EventProducerRedis(self.redis_uri,
                                                 self.redis_exchange+u'.sub',
                                                 framework=u'simple')
        self.conn = Connection(self.redis_uri)
 
    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=[u'pickle', u'json'],
                         callbacks=[self.callback],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        self.logger.error(exc)
 
    def callback(self, event, message):
        self.log_event(event, message)
        self.store_event(event, message)
        self.publish_event_to_subscriber(event, message)       
 
    def log_event(self, event, message):
        """Log received event
        
        :param event json: event to store
        :raise EventConsumerError:
        """
        message.ack()        
        self.logger.info(u'Consume event : %s' % event)
 
    def store_event(self, event, message):
        """Store event in db.
        
        :param event json: event to store
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()
            
            # clone event
            sevent = deepcopy(event)

            etype = sevent[u'type']
            
            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS' 
            if etype == ApiObject.ASYNC_OPERATION:
                status = sevent[u'data'][u'response'][0]
                if status not in [u'STARTED', u'FAILURE', u'SUCCESS']:
                    return None
            
            creation = datetime.fromtimestamp(sevent[u'creation'])
            dest = sevent[u'dest']
            objid = dest.pop(u'objid')
            objdef = dest.pop(u'objdef')
            module = dest.pop(u'objtype')
            self.manager.add(sevent[u'id'], etype, 
                             objid, objdef, module,
                             creation, sevent[u'data'],
                             event[u'source'], dest)
            
            self.logger.debug(u'Store event : %s' % sevent)
        except (TransactionError, Exception) as ex:
            self.logger.error(u'Error storing event : %s' % ex, exc_info=True)
            raise EventConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
    
    def publish_event_to_subscriber(self, event, message):
        """Publish event to subscriber queue.
        
        :param event json: event to store
        :raise EventConsumerError:        
        """
        self.__publish_event_simple(event[u'id'], event[u'type'], 
                                    event[u'data'], event[u'source'], 
                                    event[u'dest'])
    
    def __publish_event_simple(self, event_id, event_type, data, source, dest):
        try:
            self.event_producer.send(event_type, data, source, dest)
            self.logger.debug(u'Publish event %s to channel %s' % 
                              (event_id, self.redis_exchange))
        except Exception as ex:
            self.logger.error(u'Event %s can not be published: %s' % 
                              (event_id, ex), exc_info=1)      
    
    def __publish_event_kombu(self, event_id, event_type, data, source, dest):
        try:
            event = Event(event_type, data, source, dest)
            producer = producers[self.conn].acquire()
            producer.publish(event.dict(),
                             serializer=u'json',
                             compression=u'bzip2',
                             exchange=self.exchange_sub,
                             declare=[self.exchange_sub],
                             routing_key=self.routing_key_sub,
                             expiration=60,
                             delivery_mode=1)
            producer.release()
            self.logger.debug(u'Publish event %s to exchenge %s' % 
                              (event_id, self.exchange_sub))
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error(u'Event %s can not be published: %s' % 
                              (event_id, ex), exc_info=1)
        except Exception as ex:
            self.logger.error(u'Event %s can not be published: %s' % 
                              (event_id, ex), exc_info=1)
    
def start_event_consumer(params, log_path=None):
    """Start event consumer
    """
    # setup kombu logger
    #setup_logging(loglevel=u'DEBUG', loggers=[u''])
    
    # internal logger
    logger = logging.getLogger(u'beehive.module.event.manager')   
    
    logger_level = logging.DEBUG
    if log_path is None:
        log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                        params[u'api_env'])
    logname = u'%s/%s.event.consumer' % (log_path, params[u'api_id'])
    logger_file = u'%s.log' % logname
    #loggers = [logging.getLogger(), logger]
    loggers = [logger]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, logger_file)

    # performance logging
    loggers = [logging.getLogger(u'beecell.perf')]
    logger_file = u'%s/%s.watch' % (log_path, params[u'api_id'])
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
