'''
Created on May 11, 2017

@author: darkbk
'''
import logging
import ujson as json
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation
from beecell.simple import import_class, id_gen, random_password, get_value
from beehive.module.auth.controller import Objects, Role, User
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.module.catalog.controller import Catalog
from beehive.common.model.config import ConfigDbManager
from beecell.db.manager import RedisManager

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
        Catalog
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)  
    
    def get_permission_id(self, objdef):
        """Get operation objid
        """
        temp = objdef.split(u'.')
        ids = [u'*' for i in temp]
        return u'//'.join(ids)
    
    def set_permissions(self, classes=[]):
        """Set user operations
        
        :param classes: list of classes to include in perms
        """
        try:
            operation.perms = []
            for op in classes:
                perm = (1, 1, op.objtype, op.objdef, 
                        self.get_permission_id(op.objdef), 1, u'*')
                operation.perms.append(perm)
        except Exception as ex:
            raise Exception(u'Permissions assign error: %s' % ex)
    
    def read_config(self, filename):
        """
        """
        f = open(filename, u'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config    
    
    def __configure(self, config, update=True):
        """
        """
        msgs = []
    
        try:
            # create api manager
            params = {u'api_id':u'server-01',
                      u'api_name':config[u'api_system'],
                      u'api_subsystem':config[u'api_subsystem'],
                      u'database_uri':config[u'db_uri'],
                      u'api_module':[u'beehive.module.process.mod.ConfigModule'],
                      u'api_plugin':[]}
            manager = ApiManager(params)    
    
            # remove and create scchema
            if update is False:
                ConfigDbManager.remove_table(config[u'db_uri'])
            ConfigDbManager.create_table(config[u'db_uri'])
            self.logger.info(u'Create config DB %s' % (u''))
            msgs.append(u'Create config DB %s' % (u''))
    
            # create session
            operation.session = manager.get_session()
            #operation.perms = perms
            #operation.user = authuser
            
            # create config db manager
            db_manager = ConfigDbManager()
            
            # set configurations
            #
            # populate configs
            #
            for item in config[u'config']:
                value = item[u'value']
                if isinstance(value, dict):
                    value = json.dumps(value)
                res = db_manager.add(config[u'api_system'], 
                                     item[u'group'], 
                                     item[u'name'], 
                                     value)
                self.logger.info(u'Add configuration %s' % (res))
                msgs.append(u'Add configuration %s' % (res))
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise
        finally:
            # release session
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
            params = {u'api_id':u'server-01',
                      u'api_name':config[u'api_system'],
                      u'api_subsystem':config[u'api_subsystem'],
                      u'database_uri':config[u'db_uri'],
                      u'api_module':config[u'api_modules'],
                      u'api_plugin':config[u'api_plugins']}
            manager = ApiManager(params)
            manager.configure()
            manager.register_modules()
    
            # create config db manager
            config_db_manager = ConfigDbManager()
    
            for db_manager_class in config[u'db_managers']:
                db_manager = import_class(db_manager_class)
        
                # remove and create/update scchema
                if update is False:
                    db_manager.remove_table(config[u'db_uri'])
                db_manager.create_table(config[u'db_uri'])
                self.logger.info(u'Create DB %s' % (db_manager_class))
                msgs.append(u'Create DB %s' % (db_manager_class))
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise
    
        self.set_permissions(classes=self.classes)
    
        # create module
        for item in config[u'api_modules']:
            try:
                self.logger.info(u'Load module %s' % (item))
                module = manager.modules[item.split(u'.')[-1]]
                controller = module.get_controller()
                
                # create session
                operation.session = manager.get_session()
                
                # init module
                module.init_object()
                self.logger.info(u'Init module %s' % (module))
                msgs.append(u'Init module %s' % (module))
                
                # create system users and roles
                if module.name == u'AuthModule':
                    res = self.__create_main_users(controller, config, 
                                              config_db_manager)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)
                    
                elif module.name == u'Oauth2Module':
                    controller.set_superadmin_permissions()
                    
                elif module.name == u'BasicModule':
                    controller.set_superadmin_permissions()  
                    
                elif module.name == u'CatalogModule':
                    res = self.__create_main_catalogs(controller, config, 
                                                 config_db_manager)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)
              
            except Exception as ex:
                self.logger.error(ex, exc_info=1)
                raise
            finally:
                # release session
                module.release_session(operation.session)
                operation.session = None
                
        self.logger.info(u'Init subsystem %s' % (config[u'api_subsystem']))
        msgs.append(u'Init subsystem %s' % (config[u'api_subsystem']))
        
        return msgs
    
    def __create_main_users(self, controller, config, config_db_manager):
        """Create auth subsystem main users
        """
        msgs = []
    
        users = config[u'users']
    
        # add superadmin role
        #perms_to_assign = controller.get_superadmin_permissions()
        perms_to_assign = []
        controller.add_superadmin_role(perms_to_assign)
        
        # add guest role
        controller.add_guest_role()
        
        for user in users:
            # check if user already exist
            users, total = controller.get_users(name=user[u'name'])
            if len(users) > 0:
                self.logger.warn(u'User %s already exist' % (user[u'name']))
                msgs.append(u'User %s already exist' % (user[u'name']))        
            
            else:
                # create superadmin
                if user[u'type'] == u'admin':
                    expiry_date = u'31-12-2099'
                    user_id = controller.add_user(user[u'name'], 
                                               u'DBUSER', 
                                               u'USER', 
                                               active=True,
                                               password=user[u'pwd'], 
                                               description=user[u'desc'],
                                               expiry_date=expiry_date)
                    users, total = controller.get_users(name=user[u'name'])
                    users[0].append_role(u'ApiSuperadmin', 
                                         expiry_date=expiry_date)
                    
                # create users
                elif user[u'type'] == u'user':
                    expiry_date = u'31-12-2099'
                    user_id = controller.add_generic_user(user[u'name'], 
                                                   u'DBUSER', 
                                                   user[u'pwd'], 
                                                   description=user[u'desc'],
                                                   expiry_date=expiry_date)
                
                self.logger.info(u'Add user %s' % (user[u'name']))
                msgs.append(u'Add user %s' % (user[u'name']))          
                
        return msgs            
    
    def __create_main_catalogs(self, controller, config, config_db_manager):
        """Create auth/catalog subsystem main catalog
        """
        msgs = []
        
        catalog = config[u'catalog']
        
        #for catalog in catalogs:
        # check if catalog already exist
        cats = controller.get_catalogs(name=catalog[u'name'], 
                                       zone=catalog[u'zone'])
        if len(cats) > 0:
            self.logger.warn(u'Catalog name:%s zone:%s already exist' % 
                             (catalog[u'name'], catalog[u'zone']))
            msgs.append(u'Catalog name:%s zone:%s already exist' % 
                        (catalog[u'name'], catalog[u'zone']))
            res = cats[0][u'oid']
        
        # create new catalog
        else:
            res = controller.add_catalog(catalog[u'name'], 
                                         catalog[u'desc'], 
                                         catalog[u'zone'])
            self.logger.info(u'Add catalog name:%s zone:%s : %s' % 
                             (catalog[u'name'], catalog[u'zone'], res))
            msgs.append(u'Add catalog name:%s zone:%s : %s' % 
                        (catalog[u'name'], catalog[u'zone'], res))
        
        # set catalog in config
        config_db_manager.add(config[u'api_system'], u'api', 
                              u'catalog', catalog[u'name'])     
        
        return msgs
    
    def __setup_kombu_queue(self, config):
        """Setup kombu redis key fro queue
        """
        configs = config[u'config']
        for item in configs:
            if item[u'group'] == u'queue':
                value = item[u'value']
                queue = value[u'queue']
                uri = value[u'uri']
                manager = RedisManager(uri)
                manager.server.set(u'_kombu.binding.%s' % queue, value)
    
    def create_subsystem(self, subsystem_config):
        """Create subsystem.
        
        :param subsystem_config: subsystem configuration file
        """
        res = []
        
        # read subsystem config
        config = self.read_config(subsystem_config)
        subsystem = get_value(config, u'api_subsystem', None, exception=True)
        update = get_value(config, u'update', False)
        api_config = get_value(config, u'api', {})

        self.logger.debug(api_config)

        # set operation user
        operation.user = (api_config.get(u'user', None), u'localhost', None)
        self.set_permissions(classes=self.classes)        
        
        # init auth subsytem
        if subsystem == u'auth':
            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))
            
            # setup main kombu queue
            
        # init oauth2 subsytem
        elif subsystem == u'oauth2':
            res.extend(self.__init_subsystem(config, update=update))

        # init other subsystem
        else:
            # create api client instance
            client = BeehiveApiClient(api_config[u'endpoint'],
                                      u'keyauth',
                                      api_config[u'user'], 
                                      api_config[u'pwd'],
                                      api_config[u'catalog'])
            
            # create super user
            user = {u'name':u'%s_admin@local' % config[u'api_subsystem'],
                    u'pwd':random_password(20),
                    u'desc':u'%s internal user' % subsystem}
            try:
                client.add_system_user(user[u'name'], 
                                       password=user[u'pwd'], 
                                       description=u'User %s' % user[u'name'])
            except BeehiveApiClientError as ex:
                if ex.code == 409:
                    client.update_user(user[u'name'], user[u'name'], user[u'pwd'],
                                       u'User %s' % user[u'name'])
                else:
                    raise
            
            if update is False:
                # append system user config
                config[u'config'].append({u'group':u'api',
                                          u'name':u'user', 
                                          u'value':{u'name':user[u'name'],
                                                    u'pwd':user[u'pwd']}})
                # append catalog config
                config[u'config'].append({u'group':u'api', 
                                          u'name':u'catalog', 
                                          u'value':api_config[u'catalog']})
                # append auth endpoints config
                config[u'config'].append({u'group':u'api', 
                                          u'name':u'endpoints', 
                                          u'value':json.dumps(api_config[u'endpoint'])})
    
            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))
            
        return res