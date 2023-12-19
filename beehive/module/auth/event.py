# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
from datetime import datetime

from six import ensure_text

from beecell.logger import LoggerHelper
from beecell.simple import format_date
from beehive.common.event import EventHandler
from beehive.module.event.manager import EventConsumerError


class AuthEventHandler(EventHandler):
    """Auth event handler

    :param api_manager: ApiManager instance
    """

    def __init__(self, api_manager):
        EventHandler.__init__(self, api_manager)

        loggers = [self.logger]
        if api_manager.syslog_server is not None:
            syslog_server, syslog_port = api_manager.syslog_server.split(":")
            facility = "local4"
            LoggerHelper.syslog_handler(
                loggers,
                logging.INFO,
                syslog_server,
                facility,
                frmt="%(message)s",
                propagate=False,
                syslog_port=int(syslog_port),
            )
        else:
            LoggerHelper.simple_handler(loggers, logging.INFO)

    def callback(self, event, message):
        """Consume event relative to api where new access token is requested

        :param event: event received
        :param message: message received
        :return:
        """
        try:
            event_type = event.get("type")
            if event_type == "API":
                data = event.get("data")
                route = data.get("op")
                source = event.get("source")
                dest = event.get("dest")
                if route.find("token") > 0:
                    path, method = route.split(":")
                    tmpl = (
                        "%(source)s %(pod)s %(env)s %(source_ip)s %(dest_ip)s %(user)s %(identity)s %(op)s "
                        '%(response_code)s "%(response_msg)s" %(elapsed)s'
                    )
                    log = {
                        "source": "CMP",
                        "pod": self.api_manager.pod,
                        "env": self.api_manager.app_env,
                        "source_ip": source.get("ip"),
                        "dest_ip": dest.get("ip"),
                        "user": source.get("user"),
                        "identity": source.get("identity"),
                        "response_code": data.get("response")[0],
                        "response_msg": data.get("response")[1],
                        "elapsed": data.get("elapsed"),
                        "op": route,
                    }
                    if method in ["POST", "DELETE"]:
                        self.logger.info(tmpl % log)
        except Exception as ex:
            self.logger.error("Error parsing event: %s" % ex)
            raise EventConsumerError(ex)
