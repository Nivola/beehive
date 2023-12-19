# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import json
import unittest
from beehive.common.test import runtest, BeehiveTestCase
import logging
from beecell.logger.helper import LoggerHelper
from beecell.db.manager import parse_redis_uri
import pprint
import redis
import gevent


class SimpleEventConsumer(object):
    def __init__(self, redis_uri, redis_channel):
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

        self.redis_uri = redis_uri
        self.redis_channel = redis_channel

        # set redis manager
        host, port, db = parse_redis_uri(redis_uri)
        self.redis = redis.StrictRedis(host=host, port=int(port), db=int(db))

        self.pp = pprint.PrettyPrinter(indent=2)

    def start_subscriber(self):
        """ """
        channel = self.redis.pubsub()
        channel.subscribe(self.redis_channel)

        self.logger.info("Start event consumer on redis channel %s:%s" % (self.redis_uri, self.redis_channel))
        while True:
            try:
                msg = channel.get_message()
                if msg and msg["type"] == "message":
                    # get event data
                    data = json.loads(msg["data"])
                    etype = data["type"]
                    data = data["data"]
                    if etype == "API":
                        op = data["op"]
                        self.logger.debug("%s %s [%s] - %s" % (data["opid"], op["path"], op["method"], data["elapsed"]))
                    elif etype == "JOB":
                        self.logger.debug(
                            "%s %s - %s.%s - %s"
                            % (
                                data["opid"],
                                data["op"],
                                data["task"].split(".")[-1],
                                data["taskid"],
                                data["response"],
                            )
                        )
                    elif etype == "CMD":
                        self.logger.debug(
                            "%s %s - %s - %s"
                            % (
                                data["opid"],
                                data["op"],
                                data["response"],
                                data["elapsed"],
                            )
                        )

                gevent.sleep(0.05)  # be nice to the system :) 0.05
            except (gevent.Greenlet.GreenletExit, Exception) as ex:
                self.logger.error("Error receiving message: %s", exc_info=1)

        self.logger.info("Stop event consumer on redis channel %s:%s" % (self.redis_uri, self.redis_channel))


tests = [
    "test_start_consumer",
]


class SimpleEventConsumerCase(BeehiveTestCase):
    """To execute this test you need a cloudstack instance."""

    def setUp(self):
        BeehiveTestCase.setUp(self)

        # start event consumer
        redis_uri = self.redis_uri
        redis_channel = "beehive.event.sub"
        self.consumer = SimpleEventConsumer(redis_uri, redis_channel)

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # simplehttp
    #
    def test_start_consumer(self):
        # internal logger
        logger = logging.getLogger("__main__")

        logger_level = logging.DEBUG
        loggers = [logger]
        frmt = "%(asctime)s - %(message)s"
        LoggerHelper.simple_handler(loggers, logger_level, frmt=frmt, formatter=None)
        logger.info("START")
        self.consumer.start_subscriber()


def run(args):
    runtest(SimpleEventConsumerCase, tests, args)


if __name__ == "__main__":
    run({})
