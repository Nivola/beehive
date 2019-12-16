# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

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
        
        self.http_socket = uwsgi_util.opt['http-socket']
        self.server_name = uwsgi_util.opt['api_host']
        self.server_fqdn = uwsgi_util.opt['api_fqdn']
        try:
            self.server_ip = gethostbyname(uwsgi_util.opt['api_fqdn'])
        except:
            self.server_ip = '127.0.0.1'
        
        self.app_name = uwsgi_util.opt['api_name']
        self.app_id = uwsgi_util.opt['api_id']
        
        # api instance static config
        self.params = uwsgi_util.opt

        # set logging path
        log_path = '/var/log/%s/%s' % (self.params['api_package'], self.params['api_env'])
        self.log_path = self.params.get('api_log', log_path)

        def error405(e):
            error = {
                'code': 405,
                'message': 'Method Not Allowed',
                'description': 'Method Not Allowed'
            }
            logger.error('Api response: %s' % error)
            return Response(response=json.dumps(error), mimetype='application/json', status=405)
        self._register_error_handler(None, 405, error405)
        
        def error404(e):
            error = {
                'code': 404,
                'message': 'Uri %s not found' % request.path,
                'description': 'Uri %s not found' % request.path
            }
            logger.error('Api response: %s' % error)
            return Response(response=json.dumps(error), mimetype='application/json', status=404)
        self._register_error_handler(None, 404, error404)        
        
        # setup loggers
        loggin_level = int(self.params['api_logging_level'])
        self.setup_loggers(level=loggin_level)
        
        logger.info('########## SERVER STARTING ##########')
        start = time()
        
        # api manager reference
        self.api_manager = ApiManager(self.params, app=self, hostname=self.server_ip)

        # server configuration
        # self.api_manager.configure_logger()
        self.api_manager.configure()
        # self.get_configurations()

        # setup additional handler
        if self.api_manager.elasticsearch is not None:
            tags = []
            self.setup_additional_loggers(self.api_manager.elasticsearch, level=loggin_level, tags=tags,
                                          server=self.server_name, app=self.app_id, component='api')

        # load modules
        self.api_manager.register_modules()
        
        # register in catalog
        self.api_manager.register_catalog()
        
        # register in moitor
        self.api_manager.register_monitor()
        
        logger.info('Setup server over: %s' % self.api_manager.app_uri)
        logger.info('Setup server over: %s' % self.api_manager.uwsgi_uri)
        
        logger.info('########## SERVER STARTED ########## - %s' % round(time() - start, 2))
    
    def del_configurations(self):
        del self.db_uri
        del self.tcp_proxy

    def setup_loggers(self, level=LoggerHelper.DEBUG):
        """Setup loggers

        :param level:
        :return:
        """
        logname = uwsgi_util.opt['api_id']

        # base logging
        file_name = '%s/%s.log' % (self.log_path, logname)
        file_name = file_name.decode('utf-8')
        loggers = [
            logger,
            logging.getLogger('oauthlib'),
            logging.getLogger('beehive'),
            logging.getLogger('beecell'),
            logging.getLogger('beedrones'),
            logging.getLogger('beehive_oauth2'),
            logging.getLogger('beehive_service'),
            logging.getLogger('beehive_resource'),
            logging.getLogger('beehive_ssh'),
            # logging.getLogger('beehive.common.data')
        ]
        # LoggerHelper.DEBUG2
        LoggerHelper.rotatingfile_handler(loggers, level, file_name)
        
        # # transaction and db logging
        # file_name = '%s/%s.db.log' % (self.log_path, logname)
        # loggers = [
        #     logging.getLogger('sqlalchemy.engine'),
        #     logging.getLogger('sqlalchemy.pool')
        # ]
        # LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, file_name)

    def setup_additional_loggers(self, elasticsearch, level=LoggerHelper.DEBUG, tags=[], **custom_fields):
        """Setup loggers

        :param elasticsearch: elasticsearch.Elasticsearch class instance
        :param level:
        :return:
        """
        # logname = uwsgi_util.opt['api_id']

        loggers = [
            logger,
            logging.getLogger('oauthlib'),
            logging.getLogger('beehive'),
            logging.getLogger('beehive.db'),
            logging.getLogger('beecell'),
            logging.getLogger('beedrones'),
            logging.getLogger('beehive_oauth2'),
            logging.getLogger('beehive_service'),
            logging.getLogger('beehive_resource'),
            logging.getLogger('beehive_ssh'),
            # logging.getLogger('beehive.common.data')
        ]
        # LoggerHelper.DEBUG2
        LoggerHelper.elastic_handler(loggers, level, elasticsearch, index='cmp', tags=tags, **custom_fields)

    def open_db_session(self):
        """Open database session.
        """
        try:
            operation.session = self.api_manager.db_manager.get_session()
            return operation.session
        except MysqlManagerError as e:
            logger.error(e)
            raise BeehiveAppError(e)
    
    def release_db_session(self):
        """Release database session.
        """
        try:
            self.api_manager.db_manager.release_session(operation.session)
        except MysqlManagerError as e:
            logger.error(e)
            raise BeehiveAppError(e)