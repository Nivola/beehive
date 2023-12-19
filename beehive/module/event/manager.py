# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
from datetime import datetime
from copy import deepcopy
from re import match
from pylogbeat import PyLogBeatClient
from beecell.password import obscure_data
from beecell.types.type_string import truncate
from beecell.types.type_date import format_date
from beecell.types.type_id import id_gen
from beecell.simple import import_class
from beecell.logger.helper import LoggerHelper
from signal import signal
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue
from kombu.pools import producers
from kombu import Connection, exceptions
from beehive.module.event.model import EventDbManager
from beehive.common.event import EventProducerRedis, Event
from beehive.common.data import operation
from beecell.db import TransactionError
from beehive.common.apimanager import ApiManager, ApiObject
import os
from tempfile import NamedTemporaryFile
from six import ensure_binary
import base64


class EventConsumerError(Exception):
    pass


class EventConsumer(ConsumerMixin):
    """Event consumer from redis queue

    :param connection: redis connection
    :param api_manager: ApiManager instance
    :param event_handlers: list of event handlers used when event is received. An event handler is a class that extend
        EventHandler and define a callback method.
    """

    def __init__(self, connection, api_manager: ApiManager, event_handlers=None):
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

        self.connection = connection
        self.api_manager = api_manager
        self.db_manager = self.api_manager.db_manager
        self._continue = None
        self.id = id_gen()

        # event db manager
        self.manager = EventDbManager()

        # elastic search client
        self.elasticsearch = api_manager.elasticsearch
        self.logstash = api_manager.logstash
        self.__load_logstash_cert()

        self.index = "cmp-event-%s" % api_manager.app_env

        self.event_handlers = []
        if event_handlers is None:
            event_handlers = []
        for event_handler in event_handlers:
            handler = import_class(event_handler)
            self.event_handlers.append(handler(self.api_manager))

        self.broker_uri = self.api_manager.broker_event_uri
        self.broker_exchange = self.api_manager.broker_event_exchange

        self.exchange = Exchange(self.broker_exchange, type="direct")  # , delivery_mode=1, durable=False)
        self.logger.debug("declare exchange %s" % self.exchange)
        self.queue_name = "%s.queue" % self.broker_exchange
        self.routing_key = "%s.key" % self.broker_exchange
        self.queue = Queue(self.queue_name, self.exchange, routing_key=self.routing_key)
        self.logger.debug("declare queue %s" % self.queue)
        # self.event_producer = EventProducerRedis(self.broker_uri, self.broker_exchange+'.sub', framework='simple')
        self.conn = Connection(self.broker_uri)
        self.logger.debug("open connection to broker %s" % self.conn)

    def __create_temp_file(self, data):
        fp = NamedTemporaryFile()
        fp.write(ensure_binary(base64.b64decode(data)))
        fp.seek(0)
        return fp

    def __close_temp_file(self, fp):
        fp.close()

    def __load_logstash_cert(self):
        if self.logstash is not None:
            self.logstash["ca_file"] = self.__create_temp_file(self.logstash.get("ca"))
            self.logstash["cert_file"] = self.__create_temp_file(self.logstash.get("cert"))
            self.logstash["pkey_file"] = self.__create_temp_file(self.logstash.get("pkey"))

    def get_consumers(self, Consumer, channel):
        """Get consumer

        :param Consumer: kombu consumer
        :param channel: kombu channel
        :return:
        """
        return [
            Consumer(
                queues=self.queue,
                accept=["pickle", "json"],
                callbacks=[self.callback],
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

    def callback(self, event, message):
        """Consume event

        :param event: event received
        :param message: message received
        :return:
        """
        try:
            event["data"] = obscure_data(event["data"])
            self.log_event(event, message)
            self.store_event(event, message)
            # self.publish_event_to_subscriber(event, message)

            # run additional event handler
            for event_handler in self.event_handlers:
                event_handler.callback(event, message)
        except EventConsumerError as ex:
            self.logger.warning(ex, exc_info=True)

    def log_event(self, event, message):
        """Log received event

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        message.ack()
        self.logger.info("Consume event : %s" % truncate(event))
        # self.logger.warning('Consume event : %s' % event)
        # todo: remove warning

    def store_event(self, event, message):
        """Store event. If elastic search server are defined use it otherwise write on db

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        if self.logstash is not None:
            self._store_event_logstash(event, message)
        elif self.elasticsearch is not None:
            self._store_event_elastic(event, message)
        # Attenzione: sembra che solo il batch di acquisizione delle metriche passi di qui. Dati useless
        # else:
        #     self._store_event_db(event, message)

    def _store_event_elastic(self, event, message):
        """Store event in elastic search.

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        try:
            # clone event
            # sevent = deepcopy(event)

            # get event type
            etype = event["type"]

            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS'
            if etype == ApiObject.ASYNC_OPERATION:
                status = event["data"]["response"][0]
                if status not in ["STARTED", "FAILURE", "SUCCESS", "STEP"]:
                    return None

            msg = {
                "event_id": event["id"],
                "type": etype,
                "dest": event["dest"],
                "source": event["source"],
                "date": datetime.fromtimestamp(event["creation"]),
                "data": event["data"],
            }

            date = datetime.now()
            index = "%s-%s" % (self.index, date.strftime("%Y.%m.%d"))
            # self.elasticsearch.index(index=index, body=msg, request_timeout=30, doc_type="doc")
            self.elasticsearch._request_timeout = 30
            self.elasticsearch.index(index=index, body=msg)

            self.logger.debug("Store event in elastic: %s" % truncate(msg))
        except Exception as ex:
            self.logger.error("Error storing event in elastic: %s" % ex)
            raise EventConsumerError(ex)

    def _store_event_logstash(self, event, message):
        """Store event in elastic using logstash.

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        try:
            # get event type
            etype = event["type"]

            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS'
            if etype == ApiObject.ASYNC_OPERATION:
                status = event["data"]["response"][0]
                if status not in ["STARTED", "FAILURE", "SUCCESS", "STEP"]:
                    return None

            timestamp = datetime.fromtimestamp(event["creation"])
            msg = {
                "@timestamp": format_date(timestamp),
                "@version": "1",
                "tags": [],
                "@metadata": {
                    "version": "2.0.0",
                    "beat": "pylogbeat",
                    "id": self.id,
                    "name": self.api_manager.pod,
                    "hostname": self.api_manager.server_name,
                    "index": self.index,
                },
                "agent": {
                    "version": "2.0.0",
                    "type": "pylogbeat",
                    "id": self.id,
                    "pod": self.api_manager.pod,
                    "hostname": self.api_manager.server_name,
                    "env": self.api_manager.app_env,
                },
                "event_id": event["id"],
                "type": etype,
                "dest": event["dest"],
                "source": event["source"],
                "data": event["data"],
            }

            with PyLogBeatClient(
                self.logstash.get("host"),
                self.logstash.get("port"),
                ssl_enable=True,
                ssl_verify=False,
                keyfile=self.logstash["pkey_file"].name,
                certfile=self.logstash["cert_file"].name,
                ca_certs=self.logstash["ca_file"].name,
            ) as client:
                client.send([msg])

            self.logger.debug("Store event in logstash: %s" % truncate(msg))
        except Exception as ex:
            self.logger.error("Error storing event in elastic: %s" % ex)
            raise EventConsumerError(ex)

    def _store_event_db(self, event, message):
        """Store event in db.

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        try:
            # get db session
            operation.session = self.db_manager.get_session()

            # clone event
            sevent = deepcopy(event)

            etype = sevent["type"]

            # for job events save only those with status 'STARTED', 'FAILURE' and 'SUCCESS'
            if etype == ApiObject.ASYNC_OPERATION:
                status = sevent["data"]["response"][0]
                if status not in ["STARTED", "FAILURE", "SUCCESS"]:
                    return None

            creation = datetime.fromtimestamp(sevent["creation"])
            dest = sevent["dest"]
            objid = dest.pop("objid")
            objdef = dest.pop("objdef")
            module = dest.pop("objtype")
            self.manager.add(
                sevent["id"],
                etype,
                objid,
                objdef,
                module,
                creation,
                sevent["data"],
                event["source"],
                dest,
            )

            self.logger.debug("Store event in db: %s" % truncate(sevent))
        except (TransactionError, Exception) as ex:
            self.logger.error("Error storing event in db: %s" % ex)
            raise EventConsumerError(ex)
        finally:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)

    def publish_event_to_subscriber(self, event, message):
        """Publish event to subscriber queue.

        :param event: event received
        :param message: message received
        :raise EventConsumerError:
        """
        self.__publish_event_simple(event["id"], event["type"], event["data"], event["source"], event["dest"])

    def __publish_event_simple(self, event_id, event_type, data, source, dest):
        try:
            # self.event_producer.send(event_type, data, source, dest)
            self.logger.debug("Publish event %s to channel %s" % (event_id, self.broker_exchange))
        except Exception as ex:
            self.logger.error("Event %s can not be published: %s" % (event_id, ex))
            raise EventConsumerError(ex)

    def __publish_event_kombu(self, event_id, event_type, data, source, dest):
        try:
            event = Event(event_type, data, source, dest)
            producer = producers[self.conn].acquire()
            producer.publish(
                event.dict(),
                serializer="json",
                compression="bzip2",
                exchange=self.exchange_sub,
                declare=[self.exchange_sub],
                routing_key=self.routing_key_sub,
                expiration=60,
                delivery_mode=1,
            )
            producer.release()
            self.logger.debug("Publish event %s to exchange %s" % (event_id, self.exchange_sub))
        except exceptions.ConnectionLimitExceeded as ex:
            self.logger.error("Event %s can not be published: %s" % (event_id, ex), exc_info=True)
        except Exception as ex:
            self.logger.error("Event %s can not be published: %s" % (event_id, ex), exc_info=True)


def start_event_consumer(params):
    """Start event consumer

    :param params: configuration params
    """
    # internal logger
    logger = logging.getLogger("beehive.module.event.manager")

    logging_level = int(params["api_logging_level"])
    logger_level = int(os.getenv("LOGGING_LEVEL", logging_level))

    class BeehiveLogRecord(logging.LogRecord):
        def __init__(self, *args, **kwargs):
            super(BeehiveLogRecord, self).__init__(*args, **kwargs)
            self.api_id = getattr(operation, "id", "xxx")

    logging.setLogRecordFactory(BeehiveLogRecord)

    loggers = [
        logger,
        logging.getLogger("beehive.common.event"),
        logging.getLogger("beehive.module.event.model"),
    ]
    loggers = [logging.getLogger("beehive")]
    frmt = (
        "%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s " "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    LoggerHelper.simple_handler(loggers, logger_level, frmt=frmt, formatter=None)

    # get event handlers
    event_handlers = params.pop("event_handler", [])

    # setup api manager
    api_manager = ApiManager(params, hostname=os.getenv("API_POD_IP", ""))
    api_manager.configure()
    api_manager.register_modules()

    def terminate(*args):
        worker.should_stop = True

    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)

    with Connection(api_manager.broker_event_uri) as conn:
        try:
            worker = EventConsumer(conn, api_manager, event_handlers=event_handlers)
            logger.info("Start event consumer")
            logger.debug("Event handlers: %s" % event_handlers)
            logger.debug("Active worker: %s" % worker)
            logger.debug("Use broker connection: %s" % conn)
            worker.run()
        except KeyboardInterrupt:
            logger.info("Stop event consumer")
        except Exception as ex:
            logger.error(ex, exc_info=True)

    logger.info("Stop event consumer")
