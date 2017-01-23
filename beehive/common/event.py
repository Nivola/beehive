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