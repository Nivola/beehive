# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import logging
from uuid import uuid4
from six import b
import ujson as json
import datetime

from beehive.common.apimanager import ApiManager
from beehive.common.data import operation
from beecell.simple import import_class, random_password, get_value
from beehive.module.auth.controller import Objects, Role, User, Group
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.module.catalog.controller import Catalog, CatalogEndpoint
from beehive.common.model.config import ConfigDbManager
from beecell.db.manager import RedisManager
from beecell.db import QueryError


try:
    import json
except ImportError:
    import simplejson as json


class BeehiveHelper(object):
    """Beehive subsystem manager helper.
    
    """
    classes = [
        Objects,
        Role,
        User,
        Group,
        Catalog,
        CatalogEndpoint
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__+  '.' + self.__class__.__name__)
    
    def get_permission_id(self, objdef):
        """Get operation objid
        """
        temp = objdef.split('.')
        ids = ['*' for i in temp]
        return '//'.join(ids)
    
    def set_permissions(self, classes=[]):
        """Set user operations
        
        :param classes: list of classes to include in perms
        """
        try:
            operation.perms = []
            for op in classes:
                perm = (1, 1, op.objtype, op.objdef, self.get_permission_id(op.objdef), 1, '*')
                operation.perms.append(perm)
        except Exception as ex:
            raise Exception('Permissions assign error: %s' % ex)
    
    def read_config(self, filename):
        """
        """
        f = open(filename, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config    
    
    def __configure(self, config, update=True):
        """
        """
        msgs = []
        manager = None
        try:
            # create api manager
            params = {'api_id': 'server-01',
                      'api_name': config['api_system'],
                      'api_subsystem': config['api_subsystem'],
                      'database_uri': config['db_uri'],
                      'api_module': ['beehive.module.process.mod.ConfigModule'],
                      'api_plugin': []}
            manager = ApiManager(params)    
    
            # remove and create scchema
            if update is False:
                ConfigDbManager.remove_table(config['db_uri'])
            ConfigDbManager.create_table(config['db_uri'])
            self.logger.info('Create config DB %s' % (''))
            msgs.append('Create config DB %s' % (''))
    
            # create session
            operation.session = manager.get_session()
            
            # create config db manager
            db_manager = ConfigDbManager()
            
            # set configurations
            #
            # populate configs
            #
            for item in config['config']:
                # check if config already exists
                value = item['value']
                if isinstance(value, dict):
                    value = json.dumps(value)
                try:
                    res = db_manager.get(app=config['api_system'], group=item['group'], name=item['name'])
                    self.logger.warning('Configuration %s %s %s already exist' %
                                        (config['api_system'], item['group'], item['name']))
                    msgs.append('Configuration %s %s %s already exist' %
                                (config['api_system'], item['group'], item['name']))
                except QueryError as ex:
                    res = db_manager.add(config['api_system'], item['group'], item['name'], value)
                    self.logger.info('Add configuration %s' % res)
                    msgs.append('Add configuration %s' % res)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise
        finally:
            # release session
            if manager is not None:
                manager.release_session(operation.session)
            operation.session = None
            
        return msgs
    
    def __init_subsystem(self, config, update=True):
        """Init beehive subsystem
        
        :param dict config: subsystem configuration
        :param update: if update is True don't replace database schema
        :return: trace of execution
        """
        msgs = []
    
        try:
            # create api manager
            params = {'api_id': 'server-01',
                      'api_name': config['api_system'],
                      'api_subsystem': config['api_subsystem'],
                      'database_uri': config['db_uri'],
                      'redis_identity_uri': config['redis_identity_uri'],
                      'api_module': config['api_modules'],
                      'api_plugin': config['api_plugins'],
                      'api_endpoint': config['api_endpoint'],
                      'api_catalog': config['api_catalog']}
            manager = ApiManager(params)
            manager.configure()
            manager.register_modules()
    
            # create config db manager
            config_db_manager = ConfigDbManager()
    
            for db_manager_class in config['db_managers']:
                db_manager = import_class(db_manager_class)
        
                # remove and create/update scchema
                if update is False:
                    db_manager.remove_table(config['db_uri'])
                db_manager.create_table(config['db_uri'])
                self.logger.info('Create DB %s' % (db_manager_class))
                msgs.append('Create DB %s' % (db_manager_class))
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise
    
        self.set_permissions(classes=self.classes)
    
        # create module
        for item in config['api_modules']:
            try:
                self.logger.info('Load module %s' % item)
                module = manager.modules[item.split('.')[-1]]
                controller = module.get_controller()
                
                # create session
                operation.session = manager.get_session()
                
                # init module
                module.init_object()
                self.logger.info('Init module %s' % module)
                msgs.append('Init module %s' % module)
                
                # create system users and roles
                if module.name == 'AuthModule':
                    res = self.__create_main_users(controller, config, config_db_manager, update)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)
                    
                elif module.name == 'Oauth2Module':
                    controller.set_superadmin_permissions()
                    
                elif module.name == 'BasicModule':
                    controller.set_superadmin_permissions()  
                    
                elif module.name == 'CatalogModule':
                    res = self.__create_main_catalogs(controller, config, config_db_manager)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)

                elif module.name == 'ServiceModule':
                    controller.populate(config['db_uri'])
                    msgs.extend('Populate service database')
              
            except Exception as ex:
                self.logger.error(ex, exc_info=1)
                raise
            finally:
                # release session
                module.release_session(operation.session)
                operation.session = None
                
        self.logger.info('Init subsystem %s' % (config['api_subsystem']))
        msgs.append('Init subsystem %s' % (config['api_subsystem']))
        
        return msgs
    
    def __create_main_users(self, controller, config, config_db_manager, update):
        """Create auth subsystem main users
        """
        msgs = []
    
        users = config['users']
    
        if update is False:
            # add superadmin role
            # perms_to_assign = controller.get_superadmin_permissions()
            perms_to_assign = []
            controller.add_superadmin_role(perms_to_assign)
            
            # add guest role
            controller.add_guest_role()
        
        for user in users:
            # check if user already exist
            try:
                user = controller.get_user(user['name'])
                self.logger.warning('User %s already exist' % (user))
                msgs.append('User %s already exist' % (user))                  
            except:
                # create superadmin
                if user['type'] == 'admin':
                    expiry_date = datetime.datetime(2099, 12, 31)                    
                    user_id = controller.add_user(
                        name=user['name'], storetype='DBUSER', active=True, 
                        password=user['pwd'], desc=user['desc'], 
                        expiry_date=expiry_date, base=False, system=True)

                # create users
                elif user['type'] == 'user':
                    expiry_date = datetime.datetime(2099, 12, 31) 
                    user_id = controller.add_user(
                        name=user['name'], storetype='DBUSER', active=True, 
                        password=user['pwd'], desc=user['desc'], 
                        expiry_date=expiry_date, base=True, system=False)
                
                # add attribs to user
                attribs = user.get('attribs', [])
                user_obj = controller.get_user(user['name'])
                for a in attribs:
                    user_obj.set_attribute(name=a['name'], value=a['value'], desc=a['desc'])
                
                self.logger.info('Add user %s' % (user['name']))
                msgs.append('Add user %s' % (user['name']))          
                
        return msgs            
    
    def __create_main_catalogs(self, controller, config, config_db_manager):
        """Create auth/catalog subsystem main catalog
        """
        msgs = []
        
        catalogs = config['catalogs']
        
        for catalog in catalogs:
            # check if catalog already exist
            try:
                controller.get_catalog(catalog['name'])
                self.logger.warning('Catalog %s already exist' % (catalog['name']))
                msgs.append('Catalog %s already exist' % (catalog['name']))
                # res = cats[0]['oid']
            except:
                # create new catalog
                cat = controller.add_catalog(catalog['name'], catalog['desc'], catalog['zone'])
                self.logger.info('Add catalog name:%s zone:%s : %s' % (catalog['name'], catalog['zone'], cat))
                msgs.append('Add catalog name:%s zone:%s : %s' % (catalog['name'], catalog['zone'], cat))

                # set catalog in config if internal
                if catalog['zone'] == 'internal':
                    config_db_manager.add(config['api_system'], 'api', 'catalog', catalog['name'])

            # add endpoint
            for endpoint in catalog.get('endpoints', []):
                # check if endpoint already exist
                try:
                    controller.get_endpoint(endpoint['name'])
                    self.logger.warning('Endpoint %s already exist' % (endpoint['name']))
                    msgs.append('Endpoint %s already exist' % (endpoint['name']))
                    # res = cats[0]['oid']
                except:
                    # create new endpoint
                    cat = controller.get_catalog(catalog['name'])
                    res = cat.add_endpoint(name=endpoint['name'], desc=endpoint['desc'], service=endpoint['service'],
                                           uri=endpoint['uri'], active=True)
                    self.logger.info('Add endpoint name:%s service:%s : %s' % (endpoint['name'],
                                                                               endpoint['service'], res))
                    msgs.append('Add endpoint name:%s service:%s : %s' % (endpoint['name'], endpoint['service'], res))

        return msgs
    
    def __setup_kombu_queue(self, config):
        """Setup kombu redis key fro queue
        """
        configs = config['config']
        for item in configs:
            if item['group'] == 'queue':
                value = item['value']
                queue = value['queue']
                uri = value['uri']
                manager = RedisManager(uri)
                manager.server.set('_kombu.binding.%s' % queue, value)
    
    def create_subsystem(self, subsystem_config, update=False):
        """Create subsystem.
        
        :param subsystem_config: subsystem configuration file
        """
        res = []
        
        # read subsystem config
        config = self.read_config(subsystem_config)
        subsystem = get_value(config, 'api_subsystem', None, exception=True)
        # update = get_value(config, 'update', False)
        api_config = get_value(config, 'api', {})

        if update is True:
            self.logger.info('Update %s subsystem' % subsystem)
        else:
            self.logger.info('Create new %s subsystem' % subsystem)
        
        # set operation user
        operation.user = (api_config.get('user', None), 'localhost', None)
        operation.id = str(uuid4())
        self.set_permissions(classes=self.classes)        
        
        # init auth subsytem
        if subsystem == 'auth':
            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))
            
            # setup main kombu queue
            
        # init oauth2 subsytem
        elif subsystem == 'oauth2':
            res.extend(self.__init_subsystem(config, update=update))

        # init other subsystem
        else:
            # create api client instance
            client = BeehiveApiClient(api_config['endpoint'],
                                      'keyauth',
                                      api_config['user'], 
                                      api_config['pwd'],
                                      None,
                                      api_config['catalog'])
            
            if update is False:
                # create super user
                user = {'name': '%s_admin@local' % config['api_subsystem'],
                        'pwd': random_password(20),
                        'desc': '%s internal user' % subsystem}
                try:
                    client.add_system_user(user['name'], password=user['pwd'], desc='User %s' % user['name'])
                except BeehiveApiClientError as ex:
                    if ex.code == 409:
                        client.update_user(user['name'], user['name'], user['pwd'], 'User %s' % user['name'])
                    else:
                        raise
            
                # append system user config
                config['config'].append({'group': 'api', 'name': 'user',
                                         'value': {'name': user['name'], 'pwd': user['pwd']}})
                # append catalog config
                config['config'].append({'group': 'api', 'name': 'catalog', 'value': api_config['catalog']})
                # append auth endpoints config
                config['config'].append({'group': 'api', 'name': 'endpoints',
                                         'value': json.dumps(api_config['endpoint'])})
    
            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))

        return res
