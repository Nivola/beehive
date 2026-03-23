# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

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
                self.logger.debug2("Send catalog msg: %s" % msg)
                producer.publish(
                    msg,
                    serializer="json",
                    compression="bzip2",
                    exchange=self.exchange,
                    declare=[self.exchange],
                    routing_key=self.routing_key,
                    # expiration=60,
                    # delivery_mode=1
                    # see https://docs.celeryq.dev/projects/kombu/en/v5.3.5/userguide/producers.html
                    retry=True,
                    # parameters supported by the retry_over_time() function
                    retry_policy={
                        "interval_start": 0, # First retry immediately,
                        "interval_step": 2,  # then increase by 2s for every retry.
                        "interval_max": 30,  # but don't exceed 30s between retries.
                        "max_retries": 33,   # give up after 30 tries.
                    },
                    timeout=27,
                )
                self.logger.debug("Send catalog endpoint : %s" % msg)
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error("Endpoint can not be send - ConnectionLimitExceeded: %s" % ex, exc_info=True)
        except Exception as ex:
            self.logger.error("Endpoint can not be send: %s" % ex, exc_info=True)
        finally:
            # https://docs.celeryq.dev/projects/kombu/en/latest/reference/kombu.connection.html
            # self.conn.release()
            self.conn.close()
