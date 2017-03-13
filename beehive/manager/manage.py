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

def load_config(file_config):
    f = open(file_config, 'r')
    auth_config = f.read()
    auth_config = json.loads(auth_config)
    f.close()
    return auth_config

def main(run_path, argv):
    """
    CMDs:
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
    sys.path.append(os.path.expanduser(u'~/workspace/git/beecell'))
    sys.path.append(os.path.expanduser(u'~/workspace/git/beedrones'))
    sys.path.append(os.path.expanduser(u'~/workspace/git/beehive'))
    sys.path.append(os.path.expanduser(u'~/workspace/git/gibboncloudapi'))     
    
    from beecell.logger.helper import LoggerHelper
    
    # imports
    from beehive.manager import ComponentManager
    from beehive.manager.ops.platform import PlatformManager
    from beehive.manager.ops.provider import ProviderManager
    from beehive.manager.ops.resource import ResourceManager
    from beehive.manager.ops.scheduler import SchedulerManager
    from beehive.manager.ops.vsphere import VsphereManager
    from beehive.manager.ops.native_vsphere import NativeVsphereManager
    
    from beehive.manager.ops.platform import platform_main
    from beehive.manager.ops.auth import auth_main
    from beehive.manager.ops.create import create_main
    from beehive.manager.ops.create import create_client
    from beehive.manager.ops.monitor import monitor_main
    from beehive.manager.ops.scheduler import scheduler_main
    

    
    logger = logging.getLogger(__name__)
    file_config = u'./manage.conf'
    cmd = None
    p = None
    retcode = 0
    frmt = u'text'
    env = u'test'
    
    try:
        opts, args = getopt.getopt(argv,"c:f:e:hv",
                                   ["help", "conf=", 'format=', 'env=', 
                                    "version"])
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

    # load configuration
    if os.path.exists(file_config):
        auth_config = load_config(file_config)
    else:
        auth_config = {
            u'log':u'./',
            u'endpoint':None
        }        
    
    # setup loggers
    loggers = [
        logger,
        logging.getLogger(u'beecell'),
        #logging.getLogger(u'sqlalchemy'),
        logging.getLogger(u'beehive'),
    ]
    lfrmt = u'%(asctime)s - %(levelname)s - ' \
            u'%(name)s.%(funcName)s:%(lineno)d - %(message)s'
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                      u'%smanage.log' % auth_config[u'log'], 
                                      1024*1024, 5, lfrmt)
    
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
        if section == u'platform':
            retcode = PlatformManager.main(auth_config, frmt, opts, args, env, 
                                           PlatformManager)
    
        elif section == u'subsystem':
            retcode = create_main(auth_config, frmt, args)
        
        elif section == u'client':
            retcode = create_client(auth_config, frmt, args)
                
        elif section == u'auth':
            retcode = auth_main(auth_config, frmt, args)
            
        elif section == u'monitor':
            retcode = monitor_main(auth_config, frmt, opts, args)
            
        elif section == u'resource':
            retcode = ResourceManager.main(auth_config, frmt, opts, args, env, 
                                           ResourceManager)         
            
        elif section == u'scheduler':
            try: subsystem = args.pop(0)
            except:
                print(ComponentManager.__doc__)
                print(main.__doc__)
                return 0
            retcode = SchedulerManager.main(auth_config, frmt, opts, args, env, 
                                            SchedulerManager, subsystem=subsystem)
            
        elif section == u'provider':
            try: cid = args.pop(0)
            except:
                print(ComponentManager.__doc__)
                print(main.__doc__)
                return 0                
            retcode = ProviderManager.main(auth_config, frmt, opts, args, env, 
                                           ProviderManager, containerid=cid)
            
        elif section == u'vsphere':
            try: cid = args.pop(0)
            except:
                raise Exception(u'ERROR : Orchestrator id is missing')              
            retcode = VsphereManager.main(auth_config, frmt, opts, args, env, 
                                          VsphereManager, containerid=cid)
            
        elif section == u'native.vsphere':
            try: cid = args.pop(0)
            except:
                raise Exception(u'ERROR : Platform id is missing')              
            retcode = NativeVsphereManager.main(auth_config, frmt, opts, args, env, 
                                                NativeVsphereManager, 
                                                orchestrator_id=cid) 
                    
    except Exception as ex:
        print(u'ERROR : %s' % (ex))
        print(ComponentManager.__doc__)
        print(main.__doc__)
        logger.error(ex, exc_info=1)
        retcode = 1
    
    return retcode

if __name__ == u'__main__':    
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)
    