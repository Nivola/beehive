'''
Created on Jan 31, 2014

@author: darkbk
'''
import logging
import ujson as json

# patch redis socket to use async comunication 
from time import time
from gevent.socket import gethostname
from flask import Flask, Response

#from flask_admin import Admin
#from logging.handlers import SysLogHandler
from beecell.logger.helper import LoggerHelper
from beecell.server.uwsgi_server.wrapper import uwsgi_util
#from gibbonportal.controller.redis_session import RedisSessionInterface
#from gibbonportal.controller.auth import AuthController, DbAuth
#from gibbonportal.controller.auth import SystemUser
#from gibbonportal.task.manager import JobTable
#from gibbonportal.model import db
#from .status import StatusTable
#from .proxy import ProxyTable

from beecell.db.manager import MysqlManagerError
#from beecell.flask.redis_session import RedisSessionInterface
#from beecell.auth import AuthError, DatabaseAuth, LdapAuth, SystemUser
#from gibboncloud.orchestrator import OrchestratorManager, OrchestratorManagerError

#from beehive.common import ConfigDbManager
#from beehive.module.auth.model import AuthDbManager
from beehive.common import ApiManager, ApiManagerError
#from beehive.module.auth.mod import AuthenticationManager
from beehive.common import operation

class BeehiveAppError(Exception): pass
class BeehiveApp(Flask):
    """Custom Flask app used to read configuration and initialize security.
    
    TODO: pooller that execcute some periodically task like verify orchestrators
          are active
    """
    def __init__(self, *args, **kwargs):
        """ """
        #self._config = kwargs.pop('config')
        
        super(BeehiveApp, self).__init__(*args, **kwargs)

        # set debug mode
        self.debug = False
        
        self.http_socket = uwsgi_util.opt[u'http-socket']
        self.server_name = gethostname()
        
        self.app_name = uwsgi_util.opt[u'api_name']
        self.app_id = uwsgi_util.opt[u'api_id']
        self.log_path = u'/var/log/%s/%s' % (uwsgi_util.opt[u'api_package'], 
                                             uwsgi_util.opt[u'api_env'])
        
        ########################################################################
        # status table section        
        #self.status = StatusTable()
        #self.status.init_status_table(500)

        ########################################################################
        # status table section        
        #self.proxy_table = ProxyTable()
        #self.proxy_table.init_proxy_table(100)
        
        ########################################################################
        # job manager section
        #self.job_table = JobTable()
        #self.job_table.init_jobs_table(100)

        ########################################################################
        # Create database connection object
        #self.db = db
        #self.db.init_app(self)
        
        ########################################################################
        # security section
        #self._setup_security()

        #self.admin = Admin(name='Cloud Portal Admin')
        # Add views here
        #self.admin.init_app(self)
        
        #self.http_timeout = 2
        #self.http_interval = 2
        #self.db_uri = None
        #self.tcp_proxy = None
        #self.orchestrators = OrchestratorManager()
        
        # job manager
        #self.max_concurrent_jobs = 2
        #self.job_interval = 2
        #self.job_timeout = 1200
        #self.job_manager = None

        def error(e):
            error = {'status':'error', 
                     'api':'',
                     'operation':'',
                     'data':'',
                     'exception':'',
                     'code':str(405), 
                     'msg':'Method Not Allowed'}
            return Response(response=json.dumps(error), 
                            mimetype='application/json', 
                            status=405)

        self._register_error_handler(None, 405, error)
        
        # setup loggers
        self.setup_loggers()
        
        self.logger.info("##### SERVER STARTING #####")
        start = time()
        
        # api manager reference
        params = uwsgi_util.opt
        self.api_manager = ApiManager(params, app=self, 
                                      hostname=self.server_name)

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
        
        self.logger.info(u'Setup uwsgi over %s:%s' % (self.server_name, 
                                                      self.http_socket))
        
        self.logger.info("##### SERVER STARTED ##### - %s" % round(time() - start, 2))
    
    def del_configurations(self):
        del self.db_uri
        del self.tcp_proxy
        #del self.orchestrators
        #self.orchestrators = OrchestratorManager()

    def setup_loggers(self):
        """ """
        logname = uwsgi_util.opt['api_id']
        
        # base logging
        loggers = [self.logger,
                   logging.getLogger('beehive'),
                   logging.getLogger('beehive.db'),
                   logging.getLogger('gibboncloud'),
                   logging.getLogger('beecell'),
                   logging.getLogger('beedrones'),
                   logging.getLogger('beecell')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                          '%s/%s.log' % (self.log_path, logname))
        
        # async operation logging
        #loggers = [logging.getLogger('beehive.common.job')]
        #LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
        #                                  'log/%s.job' % logname)        
        
        # transaction and db logging
        loggers = [logging.getLogger('beehive.util.data'),
                   logging.getLogger('sqlalchemy.engine'),
                   logging.getLogger('sqlalchemy.pool')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                          '%s/%s.db.log' % (self.log_path, logname))
        
        # performance logging
        loggers = [logging.getLogger('beecell.perf')]
        LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                          '%s/%s.watch' % (self.log_path, logname), 
                                          frmt='%(asctime)s - %(message)s')        
        
        #from openstack import utils
        #utils.enable_logging(debug=True)

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