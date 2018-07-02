"""
Created on Jun 29, 2018

@author: darkbk
"""
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
        self.logger2 = logging.getLogger(u'ApiEventHandler')
        log_path = u'/var/log/%s/%s' % (params[u'api_package'], params[u'api_env'])
        logname = u'%s/apis' % log_path
        logger_file = u'%s.log' % logname
        loggers = [self.logger2]
        LoggerHelper.rotatingfile_handler(loggers, logging.INFO, logger_file, frmt=u'%(message)s')

    def callback(self, event, message):
        """Consume event relative to api where new access token is requested

        :param event:
        :param message:
        :return:
        """
        event_type = event.get(u'type')
        if event_type == u'API':
            data = event.get(u'data')
            route = data.get(u'op')
            source = event.get(u'source')
            tmpl = u'%(ip)s - %(user)s - %(identity)s [%(timestamp)s] "%(id)s %(method)s %(path)s" %(params)s ' \
                   u'%(response)s %(elapsed)s'
            log = {
                u'id': data.get(u'opid'),
                u'timestamp': format_date(datetime.fromtimestamp(event.get(u'creation'))),
                u'ip': source.get(u'ip'),
                u'user': source.get(u'user'),
                u'identity': source.get(u'identity'),
                u'response': data.get(u'response'),
                u'elapsed': data.get(u'elapsed'),
                u'method': route.get(u'method'),
                u'path': route.get(u'path'),
                u'params': truncate(json.dumps(data.get(u'params')))
            }
            self.logger2.info(tmpl % log)
            # self.logger.debug(tmpl % log)
