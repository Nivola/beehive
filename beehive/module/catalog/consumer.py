'''
Created on Jan 27, 2017

@author: darkbk
'''
from beecell.simple import id_gen
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue
from kombu import Connection
from logging import getLogger, DEBUG
from beehive.module.catalog.model import CatalogDbManager
from beehive.common.data import operation
from beehive.module.catalog.controller import CatalogController, Catalog, CatalogEndpoint
from beecell.db import TransactionError
from beehive.common.apimanager import ApiManager
from beehive.module.catalog.model import Catalog as ModelCatalog

class CatalogConsumerError(Exception): pass

class CatalogConsumer(ConsumerMixin):
    def __init__(self, connection, api_manager):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)
        
        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        self.manager = CatalogDbManager()
 
    def store_endpoint(self, endpoint, message):
        """Store node in db.
        
        :param node json: node to store
        :raise CatalogConsumerError:
        """
        session = None
        try:
            # get db session
            operation.session = self.db_manager.get_session()
            
            name = endpoint[u'name']
            service = endpoint[u'service']
            desc = endpoint[u'desc']
            catalog = endpoint[u'catalog']
            uri = endpoint[u'uri']
            
            catalog_obj = self.manager.get_entity(ModelCatalog, catalog)        
            
            try:
                objid = u'%s//%s' % (catalog_obj.objid, id_gen())
                res = self.manager.add_endpoint(objid, name, service, desc, 
                                            catalog_obj.id, uri, active=True)
                controller = CatalogController(None)
                obj = CatalogEndpoint(controller, Catalog(controller), 
                                      oid=res.id, objid=res.objid, 
                                      name=res.name, desc=res.desc, 
                                      active=res.active, model=res)
                # create object and permission
                obj.register_object(objid.split(u'//'), desc=endpoint[u'desc'])
            except (TransactionError) as ex:
                if ex.code == 409:
                    self.manager.update_endpoint(oid=catalog_obj.id, 
                                                 name=name, 
                                                 desc=desc, 
                                                 service=service, 
                                                 catalog=catalog_obj.id, 
                                                 uri=uri)
            
            self.logger.debug(u'Store endpoint : %s' % endpoint)
        except (TransactionError, Exception) as ex:
            self.logger.error(u'Error storing node : %s' % ex, exc_info=1)
            #raise CatalogConsumerError(ex)
        finally:
            if session is not None:
                self.db_manager.release_session(operation.session)
                
        message.ack()

class CatalogConsumerRedis(CatalogConsumer):
    def __init__(self, connection, api_manager):
        """Catalog consumer that create a zmq forwarder and a zmq subscriber.
        
        :param host: hostname to use when open zmq socket
        :param port: listen port of the zmq forwarder. Sobscriber connect to 
                     forwarder backend port = port+1
        :raise CatalogConsumerError:
        """
        super(CatalogConsumerRedis, self).__init__(connection, api_manager)

        # redis
        self.redis_uri = self.api_manager.redis_catalog_uri
        self.redis_channel = self.api_manager.redis_catalog_channel
        
        # kombu channel
        self.exchange = Exchange(self.redis_channel, type=u'direct',
                                 delivery_mode=1)
        self.queue_name = u'%s.queue' % self.redis_channel
        self.routing_key = u'%s.key' % self.redis_channel
        self.queue = Queue(self.queue_name, self.exchange,
                           routing_key=self.routing_key)

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=[u'pickle', u'json'],
                         callbacks=[self.store_endpoint],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        self.logger.error(exc)

def start_catalog_consumer(params, log_path=None):
    """Start catalog consumer
    """
    # setup kombu logger
    #setup_logging(loglevel=u'DEBUG', loggers=[u''])
    
    # internal logger
    logger = getLogger(u'beehive')   
    
    logger_level = DEBUG
    if log_path is None:
        log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                        params[u'api_env'])
    logname = u'%s/%s.catalog.consumer' % (log_path, params[u'api_id'])
    logger_file = u'%s.log' % logname
    loggers = [getLogger(), logger]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, logger_file)

    # performance logging
    loggers = [getLogger(u'beecell.perf')]
    logger_file = u'%s/%s.watch' % (log_path, params[u'api_id'])
    LoggerHelper.rotatingfile_handler(loggers, DEBUG, logger_file, 
                                      frmt=u'%(asctime)s - %(message)s')

    # setup api manager
    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    
    def terminate(*args):
        worker.should_stop = True 
    
    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)    
    
    with Connection(api_manager.redis_catalog_uri) as conn:
        try:
            worker = CatalogConsumerRedis(conn, api_manager)
            logger.info(u'Start catalog consumer')
            worker.run()
        except KeyboardInterrupt:
            logger.info(u'Stop catalog consumer')
            
    logger.info(u'Stop catalog consumer')