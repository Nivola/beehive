# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import logging
import ujson as json

# patch redis socket to use async comunication 
from time import time
from socket import gethostname, gethostbyname
from flask import Flask, Response, request
from os import urandom
from beecell.logger.helper import LoggerHelper
from beecell.server.uwsgi_server.wrapper import uwsgi_util
from beecell.db.manager import MysqlManagerError
from beehive.common.apimanager import ApiManager, ApiManagerError
from beehive.common.data import operation

logger = logging.getLogger(__name__)


class BeehiveAppError(Exception):
    pass


class BeehiveApp(Flask):
    """Custom Flask app used to read configuration and initialize security.
    
    """
    def __init__(self, *args, **kwargs):
        """ """
        # self._config = kwargs.pop('config')
        
        super(BeehiveApp, self).__init__(*args, **kwargs)

        # set debug mode
        self.debug = False
        
        # flask secret
        self.secret_key = urandom(48)         
        
        self.http_socket = uwsgi_util.opt[u'http-socket']
        self.server_name = uwsgi_util.opt[u'api_host']
        self.server_fqdn = uwsgi_util.opt[u'api_fqdn']
        self.server_ip = gethostbyname(uwsgi_util.opt[u'api_fqdn'])
        
        self.app_name = uwsgi_util.opt[u'api_name']
        self.app_id = uwsgi_util.opt[u'api_id']
        
        # api instance static config
        self.params = uwsgi_util.opt
        
        # set logging path
        log_path = u'/var/log/%s/%s' % (self.params[u'api_package'], self.params[u'api_env'])
        self.log_path = self.params.get(u'api_log', log_path)

        def error405(e):
            error = {
                u'code': 405,
                u'message': u'Method Not Allowed',
                u'description': u'Method Not Allowed'
            }
            logger.error(u'Api response: %s' % error)
            return Response(response=json.dumps(error), mimetype=u'application/json', status=405)
        self._register_error_handler(None, 405, error405)
        
        def error404(e):
            error = {
                u'code': 404,
                u'message': u'Uri %s not found' % request.path,
                u'description': u'Uri %s not found' % request.path
            }
            logger.error(u'Api response: %s' % error)
            return Response(response=json.dumps(error), mimetype=u'application/json', status=404)
        self._register_error_handler(None, 404, error404)        
        
        # setup loggers
        loggin_level = int(self.params[u'api_logging_level'])
        self.setup_loggers(level=loggin_level)
        
        self.logger.info(u'##### SERVER STARTING #####')
        start = time()
        
        # api manager reference
        self.api_manager = ApiManager(self.params, app=self, hostname=self.server_ip)

        # server configuration
        # self.api_manager.configure_logger()
        self.api_manager.configure()
        # self.get_configurations()

        # setup additional handler
        if self.api_manager.elasticsearch is not None:
            tags = [self.server_name, self.app_id, u'api']
            self.setup_additional_loggers(self.api_manager.elasticsearch, level=loggin_level, tags=tags)

        # load modules
        self.api_manager.register_modules()
        
        # register in catalog
        self.api_manager.register_catalog()
        
        # register in moitor
        self.api_manager.register_monitor()
        
        self.logger.info(u'Setup server over: %s' % self.api_manager.app_uri)
        self.logger.info(u'Setup server over: %s' % self.api_manager.uwsgi_uri)
        
        self.logger.info(u'##### SERVER STARTED ##### - %s' % round(time() - start, 2))
    
    def del_configurations(self):
        del self.db_uri
        del self.tcp_proxy

    def setup_loggers(self, level=LoggerHelper.DEBUG):
        """Setup loggers

        :param level:
        :return:
        """
        logname = uwsgi_util.opt[u'api_id']
        
        # base logging
        file_name = u'%s/%s.log' % (self.log_path, logname)
        loggers = [
            self.logger,
            logging.getLogger(u'oauthlib'),
            logging.getLogger(u'beehive'),
            logging.getLogger(u'beehive.db'),
            logging.getLogger(u'beecell'),
            logging.getLogger(u'beedrones'),
            logging.getLogger(u'beehive_oauth2'),
            logging.getLogger(u'beehive_service'),
            logging.getLogger(u'beehive_resource'),
            logging.getLogger(u'beehive_ssh'),
            # logging.getLogger(u'beehive.common.data')
        ]
        # LoggerHelper.DEBUG2
        LoggerHelper.rotatingfile_handler(loggers, level, file_name)
        
        # transaction and db logging
        file_name = u'%s/%s.db.log' % (self.log_path, logname)
        loggers = [#logging.getLogger(u'beehive.common.data'),
                   logging.getLogger(u'sqlalchemy.engine'),
                   logging.getLogger(u'sqlalchemy.pool')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, file_name)
        
        # performance logging
        file_name = u'%s/%s.watch' % (self.log_path, logname)
        file_name = u'%s/beehive.watch' % (self.log_path)
        loggers = [logging.getLogger(u'beecell.perf')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, file_name, frmt=u'%(asctime)s - %(message)s')

    def setup_additional_loggers(self, elasticsearch, level=LoggerHelper.DEBUG, tags=[]):
        """Setup loggers

        :param elasticsearch: elasticsearch.Elasticsearch class instance
        :param level:
        :return:
        """
        logname = uwsgi_util.opt[u'api_id']

        loggers = [
            self.logger,
            logging.getLogger(u'oauthlib'),
            logging.getLogger(u'beehive'),
            logging.getLogger(u'beehive.db'),
            logging.getLogger(u'beecell'),
            logging.getLogger(u'beedrones'),
            logging.getLogger(u'beehive_oauth2'),
            logging.getLogger(u'beehive_service'),
            logging.getLogger(u'beehive_resource'),
            logging.getLogger(u'beehive_ssh'),
            # logging.getLogger(u'beehive.common.data')
        ]
        # LoggerHelper.DEBUG2
        LoggerHelper.elastic_handler(loggers, level, elasticsearch, index=u'cmp', tags=tags)

    def open_db_session(self):
        """Open database session.
        """
        try:
            operation.session = self.api_manager.db_manager.get_session()
            return operation.session
        except MysqlManagerError as e:
            self.logger.error(e)
            raise BeehiveAppError(e)
    
    def release_db_session(self):
        """Release database session.
        """
        try:
            self.api_manager.db_manager.release_session(operation.session)
        except MysqlManagerError as e:
            self.logger.error(e)
            raise BeehiveAppError(e)