#!/usr/bin/env python
"""
Created on Sep 22, 2017

@author: darkbk
"""
import os
import logging
import sys
import ujson as json
from beecell.logger.helper import LoggerHelper
from beehive.common.log import ColorFormatter
from beehive.manager.util.logger import LoggingLogHandler

from ansible.utils.display import Display as OrigDisplay
from beehive.manager.sections.business.vpcaas import vpcaas_controller_handlers
from beehive.manager.sections.business.staas import staas_controller_handlers



class Display(OrigDisplay):
    def __init__(self, verbosity=0):
        super(Display, self).__init__(verbosity)
        
    def display(self, msg, color=None, stderr=False, screen_only=False, 
                log_only=False):
        OrigDisplay.display(self, msg, color=color, stderr=stderr, screen_only=screen_only, log_only=log_only)
        logger.debug(msg)


display = Display()


from beehive.manager.util.controller import BaseController
from beehive.manager.sections.platform import platform_controller_handlers
from beehive.manager.sections.resource import resource_controller_handlers
from beehive.manager.sections.auth import auth_controller_handlers
from beehive.manager.sections.catalog import catalog_controller_handlers
from beehive.manager.sections.event import event_controller_handlers
# from beehive.manager.sections.scheduler import scheduler_controller_handlers
from beehive.manager.sections.business.service import service_controller_handlers
from beehive.manager.sections.business.authority import authority_controller_handlers
from beehive.manager.sections.business.dbaas import dbaas_controller_handlers
from beehive.manager.sections.business import business_controller_handlers
from beehive.manager.sections.vsphere import vsphere_controller_handlers,\
    vsphere_platform_controller_handlers
from beehive.manager.sections.openstack import openstack_controller_handlers,\
    openstack_platform_controller_handlers
from beehive.manager.sections.environment import env_controller_handlers
from beehive.manager.sections.oauth2 import oauth2_controller_handlers
from beehive.manager.sections.provider import provider_controller_handlers
from beehive.manager.sections.graphite import graphite_controller_handlers
from beehive.manager.sections.example import example_controller_handlers
from beehive.manager.sections.veeam import veeam_controller_handlers
from beecell.cement_cmd.foundation import CementCmd, CementCmdBaseController

from cement.core.controller import expose

logging.captureWarnings(True)
logger = logging.getLogger(__name__)


'''import cement.utils.misc
def minimal_logger(namespace, debug=False):
    return logging.getLogger(namespace)
cement.utils.misc.minimal_logger = minimal_logger'''

#import cement.core.controller
#cement.core.controller.LOG = logging.getLogger(u'cement.core.controller')



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


def config_cli(app):
    # get configs
    configs = app.config.get_section_dict(u'configs')
    envs = u', '.join(configs[u'environments'].keys())
    formats = u', '.join(BaseController.Meta.formats)
    
    if app.loop is False:
        # add any arguments after setup(), and before run()
        app.args.add_argument('-v', '--version', action='version', version=BANNER)
        app.args.add_argument('-k', '--key', action='store', dest='key',
                              help='Secret key file to use for encryption/decryption')
        app.args.add_argument('--vault', action='store', dest='vault',
                              help='Ansible vault password to use for inventory decryption')
        app.args.add_argument('-e', '--env', action='store', dest='env',
                              help='Execution environment. Select from: %s' % envs)
        app.args.add_argument('-E', '--envs', action='store', dest='envs',
                              help='Comma separated execution environments. Select from: %s' % envs)
        app.args.add_argument('-f', '--format', action='store', dest='format',
                              help='response format. Select from: %s' % formats)
        app.args.add_argument('--color', action='store', dest='color',
                              help='response colered. Can be true or false. [default=true]')
        app.args.add_argument('--verbosity', action='store', dest='verbosity', help='ansible verbosity')
    #else:
    #    app.args.add_argument('version', action='version', version=BANNER)


class CliController(CementCmdBaseController):
    """Base cli controller
    """
    class Meta:
        label = u'base'
        description = "Beehive manager."
        arguments = [
        ]

    def _setup(self, base_app):
        CementCmdBaseController._setup(self, base_app)

    @expose(hide=True)
    def default(self):
        """Default controller command
        """
        self.app.print_help()


class CliManager(CementCmd):
    """Cli manager

    set BEEHIVE_LOG to use alternative log file
    """
    vault = None

    class Meta:
        label = "beehive"
        debug = False
        prompt = u'beehive> '
        
        logging_level = logging.DEBUG
        logging_format = u'%(asctime)s - %(levelname)s - %(name)s.%(funcName)s:%(lineno)d - %(message)s'
        logging_file = u'/var/log/beehive/manage.log'
        logging_max_files = 4
        logging_max_size = 4096000
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
        
        logger.info(u'Setup handler')
        handlers.extend(env_controller_handlers)
        handlers.extend(platform_controller_handlers)
        handlers.extend(resource_controller_handlers)
        handlers.extend(auth_controller_handlers)
        handlers.extend(oauth2_controller_handlers)
        handlers.extend(catalog_controller_handlers)
        handlers.extend(event_controller_handlers)
        # handlers.extend(scheduler_controller_handlers)
        handlers.extend(business_controller_handlers)
        handlers.extend(service_controller_handlers)
        handlers.extend(authority_controller_handlers)
        
        handlers.extend(dbaas_controller_handlers)
        handlers.extend(vpcaas_controller_handlers)
        handlers.extend(staas_controller_handlers)
                
        handlers.extend(vsphere_controller_handlers)
        handlers.extend(vsphere_platform_controller_handlers)
        handlers.extend(openstack_controller_handlers)
        handlers.extend(openstack_platform_controller_handlers)
        handlers.extend(provider_controller_handlers)
        handlers.extend(graphite_controller_handlers)
        handlers.extend(example_controller_handlers)
        handlers.extend(veeam_controller_handlers)

        configs_file = u'/etc/beehive/manage.conf'
        history_file = u'~/.beehive.manage'
        fernet_key = u'/etc/beehive/manage.key'
        ansible_vault = u'/etc/beehive/manage.ansible.vault'
        
        # authorization
        token_file = u'/tmp/.manage.token'
        seckey_file = u'/tmp/.manage.seckey'
        
        hooks = [
            ('pre_run', config_cli)
        ]
        
        color = True
        format = u'text'
        verbosity = 0

    def configure(self):
        """Configure app
        """
        # create .beehive dir in home directory if it does not exists
        homedir = os.path.expanduser(u'~')
        directory = u'%s/.beehive' % homedir
        if not os.path.exists(directory):
            os.makedirs(directory)
            os.chmod(directory, 0700)

        # load config file from home
        if os.path.isfile(u'%s/manage.conf' % directory) is True:
            self._meta.configs_file = u'%s/manage.conf' % directory

        # load fernet key from home
        if os.path.isfile(u'%s/manage.key' % directory) is True:
            self._meta.fernet_key = u'%s/manage.key' % directory

        # load ansible vault from home
        if os.path.isfile(u'%s/manage.ansible.vault' % directory) is True:
            self._meta.ansible_vault = u'%s/manage.ansible.vault' % directory

        # authorization
        self._meta.token_file = u'%s/.manage.token' % directory
        self._meta.seckey_file = u'%s/.manage.seckey' % directory

    def setup(self):
        """App main setup
        """
        CementCmd.setup(self)
        self.load_configs()
        logger.info(u'App %s configured' % self._meta.label)

    def setup_once(self):
        """App main setup execute only once
        """
        # if self.has_setup is False:
        #    self.setup_logging()
        CementCmd.setup_once(self)            

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
                u'log': u'./',
                u'endpoint': None
            }
        self.config.merge({u'configs': configs})
        logger.info(u'Load configuration from %s' % self._meta.configs_file)

        # fernet key
        if os.path.exists(self._meta.fernet_key):
            f = open(self._meta.fernet_key, 'r')
            self.fernet = f.read().rstrip()
            f.close()
            logger.info(u'Load fernet key from %s' % self._meta.fernet_key)

        # ansible vault
        if os.path.exists(self._meta.ansible_vault):
            f = open(self._meta.ansible_vault, 'r')
            self.vault = f.read().rstrip()
            f.close()
            logger.info(u'Load ansible vault pwd from %s' % self._meta.ansible_vault)

    @staticmethod
    def setup_logging():
        """Setup loggers
        """
        # set alternative log file
        log_file = os.environ.get(u'BEEHIVE_LOG', None)
        if log_file is None:
            log_file = CliManager.Meta.logging_file

        loggers = [logging.getLogger(item) for item in CliManager.Meta.logging_loggers]
        loggers.append(logger)
        # loggers.append(self.log)
        LoggerHelper.rotatingfile_handler(loggers, CliManager.Meta.logging_level,
                                          log_file,
                                          CliManager.Meta.logging_max_size, 
                                          CliManager.Meta.logging_max_files, 
                                          CliManager.Meta.logging_format,
                                          formatter=ColorFormatter)
        logger.info(u'========================================================')
        logger.info(u'Setup loggers over file: %s' % log_file)


if __name__ == u'__main__':    
    CliManager.setup_logging()
    app = CliManager('beehive')
    app.configure()
    app.run()
    
    # close the application
    app.close()
