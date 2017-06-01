'''
Created on Jan 27, 2017

@author: darkbk
'''
from logging import getLogger
import gevent
from kombu.pools import producers
from kombu import Connection, exceptions
from kombu import Exchange, Queue
from beehive.module.catalog.common import CatalogEndpoint
from beecell.db.manager import RedisManager

    
class CatalogProducer(object):
    def __init__(self):
        """Abstract node producer.
        """
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)
    
    def _send(self, node_type, data, source, dest):
        raise NotImplementedError()
    
    def send(self, name, desc, service, catalog, uri):
        """Send new endpoint.
        
        :param name: endpoint name
        :param service: service service
        :param desc: endpoint description
        :param catalog: catalog id
        :param uri: endpoint uri
        """
        g = gevent.spawn(self._send, name, desc, service, catalog, uri)
        return g

    def send_sync(self, name, desc, service, catalog, uri):
        """Send new endpoint.
        
        :param name: endpoint name
        :param service: service service
        :param desc: endpoint description
        :param catalog: catalog id
        :param uri: endpoint uri
        """
        self._send(name, desc, service, catalog, uri)
        
class CatalogProducerRedis(CatalogProducer):
    def __init__(self, redis_uri, redis_channel):
        """Redis node producer
        
        :param redis_uri: redis uri
        :param redis_channel: redis channel
        """
        CatalogProducer.__init__(self)
        
        self.redis_uri = redis_uri
        self.redis_channel = redis_channel
        
        self.conn = Connection(redis_uri)
        self.exchange = Exchange(self.redis_channel, type=u'direct',
                                 delivery_mode=1)
        self.routing_key = u'%s.key' % self.redis_channel
        
        self.queue = Queue(self.redis_channel, exchange=self.exchange)
        self.queue.declare(channel=self.conn.channel())
        server = RedisManager(redis_uri)
        server.delete(self.redis_channel)
    
    def _send(self, name, desc, service, catalog, uri):
        try:
            # generate endpoint
            endpoint = CatalogEndpoint(name, desc, service, catalog, uri) 
            with producers[self.conn].acquire() as producer:
                msg = endpoint.dict()
                producer.publish(msg,
                                 serializer=u'json',
                                 compression=u'bzip2',
                                 exchange=self.exchange,
                                 declare=[self.exchange],
                                 routing_key=self.routing_key,
                                 expiration=60,
                                 delivery_mode=1)
                self.logger.debug(u'Send catalog endpoint : %s' % msg)
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error(u'Endpoint can not be send: %s' % ex)
        except Exception as ex:
            self.logger.error(u'Endpoint can not be send: %s' % ex)
            