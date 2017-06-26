#!/usr/bin/env python
'''
Created on Jan 9, 2017

@author: darkbk
'''
import os, sys
import logging
import getopt
import ujson as json

from beehive.manager import ComponentManager
from beehive.common.log import ColorFormatter
from beehive.manager.ops.platform import PlatformManager
from beehive.manager.ops.provider import ProviderManager
from beehive.manager.ops.resource import ResourceManager
from beehive.manager.ops.scheduler import SchedulerManager
from beehive.manager.ops.vsphere import VsphereManager, NsxManager
from beehive.manager.ops.openstack import OpenstackManager
from beehive.manager.ops.native_vsphere import NativeVsphereManager
from beehive.manager.ops.native_openstack import NativeOpenstackManager
from beehive.manager.ops.monitor import MonitorManager
from beehive.manager.ops.auth import AuthManager
from beehive.manager.ops.catalog import CatalogManager
from beehive.manager.ops.event import EventManager
from beecell.logger.helper import LoggerHelper
from beehive.manager.ops.config import ConfigManager
from beehive.manager.ops.oauth2 import Oaut2hManager
from beehive.manager.ops.keyauth import KeyauthManager
from beehive.manager.ops.native_graphite import NativeGraphiteManager

VERSION = u'1.0.0'

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def load_config(file_config):
    f = open(file_config, 'r')
    auth_config = f.read()
    auth_config = json.loads(auth_config)
    f.close()
    return auth_config

def get_params(args):
    return {}

def main(run_path, argv):
    """
    SECTIONs:
        platform
        auth
        oauth2
        keyauth
        catalog
        event
        monitor
        resource
        scheduler
        provider
        config
        vsphere
        nsx
        openstack
        native.vsphere
        native.openstack
        native.graphite
        
    PARAMs:
        <custom section param>, ..
        
    Examples:
    
    Generic help:
    $ manage.py -h                                     
    
    <SECTION> help:
    $ manage.py -h <SECTION>
    
    Use <SECTION> commands in environment test:
    $ manage.py -e test <SECTION> [PARAMs]...
    
    Use <SECTION> commands in environment test. Format results in json:
    $ manage.py -e test -f json <SECTION> [PARAMs]...         
    """
    logger = logging.getLogger(__name__)
    file_config = u'/etc/beehive/manage.conf'
    retcode = 0
    frmt = u'table'
    env = u'test'
    color = 1
    
    sections = {
        u'platform':PlatformManager,
        u'subsystem':None,
        u'client':None,
        u'auth':AuthManager,
        u'oauth2':Oaut2hManager,
        u'keyauth':KeyauthManager,
        u'catalog':CatalogManager,
        u'event':EventManager,
        u'monitor':MonitorManager,
        u'resource':ResourceManager,
        u'scheduler':SchedulerManager,
        u'provider':ProviderManager,
        u'config':ConfigManager,
        u'vsphere':VsphereManager,
        u'nsx':NsxManager,
        u'openstack':OpenstackManager,
        u'native.vsphere':NativeVsphereManager,
        u'native.openstack':NativeOpenstackManager,
        u'native.graphite':NativeGraphiteManager,
    }
    
    try:
        opts, args = getopt.getopt(argv, u'c:f:e:o:hv',
                                   [u'help', u'conf=', u'format=', u'env=', 
                                    u'color', u'version'])
    except getopt.GetoptError:
        print(ComponentManager.__doc__)
        print(main.__doc__)
        return 2
    
    # check section
    try:
        section = args.pop(0)
    except:
        print(ComponentManager.__doc__)
        print(main.__doc__)
        return 0    
    
    if u'help' in args:
        print(ComponentManager.__doc__)
        if sections.get(section, None) is not None:
            print(bcolors.OKBLUE + sections[section].__doc__ + bcolors.ENDC)
        else:
            print(bcolors.OKBLUE + main.__doc__ + bcolors.ENDC)
        return 0
    
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print(ComponentManager.__doc__)
            if sections.get(section, None) is not None:
                print(bcolors.OKBLUE + sections[section].__doc__ + bcolors.ENDC)
            else:
                print(bcolors.OKBLUE + main.__doc__ + bcolors.ENDC)
            return 0
        elif opt in (u'-v', u'--version'):
            print u'auth %s' % VERSION
            return 0
        elif opt in (u'-e', u'--env'):
            env = arg
        elif opt in (u'-c', u'--conf'):
            # read manage alternative config
            file_config = arg
        elif opt in (u'-f', u'--format'):
            frmt = arg
        elif opt in (u'-o', u'--color'):
            color = arg
            
    # set format with param
    if (args[-1] in ComponentManager.formats) is True:
        frmt = args.pop(-1)   

    # load configuration
    if os.path.exists(file_config):
        auth_config = load_config(file_config)
    else:
        auth_config = {
            u'log':u'./',
            u'endpoint':None
        }
    auth_config[u'color'] = color

    # set token if exist
    auth_config[u'token_file'] = u'.manage.token'
    auth_config[u'seckey_file'] = u'.manage.seckey'
    auth_config[u'token'] = None
    
    # setup loggers
    loggers = [
        logger,
        logging.getLogger(u'beecell'),
        logging.getLogger(u'py.warnings'),
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beehive_oauth2'),
        logging.getLogger(u'beehive_resource'),
        logging.getLogger(u'beehive_monitor'),
        logging.getLogger(u'beehive_service'),
        logging.getLogger(u'beedrones'),
        logging.getLogger(u'requests'),
        logging.getLogger(u'urllib3'),
    ]
    lfrmt = u'%(asctime)s - %(levelname)s - ' \
            u'%(name)s.%(funcName)s:%(lineno)d - %(message)s'
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                      u'%s/manage.log' % auth_config[u'log'], 
                                      1024*1024, 5, lfrmt,
                                      formatter=ColorFormatter)
    
    loggers = [
        logging.getLogger(u'beecell.perf')
    ]
    LoggerHelper.rotatingfile_handler(loggers, logging.ERROR, 
                                      u'%s/manage.watch.log' % auth_config[u'log'], 
                                      1024*1024, 5, lfrmt)

    logging.captureWarnings(True)

    try:
        manager = main
        
        if section not in sections:
            raise Exception(u'ERROR : section %s does not exist' % section)
        manager = sections[section]
        retcode = manager.main(auth_config, frmt, opts, args, env)
        
        '''
        if section == u'platform':
            manager = PlatformManager
            retcode = PlatformManager.main(auth_config, frmt, opts, args, env, 
                                           PlatformManager)
    
        elif section == u'subsystem':
            retcode = create_main(auth_config, frmt, args)
        
        elif section == u'client':
            retcode = create_client(auth_config, frmt, args)
                
        elif section == u'auth':
            manager = AuthManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)
            
        elif section == u'oauth2':
            manager = Oaut2hManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)           
            
        elif section == u'catalog':
            manager = CatalogManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)          

        elif section == u'event':
            manager = EventManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)

        elif section == u'monitor':
            manager = MonitorManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)
            
        elif section == u'resource':
            manager = ResourceManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)
            
        elif section == u'scheduler':
            manager = SchedulerManager
            try: subsystem = args.pop(0)
            except:
                raise Exception(u'ERROR : Container id is missing')  
            retcode = SchedulerManager.main(auth_config, frmt, opts, args, env, 
                                            SchedulerManager, subsystem=subsystem)

        elif section == u'config':
            manager = ConfigManager
            retcode = manager.main(auth_config, frmt, opts, args, env, 
                                   manager)
            
        elif section == u'provider':
            manager = ProviderManager
            try: cid = int(args.pop(0))
            except:
                raise Exception(u'ERROR : Provider id is missing')                
            retcode = ProviderManager.main(auth_config, frmt, opts, args, env, 
                                           ProviderManager, containerid=cid)
            
        elif section == u'vsphere':
            manager = VsphereManager
            try: cid = int(args.pop(0))
            except:
                raise Exception(u'ERROR : Orchestrator id is missing')              
            retcode = VsphereManager.main(auth_config, frmt, opts, args, env, 
                                          VsphereManager, containerid=cid)
            
        elif section == u'nsx':
            manager = NsxManager
            try: cid = int(args.pop(0))
            except:
                raise Exception(u'ERROR : Orchestrator id is missing')              
            retcode = NsxManager.main(auth_config, frmt, opts, args, env, 
                                          NsxManager, containerid=cid)
            
        elif section == u'openstack':
            manager = OpenstackManager
            try: cid = int(args.pop(0))
            except:
                raise Exception(u'ERROR : Orchestrator id is missing')              
            retcode = OpenstackManager.main(auth_config, frmt, opts, args, env, 
                                            OpenstackManager, containerid=cid)            
            
        elif section == u'native.vsphere':
            manager = NativeVsphereManager
            try: cid = args.pop(0)
            except:
                raise Exception(u'ERROR : Vcenter id is missing')              
            retcode = NativeVsphereManager.main(auth_config, frmt, opts, args, env, 
                                                NativeVsphereManager, 
                                                orchestrator_id=cid)
            
        elif section == u'native.openstack':
            manager = NativeOpenstackManager
            try: cid = args.pop(0)
            except:
                raise Exception(u'ERROR : Openstack id is missing')              
            retcode = NativeOpenstackManager.main(auth_config, frmt, opts, args, env, 
                                                  NativeOpenstackManager, 
                                                  orchestrator_id=cid)            
            
        else:
            raise Exception(u'ERROR : section in wrong')'''
                    
    except Exception as ex:
        line = [u'='] * 50
        #print(bcolors.FAIL + bcolors.BOLD + u'    ' + u''.join(line))
        #print(u'     %s' % (ex))
        #print(u'    ' + u''.join(line) + bcolors.ENDC)
        #print(u'')
        print(bcolors.FAIL + u'   ERROR : ' + bcolors.ENDC +
              bcolors.FAIL + bcolors.BOLD + str(ex) + bcolors.ENDC)
        #print(ComponentManager.__doc__)
        print(u'')
        #print(bcolors.OKBLUE + manager.__doc__ + bcolors.ENDC)
        logger.error(ex, exc_info=1)
        retcode = 1
    
    return retcode

if __name__ == u'__main__':    
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)
    