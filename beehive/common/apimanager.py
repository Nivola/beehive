# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

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
from six import b, u
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from datetime import datetime
from flask import request, Response, session
from flask.views import MethodView as FlaskView
from flask_session import Session
from flask import current_app
from beecell.cache.client import CacheClient
from beecell.db import TransactionError, QueryError
from beecell.db.manager import MysqlManager, SqlManagerError, RedisManager
from beecell.auth import extract
from beecell.simple import import_class, truncate, get_class_name, \
    parse_redis_uri, get_remote_ip, str2bool, format_date, obscure_data
from beecell.sendmail import Mailer
from beehive.common.data import operation, trace
from beecell.auth import DatabaseAuth, LdapAuth, SystemUser
import gevent
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.common.model.config import ConfigDbManager
from beehive.common.model.authorization import AuthDbManager, Role
from beehive.common.event import EventProducerRedis

from beehive.common.dicttoxml import dicttoxml
from rediscluster.client import RedisCluster
try:
    from beecell.server.uwsgi_server.wrapper import uwsgi_util
except:
    pass
from copy import deepcopy
from flask_session.sessions import RedisSessionInterface
from beehive.common.data import encrypt_data, decrypt_data
from elasticsearch import Elasticsearch
from flasgger import Swagger, SwaggerView
from marshmallow import fields, Schema
from marshmallow.validate import OneOf, Range


logger = logging.getLogger(__name__)


class RedisSessionInterface2(RedisSessionInterface):
    def __init__(self, redis, key_prefix, use_signer=False, permanent=True):
        RedisSessionInterface.__init__(self, redis, key_prefix, use_signer, permanent)

    def save_session(self, app, session, response):
        RedisSessionInterface.save_session(self, app, session, response)
        # oauth2_user = session.get('oauth2_user', None)
        if response.mimetype not in ['text/html']:
            self.redis.delete(self.key_prefix + session.sid)
            logger.debug('Delete user session. This is an Api request')
        if session.get('_invalidate', False) is not False:
            self.redis.delete(self.key_prefix + session.sid)
            logger.debug('Delete user session. This is an Api request')            


class ApiManagerWarning(Exception):
    """Main excpetion raised by api manager and childs
    
    
        * **value: error description
        * **code** (:py:class:`int`): error code [default=400]
    """
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return 'ApiManagerWarning: %s' % self.value 

    def __str__(self):
        return '%s' % self.value


class ApiManagerError(Exception):
    """Main exception raised by api manager and childs
    
    
        * **value: error description
        * **code** (:py:class:`int`): error code [default=400]
    """
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return 'ApiManagerError: %s' % self.value 

    def __str__(self):
        return '%s' % self.value


class ApiManager(object):
    """Api Manager
    
    
    
        * **params** (:py:class:`dict`): configuration params
        * **app** (:py:class:`int`): error code [default=400]    
    """
    # logger = logging.getLogger('gibbon.cloudapi')
    
    def __init__(self, params, app=None, hostname=None):
        self.logger = logging.getLogger(self.__class__.__module__+ '.' + self.__class__.__name__)
        
        # configuration params
        self.params = params       
        
        # flask app reference
        self.app = app
        self.app_name = self.params['api_name']
        self.app_id = self.params['api_id']
        self.app_desc = self.params['api_id']
        self.app_subsytem = self.params['api_subsystem']
        self.app_fernet_key = self.params.get('api_fernet_key', None)
        self.app_endpoint_id = '%s-%s' % (self.params['api_id'], hostname)
        self.swagger_spec_path = self.params.get('api_swagger_spec_path', 'swagger.yml')
        try:
            self.app_uri = 'http://%s%s' % (hostname, self.params['http-socket'])
            self.uwsgi_uri = 'uwsgi://%s%s' % (hostname, self.params['socket'])
        except:
            self.app_uri = None
            self.uwsgi_uri = None
        
        # set encryption key
        operation.encryption_key = self.app_fernet_key

        # swagger reference
        self.swagger = Swagger(self.app, template_file=self.swagger_spec_path)

        # instance configuration
        self.http_socket = self.params.get('http-socket')
        self.server_name = hostname
        
        # modules
        self.modules = {}
        self.main_module = None
        
        # redis
        self.redis_manager = None

        # cache
        self.cache_manager = None
        self.cache_manager_ttl = 86400
        
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
        self.api_timeout = float(self.params.get('api_timeout', 10.0))
        
        # api endpoints
        self.endpoints = {}
        #self.rpc_client = ApiRpcClient(self)
        #self.rpc_httpclient = ApiRpcHttpClient(self)
        self.api_user = None
        self.api_user_pwd = None
        self.api_client = None     
        self.awx_client = None 
        
        # gateways
        self.gateways = {}

        # elasticsearch
        self.elasticsearch = None
        
        # database manager
        self.db_manager = None
        database_uri = self.params.get('database_uri', None)
        if database_uri is not None:
            self.create_pool_engine((database_uri, 5, 10, 10, 1800))
        
        # send mail
        self.mailer = None
        self.mail_sender = None
        
        # identity
        self.prefix = 'identity:'
        self.expire = 3600
        
        # scheduler
        self.redis_taskmanager = None
        self.redis_scheduler = None
        
        # Camunda Engine
        self.camunda_engine = None

        # proxy
        self.http_proxy = None
        self.https_proxies = []
        self.tcp_proxy = None

        # stack uri reference
        self.stacks_uri = None

        # git reference
        self.git = None

    def create_pool_engine(self, dbconf):
        """Create mysql pool engine.
        
        :param list dbconf: (uri, timeout, pool_size, max_overflow, pool_recycle)
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
        
        :param list dbconf: (uri, timeout)        
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
            self.db_manager.release_session(operation.session)
            operation.session = None
        except SqlManagerError as e:
            raise ApiManagerError(e)

    def get_identity(self, uid):
        """Get identity
        
        :param uid: identity id            
        :return:
            .. code-block:: python
               
               {'uid':..., 
                'user':..., 
                'timestamp':..., 
                'pubkey':..., 
                'seckey':...}
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

    def get_identities(self):
        """Get identities
        
        :return:
            .. code-block:: python
               
               [
                   {'uid':..., 
                    'user':..., 
                    'timestamp':..., 
                    'ttl':..., 
                    'ip':...},
                ...
                ]
        """
        try:
            res = []
            for key in self.redis_manager.keys(self.prefix+'*'):
                identity = self.redis_manager.get(key)
                data = pickle.loads(identity)
                ttl = self.redis_manager.ttl(key)
                res.append({'uid': data['uid'], 'user': data['user']['name'],
                            'timestamp': data['timestamp'], 'ttl': ttl,
                            'ip': data['ip']})
        except Exception as ex:
            self.logger.error('No identities found: %s' % ex)
            raise ApiManagerError('No identities found')

        self.logger.debug('Get identities from redis: %s' % (res))
        return res

    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple http credentials.

        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return:
            .. code-block:: python
               
               {'uid':..., 
                'user':..., 
                'timestamp':..., 
                'pubkey':..., 
                'seckey':...}
            
        :raise ApiManagerError:         
        """
        try:
            identity = self.api_client.simplehttp_login(user, pwd, user_ip)
        except BeehiveApiClientError as ex:
            self.logger.error(ex.value, exc_info=1)
            raise ApiManagerError(ex.value, code=ex.code)
        
        return identity

    def get_oauth2_identity(self, token):
        """Get identity that correspond to oauth2 access token
        
        :param token: identity id
        :return:

            .. code-block:: python
               
               {'uid':..., 
                'user':..., 
                'timestamp':..., 
                'pubkey':..., 
                'seckey':...}
            
        :raise ApiManagerError:
        """
        identity = self.get_identity(token)
        self.redis_manager.expire(self.prefix + token, self.expire)
        self.logger.debug('Extend identity %s expire' % (token))
        return identity

    def verify_request_signature(self, uid, sign, data):
        """Verify Request signature.

        :param uid: identity id
        :param sign: request sign
        :param data: request data
        :return:

            .. code-block:: python
               
               {'uid':..., 
                'user':..., 
                'timestamp':..., 
                'pubkey':..., 
                'seckey':...}
            
        :raise ApiManagerError:
        """
        # get identity
        identity = self.get_identity(uid)
        # verify signature
        pubkey64 = identity['pubkey']
        
        try:
            # import key
            signature = binascii.a2b_hex(sign)
            pub_key = binascii.a2b_base64(pubkey64)
            key = RSA.importKey(pub_key)
            
            # create data hash
            hash_data = SHA256.new(data)

            # verify sign
            verifier = PKCS1_v1_5.new(key)
            res = verifier.verify(hash_data, signature)
            
            # extend expire time of the redis key
            if res is True:
                self.redis_manager.expire(self.prefix + uid, self.expire)
                self.logger.debug('Data signature %s for identity %s is valid. Extend expire.' % (sign, uid))
        except:
            self.logger.error('Data signature for identity %s is not valid' % uid)
            raise ApiManagerError('Data signature for identity %s is not valid' % uid, code=401)

        return identity

    def register_modules(self, register_api=True):
        self.logger.info('Configure modules - START')
        
        module_classes = self.params['api_module']
        if type(module_classes) is str:
            module_classes = [module_classes]
        
        for item in module_classes:
            # check if module is primary
            main = False
            if item.find(',') > 0:
                item, main = item.split(',')
                main = str2bool(main)
            # import module class
            module_class = import_class(item)
            # instance module class
            module = module_class(self)
            # set main module
            if main is True:
                self.main_module = module
            self.logger.info('Register module: %s' % item)
        
        if 'api_plugin' in self.params:
            plugin_pkgs = self.params['api_plugin']
            if type(plugin_pkgs) is str:
                plugin_pkgs = [plugin_pkgs]
            
            if len(plugin_pkgs) > 0:
                plpkg = []
                for x in plugin_pkgs:
                    for p in x.replace(' ', '').split():
                        plpkg.append(p)
                plugin_pkgs = plpkg
                
            # plugin_pkgs
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
        if register_api is True:
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
        """Configure api manager"""
        self.logger.info('Configure server - CONFIGURE')

        if self.is_engine_configured() is True:
            # open db session
            self.get_session()
            operation.perms = None
            
            try:
                # get configurator instance
                configurator = ConfigDbManager()     
                
                ##### oauth2 configuration #####
                self.logger.info('Configure oauth2 - CONFIGURE')
                try:
                    self.oauth2_endpoint = self.params.get('oauth2_endpoint')
                    self.logger.info('Setup oauth2 endpoint: %s' % self.oauth2_endpoint)
                    self.logger.info('Configure oauth2 - CONFIGURED')
                except:
                    self.logger.warning('Configure oauth2 - NOT CONFIGURED')
                ##### oauth2 configuration #####
                
                ##### redis configuration #####
                self.logger.info('Configure redis - CONFIGURE')
                # connect to redis
                redis_uri = self.params['redis_identity_uri']
                                             
                # parse redis uri
                parsed_uri = parse_redis_uri(redis_uri)
                    
                # set redis manager
                self.redis_manager = None
                if parsed_uri['type'] == 'single':
                    self.redis_manager = redis.StrictRedis(
                        host=parsed_uri['host'], 
                        port=parsed_uri['port'],
                        password=parsed_uri.get('pwd', None),
                        db=parsed_uri['db'],
                        socket_timeout=5,
                        socket_connect_timeout=5)
                elif parsed_uri['type'] == 'cluster':
                    self.redis_manager = RedisCluster(
                        startup_nodes=parsed_uri['nodes'],
                        password=parsed_uri.get('pwd', None),
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5)
                
                self.logger.debug(self.redis_manager)
                
                # app session
                if self.app is not None:
                    self.app.config.update(
                        SESSION_COOKIE_NAME='auth-session',
                        # SESSION_COOKIE_DOMAIN='beehive',
                        SESSION_COOKIE_SECURE=True,
                        PERMANENT_SESSION_LIFETIME=3600,
                        SESSION_TYPE='redis',
                        SESSION_USE_SIGNER=True,
                        SESSION_KEY_PREFIX='session:',
                        SESSION_REDIS=self.redis_manager
                    )                    
                    Session(self.app)
                    i = self.app.session_interface
                    self.app.session_interface = RedisSessionInterface2(
                        i.redis, i.key_prefix, i.use_signer, i.permanent)
                    self.logger.info('Setup redis session manager: %s' % self.app.session_interface)
    
                self.logger.info('Configure redis - CONFIGURED')  
                ##### redis configuration #####

                ##### cache configuration #####
                self.logger.info('Configure cache - CONFIGURE')

                if self.redis_manager is not None:
                    self.cache_manager = CacheClient(self.redis_manager)
                    self.logger.debug(self.cache_manager)

                self.logger.info('Configure cache - CONFIGURED')
                ##### cache configuration #####

                ##### scheduler reference configuration #####
                self.logger.info('Configure scheduler reference - CONFIGURE')
                
                try:
                    from beehive.common.task.manager import configure_task_manager
                    from beehive.common.task.manager import configure_task_scheduler
                    
                    # task manager
                    broker_url = self.params['broker_url']
                    result_backend = self.params['result_backend']
                    internal_result_backend = self.params['redis_celery_uri']
                    task_manager = configure_task_manager(broker_url, result_backend,
                                                          task_queue=self.params['broker_queue'])
                    task_manager.api_manager = self
                    self.celery_broker_queue = self.params['broker_queue']
                    self.redis_taskmanager = RedisManager(internal_result_backend)

                    # scheduler
                    broker_url = self.params['broker_url']
                    schedule_backend = self.params['result_backend']
                    # internal_schedule_backend = self.params['redis_celery_uri']
                    configure_task_scheduler(broker_url, schedule_backend, task_queue=self.params['broker_queue'])
                    self.redis_scheduler = RedisManager(schedule_backend)
    
                    self.logger.info('Configure scheduler reference - CONFIGURED')
                except:
                    self.logger.warning('Configure scheduler reference - NOT CONFIGURED')
                ##### scheduler reference configuration #####
                
                ##### security configuration #####
                # configure only with auth module
                try:
                    if configurator.exist(app=self.app_name, group='auth'):
                        confs = configurator.get(app=self.app_name, group='auth')
                        self.logger.info('Configure security - CONFIGURE')

                        # Create authentication providers
                        for conf in confs:
                            item = json.loads(conf.value)
                            if item['type'] == 'db':
                                auth_provider = DatabaseAuth(AuthDbManager, self.db_manager, SystemUser)
                            elif item['type'] == 'ldap':
                                bind_pwd = decrypt_data(item['bind_pwd'])
                                auth_provider = LdapAuth(item['host'], SystemUser, timeout=item['timeout'],
                                                         ssl=item['ssl'], dn=item['dn'],
                                                         search_filter=item['search_filter'], search_id=item['search_id'],
                                                         bind_user=item['bind_user'], bind_pwd=bind_pwd)
                            self.auth_providers[item['provider']] = auth_provider
                            self.logger.info('Setup authentication provider: %s' % auth_provider)

                        self.logger.info('Configure security - CONFIGURED')
                    else:
                        self.logger.warning('Configure security - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure security - NOT CONFIGURED')
                ##### security configuration #####
        
                ##### camunda configuration #####
                try:
                    self.logger.info('Configure Camunda - CONFIGURE')            
                    from beedrones.camunda import WorkFlowEngine as CamundaEngine
                    if configurator.exist(app=self.app_name, group='bpmn', name='camunda.cluster'):
                        conf = configurator.get(app=self.app_name, group='bpmn', name='camunda.cluster')[0].value
                        self.logger.info('Configure Camunda - CONFIG app %s: %s' % (self.app_name, conf))
                        item = json.loads(conf)

                        self.camunda_engine = CamundaEngine(item['conn'], user=item['user'], passwd=item['passwd'])
                        self.logger.info('Configure Camunda  - CONFIGURED')
                    else:
                        self.logger.warning('Configure Camunda  - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure Camunda  - NOT CONFIGURED')
                ##### camunda configuration #####
                
                ##### awx configuration #####
                try:
                    self.logger.info('Configure AWX - CONFIGURE')            
                    #from beedrones.awx.old.awxclient import AwxClient, Awx
                    #self.awx_client = Awx(AwxClient(self.params['awx_uri'], user=self.params['awx_user'],
                    #                                passwd=self.params['awx_password'],
                    #                                organization=self.params['awx_organization']))
                    self.logger.info('Configure AWX  - CONFIGURED')            
                except:
                    self.logger.warning('Configure AWX  - NOT CONFIGURED')
                ##### awx configuration #####

                ##### elasticsearch configuration #####
                try:
                    self.logger.info('Configure elasticsearch - CONFIGURE')
                    el_nodes = self.params.get('elasticsearch_nodes', None)
                    if el_nodes is not None and el_nodes != '' and el_nodes != '':
                        self.elasticsearch = Elasticsearch(
                            el_nodes.split(','),
                            # sniff before doing anything
                            sniff_on_start=True,
                            # refresh nodes after a node fails to respond
                            sniff_on_connection_fail=True,
                            # and also every 60 seconds
                            sniffer_timeout=60
                        )
                        self.logger.info('Elasticsearch client: %s' % self.elasticsearch)
                        self.logger.info('Configure elasticsearch  - CONFIGURED')
                    else:
                        self.logger.warning('Configure elasticsearch  - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure elasticsearch  - NOT CONFIGURED')
                ##### awx configuration #####

                ##### sendmail configuration #####
                try:
                    self.logger.debug('Configure sendmail - CONFIGURE')
                    if configurator.exist(app=self.app_name, group='mail'):
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

                        self.logger.info('Configure sendmail - CONFIGURED')
                    else:
                        self.logger.warning('Configure sendmail - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure sendmail - NOT CONFIGURED')
                ##### sendmail configuration #####
    
                ##### gateway configuration #####
                try:
                    if configurator.exist(app=self.app_name, group='gateway'):
                        conf = configurator.get(app=self.app_name, group='gateway')
                        self.logger.info('Configure gateway - CONFIGURE')
                        for item in conf:
                            gw = json.loads(item.value)
                            self.gateways[gw['name']] = gw
                            self.logger.info('Setup gateway: %s' % gw)
                        self.logger.info('Configure gateway - CONFIGURED')
                    else:
                        self.logger.warning('Configure gateway - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure gateway - NOT CONFIGURED')
                ##### gateway configuration #####
        
                ##### service queue configuration #####
                try:
                    self.logger.info('Configure service queue - CONFIGURE')
        
                    self.redis_service_uri = self.params['redis_queue_uri']
                    self.redis_service_exchange = self.params['redis_queue_name']
        
                    self.logger.info('Configure service queue - CONFIGURED')
                except:
                    self.logger.warning('Configure service queue - NOT CONFIGURED')                
                ##### service queue configuration #####
        
                ##### event queue configuration #####
                try:
                    self.logger.info('Configure event queue- CONFIGURE')
                    if configurator.exist(app=self.app_name, group='queue', name='queue.event'):
                        conf = configurator.get(app=self.app_name, group='queue', name='queue.event')

                        # setup event producer
                        conf = json.loads(conf[0].value)
                        # set redis manager
                        self.redis_event_uri = self.params['redis_queue_uri']
                        self.redis_event_exchange = conf['queue']

                        # create instance of event producer
                        self.event_producer = EventProducerRedis(
                            self.redis_event_uri, self.redis_event_exchange, framework='komb')
                        self.logger.info('Configure exchange %s on %s' % (self.redis_event_exchange,
                                                                          self.redis_event_uri))
                        self.logger.info('Configure event queue - CONFIGURED')
                    else:
                        self.logger.warning('Configure event queue - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure event queue - NOT CONFIGURED')                
                ##### event queue configuration #####
        
                ##### catalog queue configuration #####
                try:
                    self.logger.info('Configure catalog queue - CONFIGURE')
                    if configurator.exist(app=self.app_name, group='queue', name='queue.catalog'):
                        conf = configurator.get(app=self.app_name, group='queue', name='queue.catalog')

                        # setup catalog producer
                        conf = json.loads(conf[0].value)
                        self.redis_catalog_uri = self.params['redis_queue_uri']
                        #self.redis_catalog_uri = conf['uri']
                        self.redis_catalog_channel = conf['queue']

                        # create instance of catalog producer
                        from beehive.module.catalog.producer import CatalogProducerRedis
                        self.catalog_producer = CatalogProducerRedis(self.redis_catalog_uri, self.redis_catalog_channel)
                        self.logger.info('Configure queue %s on %s' % (self.redis_catalog_channel, self.redis_catalog_uri))
                        self.logger.info('Configure catalog queue - CONFIGURED')
                    else:
                        self.logger.warning('Configure catalog queue - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure catalog queue - NOT CONFIGURED')
                ##### catalog queue configuration #####
        
                ##### tcp proxy configuration #####
                try:
                    self.logger.info('Configure tcp proxy - CONFIGURE')
                    if configurator.exist(app=self.app_name, group='tcpproxy'):
                        conf = configurator.get(app=self.app_name, group='tcpproxy')
                        self.tcp_proxy = conf[0].value
                        self.logger.info('Setup tcp proxy: %s' % self.tcp_proxy)
                        self.logger.info('Configure tcp proxy - CONFIGURED')
                    else:
                        self.logger.warning('Configure tcp proxy - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure tcp proxy - NOT CONFIGURED') 
                ##### tcp proxy configuration #####
    
                ##### http proxy configuration #####
                try:
                    self.logger.info('Configure http proxy - CONFIGURE')
                    if configurator.exist(app=self.app_name, group='httpproxy'):
                        conf = configurator.get(app=self.app_name, group='httpproxy')
                        proxy = conf[0].value
                        self.http_proxy = proxy
                        self.logger.info('Setup http proxy: %s' % self.http_proxy)
                        self.logger.info('Configure http proxy - CONFIGURED')
                    else:
                        self.logger.warning('Configure http proxy - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure http proxy - NOT CONFIGURED')
                ##### http proxy configuration #####

                ##### stacks uri reference configuration #####
                try:
                    self.logger.info('Configure stacks uri reference - CONFIGURE')
                    if configurator.exist(app=self.app_name, group='resource', name='stacks_uri'):
                        conf = configurator.get(app=self.app_name, group='resource', name='stacks_uri')
                        self.stacks_uri = conf[0].value
                        self.logger.info('Setup stacks uri reference: %s' % self.stacks_uri)
                        self.logger.info('Configure stacks uri reference - CONFIGURED')
                    else:
                        self.logger.warning('Configure stacks uri reference - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure stacks uri reference - NOT CONFIGURED')
                ##### stacks uri reference configuration #####

                ##### git uri reference configuration #####
                try:
                    self.logger.info('Configure git uri reference - CONFIGURE')
                    self.git = {
                        'uri': self.params['git_uri'],
                        'branch': self.params['git_branch'],
                    }
                    self.logger.info('Setup git reference: %s' % self.git)
                    self.logger.info('Configure git uri reference - CONFIGURED')
                except:
                    self.logger.warning('Configure git uri reference - NOT CONFIGURED')
                ##### git uri reference configuration #####
                
                ##### api authentication configuration #####
                # not configure for auth module
                try:
                    self.logger.info('Configure apiclient - CONFIGURE')

                    self.catalog = self.params['api_catalog']
                    self.logger.info('Get catalog: %s' % self.catalog)

                    endpoint = self.params.get('api_endpoint', None)
                    self.logger.info('Get api endpoint: %s' % endpoint)

                    if endpoint is None:
                        self.endpoints = [self.app_uri]
                    else:
                        self.endpoints = [endpoint]
                    self.logger.info('Get auth endpoints: %s' % self.endpoints)                    
                    
                    # get auth system user
                    if configurator.exist(app=self.app_name, group='api', name='user'):
                        auth_user = configurator.get(app=self.app_name, group='api', name='user')[0].value
                        self.auth_user = json.loads(auth_user)
                        self.logger.info('Get auth user: %s' % self.auth_user.get('name', None))

                        # configure api client
                        self.configure_api_client()

                        self.logger.info('Configure apiclient - CONFIGURED')
                    else:
                        self.logger.warning('Configure apiclient - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure apiclient - NOT CONFIGURED')
                ##### api authentication configuration #####
                
                del configurator
                
            except ApiManagerError as e:
                raise
            
            # release db session
            self.release_session()
            operation.perms = None
        
        self.logger.info('Configure server - CONFIGURED')
    
    def configure_api_client(self):
        """Configure api client instance
        """
        self.api_client = ApiClient(self.endpoints, 
                                    self.auth_user['name'], 
                                    self.auth_user['pwd'],
                                    None,
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
            self.logger.info('Register %s instance in catalog' % self.app_endpoint_id)
            
    def register_catalog(self):
        """Create endpoint instance in catalog
        """
        register = self.params.get('register-catalog', True)
        register = str2bool(register)
        
        # skip catalog registration - usefool for temporary instance
        if register is False:
            return
        
        # register catalog
        catalog = self.catalog
        service = self.app_subsytem
        uri = self.app_uri        
        self.catalog_producer.send(self.app_endpoint_id, self.app_desc, service, catalog, uri)
        self.logger.info('Register %s instance in catalog' % self.app_endpoint_id)
            
    def register_monitor(self):
        """Register instance in monitor
        """
        register = self.params.get('register-monitor', True)
        register = str2bool(register)
        
        # skip monitor registration - usefool for temporary instance
        if register is False:
            return
                        
        
class ApiModule(object):
    """ """
    def __init__(self, api_manager, name):
        self.logger = logging.getLogger(self.__class__.__module__+  '.' + self.__class__.__name__)
        
        self.api_manager = api_manager
        self.name = name
        self.views = []
        self.controller = None
        self.api_routes = []
        
        self.api_manager.modules[name] = self
    
    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+'.'+self.__class__.__name__, id(self))    

    def info(self):
        """Get module infos.
        
        :return: Dictionary with info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {'name': self.name, 'api': self.api_routes}
        return res
    
    @property
    def redis_manager(self):
        return self.api_manager.redis_manager   

    @property
    def job_manager(self):
        return self.api_manager.job_manager

    @property
    def cache(self):
        return self.api_manager.cache_manager

    @property
    def cache_ttl(self):
        return self.api_manager.cache_manager_ttl

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
        """Init object
        
        :param session: database session
        """
        # session = self.get_session()
        session = operation.session
        self.get_controller().init_object()
        # self.release_session(session)
    
    def register_api(self):
        if self.api_manager.app is not None:
            for api in self.apis:
                api.register_api(self)
                # self.logger.debug('Register api view %s' % (api.__class__))

    def get_superadmin_permissions(self):
        """Get superadmin permissions
        
        :param session: database session
        """
        perms = self.get_controller().get_superadmin_permissions()
        return perms
    
    def get_controller(self):
        raise NotImplementedError()


class ApiController(object):
    """ """
    def __init__(self, module):
        self.logger = logging.getLogger(self.__class__.__module__+ '.' + self.__class__.__name__)
        
        self.module = module
        self.version = 'v1.0'

        # base event_class. Change in every controller with ApiEvent subclass
        # self.event_class = ApiEvent
        
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
        
    def resolve_fk_id(self, key, get_entity, data, new_key=None ):
        fk = data.get(key)        
        if fk is not None and not isinstance(fk, int) and not fk.isdigit():
            oid = self.resolve_oid(fk, get_entity)
            if new_key is None:
                data[key] = oid
            else:
                data.pop(key)
                data[new_key] = oid
        else:
            if new_key is not None and data.get(key, None) is not None:
                data[new_key] = data.pop(key, None)
                
    def resolve_oid(self, fk, get_entity): 
        res = fk   
        if fk is not None and not isinstance(fk, int) and not fk.isdigit():
            res = get_entity(fk).oid
        return res
            
    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+'.'+
                                 self.__class__.__name__, id(self))    
    
    @property
    def redis_manager(self):
        return self.module.redis_manager
    
    @property
    def mailer(self):
        return (self.module.api_manager.mailer, 
                self.module.api_manager.mail_sender)

    @property
    def api_manager(self):
        return self.module.api_manager

    @property
    def api_client(self):
        return self.module.api_manager.api_client 
    
    @property
    def awx_client(self):
        return self.module.api_manager.awx_client 

    @property
    def cache(self):
        return self.module.api_manager.cache_manager

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
        self.logger.info('Init %s - START' % self)
        self.logger.info('Init childs: %s' % self.child_classes)
        # init controller child classes
        for child in self.child_classes:
            child(self).init_object()
        self.logger.info('Init %s - STOP' % self)
    
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
                   
                   {'uid':..., 
                    'user':..., 
                    'timestamp':..., 
                    'pubkey':..., 
                    'seckey':...}
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
        :raise ApiManagerError:
        """
        return self.module.api_manager.get_oauth2_identity(token)

    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.
        
        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        :raise ApiManagerError:
        """
        return self.module.api_manager.verify_simple_http_credentials(user, pwd, user_ip)

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
                 
                    {objdef:[objid1, objid2, ..]}
                 
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
                        perm_action in ['*', action]):
                        # defs.append(perm_definition)
                        objids.append(perm_objid)
                    
                    # loop between object objids, compact objids and verify match
                    if len(objids) > 0:
                        res[definition] = objids
                elif objtype is not None:      
                    if perm_objtype == objtype and perm_action in ['*', action]:
                        if perm_definition in res:
                            res[perm_definition].append(perm_objid)
                        else:
                            res[perm_definition] = [perm_objid]
                else:
                    if perm_action in ['*', action]:
                        if perm_definition in res:
                            res[perm_definition].append(perm_objid)
                        else:
                            res[perm_definition] = [perm_objid]                    

            for objdef, objids in res.items():
                # loop between object objids, compact objids and verify match
                if len(objids) > 0:
                    res[objdef] = extract(res[objdef])
                    # self.logger.debug('%s:%s can %s objects {%s, %s, %s}' %
                    #    (user[0], user[1], action, objtype, objdef, res[objdef]))
            
            if len(res.keys()) > 0:
                return res
            else:
                if definition is None:
                    definition = ''
                raise Exception(u"Identity %s can not '%s' objects '%s:%s'" %
                                (operation.user[2], action, objtype, definition))
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=403)

    def has_needs(self, needs, perms):
        """Verify if permissions overlap needs.
        
        :param needs: object needs as python set
        :param perms: user permissions as python set
        :return: True if overlap
        :rtype: bool
        """
        if len(needs.intersection(perms)) > 0:
            return True
        self.logger.warn('Perms %s do not overlap needs %s' % (perms, needs))
        return False

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
            if action == 'insert':
                if objid is None or objid == '*':
                    objid = '*'
                else:
                    objid = objid + '//*'
            needs = self.get_needs(objid.split('//'))
            
            # check if needs overlaps perms
            res = self.has_needs(needs, objset)
            if res is False:
                raise ApiManagerError('')
        except ApiManagerError:
            msg = u"Identity %s can not '%s' objects '%s:%s.%s'" % (operation.user[2], action, objtype, objdef, objid)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=403)
        return res

    #
    # encryption method
    #
    def encrypt_data(self, data):
        """Encrypt data using a fernet key and a symmetric algorithm

        :param data: data to encrypt
        :return: encrypted data
        """
        res = encrypt_data(data)
        return res

    def decrypt_data(self, data):
        """Decrypt data using a fernet key and a symmetric algorithm

        :param data: data to decrypt
        :return: decrypted data
        """
        res = decrypt_data(data)
        return res

    #
    # helper model get method
    #
    def get_entity(self, entity_class, model_class, oid, for_update=False, details=True, *args, **kvargs):
        """Get single entity by oid (id, uuid, name) if exists

        :param entity_class: Controller ApiObject Extension class. Specify when you want to verif match between
            objdef of the required resource and find resource
        :param model_class: Model ApiObject Extension class
        :param oid: entity model id or name or uuid
        :param for_update: [default=False]
        :param details: if True call custom method post_get()
        :return: entity instance
        :raise ApiManagerError`:
        """
        try:
            entity = self.manager.get_entity(model_class, oid, for_update, *args, **kvargs)
        except QueryError as ex:         
            self.logger.error(ex, exc_info=1)
            entity_name = entity_class.__name__
            raise ApiManagerError('%s %s not found or name is not unique' % (entity_name, oid), code=404)

        if entity is None:
            entity_name = entity_class.__name__
            self.logger.warn('%s %s not found' % (entity_name, oid))
            raise ApiManagerError('%s %s not found' % (entity_name, oid), code=404)
            
        # check authorization
        if operation.authorize is True:
            self.check_authorization(entity_class.objtype, entity_class.objdef, entity.objid, 'view')
        
        res = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                           desc=entity.desc, model=entity)
        
        # execute custom post_get
        if details is True:
            res.post_get()
        
        self.logger.debug('Get %s : %s' % (entity_class.__name__, res))
        return res

    def get_paginated_entities(self, entity_class, get_entities, page=0, size=10, order='DESC', field='id',
                               customize=None, *args, **kvargs):
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
        tags = []

        if operation.authorize is True:
            # verify permissions
            objs = self.can('view', entity_class.objtype, definition=entity_class.objdef)
            objs = objs.get(entity_class.objdef.lower())
        
            # create permission tags
            for p in objs:
                tags.append(self.manager.hash_from_permission(entity_class.objdef, p))
            self.logger.debug('Permission tags to apply: %s' % tags)
        else:
            kvargs['with_perm_tag'] = False
            self.logger.debug('Auhtorization disabled for command')
                
        try:
            entities, total = get_entities(tags=tags, page=page, size=size, order=order, field=field, *args, **kvargs)
            
            for entity in entities:
                obj = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                                   desc=entity.desc, model=entity)
                res.append(obj)
        
            # customize enitities
            if customize is not None:
                customize(res, tags=tags, *args, **kvargs)
            
            self.logger.debug('Get %s (total:%s): %s' % (entity_class.__name__, total, truncate(res)))
            return res, total
        except QueryError as ex:         
            self.logger.warn(ex, exc_info=1)
            return [], 0

    def get_entities(self, entity_class, get_entities, *args, **kvargs):
        """Get entities less pagination

        :param entity_class: ApiObject Extension class
        :param get_entities: model get_entities function. Return (entities, total)
        :param name: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param args: custom params
        :param kvargs: custom params
        :return: (list of entity_class instances, total)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = []
        objs = []
        tags = None

        if operation.authorize is True:
            # verify permissions
            objs = self.can('view', entity_class.objtype, definition=entity_class.objdef)
            objs = objs.get(entity_class.objdef.lower())
        
            # create permission tags
            # todo check me:  creo tags solo se operation.authorize altrimenti query fallisce senza tags
            tags = []
            for p in objs:
                tags.append(self.manager.hash_from_permission(entity_class.objdef, p))
            self.logger.debug('Permission tags to apply: %s' % tags)
                
        try:
            entities = get_entities(tags=tags, *args, **kvargs)

            for entity in entities:
                obj = entity_class(self, oid=entity.id, objid=entity.objid, 
                               name=entity.name, active=entity.active, 
                               desc=entity.desc, model=entity)
                res.append(obj)
            self.logger.debug('Get %s : %s' % (entity_class.__name__, truncate(res)))
            return res
        except QueryError as ex:         
            self.logger.warn(ex)
            return []


class ApiObject(object):
    """ """
    module = None
    objtype = ''
    objdef = ''
    objuri = ''    
    objname = 'object'
    objdesc = ''
    
    # set this to define db manger methdod used for update. If not set update is not supported
    update_object = None

    # set this to define db manger methdod used for patch. If not set delete is not supported
    patch_object = None

    # set this to define db manger methdod used for delete. If not set delete is not supported
    delete_object = None
    
    register = True
    
    API_OPERATION = 'API'
    SYNC_OPERATION = 'CMD'
    ASYNC_OPERATION = 'JOB'

    # cache key
    cache_key = 'object.get'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, active=None, model=None):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
        
        self.controller = controller
        self.model = model # db model if exist
        self.oid = oid # object internal db id
        self.objid = objid
        self.name = name
        self.desc = desc
        self.active = active
        
        # object uuid
        self.uuid = None
        if self.model is not None:
            self.uuid = self.model.uuid        

        # object uri
        self.objuri = '/%s/%s/%s' % (self.controller.version, self.objuri, self.uuid)
        
        # child classes
        self.child_classes = []

        self._admin_role_prefix = 'admin'

    def __repr__(self):
        return '<%s id=%s objid=%s name=%s>' % (self.__class__.__module__+'.'+self.__class__.__name__, self.oid,
                                                 self.objid, self.name)
 
    @property
    def manager(self):
        return self.controller.manager

    @property
    def api_manager(self):
        return self.controller.module.api_manager

    @property
    def api_client(self):
        return self.controller.module.api_manager.api_client

    @property
    def cache(self):
        return self.controller.module.api_manager.cache_manager

    @property
    def cache_ttl(self):
        return self.controller.module.api_manager.cache_manager_ttl

    @property
    def camunda_engine(self):
        return self.controller.module.api_manager.camunda_engine

    @property
    def celery_broker_queue(self):
        return self.controller.module.api_manager.celery_broker_queue

    @staticmethod
    def join_typedef(parent, child):
        """ 
        Join typedef parent with typedef child
        """        
        return '.'.join([parent, child])
    
    @staticmethod
    def get_type(self):
        """ """        
        return self.type, self.definition, self.__class__
    
    def get_user(self):
        """ """
        user = {
            'user': operation.user[0],
            'server': operation.user[1],
            'identity': operation.user[2],
            'api_id': operation.id
            # 'encryption_key': operation.encryption_key,
        }
        return user
    
    @staticmethod
    def _get_value(objtype, args):
        # logging.getLogger('gibbon.cloudapi.process').debug(objtype)
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    def convert_timestamp(self, timestamp):
        """
        """
        timestamp = datetime.fromtimestamp(timestamp)
        return format_date(timestamp)

    #
    # encryption method
    #
    def encrypt_data(self, data):
        """Encrypt data using a fernet key and a symmetric algorithm

        :param data: data to encrypt
        :return: encrypted data
        """
        return self.controller.encrypt_data(data)

    def decrypt_data(self, data):
        """Decrypt data using a fernet key and a symmetric algorithm

        :param data: data to decrypt
        :return: decrypted data
        """
        return self.controller.decrypt_data(data)

    #
    # info
    #
    def set_cache(self):
        """Cache object required infos.

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        data = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'desc': self.desc,
        }
        self.cache.set(self.cache_key + '.' + self.oid, data, ttl=self.cache_ttl)

    def small_info(self):
        """Get object small infos.
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },            
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'active': str2bool(self.active),
        }
        return res
    
    def info(self):
        """Get object info
        
        :return: Dictionary with object info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'desc': self.desc,
            'active': str2bool(self.active),
            'date': {
                'creation': format_date(self.model.creation_date),
                'modified': format_date(self.model.modification_date),
                'expiry': ''
            }
        }
        
        if self.model.expiry_date is not None:
            res['date']['expiry'] = format_date(self.model.expiry_date)
        
        return res

    def detail(self):
        """Get object extended info
        
        :return: Dictionary with object detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        res = {
            '__meta__': {
                'objid': self.objid,
                'type': self.objtype,
                'definition': self.objdef,
                'uri': self.objuri,
            },
            'id': self.oid,
            'uuid': self.uuid,
            'name': self.name,
            'desc': self.desc,
            'active': str2bool(self.active),
            'date': {
                'creation': format_date(self.model.creation_date),
                'modified': format_date(self.model.modification_date),
                'expiry': ''
            }
        }

        if self.model.expiry_date is not None:
            res['date']['expiry'] = format_date(self.model.expiry_date)

        return res

    #
    # authorization
    #
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        self.logger.info('Init api object %s.%s - START' % (self.objtype, self.objdef))
        
        try:
            # call only once during db initialization
            # add object type
            self.api_client.add_object_types(self.objtype, self.objdef)
            
            # add object and permissions
            objs = self._get_value(self.objdef, [])
            self.api_client.add_object(self.objtype, self.objdef, objs, self.objdesc)

            self.logger.info('Init api object %s.%s - STOP' % (self.objtype, self.objdef))
        except ApiManagerError as ex:
            self.logger.warn(ex.value)
            
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
        act_obj = ['*' for i in args]
        objdis = ['//'.join(act_obj)]
        pos = 0
        for arg in args:
            act_obj[pos] = arg
            objdis.append('//'.join(act_obj))
            pos += 1
    
        return objdis    
    
    def register_object_permtags(self, args):
        """Register object permission tags. Create new permission tags in 
        perm_tag if they do not already exist. Create association between
        permission tags and object in perm_tag_entity.
        
        :param args: objid split by //
        """
        # reopen session
        # self.release_session(None)
        # self.get_session()

        if self.oid is not None:
            ids = self.get_all_valid_objids(args)
            for i in ids:
                perm = '%s-%s' % (self.objdef.lower(), i)
                tag = self.manager.hash_from_permission(self.objdef.lower(), i)
                table = self.objdef
                self.manager.add_perm_tag(tag, perm, self.oid, table)
            
    def deregister_object_permtags(self):
        """Deregister object permission tags.
        """
        if self.objid is not None:
            ids = self.get_all_valid_objids(self.objid.split('//'))
            tags = []
            for i in ids:
                tags.append(self.manager.hash_from_permission(self.objdef, i))    
            table = self.objdef
            self.manager.delete_perm_tag(self.oid, table, tags)

    def register_object(self, objids, desc=''):
        """Register object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param desc: object description        
        :return:
        :raise ApiManagerError: 
        """
        self.logger.debug('Register api object: %s:%s %s - START' % (self.objtype, self.objdef, objids))

        objids = [o.decode('utf-8') for o in objids]

        # add object and permissions
        self.api_client.add_object(self.objtype, self.objdef, '//'.join(objids), desc)
        
        # register permission tags
        self.register_object_permtags(objids)
        
        self.logger.debug('Register api object: %s:%s %s - STOP' % (self.objtype, self.objdef, objids))

        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).register_object(list(objids), desc=child.objdesc)
            
    def deregister_object(self, objids):
        """Deregister object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param objid: parent objid
        """
        self.logger.debug('Deregister api object %s:%s %s - START' % (self.objtype, self.objdef, objids))
        
        # deregister permission tags
        self.deregister_object_permtags()
        
        # remove object and permissions
        objid = '//'.join([o.decode('utf-8') for o in objids])
        self.api_client.remove_object(self.objtype, self.objdef, objid)        
        
        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).deregister_object(list(objids))
        
        self.logger.debug('Deregister api object %s:%s %s - STOP' % (self.objtype, self.objdef, objid))
    
    def set_superadmin_permissions(self):
        """ """
        self.set_admin_permissions('ApiSuperadmin', [])
        
    def set_admin_permissions(self, role, args):
        """ """
        # set main permissions
        self.api_client.append_role_permissions(role, self.objtype, self.objdef,
                                                self._get_value(self.objdef, args), '*')
        
    def set_viewer_permissions(self, role, args):
        """ """
        # set main permissions
        self.api_client.append_role_permissions(role, self.objtype, self.objdef,
                                                self._get_value(self.objdef, args), 'view')
    
    def verify_permisssions(self, action, *args, **kvargs):
        """Short method to verify permissions.

        :param action: action to verify. Can be *, view, insert, update, delete, use
        :return: True if permissions overlap
        :raise ApiManagerError:
        """        
        # check authorization
        if operation.authorize is True:
            self.controller.check_authorization(self.objtype, self.objdef, self.objid, action)
    
    def authorization(self, objid=None, *args, **kvargs):
        """Get entity authorizations 
        
        :param objid: resource objid
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: [(perm, roles), ...]
        :raise ApiManagerError: if query empty return error.
        """
        try:
            # resource permissions
            if objid == None:
                objid = self.objid
            perms, total = self.api_client.get_permissions(self.objtype, self.objdef, objid, cascade=True, **kvargs)

            return perms, total
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)    
    
    #
    # pre, post function
    #
    def post_get(self):
        """Post get function. This function is used in get_entity method. Extend this function to extend description
        info returned after query.

        :raise ApiManagerError:
        """
        pass
    
    @staticmethod
    def pre_create(controller, *args, **kvargs):
        """Check input params before resource creation. This function is used in container resource_factory method.
        Extend this function to manipulate and validate create input params.
        
        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs
    
    @staticmethod
    def post_create(controller, *args, **kvargs):
        """Post create function. This function is used in object_factory method. Used only for synchronous creation.
        Extend this function to execute some operation after entity was created.
        
        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return None

    @staticmethod
    def pre_import(controller, *args, **kvargs):
        """Check input params before resource creation. This function is used in container resource_factory method.
        Extend this function to manipulate and validate import input params.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    @staticmethod
    def post_import(controller, *args, **kvargs):
        """Post import function. This function is used in object_factory method. Used only for synchronous creation.
        Extend this function to execute some operation after entity was importd.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return None

    def pre_update(self, *args, **kvargs):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.
        
        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """        
        return kvargs

    def post_update(self, *args, **kvargs):
        """Post update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: True
        :raise ApiManagerError:
        """
        return True

    def pre_patch(self, *args, **kvargs):
        """Pre patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.
        
        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method. Extend this function to execute action after
        object was deleted.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return True

    def pre_expunge(self, *args, **kvargs):
        """Pre expunge function. This function is used in expunge method. Extend this function to manipulate and
        validate expunge input params.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return kvargs

    def post_expunge(self, *args, **kvargs):
        """Post expunge function. This function is used in expunge method. Extend this function to execute action after
        object was expunged.

        :param list args: custom params
        :param dict kvargs: custom params
        :return: kvargs
        :raise ApiManagerError:
        """
        return True

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
    def send_event(self, op, args=None, params={}, opid=None, response=True, exception=None, etype=None, elapsed=0):
        """Publish an event to event queue.
        
        :param op: operation to audit
        :param opid: operation id to audit [optional]
        :param params: operation params [default={}]
        :param response: operation response. [default=True]
        :param exception: exceptione raised [optinal]
        :param etype: event type. Can be ApiObject.SYNC_OPERATION, ApiObject.ASYNC_OPERATION
        :param elapsed: elapsed time [default=0] 
        """
        if opid is None:
            opid = operation.id
        objid = '*'
        if self.objid is not None:
            objid = self.objid
        if etype is None:
            etype = self.SYNC_OPERATION
        if exception is not None:
            response = (False, str(exception))
        else:
            response = [response]

        action = op.split('.')[-1]

        import inspect

        # remove object from args - it does not serialize in event
        nargs = []
        for a in args:
            if inspect.isclass(a) is False:
                nargs.append(a)

        event_params = {}
        for k, v in params.items():
            if inspect.isclass(v) is False:
                event_params[k] = v
        
        data = {
            'opid': opid,
            # 'op': '%s.%s' % (self.objdef, op),
            'op': op,
            'api_id': opid,
            'args': nargs,
            'params': event_params,
            'elapsed': elapsed,
            'response': response
        }

        source = {
            'user': operation.user[0],
            'ip': operation.user[1],
            'identity': operation.user[2]
        }
        
        dest = {
            'ip': self.controller.module.api_manager.server_name,
            'port': self.controller.module.api_manager.http_socket,
            'objid': objid,
            'objtype': self.objtype,
            'objdef': self.objdef,
            'action': action
        }      
        
        # send event
        try:
            client = self.controller.module.api_manager.event_producer
            client.send(etype, data, source, dest)
        except Exception as ex:
            self.logger.warning('Event can not be published. Event producer '\
                                'is not configured - %s' % ex)

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
    @trace(op='update')
    def update(self, *args, **kvargs):
        """Update entity.
        
        :param args: custom params
        :param kvargs: custom params
        :return: entity uuid
        :raise ApiManagerError:
        """
        if self.update_object is None:
            raise ApiManagerError('Update is not supported for %s:%s' % (self.objtype, self.objdef))
        
        # verify permissions
        self.verify_permisssions('update')
        
        # custom action
        if self.pre_update is not None:
            kvargs = self.pre_update(**kvargs)
        
        try:  
            res = self.update_object(oid=self.oid, *args, **kvargs)
            
            self.logger.debug('Update %s %s with data %s' % (self.objdef, self.oid, truncate(kvargs)))
            return self.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='update')
    def patch(self, *args, **kvargs):
        """Patch entity.

        :param args: custom params
        :param kvargs: custom params
        :return: entity uuid
        :raise ApiManagerError:
        """
        if self.patch_object is None:
            raise ApiManagerError('Patch is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('update')

        # custom action
        if self.pre_patch is not None:
            kvargs = self.pre_patch(**kvargs)

        try:
            self.patch_object(self.model)

            self.logger.debug('Patch %s %s' % (self.objdef, self.oid))
            return self.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='delete')
    def delete(self, soft=False, **kvargs):
        """Delete entity.
        
        :param kvargs: custom params
        :param soft: if True make a soft delete            
        :return: None            
        :raise ApiManagerError:
        """
        if self.delete_object is None:
            raise ApiManagerError('Delete is not supported for %s:%s' % (self.objtype, self.objdef))
        
        # verify permissions
        self.verify_permisssions('delete')
            
        # custom action
        if self.pre_delete is not None:
            kvargs = self.pre_delete(**kvargs)            
            
        try:  
            if soft is False:
                self.delete_object(oid=self.oid)
                # self.delete_object(self.oid)
                if self.register is True:
                    # remove object and permissions
                    self.deregister_object(self.objid.split('//'))
                
                self.logger.debug('Delete %s: %s' % (self.objdef, self.oid))
            else:
                self.delete_object(self.model)
                self.logger.debug('Soft delete %s: %s' % (self.objdef, self.oid))
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # custom action
        if self.post_delete is not None:
            self.post_delete(**kvargs)

        return None

    @trace(op='delete')
    def expunge(self, **kvargs):
        """Expunge entity.

        :param kvargs: custom params
        :return: None
        :raise ApiManagerError:
        """
        if self.expunge_object is None:
            raise ApiManagerError('Expunge is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('delete')

        # custom action
        if self.pre_expunge is not None:
            kvargs = self.pre_expunge(**kvargs)

        try:
            self.expunge_object(self.model)
            if self.register is True:
                # remove object and permissions
                self.deregister_object(self.objid.split('//'))

            self.logger.debug('Expunge %s: %s' % (self.objdef, self.oid))
        except TransactionError as ex:
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

        # custom action
        if self.post_expunge is not None:
            self.post_expunge(**kvargs)

        return None


class ApiInternalObject(ApiObject):
    objtype = 'auth'
    objdef = 'abstract'
    objdesc = 'Authorization abstract object'
    
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
        self.logger.info('Init api object %s.%s - START' % 
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
            
            self.logger.info('Init api object %s.%s - STOP' % 
                              (self.objtype, self.objdef))
        except (QueryError, TransactionError) as ex:
            self.logger.warn(ex.desc)
            
        # init child classes
        for child in self.child_classes:
            child(self.controller).init_object()
    
    def register_object(self, objids, desc=''):
        """Register object types, objects and permissions related to module.
        
        :param objids: objid split by //
        :param desc: object description
        :param objid: parent objid
        """
        self.logger.debug('Register api object %s:%s %s - START' % (self.objtype, self.objdef, objids))

        try:
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, '//'.join(objids), desc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
        except (QueryError, TransactionError) as ex:
            self.logger.error('Register api object: %s - ERROR' % (ex.desc))
            raise ApiManagerError(ex.desc, code=400)       
        
        # register permission tags
        self.register_object_permtags(objids)
        
        self.logger.debug('Register api object %s:%s %s - STOP' % (self.objtype, self.objdef, objs))
        
        # register child classes
        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).register_object(objids, desc=child.objdesc)
    
    def deregister_object(self, objids):
        """Deregister object types, objects and permissions related to module.
        
        :param args: objid split by //
        """
        self.logger.debug('Deregister api object %s:%s %s - START' % 
                          (self.objtype, self.objdef, objids))
        
        # deregister permission tags
        self.deregister_object_permtags()
        
        try:
            # remove object and permissions
            obj_type = self.auth_db_manager.get_object_type(
                objtype=self.objtype, objdef=self.objdef)[0][0]
            # objid = self._get_value(self.objdef, objids)
            objid = '//'.join([o.decode('utf-8') for o in objids])
            self.auth_db_manager.remove_object(objid=objid, objtype=obj_type)

            # deregister event related to ApiObject
            # self.event_class(self.controller).deregister_object(objids)
            
            self.logger.debug('Deregister api object %s:%s %s - STOP' %
                              (self.objtype, self.objdef, objids))
        except (QueryError, TransactionError) as ex:
            self.logger.error('Deregister api object: %s - ERROR' % (ex.desc))
            raise ApiManagerError(ex.desc, code=400)       
        
        # deregister child classes
        objids.append('*')
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
                                    action='*')            
            
            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)
            
            # set child resources permissions
            for child in self.child_classes:
                res = child(self.controller, self)
                res.set_admin_permissions(role_name, self._get_value(
                            res.objdef, args).split('//'))            
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
                      objid+'//*',
                      objid+'//*//*',
                      objid+'//*//*//*',
                      objid+'//*//*//*//*',
                      objid+'//*//*//*//*//*',
                      objid+'//*//*//*//*//*//*']
            perms, total = self.auth_db_manager.get_deep_permissions(objids=objids, objtype=self.objtype, **kvargs)

            res = []
            for p in perms:
                res.append({
                    'id':p.id, 
                    'oid':p.obj.id, 
                    'subsystem':p.obj.type.objtype, 
                    'type':p.obj.type.objdef,
                    'objid':p.obj.objid, 
                    'aid':p.action.id, 
                    'action':p.action.value, 
                    'desc':p.obj.desc
                })

            self.logger.debug('Get permissions %s: %s' % (self.oid, truncate(res)))
            return res, total
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)         


class ApiViewResponse(ApiObject):
    objtype = 'api'
    objdef = 'Response'
    objdesc = 'Api Response'

    api_exclusions_list = [
        {'path': '/v1.0/server/ping', 'method': 'GET'},
    ]
    
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
            # self.event_class(self.controller).init_object()
            
            self.logger.debug('Register api object: %s' % objs)
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
                                    action='*')            
            
            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    def send_event(self, api, params={}, response=True, exception=None):
        """Publish an event to event queue.
        
        :param api: api to audit {'path':.., 'method':.., 'elapsed':..}
        :param params: operation params [default={}]
        :param response: operation response. [default=True]
        :param exception: exception raised [optional]
        """
        objid = '*'
        if exception is not None:
            response = (False, str(exception))
        else:
            response = [response]

        method = api['method']
        if method in ['GET']:
            action = 'view'
        elif method in ['POST']:
            action = 'insert'
        elif method in ['PUT']:
            action = 'update'
        elif method in ['PATCH']:
            action = 'patch'
        elif method in ['DELETE']:
            action = 'delete'
        # else:
        #    action = 'use'
        elapsed = api.pop('elapsed')

        # send event
        data = {
            'opid': operation.id,
            'op': api,
            'api_id': operation.id,
            'params': params,
            'elapsed': elapsed,
            'response': response
        }

        source = {
            'user': operation.user[0],
            'ip': operation.user[1],
            'identity': operation.user[2]
        }
        
        dest = {
            'ip': self.controller.module.api_manager.server_name,
            'port': self.controller.module.api_manager.http_socket,
            'objid': objid,
            'objtype': self.objtype,
            'objdef': self.objdef,
            'action': action
        }      
        
        # send event
        try:
            if api not in self.api_exclusions_list:
                client = self.controller.module.api_manager.event_producer
                client.send(self.API_OPERATION, data, source, dest)
        except Exception as ex:
            self.logger.warning('Event can not be published. Event producer is not configured - %s' % ex)


class ApiView(FlaskView):
    """ """
    prefix = 'identity:'
    expire = 3600
    parameters = []
    parameters_schema = None
    
    RESPONSE_MIME_TYPE = [
        'application/json', 
        'application/bson', 
        'text/xml',
        '*/*'
    ]
    
    def __init__(self, *argc, **argv):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
    
    def _get_response_mime_type(self):
        """ """
        try:
            self.response_mime = request.headers['Content-Type']
        except:
            self.response_mime = 'application/json'
        
        if self.response_mime == '*/*':
            self.response_mime = 'application/json'
            
        if self.response_mime == '':
            self.response_mime = 'application/json'

        if self.response_mime is None:
            self.response_mime = 'application/json'

        # self.logger.debug('Response mime type: %s' % self.response_mime)
    
    def __get_auth_filter(self):
        """Get authentication filter. It can be keyauth, oauth2, simplehttp or ...
        """
        headers = request.headers
        if 'uid' in headers and 'sign' in headers:
            return 'keyauth'
        if 'Authorization' in headers and \
           headers.get('Authorization').find('Basic') >= 0:
            return 'simplehttp'
        if 'Authorization' in headers and \
           headers.get('Authorization').find('Bearer') >= 0:
            return 'oauth2'
        return None
     
    def __get_token(self):
        """get uid and sign from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            uid = header['uid']
            sign = header['sign']
            data = request.path
            self.logger.debug2('Uid: %s' % uid)
            self.logger.debug2('Sign: %s' % sign)
            self.logger.debug2('Data: %s' % data)
        except:
            raise ApiManagerError('Error retrieving token and sign from http header', code=401)
        return uid, sign, data
    
    def __get_oauth2_token(self):
        """Get oauth2 access token from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            token = header['Authorization'].replace('Bearer ', '')
            self.logger.info('Get Bearer Token: %s' % token)
        except:
            raise ApiManagerError('Error retrieving bearer token', code=401)
        return token
    
    def __get_http_credentials(self):
        """Verify that simple http authentication contains valid fields and is 
        allowed for the user provided.
        
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            header = request.headers
            authorization = header['Authorization']
            self.logger.info('Authorization: %s' % authorization)
            
            # get credentials
            if not match('Basic [a-zA-z0-9]+', authorization):
                raise Exception('Authorization field syntax is wrong')
            authorization = authorization.lstrip('Basic ')
            self.logger.warn('Authorization: %s' % authorization)
            credentials = b64decode(authorization)
            user, pwd = credentials.split(':')
            user_ip = get_remote_ip(request)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError('Error retrieving Authorization from http header', code=401)
        return user, pwd, user_ip
    
    def get_current_identity(self):
        """Get uid and sign from headers
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.__get_token()
    
    def invalidate_user_session(self):
        """Remove user session from redis for api request
        """
        serializer = current_app.session_interface.serializer
        redis = current_app.session_interface.redis
        key_prefix = current_app.session_interface.key_prefix
        
        #self.logger.warn(session)
        self.logger.warn(redis.keys('%s*' % key_prefix))
        '''
        if session is not None:
            sid = session.sid
        if sid is not None:

            
            # save session not already in redis
            val = serializer.dumps(dict(session))
            redis.setex(name=key_prefix + sid, value=val, time=5)            
            
            #current_app.session_interface.save_session(current_app, request)
            
            

            #self.logger.warn(key_prefix + sid)
            #self.logger.warn(redis.get(key_prefix + sid))            
            #redis.expire(key_prefix + sid, 5)
            #redis.delete(key_prefix + sid)
            #self.logger.warn(redis.keys('%s*' % key_prefix))
            #session = None

            #redis.delete(key_prefix + sid)'''
            
        #session = None
        self.logger.warn(session)
        session['_permanent'] = False
        self.logger.warn(session)
        self.logger.debug('Invalidate user session')

    def authorize_request(self, module):
        """Authorize http request
        
        :param module: beehive module instance
        :raise AuthViewError:
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.logger.debug('Verify api %s [%s] authorization' % (request.path, request.method))

        # select correct authentication filter
        authfilter = self.__get_auth_filter()
        operation.token_type = authfilter
        self.logger.debug('Select authentication filter: "%s"' % authfilter)
        
        # get controller
        controller = module.get_controller()
        
        # - keyauth
        if authfilter == 'keyauth':
            # get identity and verify signature
            uid, sign, data = self.__get_token()
            identity = controller.verify_request_signature(uid, sign, data)
        
        # - oauth2
        elif authfilter == 'oauth2':
            uid = self.__get_oauth2_token()
            # get identity
            identity = controller.get_oauth2_identity(uid)
            if identity['type'] != 'oauth2':
                msg = 'Token type oauth2 does not match with supplied token'
                self.logger.error(msg, exc_info=1)
                raise ApiManagerError(msg, code=401)  

        # - simple http authentication
        elif authfilter == 'simplehttp':
            user, pwd, user_ip = self.__get_http_credentials()
            identity = controller.verify_simple_http_credentials(user, pwd, user_ip)
            uid = None
            identity['seckey'] = None
            identity['ip'] = user_ip

        # - no authentication
        elif authfilter is None:
            msg = 'Request is not authorized'
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)

        # get user permissions from identity
        name = 'Guest'
        try:
            # get user permission
            user = identity['user']
            name = user['name']
            # name = user['id']
            compress_perms = user['perms']
            
            # get permissions
            operation.perms = json.loads(decompress(binascii.a2b_base64(compress_perms)))
            operation.user = (name, identity['ip'], uid, identity.get('seckey', None))
            self.logger.debug2('Get user %s permissions: %s' % (name, truncate(operation.perms)))
        except Exception as ex:
            msg = 'Error retrieving user %s permissions: %s' % (name, ex)
            self.logger.error(msg, exc_info=1)
            raise ApiManagerError(msg, code=401)
        
    # response methods
    def get_warning(self, exception, code, msg, module=None):
        return self.get_error(exception, code, msg, module=module)

    # response methods
    def get_error(self, exception, code, msg, module=None):
        """Return error response

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        headers = {'Cache-Control': 'no-store', 'Pragma': 'no-cache',
                   'remote-server': module.api_manager.server_name}
        
        error = {
            'code': code,
            'message': '%s' %msg,
            'description': '%s - %s' % (exception, msg)
        }
        self.logger.error('Api response: %s' % error)
        
        if self.response_mime is None or self.response_mime == '*/*' or self.response_mime == '':
            self.response_mime = 'application/json'
            
        if code in [400, 401, 403, 404, 405, 406, 408, 409, 415, 500]:
            status = code
        else:
            status = 400
        
        self.logger.error('Code: %s, Error: %s' % (code, exception), 
                          exc_info=True)
        if self.response_mime == 'application/json':
            return Response(response=json.dumps(error), 
                            mimetype='application/json', 
                            status=status,
                            headers=headers)
        elif self.response_mime == 'application/bson':
            return Response(response=json.dumps(error), 
                            mimetype='application/bson', 
                            status=status,
                            headers=headers)
        elif self.response_mime in ['text/xml', 'application/xml']:
            xml = dicttoxml(error, root=False, attr_type=False)
            return Response(response=xml, 
                            mimetype='application/xml', 
                            status=status,
                            headers=headers)
        else:  
            # 415 Unsupported Media Type
            res = {'msg': 'Unsupported media type'}
            return Response(response=res,
                            mimetype='application/xml',
                            status=415,
                            headers=headers)           

    def get_response(self, response, code=200, headers={}, module=None):
        """Return response

        **raise** :class:`ApiManagerError`
        """
        headers.update({'Cache-Control': 'no-store', 'Pragma': 'no-cache',
                        'remote-server': module.api_manager.server_name})

        try:
            if response is None:
                return Response(response='', mimetype='text/plain', status=code)

            self.logger.debug('Api response mime type: %s' % self.response_mime)
            
            # redirect to new uri
            if code in [301, 302, 303, 305, 307]:
                self.logger.debug('Api response: %s' % truncate(response))                
                return response
            
            # render template
            elif self.response_mime.find('text/html') >= 0:
                self.logger.debug('Api response: %s' % truncate(response))                
                return response
            
            # return original response
            elif isinstance(response, Response):
                self.logger.debug('Api response: %s' % truncate(response))
                return response
            
            # render json
            elif self.response_mime == 'application/json':
                resp = json.dumps(response)
                self.logger.debug('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/json', status=code, headers=headers)
            
            # render Bson
            elif self.response_mime == 'application/bson':
                resp = json.dumps(response)
                self.logger.debug('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/bson', status=code, headers=headers)

            # render xml
            elif self.response_mime in ['text/xml', 'application/xml']:
                resp = dicttoxml(response, root=False, attr_type=False)
                self.logger.debug('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/xml', status=code, headers=headers)
                
            # 415 Unsupported Media Type
            else:
                self.logger.debug('Api response: ')
                return Response(response='', mimetype='text/plain', status=code, headers=headers)
        except Exception as ex:
            msg = 'Error creating response - %s' % ex
            self.logger.error(msg)
            raise ApiManagerError(msg, code=400)
    
    def format_paginated_response(self, response, entity, total, page=None, field='id', order='DESC', **kvargs):
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
            entity: response,
            'count': len(response),
            'page': page,
            'total': total,
            'sort': {
                'field': field,
                'order': order
            }
        }
        
        return resp
    
    def dispatch(self, controller, data, *args, **kwargs):
        """http inner function. Override to implement apis.
        """
        raise NotImplementedError()

    def to_dict(self, querystring):
        res = {}
        for k, v in querystring.items(multi=True):
            if k[-2:] == '.N':
                try:
                    res[k].append(v)
                except:
                    res[k] = [v]
            else:
                res[k] = v
        return res

    def dispatch_request(self, module=None, secure=True, *args, **kwargs):
        """Base dispatch_request method. Extend this method in your child class.
        """
        # set reqeust timeout
        res = None
        
        timeout = gevent.Timeout(module.api_manager.api_timeout)
        timeout.start()
        self.logger.debug2('Set response timeout to: %s' % module.api_manager.api_timeout)

        start = time.time()
        dbsession = None
        data = None

        # open database session.
        dbsession = module.get_session()
        controller = module.get_controller()

        try:
            headers = ['%s: %s' % (k, v) for k, v in request.headers.items()]
            
            # set operation
            operation.user = ('guest', 'localhost', None)
            operation.id = request.headers.get('request-id', str(uuid4()))
            operation.transaction = None
            operation.authorize = True
            operation.cache = True
            operation.encryption_key = module.api_manager.app_fernet_key

            self.logger.info('Start new operation: %s' % operation.id)
            
            self.logger.info('Invoke api: %s [%s] - START' % (request.path, request.method))

            query_string = self.to_dict(request.args)

            # get chunked input data
            if request.headers.get('Transfer-Encoding', '') == 'chunked':
                request_data = uwsgi_util.chunked_read(5)
            else:
                request_data = request.data

            self._get_response_mime_type()
            
            # # open database session.
            # dbsession = module.get_session()
            # controller = module.get_controller()
            
            # check security
            if secure is True:
                self.authorize_request(module)
            
            # get request data
            try:
                data = request_data 
                data = json.loads(data)
            except (AttributeError, ValueError): 
                data = request.values.to_dict()

            self.logger.debug('Api request headers: %s' % headers)
                
            # validate query/input data
            if self.parameters_schema is not None:
                if request.method.lower() == 'get':
                    # parsed = self.parameters_schema().load(request.args.to_dict())
                    query_string.update(kwargs)
                    parsed = self.parameters_schema().load(query_string)
                    self.logger.debug('Api request data: %s' % truncate(obscure_data(deepcopy(query_string))))
                else:
                    data.update(kwargs)
                    parsed = self.parameters_schema().load(data)
                    self.logger.debug('Api request data: %s' % truncate(obscure_data(deepcopy(data))))

                if len(parsed.errors.keys()) > 0:
                    self.logger.error(parsed.errors)
                    raise ApiManagerError(parsed.errors, code=400)
                data = parsed.data
                self.logger.debug('Api request data after validation: %s' % truncate(obscure_data(deepcopy(data))))
            else:
                self.logger.debug('Api request data: %s' % truncate(obscure_data(deepcopy(data))))

            # dispatch request
            meth = getattr(self, request.method.lower(), None)
            if meth is None:
                meth = self.dispatch
            resp = meth(controller, data, *args, **kwargs)
            
            if isinstance(resp, tuple):
                if len(resp) == 3:
                    res = self.get_response(resp[0], code=resp[1], headers=resp[2], module=module)
                else:
                    res = self.get_response(resp[0], code=resp[1], module=module)
            else:
                res = self.get_response(resp, module=module)
            
            # unset user permisssions in local thread object
            operation.perms = None
            
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.info('Invoke api: %s [%s] - STOP - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed}
            ApiViewResponse(controller).send_event(event_data, data)
        except gevent.Timeout:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            msg = 'Request %s %s timeout' % (request.path, request.method)
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': 408}
            ApiViewResponse(controller).send_event(event_data, data, exception=msg)
            return self.get_error('Timeout', 408, msg, module=module)
        except ApiManagerError as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': ex.code}
            ApiViewResponse(controller).send_event(event_data, data, exception=ex.value)
            return self.get_error('ApiManagerError', ex.code, ex.value, module=module)
        except ApiManagerWarning as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.warning('Invoke api: %s [%s] - Warning - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': ex.code}
            ApiViewResponse(controller).send_event(event_data, data, exception=ex.value)
            return self.get_warning('ApiManagerWarning', ex.code, ex.value, module=module)
        except Exception as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': 400}
            ApiViewResponse(controller).send_event(event_data, data, exception=ex.message)
            return self.get_error('Exception', 400, ex.message, module=module)
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
        :param rules: route to register. Ex. [('/jobs', 'GET', ListJobs.as_view('jobs')), {'secure':False}]
        """
        logger = logging.getLogger(__name__)
        
        # get version
        if version is None:
            version = module.get_controller().version
        
        # get app
        app = module.api_manager.app
        
        # get swagger
        # swagger = module.api_manager.swagger
        
        # regiter routes
        view_num = 0
        for rule in rules:
            uri = '/%s/%s' % (version, rule[0])
            defaults = {'module': module}
            defaults.update(rule[3])
            view_name = '%s-%s' % (get_class_name(rule[2]), view_num)
            view_func = rule[2].as_view(view_name)

            # setup flask route
            app.add_url_rule(uri, methods=[rule[1]], view_func=view_func, defaults=defaults)
            
            view_num += 1
            logger.debug2('Add route: %s %s' % (uri, rule[1]))
            
            # append route to module
            module.api_routes.append({'uri': uri, 'method': rule[1]})


class PaginatedRequestQuerySchema(Schema):
    size = fields.Integer(default=10, example=10, missing=10, context='query',
                          description='enitities list page size',
                          validate=Range(min=-1, max=10000, error='Size is out from range'))
    page = fields.Integer(default=0, example=0, missing=0, context='query',
                          description='enitities list page selected',
                          validate=Range(min=0, max=10000, error='Page is out from range'))
    order = fields.String(validate=OneOf(['ASC', 'asc', 'DESC', 'desc'],
                                         error='Order can be asc, ASC, desc, DESC'),
                          description='enitities list order: ASC or DESC',
                          default='DESC', example='DESC', missing='DESC', context='query')
    field = fields.String(validate=OneOf(['id', 'uuid', 'objid', 'name'],
                                         error='Field can be id, uuid, objid, name'),
                          description='enitities list order field. Ex. id, uuid, name',
                          default='id', example='id', missing='id', context='query')


class GetApiObjectRequestSchema(Schema):
    oid = fields.String(required=True, description='id, uuid or name', context='path')


class ApiObjectRequestFiltersSchema(Schema):
    filter_expired = fields.Boolean(required=False, context='query', missing=False)
    filter_creation_date_start = fields.DateTime(required=False, context='query')
    filter_creation_date_stop = fields.DateTime(required=False, context='query')
    filter_modification_date_start = fields.DateTime(required=False, context='query')
    filter_modification_date_stop = fields.DateTime(required=False, context='query')
    filter_expiry_date_start = fields.DateTime(required=False, context='query')
    filter_expiry_date_stop = fields.DateTime(required=False, context='query')


class ApiObjectPermsRequestSchema(PaginatedRequestQuerySchema, GetApiObjectRequestSchema):
    pass   


class ApiObjectResponseDateSchema(Schema):
    creation = fields.DateTime(required=True, default='1990-12-31T23:59:59Z', example='1990-12-31T23:59:59Z')
    modified = fields.DateTime(required=True, default='1990-12-31T23:59:59Z', example='1990-12-31T23:59:59Z')
    expiry = fields.String(default='')


class ApiObjecCountResponseSchema(Schema):
    count = fields.Integer(required=True, default=10)


class ApiObjectMetadataResponseSchema(Schema):
    objid = fields.String(required=True, default='396587362//3328462822', example='396587362//3328462822')
    type = fields.String(required=True, default='auth', example='auth')
    definition = fields.String(required=True, default='Role', example='Role')
    uri = fields.String(required=True, default='/v1.0/auht/roles', example='/v1.0/auht/roles')


class ApiObjectSmallResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(required=True, default='4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example='4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, default='test', example='test')
    active = fields.Boolean(required=True, default=True, example=True)
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)


class AuditResponseSchema(Schema):
    date = fields.Nested(ApiObjectResponseDateSchema, required=True)


class ApiObjectResponseSchema(AuditResponseSchema):
    id = fields.Integer(required=True, default=10, example=10)
    uuid = fields.String(required=True,  default='4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example='4cdf0ea4-159a-45aa-96f2-708e461130e1')
    name = fields.String(required=True, default='test', example='test')
    desc = fields.String(required=True, default='test', example='test')
    active = fields.Boolean(required=True, default=True, example=True)
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)


class PaginatedResponseSortSchema(Schema):
    order = fields.String(required=True, validate=OneOf(['ASC', 'asc', 'DESC', 'desc']),
                          default='DESC', example='DESC')
    field = fields.String(required=True, default='id', example='id')


class PaginatedResponseSchema(Schema):
    count = fields.Integer(required=True, default=10, example=10)
    page = fields.Integer(required=True, default=0, example=0)
    total = fields.Integer(required=True, default=20, example=20)
    sort = fields.Nested(PaginatedResponseSortSchema, required=True)


class CrudApiObjectSimpleResponseSchema(Schema):
    res = fields.Boolean(required=True,  default=True, example=True)


class CrudApiObjectResponseSchema(Schema):
    uuid = fields.UUID(required=True,  default='6d960236-d280-46d2-817d-f3ce8f0aeff7',
                       example='6d960236-d280-46d2-817d-f3ce8f0aeff7')


class CrudApiJobResponseSchema(Schema):
    jobid = fields.UUID(default='db078b20-19c6-4f0e-909c-94745de667d4', example='6d960236-d280-46d2-817d-f3ce8f0aeff7',
                        required=True)


class CrudApiObjectJobResponseSchema(CrudApiObjectResponseSchema, CrudApiJobResponseSchema):
    pass    


class ApiGraphResponseSchema(Schema):
    directed = fields.Boolean(required=True, example=True, description='if True graph is directed')
    graph = fields.Dict(required=True, example={'name': 'vShield V...'}, description='if TRue graph is directed')
    links = fields.List(fields.Dict(example={'source': 2, 'target': 7}), required=True, example=True,
                        description='links list')
    multigraph = fields.Boolean(required=True, example=False, description='if True graph is multigraph')
    nodes = fields.List(fields.Dict(example={}), required=True, example=True, description='nodes list')


class ApiObjectPermsParamsResponseSchema(Schema):
    id = fields.Integer(required=True, default=1, example=1)
    oid = fields.Integer(required=True, default=1, example=1)
    objid = fields.String(required=True, default='396587362//3328462822', example='396587362//3328462822')
    type = fields.String(required=True, default='Objects', example='Objects')
    subsystem = fields.String(required=True, default='auth', example='auth')
    desc = fields.String(required=True, default='beehive', example='beehive')
    aid = fields.Integer(required=True, default=1, example=1)
    action = fields.String(required=True, default='view', example='view')


class ApiObjectPermsResponseSchema(PaginatedResponseSchema):
    perms = fields.Nested(ApiObjectPermsParamsResponseSchema, many=True, required=True, allow_none=True)


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
        'default': {'$ref': '#/responses/DefaultError'},
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
    def __init__(self, auth_endpoints, user, pwd, secret, catalog_id=None, authtype='keyauth'):
        BeehiveApiClient.__init__(self, auth_endpoints, authtype, user, pwd, secret, catalog_id)
    
    def admin_request(self, subsystem, path, method, data='', other_headers={}, silent=False):
        """Make api request using module internal admin user credentials.

        :param subsystem:
        :param path:
        :param method:
        :param data:
        :param other_headers:
        :param silent:
        :return:
        :raise: :class:`ApiManagerError`
        """
        # propagate opernation.id to internal api call
        if isinstance(other_headers, dict):
            other_headers['request-id'] = operation.id
        else:
            other_headers = {'request-id': operation.id}

        try:
            if self.exist(self.uid) is False:
                self.create_token()
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
        
        try:
            res = self.send_request(subsystem, path, method, data, self.uid, self.seckey, other_headers, silent=silent)
            self.logger.debug('Send admin request to %s using uid %s' % (path, self.uid))
        except BeehiveApiClientError as ex:
            self.logger.error('Send admin request to %s using uid %s: %s' % (path, self.uid, ex.value), exc_info=1)
            raise ApiManagerError(ex.value, code=ex.code)

        return res

    def user_request(self, subsystem, path, method, data='', other_headers={}, silent=False):
        """Make api request using module current user credentials.
        
        :raise ApiManagerError:
        """
        # propagate opernation.id to internal api call
        if isinstance(other_headers, dict):
            other_headers['request-id'] = operation.id
        else:
            other_headers = {'request-id': operation.id}

        try:
            # get user logged uid and password
            uid = operation.user[2]
            seckey = operation.user[3]
            res = self.send_request(subsystem, path, method, data, uid, seckey, other_headers, silent=silent,
                                    api_authtype=operation.token_type)
            self.logger.debug('Send user request to %s using uid %s' % (path, self.uid))
        except BeehiveApiClientError as ex:
            self.logger.error('Send user request to %s using uid %s: %s' % (path, self.uid, ex.value), exc_info=1)
            raise

        return res
