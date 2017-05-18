'''
Usage: manage.py [OPTION]... subsystem|client [PARAMs]...

Beehive ecosystem api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    -h, --help          manager help    
    
PARAMs:
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

Exit status:
 0  if OK,
 1  if problems occurred

Created on Jan 25, 2017

@author: darkbk
'''
import logging
import ujson as json
from pprint import PrettyPrinter
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation
from beecell.simple import import_class, id_gen, random_password
from beehive.module.auth.controller import Objects, Role, User
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.module.catalog.controller import Catalog
from beehive.common.config import ConfigDbManager

logger = logging.getLogger(__name__)

classes = [
    Objects,
    Role,
    User,
    Catalog
]

def get_operation_id(objdef):
    """
    """
    temp = objdef.split(u'.')
    ids = [u'*' for i in temp]
    return u'//'.join(ids)

def set_operation(classes=[]):
    """Set user operations
    
    :param classes: list of classes to include in perms
    """
    operation.perms = []
    for op in classes:
        perm = (1, 1, op.objtype, op.objdef, op.__class__.__name__, 
                get_operation_id(op.objdef), 1, u'*')
        operation.perms.append(perm)

def configure(config, update=True):
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
        logger.info(u'Create config DB %s' % (u''))
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
            logger.info(u'Add configuration %s' % (res))
            msgs.append(u'Add configuration %s' % (res))
    except Exception as ex:
        logger.error(ex, exc_info=1)
        raise
    finally:
        # release session
        manager.release_session(operation.session)
        operation.session = None
        
    return msgs

def init_subsystem(config, update=True):
    """Init beehive subsystem
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
            logger.info(u'Create DB %s' % (db_manager_class))
            msgs.append(u'Create DB %s' % (db_manager_class))
    except Exception as ex:
        logger.error(ex, exc_info=1)    

    set_operation(classes=classes)

    # create module
    for item in config[u'api_modules']:
        try:
            module = manager.modules[item.split(u'.')[-1]]
            controller = module.get_controller()
            
            # create session
            operation.session = manager.get_session()
            
            # init module
            module.init_object()
            logger.info(u'Init module %s' % (module))
            msgs.append(u'Init module %s' % (module))
            
            # create system users and roles
            if module.name == u'AuthModule':
                res = __create_main_users(controller, config, 
                                          config_db_manager)
                controller.set_superadmin_permissions()
                msgs.extend(res)
                
            elif module.name == u'CatalogModule':
                res = __create_main_catalogs(controller, config, 
                                             config_db_manager)
                controller.set_superadmin_permissions()
                msgs.extend(res)
          
        except Exception as ex:
            logger.error(ex, exc_info=1)
            raise
        finally:
            # release session
            module.release_session(operation.session)
            operation.session = None
            
    logger.info(u'Init subsystem %s' % (config[u'api_subsystem']))
    msgs.append(u'Init subsystem %s' % (config[u'api_subsystem']))
    
    return msgs

def __create_main_users(controller, config, config_db_manager):
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
    
    # add internal system user
    '''sys_user = {u'name':u'auth_admin@local',
                u'pwd':random_password(20),
                u'desc':u'Auth admin user',
                u'type':u'admin'}
    users.append(sys_user)
    
    # set user in config
    config_db_manager.add(config[u'api_system'],
                          u'auth', 
                          u'api_user', 
                          json.dumps({u'name':sys_user[u'name'], 
                                      u'pwd':sys_user[u'pwd']}))''' 

    for user in users:
        # check if user already exist
        users = controller.get_users(name=user[u'name'])
        if len(users) > 0:
            logger.debug(u'User %s already exist' % (user[u'name']))
            msgs.append(u'User %s already exist' % (user[u'name']))        
        
        else:
            # create superadmin
            if user[u'type'] == u'admin':
                userobj = controller.add_user(user[u'name'], 
                                           u'DBUSER', 
                                           u'USER', 
                                           active=True, 
                                           password=user[u'pwd'], 
                                           description=user[u'desc'])
                userobj.append_role(u'ApiSuperadmin')
                
            # create users
            elif user[u'type'] == u'user':
                userobj = controller.add_generic_user(user[u'name'], 
                                                   u'DBUSER', 
                                                   user[u'pwd'], 
                                                   description=user[u'desc'])
            
            logger.debug(u'Add user %s' % (user[u'name']))
            msgs.append(u'Add user %s' % (user[u'name']))          
            
    return msgs            

def __create_main_catalogs(controller, config, config_db_manager):
    """Create auth/catalog subsystem main catalog
    """
    msgs = []
    
    catalog = config[u'catalog']
    
    #for catalog in catalogs:
    # check if catalog already exist
    cats = controller.get_catalogs(name=catalog[u'name'], 
                                   zone=catalog[u'zone'])
    if len(cats) > 0:
        logger.warn(u'Catalog name:%s zone:%s already exist' % 
                    (catalog[u'name'], catalog[u'zone']))
        msgs.append(u'Catalog name:%s zone:%s already exist' % 
                    (catalog[u'name'], catalog[u'zone']))
        res = cats[0][u'oid']
    
    # create new catalog
    else:
        res = controller.add_catalog(catalog[u'name'], 
                                     catalog[u'desc'], 
                                     catalog[u'zone'])
        logger.info(u'Add catalog name:%s zone:%s : %s' % 
                    (catalog[u'name'], catalog[u'zone'], res))
        msgs.append(u'Add catalog name:%s zone:%s : %s' % 
                    (catalog[u'name'], catalog[u'zone'], res))
    
    # set catalog in config
    config_db_manager.add(config[u'api_system'], u'auth', u'catalog', res)     
    
    return msgs

def __read_subsytem_config(filename):
    """
    """
    f = open(filename, 'r')
    config = f.read()
    config = json.loads(config)
    f.close()
    return config

def create_main(auth_config, format, args):
    """
    """
    pp = PrettyPrinter(width=200)
    res = []
    
    # set operation user
    operation.user = (auth_config[u'user'], u'localhost', None)
    set_operation(classes=classes)
    
    try:
        subsystem = args.pop(0)
    except:
        print(u'ERROR : Specify subsystem')
        logger.error(u'Specify subsystem', exc_info=1)
        return 1    
    
    try:
        file_config = args.pop(0)
    except:
        print(u'ERROR : Specify subsystem config file')
        logger.error(u'Specify subsystem config file', exc_info=1)
        return 1
    
    # read subsystem config
    config = __read_subsytem_config(file_config)
    update = config.get(u'update', False)
    
    # init auth subsytem
    if subsystem == u'auth':
        res.extend(configure(config, update=update))
        res.extend(init_subsystem(config, update=update))
    
    # init other subsystem
    else:
        # create api client instance
        client = BeehiveApiClient(auth_config[u'endpoint'], 
                                  auth_config[u'user'], 
                                  auth_config[u'pwd'],
                                  auth_config[u'catalog'])
        
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
            config[u'config'].append({u'group':u'auth', 
                                      u'name':u'api_user', 
                                      u'value':{u'name':user[u'name'], 
                                                u'pwd':user[u'pwd']}})
            # append catalog config
            config[u'config'].append({u'group':u'auth', 
                                      u'name':u'catalog', 
                                      u'value':auth_config[u'catalog']})
            # append auth endpoints config
            config[u'config'].append({u'group':u'auth', 
                                      u'name':u'endpoints', 
                                      u'value':json.dumps(auth_config[u'endpoint'])})

        res.extend(configure(config, update=update))
        res.extend(init_subsystem(config, update=update))
        
    if format == u'text':
        pass
    else:
        pp.pprint(res)
        
    return 0


def create_client(auth_config, format, args):
    """Create and init beehive client. Beehive client can need new:
    - auth object types
    - auth object and permissions
    - auth roles
    - auth users
    """
    pp = PrettyPrinter(width=200)
    res = []
    
    # set operation user
    operation.user = (auth_config[u'user'], u'localhost', None)
    set_operation(classes=classes)
    
    try:
        file_config = args.pop(0)
    except:
        print(u'ERROR : Specify client config file')
        logger.error(u'Specify client config file', exc_info=1)
        return 1
    
    # read subsystem config
    config = __read_subsytem_config(file_config)
    update = config.get(u'update', False)
    
    # create api client instance
    client = BeehiveApiClient(auth_config[u'endpoint'], 
                              auth_config[u'user'], 
                              auth_config[u'pwd'],
                              auth_config[u'catalog'])
    
    name = config[u'name']
    client_type = config[u'type']
    
    # create object types
    for o in config[u'object_types']:
        try:
            resp = client.add_object_types(client_type, o[0], u'')
            res.append(u'Add object type %s %s' % (client_type, o[0]))
        except BeehiveApiClientError as ex:
            res.append(u'WARN: %s' % ex)
    
    # create objects and related permissions
    for o in config[u'objects']:
        try:
            resp = client.add_object(client_type, o[0], o[1] % name, 
                                     u'%s %s object' % (name, o[0]))
            res.append(u'Add object %s %s %s' % (client_type, o[0], o[1] % name))        
        except BeehiveApiClientError as ex:
            res.append(u'WARN: %s' % ex)    
    
    # create roles
    for o in config[u'roles']:
        # create role
        try:
            resp = client.add_role(o[u'name'], o[u'description'])
            res.append(u'Add role %s' % (o[u'name']))
        except BeehiveApiClientError as ex:
            res.append(u'WARN: %s' % ex)
        
        # assign permisssions to role
        for p in o[u'perms']:
            try:
                resp = client.append_role_permissions(o[u'name'], 
                                                      p[0], p[1], p[2], p[3])
                res.append(u'Add perms %s %s %s %s to role %s' % (
                           client_type, p[0], p[1], p[2], p[3]))
            except BeehiveApiClientError as ex:
                res.append(u'WARN: %s' % ex)

    
    # create user
    for o in config[u'users']:
        # create user
        try:
            resp = client.add_user(o[u'name'], o[u'pwd'], o[u'desc'])
            res.append(u'Add user %s' % (o[u'name']))
        except BeehiveApiClientError as ex:
            res.append(u'WARN: %s' % ex)
        
        # assign permisssions to role
        try:
            resp = client.append_user_roles(o[u'name'], o[u'roles'])
            res.append(u'Add roles %s to user %s' % (o[u'roles'], o[u'name']))
        except BeehiveApiClientError as ex:
            res.append(u'WARN: %s' % ex)    
    
    if format == u'text':
        pass
    else:
        pp.pprint(res)
        
    return 0
