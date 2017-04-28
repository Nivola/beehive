'''
Created on May 20, 2016

@author: darkbk
'''
#import time
import ujson as json
import logging
#import pickle
import gevent
#import redis
from beecell.simple import id_gen, str2uni
from gibboncloudapi.util.data import operation
from gibboncloudapi.util.data import TransactionError, QueryError
from .model import CatalogDbManager
from datetime import datetime
from beecell.logger.helper import LoggerHelper
from gibboncloudapi.module.base import ApiManager
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from gibboncloudapi.module.catalog.controller import CatalogEndpoint, Catalog,\
    CatalogController

class CatalogConsumerError(Exception): pass

class CatalogConsumer(object):
    def __init__(self, api_manager):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        # process helper instance
        #self.helper = None
        # process endpoint producer      
        #self.producer = self.api_manager.process_endpoint_producer
        self.manager = CatalogDbManager()
 
    def store_endpoint(self, endpoint):
        """Store endpoint in db.
        
        :param endpoint json: endpoint to store
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
            
            catalog_obj = self.manager.get(oid=catalog)[0]
            
            try:
                objid = u'%s//%s' % (catalog_obj.objid, id_gen())
                res = self.manager.add_endpoint(objid, name, service, desc, 
                                                catalog, uri, enabled=True)
                obj = CatalogEndpoint(CatalogController(None), Catalog(None), 
                                      oid=res.id, objid=res.objid, 
                                      name=res.name, desc=res.desc, 
                                      active=res.enabled, model=res)
                # create object and permission
                obj.register_object(objid.split(u'//'), desc=endpoint[u'desc'])
            except (TransactionError) as ex:
                if ex.code == 409:
                    self.manager.update_endpoint(name=name, 
                                                 new_name=name, 
                                                 new_desc=desc, 
                                                 new_service=service, 
                                                 new_catalog=catalog, 
                                                 new_uri=uri)
            
            self.logger.debug(u'Store endpoint : %s' % endpoint)
            #gevent.sleep(0.001)  # be nice to the system :) 0.001
        except (TransactionError, Exception) as ex:
            self.logger.error(u'Error storing endpoint : %s'% ex, exc_info=1)
            raise CatalogConsumerError(ex)
        finally:
            if session is not None:
                self.db_manager.release_session(operation.session)
 
    def create_receiver(self):
        """Create endpoint receiver instance.
        
        Extend this class to create a specific receiver.
        
        :raise CatalogConsumerError:
        """
        raise NotImplementedError()
    
    def start(self):
        self.logger.info('Bringing up endpoint collector: %s' % self.id)
 
    def stop(self):
        self.logger.info('Bringing down endpoint collector: %s' % self.id)
        self._continue = False

class CatalogConsumerRedis(CatalogConsumer):
    def __init__(self, api_manager):
        """Catalog consumer that create a zmq forwarder and a zmq subscriber.
        
        :param host: hostname to use when open zmq socket
        :param port: listen port of the zmq forwarder. Sobscriber connect to 
                     forwarder backend port = port+1
        :raise CatalogConsumerError:
        """
        super(CatalogConsumerRedis, self).__init__(api_manager)
        # redis
        self.redis_channel = self.api_manager.redis_catalog_channel
        self.redis_manager = self.api_manager.redis_catalog_manager

    def create_receiver(self):
        """Create endpoint receiver instance.
        
        :raise CatalogConsumerError:
        """
        # connect to redis pubsub
        try:
            channel = self.redis_manager.pubsub(ignore_subscribe_messages=True)
            channel.subscribe(self.redis_channel)            
            self.logger.debug(u'Configure redis %s pub sub channel: %s' % 
                              (self.redis_manager, self.redis_channel))  
        except Exception as ex:
            self.logger.error(ex)
            raise CatalogConsumerError(ex)

        # start redis channel loop
        self._continue = True
        self.logger.info(u'Start redis subscriber')
        while self._continue is True:
            try:
                msg = channel.get_message()
                if msg and msg[u'type'] == u'message':
                    endpoint = msg[u'data']
                    endpoint = json.loads(endpoint)
                    self.logger.debug(u'Received endpoint: %s' % endpoint)
                    
                    # store endpoint
                    gevent.spawn(self.store_endpoint, endpoint)
                gevent.sleep(0.01)
            except Exception as ex:
            #except gevent.Greenlet.GreenletExit:
                pass
            
        channel.close()
        self.logger.info(u'Stop redis subscriber')
            
    
    def start(self):
        super(CatalogConsumerRedis, self).start()
        
        g2 = gevent.spawn(self.create_receiver)        
        g2.join()
 
    def stop(self):
        super(CatalogConsumerRedis, self).stop()


def start_catalog_consumer(params):
    logger_level = logging.DEBUG
    log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])
    logname = u'%s/%s.catalog.consumer' % (log_path, params[u'api_id'])
    logger_file = u'%s.log' % logname
    logger_names = [u'gibboncloudapi', 
                    u'beecell']
    
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        LoggerHelper.rotatingfile_handler([logger], logger_level, logger_file)
        #LoggerHelper.setup_simple_handler(logger, logger_level)

    # performance logging
    loggers = [logging.getLogger(u'beecell.perf')]
    logger_file = u'%s.watch' % logname
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, logger_file, 
                                      frmt=u'%(asctime)s - %(message)s')

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    worker = CatalogConsumerRedis(api_manager)
    
    def terminate(*args):
        worker.stop()
    
    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)
        
    worker.start()