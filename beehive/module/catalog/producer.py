# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from logging import getLogger
import gevent
from kombu.pools import producers
from kombu import Connection, exceptions
from kombu import Exchange, Queue
from beehive.module.catalog.common import CatalogEndpoint
from beecell.db.manager import RedisManager
from re import match


logger = getLogger(__name__)


class CatalogProducer(object):
    """Catalog producer"""

    def __init__(self):
        self.logger = getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

    # vecchia firma implementata diversamente def _send(self, node_type, data, source, dest):
    def _send(self, name, desc, service, catalog, uri):
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
        self.exchange = Exchange(self.redis_channel, type="direct", delivery_mode=1)
        self.routing_key = "%s.key" % self.redis_channel

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
                producer.publish(
                    msg,
                    serializer="json",
                    compression="bzip2",
                    exchange=self.exchange,
                    declare=[self.exchange],
                    routing_key=self.routing_key,
                    expiration=60,
                    delivery_mode=1,
                )
                self.logger.debug("Send catalog endpoint : %s" % msg)
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error("Endpoint can not be send: %s" % ex)
        except Exception as ex:
            self.logger.error("Endpoint can not be send: %s" % ex, exc_info=True)


class CatalogProducerKombu(CatalogProducer):
    def __init__(self, broker_uri, broker_exchange):
        """Kombu catalog producer

        :param broker_uri: broker uri
        :param broker_exchange: kombu channel
        """
        CatalogProducer.__init__(self)

        self.broker_uri = broker_uri
        self.broker_exchange = broker_exchange

        self.conn = Connection(broker_uri)
        self.exchange = Exchange(self.broker_exchange, type="direct")
        self.queue_name = "%s.queue" % self.broker_exchange
        self.routing_key = "%s.key" % self.broker_exchange
        self.queue = Queue(self.queue_name, self.exchange, routing_key=self.routing_key)

    def _send(self, name, desc, service, catalog, uri):
        try:
            # generate endpoint
            endpoint = CatalogEndpoint(name, desc, service, catalog, uri)
            with producers[self.conn].acquire() as producer:
                msg = endpoint.dict()
                producer.publish(
                    msg,
                    serializer="json",
                    compression="bzip2",
                    exchange=self.exchange,
                    declare=[self.exchange],
                    routing_key=self.routing_key,
                    # expiration=60,
                    # delivery_mode=1
                )
                self.logger.debug("Send catalog endpoint : %s" % msg)
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error("Endpoint can not be send: %s" % ex)
        except Exception as ex:
            self.logger.error("Endpoint can not be send: %s" % ex, exc_info=True)
