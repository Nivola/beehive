# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import json
import time
import logging
from re import match

import redis
#import zmq.green as zmq
import gevent
from beecell.simple import str2uni, id_gen, parse_redis_uri, truncate

from kombu.mixins import ConsumerMixin
from kombu.pools import producers
from kombu import Exchange, Queue
from kombu import Connection, exceptions
from signal import *
import pprint
from beecell.db.manager import RedisManager
from six import b


class ComplexEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return json.dumps(o)
        except TypeError:
            return str(o)
        
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


def _dumps(s):
    return json.dumps(s, cls=ComplexEncoder)


"""Register a custom encoder/decoder for JSON serialization."""
from kombu import serialization
from kombu.utils import json as _json

serialization.register('json', _dumps, _json.loads, content_type='application/json', content_encoding='utf-8')


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

        # event operation data
        self.data = data
        
        # remote address that require event fire
        self.source = source
        
        # local address that fire event using runtime execution process
        # destination contains also object used in the operation
        self.dest = dest

    def __str__(self):
        creation = str2uni(self.creation.strftime('%d-%m-%y %H:%M:%S'))
        res = '<Event id=%s, type=%s, creation=%s, data=%s, source=%s, dest=%s>' % \
              (self.id, self.type, creation, self.data, self.source, self.dest)
        return res
    
    def dict(self):
        """Return dict representation.

        .. code-block:: python
        
            {'id':.., 
             'type':.., 
             'creation':.., 
             'data':.., 
             'source':.., 
             'dest':..}        
        
        :return: dict
        """
        msg = {
            'id': self.id,
            'type': self.type,
            'creation': self.creation,
            'data': self.data,
            'source': self.source,
            'dest': self.dest
        }
        return msg    
    
    def json(self):
        """Return json representation.
        
        Ex:
        
        .. code-block:: python
        
            {'id':..,
             'type':..,
             'creation':..,
             'data':..,
             'source':..,
             'dest':..}
        
        :return: json string
        """
        msg = self.dict()
        return json.dumps(msg)


class EventHandler(object):
    def __init__(self, api_manager):
        self.logger = logging.getLogger('beehive.common.event.EventHandler')
        self.api_manager = api_manager

    def callback(self, event, message):
        pass


class EventProducer(object):
    def __init__(self):
        """Abstract event producer.
        """
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
    
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
        
    def send_sync(self, event_type, data, source, dest):
        """Send sync new event.
        
        :param event_type: type of event to send
        :param str data: data to send
        :param source: event source
        :param dest: event destination      
        """
        self._send(event_type, data, source, dest)          


class EventProducerRedis(EventProducer):
    def __init__(self, redis_uri, redis_exchange, framework='komb'):
        """Redis event producer
        
        :param redis_uri: redis uri
        :param redis_exchange: redis channel
        :param framework: framework used to manage redis pub sub. Ex. kombu, simple
        """
        EventProducer.__init__(self)
        
        self.redis_uri = redis_uri
        self.redis_exchange = redis_exchange
        self.framework = framework
        
        if framework == 'simple':
            # set redis manager
            res = parse_redis_uri(redis_uri)
            self.redis_manager = redis.StrictRedis(host=res['host'], port=int(res['port']), db=int(res['db']),
                                                   password=res['pwd'])
        
        elif framework == 'komb':
            self.conn = Connection(redis_uri)
            self.exchange = Exchange(self.redis_exchange, type='direct', delivery_mode=1, durable=False)
            self.routing_key = '%s.key' % self.redis_exchange
    
            self.queue_name = '%s.temp' % self.redis_exchange 
            self.queue = Queue(self.queue_name, exchange=self.exchange)
            self.queue.declare(channel=self.conn.channel())
            server = RedisManager(redis_uri)
            server.delete(self.queue_name)
    
    def _send(self, event_type, data, source, dest):
        if self.framework == 'komb':
            return self._send_kombu(event_type, data, source, dest)
        elif self.framework == 'simple':
            return self._send_simple(event_type, data, source, dest)        
            
    def _send_kombu(self, event_type, data, source, dest):
        try:
            event = Event(event_type, data, source, dest)
            with producers[self.conn].acquire() as producer:
                msg = event.dict()
                producer.publish(msg,
                                 serializer='json',
                                 compression='bzip2',
                                 exchange=self.exchange,
                                 declare=[self.exchange],
                                 routing_key=self.routing_key,
                                 expiration=60,
                                 delivery_mode=1)
                # self.logger.debug('Send event : %s' % msg['id'])
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error('Event can not be send: %s' % str(ex))
        except Exception as ex:
            self.logger.error('Event can not be send: %s' % str(ex))
            
    def _send_simple(self, event_type, data, source, dest):
        try:
            # generate event
            event = Event(event_type, data, source, dest)        
            # send message
            message = event.json()
            # publish message to redis
            self.redis_manager.publish(self.redis_exchange, message)
            self.logger.debug('Send event %s : %s' % (event.id, truncate(message)))
        except redis.PubSubError as ex:
            self.logger.error('Event can not be send: %s' % str(ex))
        except Exception as ex:
            self.logger.error('Event can not be encoded: %s' % str(ex))


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
        
        :param event_type: event type. String like user, role, cloudstack.org.grp.vm
        :param data: event data. Dict like {'opid':.., 'op':.., 'params':.., 'response':..}
        :param source: event source. Dict like {'user':.., 'ip':..}
        :param dest: event dist. Dict like {'user':.., 'ip':..}
        """
        zmq_socket = None
        context = None
        try:
            # create context and open socket
            context = zmq.Context()
            zmq_socket = context.socket(zmq.PUB)
            zmq_socket.connect('tcp://%s:%s' % (self._host, self._port))
            self.logger.debug('Connect to %s:%s' % (self._host, self._port))
                        
            # generate event
            event = Event(event_type, data, source, dest)        
            # send message
            message = event.json()
            gevent.sleep(0.01)
            zmq_socket.send(message)
            self.logger.debug('Send event %s : %s' % (event.id, message))
        except zmq.error.ZMQError as ex:
            self.logger.error('Event can not be send: %s' % ex)
        finally:
            # close socket and terminate context         
            if zmq_socket is not None:
                zmq_socket.close()
            if context is not None:
                context.term()


class SimpleEventConsumer(object):
    def __init__(self, redis_uri, redis_exchange):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
        
        self.redis_uri = redis_uri
        self.redis_exchange = redis_exchange     
        
        # set redis manager
        host, port, db = parse_redis_uri(redis_uri)
        self.redis = redis.StrictRedis(
            host=host, port=int(port), db=int(db))
        
        self.pp = pprint.PrettyPrinter(indent=2)

    def start_subscriber(self):
        """Start subscriber
        """
        channel = self.redis.pubsub()
        channel.subscribe(self.redis_exchange)

        self.logger.info('Start event consumer on redis channel %s:%s' % (self.redis_uri, self.redis_exchange))
        while True:
            try:
                msg = channel.get_message()
                if msg and msg['type'] == 'message':
                    # get event data
                    data = json.loads(msg['data'])
                    self.logger.debug('Get message : %s' % 
                                      self.pp.pformat(data))
                    
                gevent.sleep(0.05)  # be nice to the system :) 0.05
            except (gevent.Greenlet.GreenletExit, Exception) as ex:
                self.logger.error('Error receiving message: %s', exc_info=1)                 
                    
        self.logger.info('Stop event consumer on redis channel %s:%s' % (self.redis_uri, self.redis_exchange))


class SimpleEventConsumerKombu(ConsumerMixin):
    def __init__(self, connection, redis_exchange):
        self.logger = logging.getLogger(self.__class__.__module__ + '.'+self.__class__.__name__)
        
        self.connection = connection

        # redis
        self.redis_exchange = redis_exchange
        
        # kombu channel
        self.exchange = Exchange(self.redis_exchange+'.sub', type='topic', delivery_mode=1)
        self.queue_name = '%s.queue.%s' % (self.redis_exchange, id_gen())   
        self.routing_key = '%s.sub.key' % self.redis_exchange
        self.queue = Queue(self.queue_name, self.exchange, routing_key=self.routing_key)

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=['pickle', 'json'],
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
        self.logger.debug('Get event %s' % data['id'])
        message.ack()
                
    @staticmethod
    def start_subscriber(event_redis_uri, event_redis_exchange):
        """
        """    
        def terminate(*args):
            worker.should_stop = True 
        
        for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
            signal(sig, terminate)    
        
        with Connection(event_redis_uri) as conn:
            try:
                worker = SimpleEventConsumerKombu(conn, event_redis_exchange)
                logger.info('Start event consumer on redis channel %s:%s' % (event_redis_uri, event_redis_exchange))
                worker.run()
            except KeyboardInterrupt:
                logger.info('Stop event consumer on redis channel %s:%s' % (event_redis_uri, event_redis_exchange))
                
        logger.info('Stop event consumer on redis channel %s:%s' % (event_redis_uri, event_redis_exchange))