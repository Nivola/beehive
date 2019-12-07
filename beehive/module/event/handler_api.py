# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import logging
from datetime import datetime
import ujson as json
from beecell.logger import LoggerHelper
from beecell.simple import format_date, truncate
from beehive.common.event import EventHandler


class ApiEventHandler(EventHandler):
    def __init__(self, api_manager):
        EventHandler.__init__(self, api_manager)

        params = self.api_manager.params

        # internal logger
        self.logger2 = logging.getLogger('ApiEventHandler')

        log_path = params.get('api_log', None)
        if log_path is None:
            log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])

        logname = '%s/apis' % log_path
        logger_file = '%s.log' % logname
        loggers = [self.logger2]
        LoggerHelper.rotatingfile_handler(loggers, logging.INFO, logger_file, frmt='%(message)s')

    def callback(self, event, message):
        """Consume event relative to api where new access token is requested

        :param event:
        :param message:
        :return:
        """
        event_type = event.get('type')
        if event_type == 'API':
            data = event.get('data')
            route = data.get('op')
            source = event.get('source')
            tmpl = '%(ip)s - %(user)s - %(identity)s [%(timestamp)s] "%(id)s %(method)s %(path)s" %(params)s ' \
                   '%(response)s %(elapsed)s'
            log = {
                'id': data.get('opid'),
                'timestamp': format_date(datetime.fromtimestamp(event.get('creation'))),
                'ip': source.get('ip'),
                'user': source.get('user'),
                'identity': source.get('identity'),
                'response': data.get('response'),
                'elapsed': data.get('elapsed'),
                'method': route.get('method'),
                'path': route.get('path'),
                'params': truncate(json.dumps(data.get('params')))
            }
            self.logger2.info(tmpl % log)
            # self.logger.debug(tmpl % log)
