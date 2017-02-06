'''
Created on May 24, 2015

@author: darkbk
'''
import ujson as json
import time
import logging
import redis
#import zmq.green as zmq
import gevent
from beecell.simple import str2uni, id_gen

from kombu.mixins import ConsumerMixin
from kombu.log import get_logger as kombu_get_logger
from kombu.utils import reprcall
from kombu import Exchange, Queue
from kombu import Connection
from kombu.utils.debug import setup_logging
from signal import *

logger = logging.getLogger(__name__)

class Event(object):
    """Event.
    
    :param event_type: event type. Stirng like user, role, cloudstack.org.grp.vm
    :param data: event data. Dict like {'opid':..,  'op':..,  'params':..,  'response':..}
    :param source: event source. Dict like {'user':.., 'ip':..}
    :param dest: event dist. Dict like {'objtype':.., 'objdef':.., 'ip':.., 'objid':..}
    """
        
    def __init__(self, event_type, data, source, dest):
        # event unique id
        self.id = id_gen()
        
        # event type like user, role, resource, property
        self.type = event_type
        
        # fire time of event 
        self.creation = time.time()
        #time.strftime("%d-%m-%y %H:%M:%S")

        # event operation data
        self.data = data
        
        # remote address that require event fire
        self.source = source
        
        # local address that fire event using runtime execution process
        # destination contains also object used in the operation
        self.dest = dest

    def __str__(self):
        creation = str2uni(self.creation.strftime("%d-%m-%y %H:%M:%S"))
        res = "<Event id=%s, type=%s, creation=%s, data='%s', source='%s',\
                      dest='%s'>" % (self.id, self.type, creation, self.data, 
                                     self.source, self.dest)
        return res

    def json(self):
        """Return json representation.
        
        Ex:
        
        .. code-block:: python
        
            {"id":.., 
             "type":.., 
             "creation":.., 
             "data":.., 
             "source":.., 
             "dest":..}        
        
        :return: json string
        """
        #creation = str2uni(self.creation.strftime("%d-%m-%y %H:%M:%S"))
        #creation = str2uni(datetime.fromtimestamp(self.creation))
        msg = {'id':self.id, 'type':self.type, 'creation':self.creation, 
               'data':self.data, 'source':self.source, 'dest':self.dest}
        return json.dumps(msg)
    
class EventProducer(object):
    def __init__(self):
        """Abstract event producer.
        """
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
    
    def _send(self, event_type, data, source, dest):
        raise NotImplementedError()
    
    def send(self, event_type, data, source, dest):
        """Send new event.
        
        :param event_type: type of event to send
        :param str data: data to send
        :param source: event source
        :param dest: event destination
        """
        gevent.spawn(self._send, event_type, data, source, dest)
        
class EventProducerRedis(EventProducer):
    def __init__(self, redis_manager, redis_channel):
        """Redis event producer
        
        :param redis_manager: redis manager
        :param redis_channel: redis channel
        """
        EventProducer.__init__(self)
        
        self.redis_manager = redis_manager
        self.redis_channel = redis_channel
    
    def _send(self, event_type, data, source, dest):
        try:
            #self.logger.debug("Get event params: %s, %s, %s, %s" % 
            #                  (event_type, data, source, dest))
            # generate event
            event = Event(event_type, data, source, dest)        
            # send message
            message = event.json()
            # publish message to redis
            self.redis_manager.publish(self.redis_channel, message)
            self.logger.debug("Send event %s : %s" % (event.id, message))
        except redis.PubSubError as ex:
            self.logger.error("Event can not be send: %s" % ex)
        except Exception as ex:
            self.logger.error("Event can not be encoded: %s" % ex)

class EventProducerZmq(EventProducer):
    def __init__(self, host, port):
        """Zmq event producer
        
        :param host: Zmq consumer host
        :param port: Zmq consumer port
        """
        EventProducer.__init__(self)
        
        self._host = host
        self._port = port
            
    def _send(self, event_type, data, source, dest):
        """Send event
        
        :param event_type: event type. Stirng like user, role, cloudstack.org.grp.vm
        :param data: event data. Dict like {'opid':.., 'op':.., 'params':.., 
                                            'response':..}
        :param source: event source. Dict like {'user':.., 'ip':..}
        :param dest: event dist. Dict like {'user':.., 'ip':..}
        """
        zmq_socket = None
        context = None
        try:
            # create context and open socket
            context = zmq.Context()
            zmq_socket = context.socket(zmq.PUB)
            zmq_socket.connect("tcp://%s:%s" % (self._host, self._port))
            self.logger.debug("Connect to %s:%s" % (self._host, self._port))
                        
            # generate event
            event = Event(event_type, data, source, dest)        
            # send message
            message = event.json()
            gevent.sleep(0.01)
            zmq_socket.send(message)
            self.logger.debug("Send event %s : %s" % (event.id, message))
            #resp = zmq_socket.recv_json()
            #self.logger.debug("Event %s received by %s" % (resp['req'], resp['server']))
        except zmq.error.ZMQError as ex:
            self.logger.error("Event can not be send: %s" % ex)
        finally:
            # close socket and terminate context         
            if zmq_socket is not None:
                zmq_socket.close()
            if context is not None:
                context.term()
                
class SimpleEventConsumer(ConsumerMixin):
    def __init__(self, connection, redis_channel):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        self.connection = connection

        # redis
        self.redis_channel = redis_channel
        
        # kombu channel
        self.exchange = Exchange(self.redis_channel+u'.sub', type=u'topic',
                                 durable=False)
        self.queue_name = u'%s.queue.%s' % (self.redis_channel, id_gen())   
        self.routing_key = u'%s.sub.key' % self.redis_channel
        self.queue = Queue(self.queue_name, self.exchange,
                           routing_key=self.routing_key)        

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=[u'pickle', u'json'],
                         callbacks=[self.manage_event],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        self.logger.error(exc)
        
    def manage_event(self, data, message):
        """Manage event
        
        :param data json: event received
        :param message:
        :raise MonitorConsumerError:
        """
        self.logger.debug(u'Get event %s' % data[u'id'])
        message.ack()
                
    @staticmethod
    def start_subscriber(event_redis_uri, event_redis_channel):
        """
        """    
        def terminate(*args):
            worker.should_stop = True 
        
        for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
            signal(sig, terminate)    
        
        with Connection(event_redis_uri) as conn:
            try:
                worker = SimpleEventConsumer(conn, event_redis_channel)
                logger.info(u'Start event consumer on redis channel %s:%s' % 
                                (event_redis_uri, event_redis_channel))
                worker.run()
            except KeyboardInterrupt:
                logger.info(u'Stop event consumer on redis channel %s:%s' % 
                                (event_redis_uri, event_redis_channel))
                
        logger.info(u'Stop event consumer on redis channel %s:%s' % 
                        (event_redis_uri, event_redis_channel))                