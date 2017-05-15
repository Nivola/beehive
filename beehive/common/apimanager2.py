'''
Created on Jan 23, 2017

@author: darkbk
'''
from logging import getLogger

#####
import pickle
######

import dicttoxml

from time import time
from gevent import Timeout

import ujson as json
from redis import StrictRedis

from binascii import a2b_hex, a2b_base64, b2a_base64
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5

from flask.views import View as FlaskView
from flask import request, Response

from beecell.simple import str2uni, id_gen, import_class, truncate, \
    get_class_name, parse_redis_uri
from beecell.perf import watch
from beecell.db import TransactionError, QueryError
from beecell.db.manager import MysqlManager, SqlManagerError, RedisManager
from beecell.flask.redis_session import RedisSessionInterface
from beecell.auth import DatabaseAuth, LdapAuth, SystemUser
from beecell.sendmail import Mailer
from beecell.auth import extract
from beehive.common.event import EventProducerRedis
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.common.data import operation
from beehive.common.config import ConfigDbManager
from beehive.module.auth.model import AuthDbManager

class ApiManagerError(Exception):
    """Main excpetion raised by api manager and childs
    
    :param value: error description
    :param code: error code [default=400]

    """
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return u'ApiManagerError: %s' % self.value 

    def __str__(self):
        return u'%s, %s' % (self.value, self.code)

class ApiManager(object):
    """Api manager main class. Use this class to configure api ecosystem.
    
    :param dict params: configuration parameters
    :param app: BeehiveApp istance
    :param str hostname: server name
    :return: ApiManager instance
    """

    def __init__(self, params, app=None, hostname=None):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)
        
        # configuration params
        self.params = params       
        
        # flask app reference
        self.app = app
        self.app_name = self.params[u'api_name']
        self.app_id = self.params[u'api_id']
        self.app_desc = self.params[u'api_id']
        self.app_subsytem = self.params[u'api_subsystem']
        self.app_endpoint_id = u'%s-%s' % (self.params[u'api_id'], hostname)
        try:
            #self.app_uri = {u'uwsgi':u'%s:%s' % (host, self.params['socket']),
            #                u'http':u'http://%s%s' % (host, self.params['http-socket'])}
            self.app_uri = u'http://%s%s' % (hostname, self.params[u'http-socket'])
        except:
            self.app_uri = None
        
        # instance configuration
        self.http_socket = self.params.get(u'http-socket')
        self.server_name = hostname
        
        # modules
        self.modules = {}
        
        # redis
        #self.redis_msg_manager = None
        #self.redis_msg_channel = None
        #self.redis_process_manager = None
        #self.redis_process_channel = None
        self.redis_manager = None
        
        # security
        self.auth_providers = {}
        self.authentication_manager = None
        
        # job manager
        self.job_manager = None
        self.max_concurrent_jobs = 2
        self.job_interval = 1.0
        self.job_timeout = 1200        
        
        # event producer
        self.event_producer = None
        
        # process event producer
        #self.process_event_producer = None
        
        # api listener
        self.api_timeout = 10.0
        
        # api endpoints
        self.endpoints = {}
        #self.rpc_client = ApiRpcClient(self)
        #self.rpc_httpclient = ApiRpcHttpClient(self)
        self.api_user = None
        self.api_user_pwd = None
        self.api_client = None      
        
        # gateways
        self.gateways = {}
        
        # database manager
        self.db_manager = None
        database_uri = self.params.get('database_uri')
        if database_uri != None:
            self.create_pool_engine((database_uri, 5, 10, 10, 1800))
        
        # send mail
        self.mailer = None
        self.mail_sender = None
        
        # identity
        self.prefix = 'identity:'
        self.expire = 1800
        
        # scheduler
        self.redis_taskmanager = None
        self.redis_scheduler = None

    def create_pool_engine(self, dbconf):
        """Create mysql pool engine.
        
        :param dbconf list: (uri, timeout, pool_size, max_overflow, pool_recycle) 
        """
        try:
            db_uri = dbconf[0]
            connect_timeout = dbconf[1]
            pool_size = dbconf[2]
            max_overflow = dbconf[3]
            pool_recycle = dbconf[4]
            self.db_manager = MysqlManager('db_manager01', db_uri, 
                                           connect_timeout=connect_timeout)
            self.db_manager.create_pool_engine(pool_size=pool_size, 
                                               max_overflow=max_overflow, 
                                               pool_recycle=pool_recycle)
        except SqlManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)
    
    def create_simple_engine(self, dbconf):
        """Create mysql simple engine.
        
        :param dbconf list: (uri, timeout) 
        """
        try:
            db_uri = dbconf[0]
            connect_timeout = dbconf[1]
            self.db_manager = MysqlManager('db_manager01', db_uri, 
                                           connect_timeout=connect_timeout)
            self.db_manager.create_simple_engine()
        except SqlManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)
            
    def get_session(self):
        """open db session"""
        try:
            operation.session = self.db_manager.get_session()
            return operation.session
        except SqlManagerError as e:
            raise ApiManagerError(e)
        
    def flush_session(self, dbsession=None):
        """release db session"""
        try:
            if operation.session is not None:
                operation.session.flush()
        except SqlManagerError as e:
            raise ApiManagerError(e)          
        
    def release_session(self, dbsession=None):
        """release db session"""
        try:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
                operation.session = None
        except SqlManagerError as e:
            raise ApiManagerError(e)            

    @watch
    def get_identity(self, uid):
        """Get identity
        
        :param uid: identity id
        :return: dictionary like:
        
                 .. code-block:: python
                   
                   {u'uid':..., 
                    u'user':..., 
                    u'timestamp':..., 
                    u'pubkey':..., 
                    u'seckey':...}
        """
        identity = self.redis_manager.get(self.prefix + uid)
        if identity is not None:
            data = pickle.loads(identity)
            data['ttl'] = self.redis_manager.ttl(self.prefix + uid)
            self.logger.debug('Get identity %s from redis' % (uid))           
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=401)

    @watch
    def get_identities(self):
        try:
            res =  []
            for key in self.redis_manager.keys(self.prefix+'*'):
                identity = self.redis_manager.get(key)
                data = pickle.loads(identity)
                ttl = self.redis_manager.ttl(key)
                res.append({'uid':data['uid'], 'user':data['user']['name'],
                            'timestamp':data['timestamp'], 'ttl':ttl, 
                            'ip':data['ip']})
        except Exception as ex:
            self.logger.error('No identities found: %s' % ex)
            raise ApiManagerError('No identities found')
        
        #User(self).event('user.identity.get', {}, (True))
        self.logger.debug('Get identities from redis: %s' % (res))
        return res

    @watch
    def verify_request_signature(self, uid, sign, data):
        """Verify Request signature.
        
        :param uid: identity id
        :param sign: request sign
        :param data: request data
        :raise ApiUtilError:
        """
        # retrieve token and sign
        #uid, sign, data = self._get_token()
        
        # get identity
        identity = self.get_identity(uid)
        from beecell.perf import watch
        # verify signature
        pubkey64 = identity['pubkey']
        
        try:
            # import key        
            #signature = a2b_base64(sign)
            signature = a2b_hex(sign)
            pub_key = a2b_base64(pubkey64)
            key = RSA.importKey(pub_key)
            
            # create data hash
            hash_data = SHA256.new(data)
            self.logger.debug('Get data: %s' % data)
            self.logger.debug('Created hash: %s' % b2a_base64(hash_data.digest()))

            # verify sign
            verifier = PKCS1_v1_5.new(key)
            res = verifier.verify(hash_data, signature)
            
            # extend expire time of the redis key
            if res is True:
                self.redis_manager.expire(self.prefix + uid, self.expire)
                self.logger.debug('Extend expire for identity %s: %ss' % (
                                                    uid, self.expire))
        except:
            self.logger.error("Data signature for identity %s is not valid" % uid)
            raise ApiManagerError("Data signature for identity %s is not valid" % uid, code=401)

        if not res:
            raise ApiManagerError("Data signature for identity %s is not valid" % uid, code=401)
        else:    
            self.logger.debug('Data signature is valid')

        return identity

    def register_modules(self):
        self.logger.info('Configure modules - START')
        
        module_classes = self.params['api_module']
        if type(module_classes) is str:
            module_classes = [module_classes]
        
        for item in module_classes:
            # import module class
            module_class = import_class(item)
            # instance module class
            module = module_class(self)
            self.logger.info('Register module: %s' % item)
        
        if 'api_plugin' in self.params:
            plugin_pkgs = self.params['api_plugin']
            if type(plugin_pkgs) is str:
                plugin_pkgs = [plugin_pkgs]
            for plugin_pkg in plugin_pkgs:
                name, class_name = plugin_pkg.split(',')
                # import plugin class
                plugin_class = import_class(class_name)
                # get module plugin
                module = self.modules[name]
                # instance plugin class
                plugin = plugin_class(module)
                # register plugin
                plugin.register()
                self.logger.info('Register plugin: %s' % class_name)
        
        # register api
        for module in self.modules.values():
            # register module api
            module.register_api()
        
        self.logger.info('Configure modules - STOP')

    def list_modules(self):
        """Return list of configures modules.
        
        :param name: module name
        :return: ApiModule instance
        """
        return self.modules

    def get_module(self, name):
        """Return module by name.
        
        :param name: module name
        :return: ApiModule instance
        """
        return self.modules[name]

    def configure(self):
        """ """
        # create db manager
        #self.db_uri = self.params['database_uri']
        #self.db_manager = MysqlManager('db_manager01', self.db_uri, connect_timeout=5)
        #self.db_manager.create_pool_engine(pool_size=10, max_overflow=10, pool_recycle=3600)
        #self.db_manager.create_simple_engine()

        self.logger.debug('Configure server - START')

        if self.db_manager is not None:
            # open db session
            self.get_session()
            operation.perms = None
            
            try:
                # get configurator instance
                configurator = ConfigDbManager()     
                
                ##### redis configuration #####
                self.logger.info('Configure redis - START')
                # connect to redis
                redis_uri = configurator.get(app=self.app_name, 
                                             group='redis', 
                                             name='redis_01')[0].value
                # parse redis uri
                host, port, db = parse_redis_uri(redis_uri)
                    
                # set redis manager
                self.redis_manager = StrictRedis(host=host, port=int(port), db=int(db))          
    
                # create job manager
                '''
                self.job_manager = JobManager(self.redis_manager, 
                                              self.redis_msg_channel, 
                                              self.max_concurrent_jobs,
                                              self.job_interval,
                                              self.job_timeout)
                self.logger.info('Create JobManager instance: %s' % self.job_manager)
                '''
                
                # app session
                self.session_interface = RedisSessionInterface(redis=self.redis_manager)
                self.logger.info('Setup redis session manager: %s' % self.session_interface)
    
                self.logger.info('Configure redis - STOP')  
                ##### redis configuration #####
                
                ##### scheduler reference configuration #####
                self.logger.info('Configure scheduler reference - START')
                
                try:
                    from gibboncloudapi.module.scheduler.manager import configure_task_manager
                    from gibboncloudapi.module.scheduler.manager import configure_task_scheduler
                    
                    # task manager
                    '''
                    broker_url = configurator.get(app=self.app_name, 
                                                  group='taskmanager',
                                                  name='task_broker_url')[0].value           
                    result_backend = configurator.get(app=self.app_name, 
                                                      group='taskmanager',
                                                      name='task_result_backend')[0].value'''
                    
                    broker_url = self.params['broker_url']
                    result_backend = self.params['result_backend']
                    configure_task_manager(broker_url, result_backend)
                    self.redis_taskmanager = RedisManager(result_backend)
                    
                    # scheduler
                    '''
                    broker_url = configurator.get(app=self.app_name, 
                                                  group='scheduler',
                                                  name='scheduler_broker_url')[0].value           
                    schedule_backend = configurator.get(app=self.app_name, 
                                                        group='scheduler',
                                                        name='scheduler_result_backend')[0].value'''
                    broker_url = self.params['broker_url']
                    schedule_backend = self.params['result_backend']                                                    
                    configure_task_scheduler(broker_url, schedule_backend)
                    self.redis_scheduler = RedisManager(schedule_backend)
    
                    self.logger.info('Configure scheduler reference - STOP')
                except:
                    self.logger.warning('Scheduler not configured')            
                ##### scheduler reference configuration #####            
                
                
                ##### security configuration #####
                # configure only with auth module
                try:
                    confs = configurator.get(app=self.app_name, group='auth')
                    self.logger.info('Configure security - START')
                    
                    # Create authentication providers
        
                    for conf in confs:
                        item = json.loads(conf.value)
                        if item['type'] == 'db':
                            auth_provider = DatabaseAuth(AuthDbManager, 
                                                         self.db_manager, 
                                                         SystemUser)
                        elif item['type'] == 'ldap':
                            auth_provider = LdapAuth(item['host'], item['domain'], 
                                                     SystemUser, timeout=item['timeout'], 
                                                     ssl=item['ssl'])
                        self.auth_providers[item['domain']] = auth_provider
                        self.logger.info('Setup authentication provider: %s' % auth_provider)
            
                    # Create authentication manager
                    #self.api_manager.authentication_manager = AuthenticationManager(self.auth_providers)
            
                    # Create security datastore
                    #self.security_datastore = AuthController(self.auth_providers)
                    #self.logger.debug('Setup security datastore: %s' % self.security_datastore)
                    
                    """
                    # login manager
                    def unauthorized_callback():
                        return redirect(login_url(login_view, request.url))            
                    
                    self.login_manager = LoginManager(self)
                    login_view = "login"
                    self.login_manager.login_view = login_view
                    self.login_manager.unauthorized_callback = unauthorized_callback
                    self.logger.debug('Setup login manager: %s' % self.login_manager)
                    
                    @self.login_manager.user_loader
                    def load_user(userid):
                        # Return an instance of the User model
                        user = session.get('user_obj')
                        return user
                    """
                    
                    self.logger.info('Configure security - STOP')
                except:
                    self.logger.warning('Security not configured')
                ##### security configuration #####
        
                ##### sendmail configuration #####
                try:
                    self.logger.debug('Configure sendmail - START')            
                    confs = configurator.get(app=self.app_name, group='mail')
                    for conf in confs:
                        if conf.name == 'server1':
                            mail_server = conf.value
                            self.mailer = Mailer(mail_server)
                            self.logger.info('Use mail server: %s' % mail_server)                        
                        if conf.name == 'sender1':
                            mail_sender = conf.value
                            self.mail_sender = mail_sender
                            self.logger.info('Use mail sender: %s' % mail_sender) 
    
                    self.logger.info('Configure sendmail - STOP')
                except:
                    self.logger.warning('Sendmail not configured')
                ##### sendmail configuration #####
    
                ##### gateway configuration #####
                try:    
                    conf = configurator.get(app=self.app_name, group='gateway')
                    self.logger.info('Configure gateway - START')
                    for item in conf:
                        gw = json.loads(item.value)
                        self.gateways[gw['name']] = gw
                        self.logger.info('Setup gateway: %s' % gw)
                    self.logger.info('Configure gateway - STOP')
                except:
                    self.logger.warning('Gateways not configured')
                ##### gateway configuration #####
        
                ##### event queue configuration #####
                try:
                    conf = configurator.get(app=self.app_name, 
                                            group='queue', 
                                            name='queue.event')
                    self.logger.info('Configure event queue - START')
    
                    # setup event producer
                    conf = json.loads(conf[0].value)
                    self.redis_event_uri = conf['uri']
                    self.redis_event_channel = conf['queue']
                            
                    # create instance of event producer
                    self.event_producer = EventProducerRedis(
                                                        self.redis_event_uri, 
                                                        self.redis_event_channel)
                    self.logger.info('Configure event queue - STOP')
                except:
                    self.logger.warning('Event queue not configured')                
                ##### event queue configuration #####
                
                ##### monitor queue configuration #####
                try:
                    conf = configurator.get(app=self.app_name, 
                                            group='queue', 
                                            name='queue.monitor')
                    self.logger.info('Configure monitor queue - START')
    
                    # setup monitor producer
                    conf = json.loads(conf[0].value)
                    self.redis_monitor_uri = conf['uri']
                    self.redis_monitor_channel = conf['queue']                    
                        
                    # create instance of monitor producer
                    from beehive_monitor.producer import MonitorProducerRedis
                    self.monitor_producer = MonitorProducerRedis(
                                                        self.redis_monitor_uri, 
                                                        self.redis_monitor_channel)
                    
                    self.logger.info('Configure monitor queue - STOP')
                except Exception as ex:
                    self.logger.warning('Monitor queue not configured - %s' % ex)                
                ##### monitor queue configuration #####
        
                ##### catalog queue configuration #####
                try:
                    conf = configurator.get(app=self.app_name, 
                                            group='queue', 
                                            name='queue.catalog')
                    self.logger.info('Configure catalog queue - START')
    
                    # setup catalog producer
                    conf = json.loads(conf[0].value)
                    self.redis_catalog_uri = conf['uri']
                    self.redis_catalog_channel = conf['queue']                    
                        
                    # create instance of catalog producer
                    from beehive.module.catalog.producer import CatalogProducerRedis
                    self.catalog_producer = CatalogProducerRedis(
                                                        self.redis_catalog_uri, 
                                                        self.redis_catalog_channel)
                    
                    self.logger.info('Configure catalog queue - STOP')
                except Exception as ex:
                    self.logger.warning('Catalog queue not configured - %s' % ex)                
                ##### catalog queue configuration #####          
        
                ##### tcp proxy configuration #####
                try:
                    conf = configurator.get(app=self.app_name, group='tcpproxy')
                    self.logger.info('Configure tcp proxy - START')
                    self.tcp_proxy = conf[0].value
                    self.logger.info('Setup tcp proxy: %s' % self.tcp_proxy)
                    self.logger.info('Configure tcp proxy - STOP')
                except:
                    self.logger.warning('Tcp proxy queue not configured') 
                ##### tcp proxy configuration #####        
    
                ##### http proxy configuration #####
                try:
                    conf = configurator.get(app=self.app_name, group='httpproxy')
                    self.logger.info('Configure http proxy - START')
                    self.http_proxy = conf[0].value
                    self.logger.info('Setup http proxy: %s' % self.http_proxy)
                    self.logger.info('Configure http proxy - STOP')
                except:
                    self.logger.warning('Http proxy queue not configured') 
                ##### http proxy configuration #####
                
                ##### api authentication configuration #####
                # not configure for auth module
                try:
                    self.logger.info('Configure apiclient- START')
                    
                    # get auth catalog
                    self.catalog = configurator.get(app=self.app_name, 
                                                    group='auth', 
                                                    name='catalog')[0].value
                    self.logger.info('Get catalog: %s' % self.catalog)                
                    
                    # get auth endpoints
                    try:
                        endpoints = configurator.get(app=self.app_name, 
                                                   group='auth', 
                                                   name='endpoints')[0].value
                        self.endpoints = json.loads(endpoints)
                    except:
                        # auth subsystem instance
                        self.endpoints = [self.app_uri]
                    self.logger.info('Get auth endpoints: %s' % self.endpoints)                    
                    
                    # get auth system user
                    auth_user = configurator.get(app=self.app_name, 
                                                 group='auth', 
                                                 name='api_user')[0].value
                    self.auth_user = json.loads(auth_user)
                    self.logger.info('Get auth user: %s' % self.auth_user)

                    # configure api client
                    self.configure_api_client()                   
                    
                    self.logger.info('Configure apiclient - STOP')
                except Exception as ex:
                    self.logger.warning('Apiclient not configured')
                ##### api authentication configuration #####              
                
                del configurator
                
            except ApiManagerError as e:
                raise
            
            # release db session
            self.release_session()
            operation.perms = None
        
        self.logger.info('Configure server - STOP')
    
    def configure_api_client(self):
        """Configure api client instance
        """
        self.api_client = ApiClient(self.endpoints, 
                                    self.auth_user[u'name'], 
                                    self.auth_user[u'pwd'], 
                                    catalog_id=self.catalog)        
    
    def register_catalog_old(self):
        """Create endpoint instance in catalog
        """
        if self.api_client is not None:
            # if endpoint exist update it else create new one
            catalog = self.api_client.catalog_id
            service = self.app_subsytem
            uri = self.app_uri
            try:
                self.api_client.create_endpoint(catalog, self.app_endpoint_id, 
                                                service, uri)
            except BeehiveApiClientError as ex:
                if ex.code == 409:
                    self.api_client.update_endpoint(self.app_endpoint_id, 
                                                    catalog_id=catalog, 
                                                    name=self.app_endpoint_id, 
                                                    service=service, 
                                                    uri=uri)
                else:
                    raise
            self.logger.info(u'Register %s instance in catalog' % self.app_endpoint_id)
            
    def register_catalog(self):
        """Create endpoint instance in catalog
        """
        catalog = self.catalog
        service = self.app_subsytem
        uri = self.app_uri        
        self.catalog_producer.send(self.app_endpoint_id, self.app_desc, 
                                   service, catalog, uri)
        self.logger.info(u'Register %s instance in catalog' % self.app_endpoint_id)
            
    def register_monitor(self):
        """Register instance in monitor
        """
        self.monitor_producer.send(self.app_endpoint_id, self.app_desc, 
                                   self.app_name, {u'uri':self.app_uri})
        self.logger.info(u'Register %s instance in monitor' % self.app_endpoint_id)
                        
class ApiModule(object):
    """ """
    #logger = getLogger('gibbon.cloudapi')
    
    def __init__(self, api_manager, name):
        self.logger = getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.api_manager = api_manager
        self.name = str2uni(name)
        self.views = []
        self.controller = None
        self.api_routes = []
        
        self.api_manager.modules[name] = self
    
    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+'.'+self.__class__.__name__, id(self))    
    
    @watch
    def info(self):
        """Get module infos.
        
        :return: Dictionary with info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {u'name':self.name, 
               u'api':self.api_routes}
        return res
    
    @property
    def redis_manager(self):
        return self.api_manager.redis_manager   

    @property
    def job_manager(self):
        return self.api_manager.job_manager
    
    @staticmethod
    def _get_value(objtype, args):
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)
    
    def get_session(self):
        """open db session"""
        try:
            if self.api_manager.db_manager is not None:
                operation.session = self.api_manager.db_manager.get_session()
                return operation.session
            else:
                return None
        except SqlManagerError as e:
            raise ApiManagerError(e)
        
    def release_session(self, dbsession):
        """release db session"""
        try:
            self.api_manager.db_manager.release_session(operation.session)
            operation.session = None
        except SqlManagerError as e:
            raise ApiManagerError(e)


    def init_object(self):
        """
        
        :param session: database session
        """
        #session = self.get_session()
        session = operation.session
        self.get_controller().init_object()
        #self.release_session(session)
    
    def register_api(self):
        if self.api_manager.app is not None:
            for api in self.apis:
                api.register_api(self)
                #self.logger.debug('Register api view %s' % (api.__class__))

    def get_superadmin_permissions(self):
        """
        
        :param session: database session
        """
        #session = self.get_session()
        session = operation.session
        perms = self.get_controller().get_superadmin_permissions()
        #self.release_session(session)
        return perms
    
    def get_controller(self):
        raise NotImplementedError()

class ApiController(object):
    """ """
    #logger = getLogger('gibbon.cloudapi')
    
    def __init__(self, module):
        self.logger = getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.module = module
        #self.dbauth = AuthDbManager()
        # base event_class. Change in every controller with ApiEvent subclass
        self.event_class = ApiEvent
        
        # identity
        self.prefix = self.module.api_manager.prefix
        self.expire = self.module.api_manager.expire
            
    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+'.'+self.__class__.__name__, id(self))    
    
    @property
    def redis_manager(self):
        return self.module.redis_manager   

    @property
    def job_manager(self):
        return self.module.job_manager
    
    @property
    def mailer(self):
        return (self.module.api_manager.mailer, 
                self.module.api_manager.mail_sender)
    
    @property
    def api_client(self):
        return self.module.api_manager.api_client 
    
    @property
    def redis_taskmanager(self):
        return self.module.api_manager.redis_taskmanager
        
    @property
    def redis_scheduler(self):
        return self.module.api_manager.redis_scheduler
    
    def init_object(self):
        """ """
        raise NotImplementedError()
    
    def get_session(self):
        """open db session"""
        return self.module.get_session()
        
    def release_session(self, dbsession):
        """release db session"""
        return self.module.release_session(dbsession)   
    
    @staticmethod
    def _get_value(objtype, args):
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    def get_identity(self, uid):
        """Get identity
        
        :param uid: identity id
        :return: dictionary like:
        
                 .. code-block:: python
                   
                   {u'uid':..., 
                    u'user':..., 
                    u'timestamp':..., 
                    u'pubkey':..., 
                    u'seckey':...}
        """    
        return self.module.api_manager.get_identity(uid)
    
    def get_identities(self):
        """ """
        return self.module.api_manager.get_identities()
    
    def verify_request_signature(self, uid, sign, data):
        """Verify Request signature.
        
        :param uid: identity id
        :param sign: request sign
        :param data: request data
        :raise ApiUtilError:
        """        
        return self.module.api_manager.verify_request_signature(uid, sign, data)

    @watch
    def can(self, action, objtype, definition=None):
        """Verify if  user can execute an action over a certain object type.
        Specify at least name or perms.
        
        :param objtype: object type. Es. 'resource', 'service',
        :param definition: object definition. Es. 'container.org.group.vm' [optional]                                    
        :param action: object action. Es. \*, view, insert, update, delete, use
        :return: dict like 
        
                 .. code-block:: python
        
                    {objdef1:[objid1, objid2, ..],
                     objdef2:[objid3, objid4, ..],
                     objdef3:[objid4, objid5, ..]}
                     
                 If definition is not None dict contains only 
                 
                 .. code-block:: python
                 
                    {definition:[objid1, objid2, ..]}
                 
        :rtype: dict
        :raises ApiManagerError:
        """
        try:
            objids = []
            defs = []
            user = (operation.user[0], operation.user[1])

            res = {}
            for perm in operation.perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, 'resource', 'container.org.group.vm', 'Vm', 'c1.o1.g1.*', 6, 'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]
                
                # definition is specified
                if definition is not None:
                    # verify object type, definition and action. If they match 
                    # objid to values list
                    if (perm_objtype == objtype and
                        perm_definition == definition and
                        perm_action in ['*', action]):
                        #defs.append(perm_definition)
                        objids.append(perm_objid)
                    
                    # loop between object objids, compact objids and verify match
                    if len(objids) > 0:
                        res[definition] = objids              
                else:
                    if (perm_objtype == objtype and
                        perm_action in ['*', action]):
                        if perm_definition in res:
                            res[perm_definition].append(perm_objid)
                        else:
                            res[perm_definition] = [perm_objid]
            
            for objdef, objids in res.iteritems():
                # loop between object objids, compact objids and verify match
                if len(objids) > 0:
                    res[objdef] = extract(res[objdef])
                    #self.logger.debug('%s:%s can %s objects {%s, %s, %s}' % 
                    #    (user[0], user[1], action, objtype, objdef, res[objdef]))
            
            if len(res.keys()) > 0:
                return res
            else:
                if definition is None:
                    definition = ''
                raise Exception('%s can not \'%s\' objects \'%s:%s\'' % 
                                (user, action, objtype, definition))      
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=401)

    @watch
    def has_needs(self, needs, perms):
        """Verify if permissions overlap needs.
        
        :param needs: object needs as python set
        :param perms: user permissions as python set
        :return: True if overlap
        :rtype: bool
        """
        if len(needs.intersection(perms)) > 0:
            #self.logger.debug('Perms %s overlap needs %s' % (perms, needs))
            return True
        self.logger.warn('Perms %s do not overlap needs %s' % (perms, needs))
        return False

    @watch
    def get_needs(self, args):
        """"""
        # first item *.*.*.....
        act_need = ['*' for i in args]
        needs = ['//'.join(act_need)]
        pos = 0
        for arg in args:
            act_need[pos] = arg
            needs.append('//'.join(act_need))
            pos += 1

        return set(needs)

    @watch
    def check_authorization(self, objtype, objdef, objid, action):
        """This method combine can, get_needs and has_needs, Use when you want
        to verify overlap between needs and permissions for a unique object.
        
        :param objtype: object type. Es. 'resource', 'service',
        :param definition: object definition. Es. 'container.org.group.vm' [optional]                                    
        :param action: object action. Es. \*, view, insert, update, delete, use
        :param objid: object unique id. Es. \*//\*//\*, nome1//nome2//\*, nome1//nome2//nome3        
        :return: True if needs and permissions overlap
        """
        try:
            objs = self.can(action, objtype, definition=objdef)
            
            # check authorization
            objset = set(objs[objdef])
    
            # create needs
            if action == 'insert':
                objid = objid + '//*'
            needs = self.get_needs(objid.split('//'))
            
            # check if needs overlaps perms
            res = self.has_needs(needs, objset)
            if res is False:
                raise ApiManagerError('')
            self.logger.debug("%s can '%s' objects '%s:%s' '%s'" % (
                    (operation.user[0], operation.user[1]), action, objtype, 
                    objdef, objid))
        except ApiManagerError:
            msg = "%s can not '%s' objects '%s:%s' '%s'" % (
                    (operation.user[0], operation.user[1]), action, objtype, 
                    objdef, objid)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)
        return res

    def get_superadmin_permissions(self):
        """ """
        raise NotImplementedError()

class ApiEvent(object):
    """Generic event.
    
    :param controller: ApiController instance
    :param oid: unique id
    :param objid: object id
    :param data: event data. Ex {'opid':opid, 'op':op, 'params':params, 'response':response}
    :param creation: event creation data
    :param source: event source
    :param creation: creation date
    :param dest: event dest 
    """
    #logger = getLogger('gibbon.cloudapi')
    objtype = 'event'
    objdef = ''
    objdesc = ''
    
    def __init__(self, controller, oid=None, objid=None, data=None, 
                       source=None, dest=None, creation=None):
        self.logger = getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.controller = controller
        self.oid = oid
        self.objid = str2uni(objid)
        self.data = data
        self.source = source
        self.dest = dest  
    
    def __repr__(self):
        return "<ApiEvent id='%s' objid='%s'>" % (self.oid, self.objid)
    
    @property
    def dbauth(self):
        return self.controller.dbauth    
    
    @property
    def api_client(self):
        return self.controller.module.api_manager.api_client 
    
    @property
    def job_manager(self):
        return self.controller.module.job_manager    
    
    @staticmethod
    def get_type(self):
        """ """        
        return (self.type, self.definition, self.__class__)    
    
    @staticmethod
    def _get_value(objtype, args):
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    @watch
    def info(self):
        """Get event infos.
        
        :return: Dictionary with info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)        
        creation = str2uni(self.creation.strftime("%d-%m-%y %H:%M:%S"))
        return {u'id':self.oid, u'objid':self.objid, u'data':self.data, 
                u'source':self.source, u'dest':self.dest, 
                u'creation':self.creation}

    @watch
    def publish(self, objtype, event_type):
        """Publish event to event consumer.
        
        :param event_type: type of event
        """
        if self.source is None:
            self.source = {u'user':operation.user[0],
                           u'ip':operation.user[1],
                           u'identity':operation.user[2]}
            
        if self.dest is None:
            self.dest = {u'ip':self.controller.module.api_manager.server_name,
                         u'port':self.controller.module.api_manager.http_socket,
                         u'objid':self.objid, 
                         u'objtype':objtype,
                         u'objdef':self.objdef}      
        
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(event_type, self.data, self.source, self.dest)
        except Exception as ex:
            self.logger.warning('Event can not be published. Event producer is not configured - %s' % ex)

    def init_object(self):
        """ """
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                """
                # call only once during db initialization
                """
                # add object type
                class_name = self.__class__.__module__ + '.' + self.__class__.__name__
                obj_types = [(self.objtype, self.objdef, class_name)]
                self.dbauth.add_object_types(obj_types)
                
                # add object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc+" events")]
                actions = self.dbauth.get_object_action()
                self.dbauth.add_object(objs, actions)
                
                self.logger.debug('Register api object: %s' % objs)
            except (QueryError, TransactionError) as ex:
                self.logger.error(ex, exc_info=True)
                raise ApiManagerError(ex)
        # use httpclient
        else:
            """
            # call only once during db initialization
            """
            # add object type
            class_name = self.__class__.__module__ + '.' + self.__class__.__name__
            #obj_types = [(self.objtype, self.objdef, class_name)]
            #self.rpc_client.add_object_types(self.objtype, self.objdef, class_name)
            self.api_client.add_object_types(self.objtype, self.objdef, class_name)
            
            # add object and permissions
            objs = self._get_value(self.objdef, [])
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.api_client.add_object(self.objtype, self.objdef, objs, self.objdesc+" events")
            
            self.logger.debug('Register api object: %s' % objs)            
        '''
        # use rpcclient
        else:
            """
            # call only once during db initialization
            """
            # add object type
            class_name = self.__class__.__module__ + '.' + self.__class__.__module__+'.'+self.__class__.__name__
            #obj_types = [(self.objtype, self.objdef, class_name)]
            #self.rpc_client.add_object_types(self.objtype, self.objdef, class_name)
            self.rpc_httpclient.add_object_types(self.objtype, self.objdef, class_name)
            
            # add object and permissions
            objs = self._get_value(self.objdef, [])
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.rpc_httpclient.add_object(self.objtype, self.objdef, objs)
            
            self.logger.debug('Register api object: %s' % objs)
        '''

    def register_object(self, args, desc=''):
        """Register object types, objects and permissions related to module.
        
        :param args:
        """
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                # add object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objs = [(obj_type, self._get_value(self.objdef, args), 
                         u'%s events' % desc)]
                actions = self.dbauth.get_object_action()
                self.dbauth.add_object(objs, actions)
                
                self.logger.debug('Register api object: %s:%s %s' % 
                                  (self.objtype, self.objdef, objs))
            except (QueryError, TransactionError) as ex:
                self.logger.error(ex, exc_info=True)
                raise ApiManagerError(ex)
        # use httpclient
        else:
            # add object and permissions
            objs = self._get_value(self.objdef, args)
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.api_client.add_object(self.objtype, self.objdef, objs, 
                                       u'%s events' % desc)
            
            self.logger.debug('Register api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objs))
        '''
        # use rpcclient
        else:
            # add object and permissions
            objs = self._get_value(self.objdef, args)
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.rpc_httpclient.add_object(self.objtype, self.objdef, objs)
            
            self.logger.debug('Register api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objs))
        '''

    def deregister_object(self, args):
        """Deregister object types, objects and permissions related to module.
        
        :param args: 
        """
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                # remove object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objid = self._get_value(self.objdef, args)
                self.dbauth.remove_object(objid=objid, objtype=obj_type)
                self.logger.debug('Deregister api object: %s:%s %s' % 
                                  (self.objtype, self.objdef, objid))
            except (QueryError, TransactionError) as ex:
                self.logger.error(ex, exc_info=True)
                raise ApiManagerError(ex)
        # use httpclient
        else:
            # add object and permissions
            objid = self._get_value(self.objdef, args)
            #self.rpc_client.remove_object(self.objtype, self.objdef, objid)
            self.api_client.remove_object(self.objtype, self.objdef, objid)
            
            self.logger.debug('Deregister api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objid))
        '''            
        # use rpcclient
        else:
            # add object and permissions
            objid = self._get_value(self.objdef, args)
            #self.rpc_client.remove_object(self.objtype, self.objdef, objid)
            self.rpc_httpclient.remove_object(self.objtype, self.objdef, objid)
            
            self.logger.debug('Deregister api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objid))
        '''
    
    def get_session(self):
        """open db session"""
        return self.controller.get_session()
        
    def release_session(self, dbsession):
        """release db session"""
        return self.controller.release_session(dbsession)

def make_event_class(name, **kwattrs):
    return type(name, (ApiEvent,), dict(**kwattrs))

class ApiObject(object):
    """ """
    objtype = ''
    objdef = ''
    objdesc = ''
    objuri = u''
    
    def __init__(self, controller, oid=None, objid=None, name=None, 
                 desc=None, active=None):
        self.logger = getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
        
        self.controller = controller
        self.oid = oid
        self.uuid = None
        self.name = str2uni(name)
        self.objid = str2uni(objid)
        self.desc = str2uni(desc)
        self.active = active
        
        self._admin_role_prefix = 'admin'
        
        self.event_class = make_event_class(self.__class__.__module__+'.'+self.__class__.__name__+'Event',
                                            objdef=self.objdef, 
                                            objdesc=self.objdesc)
    
    def __repr__(self):
        return "<%s id='%s' objid='%s' name='%s'>" % (
                        self.__class__.__module__+'.'+self.__class__.__name__, 
                        self.oid, self.objid, self.name)
 
    @property
    def dbauth(self):
        return self.controller.dbauth
    
    @property
    def job_manager(self):
        return self.controller.module.job_manager    

    @property
    def api_client(self):
        return self.controller.module.api_manager.api_client
    
    @staticmethod
    def get_type(self):
        """ """        
        return (self.type, self.definition, self.__class__)    
    
    def get_user(self):
        """ """
        user = {u'user':operation.user[0],
                u'server':operation.user[1],
                u'identity':operation.user[2]}
        return user
    
    @staticmethod
    def _get_value(objtype, args):
        #getLogger('gibbon.cloudapi.process').debug(objtype)
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    def init_object(self):
        """ """
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                """
                # call only once during db initialization
                """
                # add object type
                class_name = self.__class__.__module__ +'.'+self.__class__.__name__
                obj_types = [(self.objtype, self.objdef, class_name)]
                self.dbauth.add_object_types(obj_types)
                
                # add object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc)]
                actions = self.dbauth.get_object_action()
                self.dbauth.add_object(objs, actions)
                
                # register event related to ApiObject
                self.event_class(self.controller).init_object()
                
                self.logger.debug('Register api object: %s' % objs)
            except (QueryError, TransactionError) as ex:
                self.logger.warn(ex.value)
                #raise ApiManagerError(ex)
                
        # use httpclient
        else:
            try:
                """
                # call only once during db initialization
                """
                # add object type
                class_name = self.__class__.__module__ +'.'+self.__class__.__name__
                #obj_types = [(self.objtype, self.objdef, class_name)]
                #self.rpc_client.add_object_types(self.objtype, self.objdef, class_name)
                self.api_client.add_object_types(self.objtype, self.objdef, class_name)
                
                # add object and permissions
                objs = self._get_value(self.objdef, [])
                #self.rpc_client.add_object(self.objtype, self.objdef, objs)
                self.api_client.add_object(self.objtype, self.objdef, objs, self.objdesc)
                
                # register event related to ApiObject
                self.event_class(self.controller).init_object()
                
                self.logger.debug('Register api object: %s' % objs)
            except ApiManagerError as ex:
                self.logger.warn(ex.value)
                #raise ApiManagerError(ex)            

    def register_object(self, args, desc=''):
        """Register object types, objects and permissions related to module.
        
        :param args:
        """
        self.logger.debug('Register api object - START')
        
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                # add object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objs = [(obj_type, self._get_value(self.objdef, args), desc)]
                actions = self.dbauth.get_object_action()
                self.dbauth.add_object(objs, actions)
                
                # register event related to ApiObject
                self.event_class(self.controller).register_object(args, desc)                
                
                self.logger.debug('Register api object %s:%s %s - STOP' % 
                                  (self.objtype, self.objdef, objs))
            except (QueryError, TransactionError) as ex:
                self.logger.error('Register api object: %s - ERROR' % (ex.desc))
                raise ApiManagerError(ex.desc, code=2020)
        # use httpclient
        else:
            # add object and permissions
            objs = self._get_value(self.objdef, args)
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.api_client.add_object(self.objtype, self.objdef, objs, desc)
            
            # register event related to ApiObject
            self.event_class(self.controller).register_object(args, desc=desc)
            
            self.logger.debug('Register api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objs))
            
    def deregister_object(self, args):
        """Deregister object types, objects and permissions related to module.
        
        :param args: 
        """
        self.logger.debug('Deregister api object - START')
        
        # if module has an instance of dbauth use it, else use rcpclient
        if 'dbauth' in self.controller.__dict__:
            try:
                # remove object and permissions
                obj_type = self.dbauth.get_object_type(objtype=self.objtype, 
                                                       objdef=self.objdef)[0]
                objid = self._get_value(self.objdef, args)
                self.dbauth.remove_object(objid=objid, objtype=obj_type)
                
                # deregister event related to ApiObject
                self.event_class(self.controller).deregister_object(args)
                
                self.logger.debug('Deregister api object %s:%s %s - STOP' % 
                                  (self.objtype, self.objdef, objid))                
            except (QueryError, TransactionError) as ex:
                self.logger.error('Deregister api object: %s - ERROR' % (ex.desc))
                raise ApiManagerError(ex.desc, code=2021)
        # use httpclient
        else:
            # add object and permissions
            objid = self._get_value(self.objdef, args)
            #self.rpc_client.remove_object(self.objtype, self.objdef, objid)
            self.api_client.remove_object(self.objtype, self.objdef, objid)
            
            # deregister event related to ApiObject
            self.event_class(self.controller).deregister_object(args)            
            
            self.logger.debug('Deregister api object %s:%s %s - STOP' % 
                              (self.objtype, self.objdef, objid))
    
    def get_session(self):
        """open db session"""
        return self.controller.get_session()
        
    def release_session(self, dbsession):
        """release db session"""
        return self.controller.release_session(dbsession)
    
    def event(self, op, params, response):
        """Publish an event to event queue.
        
        :param op: operation to audit
        :param params: operation params
        :param response: operation response.
        """
        objid = '*'
        if self.objid is not None: objid = self.objid
        self.event_class(self.controller, objid=objid, 
                         data={'opid':id_gen(), 
                               'op':op, 
                               'params':params,
                               'response':response}).publish(self.objtype, 'syncop')

    def event_job(self, op, opid, params, response):
        """Publish a job event to event queue.
        
        :param op: operation to audit
        :param opid: operation id to audit
        :param params: operation params
        :param response: operation response.
        """
        objid = '*'
        if self.objid is not None: objid = self.objid
        self.event_class(self.controller, objid=objid, 
                         data={'opid':opid, 'op':op,
                               'params':params,
                               'response':response}).publish(self.objtype, 'asyncop')

    '''
    def event_process(self, op, process, task, params, response):
        """Publish a process event to event queue.
        
        :param process: process identifier (name, id)
        :param task: task identifier (name, id)
        :param params: operation params
        :param response: operation response.
        """
        objid = '*'
        if self.objid is not None: objid = self.objid
        if process is None:
            process = [None, None]
        self.event_class(self.controller, objid=objid,
                         data={'op':op, 'process':process[0], 'processid':process[1], 
                               'task':task[0], 'taskid':task[1],
                               'params':params,
                               'response':response}).publish(self.objtype, 'process')'''

    def event_monitor(self, op, platform, component, status, metrics=None):
        """Publish a monitor event to event queue.
        
        :param platform: platform identifier (name, id)
        :param component: platform component identifier (name, id)
        :param status: platform component status
        :param metrics: platform component metrics
        """
        objid = '*'
        if self.objid is not None: objid = self.objid
        self.event_class(self.controller, objid=objid,
                         data={'op':op, 'platform':platform, 'component':component, 
                               'status':status, 'metrics':metrics}).publish(
                                            self.objtype, 'monitor')

    def get_field(self, obj, name):
        """Get object field if exist. Return None if it can be retrieved 
        
        :param obj: object
        :param name: object field name
        :return: field value or None
        """
        try:
            return obj.__dict__[name]
        except:
            return None

class ApiView(FlaskView):
    """ """
    prefix = 'identity:'
    expire = 1800
    #logger = getLogger('gibbon.cloudapi.view')
    RESPONSE_MIME_TYPE = ['json', 'bson', 'xml']
    
    def __init__(self, *argc, **argv):
        FlaskView.__init__(self, *argc, **argv)
        self.logger = getLogger(self.__class__.__module__+ \
                                        '.'+self.__class__.__name__)
    
    def _get_response_mime_type(self):
        """ """
        try:
            self.response_mime = request.headers['Accept']
        except:
            self.response_mime = 'json'
        
        if self.response_mime not in self.RESPONSE_MIME_TYPE:
            self.logger.error('Response mime type %s is not supported' % 
                               self.response_mime)
            self.response_mime = 'json'
        
        self.logger.debug("Response mime type: %s" % self.response_mime)
    
    def _get_token(self):
        # get uid and sign from headers
        try:
            header = request.headers
            uid = header['uid']
            sign = header['sign']
            data = request.path
            self.logger.debug('Uid: %s' % uid)
            self.logger.debug('Sign: %s' % sign)
            self.logger.debug('Data: %s' % data)
        except:
            raise ApiManagerError('Error retrieving token and sign from http header', 
                                  code=401)
        return (uid, sign, data)
    
    @watch
    def authorize_request(self, module):
        """
        
        :raise AuthViewError:
        :raise ApiManagerError:
        """
        self.logger.debug('Verify api authorization: %s' % request.path)

        # get identity and verify signature
        uid, sign, data = self._get_token()
        controller = module.get_controller()
        identity = controller.verify_request_signature(uid, sign, data)
        
        # get user permissions from identity
        try:
            # get user permission
            user = identity['user']
            operation.perms = user['perms']
            operation.user = (user['name'], identity['ip'], uid, identity['seckey'])
            #perms = user.get_perms()
            self.logger.debug('Get user %s permissions' % (user['name']))
        except Exception as ex:
            msg = 'Error retrieving user %s permissions: %s' % (user['name'], ex)
            raise ApiManagerError(msg, code=401)
        
        #return user

    # response methods
    @watch    
    def get_error(self, exception, code, msg):
        error = {u'status':u'error', 
                 u'api':request.path,
                 u'operation':request.method,
                 #u'data':request.data,
                 u'exception':exception,
                 u'code':code, 
                 u'msg':str(msg)}
        self.logger.error(u'Api response: %s' % truncate(error))
            
        if code in [400, 401, 403, 404, 405, 406, 408, 409, 415, 500]:
            status = code
        else:
            status = 400
        
        self.logger.error(u'Code: %s, Error: %s' % (code, exception), 
                          exc_info=True)
        if self.response_mime == u'json':
            return Response(response=json.dumps(error), 
                            mimetype=u'application/json', 
                            status=status)
        elif self.response_mime == u'bson':
            return Response(response=json.dumps(error), 
                            mimetype=u'application/bson', 
                            status=status)
        elif self.response_mime == u'xml':
            xml = dicttoxml.dicttoxml(error)
            return Response(response=xml, mimetype=u'text/xml', status=status)
        else:  
            # 415 Unsupported Media Type
            return Response(response=u'', 
                            mimetype=u'text/plain', 
                            status=415)           

    @watch
    def get_response(self, response, code=200):
        try:
            res = {u'status':u'ok',
                   u'api':request.path,
                   u'operation':request.method,
                   #u'data':request.data,
                   u'response':response}
            self.logger.debug(u'Api response: %s' % truncate(res))
            
            if self.response_mime == u'json':
                resp = json.dumps(res)
                return Response(resp, 
                                mimetype=u'application/json',
                                status=code)
            elif self.response_mime == u'bson':
                return Response(json.dumps(res), 
                                mimetype=u'application/bson',
                                status=code)
            elif self.response_mime == u'xml':
                xml = dicttoxml.dicttoxml(res)
                return Response(xml, 
                                mimetype=u'text/xml',
                                status=code)
            else:
                # 415 Unsupported Media Type
                return Response(response='', 
                                mimetype=u'text/plain', 
                                status=code)
        except Exception as ex:
            raise ApiManagerError(u'Error creating response - %s' % ex, code=400)
    
    def dispatch(self, controller, data, *args, **kwargs):
        """http inner function. Override to implement apis.
        """
        raise NotImplementedError()    
    
    def dispatch_request(self, module=None, secure=True, *args, **kwargs):
        """Base dispatch_request method. Extend this method in your child class.
        """
        # set reqeust timeout
        res = None
        
        timeout = Timeout(module.api_manager.api_timeout)
        timeout.start()

        start = time()
        dbsession = None
        try:
            headers = [u'%s: %s' % (k,v) for k,v in request.headers.iteritems()]
            self.logger.debug(u'Invoke api: %s [%s] - START' % (request.path, request.method))
            self.logger.debug(u'Api request headers: %s' % headers)
            self.logger.debug(u'Api request query: %s' % request.query_string)
            self.logger.debug(u'Api request data: %s' % request.data)
            self._get_response_mime_type()     
            
            if secure is True:
                self.authorize_request(module)
            
            # open database session.
            dbsession = module.get_session()
            controller = module.get_controller()
            
            # get request data
            try:
                data = json.loads(request.data)
            except:
                data = None            
        
            resp = self.dispatch(controller, data, *args, **kwargs)
            if isinstance(resp, tuple):
                res = self.get_response(resp[0], code=resp[1])
            else:
                res = self.get_response(resp)
            
            # unset user permisssions in local thread object
            operation.perms = None
            
            # get request elapsed time
            elapsed = round(time() - start, 4)
            self.logger.debug('Invoke api: %s [%s] - STOP - %s' % (request.path, 
                                                                   request.method,
                                                                   elapsed))
        except Timeout:
            # get request elapsed time
            elapsed = round(time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, 
                                                                    request.method,
                                                                    elapsed))             
            msg = 'Request %s %s timeout' % (request.path, request.method) 
            return self.get_error('Timeout', 408, msg)
        except ApiManagerError as ex:
            # get request elapsed time
            elapsed = round(time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, 
                                                                    request.method,
                                                                    elapsed))
            return self.get_error('ApiManagerError', ex.code, ex.value)
        except Exception as ex:
            # get request elapsed time
            elapsed = round(time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, 
                                                                    request.method,
                                                                    elapsed))
            return self.get_error('Exception', 400, str(ex))
        finally:
            if dbsession is not None:
                module.release_session(dbsession)
            timeout.cancel()
            self.logger.debug('Timeout released')

        return res
    
    @staticmethod
    def register_api(module, rules, version=None):
        """
        :param module: beehive module
        :param rules: url rules to register. Ex. 
                      [('/jobs', 'GET', ListJobs.as_view('jobs')), {'secure':False}]
        """
        logger = getLogger(__name__)
        #logger = getLogger('gibbon.cloudapi.view')
        
        # get version
        if version is None:
            version = module.get_controller().version
        
        # get app
        app = module.api_manager.app
        
        # regiter url rules
        view_num = 0
        for rule in rules:
            uri = u'/%s/%s/' % (version, rule[0])
            defaults = {'module':module}
            defaults.update(rule[3])
            view_name = "%s-%s" % (get_class_name(rule[2]), view_num)
            view_func = rule[2].as_view(str(view_name))
            app.add_url_rule(uri,
                             methods=[rule[1]],
                             view_func=view_func, 
                             defaults=defaults)
            view_num += 1
            logger.debug('Add url rule: %s %s' % (uri, rule[1]))
            
            # append route to module
            module.api_routes.append({'uri':uri, 'method':rule[1]})            
 
class ApiClient(BeehiveApiClient):
    """ """
    def __init__(self, auth_endpoints, user, pwd, catalog_id=None):
        BeehiveApiClient.__init__(self, auth_endpoints, user, pwd, catalog_id)
    
    def admin_request(self, subsystem, path, method, data=u'', 
                      other_headers=None):
        """Make api request using module internal admin user credentials.
        
        :raise ApiManagerError:
        """
        if self.exist(self.uid) is False:
            self.login()
        
        try:
            res = self.send_signed_request(subsystem, path, method, data, 
                                           self.uid, self.seckey, other_headers)
        except ApiManagerError as ex:
            self.logger.error('Send admin request to %s using uid %s: %s' % 
                              (path, self.uid, ex.value))
            raise ApiManagerError(ex.value, code=ex.code)
        
        if res['status'] == 'error':
            self.logger.error('Send admin request to %s using uid %s: %s' % 
                              (path, self.uid, res['msg']))
            raise ApiManagerError(res['msg'], code=res['code'])
        else:
            self.logger.info('Send admin request to %s using uid %s: %s' % 
                             (path, self.uid, truncate(res)))
            return res['response']

    def user_request(self, module, path, method, data=u'', other_headers=None):
        """Make api request using module current user credentials.
        
        :raise ApiManagerError:
        """
        try:
            # get user logged uid and password
            uid = operation.user[2]
            seckey = operation.user[3]
            res = self.send_signed_request(module, path, method, data, uid, 
                                           seckey, other_headers)
        except ApiManagerError as ex:
            self.logger.error('Send user request to %s using uid %s: %s' % 
                              (path, self.uid, ex.value))
            raise
        
        if res['status'] == 'error':
            self.logger.error('Send user request to %s using uid %s: %s' % 
                              (path, self.uid, res['msg']))
            raise ApiManagerError(res['msg'], code=res['code'])
        else:
            self.logger.info('Send user request to %s using uid %s: %s' % 
                             (path, self.uid, truncate(res)))            
            return res['response']    
    



