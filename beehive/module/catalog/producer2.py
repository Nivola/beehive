'''
Created on May 20, 2016

@author: darkbk
'''
import ujson as json
import time
import logging
import redis
from beecell.simple import str2uni, id_gen
import gevent
from .common import CatalogEndpoint
    
class CatalogProducer(object):
    def __init__(self):
        """Abstract node producer.
        """
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
    
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
        #self._send(name, desc, nodetype, connection)
        
class CatalogProducerRedis(CatalogProducer):
    def __init__(self, redis_manager, redis_channel):
        """Redis node producer
        
        :param redis_manager: redis manager
        :param redis_channel: redis channel
        """
        CatalogProducer.__init__(self)
        
        self.redis_manager = redis_manager
        self.redis_channel = redis_channel
    
    def _send(self, name, desc, service, catalog, uri):
        try:
            # generate node
            node = CatalogEndpoint(name, desc, service, catalog, uri)        
            # send message
            message = node.json()
            # publish message to redis
            self.redis_manager.publish(self.redis_channel, message)
            self.logger.debug("Send endpoint %s : %s" % (node.id, message))
            return message
        except redis.PubSubError as ex:
            self.logger.error("Endpoint can not be send: %s" % ex)
        except Exception as ex:
            self.logger.error("Endpoint can not be encoded: %s" % ex)
            