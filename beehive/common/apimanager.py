'''
Created on Oct 31, 2014

@author: darkbk
'''
import logging
import time
import binascii
import pickle
import redis
import ujson as json
from zlib import decompress
from uuid import uuid4
from base64 import b64decode
from re import match
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from flask import request, Response
#from flask.views import MethodView as FlaskMethodView
#from flask.views import View as FlaskView
from flask.views import MethodView as FlaskView
from random import randint
from beecell.perf import watch
from beecell.db import TransactionError, QueryError
from beecell.db.manager import MysqlManager, SqlManagerError, RedisManager
from beecell.auth import extract
from beecell.simple import str2uni, id_gen, import_class, truncate, get_class_name,\
    parse_redis_uri, get_remote_ip, nround, str2bool, format_date
from beecell.sendmail import Mailer
from beehive.common.data import operation, trace
from beecell.auth import AuthError, DatabaseAuth, LdapAuth, SystemUser
from beecell.logger.helper import LoggerHelper
from beecell.flask.redis_session import RedisSessionInterface
import gevent
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.common.model.config import ConfigDbManager
from beehive.common.model.authorization import AuthDbManager, Role
from beehive.common.event import EventProducerRedis
from flasgger import Swagger, Schema, fields, SwaggerView
from beecell.dicttoxml import dicttoxml
from beecell.flask.api_util import get_error
try:
    from beecell.server.uwsgi_server.wrapper import uwsgi_util
except:
    pass
from re import escape
from marshmallow.validate import OneOf, Range
from copy import deepcopy

class ApiManagerWarning(Exception):
    """Main excpetion raised by api manager and childs
    
    **Parameters:**
        * **value** (:py:class:`str`): error description
        * **code** (:py:class:`int`): error code [default=400]
    """
    def __init__(self, value, code=208):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return u'ApiManagerWarning: %s' % self.value 

    def __str__(self):
        return u'%s' % self.value

class ApiManagerError(Exception):
    """Main excpetion raised by api manager and childs
    
    **Parameters:**
        * **value** (:py:class:`str`): error description
        * **code** (:py:class:`int`): error code [default=400]
    """
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return u'ApiManagerError: %s' % self.value 

    def __str__(self):
        return u'%s' % self.value

class ApiManager(object):
    """Api Manager
    
    **Parameters:**
    
        * **params** (:py:class:`dict`): configuration params
        * **app** (:py:class:`int`): error code [default=400]    
    """
    #logger = logging.getLogger('gibbon.cloudapi')
    
    def __init__(self, params, app=None, hostname=None):
        self.logger = logging.getLogger(self.__class__.__module__+ \
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
        
        # swagger reference
        self.swagger = Swagger(self.app, template_file=u'swagger.yml')
        
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
        database_uri = self.params.get(u'database_uri', None)
        if database_uri != None:
            self.create_pool_engine((database_uri, 5, 10, 10, 1800))
        
        # send mail
        self.mailer = None
        self.mail_sender = None
        
        # identity
        self.prefix = u'identity:'
        self.expire = 3600
        
        # scheduler
        self.redis_taskmanager = None
        self.redis_scheduler = None

    def create_pool_engine(self, dbconf):
        """Create mysql pool engine.
        
        **Parameters:**
        
            * **dbconf** (:py:class:`list`): 
                (uri, timeout, pool_size, max_overflow, pool_recycle)
        """
        try:
            db_uri = dbconf[0]
            connect_timeout = dbconf[1]
            pool_size = dbconf[2]
            max_overflow = dbconf[3]
            pool_recycle = dbconf[4]
            self.db_manager = MysqlManager(u'db_manager01', db_uri, 
                                           connect_timeout=connect_timeout)
            self.db_manager.create_pool_engine(pool_size=pool_size, 
                                               max_overflow=max_overflow, 
                                               pool_recycle=pool_recycle)
        except SqlManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)
    
    def create_simple_engine(self, dbconf):
        """Create mysql simple engine.
        
        **Parameters:**
        
            * **dbconf** (:py:class:`list`): 
                (uri, timeout)        
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
        
    def is_engine_configured(self):    
        """Return True if database engine is configured
        """
        if self.db_manager is not None:
            return True
        return False
        
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

    def get_identity(self, uid):
        """Get identity
        
        **Parameters:**
        
            * **uid** (:py:class:`str`): identity id
            
        **Returns:**

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
            data[u'ttl'] = self.redis_manager.ttl(self.prefix + uid)
            self.logger.debug(u'Get identity %s from redis' % (uid))           
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=401)

    def get_identities(self):
        """Get identities
        
        **Returns:**

            .. code-block:: python
               
               [
                   {u'uid':..., 
                    u'user':..., 
                    u'timestamp':..., 
                    u'ttl':..., 
                    u'ip':...},
                ...
                ]
        """
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
    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.
        
        **Parameters:**
        
            * **user** (:py:class:`str`): user
            * **pwd** (:py:class:`str`): password
            * **user_ip** (:py:class:`str`): user ip address
            
        **Returns:**

            .. code-block:: python
               
               {u'uid':..., 
                u'user':..., 
                u'timestamp':..., 
                u'pubkey':..., 
                u'seckey':...}
            
        **Raise:** :class:`ApiManagerError`         
        """
        try:
            identity = self.api_client.simplehttp_login(user, pwd, user_ip)
        except BeehiveApiClientError as ex:
            self.logger.error(ex.value, exc_info=1)
            raise ApiManagerError(ex.value, code=ex.code)
        
        return identity

    @watch
    def get_oauth2_identity(self, token):
        """Get identity that correspond to oauth2 access token

        **Parameters:**
        
            * **token** (:py:class:`str`): identity id
            
        **Returns:**

            .. code-block:: python
               
               {u'uid':..., 
                u'user':..., 
                u'timestamp':..., 
                u'pubkey':..., 
                u'seckey':...}
            
        **Raise:** :class:`ApiManagerError`
        """
        identity = self.get_identity(token)
        self.redis_manager.expire(self.prefix + token, self.expire)
        self.logger.debug(u'Extend identity %s expire' % (token))
        return identity

    def verify_request_signature(self, uid, sign, data):
        """Verify Request signature.
        
        **Parameters:**
        
            * **uid** (:py:class:`str`): identity id
            * **sign** (:py:class:`str`): request sign
            * **data** (:py:class:`str`): request data
            
        **Returns:**

            .. code-block:: python
               
               {u'uid':..., 
                u'user':..., 
                u'timestamp':..., 
                u'pubkey':..., 
                u'seckey':...}
            
        **Raise:** :class:`ApiManagerError`
        """
        # retrieve token and sign
        #uid, sign, data = self.__get_token()
        
        # get identity
        identity = self.get_identity(uid)
        # verify signature
        pubkey64 = identity[u'pubkey']
        
        try:
            # import key        
            #signature = binascii.a2b_base64(sign)
            signature = binascii.a2b_hex(sign)
            pub_key = binascii.a2b_base64(pubkey64)
            key = RSA.importKey(pub_key)
            
            # create data hash
            hash_data = SHA256.new(data)
            #self.logger.debug('Get data: %s' % data)
            #self.logger.debug('Created hash: %s' % binascii.b2a_base64(
            #                                            hash_data.digest()))

            # verify sign
            verifier = PKCS1_v1_5.new(key)
            res = verifier.verify(hash_data, signature)
            
            # extend expire time of the redis key
            if res is True:
                self.redis_manager.expire(self.prefix + uid, self.expire)
                self.logger.debug(u'Data signature %s for identity %s is valid. '\
                                  u'Extend expire.' % (sign, uid))
        except:
            self.logger.error(u'Data signature for identity %s is not valid' % uid)
            raise ApiManagerError(u'Data signature for identity %s is not valid' % uid, code=401)

        if not res:
            raise ApiManagerError(u'Data signature for identity %s is not valid' % uid, code=401)
        else:    
            self.logger.debug(u'Data signature is valid')

        return identity

    def register_modules(self):
        self.logger.info('Configure modules - START')
        
        module_classes = self.params[u'api_module']
        if type(module_classes) is str:
            module_classes = [module_classes]
        
        for item in module_classes:
            # import module class
            module_class = import_class(item)
            # instance module class
            module = module_class(self)
            self.logger.info(u'Register module: %s' % item)
        
        if u'api_plugin' in self.params:
            plugin_pkgs = self.params[u'api_plugin']
            if type(plugin_pkgs) is str:
                plugin_pkgs = [plugin_pkgs]
            for plugin_pkg in plugin_pkgs:
                name, class_name = plugin_pkg.split(u',')
                # import plugin class
                plugin_class = import_class(class_name)
                # get module plugin
                module = self.modules[name]
                # instance plugin class
                plugin = plugin_class(module)
                # register plugin
                plugin.register()
                self.logger.info(u'Register plugin: %s' % class_name)
        
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

        self.logger.info(u'Configure server - CONFIGURE')

        if self.is_engine_configured() is True:
            # open db session
            self.get_session()
            operation.perms = None
            
            try:
                # get configurator instance
                configurator = ConfigDbManager()     
                
                ##### oauth2 configuration #####
                self.logger.info(u'Configure oauth2 - CONFIGURE')
                try:
                    self.oauth2_endpoint = configurator.get(
                        app=self.app_name, group=u'oauth2', name=u'endpoint')[0].value
                    self.logger.info(u'Setup oauth2 endpoint: %s' % self.oauth2_endpoint)
                    self.logger.info(u'Configure oauth2 - CONFIGURED')
                except:
                    self.logger.warning(u'Configure oauth2 - NOT CONFIGURED')
                ##### oauth2 configuration #####                
                
                ##### redis configuration #####
                self.logger.info(u'Configure redis - CONFIGURE')
                # connect to redis
                redis_uri = configurator.get(app=self.app_name, 
                                             group='redis', 
                                             name='redis_01')[0].value
                # parse redis uri
                host, port, db = parse_redis_uri(redis_uri)
                    
                # set redis manager
                self.redis_manager = redis.StrictRedis(
                    host=host, port=int(port), db=int(db))
                
                # app session
                if self.app is not None:
                    self.app.session_interface = RedisSessionInterface(
                        redis=self.redis_manager)
                    self.logger.info(u'Setup redis session manager: %s' % 
                                     self.app.session_interface)
    
                self.logger.info(u'Configure redis - CONFIGURED')  
                ##### redis configuration #####
                
                ##### scheduler reference configuration #####
                self.logger.info(u'Configure scheduler reference - CONFIGURE')
                
                try:
                    from beehive.common.task.manager import configure_task_manager
                    from beehive.common.task.manager import configure_task_scheduler
                    
                    # task manager
                    broker_url = self.params['broker_url']
                    result_backend = self.params['result_backend']
                    configure_task_manager(broker_url, result_backend)
                    self.redis_taskmanager = RedisManager(result_backend)
                    
                    # scheduler
                    broker_url = self.params['broker_url']
                    schedule_backend = self.params['result_backend']                                                    
                    configure_task_scheduler(broker_url, schedule_backend)
                    self.redis_scheduler = RedisManager(schedule_backend)
    
                    self.logger.info(u'Configure scheduler reference - CONFIGURED')
                except:
                    self.logger.warning(u'Configure scheduler reference - NOT CONFIGURED')            
                ##### scheduler reference configuration #####            
                
                ##### security configuration #####
                # configure only with auth module
                try:
                    confs = configurator.get(app=self.app_name, group='auth')
                    self.logger.info(u'Configure security - CONFIGURE')
                    
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

                    self.logger.info(u'Configure security - CONFIGURED')
                except:
                    self.logger.warning(u'Configure security - NOT CONFIGURED')
                ##### security configuration #####
        
                ##### camunda configuration #####
                try:
                    self.logger.debug(u'Configure Camunda - CONFIGURE')            
                    from beedrones.camunda import WorkFlowEngine as CamundaEngine
                    confs = configurator.get(app=self.app_name, group='bpmn')
                    for conf in confs:
                        item = json.loads(conf.value)
                    self.camunda_engine = CamundaEngine( item['conn'],
                            user=item['USER'],
                            passwd=item['PASSWD'])
                    self.logger.debug(u'Configure Camunda  - CONFIGURED')            
                except:
                    self.logger.warning(u'Configure Camunda  - NOT CONFIGURED')
                ##### camunda configuration #####

                ##### sendmail configuration #####
                try:
                    self.logger.debug(u'Configure sendmail - CONFIGURE')            
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
    
                    self.logger.info(u'Configure sendmail - CONFIGURED')
                except:
                    self.logger.warning(u'Configure sendmail - NOT CONFIGURED')
                ##### sendmail configuration #####
    
                ##### gateway configuration #####
                try:    
                    conf = configurator.get(app=self.app_name, group='gateway')
                    self.logger.info(u'Configure gateway - CONFIGURE')
                    for item in conf:
                        gw = json.loads(item.value)
                        self.gateways[gw['name']] = gw
                        self.logger.info('Setup gateway: %s' % gw)
                    self.logger.info(u'Configure gateway - CONFIGURED')
                except:
                    self.logger.warning(u'Configure gateway - NOT CONFIGURED')
                ##### gateway configuration #####
        
                ##### event queue configuration #####
                try:
                    self.logger.info(u'Configure event queue- CONFIGURE')
                    conf = configurator.get(app=self.app_name, 
                                            group=u'queue',
                                            name=u'queue.event')
    
                    # setup event producer
                    conf = json.loads(conf[0].value)
                    # set redis manager   
                    self.redis_event_uri = conf[u'uri']
                    self.redis_event_exchange = conf[u'queue']
                    # create instance of event producer
                    self.event_producer = EventProducerRedis(
                                                        self.redis_event_uri, 
                                                        self.redis_event_exchange,
                                                        framework=u'kombu')
                    self.logger.info(u'Configure exchange %s on %s' % 
                                     (self.redis_event_exchange, 
                                      self.redis_event_uri))
                    self.logger.info(u'Configure event queue - CONFIGURED')
                except:
                    self.logger.warning(u'Configure event queue - NOT CONFIGURED')                
                ##### event queue configuration #####
                
                ##### monitor queue configuration #####
                try:
                    self.logger.info(u'Configure monitor queue- CONFIGURE')
                    try:
                        from beehive_monitor.producer import MonitorProducerRedis
                    except:
                        raise Exception(u'beehive_monitor is not installed')
                    
                    conf = configurator.get(app=self.app_name, 
                                            group='queue', 
                                            name='queue.monitor')
    
                    # setup monitor producer
                    conf = json.loads(conf[0].value)
                    self.redis_monitor_uri = conf['uri']
                    self.redis_monitor_channel = conf['queue']                    
                        
                    # create instance of monitor producer
                    self.monitor_producer = MonitorProducerRedis(
                                                        self.redis_monitor_uri, 
                                                        self.redis_monitor_channel)
                    self.logger.info(u'Configure queue %s on %s' % 
                                     (self.redis_monitor_channel, 
                                      self.redis_monitor_uri))                    
                    self.logger.info(u'Configure monitor queue - CONFIGURED')
                except Exception as ex:
                    self.logger.warning(u'Configure monitor queue - NOT CONFIGURED')                
                ##### monitor queue configuration #####
        
                ##### catalog queue configuration #####
                try:
                    self.logger.info(u'Configure catalog queue - CONFIGURE')
                    conf = configurator.get(app=self.app_name, 
                                            group=u'queue', 
                                            name=u'queue.catalog')
    
                    # setup catalog producer
                    conf = json.loads(conf[0].value)
                    self.redis_catalog_uri = conf[u'uri']
                    self.redis_catalog_channel = conf[u'queue']                    
                        
                    # create instance of catalog producer
                    from beehive.module.catalog.producer import CatalogProducerRedis
                    self.catalog_producer = CatalogProducerRedis(
                                                        self.redis_catalog_uri, 
                                                        self.redis_catalog_channel)
                    self.logger.info(u'Configure queue %s on %s' % 
                                     (self.redis_catalog_channel, 
                                      self.redis_catalog_uri))                    
                    self.logger.info(u'Configure catalog queue - CONFIGURED')
                except Exception as ex:
                    self.logger.warning(u'Configure catalog queue - NOT CONFIGURED')
                ##### catalog queue configuration #####          
        
                ##### tcp proxy configuration #####
                try:
                    self.logger.info(u'Configure tcp proxy - CONFIGURE')
                    conf = configurator.get(app=self.app_name, group=u'tcpproxy')                    
                    self.tcp_proxy = conf[0].value
                    self.logger.info(u'Setup tcp proxy: %s' % self.tcp_proxy)
                    self.logger.info(u'Configure tcp proxy - CONFIGURED')
                except:
                    self.logger.warning(u'Configure tcp proxy - NOT CONFIGURED') 
                ##### tcp proxy configuration #####        
    
                ##### http proxy configuration #####
                try:
                    self.logger.info(u'Configure http proxy- CONFIGURE')
                    conf = configurator.get(app=self.app_name, group=u'httpproxy')                    
                    self.http_proxy = conf[0].value
                    self.logger.info(u'Setup http proxy: %s' % self.http_proxy)
                    self.logger.info(u'Configure http proxy - CONFIGURED')
                except:
                    self.logger.warning(u'Configure http proxy - NOT CONFIGURED') 
                ##### http proxy configuration #####
                
                ##### api authentication configuration #####
                # not configure for auth module
                try:
                    self.logger.info(u'Configure apiclient - CONFIGURE')
                    
                    # get auth catalog
                    self.catalog = configurator.get(app=self.app_name, 
                                                    group=u'api', 
                                                    name=u'catalog')[0].value
                    self.logger.info(u'Get catalog: %s' % self.catalog)                
                    
                    # get auth endpoints
                    try:
                        endpoints = configurator.get(app=self.app_name, 
                                                     group=u'api', 
                                                     name=u'endpoints')[0].value
                        self.endpoints = json.loads(endpoints)
                    except:
                        # auth subsystem instance
                        self.endpoints = [self.app_uri]
                    self.logger.info(u'Get auth endpoints: %s' % self.endpoints)                    
                    
                    # get auth system user
                    auth_user = configurator.get(app=self.app_name, 
                                                 group=u'api', 
                                                 name=u'user')[0].value
                    self.auth_user = json.loads(auth_user)
                    self.logger.info(u'Get auth user: %s' % self.auth_user)

                    # configure api client
                    self.configure_api_client()                   
                    
                    self.logger.info(u'Configure apiclient - CONFIGURED')
                except Exception as ex:
                    self.logger.warning(u'Configure apiclient - NOT CONFIGURED')
                ##### api authentication configuration #####              
                
                del configurator
                
            except ApiManagerError as e:
                raise
            
            # release db session
            self.release_session()
            operation.perms = None
        
        self.logger.info(u'Configure server - CONFIGURED')
    
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
        register = self.params.get(u'register-catalog', True)
        register = str2bool(register)
        
        # skip catalog registration - usefool for temporary instance
        if register is False:
            return
        
        # register catalog
        catalog = self.catalog
        service = self.app_subsytem
        uri = self.app_uri        
        self.catalog_producer.send(self.app_endpoint_id, self.app_desc, 
                                   service, catalog, uri)
        self.logger.info(u'Register %s instance in catalog' % self.app_endpoint_id)
            
    def register_monitor(self):
        """Register instance in monitor
        """
        register = self.params.get(u'register-monitor', True)
        register = str2bool(register)
        
        # skip monitor registration - usefool for temporary instance
        if register is False:
            return
        
        # register monitor        
        self.monitor_producer.send(self.app_endpoint_id, self.app_desc, 
                                   self.app_name, {u'uri':self.app_uri})
        self.logger.info(u'Register %s instance in monitor' % self.app_endpoint_id)
                        
        
class ApiModule(object):
    """ """
    #logger = logging.getLogger('gibbon.cloudapi')
    
    def __init__(self, api_manager, name):
        self.logger = logging.getLogger(self.__class__.__module__+ \
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
    #logger = logging.getLogger('gibbon.cloudapi')
    
    def __init__(self, module):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        self.module = module

        # base event_class. Change in every controller with ApiEvent subclass
        #self.event_class = ApiEvent
        
        # child classes
        self.child_classes = []
        
        # identity        
        try:
            self.prefix = self.module.api_manager.prefix
            self.expire = self.module.api_manager.expire
        except:
            self.prefix = None
            self.expire = None
            
        # db manager
        self.dbmanager = None
            
    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+u'.'+
                                 self.__class__.__name__, id(self))    
    
    @property
    def redis_manager(self):
        return self.module.redis_manager   

    #@property
    #def job_manager(self):
    #    return self.module.job_manager
    
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
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        self.logger.info(u'Init %s - START' % self)
        self.logger.info(u'Init childs: %s' % self.child_classes)
        # init controller child classes
        for child in self.child_classes:
            child(self).init_object()
        self.logger.info(u'Init %s - STOP' % self)
    
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
    
    def get_oauth2_identity(self, token):
        """Get identity that correspond to oauth2 access token

        :param token: identity id
        :return: identity
        **Raise:** :class:`ApiManagerError`
        """
        return self.module.api_manager.get_oauth2_identity(token)

    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.
        
        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        **Raise:** :class:`ApiManagerError`
        """
        return self.module.api_manager.verify_simple_http_credentials(user, pwd, user_ip)

    @watch
    def can(self, action, objtype=None, definition=None):
        """Verify if  user can execute an action over a certain object type.
        Specify at least name or perms.
        
        :param objtype: object type. Es. 'resource', 'service' [optional]
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
                # perm = (0-pid, 1-oid, 2-type, 3-definition, 4-objid, 5-aid, 6-action)
                # Es: (5, 1, 'resource', 'container.org.group.vm', 'c1.o1.g1.*', 6, 'use')
                perm_objtype = perm[2]
                perm_objid = perm[4]
                perm_action = perm[6]
                perm_definition = perm[3].lower()
                
                # definition is specified
                if definition is not None:
                    definition = definition.lower()
                    
                    # verify object type, definition and action. If they match 
                    # append objid to values list
                    if (perm_objtype == objtype and
                        perm_definition == definition and
                        perm_action in [u'*', action]):
                        #defs.append(perm_definition)
                        objids.append(perm_objid)
                    
                    # loop between object objids, compact objids and verify match
                    if len(objids) > 0:
                        res[definition] = objids
                elif objtype is not None:      
                    if (perm_objtype == objtype and
                        perm_action in [u'*', action]):
                        if perm_definition in res:
                            res[perm_definition].append(perm_objid)
                        else:
                            res[perm_definition] = [perm_objid]
                else:
                    if (perm_action in [u'*', action]):
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
                    definition = u''
                raise Exception(u'%s can not %s objects %s:%s' % 
                                (user, action, objtype, definition))      
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=401)

    #@watch
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

    #@watch
    def get_needs(self, args):
        """"""
        # first item *.*.*.....
        act_need = [u'*' for i in args]
        needs = [u'//'.join(act_need)]
        pos = 0
        for arg in args:
            act_need[pos] = arg
            needs.append(u'//'.join(act_need))
            pos += 1

        return set(needs)

    def check_authorization(self, objtype, objdef, objid, action):
        """This method combine can, get_needs and has_needs, Use when you want
        to verify overlap between needs and permissions for a unique object.
        
        :param objtype: object type. Es. 'resource', 'service',
        :param definition: object definition. Es. 'container.org.group.vm' [optional]                                    
        :param action: object action. Es. \*, view, insert, update, delete, use
        :param objid: object unique id. Es. \*//\*//\*, nome1//nome2//\*, nome1//nome2//nome3        
        :return: True if permissions overlap
        """
        try:
            objs = self.can(action, objtype, definition=objdef)
            
            # check authorization
            objset = set(objs[objdef.lower()])
    
            # create needs
            if action == u'insert':
                if objid is None or objid == u'*':
                    objid = u'*'
                else:
                    objid = objid + u'//*'
            needs = self.get_needs(objid.split(u'//'))
            
            # check if needs overlaps perms
            res = self.has_needs(needs, objset)
            if res is False:
                raise ApiManagerError('')
        except ApiManagerError:
            msg = "Identity %s can not '%s' objects '%s:%s' '%s'" % (
                    operation.user[2], action, objtype, objdef, objid)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=403)
        return res

    '''
    def get_superadmin_permissions(self):
        """ """
        raise NotImplementedError()'''
    
    #
    # helper model get method
    #
    def get_entity(self, entity_class, model_class, oid, authorize=True):
        """Get single entity by oid (id, uuid, name) if exists
        
        **Parameters:**
        
            * **entity_class** (): Controller ApiObject Extension class
            * **model_class** (:py:class:`ApiObject`): Model ApiObject 
                Extension class
            * **oid** (:py:class:`str`): entity model id or name or uuid
            * **authorize** (:py:class:`str`): if True check permissions for 
                authorization
            * **customize** (function): function used to customize entities. 
                Signature def customize(entity, resource)            
            
        **Returns:**
        
            entity instance
            
        **Raise:** :class:`ApiManagerError`     
        """
        try:
            entity = self.manager.get_entity(model_class, oid)
        except QueryError as ex:         
            self.logger.error(ex, exc_info=1)
            entity_name =  entity_class.__name__
            raise ApiManagerError(u'%s %s not found' % (entity_name, oid), 
                                  code=404)            
            
        # check authorization
        if authorize is True:
            self.check_authorization(entity_class.objtype, 
                                     entity_class.objdef, 
                                     entity.objid, u'view')
        
        res = entity_class(self, oid=entity.id, objid=entity.objid, 
                       name=entity.name, active=entity.active, 
                       desc=entity.desc, model=entity)
        
        # execute custom post_get
        res.post_get()        
        
        self.logger.debug(u'Get %s : %s' % 
                          (entity_class.__name__, res))
        return res

    def get_paginated_entities(self, entity_class, get_entities, 
            page=0, size=10, order=u'DESC', field=u'id', customize=None, authorize=True,
            *args, **kvargs):
        """Get entities with pagination

        :param entity_class: ApiObject Extension class
        :param get_entities: model get_entities function. Return (entities, total)
        :param name: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param page: objects list page to show [default=0]
        :param size: number of objects to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param customize: function used to customize entities. Signature
                def customize(entities, *args, **kvargs)
        :param args: custom params
        :param kvargs: custom params
        :return: (list of entity_class instances, total)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = []
        objs =  []
        
        if authorize is True:
            # verify permissions
            objs = self.can(u'view', entity_class.objtype, 
                            definition=entity_class.objdef)
            objs = objs.get(entity_class.objdef.lower())
        
        # create permission tags
        tags = []
        for p in objs:
            tags.append(self.manager.hash_from_permission(entity_class.objdef, p))
        self.logger.debug(u'Permission tags to apply: %s' % tags)
                
        try:
            entities, total = get_entities(tags=tags, page=page, size=size, 
                order=order, field=field, *args, **kvargs)
            
            for entity in entities:
                obj = entity_class(self, oid=entity.id, objid=entity.objid, 
                               name=entity.name, active=entity.active, 
                               desc=entity.desc, model=entity)
                res.append(obj)
        
            # customize enitities
            if customize is not None:
                customize(res, tags=tags, *args, **kvargs)
            
            self.logger.debug(u'Get %s (total:%s): %s' % 
                              (entity_class.__name__, total, truncate(res)))
            return res, total
        except QueryError as ex:         
            self.logger.warn(ex)
            return [], 0
    
    '''
    def get_paginated_entities2(self, object_class, get_entities, 
                              page=0, size=10, order=u'DESC', field=u'id', 
                              *args, **kvargs):
        """Get objects with pagination

        :param object_class: ApiObject Extension class
        :param get_entities: model get_entities function. Return (entities, total)
        :param page: objects list page to show [default=0]
        :param size: number of objects to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param args: custom params
        :param kvargs: custom params
        :return: (list of object_class instances, total)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can(u'view', object_class.objtype, 
                        definition=object_class.objdef)
        res = []
                
        try:
            entities, total = get_entities(page=page, size=size, order=order, 
                                           field=field, *args, **kvargs)
            
            for entity in entities:
                expiry_date = None
                if isinstance(entity, tuple):
                    expiry_date = entity[1]
                    entity = entity[0]
                
                # check authorization
                objset = set(objs[object_class.objdef.lower()])

                # create needs
                needs = self.get_needs([entity.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    try: objid=entity.objid
                    except: objid=None
                    try: active=entity.active
                    except: active=None                    
                    obj = object_class(self, oid=entity.id, objid=objid, 
                               name=entity.name, active=active, 
                               desc=entity.desc, model=entity)
                    # set expiry_date
                    if expiry_date is not None:
                        obj.expiry_date = expiry_date
                    res.append(obj)                
            
            self.logger.debug(u'Get entities %s: %s' % (object_class, len(res)))
            return res, total
        except QueryError as ex:         
            self.logger.warn(ex)
            return [], 0'''

'''
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
    objtype = u'event'
    objdef = u''
    objdesc = u''
    
    def __init__(self, controller, oid=None, objid=None, data=None, 
                       source=None, dest=None, creation=None, action=None):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        self.controller = controller
        self.oid = oid
        self.objid = str2uni(objid)
        self.data = data
        self.source = source
        self.dest = dest
        self.action = action
    
    def __repr__(self):
        return "<ApiEvent id='%s' objid='%s'>" % (self.oid, self.objid)
    
    @property
    def dbmanager(self):
        return self.controller.dbmanager    
    
    @property
    def api_client(self):
        return self.controller.module.api_manager.api_client 
    
    #@property
    #def job_manager(self):
    #    return self.controller.module.job_manager    
    
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

    def info(self):
        """Get event infos.
        
        :return: Dictionary with info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """  
        creation = str2uni(self.creation.strftime(u'%d-%m-%Y %H:%M:%S'))
        return {u'id':self.oid, u'objid':self.objid, u'data':self.data, 
                u'source':self.source, u'dest':self.dest, 
                u'creation':creation}

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
                         u'objdef':self.objdef,
                         u'action':self.action}      
        
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(event_type, self.data, self.source, self.dest)
        except Exception as ex:
            self.logger.warning(u'Event can not be published. Event producer '\
                                u'is not configured - %s' % ex)

    def init_object(self):
        """Call only once during db initialization"""
        # add object type
        self.api_client.add_object_types(self.objtype, self.objdef)
        
        # add object and permissions
        objs = self._get_value(self.objdef, [])
        self.api_client.add_object(self.objtype, self.objdef, objs, 
                                   self.objdesc+u' events')
        
        self.logger.debug(u'Register api object: %s' % objs)

    def register_object(self, args, desc=u'', objid=None):
        """Register object types, objects and permissions related to module.
        
        :param args:
        """
        # add object and permissions
        objs = self._get_value(self.objdef, args)
        #self.rpc_client.add_object(self.objtype, self.objdef, objs)
        self.api_client.add_object(self.objtype, self.objdef, objs, 
                                   u'%s events' % desc)
        
        self.logger.debug(u'Register api object: %s:%s %s' % 
                          (self.objtype, self.objdef, objs))

    def deregister_object(self, args, objid=None):
        """Deregister object types, objects and permissions related to module.
        
        :param args: 
        """
        # remove object and permissions
        objid = self._get_value(self.objdef, args)
        #self.rpc_client.remove_object(self.objtype, self.objdef, objid)
        self.api_client.remove_object(self.objtype, self.objdef, objid)
        
        self.logger.debug(u'Deregister api object: %s:%s %s' % 
                          (self.objtype, self.objdef, objid))
    
    def get_session(self):
        """open db session"""
        return self.controller.get_session()
        
    def release_session(self, dbsession):
        """release db session"""
        return self.controller.release_session(dbsession)

class ApiInternalEvent(ApiEvent):
    def __init__(self, *args, **kvargs):
        ApiEvent.__init__(self, *args, **kvargs)
        self.auth_db_manager = AuthDbManager()
    
    def init_object(self):
        """Call only once during db initialization"""
        try:
            # call only once during db initialization
            # add object type
            obj_types = [(self.objtype, self.objdef)]
            self.auth_db_manager.add_object_types(obj_types)
            
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, []), 
                     self.objdesc+u' events')]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
            
            self.logger.debug(u'Register api object: %s' % objs)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

    def register_object(self, args, desc=u'', objid=None):
        """Register object types, objects and permissions related to module.
        
        :param args:
        """
        try:
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, args), 
                     u'%s events' % desc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
            
            self.logger.debug(u'Register api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objs))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

    def deregister_object(self, args, objid=None):
        """Deregister object types, objects and permissions related to module.
        
        :param args: 
        """
        try:
            # remove object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            objid = self._get_value(self.objdef, args)
            self.auth_db_manager.remove_object(objid=objid, objtype=obj_type)
            self.logger.debug(u'Deregister api object: %s:%s %s' % 
                              (self.objtype, self.objdef, objid))
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex)

def make_event_class(name, event_class, **kwattrs):
    return type(str(name), (event_class,), dict(**kwattrs))
'''

class ApiObject(object):
    """ """
    module = None
    objtype = u''
    objdef = u''
    objuri = u''    
    objname = u'object'
    objdesc = u''
    
    # set this to define db manger methdod used for update. If not set update 
    # is not supported
    update_object = None
    # set this to define db manger methdod used for delete. If not set delete 
    # is not supported
    delete_object = None
    
    register = True
    
    API_OPERATION = u'API'
    SYNC_OPERATION = u'CMD'
    ASYNC_OPERATION = u'JOB'
    
    #event_ref_class = ApiEvent
    
    def __init__(self, controller, oid=None, objid=None, name=None, 
                 desc=None, active=None, model=None):
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        self.controller = controller
        self.model = model # db model if exist
        self.oid = oid # object internal db id
        self.objid = str2uni(objid)
        self.name = str2uni(name)
        self.desc = str2uni(desc)
        self.active = active
        
        # object uuid
        self.uuid = None
        if self.model is not None:
            self.uuid = self.model.uuid        

        # object uri
        self.objuri = u'/%s/%s/%s' % (self.controller.version, self.objuri, 
                                      self.uuid)
        
        # child classes
        self.child_classes = []
        
        #self.register = True
        
        self._admin_role_prefix = u'admin'
        
        #self.event_class = make_event_class(
        #    self.__class__.__module__+u'.'+self.__class__.__name__+u'Event',
        #    self.event_ref_class, objdef=self.objdef, objdesc=self.objdesc)
    
    def __repr__(self):
        return u'<%s id=%s objid=%s name=%s>' % (
                        self.__class__.__module__+'.'+self.__class__.__name__, 
                        self.oid, self.objid, self.name)
 
    @property
    def manager(self):
        return self.controller.manager
    
    @property
    def api_client(self):
        return self.controller.module.api_manager.api_client
    
    @staticmethod
    def join_typedef(parent, child):
        """ 
        Join typedef parent with typedef child
        """        
        return u'.'.join ([parent, child])
    
    @staticmethod
    def get_type(self):
        """ """        
        return (self.type, self.definition, self.__class__)
    
    def get_user(self):
        """ """
        user = {
            u'user':operation.user[0],
            u'server':operation.user[1],
            u'identity':operation.user[2]
        }
        return user
    
    @staticmethod
    def _get_value(objtype, args):
        #logging.getLogger('gibbon.cloudapi.process').debug(objtype)
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    #
    # info
    #
    def small_info(self):
        """Get object small infos.
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            u'__meta__':{
                u'objid':self.objid,             
                u'type':self.objtype,
                u'definition':self.objdef,
                u'uri':self.objuri,
            },            
            u'id':self.oid,
            u'uuid':self.uuid,
            u'name':self.name,
            u'active':str2bool(self.active),
        }
        return res
    
    def info(self):
        """Get object info
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            u'__meta__':{
                u'objid':self.objid,             
                u'type':self.objtype,
                u'definition':self.objdef,
                u'uri':self.objuri,
            },
            u'id':self.oid, 
            u'uuid':self.uuid,
            u'name':self.name, 
            u'desc':self.desc, 
            u'active':str2bool(self.active),
            u'date':{
                u'creation':format_date(self.model.creation_date),
                u'modified':format_date(self.model.modification_date),
                u'expiry':u''
            }
        }
        
        if self.model.expiry_date is not None:
            res[u'date'][u'expiry'] = format_date(self.model.expiry_date)
        
        return res

    def detail(self):
        """Get object extended info
        
        :return: Dictionary with object detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return self.info()

    #
    # authorization
    #
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        self.logger.info(u'Init api object %s.%s - START' % 
                          (self.objtype, self.objdef))
        
        try:
            # call only once during db initialization
            # add object type
            self.api_client.add_object_types(self.objtype, self.objdef)
            
            # add object and permissions
            objs = self._get_value(self.objdef, [])
            #self.rpc_client.add_object(self.objtype, self.objdef, objs)
            self.api_client.add_object(self.objtype, self.objdef, objs, 
                                       self.objdesc)
            
            # register event related to ApiObject
            #self.event_class(self.controller).init_object()
            
            self.logger.info(u'Init api object %s.%s - STOP' % 
                              (self.objtype, self.objdef))
        except ApiManagerError as ex:
            self.logger.warn(ex.value)
            #raise ApiManagerError(ex)
            
        # init child classes
        for child in self.child_classes:
            child(self.controller).init_object()
            
        # add full permissions to superadmin role
        self.set_superadmin_permissions()

    def get_all_valid_objids(self, args):
        """Get a list of authorization ids that map object
        
        :param args: objid split by //
        :return: list of valid objids
        """
        # first item *.*.*.....
        act_obj = [u'*' for i in args]
        objdis = [u'//'.join(act_obj)]
        pos = 0
        for arg in args:
            act_obj[pos] = arg
            objdis.append(u'//'.join(act_obj))
            pos += 1
    
        return objdis    
    
    def register_object_permtags(self, args):
        """Register object permission tags. Create new permission tags in 
        perm_tag if they do not already exist. Create association between
        permission tags and object in perm_tag_entity.
        
        :param args: objid split by //
        """
        if self.oid is not None:
            ids = self.get_all_valid_objids(args)
            for i in ids:
                perm = u'%s-%s' % (self.objdef.lower(), i)
                tag = self.manager.hash_from_permission(self.objdef.lower(), i)
                table = self.objdef
                self.manager.add_perm_tag(tag, perm, self.oid, table)
            
    def deregister_object_permtags(self):
        """Deregister object permission tags.
        """
        if self.objid is not None:
            ids = self.get_all_valid_objids(self.objid.split(u'//'))
            tags = []
            for i in ids:
                tags.append(self.manager.hash_from_permission(self.objdef, i))    
            table = self.objdef
            self.manager.delete_perm_tag(self.oid, table, tags)

    def register_object(self, objids, desc=u''):
        """Register object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param desc: object description
        """
        self.logger.debug(u'Register api object: %s:%s %s - START' % 
                          (self.objtype, self.objdef, objids))
        
        # add object and permissions
        #objs = self._get_value(self.objdef, objids)
        #self.rpc_client.add_object(self.objtype, self.objdef, objs)
        self.api_client.add_object(self.objtype, self.objdef, 
                                   u'//'.join(objids), desc)
        
        # register event related to ApiObject
        #self.event_class(self.controller).register_object(args, desc=desc)
        
        # register permission tags
        self.register_object_permtags(objids)
        
        self.logger.debug(u'Register api object: %s:%s %s - STOP' % 
                          (self.objtype, self.objdef, u'//'.join(objids)))
        
        # register child classes
        #if objid == None:
        #    objid = self.objid
        #objid = objid + u'//*'
        
        objids.append(u'*')
        for child in self.child_classes:
            child(self.controller, oid=None).register_object(
                  list(objids), desc=child.objdesc)
            
    def deregister_object(self, objids):
        """Deregister object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param objid: parent objid
        """
        self.logger.debug(u'Deregister api object %s:%s %s - START' %
                          (self.objtype, self.objdef, objids))
        
        # deregister permission tags
        self.deregister_object_permtags()
        
        # define objid
        #if objid == None:
        #    objid = self.objid
        #objid = objid + u'//*'
        
        # remove object and permissions
        #objid = self._get_value(self.objdef, args)
        objid = u'//'.join(objids)
        self.api_client.remove_object(self.objtype, self.objdef, objid)        
        
        objids.append(u'*')
        for child in self.child_classes:
            child(self.controller, oid=None).deregister_object(list(objids))
        
        # deregister event related to ApiObject
        #self.event_class(self.controller).deregister_object(args)            
        
        self.logger.debug(u'Deregister api object %s:%s %s - STOP' % 
                          (self.objtype, self.objdef, objid))       
    
    def set_superadmin_permissions(self):
        """ """
        self.set_admin_permissions(u'ApiSuperadmin', [])
        
    def set_admin_permissions(self, role, args):
        """ """
        # set main permissions
        self.api_client.append_role_permissions(
                role, self.objtype, self.objdef,
                self._get_value(self.objdef, args), u'*')
        #self.api_client.append_role_permissions(
        #        role, u'event', self.objdef,
        #        self._get_value(self.objdef, args), u'*')
        
    def set_viewer_permissions(self, role, args):
        """ """
        # set main permissions
        self.api_client.append_role_permissions(
                role, self.objtype, self.objdef,
                self._get_value(self.objdef, args), u'view')
        #self.api_client.append_role_permissions(
        #        role, u'event', self.objdef,
        #        self._get_value(self.objdef, args), u'view')
    
    def verify_permisssions(self, action, authorize=True):
        """Short method to verify permissions.
        
        :param authorize: if True check authorization
        :param action: action to verify. Can be *, view, insert, update, delete, 
            use
        :return: True if permissions overlap
        **Raise:** :class:`ApiManagerError`
        """        
        # check authorization
        if authorize is True:
            self.controller.check_authorization(
                self.objtype, self.objdef, self.objid, action)
    
    def authorization(self, objid=None, *args, **kvargs):
        """Get entity authorizations 
        
        :param objid: resource objid
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: [(perm, roles), ...]
        :raises ApiManagerError: if query empty return error.  
        """
        try:
            # resource permissions
            if objid == None:
                objid = self.objid
            perms, total = self.api_client.get_permissions(
                self.objtype, self.objdef, objid, cascade=True, **kvargs)

            return perms, total
        except (ApiManagerError), ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)    
    
    #
    # pre, post function
    #
    def post_get(self):
        """Post get function. This function is used in get_entity method.
        Extend this function to extend description info returned after query.
        
        **Parameters:**

        **Returns:**
            
        **Raise:** :class:`ApiManagerError`
        """
        pass
    
    @staticmethod
    def pre_create(controller, *args, **kvargs):
        """Check input params before resource creation. This function is used 
        in container resource_factory method. Extend this function to manipulate 
        and validate create input params.
        
        **Parameters:**
        
            * **args** (:py:class:`list`): custom params
            * **kvargs** (:py:class:`dict`): custom params
            
        **Returns:**
        
            kvargs
            
        **Raise:** :class:`ApiManagerError`
        """
        return kvargs
    
    @staticmethod
    def post_create(controller, *args, **kvargs):
        """Post create function. This function is used in object_factory method. 
        Used only for synchronous creation. Extend this function to execute 
        some operation after entity was created.
        
        **Parameters:**
        
            * **args** (:py:class:`list`): custom params
            * **kvargs** (:py:class:`dict`): custom params
            
        **Returns:**
        
            None
            
        **Raise:** :class:`ApiManagerError`
        """
        return None    
    
    def pre_update(self, *args, **kvargs):
        """Pre update function. This function is used in update method. Extend 
        this function to manipulate and validate update input params. 
        
        **Parameters:**
        
            * **args** (:py:class:`list`): custom params
            * **kvargs** (:py:class:`dict`): custom params
            
        **Returns:**
        
            kvargs
            
        **Raise:** :class:`ApiManagerError`
        """        
        return kvargs
    
    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend 
        this function to manipulate and validate delete input params. 
        
        **Parameters:**
        
            * **args** (:py:class:`list`): custom params
            * **kvargs** (:py:class:`dict`): custom params
            
        **Returns:**
        
            kvargs
            
        **Raise:** :class:`ApiManagerError`
        """
        return kvargs    
    
    #
    # db session
    #
    def get_session(self):
        """open db session"""
        return self.controller.get_session()
        
    def release_session(self, dbsession):
        """release db session"""
        return self.controller.release_session(dbsession)
    
    #
    # event
    #
    def send_event(self, op, args=None, params={}, opid=None, response=True, 
                   exception=None, etype=None, elapsed=0):
        """Publish an event to event queue.
        
        :param op: operation to audit
        :param op: operation id to audit [optional]
        :param params: operation params [default={}]
        :param response: operation response. [default=True]
        :param exception: exceptione raised [optinal]
        :param etype: event type. Can be ApiObject.SYNC_OPERATION, 
            ApiObject.ASYNC_OPERATION
        :param elapsed: elapsed time [default=0] 
        """
        if opid is None: opid = operation.id
        objid = u'*'
        if self.objid is not None: objid = self.objid
        if etype is None: etype = self.SYNC_OPERATION
        if exception is not None: response = (False, escape(str(exception)))
        action = op.split(u'.')[-1]
        
        # remove object from args - it does not serialize in event
        nargs = []
        for a in args:
            if str(type(a)).find(u'class') < 0:
                nargs.append(a)
                
        for k,v in params.items():
            if str(type(v)).find(u'class') > -1:
                args.pop(k)                
        
        data = {
            u'opid':opid,
            u'op':u'%s.%s' % (self.objdef, op),
            u'args':nargs,
            u'params':params,
            u'elapsed':elapsed,
            u'response':response
        }

        source = {
            u'user':operation.user[0],
            u'ip':operation.user[1],
            u'identity':operation.user[2]
        }
        
        dest = {
            u'ip':self.controller.module.api_manager.server_name,
            u'port':self.controller.module.api_manager.http_socket,
            u'objid':objid, 
            u'objtype':self.objtype,
            u'objdef':self.objdef,
            u'action':action
        }      
        
        # send event
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(etype, data, source, dest)
        except Exception as ex:
            self.logger.warning(u'Event can not be published. Event producer '\
                                u'is not configured - %s' % ex)
            
    
    '''
    def event(self, op, params, response):
        """[deprecated] Publish an event to event queue.
        
        :param op: operation to audit
        :param params: operation params
        :param response: operation response.
        """
        objid = u'*'
        if self.objid is not None: objid = self.objid
        self.event_class(self.controller, objid=objid, 
                         data={u'opid':id_gen(), u'op':op, u'params':params,
                               u'response':response}).publish(self.objtype, 
                                                              self.SYNC_OPERATION)

    def event_job(self, op, opid, params, response):
        """[deprecated] Publish a job event to event queue.
        
        :param op: operation to audit
        :param opid: operation id to audit
        :param params: operation params
        :param response: operation response.
        """
        objid = u'*'
        if self.objid is not None: objid = self.objid
        self.event_class(self.controller, objid=objid, 
                         data={u'opid':opid, u'op':op, u'params':params,
                               u'response':response}).publish(self.objtype, 
                                                              self.ASYNC_OPERATION)
    '''
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

    '''
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
    '''

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

    #
    # update, delete
    #
    @trace(op=u'update')
    def update(self, authorize=True, *args, **kvargs):
        """Update entity.
        
        **Parameters:**
        
            * **args** (:py:class:`list`): custom params
            * **kvargs** (:py:class:`dict`): custom params
            * **authorize** (:py:class:`bool`): if True check permissions for authorization
            
        **Returns:**
        
            entity uuid
            
        **Raise:** :class:`ApiManagerError`
        """
        if self.update_object is None:
            raise ApiManagerError(u'Update is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))
        
        # verify permissions
        self.verify_permisssions(u'update', authorize=authorize)
        
        # custom action
        if self.pre_update is not None:
            kvargs = self.pre_update(**kvargs)
        
        try:  
            res = self.update_object(oid=self.oid, *args, **kvargs)
            
            self.logger.debug(u'Update %s %s with data %s' % 
                              (self.objdef, self.oid, kvargs))
            #self.send_event(u'update', params=params)
            return self.uuid
        except TransactionError as ex:
            #self.send_event(u'update', params=params, exception=ex)        
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op=u'delete')
    def delete(self, authorize=True, soft=False, **kvargs):
        """Delete entity.
        
        **Parameters:**
        
            * **kvargs** (:py:class:`dict`): custom params
            * **authorize** (:py:class:`bool`): if True check permissions for authorization
            * **soft** (:py:class:`bool`): if True make a soft delete
            
        **Returns:**
        
            None
            
        **Raise:** :class:`ApiManagerError`
        """
        if self.delete_object is None:
            raise ApiManagerError(u'Delete is not supported for %s:%s' % 
                                  (self.objtype, self.objdef))        
        
        # verify permissions
        self.verify_permisssions(u'delete', authorize=authorize)
            
        # custom action
        if self.pre_delete is not None:
            kvargs = self.pre_delete(**kvargs)            
            
        try:  
            if soft is False:
                self.delete_object(oid=self.oid)
                if self.register is True:
                    # remove object and permissions
                    self.deregister_object(self.objid.split(u'//'))
                
                self.logger.debug(u'Delete %s: %s' % (self.objdef, self.oid))
            else:
                self.delete_object(self.model)
                self.logger.debug(u'Soft delete %s: %s' % (self.objdef, self.oid))
            return None
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

class ApiInternalObject(ApiObject):
    objtype = u'auth'
    objdef = u'abstract'
    objdesc = u'Authorization abstract object'
    
    #event_ref_class = ApiInternalEvent
    
    def __init__(self, *args, **kvargs):
        ApiObject.__init__(self, *args, **kvargs)
        self.auth_db_manager = AuthDbManager()    
    
    #
    # authorization
    #
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        self.logger.info(u'Init api object %s.%s - START' % 
                          (self.objtype, self.objdef))
        
        try:
            # call only once during db initialization
            # add object type
            obj_types = [(self.objtype, self.objdef)]
            self.auth_db_manager.add_object_types(obj_types)
            
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
            
            # register event related to ApiObject
            #self.event_class(self.controller).init_object()
            
            self.logger.info(u'Init api object %s.%s - STOP' % 
                              (self.objtype, self.objdef))
        except (QueryError, TransactionError) as ex:
            self.logger.warn(ex.desc)
            
        # init child classes
        for child in self.child_classes:
            child(self.controller).init_object()
    
    def register_object(self, objids, desc=u''):
        """Register object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param desc: object description
        :param objid: parent objid
        """
        self.logger.debug(u'Register api object %s:%s %s - START' % 
                          (self.objtype, self.objdef, objids))
        
        try:
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, 
                                                   objdef=self.objdef)[0][0]
            #objs = [(obj_type, self._get_value(self.objdef, args), desc)]
            objs = [(obj_type, u'//'.join(objids), desc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
            
            # register event related to ApiObject
            #self.event_class(self.controller).register_object(objids, desc)
        except (QueryError, TransactionError) as ex:
            self.logger.error(u'Register api object: %s - ERROR' % (ex.desc))
            raise ApiManagerError(ex.desc, code=400)       
        
        # register permission tags
        self.register_object_permtags(objids)
        
        self.logger.debug(u'Register api object %s:%s %s - STOP' % 
                          (self.objtype, self.objdef, objs))
        
        # register child classes
        objids.append(u'*')
        for child in self.child_classes:
            child(self.controller, oid=None).register_object(objids, desc=child.objdesc)
    
    def deregister_object(self, objids):
        """Deregister object types, objects and permissions related to module.
        
        :param args: objid split by //
        """
        self.logger.debug(u'Deregister api object %s:%s %s - START' % 
                          (self.objtype, self.objdef, objids))
        
        # deregister permission tags
        self.deregister_object_permtags()
        
        try:
            # remove object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            #objid = self._get_value(self.objdef, objids)
            objid = u'//'.join(objids)
            self.auth_db_manager.remove_object(objid=objid, objtype=obj_type)
            
            # deregister event related to ApiObject
            #self.event_class(self.controller).deregister_object(objids)
            
            self.logger.debug(u'Deregister api object %s:%s %s - STOP' % 
                              (self.objtype, self.objdef, objids))                
        except (QueryError, TransactionError) as ex:
            self.logger.error(u'Deregister api object: %s - ERROR' % (ex.desc))
            raise ApiManagerError(ex.desc, code=400)       
        
        # deregister child classes
        objids.append(u'*')
        for child in self.child_classes:
            child(self.controller, oid=None).deregister_object(objids)        
    
    def set_admin_permissions(self, role_name, args):
        """Set admin permissions
        """
        try:
            role = self.auth_db_manager.get_entity(Role, role_name)
            perms, total = self.auth_db_manager.get_permissions(
                                    objid=self._get_value(self.objdef, args),
                                    objtype=None, 
                                    objdef=self.objdef,
                                    action=u'*')            
            
            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)
            
            # set child resources permissions
            for child in self.child_classes:
                res = child(self.controller, self)
                res.set_admin_permissions(role_name, self._get_value(
                            res.objdef, args).split(u'//'))            
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)
        
    def authorization(self, objid=None, *args, **kvargs):
        """Get resource authorizations 
        
        :param objid: resource objid
        :param page: perm list page to show [default=0]
        :param size: number of perms to show in list per page [default=10]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]              
        :return: [perms]
        :rtype: list
        :raises ApiManagerError: if query empty return error.  
        """
        try:
            # resource permissions
            if objid == None:
                objid = self.objid
            objids = [objid, 
                      objid+u'//*',
                      objid+u'//*//*',
                      objid+u'//*//*//*',
                      objid+u'//*//*//*//*',
                      objid+u'//*//*//*//*//*',
                      objid+u'//*//*//*//*//*//*']
            perms, total = self.auth_db_manager.get_deep_permissions(
                    objids=objids, objtype=self.objtype)

            res = []
            for p in perms:
                res.append({
                    u'id':p.id, 
                    u'oid':p.obj.id, 
                    u'subsystem':p.obj.type.objtype, 
                    u'type':p.obj.type.objdef,
                    u'objid':p.obj.objid, 
                    u'aid':p.action.id, 
                    u'action':p.action.value, 
                    u'desc':p.obj.desc
                })

            self.logger.debug(u'Get permissions %s: %s' % 
                              (self.oid, truncate(res)))
            return res, total
        except (ApiManagerError), ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)         

class ApiViewResponse(ApiObject):
    objtype = u'api'
    objdef = u'Response'
    objdesc = u'Api Response'
    
    #event_ref_class = ApiInternalEvent
    
    def __init__(self, *args, **kvargs):
        ApiObject.__init__(self, *args, **kvargs)
        self.auth_db_manager = AuthDbManager()    
    
    @property
    def manager(self):
        return self.controller.manager    
    
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        try:
            # call only once during db initialization
            # add object type
            obj_types = [(self.objtype, self.objdef)]
            self.auth_db_manager.add_object_types(obj_types)
            
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
            
            # register event related to ApiObject
            #self.event_class(self.controller).init_object()
            
            self.logger.debug(u'Register api object: %s' % objs)
        except (QueryError, TransactionError) as ex:
            self.logger.warn(ex.desc)    
    
    def set_admin_permissions(self, role_name, args):
        """Set admin permissions
        """
        try:
            role = self.auth_db_manager.get_entity(Role, role_name)
            perms, total = self.auth_db_manager.get_permissions(
                                    objid=self._get_value(self.objdef, args),
                                    objtype=None, 
                                    objdef=self.objdef,
                                    action=u'*')            
            
            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    def send_event(self, api, params={}, response=True, exception=None):
        """Publish an event to event queue.
        
        :param api: api to audit {u'path':.., u'method':.., u'elapsed':..}
        :param params: operation params [default={}]
        :param response: operation response. [default=True]
        :param exception: exceptione raised [optinal]
        """
        objid = u'*'
        if exception is not None: response = (False, escape(exception))
        method = api[u'method']
        if method in [u'GET']:
            action = u'view'
        elif method in [u'POST']:
            action = u'insert'
        elif method in [u'PUT']:
            action = u'update'
        elif method in [u'DELETE']:
            action = u'delete'
        #else:
        #    action = u'use'
        elapsed = api.pop(u'elapsed')
        
        # send event
        data = {
            u'opid':operation.id,
            u'op':api,
            u'params':params,
            u'elapsed':elapsed,
            u'response':response
        }

        source = {
            u'user':operation.user[0],
            u'ip':operation.user[1],
            u'identity':operation.user[2]
        }
        
        dest = {
            u'ip':self.controller.module.api_manager.server_name,
            u'port':self.controller.module.api_manager.http_socket,
            u'objid':objid, 
            u'objtype':self.objtype,
            u'objdef':self.objdef,
            u'action':action
        }      
        
        # send event
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(self.SYNC_OPERATION, data, source, dest)
        except Exception as ex:
            self.logger.warning(u'Event can not be published. Event producer '\
                                u'is not configured - %s' % ex)            

class ApiView(FlaskView):
    """ """
    prefix = u'identity:'
    expire = 3600
    parameters = []
    parameters_schema = None
    
    RESPONSE_MIME_TYPE = [
        u'application/json', 
        u'application/bson', 
        u'text/xml',
        u'*/*'
    ]
    
    def __init__(self, *argc, **argv):
        #FlaskView.__init__(self, *argc, **argv)
        self.logger = logging.getLogger(self.__class__.__module__+ \
                                        u'.'+self.__class__.__name__)
        
        #self.get.__func__.__doc__ = self.__class__.__doc__
        #self.put.__func__.__doc__ = self.__class__.__doc__
        #self.post.__func__.__doc__ = self.__class__.__doc__
        #self.delete.__func__.__doc__ = self.__class__.__doc__
    
    def _get_response_mime_type(self):
        """ """
        try:
            self.response_mime = request.headers[u'Content-Type']
        except:
            self.response_mime = u'application/json'
        
        '''if self.response_mime not in self.RESPONSE_MIME_TYPE:
            self.logger.warn(u'Response mime type %s is not supported' % 
                             self.response_mime)
            self.response_mime = u'application/json'''
        
        self.logger.debug(u'Response mime type: %s' % self.response_mime)
    
    def __get_auth_filter(self):
        """Get authentication filter. It can be keyauth, oauth2, simplehttp or ...
        """
        headers = request.headers
        if u'uid' in headers and u'sign' in headers:
            return u'keyauth'
        if u'Authorization' in headers and \
           headers.get(u'Authorization').find(u'Basic') >= 0:
            return u'simplehttp'
        if u'Authorization' in headers and \
           headers.get(u'Authorization').find(u'Bearer') >= 0:
            return u'oauth2'
        return None
     
    def __get_token(self):
        """get uid and sign from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            uid = header[u'uid']
            sign = header[u'sign']
            data = request.path
            self.logger.info(u'Uid: %s' % uid)
            self.logger.debug(u'Sign: %s' % sign)
            self.logger.debug(u'Data: %s' % data)
        except:
            raise ApiManagerError(u'Error retrieving token and sign from http header', 
                                  code=401)
        return (uid, sign, data)
    
    def __get_oauth2_token(self):
        """Get oauth2 access token from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            token = header[u'Authorization'].replace(u'Bearer ', u'')
            self.logger.info(u'Get Bearer Token: %s' % token)
        except:
            raise ApiManagerError(u'Error retrieving bearer token', code=401)
        return token
    
    def __get_http_credentials(self):
        """Verify that simple http authentication contains valid fields and is 
        allowed for the user provided.
        
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            authorization = header[u'Authorization']
            self.logger.info(u'Authorization: %s' % authorization)
            
            # get credentials
            if not match(u'Basic [a-zA-z0-9]+', authorization):
                raise Exception(u'Authorization field syntax is wrong')
            authorization = authorization.lstrip(u'Basic ')
            self.logger.warn(u'Authorization: %s' % authorization)
            credentials = b64decode(authorization)
            user, pwd = credentials.split(u':')
            user_ip = get_remote_ip(request)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(u'Error retrieving Authorization from http header', 
                                  code=401)
        return user, pwd, user_ip
    
    def get_current_identity(self):
        """Get uid and sign from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.__get_token()
    
    @watch
    def authorize_request(self, module):
        """Authorize http request
        
        :param module: beehive module instance
        :raise AuthViewError:
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.logger.debug(u'Verify api authorization: %s' % request.path)

        # select correct authentication filter
        authfilter = self.__get_auth_filter()
        self.logger.debug(u'Select authentication filter "%s"' % authfilter)
        
        # get controller
        controller = module.get_controller()
        
        # - keyauth
        if authfilter == u'keyauth':
            # get identity and verify signature
            uid, sign, data = self.__get_token()
            identity = controller.verify_request_signature(uid, sign, data)
        
        # - oauth2
        elif authfilter == u'oauth2':
            uid = self.__get_oauth2_token()
            # get identity
            identity = controller.get_oauth2_identity(uid)
            if identity[u'type'] != u'oauth2':
                msg = u'Token type oauth2 does not match with supplied token'
                self.logger.error(msg, exc_info=1)
                raise ApiManagerError(msg, code=401)  

        # - simple http authentication
        elif authfilter == u'simplehttp':
            user, pwd, user_ip = self.__get_http_credentials()
            identity = controller.verify_simple_http_credentials(user, pwd, user_ip)
            uid = None
            identity[u'seckey'] = None
            identity[u'ip'] = user_ip

        # - no authentication
        elif authfilter is None:
            msg = u'Request is not authorized'
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)

        # get user permissions from identity
        name = u'Guest'
        try:
            # get user permission
            user = identity[u'user']
            name = user[u'name']
            compress_perms = user[u'perms']
            
            # get permissions
            # u'id', u'oid', u'objtype', u'objdef', u'objid', u'aid', u'action'
            '''if u'dbauth' in controller.__dict__:
                user_obj = controller.dbauth.get_users(name=name)[0][0]
                perms = controller.dbauth.get_login_permissions(user_obj)
            else:
                perms = controller.api_client.get_user_perms(name)
            self.logger.warn(perms)'''
            
            operation.perms = json.loads(decompress(binascii.a2b_base64(compress_perms)))
            operation.user = (name, identity[u'ip'], uid, 
                              identity.get(u'seckey', None))
            self.logger.debug(u'Get user %s permissions: %s' % 
                              (name, truncate(operation.perms)))
        except Exception as ex:
            msg = u'Error retrieving user %s permissions: %s' % (name, ex)
            self.logger.error(msg, exc_info=1)
            raise ApiManagerError(msg, code=401)
        
        #return user
        
    # response methods
    @watch    
    def get_warning(self, exception, code, msg):
        self.get_error(exception, code, msg)
    

    # response methods
    @watch    
    def get_error(self, exception, code, msg):
        """
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        headers = {u'Cache-Control':u'no-store',
                   u'Pragma':u'no-cache'}        
        
        error = {
            u'code':code, 
            u'message':str(msg),
            u'description':u'%s - %s' % (exception, msg)
        }
        self.logger.error(u'Api response: %s' % error)
        
        if self.response_mime is None or \
           self.response_mime == u'*/*' or \
           self.response_mime == u'':
            self.response_mime = u'application/json'
            
        if code in [400, 401, 403, 404, 405, 406, 408, 409, 415, 500]:
            status = code
        else:
            status = 400
        
        self.logger.error(u'Code: %s, Error: %s' % (code, exception), 
                          exc_info=True)
        if self.response_mime == u'application/json':
            return Response(response=json.dumps(error), 
                            mimetype=u'application/json', 
                            status=status,
                            headers=headers)
        elif self.response_mime == u'application/bson':
            return Response(response=json.dumps(error), 
                            mimetype=u'application/bson', 
                            status=status,
                            headers=headers)
        elif self.response_mime in [u'text/xml', u'application/xml']:
            xml = dicttoxml(error, root=False, attr_type=False)
            return Response(response=xml, 
                            mimetype=u'application/xml', 
                            status=status,
                            headers=headers)
        else:  
            # 415 Unsupported Media Type
            return Response(response=u'', 
                            mimetype=u'text/plain', 
                            status=415,
                            headers=headers)           

    @watch
    def get_response(self, response, code=200, headers=None):
        """
        **raise** :class:`ApiManagerError`
        """
        try:
            if response is None:
                return Response(response=u'', 
                                mimetype=u'text/plain', 
                                status=code)
            
            if self.response_mime == u'*/*':
                self.response_mime = u'application/json'
            
            self.logger.debug(u'Api response mime type: %s' % self.response_mime)
            
            # redirect to new uri
            if code in [301, 302, 303, 305, 307]:
                self.logger.debug(u'Api response: %s' % truncate(response))                
                return response
            
            # render template
            elif self.response_mime.find(u'text/html') >= 0:
                self.logger.debug(u'Api response: %s' % truncate(response))                
                return response
            
            # return original response
            elif isinstance(response, Response):
                self.logger.debug(u'Api response: %s' % truncate(response))
                return response
            
            # render json
            elif self.response_mime == u'application/json':
                resp = json.dumps(response)
                self.logger.debug(u'Api response: %s' % truncate(resp))
                return Response(resp, 
                                mimetype=u'application/json',
                                status=code)
            
            # render Bson
            elif self.response_mime == u'application/bson':
                resp = json.dumps(response)
                self.logger.debug(u'Api response: %s' % truncate(resp))
                return Response(resp, 
                                mimetype=u'application/bson',
                                status=code)
                
            # render xml
            elif self.response_mime in [u'text/xml', u'application/xml']:
                resp = dicttoxml(response, root=False, attr_type=False)
                #xml = dicttoxml.dicttoxml(res)
                self.logger.debug(u'Api response: %s' % truncate(resp))
                return Response(resp, 
                                mimetype=u'application/xml',
                                status=code)
                
            # 415 Unsupported Media Type
            else:
                self.logger.debug(u'Api response: ')
                return Response(response=u'', 
                                mimetype=u'text/plain', 
                                status=code)
        except Exception as ex:
            msg = u'Error creating response - %s' % ex
            self.logger.error(msg)
            raise ApiManagerError(msg, code=400)
    
    def format_paginated_response(self, response, entity, total, page=None, 
                                  field=u'id', order=u'DESC', **kvargs):
        """Format response with pagination info
        
        :param response: response
        :param entity: entity like users
        :param page: page number
        :param total: total response records that user can view
        :param field: sorting field
        :param order: sorting order
        :return: dict with data
        """
        resp = {
            entity:response,
            u'count':len(response),
            u'page':page,
            u'total':total,
            u'sort':{
                u'field':field,
                u'order':order           
            }
        }
        
        return resp
    
    def dispatch(self, controller, data, *args, **kwargs):
        """http inner function. Override to implement apis.
        """
        raise NotImplementedError()    
    
    def dispatch_request(self, module=None, secure=True, *args, **kwargs):
        """Base dispatch_request method. Extend this method in your child class.
        """
        # set reqeust timeout
        res = None
        
        timeout = gevent.Timeout(module.api_manager.api_timeout)
        timeout.start()

        start = time.time()
        dbsession = None
        try:
            headers = [u'%s: %s' % (k,v) for k,v in request.headers.iteritems()]
            
            # set operation
            operation.user = (u'guest', u'localhost', None)
            operation.id = request.headers.get(u'request-id', str(uuid4()))
            operation.transaction = None
            
            self.logger.info(u'Start new operation [%s]' % (operation.id))
            
            self.logger.info(u'Invoke api: %s [%s] - START' % 
                             (request.path, request.method))
            query_string = request.values.to_dict()    
            self.logger.debug(u'Api request headers:%s, data:%s, query:%s' % 
                              (headers, request.data, query_string))
            self._get_response_mime_type()
            
            # open database session.
            dbsession = module.get_session()
            controller = module.get_controller()            
            
            # check security
            if secure is True:
                self.authorize_request(module)
            
            # get request data
            try:
                data = request.data 
                data = json.loads(data)
            except (AttributeError, ValueError): 
                data = request.values.to_dict()
                
            # validate query/input data
            if self.parameters_schema is not None:
                if request.method.lower() == u'get':
                    parsed = self.parameters_schema().load(request.args.to_dict())
                else:
                    parsed = self.parameters_schema().load(data)
                if len(parsed.errors.keys()) > 0:
                    self.logger.error(parsed.errors)
                    raise ApiManagerError(parsed.errors, code=400)
                data = parsed.data
                self.logger.debug(u'Query/data after schema validation: %s' % data)
        
            # dispatch request
            meth = getattr(self, request.method.lower(), None)
            if meth is None:
                meth = self.dispatch
            resp = meth(controller, data, *args, **kwargs)
            
            if isinstance(resp, tuple):
                if len(resp) == 3:
                    res = self.get_response(resp[0], code=resp[1], 
                                            headers=resp[2])
                else:
                    res = self.get_response(resp[0], code=resp[1])
            else:
                res = self.get_response(resp)
            
            # unset user permisssions in local thread object
            operation.perms = None
            
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.info(u'Invoke api: %s [%s] - STOP - %s' % 
                             (request.path, request.method, elapsed))
            ApiViewResponse(controller).send_event({u'path':request.path,
                                                    u'method':request.method,
                                                    u'elapsed':elapsed}, 
                                                   request.data)
        except gevent.Timeout:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error(u'Invoke api: %s [%s] - ERROR - %s' % 
                              (request.path, request.method, elapsed))             
            msg = u'Request %s %s timeout' % (request.path, request.method)
            ApiViewResponse(controller).send_event({u'path':request.path,
                                                    u'method':request.method,
                                                    u'elapsed':elapsed,
                                                    u'code':408}, 
                                                   request.data,
                                                   exception=msg)            
            return self.get_error(u'Timeout', 408, msg)
        except ApiManagerError as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error(u'Invoke api: %s [%s] - ERROR - %s' % 
                              (request.path, request.method, elapsed))
            ApiViewResponse(controller).send_event({u'path':request.path,
                                                    u'method':request.method,
                                                    u'elapsed':elapsed,
                                                    u'code':ex.code}, 
                                                   request.data,
                                                   exception=ex.value)            
            return self.get_error(u'ApiManagerError', ex.code, ex.value)
        except ApiManagerWarning as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.warning(u'Invoke api: %s [%s] - Warning - %s' % 
                              (request.path, request.method, elapsed))
            ApiViewResponse(controller).send_event({u'path':request.path,
                                                    u'method':request.method,
                                                    u'elapsed':elapsed,
                                                    u'code':ex.code}, 
                                                   request.data,
                                                   exception=ex.value)            
            return self.get_warning(u'ApiManagerWarning', ex.code, ex.value)
        except Exception as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error(u'Invoke api: %s [%s] - ERROR - %s' % 
                              (request.path, request.method, elapsed))
            ApiViewResponse(controller).send_event({u'path':request.path,
                                                    u'method':request.method,
                                                    u'elapsed':elapsed,
                                                    u'code':400}, 
                                                   request.data,
                                                   exception=str(ex))            
            return self.get_error(u'Exception', 400, str(ex))
        finally:
            if dbsession is not None:
                module.release_session(dbsession)
            timeout.cancel()
            self.logger.debug(u'Timeout released')

        return res
    
    @staticmethod
    def register_api(module, rules, version=None):
        """
        :param module: beehive module
        :param rules: route to register. Ex. 
                      [('/jobs', 'GET', ListJobs.as_view('jobs')), {'secure':False}]
        """
        logger = logging.getLogger(__name__)
        #logger = logging.getLogger('gibbon.cloudapi.view')
        
        # get version
        if version is None:
            version = module.get_controller().version
        
        # get app
        app = module.api_manager.app
        
        # get swagger
        #swagger = module.api_manager.swagger
        
        # regiter routes
        view_num = 0
        for rule in rules:
            uri = u'/%s/%s' % (version, rule[0])
            defaults = {u'module':module}
            defaults.update(rule[3])
            view_name = u'%s-%s' % (get_class_name(rule[2]), view_num)
            view_func = rule[2].as_view(str(view_name))

            # setup flask route
            app.add_url_rule(uri,
                             methods=[rule[1]],
                             view_func=view_func, 
                             defaults=defaults)
            
            view_num += 1
            logger.debug('Add route: %s %s' % (uri, rule[1]))
            
            # append route to module
            module.api_routes.append({'uri':uri, 'method':rule[1]})

class PaginatedRequestQuerySchema(Schema):
    size = fields.Integer(default=10, example=10, missing=10, context=u'query',
                          description=u'enitities list page size',
                          validate=Range(min=0, max=200,
                                         error=u'Size is out from range'))
    page = fields.Integer(default=0, example=0, missing=0, context=u'query',
                          description=u'enitities list page selected',
                          validate=Range(min=0, max=1000,
                                         error=u'Page is out from range'))
    order = fields.String(validate=OneOf([u'ASC', u'asc', u'DESC', u'desc'],
                                         error=u'Order can be asc, ASC, desc, DESC'),
                          description=u'enitities list order: ASC or DESC',
                          default=u'DESC', example=u'DESC', missing=u'DESC', context=u'query')
    field = fields.String(validate=OneOf([u'id', u'uuid', u'objid', u'name'],
                                         error=u'Field can be id, uuid, objid, name'),
                          description=u'enitities list order field. Ex. id, uuid, name',
                          default=u'id', example=u'id', missing=u'id', context=u'query')
    
class GetApiObjectRequestSchema(Schema):
    oid = fields.String(required=True, description=u'id, uuid or name',
                        context=u'path')
    
class ApiObjectPermsRequestSchema(PaginatedRequestQuerySchema,
                                  GetApiObjectRequestSchema):
    pass   

class ApiObjectResponseDateSchema(Schema):
    creation = fields.DateTime(required=True, default=u'1990-12-31T23:59:59Z', 
                               example=u'1990-12-31T23:59:59Z')
    modified = fields.DateTime(required=True, default=u'1990-12-31T23:59:59Z', 
                               example=u'1990-12-31T23:59:59Z')
    expiry = fields.String(default=u'')

class ApiObjecCountResponseSchema(Schema):
    count = fields.Integer(required=True, default=10)

class ApiObjectMetadataResponseSchema(Schema):
    objid = fields.String(required=True, default=u'396587362//3328462822',
                          example=u'396587362//3328462822')
    type = fields.String(required=True, default=u'auth', example=u'auth')
    definition = fields.String(required=True, default=u'Role', example=u'Role')
    uri = fields.String(required=True, default=u'/v1.0/auht/roles', 
                        example=u'/v1.0/auht/roles')

class ApiObjectSmallResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(required=True, 
                         default=u'4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example=u'4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, default=u'test', example=u'test')
    active = fields.Boolean(required=True, default=True, example=True)
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)

class ApiObjectResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(required=True, 
                         default=u'4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example=u'4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, default=u'test', example=u'test')
    desc = fields.String(required=True, default=u'test', example=u'test')
    date = fields.Nested(ApiObjectResponseDateSchema, required=True)
    active = fields.Boolean(required=True, default=True, example=True)
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)

class PaginatedResponseSortSchema(Schema):
    order = fields.String(required=True, 
                          validate=OneOf([u'ASC', u'asc', u'DESC', u'desc']),
                          default=u'DESC', example=u'DESC')
    field = fields.String(required=True, default=u'id', example=u'id')

class PaginatedResponseSchema(Schema):
    count = fields.Integer(required=True, default=10, example=10)
    page = fields.Integer(required=True, default=0, example=0)
    total = fields.Integer(required=True, default=20, example=20)
    sort = fields.Nested(PaginatedResponseSortSchema, required=True)
    
class CrudApiObjectResponseSchema(Schema):
    uuid = fields.UUID(required=True, 
                       default=u'6d960236-d280-46d2-817d-f3ce8f0aeff7',
                       example=u'6d960236-d280-46d2-817d-f3ce8f0aeff7')
    
class CrudApiJobResponseSchema(Schema):
    jobid = fields.UUID(default=u'db078b20-19c6-4f0e-909c-94745de667d4',
                        example=u'6d960236-d280-46d2-817d-f3ce8f0aeff7',
                        required=True)
    
class CrudApiObjectJobResponseSchema(CrudApiObjectResponseSchema,
                                     CrudApiJobResponseSchema):
    pass    

class ApiObjectPermsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=1, example=1)
    oid = fields.Integer(required=True, default=1, example=1)
    objid = fields.String(required=True, default=u'396587362//3328462822', 
                          example=u'396587362//3328462822')
    type = fields.String(required=True, default=u'Objects', example=u'Objects')
    subsystem = fields.String(required=True, default=u'auth', example=u'auth')
    desc = fields.String(required=True, default=u'beehive', example=u'beehive')
    aid = fields.Integer(required=True, default=1, example=1)
    action = fields.String(required=True, default=u'view', example=u'view')

class ApiObjectPermsResponseSchema(PaginatedResponseSchema):
    perms = fields.Nested(ApiObjectPermsParamsResponseSchema, many=True, 
                          required=True) 

class SwaggerApiView(ApiView, SwaggerView):
    consumes = ['application/json',
                'application/xml']
    produces = ['application/json',
                'application/xml',
                'text/plain']
    security = [
        {'ApiKeyAuth': []},
        {'OAuth2': ['auth', 'beehive']},
    ]
    definitions = {}
    parameters = []
    responses = {
        u'default': {'$ref': '#/responses/DefaultError'},
        500: {'$ref': '#/responses/InternalServerError'},
        400: {'$ref': '#/responses/BadRequest'},
        401: {'$ref': '#/responses/Unauthorized'},
        403: {'$ref': '#/responses/Forbidden'},
        405: {'$ref': '#/responses/MethodAotAllowed'},
        408: {'$ref': '#/responses/Timeout'},
        410: {'$ref': '#/responses/Gone'},
        415: {'$ref': '#/responses/UnsupportedMediaType'},
        422: {'$ref': '#/responses/UnprocessableEntity'},
        429: {'$ref': '#/responses/TooManyRequests'},
    }
    
    @classmethod
    def setResponses(cls, data):
        new = deepcopy(cls.responses)
        new.update(data)
        return new    

class ApiClient(BeehiveApiClient):
    """ """
    def __init__(self, auth_endpoints, user, pwd, catalog_id=None, 
                 authtype=u'keyauth'):
        BeehiveApiClient.__init__(self, auth_endpoints, authtype, 
                                  user, pwd, catalog_id)
    
    def admin_request(self, subsystem, path, method, data=u'', 
                      other_headers=None):
        """Make api request using module internal admin user credentials.
        
        **Raise:** :class:`ApiManagerError`
        """
        try:
            if self.exist(self.uid) is False:
                self.login()
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
        
        try:
            res = self.send_request(subsystem, path, method, data, 
                                    self.uid, self.seckey, other_headers)
        except BeehiveApiClientError as ex:
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
        
        **Raise:** :class:`ApiManagerError`
        """
        try:
            # get user logged uid and password
            uid = operation.user[2]
            seckey = operation.user[3]
            res = self.send_request(module, path, method, data, uid, 
                                    seckey, other_headers)
        except BeehiveApiClientError as ex:
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