"""
Created on Jan 31, 2014

@author: darkbk
"""
import logging
import ujson as json

# patch redis socket to use async comunication 
from time import time
from socket import gethostname
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
        self.setup_loggers()
        
        self.logger.info("##### SERVER STARTING #####")
        start = time()
        
        # api manager reference
        self.api_manager = ApiManager(self.params, app=self, hostname=self.server_name)

        # server configuration
        #self.api_manager.configure_logger()
        self.api_manager.configure()
        #self.get_configurations()
        
        # load modules
        self.api_manager.register_modules()
        
        # register in catalog
        self.api_manager.register_catalog()
        
        # register in moitor
        self.api_manager.register_monitor()
        
        self.logger.info(u'Setup server over: %s' % (self.api_manager.app_uri))
        self.logger.info(u'Setup server over: %s' % (self.api_manager.uwsgi_uri))      
        
        self.logger.info("##### SERVER STARTED ##### - %s" % round(time() - start, 2))
    
    def del_configurations(self):
        del self.db_uri
        del self.tcp_proxy
        #del self.orchestrators
        #self.orchestrators = OrchestratorManager()

    def setup_loggers(self):
        """ """
        logname = uwsgi_util.opt[u'api_id']
        
        # base logging
        file_name = u'%s/%s.log' % (self.log_path, logname)
        loggers = [self.logger,
                   logging.getLogger(u'oauthlib'),
                   logging.getLogger(u'beehive'),
                   logging.getLogger(u'beehive.db'),
                   logging.getLogger(u'beecell'),
                   logging.getLogger(u'beedrones'),
                   logging.getLogger(u'beehive_oauth2'),
                   logging.getLogger(u'beehive_monitor'),
                   logging.getLogger(u'beehive_service'),
                   logging.getLogger(u'beehive_resource')]
        # LoggerHelper.DEBUG2
        LoggerHelper.rotatingfile_handler(loggers, LoggerHelper.DEBUG, file_name)
        
        # transaction and db logging
        file_name = u'%s/%s.db.log' % (self.log_path, logname)
        loggers = [logging.getLogger(u'beehive.common.data'),
                   logging.getLogger(u'sqlalchemy.engine'),
                   logging.getLogger(u'sqlalchemy.pool')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, file_name)
        
        # performance logging
        file_name = u'%s/%s.watch' % (self.log_path, logname)
        file_name = u'%s/beehive.watch' % (self.log_path)
        loggers = [logging.getLogger(u'beecell.perf')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, file_name, frmt=u'%(asctime)s - %(message)s')

    def open_db_session(self):
        """Open database session.
        """
        try:
            operation.session = self.api_manager.db_manager.get_session()
            return operation.session
        except MysqlManagerError, e:
            self.logger.error(e)
            raise BeehiveAppError(e)
    
    def release_db_session(self):
        """Release database session.
        """
        try:
            self.api_manager.db_manager.release_session(operation.session)
        except MysqlManagerError, e:
            self.logger.error(e)
            raise BeehiveAppError(e)