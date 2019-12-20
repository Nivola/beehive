# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import logging
from datetime import datetime
from copy import deepcopy
from re import match

from beecell.simple import id_gen, obscure_data, import_class, truncate
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


class EventConsumerError(Exception):
    pass


class EventConsumerRedis(ConsumerMixin):
    """Event consumer from redis queue

    :param connection: redis connection
    :param api_manager: ApiManager instance
    :param event_handlers: list of event handlers used when event is received. An event handler is a class that extend
        EventHandler and define a callback method.
    """

    def __init__(self, connection, api_manager, event_handlers=[]):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
        
        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        self.manager = EventDbManager()

        self.event_handlers = []
        for event_handler in event_handlers:
            handler = import_class(event_handler)
            self.event_handlers.append(handler(self.api_manager))
        
        self.redis_uri = self.api_manager.redis_event_uri
        self.redis_exchange = self.api_manager.redis_event_exchange
        
        self.exchange = Exchange(self.redis_exchange, type='direct', delivery_mode=1, durable=False)
        self.queue_name = '%s.queue' % self.redis_exchange   
        self.routing_key = '%s.key' % self.redis_exchange
        self.queue = Queue(self.queue_name, self.exchange, routing_key=self.routing_key, delivery_mode=1, durable=False)
        self.event_producer = EventProducerRedis(self.redis_uri, self.redis_exchange+'.sub', framework='simple')
        self.conn = Connection(self.redis_uri)
 
    def get_consumers(self, Consumer, channel):
        """Get consumer

        :param Consumer: kombu consumer
        :param channel: kombu channel
        :return:
        """
        return [Consumer(queues=self.queue, accept=['pickle', 'json'], callbacks=[self.callback],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        """Decode error

        :param message: message received
        :param exc: exception raised
        :return:
        """
        self.logger.error(exc)

    def callback(self, event, message):
        """Consume event

        :param event: event received
        :param message: message received
        :return:
        """
        event['data'] = obscure_data(event['data'])
        self.log_event(event, message)
        self.store_event(event, message)
        self.publish_event_to_subscriber(event, message)

        # run additional event handler
        for event_handler in self.event_handlers:
            event_handler.callback(event, message)
 
    def log_event(self, event, message):
        """Log received event
        
        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        message.ack()        
        self.logger.info('Consume event : %s' % truncate(event))
 
    def store_event(self, event, message):
        """Store event in db.
        
        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()
            
            # clone event
            sevent = deepcopy(event)

            etype = sevent['type']
            
            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS' 
            if etype == ApiObject.ASYNC_OPERATION:
                status = sevent['data']['response'][0]
                if status not in ['STARTED', 'FAILURE', 'SUCCESS']:
                    return None
            
            creation = datetime.fromtimestamp(sevent['creation'])
            dest = sevent['dest']
            objid = dest.pop('objid')
            objdef = dest.pop('objdef')
            module = dest.pop('objtype')
            self.manager.add(sevent['id'], etype, objid, objdef, module, creation, sevent['data'], event['source'],
                             dest)
            
            self.logger.debug('Store event : %s' % truncate(sevent))
        except (TransactionError, Exception) as ex:
            self.logger.error('Error storing event : %s' % ex, exc_info=True)
            raise EventConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
    
    def publish_event_to_subscriber(self, event, message):
        """Publish event to subscriber queue.
        
        :param event: event received
        :param message: message received
        :raise EventConsumerError:        
        """
        self.__publish_event_simple(event['id'], event['type'], event['data'], event['source'], event['dest'])
    
    def __publish_event_simple(self, event_id, event_type, data, source, dest):
        try:
            self.event_producer.send(event_type, data, source, dest)
            self.logger.debug('Publish event %s to channel %s' % (event_id, self.redis_exchange))
        except Exception as ex:
            self.logger.error('Event %s can not be published: %s' % (event_id, ex), exc_info=1)
    
    def __publish_event_kombu(self, event_id, event_type, data, source, dest):
        try:
            event = Event(event_type, data, source, dest)
            producer = producers[self.conn].acquire()
            producer.publish(event.dict(),
                             serializer='json',
                             compression='bzip2',
                             exchange=self.exchange_sub,
                             declare=[self.exchange_sub],
                             routing_key=self.routing_key_sub,
                             expiration=60,
                             delivery_mode=1)
            producer.release()
            self.logger.debug('Publish event %s to exchange %s' % (event_id, self.exchange_sub))
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error('Event %s can not be published: %s' % (event_id, ex), exc_info=1)
        except Exception as ex:
            self.logger.error('Event %s can not be published: %s' % (event_id, ex), exc_info=1)


def start_event_consumer(params):
    """Start event consumer

    :param params: configuration params
    """
    # internal logger
    logger = logging.getLogger('beehive.module.event.manager')

    logger_level = int(params.get('api_logging_level', logging.DEBUG))

    name = params['api_id'].decode('utf-8') + '.event.consumer'
    log_path = params.get('api_log', None)

    if log_path is None:
        log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])
    else:
        log_path = log_path.decode('utf-8')

    file_name = log_path + name + '.log'
    loggers = [logger,
               logging.getLogger('beehive.common.event'),
               logging.getLogger('beehive.module.event.model')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, file_name)

    # get event handlers
    event_handlers = params.pop('event_handler', [])

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
            worker = EventConsumerRedis(conn, api_manager, event_handlers=event_handlers)
            logger.info('Start event consumer')
            logger.debug('Event handlers: %s' % event_handlers)
            logger.debug('Active worker: %s' % worker)
            logger.debug('Use redis connection: %s' % conn)
            worker.run()
        except KeyboardInterrupt:
            logger.info('Stop event consumer')

    logger.info('Stop event consumer')
