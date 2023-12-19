# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
from datetime import datetime
import ujson as json
from six import ensure_text

from beecell.logger import LoggerHelper
from beecell.simple import format_date, truncate
from beehive.common.event import EventHandler
from beehive.module.event.manager import EventConsumerError


class CliEventHandler(EventHandler):
    """Base event handler

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

        # params = self.api_manager.params
        #
        # # internal logger
        # self.logger2 = logging.getLogger('ApiEventHandler')
        #
        # log_path = params.get('api_log', None)
        #
        # if log_path is None:
        #     log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])
        # else:
        #     log_path = log_path.decode('utf-8')
        #
        # file_name = ensure_text(log_path) + '/apis.log'
        # loggers = [self.logger2]
        # LoggerHelper.rotatingfile_handler(loggers, logging.INFO, file_name, frmt='%(message)s')

    def callback(self, event, message):
        """Consume event relative to api where new access token is requested

        :param event: event received
        :param message: message received
        :return:
        """
        try:
            event_type = event.get("type")
            if event_type == "SSH":
                data = event.get("data")
                op = data.get("op")
                opid = data.get("opid")
                source = event.get("source")
                dest = event.get("dest")
                kvargs = json.loads(data.get("kwargs"))
                node_name = kvargs.get("node_name")
                node_user = kvargs.get("user").split(".")[0]
                tmpl = (
                    "%(source)s %(pod)s %(env)s %(source_ip)s %(dest_ip)s %(user)s %(identity)s %(op)s "
                    '%(node_name)s "%(node_user)s" %(elapsed)s'
                )
                log = {
                    "source": "CLI",
                    "pod": self.api_manager.pod,
                    "env": self.api_manager.app_env,
                    "source_ip": source.get("ip"),
                    "dest_ip": dest.get("ip"),
                    "user": source.get("user"),
                    "identity": source.get("identity"),
                    "node_name": node_name,
                    "node_user": node_user,
                    "elapsed": data.get("elapsed"),
                    "op": "%s.%s" % (opid, op),
                }
                self.logger.info(tmpl % log)
        except Exception as ex:
            self.logger.error("Error parsing event: %s" % ex)
            raise EventConsumerError(ex)
