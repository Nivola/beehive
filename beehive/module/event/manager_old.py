'''
Created on Mar 2, 2015

@author: darkbk

https://learning-0mq-with-pyzmq.readthedocs.org/en/latest/
http://zeromq.github.io/pyzmq/
'''
from datetime import datetime
import ujson as json
import logging
import zmq.green as zmq
import gevent
from beecell.simple import id_gen
from gibboncloudapi.module.event.model import EventDbManager
from gibboncloudapi.module.base import ApiManager
from gibboncloudapi.util.data import operation
from gibboncloudapi.util.data import TransactionError, QueryError
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT

class EventConsumerError(Exception): pass

class EventConsumer(object):
    def __init__(self, api_manager):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        # process helper instance
        #self.helper = None
        # process event producer      
        #self.producer = self.api_manager.process_event_producer
        self.manager = EventDbManager()
 
 
    '''
    def create_pool_engine(self, dbconf):
        """Create mysql pool engine."""
        try:
            db_uri = dbconf[0]
            connect_timeout = dbconf[1]
            pool_size = dbconf[2]
            max_overflow = dbconf[3]
            pool_recycle = dbconf[4]
            self.db_manager = MysqlManager('db_manager02', db_uri, 
                                           connect_timeout=connect_timeout)
            self.db_manager.create_pool_engine(pool_size=pool_size, 
                                               max_overflow=max_overflow, 
                                               pool_recycle=pool_recycle)
        except MysqlManagerError as ex:
            self.logger.error(ex)
            raise EventConsumerError(ex)
    '''
    '''
    def get_identity(self, uid):
        """Get identity
        :return: {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 
                  'seckey':...}
        :rtype: dict
        """
        identity = self.redis_manager.get(self.prefix + uid)
        if identity is not None:
            data = pickle.loads(identity)
            self.logger.debug('Get identity %s from redis: %s' % (uid, data))
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise EventConsumerError("Identity %s doen't exist or is expired" % uid, code=1014)
     '''
 
    def store_event(self, event):
        """Store event in db.
        
        :param event json: event to store
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()
            #token = event['source']
            #identity = self.get_identity(token)
            #print identity
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
            
            self.logger.debug('Store event : %s' % event[u'id'])
            #gevent.sleep(0.001)  # be nice to the system :) 0.001
        except (TransactionError, Exception) as ex:
            self.logger.error("Error storing event : %s" % ex, exc_info=True)
            raise EventConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
 
    def create_receiver(self):
        """Create event receiver instance.
        
        Extend this class to create a specific receiver.
        
        :raise EventConsumerError:
        """
        raise NotImplementedError()
        # create db connection pool
        #dbconf = (self._database_uri, 5, 10, 10, 3600)
        #self.create_pool_engine(dbconf)
    
    def start(self):
        self.logger.info('Bringing up event collector: %s' % self.id)
 
    def stop(self):
        self.logger.info('Bringing down event collector: %s' % self.id)
        self._continue = False

class EventConsumerRedis(EventConsumer):
    def __init__(self, api_manager):
        """Event consumer that create a zmq forwarder and a zmq subscriber.
        
        :param host: hostname to use when open zmq socket
        :param port: listen port of the zmq forwarder. Sobscriber connect to 
                     forwarder backend port = port+1
        :raise EventConsumerError:
        """
        super(EventConsumerRedis, self).__init__(api_manager)
        # redis
        self.redis_channel = self.api_manager.redis_event_channel
        self.redis_manager = self.api_manager.redis_event_manager

    def create_receiver(self):
        """Create event receiver instance.
        
        :raise EventConsumerError:
        """
        # connect to redis pubsub
        try:
            channel = self.redis_manager.pubsub(ignore_subscribe_messages=True)
            channel.subscribe(self.redis_channel)            
            self.logger.debug('Configure redis pub sub channel: %s' % self.redis_channel)            
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise EventConsumerError(ex)

        # start redis channel loop
        self._continue = True
        self.logger.info("Start redis subscriber")
        while self._continue is True:
            try:
                msg = channel.get_message()
                if msg and msg['type'] == 'message':
                    event = msg['data']
                    event = json.loads(event)
                    self.logger.debug("Received event: %s" % event)
                    
                    # store event
                    gevent.spawn(self.store_event, event)
                gevent.sleep(0.01)
            except Exception as ex:
            #except gevent.Greenlet.GreenletExit:
                pass
            
        channel.close()
        self.logger.info("Stop redis subscriber")
            
    
    def start(self):
        super(EventConsumerRedis, self).start()
        
        g2 = gevent.spawn(self.create_receiver)        
        g2.join()
 
    def stop(self):
        super(EventConsumerRedis, self).stop()

class EventConsumerZmq(EventConsumer):
    def __init__(self, api_manager):
        """Event consumer that create a zmq forwarder and a zmq subscriber.
        
        :param host: hostname to use when open zmq socket
        :param port: listen port of the zmq forwarder. Sobscriber connect to 
                     forwarder backend port = port+1
        :raise EventConsumerError:
        """
        super(EventConsumerZmq, self).__init__(api_manager)
        self._host = host
        self._port = port
        self._server_port = port+1
 
    def create_forwarder(self):
        try:
            self.logger.info("Bringing up zmq device")
            context = zmq.Context(1)
            # Socket facing clients
            frontend = context.socket(zmq.SUB)
            frontend.setsockopt(zmq.SUBSCRIBE, '')
            frontend.bind("tcp://%s:%s" % (self._host, self._port))
            self.logger.info("Bind frontend to : %s:%s" % (self._host, self._port))
            # Socket facing services
            backend = context.socket(zmq.PUB)
            backend.bind("tcp://%s:%s" % (self._host, self._server_port))
            self.logger.info("Bind backend to : %s:%s" % (self._host, self._server_port))
            # create forwarder
            zmq.device(zmq.FORWARDER, frontend, backend)
        except Exception as ex:
            self.logger.error("Bringing down zmq device : %s" % ex, exc_info=True)
            raise EventConsumerError(ex)
        finally:
            frontend.close()
            backend.close()
            context.term()

    def create_receiver(self):
        """Create event receiver instance.
        
        :raise EventConsumerError:
        """        
        super(EventConsumerZmq, self).create_receiver()

        # start receiver
        try:
            self.context = zmq.Context()
            self.receiver = self.context.socket(zmq.SUB)
            self.receiver.setsockopt(zmq.SUBSCRIBE, '')
            self.receiver.connect('tcp://%s:%s' % (self._host, self._server_port))
            
            self._continue = True
            self.logger.info("Start receiver over %s:%s" % (self._host, 
                                                            self._server_port))
        except Exception as ex:
            self.logger.error("Stop receiver over %s:%s : %s" % (self._host, 
                                                                 self._server_port, 
                                                                 ex))
            raise EventConsumerError(ex)
        
        while self._continue is True:
            try:
                #  Wait for next request from client
                #event = self.receiver.recv_json()
                event = self.receiver.recv()
                event = json.loads(event)
                self.logger.debug("Received event: %s" % event)
                
                # store event
                gevent.spawn(self.store_event, event)
                gevent.sleep(0.01)
                # create response
                #response = {'server':self.id, 'req':event['id']}
                #self.receiver.send_json(response)
            except EventConsumerError as ex:
                break
            except Exception as ex:
                self.logger.error(ex, exc_info=True)
    
    def start(self):
        super(EventConsumerZmq, self).start()
        
        g1 = gevent.spawn(self.create_forwarder)
        g2 = gevent.spawn(self.create_receiver)        
        g2.join()
 
    def stop(self):
        super(EventConsumerZmq, self).stop()
        
        self.receiver.close()
        self.context.term()
        #self.pool.join()


def start_event_consumer(params):
    """start event consumer
    """
    logger_level = logging.DEBUG
    log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])
    logname = u'%s/%s.event.consumer' % (log_path, params[u'api_id'])
    logger_file = u'%s.log' % logname
    logger_names = [u'gibboncloudapi.module.event.manager']    
    
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        LoggerHelper.rotatingfile_handler([logger], logger_level, logger_file)
        #LoggerHelper.setup_simple_handler(logger, logger_level)

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    worker = EventConsumerRedis(api_manager)
    
    def terminate(*args):
        worker.stop()
    
    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)
        
    worker.start()