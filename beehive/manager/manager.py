#!/usr/bin/env python
'''
@author: darkbk

use: init_beehive.py <cmd> PARAMS

cmd: 
    configure <component> - setup beehive server instances cofigurations.
                            <component> : apicore|resource|service|bpm
    configure-portal      - setup portal server instances cofigurations
    auth                  - setup beehive auth module and main roles and users
    catalog               - setup beehive catalog module
    config                - setup beehive config module
    resource              - setup beehive resource module
    platform              - setup beehive platform module
    service               - setup beehive service module
    process               - setup beehive process module
    event                 - setup beehive event module
    admin                 - setup cloduapi admin module
    scheduler             - setup cloduapi scheduler module
    apicore               - setup beehive config, amdin, event, scheduler modules
    bpm                   - setup cloduapi bpm module
    monitor               - setup cloduapi monitor module
    plugin <module> <plugin class fullpath>
              - setup beehive plugin
    
    init
    
    update
            resource      - update resource db and related data
            monitor       - update monitor db and related data
'''
import os
#os.environ[u'GEVENT_RESOLVER'] = u'ares'
import gevent.monkey
gevent.monkey.patch_all()
import sys
import env
import logging
import traceback
import getopt
import ujson as json
from beecell.logger import LoggerHelper
from gibbonbeehive.module.base import ApiManager
from gibbonbeehive.util.data import operation
from beecell.simple import import_class, dynamic_import
from beecell.simple import id_gen

from manage.config import *
from manage.permission import perms

VERSION = 0.1

containers = []

def init_auth(logger, db_uri):
    # create configuration tables
    try:
        from gibbonbeehive.common import ConfigDbManager 
        
        # create api manager
        params = {'api_name':'auth',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.process.mod.ConfigModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)        

        # remove and create scchema
        ConfigDbManager.remove_table(db_uri)
        ConfigDbManager.create_table(db_uri)

        # create session
        operation.session = manager.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # create db manager
        config = ConfigDbManager()
        
        # set configurations
        #
        # populate table for beehive
        #
        app = 'beehive'
        
        # - redis
        #res = config.add(app, 'redis', 'redis_01', '10.102.47.208;6379;0')
        res = config.add(app, 'redis', 'redis_01', redis_uri)
        logger.info('Add redis configuration: %s' % res)

        # - mail server
        #res = config.add(app, 'redis', 'redis_01', '10.102.47.208;6379;0')
        res = config.add(app, 'mail', 'server1', mail_server)
        logger.info('Add mail server configuration: %s' % res)
        res = config.add(app, 'mail', 'sender1', mail_sender)
        logger.info('Add mail sender configuration: %s' % res)        
        
        # - authentication domains
        for auth in auths:          
            res = config.add(app, 'auth', auth['domain'], json.dumps(auth)) 
            logger.debug('Add auth domain: %s' % res)
        
        # - beehive queue        
        for queue in queues:
            res = config.add('beehive', 'queue', queue['name'], json.dumps(queue))
            logger.debug('Add queue: %s' % res)        
        
        # - tcp proxy
        #res = config.add('beehive', 'tcpproxy', 'proxy01', '10.102.47.208')
        #logger.debug('Add tcp proxy: %s' % res)    
    
        # - http proxy
        #res = config.add('beehive', 'httpproxy', 'proxy02', 'http://10.102.162.5:3128')
        #logger.debug('Add http proxy: %s' % res)
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        manager.release_session(operation.session)
        operation.session = None
    
    try:
        from gibbonbeehive.module.auth.model import AuthDbManager        
        
        # create api manager
        params = {'api_name':'auth',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.auth.mod.AuthModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # remove and create scchema
        AuthDbManager.remove_table(db_uri)
        AuthDbManager.create_table(db_uri)
    
        # create module
        auth_module = manager.modules['AuthModule']
        controller = auth_module.get_controller()
        
        # create session
        operation.session = auth_module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # init module
        auth_module.init_object()

        # add superadmin role
        perms_to_assign = auth_module.get_controller().get_superadmin_permissions()
        controller.add_superadmin_role(perms_to_assign)
    
        # add guest role
        controller.add_guest_role()
    
        # add superadmin role
        name = 'admin@local'
        storetype = 'DBUSER'
        systype = 'USER'
        profile = 'system'
        active = True
        password = 'testlab'
        description = 'Super Administrator'
        attribute = ''
        user = controller.add_user(name, storetype, systype, active=active, 
                                   password=password, description=description)
        #user = controller.get_users(name)[0]
        user.append_role('ApiSuperadmin')
    
        # create users
        user = controller.add_generic_user('test1@local', 'DBUSER', 'testlab')
        #user = controller.get_users('test1@local')[0]
        #user.append_role('clsk44_209Admin')
    
        user = controller.add_generic_user('test2@local', 'DBUSER', 'testlab')
        #user = controller.get_users('test2@local')[0]
        #user.append_role('clsk44_209Admin')
        
        controller.add_system_user(api_user['name'], password=api_user['pwd'], 
                                   description='api user all modules')
          
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        auth_module.release_session(operation.session)
        operation.session = None

def init_catalog(logger, db_uri):
    # create configuration tables
    try:
        from gibbonbeehive.module.catalog.model import CatalogDbManager 
        
        # create api manager
        params = {'api_name':'catalog',
                  'api_id':'auth',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.catalog.mod.CatalogModule'],
                  'api_plugin':[],
                  'api_subsystem':'catalog'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()

        # remove and create scchema
        CatalogDbManager.remove_table(db_uri)
        CatalogDbManager.create_table(db_uri)
        
        # create module
        catalog_module = manager.modules['CatalogModule']
        controller = catalog_module.get_controller()

        # create session
        operation.session = manager.get_session()
        operation.perms = perms
        operation.user = authuser

        # init module
        catalog_module.init_object()
        
        cat1 = controller.add_catalog(catalog1['name'],
                                      catalog1['desc'], 
                                      catalog1['use'])
        cat = controller.get_catalogs(oid=cat1)[0]
        for s in services1:
            cat.add_service(s['name'], s['type'], s['desc'], s['uri'])
        
        cat2 = controller.add_catalog(catalog2['name'],
                                      catalog2['desc'], 
                                      catalog2['use'])
        cat = controller.get_catalogs(oid=cat2)[0]
        for s in services2:
            cat.add_service(s['name'], s['type'], s['desc'], s['uri'])        
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        manager.release_session(operation.session)
        operation.session = None

def configure(logger, db_uri):
    try:
        from gibbonbeehive.common import ConfigDbManager 
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.process.mod.ConfigModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)        

        # remove and create scchema
        ConfigDbManager.remove_table(db_uri)
        ConfigDbManager.create_table(db_uri)

        # create session
        operation.session = manager.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # create db manager
        config = ConfigDbManager()
        
        # set configurations
        #
        # populate table for beehive
        #
        app = 'beehive'
        
        # - api user
        res = config.add(app, 'auth', 'api_user', json.dumps(api_user))
        logger.info('Add api user configuration: %s' % res)        
        
        # - redis
        #res = config.add(app, 'redis', 'redis_01', '10.102.47.208;6379;0')
        res = config.add(app, 'redis', 'redis_01', redis_uri)
        logger.info('Add redis configuration: %s' % res)
        
        # - task manager
        res = config.add(app, 'taskmanager', 'task_broker_url', task_broker_url)
        res = config.add(app, 'taskmanager', 'task_result_backend', task_result_backend)
        logger.info('Add task manager configuration: %s' % res)        
        
        # - scheduler
        res = config.add(app, 'scheduler', 'scheduler_broker_url', scheduler_broker_url)
        res = config.add(app, 'scheduler', 'scheduler_result_backend', scheduler_result_backend)
        logger.info('Add scheduler configuration: %s' % res)        
        
        # - tcp proxy
        res = config.add('beehive', 'tcpproxy', 'proxy01', '10.102.47.208')
        logger.debug('Add tcp proxy: %s' % res)    
    
        # - http proxy
        res = config.add('beehive', 'httpproxy', 'proxy02', 'http://10.102.162.5:3128')
        logger.debug('Add http proxy: %s' % res)
        
        # - endpoint
        for endpoint in endpoints:
            res = config.add('beehive', 'endpoint', endpoint['name'], 
                             json.dumps(endpoint))
            logger.debug('Add endpoint: %s' % res)
        
        # - gateway
        for gw in gateways:
            res = config.add('beehive', 'gateway', gw['name'], 
                             json.dumps(gw))
            logger.debug('Add gateway: %s' % res)        
        
        # - beehive queue        
        for queue in queues:
            res = config.add('beehive', 'queue', queue['name'], json.dumps(queue))
            logger.debug('Add queue: %s' % res)      
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        manager.release_session(operation.session)
        operation.session = None
        
def configure_portal(logger, db_uri):
    try:
        from gibbonbeehive.common import ConfigDbManager 
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.process.mod.ConfigModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)        

        # create session
        operation.session = manager.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # create db manager
        config = ConfigDbManager()
        
        # set configurations
        #
        # populate table for portal
        #
        app = 'portal'
        
        '''
        # log
        logconf = {'gibbon.portal':('DEBUG', 'log/portal2.log'),
                   'gibbon.beehive':('DEBUG', 'log/portal2.log'),
                   'gibbon.cloud':('DEBUG', 'log/portal2.log'),
                   'gibbon.util':('DEBUG', 'log/portal2.log'),
                   'gibbon.util.watch':('DEBUG', 'log/portal2.watch.log', 
                                        '%(asctime)s - %(message)s')}
        num = 0
        for log_name, log_conf in logconf.iteritems():
            name = "logger_portal%s" % num
            res = config.add_log_config(app, name, log_name, log_conf)
            logger.debug('Add logger: %s' % res)
            num += 1
        '''
        
        # http_timeout
        res = config.add(app, 'http', 'http_timeout', 30)
        logger.debug('Add http timeout: %s' % res)
        
        # flask secret key
        #res = manager.set_config(app, 'flask', 'flask_secret_key', urandom(80))
        #logger.debug('Add flask secret key: %s' % res)    
        
        # flask babel
        res = config.add(app, 'flask-babel', 'default_locale', 'it')
        logger.debug('Add flask babel default locale: %s' % res)
        res = config.add(app, 'flask-babel', 'default_timezone', 'utc')
        logger.debug('Add flask babel default timezone: %s' % res)
        langs = {
            'en': 'English',
            'it': 'Italian',
        }
        res = config.add(app, 'flask-babel', 'languages', json.dumps(langs))
        logger.debug('Add flask babel languges: %s' % res)            
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        manager.release_session(operation.session)
        operation.session = None

def init_config(logger, db_uri):
    try:
        #from gibbonbeehive.common.auth import AuthDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.config.mod.ConfigModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # create module
        conf_module = manager.modules['ConfigModule']
        controller = conf_module.get_controller()
        
        # create session
        operation.session = conf_module.get_session()
        operation.perms = perms
        operation.user = authuser 
        
        # init module
        conf_module.init_object()
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        conf_module.release_session(operation.session)
        operation.session = None

def init_process(logger, db_uri):
    try:
        from gibbonbeehive.module.process.model import ProcessDbManager
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.process.mod.ProcessModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()

        # remove and create scchema
        ProcessDbManager.remove_table(db_uri)
        ProcessDbManager.create_table(db_uri)
    
        # create module
        process_module = manager.modules['ProcessModule']
        controller = process_module.get_controller()
        
        # create session
        operation.session = process_module.get_session()
        operation.perms = perms
        operation.user = authuser     
        
        # init module
        process_module.init_object()

        # register main task type
        proc_manager = ProcessDbManager()
        proc_manager.add_task_type('start', 'gibbonbeehive.common.process.StartTask', type='SYS', desc='')
        proc_manager.add_task_type('stop', 'gibbonbeehive.common.process.StopTask', type='SYS', desc='')
        proc_manager.add_task_type('task1', 'gibbonbeehive.common.process.UserTask', type='USER', desc='')
        
        # create dummy process
        controller.create_dummy_process() 
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        process_module.release_session(operation.session)
        operation.session = None

def init_event(logger, db_uri):
    try:
        from gibbonbeehive.module.event.model import EventDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.event.mod.EventModule'],
                  'api_plugin':[],
                  'api_subsystem':'process'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
        
        # remove and create scchema
        EventDbManager.remove_table(db_uri)
        EventDbManager.create_table(db_uri)
    
        # create module
        event_module = manager.modules['EventModule']
        controller = event_module.get_controller()
        
        # create session
        operation.session = event_module.get_session()
        operation.perms = perms
        operation.user = authuser 
        
        # init module
        event_module.init_object()  
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        event_module.release_session(operation.session)
        operation.session = None

def init_monitor(logger, db_uri, update=False):
    try:
        from gibbonbeehive.module.monitor.model import MonitorDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'monitor',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.monitor.mod.MonitorModule'],
                  'api_plugin':[],
                  'api_subsystem':'monitor'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
        
        # remove and create scchema
        if update is False:
            MonitorDbManager.remove_table(db_uri)
        MonitorDbManager.create_table(db_uri)
    
        # create module
        module = manager.modules['MonitorModule']
        controller = module.get_controller()
        
        # create session
        operation.session = module.get_session()
        operation.perms = perms
        operation.user = authuser 
        
        # init module
        module.init_object()
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        module.release_session(operation.session)
        operation.session = None

def init_scheduler(logger, db_uri):
    try:
        #from gibbonbeehive.module.event.model import EventDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.scheduler.mod.SchedulerModule'],
                  'api_plugin':[],
                  'api_subsystem':'scheduler'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
        
        # remove and create scchema
        #EventDbManager.remove_table(db_uri)
        #EventDbManager.create_table(db_uri)
    
        # create module
        scheduler_module = manager.modules['SchedulerModule']
        #controller = scheduler_module.get_controller()
        
        # create session
        operation.session = scheduler_module.get_session()
        operation.perms = perms
        operation.user = authuser 
        
        # init module
        scheduler_module.init_object()  
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        scheduler_module.release_session(operation.session)
        operation.session = None

def init_platform(logger, db_uri):
    try:
        from gibbonbeehive.module.platform.model import PlatformDbManager
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'platform',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.platform.mod.PlatformModule'],
                  'api_plugin':[],
                  'api_subsystem':'platform'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
        
        # remove and create scchema
        PlatformDbManager.remove_table(db_uri)
        PlatformDbManager.create_table(db_uri)
    
        # create module
        platorm_module = manager.modules['PlatformModule']
        #controller = scheduler_module.get_controller()
        
        # create session
        operation.session = platorm_module.get_session()
        operation.perms = perms
        operation.user = authuser 
        
        # init module
        platorm_module.init_object()  
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        platorm_module.release_session(operation.session)
        operation.session = None

def init_resource(logger, db_uri):
    try:
        from gibbonbeehive.module.resource.model import ResourceDbManager
        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.resource.mod.ResourceModule'],
                  'api_plugin':[],
                  'api_subsystem':'resource'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # remove and create scchema
        ResourceDbManager.remove_table(db_uri)
        ResourceDbManager.create_table(db_uri)
    
        # create module
        #from gibbonbeehive.module.resource.mod import ResourceModule
        #from gibbonbeehive.module.resource.plugins.cloudstack import CloudstackPlugin
        #resource_module = ResourceModule(manager)
        #CloudstackPlugin(resource_module).register()
        resource_module = manager.modules['ResourceModule']
        controller = resource_module.get_controller()
        
        # create session
        operation.session = resource_module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # init module
        resource_module.init_object()
        
        controller = resource_module.get_controller()
        for item in containers:
            container_class = import_class(item['class'])
            container = container_class(controller, objid=id_gen(), 
                                        name=item['name'], desc=item['desc'], 
                                        active=True, 
                                        connection=json.dumps(item['conn']))        
            controller.add_container(container)        
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        resource_module.release_session(operation.session)
        operation.session = None

def update_resource(logger, db_uri):
    try:
        from gibbonbeehive.module.resource.model import ResourceDbManager
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'resource',
                  'http-socket':None,
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.resource.mod.ResourceModule'],
                  'api_plugin':[#'ResourceModule,gibbonbeehive.module.resource.plugins.vsphere.VspherePlugin',
                                'ResourceModule,gibbonbeehive.module.resource.plugins.openstack.OpenstackPlugin',
                                #'ResourceModule,gibbonbeehive.module.resource.plugins.tenant.TenantPlugin',
                               ],
                  'api_subsystem':'resource'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # remove and create scchema
        #ResourceDbManager.remove_table(db_uri)
        ResourceDbManager.create_table(db_uri)

        # create module
        resource_module = manager.modules['ResourceModule']
        #controller = service_module.get_controller()
        
        # create session
        operation.session = resource_module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # init module
        resource_module.init_object()

        #role = 'ApiSuperadmin'
        # add resource tag permission object
        
        '''
        objdef = 'tag'
        class_name = 'gibbonbeehive.module.resource.container.ResourceTag'
        desc = 'All the resource tags'
        objaction = '*'
        objid = '*'
        manager.api_client.add_object_types(objtype, objdef, class_name)
        manager.api_client.add_object(objtype, objdef, objid, desc)
        manager.api_client.append_role_permissions(role, objtype, objdef, objid, objaction)
        objtype = 'event'
        manager.api_client.add_object_types(objtype, objdef, class_name)
        manager.api_client.add_object(objtype, objdef, objid, desc)
        manager.api_client.append_role_permissions(role, objtype, objdef, objid, objaction)
        '''
        '''
        objdefs = ['vsphere.nsx', 
                   'vsphere.nsx.logical_switch', 
                   'vsphere.nsx.security_group', 
                   'vsphere.nsx.dlr', 
                   'vsphere.nsx.edge', 
                   'openstack.domain.project.security_group']
        class_names = ['gibbonbeehive.module.resource.plugins.vsphere.container.NsxManager',
                       'gibbonbeehive.module.resource.plugins.vsphere.container.container.NsxLogicalSwitch',
                       'gibbonbeehive.module.resource.plugins.vsphere.container.container.NsxSecurityGroup',
                       'gibbonbeehive.module.resource.plugins.vsphere.container.container.NsxDlr',
                       'gibbonbeehive.module.resource.plugins.vsphere.container.container.NsxEdge',
                       'gibbonbeehive.module.resource.plugins.openstack.container.container.OpenstackSecurityGroup']
        descs = ['All the nsx managers',
                 'All the nsx logical switches',
                 'All the nsx security groups',
                 'All the nsx dlrs',
                 'All the nsx edges',
                 'All the openstack security groups']
        objaction = '*'
        objid = '*'
        n = 0
        for objdef in objdefs:
            objtype = 'resource'
            manager.api_client.add_object_types(objtype, objdef, class_names[n])
            manager.api_client.add_object(objtype, objdef, objid, descs[n])
            manager.api_client.append_role_permissions(role, objtype, objdef, objid, objaction)
            objtype = 'event'
            manager.api_client.add_object_types(objtype, objdef, class_names[n])
            manager.api_client.add_object(objtype, objdef, objid, descs[n])
            manager.api_client.append_role_permissions(role, objtype, objdef, objid, objaction)
            n += 1          
        '''

    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        resource_module.release_session(operation.session)
        operation.session = None

def init_service(logger, db_uri):
    try:
        from gibbonbeehive.module.service.model import ServiceDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.service.mod.ServiceModule'],
                  'api_plugin':['ServiceModule,gibbonbeehive.module.service.plugins.test.TestServicePlugin'],
                  'api_subsystem':'service'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # remove and create scchema
        ServiceDbManager.remove_table(db_uri)
        ServiceDbManager.create_table(db_uri)
    
        # create module
        service_module = manager.modules['ServiceModule']
        #controller = service_module.get_controller()
        
        # create session
        operation.session = service_module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # init module
        service_module.init_object()
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        service_module.release_session(operation.session)
        operation.session = None

def init_admin(logger, db_uri):
    try:
        #from gibbonbeehive.common.auth import AuthDbManager        
        
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.admin.mod.AdminModule'],
                  'api_plugin':[],
                  'api_subsystem':'admin'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()
    
        # remove and create scchema
        #AuthDbManager.remove_table(db_uri)
        #AuthDbManager.create_table(db_uri)
    
        # create module
        admin_module = manager.modules['AdminModule']
        controller = admin_module.get_controller()
        
        # create session
        operation.session = admin_module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        # init module
        admin_module.init_object()  
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        admin_module.release_session(operation.session)
        operation.session = None

def register_service_plugin(logger, db_uri, plugin_class_name):
    try:
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.service.mod.ServiceModule'],
                  'api_plugin':[],
                  'api_subsystem':'service'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()

        # create module
        module = manager.modules['ServiceModule']
    
        # import plugin
        operation.session = module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        plugin_class = import_class(plugin_class_name)
        plugin = plugin_class(module)
        plugin.init()
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        module.release_session(operation.session)
        operation.session = None
        
def register_resource_plugin(logger, db_uri, plugin_class_name):
    try:
        # create api manager
        params = {'api_name':'beehive',
                  'api_id':'process',
                  'database_uri':db_uri,
                  'api_module':['gibbonbeehive.module.resource.mod.ResourceModule'],
                  'api_plugin':[],
                  'api_subsystem':'resource'}
        manager = ApiManager(params)
        manager.configure()
        manager.register_modules()

        # create module
        module = manager.modules['ResourceModule']
    
        # import plugin
        operation.session = module.get_session()
        operation.perms = perms
        operation.user = authuser
        
        plugin_class = import_class(plugin_class_name)
        plugin = plugin_class(module)
        plugin.init()
    except:
        msg = traceback.format_exc()
        logger.error(msg)
    finally:
        # release session
        module.release_session(operation.session)
        operation.session = None        

def main(run_path, argv):
    cmd = None
    p = None
    retcode = 0
    
    try:
        opts, args = getopt.getopt(argv,"c:hv",["help", "cmd=",
                                                "version"])
    except getopt.GetoptError:
        print __doc__
        return 2
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            return 0
        elif opt in ("-v", "--version"):
            print "auth %s" % VERSION
            return 0        
        elif opt in ("-c", "--cmd"):
            cmd = arg

    try:
        cmd = args[0]
    except:
        print __doc__
        return 0
    
    # configure logger
    logger = logging.getLogger('gibbonbeehive')
    #frmt = "%(asctime)s - %(message)s" 
    LoggerHelper.setup_simple_handler(logger, logging.DEBUG, frmt=None)
    logger = logging.getLogger('beecell')
    #frmt = "%(asctime)s - %(message)s" 
    LoggerHelper.setup_simple_handler(logger, logging.DEBUG, frmt=None)

    logger = logging.getLogger('beecell.perf')
    LoggerHelper.setup_simple_handler(logger, logging.WARN, frmt=None)
    logger = logging.getLogger('beecell.watch')
    LoggerHelper.setup_simple_handler(logger, logging.WARN, frmt=None)
    logger = logging.getLogger('gibbonbeehive.module.base.ApiClient')
    LoggerHelper.setup_simple_handler(logger, logging.WARN, frmt=None)
    logger = logging.getLogger('gibbonbeehive.util.auth.AuthClient')
    LoggerHelper.setup_simple_handler(logger, logging.WARN, frmt=None)

    if (cmd == 'configure'):
        comp = args[1]
        configure(logger, db_uri[comp])
    elif (cmd == 'configure-portal'):
        configure_portal(logger, db_uri['apicore'])        
    elif (cmd == 'auth'):
        init_auth(logger, db_uri['auth'])
    elif (cmd == 'catalog'):
        init_catalog(logger, db_uri['auth'])        
    elif (cmd == 'apicore'):
        init_config(logger, db_uri['apicore'])
        init_admin(logger, db_uri['apicore'])
        #init_process(logger, db_uri['apicore'])
        init_event(logger, db_uri['apicore'])
        init_scheduler(logger, db_uri['apicore'])
    elif (cmd == 'config'):
        init_config(logger, db_uri['apicore'])
    elif (cmd == 'admin'):
        init_admin(logger, db_uri['apicore'])   
    elif (cmd == 'resource'):
        init_resource(logger, db_uri['resource'])
    elif (cmd == 'platform'):
        init_platform(logger, db_uri['resource'])
    elif (cmd == 'service'):
        init_service(logger, db_uri['service'])
    elif (cmd == 'event'):
        init_event(logger, db_uri['apicore'])
    elif (cmd == 'monitor'):
        init_monitor(logger, db_uri['monitor'])        
    elif (cmd == 'scheduler'):
        init_scheduler(logger, db_uri['apicore'])
    elif (cmd == 'plugin'):
        try:
            module = args[1]
            plugin_class_name = args[2]
        except:
            print __doc__
            return 0
        if module == 'service':
            register_service_plugin(logger, db_uri['service'], plugin_class_name)
        elif module == 'resource':
            register_resource_plugin(logger, db_uri['resource'], plugin_class_name)
    elif (cmd == 'ping'):
        '''
        endpoint = endpoints[0]
        print '%s:%s' % (endpoint['host'], endpoint['port'][1])
        res = uwsgi_util.rpc('%s:%s' % (endpoint['host'], endpoint['port'][1]), 
                             'ping')
        print res
        '''
        manager = ApiManager(None)
        dbconf = (db_uri, 5)
        manager.create_simple_engine(dbconf)
        for endpoint in endpoints:
            manager.endpoints[endpoint['name']] = endpoint
        
        print manager.rpc_client.ping_auth()
    
    elif (cmd == u'update'):
        module = args[1]
        
        if (module == u'resource'):
            update_resource(logger, db_uri[u'resource'])
        elif (module == u'monitor'):
            init_monitor(logger, db_uri[u'monitor'], update=True)              

if __name__ == '__main__':
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)
