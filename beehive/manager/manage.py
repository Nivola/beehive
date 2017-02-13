#!/usr/bin/env python
'''
use: manage.py <otions> <cmd> PARAMS

options:
    -c --config: json auth config file
    -f --format: outpute format

section:
    test redis <host>
    test mysql <host> <user> <pwd> <db>
    test beehive <host> <port>
    
    subsystem <subsystem> <config-file>
        subsystem: auth, catalog, apicore, resource, tenant, monitor, service
        config-file: json file like
            {
                'api_system':'beehive',
                'api_subsystem':'auth',
                'api_modules':['beehive.module.auth.mod.AuthModule'],
                'api_plugins':[],
                'db_uri':'mysql+pymysql://auth:auth@localhost:3306/auth',
                'db_manager':'beehive.module.auth.model.AuthDbManager',  
                'config':[
                   {'group':'redis', 'name':'redis_01', 'value':'redis://localhost:6379/0'},
                   ...
                ],
                'user':{'type':'admin', 'name':'admin@local', 'pwd':'..', 'desc':'Super Administrator'},
                'user':{'type':'user', 'name':'test1@local', 'pwd':'..', 'desc':'Test user 1'},
                'user':{'type':'user', 'name':'test2@local', 'pwd':'..', 'desc':'Test user 2'},                
            }
            
    client <config-file>
        config-file: json file like
            {
                'name':'portla-01',
                'type':'portal',
                "object_types":[],
                "objects":[],
                "roles":[],
                "users":[]             
            }    
            
    auth <entity> <op>
        entity: user, role, object
        op: list, get, add, delete
        
        auth catalog
        auth catalog get <id>
        auth catalog add <name> <zone>
        auth catalog delete <id>
        
        auth endpoint add <name> <catalog_id> <subsystem> <uri=http://localhost:3030>
        auth endpoint delete <id>
        
        auth perm
        auth object
        auth role
        auth role get <name>
        auth user
        auth user get <name>
        auth user add_system <name> <pwdd> <desc> 

Created on Jan 9, 2017

@author: darkbk
'''
import os, sys
import logging
import getopt

VERSION = u'1.0.0'

def main(run_path, argv):
    """
    """
    # setup pythonpath
    sys.path.append(os.path.expanduser("~/workspace/git/beecell"))
    sys.path.append(os.path.expanduser("~/workspace/git/beedrones"))
    sys.path.append(os.path.expanduser("~/workspace/git/beehive"))
    sys.path.append(os.path.expanduser("~/workspace/git/gibboncloudapi"))     
    
    from beecell.logger.helper import LoggerHelper
    
    # imports
    import ujson as json
    from beehive.manager.ops.platform import platform_main
    from beehive.manager.ops.auth import auth_main
    from beehive.manager.ops.create import create_main
    from beehive.manager.ops.create import create_client
    from beehive.manager.ops.monitor import monitor_main
    from beehive.manager.ops.resource import resource_main
    from beehive.manager.ops.scheduler import scheduler_main
    from beehive.manager.ops.provider import provider_main
    
    cmd = None
    p = None
    retcode = 0
    format = u'text'
    
    auth_config = {u'log':u'./',
                   u'endpoint':None}
    
    try:
        opts, args = getopt.getopt(argv,"c:f:hv",["help", "conf=", 'format=',
                                                "version"])
    except getopt.GetoptError:
        print __doc__
        return 2
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print __doc__
            return 0
        elif opt in ('-v', '--version'):
            print 'auth %s' % VERSION
            return 0        
        elif opt in ('-c', '--conf'):
            # read subsystem config
            file_config = arg
            f = open(file_config, 'r')
            auth_config = f.read()
            auth_config = json.loads(auth_config)
            f.close()
        elif opt in ('-f', '--format'):
            format = arg

    logger = logging.getLogger(__name__)

    # setup loggers
    loggers = [
        logger,
        logging.getLogger(u'beecell'),
        #logging.getLogger(u'sqlalchemy'),
        logging.getLogger(u'beehive'),
    ]
    frmt = u'%(asctime)s - %(levelname)s - ' \
           u'%(name)s.%(funcName)s:%(lineno)d - %(message)s'
    LoggerHelper.rotatingfile_handler(loggers, logging.DEBUG, 
                                      u'%smanage.log' % auth_config[u'log'], 
                                      1024*1024, 5, frmt)
    
    loggers = [
        logging.getLogger(u'beecell.perf')
    ]
    LoggerHelper.rotatingfile_handler(loggers, logging.ERROR, 
                                      u'%smanage.watch.log' % auth_config[u'log'], 
                                      1024*1024, 5, frmt)

    try:
        section = args.pop(0)
    except:
        print __doc__
        return 0

    try:
        if section == u'platform':
            retcode = platform_main(auth_config, format, opts, args)
    
        elif section == u'subsystem':
            retcode = create_main(auth_config, format, args)
        
        elif section == u'client':
            retcode = create_client(auth_config, format, args)
                
        elif section == u'auth':
            retcode = auth_main(auth_config, format, args)
            
        elif section == u'monitor':
            retcode = monitor_main(auth_config, format, opts, args)
            
        elif section == u'resource':
            retcode = resource_main(auth_config, format, opts, args)            
            
        elif section == u'scheduler':
            retcode = scheduler_main(auth_config, format, opts, args) 
            
        elif section == u'provider':
            retcode = provider_main(auth_config, format, opts, args) 
                    
    except Exception as ex:
        print(u'ERROR : %s' % (ex))
        logger.error(ex, exc_info=1)
        retcode = 1
    
    return retcode

if __name__ == u'__main__':    
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)
    