# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import logging
from datetime import datetime

from beecell.logger import LoggerHelper
from beecell.simple import format_date
from beehive.common.event import EventHandler


class AuthEventHandler(EventHandler):
    def __init__(self, api_manager):
        EventHandler.__init__(self, api_manager)

        params = self.api_manager.params

        # internal logger
        self.logger2 = logging.getLogger('AuthEventHandler')
        log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])
        logname = '%s/accesses' % log_path
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
            if route.get('path').find('token') > 0:
                tmpl = '%(ip)s - %(user)s - %(identity)s [%(timestamp)s] "%(id)s %(op)s" %(response)s %(elapsed)s'
                log = {
                    'id': data.get('opid'),
                    'timestamp': format_date(datetime.fromtimestamp(event.get('creation'))),
                    'ip': source.get('ip'),
                    'user': source.get('user'),
                    'identity': source.get('identity'),
                    'response': data.get('response'),
                    'elapsed': data.get('elapsed'),
                    'op': '%s %s' % (route.get('method'), route.get('path'))
                }
                if route.get('method') in ['POST', 'DELETE']:
                    self.logger2.info(tmpl % log)
                    # self.logger.debug(tmpl % log)
