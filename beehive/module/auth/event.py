"""
Created on Jun 29, 2018

@author: darkbk
"""
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
        self.logger2 = logging.getLogger(u'AuthEventHandler')
        log_path = u'/var/log/%s/%s' % (params[u'api_package'], params[u'api_env'])
        logname = u'%s/accesses' % log_path
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
            if route.get(u'path').find(u'token') > 0:
                tmpl = u'%(ip)s - %(user)s - %(identity)s [%(timestamp)s] "%(id)s %(op)s" %(response)s %(elapsed)s'
                log = {
                    u'id': data.get(u'opid'),
                    u'timestamp': format_date(datetime.fromtimestamp(event.get(u'creation'))),
                    u'ip': source.get(u'ip'),
                    u'user': source.get(u'user'),
                    u'identity': source.get(u'identity'),
                    u'response': data.get(u'response'),
                    u'elapsed': data.get(u'elapsed'),
                    u'op': u'%s %s' % (route.get(u'method'), route.get(u'path'))
                }
                if route.get(u'method') in [u'POST', u'DELETE']:
                    self.logger2.info(tmpl % log)
                    # self.logger.debug(tmpl % log)
