#!/usr/bin/env python
'''
Created on Sep 22, 2017

@author: darkbk
'''
import os
import logging
import sys
import ujson as json
from beecell.logger.helper import LoggerHelper
from beehive.common.log import ColorFormatter
from beehive.manager.util.logger import LoggingLogHandler
#from beehive.manager.sections.auth import AuthController
from beehive.manager.util.controller import BaseController
from beehive.manager.sections.platform import platform_controller_handlers
from beehive.manager.sections.resource import resource_controller_handlers
from beehive.manager.sections.auth import auth_controller_handlers
from beehive.manager.sections.catalog import catalog_controller_handlers
from beehive.manager.sections.event import event_controller_handlers
from beehive.manager.sections.scheduler import scheduler_controller_handlers
from beehive.manager.sections.service import service_controller_handlers
# from beehive.manager.sections.vsphere import vsphere_controller_handlers
from beehive.manager.sections.openstack import openstack_controller_handlers,\
    openstack_platform_controller_handlers
logging.captureWarnings(True)
logger = logging.getLogger(__name__)


'''import cement.utils.misc
def minimal_logger(namespace, debug=False):
    return logging.getLogger(namespace)
cement.utils.misc.minimal_logger = minimal_logger'''

#import cement.core.controller
#cement.core.controller.LOG = logging.getLogger(u'cement.core.controller')

from cement.core.controller import CementBaseController, expose
from cement.core.foundation import CementApp

VERSION = '0.1.0'

BANNER = """
Beehive Cli v%s
Copyright (c) 2017 Sergio Tonani
""" % VERSION

'''
import cement.utils.misc
class CliMinimalLogger(cement.utils.misc.MinimalLogger):
    """MinimalLogger extension. Remove console logger and introduce file stream 
    logger.
    """

    def __init__(self, namespace, debug, *args, **kw):
        level = logging.INFO
        if '--debug' in sys.argv or debug:
            level = logging.DEBUG 
        
        self.namespace = namespace
        self.backend = logging.getLogger(namespace)
        self.backend.setLevel(level)      
        
        loggers = [self.backend]
        LoggerHelper.rotatingfile_handler(loggers, level,
                                          CliManager.Meta.logging_file, 
                                          CliManager.Meta.logging_max_size, 
                                          CliManager.Meta.logging_max_files, 
                                          CliManager.Meta.logging_format,
                                          formatter=ColorFormatter)

cement.utils.misc.MinimalLogger = CliMinimalLogger'''

class CliController(CementBaseController):
    class Meta:
        label = u'base'
        description = "Beehive manager."
        arguments = [
        ]

    def _setup(self, base_app):
        CementBaseController._setup(self, base_app)

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()

class CliManager(CementApp):
    """Cli manager
    """
    class Meta:
        label = "beehive"
        debug = False
        #log_handler = 'clilogging'
        
        logging_level = logging.DEBUG
        logging_format = u'%(asctime)s - %(levelname)s - ' \
                         u'%(name)s.%(funcName)s:%(lineno)d - %(message)s'
        logging_file = u'/var/log/beehive/manage.log'
        logging_max_files = 4
        logging_max_size = 512000
        logging_loggers = [
            u'beecell',
            u'py.warnings',
            u'beehive',
            u'beehive_oauth2',
            u'beehive_resource',
            u'beehive_monitor',
            u'beehive_service',
            u'beedrones',
            u'requests',
            u'urllib3',
            u'ansible',
        ]

        config_defaults = {
            u'log.logging': {
            }
        }
        
        extensions = ['json']
        
        framework_logging = False
        config_handler = 'json'
        base_controller = "base"
        handlers = [
            #LoggingLogHandler,
            CliController,
        ]
        
        handlers.extend(platform_controller_handlers)
        handlers.extend(resource_controller_handlers)
        handlers.extend(auth_controller_handlers)
        handlers.extend(catalog_controller_handlers)
        handlers.extend(event_controller_handlers)
        handlers.extend(scheduler_controller_handlers)
        handlers.extend(service_controller_handlers)
        #handlers.extend(vsphere_controller_handlers)
        handlers.extend(openstack_controller_handlers)
        handlers.extend(openstack_platform_controller_handlers)
        
        configs_file = u'/etc/beehive/manage.conf'
        history_file = u'~/.beehive.manage'
        
        # authorization
        token_file = u'.manage.token'
        seckey_file = u'.manage.seckey'
        
        #config_files = [u'/etc/beehive/manage.conf']
        

    def __init__(self, *args, **kvargs):
        """Init cli manager
        """
        CementApp.__init__(self, *args, **kvargs)
        
        
    def setup(self):
        CementApp.setup(self)
        
        self.setup_logging()
        self.load_configs()

    def load_configs(self):
        """Load configurations
        """
        if os.path.exists(self._meta.configs_file):
            f = open(self._meta.configs_file, 'r')
            configs = f.read()
            configs = json.loads(configs)
            f.close()
            
        else:
            configs = {
                u'log':u'./',
                u'endpoint':None
            }
        self.config.merge({u'configs':configs})

    def setup_logging(self):
        """Setup loggers
        """
        loggers = [logging.getLogger(item) for item in self._meta.logging_loggers]
        loggers.append(logger)
        #loggers.append(self.log)
        LoggerHelper.rotatingfile_handler(loggers, self._meta.logging_level, 
                                          self._meta.logging_file, 
                                          self._meta.logging_max_size, 
                                          self._meta.logging_max_files, 
                                          self._meta.logging_format,
                                          formatter=ColorFormatter)


with CliManager() as app:
    # get configs
    configs = app.config.get_section_dict(u'configs')
    envs = u', '.join(configs[u'environments'].keys())
    formats = u', '.join(BaseController.Meta.formats)
    
    # add any arguments after setup(), and before run()
    app.args.add_argument('-v', '--version', action='version', version=BANNER)
    app.args.add_argument('-e', '--env', action='store', dest='env',
                      help='execution environment. Select from: %s' % envs)
    app.args.add_argument('-f', '--format', action='store', dest='format',
                      help='response format. Select from: %s' % formats)
    app.args.add_argument('--color', action='store', dest='color',
                      help='response colered. Can be true or false. [default=true]')
    
    logger.info(u'configure app')

    #app.config.parse_file(app.configs_file)
    #print app.config.get_sections()
    #print app.config.get_section_dict(u'beehive')
    #print app.config.get_section_dict(u'log.logging')
    
    # Check if an interface called 'output' is defined
    app.handler.defined('output')

    # Check if the handler 'argparse' is registered to the 'argument'
    # interface
    app.handler.registered('argument', 'argparse')
    app.run()
    
    # close the application
    app.close()
    
    