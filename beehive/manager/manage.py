#!/usr/bin/env python
'''
Created on Jan 9, 2017

@author: darkbk
'''
import os, sys
import logging
import getopt
import ujson as json

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

def main(run_path, argv):
    """
    SECTIONs:
        platform
        subsystem
        client
        auth
        monitor
        resource
        scheduler
        provider
    """
    # setup pythonpath
    #sys.path.append(os.path.expanduser(u'~/workspace/git/beecell'))
    #sys.path.append(os.path.expanduser(u'~/workspace/git/beedrones'))
    #sys.path.append(os.path.expanduser(u'~/workspace/git/beehive'))
    #sys.path.append(os.path.expanduser(u'~/workspace/git/gibboncloudapi'))     
    
    from beecell.logger.helper import LoggerHelper
    
    # imports
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
    from beehive.manager.ops.event import EventManager
    
    from beehive.manager.ops.create import create_main
    from beehive.manager.ops.create import create_client
    
    logger = logging.getLogger(__name__)
    file_config = u'./manage.conf'
    cmd = None
    p = None
    retcode = 0
    frmt = u'table'
    env = u'test'
    color = 1
    
    try:
        opts, args = getopt.getopt(argv, u'c:f:e:o:hv',
                                   [u'help', u'conf=', u'format=', u'env=', 
                                    u'color', u'version'])
    except getopt.GetoptError:
        print(ComponentManager.__doc__)
        print(main.__doc__)
        return 2
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print(ComponentManager.__doc__)
            print(main.__doc__)
            return 0
        elif opt in ('-v', '--version'):
            print 'auth %s' % VERSION
            return 0
        elif opt in ('-e', '--env'):
            env = arg
        elif opt in ('-c', '--conf'):
            # read manage alternative config
            file_config = arg
        elif opt in ('-f', '--format'):
            frmt = arg
        elif opt in ('-o', '--color'):
            color = arg            

    # load configuration
    if os.path.exists(file_config):
        auth_config = load_config(file_config)
    else:
        auth_config = {
            u'log':u'./',
            u'endpoint':None
        }
    auth_config[u'color'] = color
    
    # setup loggers
    loggers = [
        logger,
        logging.getLogger(u'beecell'),
        #logging.getLogger(u'sqlalchemy'),
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beedrones'),
    ]
    lfrmt = u'%(asctime)s - %(levelname)s - ' \
            u'%(name)s.%(funcName)s:%(lineno)d - %(message)s'
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                      u'%smanage.log' % auth_config[u'log'], 
                                      1024*1024, 5, lfrmt,
                                      formatter=ColorFormatter)
    
    loggers = [
        logging.getLogger(u'beecell.perf')
    ]
    LoggerHelper.rotatingfile_handler(loggers, logging.ERROR, 
                                      u'%smanage.watch.log' % auth_config[u'log'], 
                                      1024*1024, 5, lfrmt)

    # check section
    try:
        section = args.pop(0)
    except:
        print(ComponentManager.__doc__)
        print(main.__doc__)
        return 0

    try:
        manager = main
        
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
            retcode = AuthManager.main(auth_config, frmt, opts, args, env, 
                                       AuthManager)

        elif section == u'event':
            manager = EventManager
            retcode = EventManager.main(auth_config, frmt, opts, args, env, 
                                        EventManager)

        elif section == u'monitor':
            manager = MonitorManager
            retcode = MonitorManager.main(auth_config, frmt, opts, args, env, 
                                          MonitorManager)
            
        elif section == u'resource':
            manager = ResourceManager
            retcode = ResourceManager.main(auth_config, frmt, opts, args, env, 
                                           ResourceManager)
            
        elif section == u'scheduler':
            manager = SchedulerManager
            try: subsystem = args.pop(0)
            except:
                raise Exception(u'ERROR : Container id is missing')  
            retcode = SchedulerManager.main(auth_config, frmt, opts, args, env, 
                                            SchedulerManager, subsystem=subsystem)
            
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
            raise Exception(u'ERROR : Specify a section')
                    
    except Exception as ex:
        line = [u'='] * 50
        print(bcolors.FAIL + bcolors.BOLD + u'    ' + u''.join(line))
        print(u'     %s' % (ex))
        print(u'    ' + u''.join(line) + bcolors.ENDC)        
        print(ComponentManager.__doc__)
        print(bcolors.OKBLUE + manager.__doc__ + bcolors.ENDC)
        logger.error(ex, exc_info=1)
        retcode = 1
    
    return retcode

if __name__ == u'__main__':    
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)
    