# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
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
from beehive.module.catalog.controller import (
    CatalogController,
    Catalog,
    CatalogEndpoint,
)
from beecell.db import TransactionError, QueryError
from beehive.common.apimanager import ApiManager
from beehive.module.catalog.model import (
    Catalog as ModelCatalog,
    CatalogEndpoint as ModelEndpoint,
)
import os


class CatalogConsumerError(Exception):
    pass


class CatalogConsumer(ConsumerMixin):
    """Catalog consumer

    :param connection: consumer connection
    :param api_manager: ApiManager instance
    """

    def __init__(self, connection, api_manager):
        self.logger = getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()
        self.manager = CatalogDbManager()

    def store_endpoint(self, endpoint, message):
        """Store node in db.

        :param endpoint: endpoint
        :param message: message
        :raise CatalogConsumerError:
        """
        session = None
        try:
            # get db session
            operation.session = self.db_manager.get_session()
            self.logger.warning(endpoint)
            name = endpoint["name"]
            service = endpoint["service"]
            desc = endpoint["desc"]
            catalog = endpoint["catalog"]
            uri = endpoint["uri"]
            catalog_obj = self.manager.get_entity(ModelCatalog, catalog)

            if self.manager.exist_entity(ModelEndpoint, name) is True:
                endpoint = self.manager.get_entity(ModelEndpoint, name)
                self.manager.update_endpoint(
                    oid=endpoint.id,
                    name=name,
                    desc=desc,
                    service=service,
                    catalog_id=catalog_obj.id,
                    uri=uri,
                )
                self.logger.debug("Update endpoint : %s" % endpoint)
            else:
                objid = "%s//%s" % (catalog_obj.objid, id_gen())
                res = self.manager.add_endpoint(objid, name, service, desc, catalog_obj.id, uri, active=True)
                controller = CatalogController(None)
                # create object and permission
                CatalogEndpoint(controller, oid=res.id).register_object(objid.split("//"), desc=endpoint["desc"])
                self.logger.debug("Create endpoint : %s" % endpoint)
        except (TransactionError, Exception) as ex:
            self.logger.error("Error storing endpoint: %s" % ex, exc_info=True)
        finally:
            if session is not None:
                self.db_manager.release_session(operation.session)

        message.ack()


class CatalogConsumerKombu(CatalogConsumer):
    def __init__(self, connection, api_manager):
        """Catalog consumer based on kombu queue

        :param connection: consumer connection
        :param api_manager: ApiManager instance
        :raise CatalogConsumerError:
        """
        # super(CatalogConsumerRedis, self).__init__(connection, api_manager)
        super(CatalogConsumerKombu, self).__init__(connection, api_manager)

        self.broker_uri = self.api_manager.broker_catalog_uri
        self.broker_exchange = self.api_manager.broker_catalog_exchange

        # redis
        # self.redis_uri = self.api_manager.redis_catalog_uri
        # self.redis_channel = self.api_manager.redis_catalog_channel

        # kombu channel
        # self.exchange = Exchange(self.redis_channel, type='direct', delivery_mode=1)
        self.exchange = Exchange(self.broker_exchange, type="direct")  # , delivery_mode=1, durable=False)
        self.logger.debug("declare exchange %s" % self.exchange)
        self.queue_name = "%s.queue" % self.broker_exchange
        self.routing_key = "%s.key" % self.broker_exchange
        self.queue = Queue(self.queue_name, self.exchange, routing_key=self.routing_key)

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=self.queue,
                accept=["pickle", "json"],
                callbacks=[self.store_endpoint],
                on_decode_error=self.decode_error,
            )
        ]

    def decode_error(self, message, exc):
        """Decode error

        :param message: message received
        :param exc: exception raised
        :return:
        """
        self.logger.error(exc)


def start_catalog_consumer(params):
    """Start catalog consumer

    :param params: configuration params
    """
    # internal logger
    logger = getLogger("beehive")

    # logger_level = int(params.get('api_logging_level', DEBUG))
    logger_level = int(os.getenv("LOGGING_LEVEL", logging.DEBUG))

    class BeehiveLogRecord(logging.LogRecord):
        def __init__(self, *args, **kwargs):
            super(BeehiveLogRecord, self).__init__(*args, **kwargs)
            self.api_id = getattr(operation, "id", "xxx")

    logging.setLogRecordFactory(BeehiveLogRecord)

    loggers = [logger, getLogger("beecell")]
    frmt = (
        "%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s " "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    LoggerHelper.simple_handler(loggers, logger_level, frmt=frmt, formatter=None)
    # LoggerHelper.simple_handler(loggers, logger_level)

    # setup api manager
    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()

    def terminate(*args):
        worker.should_stop = True

    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)

    # with Connection(api_manager.redis_catalog_uri) as conn:
    with Connection(api_manager.broker_event_uri) as conn:
        try:
            worker = CatalogConsumerKombu(conn, api_manager)
            logger.info("Start catalog consumer")
            logger.debug("Active worker: %s" % worker)
            logger.debug("Use broker connection: %s" % conn)
            worker.run()
        except KeyboardInterrupt:
            logger.info("Stop catalog consumer")

    logger.info("Stop catalog consumer")
