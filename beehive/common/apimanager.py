# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from modulefinder import Module
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
from datetime import datetime
from flask import request, Response, session
from flask.views import MethodView as FlaskView
from flask_session import Session
from flask import current_app
from six import ensure_text
from beecell.cache.client import CacheClient
from beecell.db import TransactionError, QueryError
from beecell.db.manager import MysqlManager, SqlManagerError, RedisManager
from beecell.auth import extract
from beecell.db.manager import parse_redis_uri
from beecell.password import obscure_data
from beecell.file import read_file
from beecell.types.type_class import get_class_methods_by_decorator
from beecell.types.type_string import truncate, str2bool
from beecell.types.type_date import format_date
from beecell.types.type_dict import dict_get
from beecell.simple import import_class, get_class_name, get_remote_ip, dynamic_import
from beecell.sendmail import Mailer
from beehive.common.data import operation, trace
from beecell.auth import DatabaseAuth, LdapAuth, SystemUser
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
from beehive.common.model.config import ConfigDbManager
from beehive.common.model.authorization import AuthDbManager, Role
# from dicttoxml import dicttoxml
from dict2xml import dict2xml
from beecell.simple import jsonDumps
try:
    from beehive.common.event import EventProducerKombu
except:
    pass
try:
    from beecell.server.uwsgi_server.wrapper import uwsgi_util
except:
    pass
from copy import deepcopy
from flask_session.sessions import RedisSessionInterface
from beehive.common.data import encrypt_data, decrypt_data
from elasticsearch import Elasticsearch
from flasgger import Swagger, SwaggerView
from marshmallow import fields, Schema, ValidationError
from marshmallow.validate import OneOf, Range
from beecell.db.manager import RedisManager
from typing import List, Type, Tuple, Any, Union, Dict, Callable

logger = logging.getLogger(__name__)

class ApiMethod(object):
    objtype = 'ApiMethod'
    objdef = 'ApiMethod'
    objdesc = 'Api Method'

class RedisSessionInterface2(RedisSessionInterface):
    def __init__(self, redis, key_prefix, use_signer=False, permanent=True):
        RedisSessionInterface.__init__(self, redis, key_prefix, use_signer, permanent)

    def save_session(self, app, session, response):
        if response.mimetype in ['text/html']:
            RedisSessionInterface.save_session(self, app, session, response)

        # if response.mimetype not in ['text/html']:
        #     self.redis.delete(self.key_prefix + session.sid)
        #     logger.debug2('Delete user session. This is an Api request')
        if session.get('_invalidate', False) is not False:
            self.redis.delete(self.key_prefix + session.sid)
            logger.debug2('Delete user session. This is an Api request')


class ApiManagerWarning(Exception):
    """Main excpetion raised by api manager and childs

    :param value: error description
    :param code: error code [default=400]
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

    :param value: error description
    :param code: error code [default=400]
    """
    def __init__(self, value, code=400):
        self.code = code
        self.value = str(value)
        Exception.__init__(self, self.value, code)

    def __repr__(self):
        return 'ApiManagerError: %s' % self.value

    def __str__(self):
        return '%s' % self.value


class ApiManager(object):
    """Api Manager

    :param params: configuration params
    :param app: flask app reference
    :param hostname: server hostname
    """
    def __init__(self, params, app=None, hostname=None):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

        # configuration params
        self.params = params

        # flask app reference
        self.app = app
        self.app_name = ensure_text(self.params['api_name'])
        self.app_id = ensure_text(self.params['api_id'])
        self.app_env = ensure_text(self.params['api_env'])
        self.app_desc = ensure_text(self.params['api_id'])
        self.app_subsytem = ensure_text(self.params['api_subsystem'])
        self.app_fernet_key = self.params.get('api_fernet_key', None)
        if self.app_fernet_key is not None:
            self.app_fernet_key = ensure_text(self.app_fernet_key)
        self.app_endpoint_id = '%s-%s' % (ensure_text(self.params['api_id']), hostname)
        self.swagger_spec_path = ensure_text(self.params.get('api_swagger_spec_path', 'swagger.yml'))
        self.app_k8s_pod = ensure_text(self.params.get('api_k8s_pod', ''))

        try:
            self.app_uri = 'http://%s%s' % (hostname, ensure_text(self.params['http-socket']))
            self.uwsgi_uri = 'uwsgi://%s%s' % (hostname, ensure_text(self.params['socket']))
        except:
            self.app_uri = None
            self.uwsgi_uri = None

        self.cluster_ip = self.params.get('api_cluster_ip', None)
        self.cluster_app_uri = self.app_uri
        if self.cluster_ip is not None:
            self.cluster_ip = ensure_text(self.cluster_ip)
            self.cluster_app_uri = 'http://%s%s' % (self.cluster_ip, ensure_text(self.params['http-socket']))
            self.app_endpoint_id = '%s-%s' % (ensure_text(self.params['api_id']), self.app_env)

        # set syslog server
        syslog = self.params.get('syslog_server', None)
        self.syslog_server = None
        if syslog is not None:
            self.syslog_server = ensure_text(syslog)

        # get pod
        pod = self.params.get('api_pod', None)
        self.pod = None
        if pod is not None:
            self.pod = ensure_text(pod)

        # set encryption key
        operation.encryption_key = self.app_fernet_key

        # swagger reference
        try:
            swagger_template = read_file(self.swagger_spec_path)
            self.swagger = Swagger(self.app, template=swagger_template)
        except FileNotFoundError:
            self.logger.warning('file %s not found' % self.swagger_spec_path)
            self.swagger = None
        except:
            self.logger.warning('', exc_info=True)
            self.swagger = None

        # instance configuration
        self.http_socket = self.params.get('http-socket', None)
        if self.http_socket is not None:
            self.http_socket = ensure_text(self.http_socket)
        self.server_name = hostname

        # modules
        self.modules = {}
        self.main_module = None

        # redis
        self.redis_manager: RedisManager = None
        self.redis_identity_manager: RedisManager = None

        # cache
        self.cache_manager = None
        self.cache_manager_ttl = 86400

        # security
        self.auth_providers = {}
        self.auth_user = {}
        self.api_oauth2_client = None
        self.authentication_manager = None

        # job manager
        self.job_manager = None
        self.max_concurrent_jobs = 2
        self.job_interval = 1.0
        self.job_timeout = 1200

        # task manager
        self.task_manager = None
        self.task_scheduler = None

        # event producer
        self.event_producer = None

        # api listener
        self.api_timeout = float(self.params.get('api_timeout', 10.0))

        # api endpoints
        self.endpoints = []
        self.api_user = None
        self.api_user_pwd = None
        self.api_client: ApiClient= None
        # self.awx_client = None

        # gateways
        # self.gateways = {}

        # elasticsearch
        self.elasticsearch = None

        # logstash
        self.logstash = None

        # database manager
        self.db_manager = None
        if self.params.get('database_uri', None) is not None:
            database_uri = ensure_text(self.params.get('database_uri', ''))
            self.create_pool_engine((database_uri, 5, 10, 10, 1800))

        # send mail
        self.mailer = None
        self.mail_sender = None

        # identity
        self.prefix = 'identity:'
        self.prefix_index = 'identity:index:'
        self.expire = 3600

        # scheduler
        self.redis_taskmanager: RedisManager = None
        self.redis_scheduler: RedisManager = None

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

        # oauth2 endpoint
        self.oauth2_endpoint = None

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
            self.db_manager = MysqlManager('db_manager01', db_uri, connect_timeout=connect_timeout)
            self.db_manager.create_pool_engine(pool_size=pool_size, max_overflow=max_overflow,
                                               pool_recycle=pool_recycle)
            self.logger.debug('setup db manager on uri %s: %s ' % (db_uri, self.db_manager))
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
            self.db_manager = MysqlManager('db_manager01', db_uri, connect_timeout=connect_timeout)
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

    def flush_session(self):
        """Flush db session"""
        try:
            if operation.session is not None:
                operation.session.flush()
        except SqlManagerError as e:
            raise ApiManagerError(e)

    def release_session(self):
        """Release db session"""
        try:
            if operation.session is not None:
                self.db_manager.release_session(operation.session)
                operation.session = None
        except SqlManagerError as e:
            raise ApiManagerError(e)

    def get_identity(self, uid):
        """Get identity

        :param uid: identity id
        :return: {'uid':..., 'user':..., timestamp':..., 'pubkey':..., 'seckey':...}
        """
        identity = self.redis_identity_manager.conn.get(self.prefix + uid)
        if identity is not None:
            data = pickle.loads(identity)
            data['ttl'] = self.redis_identity_manager.conn.ttl(self.prefix + uid)
            self.logger.debug('Get identity %s from redis' % (uid))
            return data
        else:
            self.logger.error("Identity %s doesn't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doesn't exist or is expired" % uid, code=401)

    def get_identities(self):
        """Get identities

        :return: [{'uid':..., 'user':..., timestamp':..., 'pubkey':..., 'seckey':...}, ..]
        """
        try:
            res = []
            for key in self.redis_identity_manager.conn.keys(self.prefix+'*'):
                identity = self.redis_identity_manager.conn.get(key)
                data = pickle.loads(identity)
                ttl = self.redis_identity_manager.conn.ttl(key)
                res.append({'uid': data['uid'], 'user': data['user']['name'], 'timestamp': data['timestamp'],
                            'ttl': ttl, 'ip': data['ip']})
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
        :return: {'uid':..., 'user':..., timestamp':..., 'pubkey':..., 'seckey':...}
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            identity = self.api_client.simplehttp_login(user, pwd, user_ip)
        except BeehiveApiClientError as ex:
            self.logger.error(ex.value, exc_info=True)
            raise ApiManagerError(ex.value, code=ex.code)

        return identity

    def get_oauth2_identity(self, token):
        """Get identity that correspond to oauth2 access token

        :param token: identity id
        :return: {'uid':..., 'user':..., timestamp':..., 'pubkey':..., 'seckey':...}
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        identity = self.get_identity(token)
        self.redis_identity_manager.conn.expire(self.prefix + token, self.expire)
        self.logger.debug('Extend identity %s expire' % token)
        return identity

    def verify_request_signature(self, uid, sign, data):
        """Verify Request signature.

        :param uid: identity id
        :param sign: request sign
        :param data: request data
        :return: {'uid':..., 'user':..., timestamp':..., 'pubkey':..., 'seckey':...}
        :raises ApiManagerError: raise :class:`ApiManagerError`
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
            hash_data = SHA256.new()
            hash_data.update(bytes(data, encoding='utf-8'))

            # verify sign
            verifier = PKCS1_v1_5.new(key)
            res = verifier.verify(hash_data, signature)
        except:
            self.logger.error('Data signature for identity %s is not valid' % uid)
            raise ApiManagerError('Data signature for identity %s is not valid' % uid, code=401)

        # extend expire time of the redis key
        if res is True:
            self.redis_identity_manager.conn.expire(self.prefix + uid, self.expire)
            self.redis_identity_manager.conn.expire(self.prefix_index + dict_get(identity, 'user.id'), self.expire)
            self.logger.debug('Data signature %s for identity %s is valid. Extend expire.' % (sign, uid))
        else:
            self.logger.error('Data signature for identity %s is not valid' % uid)
            raise ApiManagerError('Data signature for identity %s is not valid' % uid, code=401)


        return identity

    def register_modules(self, register_api=True, register_task=False):
        """Register ApiModule

        :param register_api: if True register api module
        :param register_task: if True register async method as Celery task
        """
        self.logger.info('Configure modules - START')

        is_list = isinstance(self.params['api_module'], list)

        if is_list:
            module_classes_num = len(self.params['api_module'])
            start_idx = 0
        else:
            module_classes_num = int(self.params['api_module'])+1
            start_idx = 1

        for i in range(start_idx, module_classes_num):
            if is_list:
                item = self.params['api_module'][i]
            else:
                item = ensure_text(self.params['api_module.%s' % i])

            # check if module is primary
            main = False
            ## TODO remove debugging loggin
            self.logger.info(f'PARSING module: {item} ' )
            if item.find(',') > 0:
                item, main = item.split(',')
                main = str2bool(main)
            # import module class
            ## TODO remove debugging loggin
            self.logger.info(f'Registering module: {item}  is main {main}' )
            module_class = import_class(item)
            # instance module class
            module = module_class(self)
            # set main module
            if main is True:
                self.main_module = module
            self.logger.info('Register module: %s' % item)

        if 'api_plugin' in self.params:
            is_list = isinstance(self.params['api_plugin'], list)

            if is_list:
                api_plugin_num = len(self.params['api_plugin'])
                start_idx = 0
            else:
                api_plugin_num = int(self.params['api_plugin']) + 1
                start_idx = 1

            plugin_pkgs = []
            for i in range(start_idx, api_plugin_num):
                if is_list:
                    plugin_pkgs.append(ensure_text(self.params['api_plugin'][i]))
                else:
                    plugin_pkgs.append(ensure_text(self.params['api_plugin.%s' % i]))

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
            self.logger.info(" registering Api")

            for module in self.modules.values():
                # register module api
                self.logger.warning(f"module ; {module}")

                module.register_api()
        else:
            self.logger.info("not registering Api")

        # register async methods
        if register_task is True:
            for module in self.modules.values():
                # register module api
                module.register_task()

        self.logger.info('Configure modules - STOP')

    def list_modules(self):
        """Return list of configured modules

        :param name: module name
        :return: ApiModule instance
        """
        return self.modules

    def get_module(self, name):
        """Return module by name

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

                #
                # oauth2 configuration
                #
                self.logger.info('Configure oauth2 - CONFIGURE')
                try:
                    self.oauth2_endpoint = ensure_text(self.params.get('oauth2_endpoint'))
                    self.logger.info('Setup oauth2 endpoint: %s' % self.oauth2_endpoint)
                    self.logger.info('Configure oauth2 - CONFIGURED')
                except:
                    self.logger.warning('Configure oauth2 - NOT CONFIGURED')

                #
                # identity redis configuration
                #
                self.logger.info('Configure identity redis - CONFIGURE')
                # connect to redis
                redis_identity_uri = self.params.get('redis_identity_uri', None)
                if redis_identity_uri is not None:
                    redis_identity_uri = ensure_text(redis_identity_uri)

                    # parse redis uri
                    parsed_uri = parse_redis_uri(redis_identity_uri)

                    # set redis manager
                    self.redis_identity_manager = None
                    if parsed_uri['type'] == 'single':
                        self.redis_identity_manager = RedisManager(
                            redis_identity_uri,
                            timeout=5,
                            max_connections=200)
                        # self.redis_identity_manager = redis.StrictRedis(
                        #     host=parsed_uri['host'],
                        #     port=parsed_uri['port'],
                        #     password=parsed_uri.get('pwd', None),
                        #     db=parsed_uri['db'],
                        #     socket_timeout=5,
                        #     socket_connect_timeout=5)
                    elif parsed_uri['type'] == 'sentinel':
                        port = parsed_uri['port']
                        pwd = parsed_uri['pwd']
                        self.redis_identity_manager = RedisManager(
                            None,
                            timeout=5,
                            max_connections=200,
                            sentinels=[(host, port) for host in parsed_uri['hosts']],
                            sentinel_name=parsed_uri['group'],
                            sentinel_pwd=pwd,
                            db=0,
                            pwd=pwd) #.conn

                    # app session
                    if self.app is not None:
                        self.app.config.update(
                            SESSION_COOKIE_NAME='auth-session',
                            SESSION_COOKIE_SECURE=True,
                            PERMANENT_SESSION_LIFETIME=3600,
                            SESSION_TYPE='redis',
                            SESSION_USE_SIGNER=True,
                            SESSION_KEY_PREFIX='session:',
                            SESSION_REDIS=self.redis_identity_manager.conn
                        )
                        Session(self.app)
                        i = self.app.session_interface
                        self.app.session_interface = RedisSessionInterface2(
                            i.redis, i.key_prefix, i.use_signer, i.permanent)
                        self.logger.info('Setup redis session manager: %s' % self.app.session_interface)

                    self.logger.info('Configure identity redis - CONFIGURED')
                else:
                    self.logger.warning('Configure identity redis - NOT CONFIGURED')

                #
                # redis configuration
                #
                self.logger.info('Configure redis - CONFIGURE')
                # connect to redis
                redis_uri = self.params.get('redis_uri', None)
                if redis_uri is not None:
                    redis_uri = ensure_text(redis_uri)

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

                    self.logger.info('Configure redis - CONFIGURED')
                else:
                    self.logger.warning('Configure redis - NOT CONFIGURED', exc_info=True)

                #
                # cache configuration
                #
                self.logger.info('Configure cache - CONFIGURE')

                if self.redis_manager is not None:
                    self.cache_manager = CacheClient(self.redis_manager)
                    self.logger.debug(self.cache_manager)

                    self.logger.info('Configure cache - CONFIGURED')
                else:
                    self.logger.warning('Configure cache - NOT CONFIGURED')

                #
                # scheduler reference configuration
                #
                self.logger.info('Configure scheduler reference - CONFIGURE')

                try:
                    from beehive.common.task_v2.manager import configure_task_manager
                    from beehive.common.task_v2.manager import configure_task_scheduler

                    broker_url = self.params.get('broker_url', None)
                    result_backend = self.params.get('result_backend', None)
                    if broker_url is not None and result_backend is not None:
                        # task manager
                        broker_url = ensure_text(broker_url)
                        result_backend = ensure_text(result_backend)
                        internal_result_backend = ensure_text(self.params['redis_celery_uri'])
                        task_manager = configure_task_manager(broker_url, result_backend,
                                                              task_queue=self.params['broker_queue'])
                        task_manager.api_manager = self
                        self.celery_broker_queue = ensure_text(self.params['broker_queue'])
                        self.redis_taskmanager = RedisManager(internal_result_backend)
                        self.task_manager = task_manager

                        # scheduler
                        broker_url = ensure_text(broker_url)
                        schedule_backend = ensure_text(result_backend)
                        task_scheduler = configure_task_scheduler(broker_url, schedule_backend,
                                                                  task_queue=self.params['broker_queue'])
                        self.redis_scheduler = RedisManager(schedule_backend)
                        self.task_scheduler = task_scheduler
                    else:
                        self.logger.warning('Configure scheduler reference - NOT CONFIGURED')

                    self.logger.info('Configure scheduler reference - CONFIGURED')
                except:
                    self.logger.warning('Configure scheduler reference - NOT CONFIGURED', exc_info=True)

                #
                # identity provider configuration - configure only with auth module
                #
                try:
                    identity_provider = self.params.get('identity_provider', None)

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
                                auth_provider = LdapAuth(item['host'], SystemUser, timeout=int(item['timeout']),
                                                         ssl=item['ssl'], dn=item['dn'],
                                                         search_filter=item['search_filter'],
                                                         search_id=item['search_id'],
                                                         bind_user=item['bind_user'], bind_pwd=bind_pwd)
                            self.auth_providers[item['provider']] = auth_provider
                            self.logger.info('Setup authentication provider: %s' % auth_provider)

                        self.logger.info('Configure security - CONFIGURED')
                    elif identity_provider is not None:
                        identity_provider_num = int(self.params['identity_provider']) + 1
                        start_idx = 1

                        for i in range(start_idx, identity_provider_num):
                            auth_provider = None
                            item_type = ensure_text(self.params['identity_provider.%s.type' % i])
                            item_host = ensure_text(self.params['identity_provider.%s.host' % i])
                            item_provider = ensure_text(self.params['identity_provider.%s.provider' % i])
                            item_ssl = self.params['identity_provider.%s.ssl' % i]
                            if not isinstance(item_ssl, bool):
                                item_ssl = str2bool(ensure_text(item_ssl))
                            item_timeout = self.params['identity_provider.%s.timeout' % i]
                            if not isinstance(item_timeout, int):
                                item_timeout = int(ensure_text(item_timeout))
                            if item_type == 'db':
                                auth_provider = DatabaseAuth(AuthDbManager, self.db_manager, SystemUser)
                            elif item_type == 'ldap':
                                item_dn = ensure_text(self.params['identity_provider.%s.dn' % i])
                                item_search_filter = ensure_text(self.params['identity_provider.%s.search_filter' % i])
                                item_search_id = ensure_text(self.params['identity_provider.%s.search_id' % i])
                                item_bind_user = ensure_text(self.params['identity_provider.%s.bind_user' % i])
                                item_bind_pwd = ensure_text(self.params['identity_provider.%s.bind_pwd' % i])
                                auth_provider = LdapAuth(item_host, SystemUser, timeout=item_timeout, ssl=item_ssl,
                                                         dn=item_dn, search_filter=item_search_filter,
                                                         search_id=item_search_id, bind_user=item_bind_user,
                                                         bind_pwd=item_bind_pwd)
                            self.auth_providers[item_provider] = auth_provider
                            self.logger.info('Setup authentication provider: %s' % auth_provider)

                    else:
                        self.logger.warning('Configure security - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure security - NOT CONFIGURED', exc_info=True)

                #
                # camunda configuration
                #
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
                    self.logger.warning('Configure Camunda  - NOT CONFIGURED', exc_info=True)

                # ##### awx configuration #####
                # try:
                #     self.logger.info('Configure AWX - CONFIGURE')
                #     #from beedrones.awx.old.awxclient import AwxClient, Awx
                #     #self.awx_client = Awx(AwxClient(self.params['awx_uri'], user=self.params['awx_user'],
                #     #                                passwd=self.params['awx_password'],
                #     #                                organization=self.params['awx_organization']))
                #     self.logger.info('Configure AWX  - CONFIGURED')
                # except:
                #     self.logger.warning('Configure AWX  - NOT CONFIGURED')
                # ##### awx configuration #####

                #
                # logstash configuration
                #
                try:
                    self.logger.info('Configure logstash - CONFIGURE')
                    logstash = self.params.get('logstash_host', None)
                    logstash_ca = self.params.get('logstash_ca', None)
                    logstash_cert = self.params.get('logstash_cert', None)
                    logstash_pkey = self.params.get('logstash_pkey', None)
                    if logstash is not None and logstash_ca is not None and logstash_cert is not None \
                            and logstash_pkey is not None:
                        logstash = ensure_text(logstash)
                        logstash_ca = ensure_text(logstash_ca)
                        logstash_cert = ensure_text(logstash_cert)
                        logstash_pkey = ensure_text(logstash_pkey)
                        host, port = logstash.split(':')
                        self.logstash = {
                            'host': host,
                            'port': int(port),
                            'ca': logstash_ca,
                            'ca_file': None,
                            'cert': logstash_cert,
                            'cert_file': None,
                            'pkey': logstash_pkey,
                            'pkey_file': None,
                        }
                        self.logger.debug('logstash config: %s' % truncate(self.logstash))
                        self.logger.info('Configure logstash - CONFIGURED')
                    else:
                        self.logger.warning('Configure logstash - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure logstash - NOT CONFIGURED', exc_info=True)

                #
                # elasticsearch configuration
                #
                try:
                    self.logger.info('Configure elasticsearch - CONFIGURE')
                    el_nodes = self.params.get('elasticsearch_nodes', None)
                    self.logger.info('configure - el_nodes: %s' % el_nodes)

                    if el_nodes is not None and el_nodes != '' and el_nodes != b'':
                        el_nodes = ensure_text(el_nodes)
                        el_nodes_and_and_cred = el_nodes.split('@')
                        http_auth = None
                        if len(el_nodes_and_and_cred) > 1:
                            http_auth = el_nodes_and_and_cred[1].split(':')
                        el_nodes = el_nodes_and_and_cred[0]
                        hosts = el_nodes.split(',')

                        self.logger.debug('configure - hosts: %s' % hosts)
                        # self.logger.warn('configure - http_auth: %s' % http_auth)

                        self.elasticsearch = Elasticsearch(
                            hosts,
                            # http_auth
                            http_auth=http_auth,
                            # turn on SSL
                            use_ssl=True,
                            # make sure we verify SSL certificates
                            verify_certs=False,
                        )
                        self.logger.info('Elasticsearch client: %s' % self.elasticsearch)
                        self.logger.info('Configure elasticsearch - CONFIGURED')
                    else:
                        self.logger.warning('Configure elasticsearch - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure elasticsearch - NOT CONFIGURED', exc_info=True)

                #
                # sendmail configuration
                #
                try:
                    self.logger.debug('Configure sendmail - CONFIGURE')

                    mail_server = self.params.get('sendmail_server', None)
                    mail_sender = self.params.get('sendmail_sender', None)
                    if mail_server is not None and mail_sender is not None:
                        mail_server = ensure_text(mail_server)
                        self.mailer = Mailer(mail_server)
                        self.logger.info('Use mail server: %s' % mail_server)

                        mail_sender = ensure_text(mail_sender)
                        self.mail_sender = mail_sender
                        self.logger.info('Use mail sender: %s' % mail_sender)

                        self.logger.info('Configure sendmail - CONFIGURED')
                    elif configurator.exist(app=self.app_name, group='mail'):
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
                    self.logger.warning('Configure sendmail - NOT CONFIGURED', exc_info=True)

                # ##### gateway configuration #####
                # try:
                #     if configurator.exist(app=self.app_name, group='gateway'):
                #         conf = configurator.get(app=self.app_name, group='gateway')
                #         self.logger.info('Configure gateway - CONFIGURE')
                #         for item in conf:
                #             gw = json.loads(item.value)
                #             self.gateways[gw['name']] = gw
                #             self.logger.info('Setup gateway: %s' % gw)
                #         self.logger.info('Configure gateway - CONFIGURED')
                #     else:
                #         self.logger.warning('Configure gateway - NOT CONFIGURED')
                # except:
                #     self.logger.warning('Configure gateway - NOT CONFIGURED')
                # ##### gateway configuration #####

                #
                # service queue configuration
                #
                # try:
                #     self.logger.info('Configure service queue - CONFIGURE')
                #
                #     redis_service_uri = self.params.get('redis_queue_uri', None)
                #     redis_service_exchange = self.params.get('redis_service_exchange', None)
                #     if redis_service_uri is not None and redis_service_exchange is not None:
                #         self.redis_service_uri = ensure_text(redis_service_uri)
                #         self.redis_service_exchange = redis_service_exchange
                #     else:
                #         self.logger.warning('Configure service queue - NOT CONFIGURED')
                #
                #     self.logger.info('Configure service queue - CONFIGURED')
                # except:
                #     self.logger.warning('Configure service queue - NOT CONFIGURED')

                #
                # event queue configuration
                #
                try:
                    self.logger.info('Configure event queue - CONFIGURE')
                    broker_queue_event = self.params.get('broker_queue_event', None)

                    if configurator.exist(app=self.app_name, group='queue', name='queue.event'):
                        conf = configurator.get(app=self.app_name, group='queue', name='queue.event')

                        # setup event producer
                        conf = json.loads(conf[0].value)
                        # set redis manager
                        self.broker_event_uri = ensure_text(self.params.get('broker_url', ''))
                        self.broker_event_exchange = ensure_text(conf['queue'])

                        # create instance of event producer
                        self.event_producer = EventProducerKombu(self.broker_event_uri, self.broker_event_exchange)
                        self.logger.info('Configure exchange %s on %s' % (self.broker_event_exchange,
                                                                          self.broker_event_uri))
                        self.logger.info('Configure event queue - CONFIGURED')
                    elif broker_queue_event is not None:
                        self.broker_event_uri = ensure_text(self.params.get('broker_url', ''))
                        self.broker_event_exchange = ensure_text(broker_queue_event)

                        # create instance of event producer
                        self.event_producer = EventProducerKombu(self.broker_event_uri, self.broker_event_exchange)
                        self.logger.info('Configure exchange %s on %s' % (self.broker_event_exchange,
                                                                          self.broker_event_uri))
                        self.logger.info('Configure event queue - CONFIGURED')
                    else:
                        self.logger.warning('Configure event queue - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure event queue - NOT CONFIGURED', exc_info=True)

                #
                # catalog queue configuration
                #
                try:
                    self.logger.info('Configure catalog queue - CONFIGURE')
                    broker_queue_catalog = self.params.get('broker_queue_catalog', None)
                    broker_url = self.params.get('broker_url', None)

                    if configurator.exist(app=self.app_name, group='queue', name='queue.catalog'):
                        conf = configurator.get(app=self.app_name, group='queue', name='queue.catalog')

                        # setup catalog producer
                        conf = json.loads(conf[0].value)
                        self.broker_catalog_uri = ensure_text(self.params.get('broker_url', ''))
                        self.broker_catalog_exchange = ensure_text(conf['queue'])
                        # self.redis_catalog_uri = ensure_text(self.params['redis_queue_uri'])
                        # self.redis_catalog_channel = ensure_text(conf['queue'])

                        # create instance of catalog producer
                        from beehive.module.catalog.producer import CatalogProducerKombu
                        self.catalog_producer = CatalogProducerKombu(self.broker_catalog_uri,
                                                                     self.broker_catalog_exchange)
                        self.logger.info('Configure exchange %s on %s' % (self.broker_catalog_exchange,
                                                                          self.broker_catalog_uri))
                        # from beehive.module.catalog.producer import CatalogProducerRedis
                        # self.catalog_producer = CatalogProducerKombu(self.redis_catalog_uri, self.redis_catalog_channel)
                        # self.logger.info('Configure queue %s on %s' % (self.redis_catalog_channel,
                        #                                                self.redis_catalog_uri))
                        self.logger.info('Configure catalog queue - CONFIGURED')
                    elif broker_url is not None and broker_queue_catalog is not None:
                        self.broker_catalog_uri = ensure_text(broker_url)
                        self.broker_catalog_exchange = ensure_text(broker_queue_catalog)

                        # create instance of catalog producer
                        from beehive.module.catalog.producer import CatalogProducerKombu
                        self.catalog_producer = CatalogProducerKombu(self.broker_catalog_uri,
                                                                     self.broker_catalog_exchange)
                        self.logger.info('Configure exchange %s on %s' % (self.broker_catalog_exchange,
                                                                          self.broker_catalog_uri))

                        # self.redis_catalog_uri = ensure_text(self.params['redis_queue_uri'])
                        # self.redis_catalog_channel = ensure_text(broker_queue_catalog)
                        #
                        # # create instance of catalog producer
                        # from beehive.module.catalog.producer import CatalogProducerRedis
                        # self.catalog_producer = CatalogProducerRedis(self.redis_catalog_uri, self.redis_catalog_channel)
                        # self.logger.info('Configure queue %s on %s' % (self.redis_catalog_channel,
                        #                                                self.redis_catalog_uri))
                        self.logger.info('Configure catalog queue - CONFIGURED')
                    else:
                        self.logger.warning('Configure catalog queue - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure catalog queue - NOT CONFIGURED', exc_info=True)

                ##### tcp proxy configuration #####
                # try:
                #     self.logger.info('Configure tcp proxy - CONFIGURE')
                #     if configurator.exist(app=self.app_name, group='tcpproxy'):
                #         conf = configurator.get(app=self.app_name, group='tcpproxy')
                #         self.tcp_proxy = conf[0].value
                #         self.logger.info('Setup tcp proxy: %s' % self.tcp_proxy)
                #         self.logger.info('Configure tcp proxy - CONFIGURED')
                #     else:
                #         self.logger.warning('Configure tcp proxy - NOT CONFIGURED')
                # except:
                #     self.logger.warning('Configure tcp proxy - NOT CONFIGURED')
                ##### tcp proxy configuration #####

                ##### http proxy configuration #####
                # try:
                #     self.logger.info('Configure http proxy - CONFIGURE')
                #     if configurator.exist(app=self.app_name, group='httpproxy'):
                #         conf = configurator.get(app=self.app_name, group='httpproxy')
                #         proxy = conf[0].value
                #         self.http_proxy = proxy
                #         self.logger.info('Setup http proxy: %s' % self.http_proxy)
                #         self.logger.info('Configure http proxy - CONFIGURED')
                #     else:
                #         self.logger.warning('Configure http proxy - NOT CONFIGURED')
                # except:
                #     self.logger.warning('Configure http proxy - NOT CONFIGURED')
                ##### http proxy configuration #####

                #
                # stacks uri reference configuration
                #
                try:
                    self.logger.info('Configure stacks uri reference - CONFIGURE')
                    stacks_uri = self.params.get('stacks_uri', None)
                    if configurator.exist(app=self.app_name, group='resource', name='stacks_uri'):
                        conf = configurator.get(app=self.app_name, group='resource', name='stacks_uri')
                        self.stacks_uri = conf[0].value
                        self.logger.info('Setup stacks uri reference: %s' % self.stacks_uri)
                        self.logger.info('Configure stacks uri reference - CONFIGURED')
                    elif stacks_uri is not None:
                        self.stacks_uri = ensure_text(stacks_uri)
                        self.logger.info('Setup stacks uri reference: %s' % self.stacks_uri)
                        self.logger.info('Configure stacks uri reference - CONFIGURED')
                    else:
                        self.logger.warning('Configure stacks uri reference - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure stacks uri reference - NOT CONFIGURED', exc_info=True)

                #
                # git uri reference configuration
                #
                try:
                    self.logger.info('Configure git uri reference - CONFIGURE')
                    git_uri = self.params.get('git_uri', None)
                    git_branch = self.params.get('git_branch', None)
                    if git_uri is not None and git_branch is not None:
                        self.git = {
                            'uri': ensure_text(git_uri),
                            'branch': ensure_text(git_branch),
                        }
                        self.logger.info('Setup git reference: %s' % self.git)
                        self.logger.info('Configure git uri reference - CONFIGURED')
                    else:
                        self.logger.warning('Configure git uri reference - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure git uri reference - NOT CONFIGURED', exc_info=True)

                #
                # api authentication configuration - not configure for auth module
                #
                try:
                    self.logger.info('Configure apiclient - CONFIGURE')

                    prefix = self.params.get('api_prefix', '')
                    if prefix is None:
                        prefix = ''
                    self.prefixuri = ensure_text(prefix)
                    self.logger.info('Get prefix: %s' % self.prefixuri)

                    self.catalog = ensure_text(self.params['api_catalog'])
                    self.logger.info('Get catalog: %s' % self.catalog)

                    endpoint = self.params.get('api_endpoint', None)
                    if endpoint is not None:
                        endpoint = ensure_text(endpoint)
                    self.logger.info('Get api endpoint: %s' % endpoint)

                    if endpoint is None:
                        self.endpoints = [self.cluster_app_uri]
                    else:
                        self.endpoints = [endpoint]
                    self.logger.info('Get auth endpoints: %s' % self.endpoints)

                    api_oauth2_client = self.params.get('api_oauth2_client', None)
                    api_user = self.params.get('api_user', None)
                    api_user_password = self.params.get('api_user_password', None)

                    # get oauth2 client
                    if api_oauth2_client is not None and api_oauth2_client != b'':
                        api_oauth2_client = ensure_text(api_oauth2_client)
                        client_id, client_secret = api_oauth2_client.split(':')
                        self.api_oauth2_client = {
                            'grant_type': 'client_credentials',
                            'uuid': client_id,
                            'secret': client_secret
                        }

                        # configure api client
                        self.configure_api_client()

                        self.logger.info('Get oauth2 client: %s' % api_oauth2_client)

                    # get auth system user from db config
                    elif configurator.exist(app=self.app_name, group='api', name='user'):
                        auth_user = configurator.get(app=self.app_name, group='api', name='user')[0].value
                        self.auth_user = json.loads(auth_user)
                        self.logger.info('Get auth user: %s' % self.auth_user.get('name', None))

                        # configure api client
                        self.configure_api_client()

                        self.logger.info('Configure apiclient - CONFIGURED')

                    # get auth system user from file config
                    elif api_user is not None and api_user_password is not None:
                        self.auth_user = {
                            'pwd': api_user_password,
                            'name': api_user
                        }
                        self.logger.info('Get auth user: %s' % self.auth_user.get('name', None))

                        # configure api client
                        self.configure_api_client()

                        self.logger.info('Configure apiclient - CONFIGURED')

                    else:
                        self.logger.warning('Configure apiclient - NOT CONFIGURED')
                except:
                    self.logger.warning('Configure apiclient - NOT CONFIGURED', exc_info=True)
                ##### api authentication configuration #####

                del configurator

            except ApiManagerError:
                raise

            # release db session
            self.release_session()
            operation.perms = None

        self.logger.info('Configure server - CONFIGURED')

    def configure_api_client(self):
        """Configure api client instance
        """
        oauth2_grant_type = 'jwt'
        authtype = 'keyauth'
        if self.api_oauth2_client is not None:
            oauth2_grant_type = 'client'
            authtype = 'oauth2'
        self.api_client = ApiClient(self.endpoints,
                                    self.auth_user.get('name', None),
                                    self.auth_user.get('pwd', None),
                                    None,
                                    catalog_id=self.catalog,
                                    prefixuri=self.prefixuri,
                                    client_config=self.api_oauth2_client,
                                    oauth2_grant_type=oauth2_grant_type,
                                    authtype=authtype)
        self.logger.debug('Configure api client: %s' % self.api_client)

    # def register_catalog_old(self):
    #     """Create endpoint instance in catalog
    #     """
    #     if self.api_client is not None:
    #         # if endpoint exist update it else create new one
    #         catalog = self.api_client.catalog_id
    #         service = self.app_subsytem
    #         uri = self.app_uri
    #         try:
    #             self.api_client.create_endpoint(catalog, self.app_endpoint_id,
    #                                             service, uri)
    #         except BeehiveApiClientError as ex:
    #             if ex.code == 409:
    #                 self.api_client.update_endpoint(self.app_endpoint_id,
    #                                                 catalog_id=catalog,
    #                                                 name=self.app_endpoint_id,
    #                                                 service=service,
    #                                                 uri=uri)
    #             else:
    #                 raise
    #         self.logger.info('Register %s instance in catalog' % self.app_endpoint_id)

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
        # uri = self.app_uri
        uri = self.cluster_app_uri
        if uri is not None:
            self.catalog_producer.send_sync(self.app_endpoint_id, self.app_desc, service, catalog, uri)
            # self.logger.info('Register %s instance in catalog' % self.app_endpoint_id)

    # def register_monitor(self):
    #     """Register instance in monitor
    #     """
    #     register = self.params.get('register-monitor', True)
    #     register = str2bool(register)
    #
    #     # skip monitor registration - usefool for temporary instance
    #     if register is False:
    #         return


class ApiModule(object):
    """Api module base class

    :param api_manager: ApiManager instance
    :param name: module name
    """
    def __init__(self, api_manager:ApiManager, name:str):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

        self.api_manager:ApiManager = api_manager
        self.name:str = name
        #TODO views seems unused added apis
        self.views = []
        self.apis = []
        self.controller: ApiController = None
        self.api_routes = []

        self.api_manager.modules[name] = self

    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__+'.'+self.__class__.__name__, id(self))

    def info(self):
        """Get module infos.

        :return: Dictionary with info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = {'name': self.name, 'api': self.api_routes}
        return res

    @property
    def redis_manager(self):
        return self.api_manager.redis_manager

    @property
    def redis_identity_manager(self):
        return self.api_manager.redis_identity_manager

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
        self.api_manager.get_session()

    def release_session(self):
        """release db session"""
        self.api_manager.release_session()

    def init_object(self):
        """Init object
        """
        self.get_controller().init_object()

    def register_api(self, **kwargs):
        self.logger.info(f"module {self.__module__}.{self.__class__} register api")
        if self.api_manager.app is not None:
            for api in self.apis:
                api.register_api(self, **kwargs)
        else:
            self.logger.warning( f"Warning self.api_manager.app is  None ")

    def register_task(self):
        if self.controller is not None:
            self.controller.register_async_methods()

    def get_superadmin_permissions(self):
        """Get superadmin permissions
        """
        perms = self.get_controller().get_superadmin_permissions()
        return perms

    def get_controller(self) -> 'ApiController':
        raise NotImplementedError()


class ApiController(object):
    """Base api controller

    :param module: ApiModule instance
    """
    def __init__(self, module: ApiModule):
        self.logger: logging.Logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

        self.module = module
        self.version = 'v1.0'

        # child classes
        self.child_classes = []

        # identity
        try:
            self.prefix = self.module.api_manager.prefix
            self.prefix_index = self.module.api_manager.prefix_index
            self.expire = self.module.api_manager.expire
        except:
            self.prefix = None
            self.prefix_index = None
            self.expire = None

        # db manager
        self.dbmanager = None

    def register_async_methods(self):
        self.logger.info('Register async methods for controller %s' % self)
        for child_class in self.child_classes:
            child_class(self).register_async_methods()

    def resolve_fk_id(self, key: str, get_entity: Callable, data: dict, new_key=None):
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

    def resolve_oid(self, fk :int or str, get_entity: Callable) -> str:
        res = fk
        if fk is not None and not isinstance(fk, int) and not fk.isdigit():
            res = get_entity(fk).oid
        return res

    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__module__ + '.' + self.__class__.__name__, id(self))

    @property
    def redis_manager(self):
        return self.module.redis_manager

    @property
    def redis_identity_manager(self):
        return self.api_manager.redis_identity_manager

    @property
    def mailer(self):
        return (self.module.api_manager.mailer, self.module.api_manager.mail_sender)

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

    #
    # server info
    #
    def ping(self):
        """ping service

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            sql_ping = self.api_manager.db_manager.ping()
        except:
            self.logger.warning('', exc_info=True)
            sql_ping = False

        try:
            redis_ping = self.api_manager.redis_manager.ping()
        except:
            self.logger.warning('', exc_info=True)
            redis_ping = False

        try:
            redis_identity_ping = self.api_manager.redis_identity_manager.ping()
        except:
            self.logger.warning('', exc_info=True)
            redis_identity_ping = False

        try:
            res = {
                'name': self.module.api_manager.app_name,
                'id': self.module.api_manager.app_id,
                'hostname': self.module.api_manager.server_name,
                'uri': self.module.api_manager.app_uri,
                'sql_ping': sql_ping,
                'redis_ping': redis_ping,
                'redis_identity_ping': redis_identity_ping

            }
            self.logger.debug('ping service: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            return False

    def info(self):
        """service info

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = {
                'name': self.module.api_manager.app_name,
                'id': self.module.api_manager.app_id,
                'modules': {k: v.info() for k, v in self.module.api_manager.modules.items()},
            }
            self.logger.debug('Get server info: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    def __get_version(self, package):
        """Get package version

        :param package: package name
        """
        try:
            mod = dynamic_import(package)
            res = {'name': package, 'version': mod.__version__}
        except:
            res = None

        return res

    def versions(self):
        """service package version

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = []
        packages = [
            'beecell',
            'beedrones',
            'beehive',
            'beehive_oauth2',
            'beehive_resource',
            'beehive_ssh',
            'beehive_service',
            'beehive_service_netaas'
        ]
        try:
            for package in packages:
                ver = self.__get_version(package)
                if ver is not None:
                    res.append(ver)

            self.logger.debug('Get server beehive package versions: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    #
    # query log
    #
    def get_log_from_elastic(self, *args, **kvargs):
        """Get log from elastic search

        :param args:
        :param kvargs:
        :param kvargs.date: date used to search index. Format YYYY.MM.DD
        :param kvargs.name: container partial name. Ex. uwsgi-auth, worker-auth, uwsgi-ssh
        :param kvargs.pod: pod name
        :param kvargs.op: operation id. Can be api_id, task_id, task_id:step_name
        :param kvargs.sort: sort field like timestamp:desc
        :param kvargs.page: page number
        :param kvargs.size: page size
        :return: list of events
        """
        self.logger.warn('elk query params: %s' % kvargs)

        date = kvargs.get('date', None)
        name = kvargs.get('name', None)
        pod = kvargs.get('pod', None)
        op = kvargs.get('op', None)
        # component = kvargs.get('component', None)
        # task = kvargs.get('task', None)
        page = kvargs.get('page', 0)
        size = kvargs.get('size', 20)
        sort = kvargs.get('sort', 'timestamp:desc')

        if date is None:
            date = datetime.now().strftime('%Y.%m.%d')
        index = '*-beehive-%s-filebeat-%s-%s-cmp_nivola*' % (self.api_manager.app_env, '7.12.0', date)

        match = []
        if name is not None:
            match.append({'match': {'kubernetes.container.name': {'query': name, 'operator': 'and'}}})

        if pod is not None:
            match.append({'match': {'kubernetes.pod.name': {'query': pod, 'operator': 'and'}}})

        if op is not None:
            match.append({'match': {'message': {'query': op, 'operator': 'and'}}})

        # if component is not None:
        #     match.append({'match': {'component': {'query': component, 'operator': 'and'}}})
        #
        # if task is not None:
        #     match.append({'match': {'task_id': {'query': task, 'operator': 'and'}}})

        if name is None and pod is None and op is None:
            query = {
                'bool': {
                    'must': [{
                        'match': {
                            'kubernetes.namespace': {
                                'query': 'beehive-%s' % self.api_manager.app_env
                            }
                        }
                    }]
                }
            }
        else:
            query = {
                'bool': {
                    'must': match
                }
            }

        self.logger.warn('elk query: %s' % query)

        page = page * size
        body = {'query': query}
        body.update({'sort': [{f[0]: f[1]} for f in [sort.split(':')]]})
        res = self.api_manager.elasticsearch.search(index=index, body=body, from_=page, size=size, sort=sort)
        logger.debug2('query elastic: %s' % truncate(res))
        hits = res.get('hits', {})
        values = []
        if len(hits.get('hits', [])) > 0:
            fields = ['_id']
            fields.extend(hits.get('hits', [])[0].get('_source').keys())
            headers = fields
            headers[0] = 'id'
        for hit in hits.get('hits', []):
            value = hit.get('_source')
            values.append(value.get('message'))
        values.reverse()
        total = hits.get('total', {})
        if isinstance(total, dict):
            total = total.get('value', 0)
        resp = {
            'page': page,
            'count': size,
            'total': total,
            'sort': sort,
            'values': values
        }
        logger.debug('query events: %s' % truncate(resp))
        return resp

    #
    # authorization
    #
    def init_object(self):
        """Register object types, objects and permissions related to module. Call this function when initialize
        system first time.
        """
        self.logger.info('Init %s - START' % self)
        self.logger.info('Init childs: %s' % self.child_classes)

        # init controller child classes
        for child in self.child_classes:
            child(self).init_object()
        self.logger.info('Init %s - STOP' % self)

    def get_session(self):
        """open db session"""
        return self.module.api_manager.get_session()

    def release_session(self, dbsession):
        """release db session"""
        return self.module.api_manager.release_session()

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
        :return: {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 'seckey':...}
        """
        return self.module.api_manager.get_identity(uid)

    def get_identities(self):
        """Get identities

        :return: [{'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 'seckey':...}, ..]
        """
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.module.api_manager.get_oauth2_identity(token)

    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.

        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.module.api_manager.verify_simple_http_credentials(user, pwd, user_ip)

    def can(self, action, objtype=None, definition=None):
        """Verify if  user can execute an action over a certain object type. Specify at least name or perms.

        :param objtype: object type. Es. 'resource', 'service' [optional]
        :param definition: object definition. Es. 'container.org.group.vm' [optional]
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: dict like {objdef1: [objid1, objid2, ..], objdef2: [objid3, objid4, ..], objdef3:[objid4, objid5, ..]}
            If definition is not None dict contains only {objdef: [objid1, objid2, ..]}
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
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
                    if (perm_objtype == objtype and perm_definition == definition and perm_action in ['*', action]):
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

            if len(list(res.keys())) > 0:
                return res
            else:
                if definition is None:
                    definition = ''
                raise Exception("Identity %s can not '%s' objects '%s:%s'" %
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
        self.logger.warning('Perms %s do not overlap needs %s' % (perms, needs))
        return False

    def get_needs(self, args):
        """Get needs

        :param args:
        :return:
        """
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
        """This method combine can, get_needs and has_needs, Use when you want to verify overlap between needs and
        permissions for a unique object.

        :param objtype: object type. Es. 'resource', 'service',
        :param definition: object definition. Es. 'container.org.group.vm' [optional]
        :param action: object action. Es. *, view, insert, update, delete, use
        :param objid: object unique id. Es. *//*//*, nome1//nome2//*, nome1//nome2//nome3
        :return: True if permissions overlap
        """
        if operation.authorize is False:
            return True
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

            # check needs overlaps perms
            res = self.has_needs(needs, objset)
            if res is False:
                raise ApiManagerError('')
            self.logger.debug2('check authorization OK')
        except ApiManagerError:
            msg = "Identity %s can not '%s' objects '%s:%s.%s'" % (operation.user[2], action, objtype, objdef, objid)
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
    # scheduler
    #
    def get_scheduler(self):
        """Get scheduler instance"""
        scheduler_module = self.api_manager.get_module('SchedulerModuleV2')
        scheduler_controller = scheduler_module.get_controller()
        scheduler = scheduler_controller.get_scheduler()
        return scheduler

    def create_schedule(self, name, task, schedule, args):
        """Create schedule

        :param name: schedule name
        :param task: schedule task
        :param schedule: schedule schedulation
        :param list args: schedule args
        :return:
        """
        scheduler = self.get_scheduler()
        scheduler.create_update_entry(name, task, schedule, args=args, kwargs=None, options={}, relative=None)
        return name

    def remove_schedule(self, schedule_name):
        """Remove schedule

        :param schedule_name: schedule name
        :return:
        """
        scheduler = self.get_scheduler()
        scheduler.remove_entry(schedule_name)
        self.logger.info('remove schedule %s' % schedule_name)

    #
    # helper model get method
    #
    def get_entity(self, entity_class, model_class, oid, for_update=False, details=True, authorize=True,*args, **kvargs):
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
            self.logger.error(ex, exc_info=True)
            entity_name = entity_class.__name__
            raise ApiManagerError('%s %s not found or name is not unique' % (entity_name, oid), code=404)

        if entity is None:
            entity_name = entity_class.__name__
            self.logger.warning('%s %s not found' % (entity_name, oid))
            raise ApiManagerError('%s %s not found' % (entity_name, oid), code=404)

        # check authorization
        if operation.authorize is True:
            if authorize:
                self.check_authorization(entity_class.objtype, entity_class.objdef, entity.objid, 'view')

        res = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                           desc=entity.desc, model=entity)

        # execute custom post_get
        if details is True:
            res.post_get()

        self.logger.debug('Get %s : %s' % (entity_class.__name__, res))
        return res

    def get_entity_for_task(self, entity_class, oid, *args, **kvargs):
        """Get single entity usable bya a celery task

        :param entity_class: Controller ApiObject Extension class
        :param oid: entity id
        :return: entity instance
        :raise ApiManagerError`:
        """
        return None

    def get_paginated_entities(self, entity_class, get_entities, page=0, size=10, order='DESC', field='id',
                               customize=None, authorize=True, *args, **kvargs):
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
        :param customize: function used to customize entities. Signature: def customize(entities, *args, **kvargs)
        :param authorize: boolean if True check authorizatione and query with perm_tag default True
        :param args: custom params
        :param kvargs: custom params
        :return: (list of entity_class instances, total)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        res = []
        tags = []

        if operation.authorize is True:
            if authorize:
                # verify permissions
                objs = self.can('view', entity_class.objtype, definition=entity_class.objdef)
                objs = objs.get(entity_class.objdef.lower())

                # create permission tags
                for p in objs:
                    tags.append(self.manager.hash_from_permission(entity_class.objdef, p))
                self.logger.debug('Permission tags to apply: %s' % tags)
            else:
                kvargs['with_perm_tag'] = False
                self.logger.debug('Auhtorization disabled by flag for command')
        else:
            kvargs['with_perm_tag'] = False
            self.logger.debug('Auhtorization disabled by greenlet for command')

        try:
            entities, total = get_entities(tags=tags, page=page, size=size, order=order, field=field, *args, **kvargs)

            for entity in entities:
                obj = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name,
                                   active=entity.active, desc=entity.desc, model=entity)
                res.append(obj)

            # customize entities
            if customize is not None:
                customize(res, tags=tags, *args, **kvargs)

            self.logger.debug('Get %s (total:%s): %s' % (entity_class.__name__, total, truncate(res)))
            return res, total
        except QueryError as ex:
            self.logger.warning(ex, exc_info=True)
            return [], 0

    def get_entities(self, entity_class, get_entities, authorize=True, *args, **kvargs):
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
            if authorize:
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
                obj = entity_class(self, oid=entity.id, objid=entity.objid, name=entity.name, active=entity.active,
                                   desc=entity.desc, model=entity)
                res.append(obj)
            self.logger.debug('Get %s : %s' % (entity_class.__name__, truncate(res)))
            return res
        except QueryError as ex:
            self.logger.warning(ex)
            return []


class ApiObject(object):
    """Base api object

    :param controller: ApiController instance
    :param oid: database id
    :param objid: authorization id
    :param name: name
    :param desc: description
    :param active: active
    :param model: orm class instance
    """
    module: ApiModule = None
    objtype = ''
    objdef = ''
    objuri = ''
    objname = 'object'
    objdesc = ''
    objmodel = None

    # set this to define db manger methdod used for update. If not set update is not supported
    update_object = None

    # set this to define db manger methdod used for patch. If not set delete is not supported
    patch_object = None

    # set this to define db manger methdod used for delete. If not set delete is not supported
    delete_object = None

    register = True

    API_OPERATION = 'API'
    SYNC_OPERATION = 'CMD'
    ASYNC_OPERATION = 'TASK'

    # cache key
    cache_key = 'object.get'

    def __init__(self, controller: ApiController, oid=None, objid=None, name=None, desc=None, active=None, model=None):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

        self.controller = controller
        self.model = model # db model if exist
        self.oid = oid # object internal db id
        self.objid = objid
        self.name = name
        self.desc = desc
        self.active = active

        # object uuid
        self.uuid: str = None
        if self.model is not None:
            self.uuid = self.model.uuid

        # object uri
        self.objuri = '/%s/%s/%s' % (getattr(self.controller, 'version', 'v1.0'), self.objuri, self.uuid)

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

    @property
    def task_manager(self):
        return self.api_manager.task_manager

    @property
    def task_scheduler(self):
        return self.api_manager.task_scheduler

    @staticmethod
    def join_typedef(parent, child):
        """
        Join typedef parent with typedef child
        """
        return '.'.join([parent, child])

    @staticmethod
    def get_type(self):
        """Get type"""
        return self.type, self.definition, self.__class__

    def get_user(self):
        """Get user info"""
        user = {
            'user': operation.user[0],
            'server': operation.user[1],
            'identity': operation.user[2],
            'api_id': operation.id
        }
        return user

    @staticmethod
    def _get_value(objtype, args):
        """Get value

        :param objtype: object type
        :param args: value args
        :return:
        """
        data = ['*' for i in objtype.split('.')]
        pos = 0
        for arg in args:
            data[pos] = arg
            pos += 1
        return '//'.join(data)

    def convert_timestamp(self, timestamp):
        """Convert timestamp to string

        :param timestamp: timestamp
        :return: timestamp converted
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
    # scheduled actions
    #
    def scheduled_action(self, action, schedule, params=None, task_path=None, task_name='scheduled_action_task'):
        """"""
        if task_path is None:
            task_path = 'beehive.module.scheduler_v2.tasks.ScheduledActionTask.'
        task = task_path + task_name
        schedule_name = 'action-%s-schedule' % action
        if params is None:
            params = {'steps': []}

        params.update(self.get_user())
        params['objid'] = str(uuid4())
        params['alias'] = 'ScheduledAction.%s' % action
        params['schedule_name'] = schedule_name
        params['steps'].insert(0, 'beehive.module.scheduler_v2.tasks.ScheduledActionTask.remove_schedule_step')
        args = [params]
        self.controller.create_schedule(schedule_name, task, schedule, args)
        self.logger.info('create scheduled action %s' % schedule_name)
        return schedule_name

    #
    # cache
    #
    def set_cache(self):
        """Cache object required infos.

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
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
        self.cache.set('%s.%s' % (self.cache_key, self.oid), data, ttl=self.cache_ttl)

    def get_cache(self):
        """Get cache items
        """
        res = self.cache.get_by_pattern('*.%s' % self.uuid)
        res.extend(self.cache.get_by_pattern('*.%s' % self.oid))
        res.extend(self.cache.get_by_pattern('*.%s' % self.name))
        res.extend(self.cache.get_by_pattern('*.%s' % self.objid))
        return res

    def clean_cache(self):
        """Clean cache
        """
        self.cache.delete_by_pattern('*.%s' % self.uuid)
        self.cache.delete_by_pattern('*.%s' % self.oid)
        self.cache.delete_by_pattern('*.%s' % self.name)
        self.cache.delete_by_pattern('*.%s' % self.objid)
        self.cache.delete_by_pattern('metrics.%s' % self.oid)

    def cache_data(self, cache_key, func, cache=True, ttl=1800, *args, **kwargs):
        """cache data from executed function

        :return: None if runstate does not exist
        """
        ret = self.controller.cache.get(cache_key)
        if operation.cache is False or cache is False or ret is None or ret == {} or ret == []:
            ret = func(*args, **kwargs)

            # save data in cache
            self.controller.cache.set(cache_key, ret, ttl=ttl)

        self.logger.debug2('cache data from func %s: %s' % (func.__name__, ret))
        return ret

    #
    # info
    #
    def small_info(self):
        """Get object small infos.

        :return: Dictionary with object info.
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
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

        if hasattr(self.model,'expiry_date') and self.model.expiry_date is not None:
            res['date']['expiry'] = format_date(self.model.expiry_date)

        return res

    def detail(self):
        """Get object extended info

        :return: Dictionary with object detail.
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
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

        if hasattr(self.model,'expiry_date') and self.model.expiry_date is not None:
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
            self.logger.warning(ex.value)

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
        """Register object permission tags. Create new permission tags in perm_tag if they do not already exist.
        Create association between permission tags and object in perm_tag_entity.

        :param args: objid split by //
        """
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.logger.debug('Register api object: %s:%s %s - START' % (self.objtype, self.objdef, objids))

        objids = [ensure_text(o) for o in objids]

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
        """
        self.logger.debug('Deregister api object %s:%s %s - START' % (self.objtype, self.objdef, objids))

        # deregister permission tags
        self.deregister_object_permtags()

        # remove object and permissions
        objid = '//'.join([ensure_text(o) for o in objids])
        self.api_client.remove_object(self.objtype, self.objdef, objid)

        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).deregister_object(list(objids))

        self.logger.debug('Deregister api object %s:%s %s - STOP' % (self.objtype, self.objdef, objid))

    def register_async_methods(self):
        # self.logger.debug('register class %s methods' % self.__class__.__name__)
        methods = get_class_methods_by_decorator(self.__class__, 'run_async')
        for method in methods:
            self.logger.debug('register async method %s for class %s' % (method, self.__class__.__name__))
            # self.logger.warn('register async method %s for class %s' % (method, self.__class__.__name__))
            getattr(self.__class__, method)(entity_class=self.__class__, register=True)

        # register async methods for child classes
        for child in self.child_classes:
            child(self.controller).register_async_methods()

    def set_superadmin_permissions(self):
        """ """
        self.set_admin_permissions('ApiSuperadmin', [])

    def set_admin_permissions(self, role, args):
        """Set admin permissions

        :param role: authorization role
        :param args: permissions args
        """
        # set main permissions
        self.api_client.append_role_permissions(role, self.objtype, self.objdef, self._get_value(self.objdef, args),
                                                '*')

    def set_viewer_permissions(self, role, args):
        """Set viewer permissions

        :param role: authorization role
        :param args: permissions args
        """
        # set main permissions
        self.api_client.append_role_permissions(role, self.objtype, self.objdef, self._get_value(self.objdef, args),
                                                'view')

    def verify_permisssions(self, action, *args, **kvargs):
        """Short method to verify permissions.

        :param action: action to verify. Can be *, view, insert, update, delete, use
        :return: True if permissions overlap
        :raises ApiManagerError: raise :class:`ApiManagerError`
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            # resource permissions
            if objid is None:
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

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        pass

    @staticmethod
    def pre_create(controller, *args, **kvargs):
        """Check input params before resource creation. This function is used in container resource_factory method.
        Extend this function to manipulate and validate create input params.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    @staticmethod
    def post_create(controller, *args, **kvargs):
        """Post create function. This function is used in object_factory method.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return None

    @staticmethod
    def pre_import(controller, *args, **kvargs):
        """Check input params before resource creation. This function is used in container resource_factory method.
        Extend this function to manipulate and validate import input params.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    @staticmethod
    def post_import(controller, *args, **kvargs):
        """Post import function. This function is used in object_factory method.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return None

    @staticmethod
    def pre_clone(controller, *args, **kvargs):
        """Check input params before resource cloning. This function is used in container resource_factory method.
        Extend this function to manipulate and validate clone input params.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    @staticmethod
    def post_clone(controller, *args, **kvargs):
        """Post clone function. This function is used in object_factory method.

        :param controller: ApiController instance
        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return None

    def pre_update(self, *args, **kvargs):
        """Pre update function. This function is used in update method. Extend this function to manipulate and
        validate update input params.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    def post_update(self, *args, **kvargs):
        """Post update function. This function is used in update method.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return True

    def pre_patch(self, *args, **kvargs):
        """Pre patch function. This function is used in update method. Extend this function to manipulate and
        validate patch input params.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    def post_patch(self, *args, **kvargs):
        """Post patch function. This function is used in update method.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return True

    def pre_delete(self, *args, **kvargs):
        """Pre delete function. This function is used in delete method. Extend this function to manipulate and
        validate delete input params.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    def post_delete(self, *args, **kvargs):
        """Post delete function. This function is used in delete method.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return True

    def pre_expunge(self, *args, **kvargs):
        """Pre expunge function. This function is used in expunge method. Extend this function to manipulate and
        validate expunge input params.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return kvargs

    def post_expunge(self, *args, **kvargs):
        """Post expunge function. This function is used in expunge method.

        :param list args: positional args
        :param dict kvargs: key value args
        :return: kvargs
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return True

    #
    # db session
    #
    def get_session(self):
        """open db session"""
        return self.controller.get_session()

    def release_session(self):
        """release db session"""
        return self.controller.release_session()

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
            response = ['KO', str(exception)]
        else:
            response = ['OK', '']

        action = op.split('.')[-1]

        data = {
            'opid': opid,
            'op': op,
            'api_id': opid,
            # 'args': compat(args),
            # 'kwargs': compat(params),
            # 'args': args,
            # 'kwargs': params,
            'args': [],
            'kvargs': '',
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
            'pod': self.api_manager.app_k8s_pod,
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
            self.logger.warning('Event can not be published. Event producer is not configured - %s' % ex)

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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        if self.update_object is None:
            raise ApiManagerError('Update is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('update')

        # clean cache
        self.clean_cache()

        # custom action
        if self.pre_update is not None:
            kvargs = self.pre_update(**kvargs)

        try:
            res = self.update_object(oid=self.oid, *args, **kvargs)

            self.logger.debug('Update %s %s with data %s' % (self.objdef, self.oid, truncate(kvargs)))
            return self.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='update')
    def patch(self, *args, **kvargs):
        """Patch entity.

        :param args: custom params
        :param kvargs: custom params
        :return: entity uuid
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        if self.patch_object is None:
            raise ApiManagerError('Patch is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('update')

        # clean cache
        self.clean_cache()

        # custom action
        if self.pre_patch is not None:
            kvargs = self.pre_patch(**kvargs)

        try:
            self.patch_object(self.model)

            self.logger.debug('Patch %s %s' % (self.objdef, self.oid))
            return self.uuid
        except TransactionError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

    @trace(op='delete')
    def delete(self, soft=False, **kvargs):
        """Delete entity.

        :param kvargs: custom params
        :param soft: if True make a soft delete
        :return: None
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        if self.delete_object is None:
            raise ApiManagerError('Delete is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('delete')

        # clean cache
        self.clean_cache()

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
            self.logger.error(ex, exc_info=True)
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        if self.expunge_object is None:
            raise ApiManagerError('Expunge is not supported for %s:%s' % (self.objtype, self.objdef))

        # verify permissions
        self.verify_permisssions('delete')

        # clean cache
        self.clean_cache()

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
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)

        # custom action
        if self.post_expunge is not None:
            self.post_expunge(**kvargs)

        return None


class ApiInternalObject(ApiObject):
    """Base api object used in base, auth and catalog module. This class use orm to create permissions.

    :param controller: ApiController instance
    :param oid: database id
    :param objid: authorization id
    :param name: name
    :param desc: description
    :param active: active
    :param model: orm class instance
    """
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
        self.logger.info('Init api object %s.%s - START' % (self.objtype, self.objdef))

        try:
            # call only once during db initialization
            # add object type
            obj_types = [(self.objtype, self.objdef)]
            self.auth_db_manager.add_object_types(obj_types)

            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)

            self.logger.info('Init api object %s.%s - STOP' % (self.objtype, self.objdef))
        except (QueryError, TransactionError) as ex:
            self.logger.warning(ex)

        # init child classes
        for child in self.child_classes:
            child(self.controller).init_object()

    def register_object(self, objids, desc=''):
        """Register object types, objects and permissions related to module.

        :param objids: objid split by //
        :param desc: object description
        """
        self.logger.debug('Register api object %s:%s %s - START' % (self.objtype, self.objdef, objids))

        try:
            # add object and permissions
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, '//'.join(objids), desc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)
        except (QueryError, TransactionError) as ex:
            self.logger.error('Register api object: %s - ERROR' % ex.value)
            raise ApiManagerError(ex, code=400)

        # register permission tags
        self.register_object_permtags(objids)

        self.logger.debug('Register api object %s:%s %s - STOP' % (self.objtype, self.objdef, objs))

        # register child classes
        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).register_object(objids, desc=child.objdesc)

    def deregister_object(self, objids):
        """Deregister object types, objects and permissions related to module.

        :param objids: objid split by //
        """
        self.logger.debug('Deregister api object %s:%s %s - START' % (self.objtype, self.objdef, objids))

        # deregister permission tags
        self.deregister_object_permtags()

        try:
            # remove object and permissions
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, objdef=self.objdef)[0][0]
            objid = '//'.join([ensure_text(o) for o in objids])
            self.auth_db_manager.remove_object(objid=objid, objtype=obj_type)

            self.logger.debug('Deregister api object %s:%s %s - STOP' % (self.objtype, self.objdef, objids))
        except (QueryError, TransactionError) as ex:
            self.logger.error('Deregister api object: %s - ERROR' % ex.value)
            raise ApiManagerError(ex, code=400)

        # deregister child classes
        objids.append('*')
        for child in self.child_classes:
            child(self.controller, oid=None).deregister_object(objids)

    def set_admin_permissions(self, role_name, args):
        """Set admin permissions

        :param role_name: authorization role
        :param args: permissions args
        """
        try:
            role = self.auth_db_manager.get_entity(Role, role_name)
            perms, total = self.auth_db_manager.get_permissions(objid=self._get_value(self.objdef, args), objtype=None,
                                                                objdef=self.objdef, action='*')

            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)

            # set child resources permissions
            for child in self.child_classes:
                res = child(self.controller, self)
                res.set_admin_permissions(role_name, self._get_value(res.objdef, args).split('//'))
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
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
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            # resource permissions
            if objid is None:
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
                    'id': p.id,
                    'oid': p.obj.id,
                    'subsystem': p.obj.type.objtype,
                    'type': p.obj.type.objdef,
                    'objid': p.obj.objid,
                    'aid': p.action.id,
                    'action': p.action.value,
                    'desc': p.obj.desc
                })

            self.logger.debug('Get permissions %s: %s' % (self.oid, truncate(res)))
            return res, total
        except ApiManagerError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)


class ApiViewResponse(ApiObject):
    """Base api object used when create api response

    :param controller: ApiController instance
    """
    objtype = 'api'
    objdef = 'Response'
    objdesc = 'Api Response'

    api_exclusions_list = [
        '/v1.0/server/ping:GET',
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
            obj_type = self.auth_db_manager.get_object_type(objtype=self.objtype, objdef=self.objdef)[0][0]
            objs = [(obj_type, self._get_value(self.objdef, []), self.objdesc)]
            actions = self.auth_db_manager.get_object_action()
            self.auth_db_manager.add_object(objs, actions)

            self.logger.debug('Register api object: %s' % objs)
        except (QueryError, TransactionError) as ex:
            self.logger.warning(ex)

    def set_admin_permissions(self, role_name, args):
        """Set admin permissions

        :param role_name: authorization role
        :param args: permission args
        """
        try:
            role = self.auth_db_manager.get_entity(Role, role_name)
            perms, total = self.auth_db_manager.get_permissions(objid=self._get_value(self.objdef, args), objtype=None,
                                                                objdef=self.objdef, action='*')

            # set container main permissions
            self.auth_db_manager.append_role_permissions(role, perms)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=400)

    def send_event(self, api, params={}, response=True, exception=None, opid=None):
        """Publish an event to event queue.

        :param api: api to audit {'path':.., 'method':.., 'elapsed':..}
        :param params: operation params [default={}]
        :param response: operation response. [default=True]
        :param exception: exception raised [optional]
        """
        elapsed = api.get('elapsed')
        code = api.get('code')
        path = api.get('path')
        method = api.get('method')
        objid = '*'
        api_explain = '%s:%s' % (api.get('path'), api.get('method'))

        if opid is None:
            opid = operation.id

        if exception is not None:
            response = [str(code), str(exception)]
        else:
            response = [str(code), '']

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

        # send event
        data = {
            'opid': opid,
            'op': '%s:%s' % (path, method),
            'api_id': operation.id,
            # 'args': [],
            # 'kwargs': compat(params),
            # 'args': compat(args),
            # 'kwargs': compat(params),
            'kwargs': jsonDumps(params),
            'args': [],
            # 'kwargs': params,
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
            'pod': self.api_manager.app_k8s_pod,
            'objid': objid,
            'objtype': self.objtype,
            'objdef': self.objdef,
            'action': action
        }

        # send event
        try:
            if api_explain not in self.api_exclusions_list:
                client = self.controller.module.api_manager.event_producer
                client.send(self.API_OPERATION, data, source, dest)
        except Exception as ex:
            self.logger.warning('Event can not be published. Event producer is not configured - %s' % ex)


class ApiView(FlaskView):
    """Base api object used when create an api view
    """
    authorizable = False
    prefix = 'identity:'
    expire = 3600
    parameters = []
    parameters_schema = None
    response_schema = None

    RESPONSE_MIME_TYPE = [
        'application/json',
        'application/bson',
        'text/xml',
        '*/*'
    ]

    def __init__(self, *argc, **argv):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

    def get_user_agent(self):
        return request.headers.get('User-Agent')

    def _get_response_mime_type(self):
        """Get response mime type"""
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

    def __get_auth_filter(self):
        """Get authentication filter. It can be keyauth, oauth2, simplehttp or ...
        """
        headers = request.headers
        if 'uid' in headers and 'sign' in headers:
            return 'keyauth'
        if 'Authorization' in headers and headers.get('Authorization').find('Basic') >= 0:
            return 'simplehttp'
        if 'Authorization' in headers and headers.get('Authorization').find('Bearer') >= 0:
            return 'oauth2'
        return None

    def __get_token(self):
        """get uid and sign from headers

        :return: authorization token, sign, request data
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

        :return: authorization token
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
        """Verify that simple http authentication contains valid fields and is allowed for the user provided.

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
            self.logger.warning('Authorization: %s' % authorization)
            credentials = b64decode(authorization)
            user, pwd = credentials.split(':')
            user_ip = get_remote_ip(request)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError('Error retrieving Authorization from http header', code=401)
        return user, pwd, user_ip

    def get_current_identity(self):
        """Get uid and sign from headers

        :return: authorization token, sign, request data
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.__get_token()

    def invalidate_user_session(self):
        """Remove user session from redis for api request
        """
        serializer = current_app.session_interface.serializer
        redis = current_app.session_interface.redis
        key_prefix = current_app.session_interface.key_prefix

        self.logger.warning(redis.keys('%s*' % key_prefix))

        session['_permanent'] = False
        self.logger.debug('Invalidate user session')

    def authorize_request(self, module):
        """Authorize http request

        :param module: beehive module instance
        :raise AuthViewError: raise :class:`AuthViewError`
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
                self.logger.error(msg, exc_info=True)
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
            compress_perms = user['perms']

            # get permissions
            operation.perms = json.loads(decompress(binascii.a2b_base64(compress_perms)))
            operation.user = (name, identity['ip'], uid, identity.get('seckey', None))
            self.logger.debug2('Get user %s permissions: %s' % (name, truncate(operation.perms)))
            if self.authorizable:
                ## TODO manage per method authorization
                pass
        except Exception as ex:
            msg = 'Error retrieving user %s permissions: %s' % (name, ex)
            self.logger.error(msg, exc_info=True)
            raise ApiManagerError(msg, code=401)

    # response methods
    def get_warning(self, exception, code, msg, module=None):
        """Return warning response

        :param exception: exception raised
        :param code: exception code
        :param msg: exception message
        :param module: current module [optional]
        :return: Flask Response
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.get_error(exception, code, msg, module=module)

    # response methods
    def get_error(self, exception, code, msg, module=None):
        """Return error response

        :param exception: exception raised
        :param code: exception code
        :param msg: exception message
        :param module: current module [optional]
        :return: Flask Response
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        headers = {'Cache-Control': 'no-store', 'Pragma': 'no-cache', 'remote-server': module.api_manager.server_name}

        error = {
            'code': code,
            'message': '%s' % msg,
            'description': '%s - %s' % (exception, msg)
        }
        self.logger.error('Api response: %s' % error)

        if self.response_mime is None or self.response_mime == '*/*' or self.response_mime == '':
            self.response_mime = 'application/json'

        if code in [400, 401, 403, 404, 405, 406, 408, 409, 415, 500]:
            status = code
        else:
            status = 400

        self.logger.error('Code: %s, Error: %s' % (code, exception), exc_info=True)
        if self.response_mime == 'application/json':
            return Response(response=json.dumps(error), mimetype='application/json', status=status, headers=headers)
        elif self.response_mime == 'application/bson':
            return Response(response=json.dumps(error), mimetype='application/bson', status=status, headers=headers)
        elif self.response_mime in ['text/xml', 'application/xml']:
            # xml = dicttoxml(error, root=False, attr_type=False)
            xml = dict2xml(error)
            return Response(response=xml, mimetype='application/xml', status=status, headers=headers)
        else:
            # 415 Unsupported Media Type
            res = {'msg': 'Unsupported media type'}
            return Response(response=res, mimetype='application/xml', status=415, headers=headers)

    def get_response(self, response, code=200, headers={}, module=None):
        """Return api response

        :param response: api response
        :param code: api response code [default=200]
        :param headers: custom headers
        :param module: current module [optional]
        :return: Flask Response
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        headers.update({'Cache-Control': 'no-store', 'Pragma': 'no-cache',
                        'remote-server': module.api_manager.server_name})

        try:
            if response is None:
                return Response(response='', mimetype='text/plain', status=code)

            self.logger.debug2('Api response mime type: %s' % self.response_mime)

            # redirect to new uri
            if code in [301, 302, 303, 305, 307]:
                self.logger.debug2('Api response: %s' % truncate(response))
                return response

            # render template
            elif self.response_mime.find('text/html') >= 0:
                self.logger.debug2('Api response: %s' % truncate(response))
                return response

            # return original response
            elif isinstance(response, Response):
                self.logger.debug2('Api response: %s' % truncate(response))
                return response

            # render json
            elif self.response_mime == 'application/json':
                resp = jsonDumps(response)
                self.logger.debug2('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/json', status=code, headers=headers)

            # render Bson
            elif self.response_mime == 'application/bson':
                resp = jsonDumps(response)
                self.logger.debug2('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/bson', status=code, headers=headers)

            # render xml
            elif self.response_mime in ['text/xml', 'application/xml']:
                # resp = dicttoxml(response, root=False, attr_type=False)
                resp = dict2xml(response)
                self.logger.debug2('Api response: %s' % truncate(resp))
                return Response(resp, mimetype='application/xml', status=code, headers=headers)

            # 415 Unsupported Media Type
            else:
                self.logger.debug2('Api response: ')
                return Response(response='', mimetype='text/plain', status=code, headers=headers)
        except Exception as ex:
            msg = 'Error creating response - %s' % ex
            self.logger.error(msg)
            raise ApiManagerError(msg, code=400)

    def format_paginated_response(self, response, entity, total, page=None, field='id', order='DESC', **kvargs):
        """Format response with pagination info

        :param response: response
        :param entity: entity like users
        :param page: page number [optional]
        :param total: total response records that user can view
        :param field: sorting field [default=id]
        :param order: sorting order [default=DESC]
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
        """http inner function. Override to implement apis

        :param controller: ApiController instance
        :param data: request data
        :param args: positional args
        :param kwargs: key value args
        :return: response
        """
        raise NotImplementedError()

    def to_dict(self, querystring):
        """Convert query string to dict

        :param querystring: query string
        :return:
        """
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

    def check_permission(self, controller:ApiController, rule:str, method:str ):
        if not operation.authorize is True:
            return
        if not self.authorizable is True:
            return
        objid = SHA256.new(bytes(rule, encoding='utf-8')).hexdigest()
        # objid = hashlib.sha256(bytes(rule, encoding='utf-8')).hexdigest()
        action = "view"
        if method == "get":
            action = "view"
        elif method == "post":
            action = "use"
        elif method == "put":
            action = "update"
        elif method == "delete":
            action = "delete"
        type = controller.module.api_manager.app_subsytem

        controller.check_authorization(type, ApiMethod.objdef, objid, action)

        pass

    def dispatch_request(self, module=None, secure=True, *args, **kwargs):
        """Base dispatch_request method. Extend this method in your child class

        :param module: ApiModule instance
        :param secure: if True dispatch request after authorization [default=True]
        :param args: positional args
        :param kwargs: key value args
        :return: Flask Response
        """
        import gevent

        # set reqeust timeout
        res = None

        timeout = gevent.Timeout(module.api_manager.api_timeout)
        timeout.start()

        start = time.time()
        data = None

        # open database session.
        # dbsession = module.get_session()
        module.get_session()
        controller = module.get_controller()

        opid = None

        try:
            headers = ['%s: %s' % (k, v) for k, v in request.headers.items()]

            # set operation
            operation.user = ('guest', get_remote_ip(request), None)
            operation.id = request.headers.get('request-id', str(uuid4()))
            operation.transaction = None
            operation.authorize = True
            operation.cache = True
            operation.encryption_key = module.api_manager.app_fernet_key

            self.logger.debug2('Set response timeout to: %s' % module.api_manager.api_timeout)

            if self.get_user_agent() != 'beehive-cmp':
                opid = getattr(operation, 'id', None)

            # class BeehiveLogRecord(logging.LogRecord):
            #     def __init__(self, *args, **kwargs):
            #         super(BeehiveLogRecord, self).__init__(*args, **kwargs)
            #         self.api_id = getattr(operation, 'id', None)
            #
            # logging.setLogRecordFactory(BeehiveLogRecord)

            self.logger.debug2('Start new operation: %s' % operation.id)
            self.logger.info('Invoke api: %s [%s] - START' % (request.path, request.method))

            query_string = self.to_dict(request.args)

            # get chunked input data
            if request.headers.get('Transfer-Encoding', '') == 'chunked':
                request_data = uwsgi_util.chunked_read(5)
            else:
                request_data = request.data

            self._get_response_mime_type()

            # check security
            if secure is True:
                self.authorize_request(module)

            # get request data
            try:
                data = request_data
                data = json.loads(data)
            except (AttributeError, ValueError):
                data = request.values.to_dict()

            request_data = deepcopy(data)

            self.logger.debug2('Api request headers: %s' % headers)

            # validate query/input data
            if self.parameters_schema is not None:
                if request.method.lower() == 'get':
                    query_string.update(kwargs)
                    try:
                        parsed = self.parameters_schema().load(query_string)
                        self.logger.debug2('Api request data: %s' % obscure_data(deepcopy(query_string)))
                    except ValidationError as err:
                        # self.logger.error(err.messages)
                        self.logger.error('+++++ validate request - err.messages: {}'.format(err.messages))
                        self.logger.error('+++++ validate request - query_string: %s' % (obscure_data(deepcopy(query_string))))
                        raise ApiManagerError(err.messages, code=400)
                else:
                    # data.update(kwargs)
                    try:
                        parsed = self.parameters_schema().load(data)
                        self.logger.debug2('Api request data: %s' % obscure_data(request_data))
                    except ValidationError as err:
                        # self.logger.error(err.messages)
                        self.logger.error('+++++ validate request - err.messages: {}'.format(err.messages))
                        self.logger.error('+++++ validate request - request_data: %s' % (obscure_data(request_data)))
                        raise ApiManagerError(err.messages, code=400)

                data = parsed
                self.logger.debug2('Api request data after validation: %s' % obscure_data(request_data))
            else:
                self.logger.debug2('Api request data: %s' % obscure_data(request_data))

            # TODO disabilitata per relase 1.11.0
            # if self.authorizable == True:
            #     self.check_permission(controller, request.url_rule.rule, request.method.lower())
            # dispatch request
            meth = getattr(self, request.method.lower(), None)
            if meth is None:
                meth = self.dispatch
            resp = meth(controller, data, *args, **kwargs)

            # fv - validate response
            if self.response_schema is not None:
                try:
                    # self.logger.info('+++++ validate response - self.response_schema: %s' % self.response_schema)
                    schema: Schema = self.response_schema()
                    if isinstance(resp, tuple):
                        parsed_response = schema.load(data=resp[0])
                    else:
                        parsed_response = schema.load(data=resp)
                    self.logger.info('+++++ validate response - OK - %s' % self.response_schema)
                except ValidationError as err:
                    self.logger.error('+++++ validate response - KO - %s' % self.response_schema)
                    self.logger.error('+++++ validate response - err.messages: {}'.format(err.messages))

                    try:
                        if isinstance(resp, tuple):
                            # self.logger.warning('+++++ validate response - resp original: %s' % (resp[0]))
                            self.logger.warning('+++++ validate response - resp: %s' % (obscure_data(resp[0])))
                        else:
                            self.logger.warning('+++++ validate response - resp: %s' % (obscure_data(resp)))
                    except Exception as ex:
                        self.logger.error('ex trying logging resp: %s' % ex)

            if isinstance(resp, tuple):
                code = resp[1]
                if len(resp) == 3:
                    res = self.get_response(resp[0], code=resp[1], headers=resp[2], module=module)
                else:
                    res = self.get_response(resp[0], code=resp[1], module=module)
            else:
                code = 200
                res = self.get_response(resp, module=module)

            # unset user permisssions in local thread object
            operation.perms = None
            # print('############# %s %s' % (gevent.getcurrent().name, request.path))
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.info('Invoke api: %s [%s] - STOP - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': code}
            ApiViewResponse(controller).send_event(event_data, request_data, opid=opid)
        except gevent.Timeout:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            msg = 'Request %s %s timeout' % (request.path, request.method)
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': 408}
            ApiViewResponse(controller).send_event(event_data, request_data, exception=msg, opid=opid)
            return self.get_error('Timeout', 408, msg, module=module)
        except ApiManagerError as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': ex.code}
            ApiViewResponse(controller).send_event(event_data, request_data, exception=ex.value, opid=opid)
            return self.get_error('ApiManagerError', ex.code, ex.value, module=module)
        except ApiManagerWarning as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.warning('Invoke api: %s [%s] - Warning - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': ex.code}
            ApiViewResponse(controller).send_event(event_data, request_data, exception=ex.value, opid=opid)
            return self.get_warning('ApiManagerWarning', ex.code, ex.value, module=module)
        except Exception as ex:
            # get request elapsed time
            elapsed = round(time.time() - start, 4)
            self.logger.error('Invoke api: %s [%s] - ERROR - %s' % (request.path, request.method, elapsed))
            event_data = {'path': request.path, 'method': request.method, 'elapsed': elapsed, 'code': 400}
            ApiViewResponse(controller).send_event(event_data, request_data, exception=str(ex), opid=opid)
            return self.get_error('Exception', 400, str(ex), module=module)
        finally:
            module.release_session()
            timeout.cancel()
            self.logger.debug2('Timeout released')

        return res

    @staticmethod
    def register_authorizable(module: ApiModule, rules: List[List[str]], version: str):
        """Register Api methods as object in the auth module.

        :param module: beehive module
        :param rules: route to register. Ex. [('/jobs', 'GET', ListJobs.as_view('jobs')), {'secure':False}]
        """
        subsystem = module.api_manager.app_subsytem
        objdef = ApiMethod.objdef

        def register_object(url:str):
            rule =f"/{version}/{url}"
            objid = SHA256.new(bytes(rule, encoding='utf-8')).hexdigest()
            #objid = hashlib.sha256(bytes(rule, encoding='utf-8')).hexdigest()

            logger.debug( f'Register api object: {subsystem}:{objdef} {rule} {objid} - START' )
            # add object and permissions
            module.api_manager.api_client.add_object(subsystem, objdef, objid, rule)
            logger.debug(f'Register api object: {subsystem}:{objdef} {objid} - STOP' )

        for rule in rules:
            url: str = rule[0]
            method: str = rule[1]
            view: ApiView = rule[2]
            if view.authorizable:
                logger.warning ( f'view for {url} is authorizable')
                logger.warning ( f'registering {url} for {method}')
                register_object(url)
                pass


    @staticmethod
    def register_api(module: ApiModule, rules: list, version:str=None, only_auth=False):
        """Register api as Flask route

        :param module: beehive module
        :param rules: route to register. Ex. [('/jobs', 'GET', ListJobs.as_view('jobs')), {'secure':False}]
        :param version: custom api version [optional]
        """

        logger = logging.getLogger(__name__)

        # get version
        if version is None:
            version = module.get_controller().version

        if only_auth:
            ApiView.register_authorizable(module, rules, version)
            return

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


class XmlnsSchema(Schema):
    xmlns = fields.String(required=False, data_key='__xmlns')


class PaginatedRequestQuerySchema(Schema):
    size = fields.Integer(default=20, example=20, missing=20, context='query',
                          description='entities list page size. -1 to get all the records',
                          validate=Range(min=-1, max=100, error='Size is out from range'))
    page = fields.Integer(default=0, example=0, missing=0, context='query',
                          description='entities list page selected',
                          validate=Range(min=0, max=10000, error='Page is out from range'))
    order = fields.String(validate=OneOf(['ASC', 'asc', 'DESC', 'desc'], error='Order can be asc, ASC, desc, DESC'),
                          description='entities list order: ASC or DESC',
                          default='DESC', example='DESC', missing='DESC', context='query')
    field = fields.String(validate=OneOf(['id', 'uuid', 'objid', 'name'], error='Field can be id, uuid, objid, name'),
                          description='entities list order field. Ex. id, uuid, name',
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
    creation = fields.DateTime(required=True, default='1990-12-31T23:59:59Z', example='1990-12-31T23:59:59Z',
                               description='creation date')
    modified = fields.DateTime(required=True, default='1990-12-31T23:59:59Z', example='1990-12-31T23:59:59Z',
                               description='modification date')
    expiry = fields.String(required=False, allow_none=True, default='', description='expiry date')


class ApiObjecCountResponseSchema(Schema):
    count = fields.Integer(required=True, default=10, description='number of items')


class ApiObjectMetadataResponseSchema(Schema):
    objid = fields.String(required=True, default='396587362//3328462822', example='396587362//3328462822',
                          description='authorization id')
    type = fields.String(required=True, default='auth', example='auth', description='entity category')
    definition = fields.String(required=True, default='Role', example='Role', description='entity type')
    uri = fields.String(required=True, default='/v1.0/auht/roles', example='/v1.0/auht/roles',
                        description='entity rest uri')


class ApiObjectSmallResponseSchema(Schema):
    id = fields.Integer(required=True, default=10, example=10, description='entity database id')
    uuid = fields.String(required=True, default='4cdf0ea4-159a-45aa-96f2-708e461130e1',
                         example='4cdf0ea4-159a-45aa-96f2-708e461130e1', description='entity uuid')
    name = fields.String(required=True, default='test', example='test', description='entity name')
    active = fields.Boolean(required=True, default=True, example=True, description='entity acitve status')
    __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)


class AuditResponseSchema(Schema):
    date = fields.Nested(ApiObjectResponseDateSchema, required=True)


class ApiObjectResponseSchema(AuditResponseSchema, ApiObjectSmallResponseSchema):
    # id = fields.Integer(required=True, default=10, example=10)
    # uuid = fields.String(required=True,  default='4cdf0ea4-159a-45aa-96f2-708e461130e1',
    #                      example='4cdf0ea4-159a-45aa-96f2-708e461130e1')
    # name = fields.String(required=True, default='test', example='test')
    desc = fields.String(required=True, default='test', example='test')
    # active = fields.Boolean(required=True, default=True, example=True)
    # __meta__ = fields.Nested(ApiObjectMetadataResponseSchema, required=True)


class PaginatedResponseSortSchema(Schema):
    order = fields.String(required=True, validate=OneOf(['ASC', 'asc', 'DESC', 'desc']), default='DESC', example='DESC')
    field = fields.String(required=True, default='id', example='id')


class PaginatedResponseSchema(Schema):
    count = fields.Integer(required=True, default=10, example=10, description='number of query items returned')
    page = fields.Integer(required=True, default=0, example=0, description='query page number')
    total = fields.Integer(required=True, default=20, example=20, description='total number of available query items')
    sort = fields.Nested(PaginatedResponseSortSchema, required=True, description='query sort order')


class CrudApiObjectSimpleResponseSchema(Schema):
    res = fields.Boolean(required=True,  default=True, example=True)


class CrudApiObjectResponseSchema(Schema):
    uuid = fields.UUID(required=True,  default='6d960236-d280-46d2-817d-f3ce8f0aeff7',
                       example='6d960236-d280-46d2-817d-f3ce8f0aeff7', description='api object uuid')


class CrudApiJobResponseSchema(Schema):
    jobid = fields.UUID(default='db078b20-19c6-4f0e-909c-94745de667d4',
                        example='6d960236-d280-46d2-817d-f3ce8f0aeff7',
                        required=True)


class CrudApiObjectJobResponseSchema(CrudApiObjectResponseSchema, CrudApiJobResponseSchema):
    pass


class CrudApiTaskResponseSchema(Schema):
    taskid = fields.UUID(default='db078b20-19c6-4f0e-909c-94745de667d4',
                         example='6d960236-d280-46d2-817d-f3ce8f0aeff7',
                         required=True, description='task id')


class CrudApiObjectTaskResponseSchema(CrudApiObjectResponseSchema, CrudApiTaskResponseSchema):
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
    """Base api object used when create api response

    :param controller: ApiController instance
    """
    authorizable = False
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
    """Base ApiClient class used by ApiManager"""
    def __init__(self, auth_endpoints, user, pwd, secret, catalog_id=None, authtype='keyauth', prefixuri='',
                 client_config=None, key=None, proxy=None, oauth2_grant_type='jwt'):
        BeehiveApiClient.__init__(self, auth_endpoints, authtype, user, pwd, secret, catalog_id, client_config, key,
                                  proxy, prefixuri, oauth2_grant_type)

    def admin_request(self, subsystem, path, method, data='', other_headers={}, silent=False, timeout=60):
        """Make api request using module internal admin user credentials

        :param subsystem: subsystem
        :param path: request path
        :param method: http method
        :param data: request data
        :param other_headers: other headers
        :param timeout: timeout [default=60]
        :param silent: if True does not log request
        :return: request response
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # propagate opernation.id to internal api call
        if isinstance(other_headers, dict):
            other_headers['request-id'] = operation.id
            other_headers['User-Agent'] = 'beehive-cmp'
        else:
            other_headers = {'request-id': operation.id, 'User-Agent': 'beehive-cmp'}

        try:
            if self.exist(self.uid, other_headers=other_headers) is False:
                self.create_token(other_headers=other_headers)
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex.value, code=ex.code)

        try:
            res = self.send_request(subsystem, path, method, data, self.uid, self.seckey, other_headers, silent=silent,
                                    timeout=timeout)
            self.logger.debug('Send admin request to %s using uid %s' % (path, self.uid))
        except BeehiveApiClientError as ex:
            self.logger.error('Send admin request to %s using uid %s: %s' % (path, self.uid, ex.value), exc_info=True)
            raise ApiManagerError(ex.value, code=ex.code)

        return res

    def user_request(self, subsystem, path, method, data='', other_headers={}, silent=False, timeout=60):
        """Make api request using module current user credentials

        :param subsystem: subsystem
        :param path: request path
        :param method: http method
        :param data: request data
        :param other_headers: other headers
        :param timeout: timeout [default=60]
        :param silent: if True does not log request
        :return: request response
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # propagate opernation.id to internal api call
        if isinstance(other_headers, dict):
            other_headers['request-id'] = operation.id
            other_headers['User-Agent'] = 'beehive-cmp'
        else:
            other_headers = {'request-id': operation.id, 'User-Agent': 'beehive-cmp'}

        try:
            # get user logged uid and password
            uid = operation.user[2]
            seckey = operation.user[3]
            res = self.send_request(subsystem, path, method, data, uid, seckey, other_headers, silent=silent,
                                    api_authtype=operation.token_type, timeout=timeout)
            self.logger.debug('Send user request to %s using uid %s' % (path, self.uid))
        except BeehiveApiClientError as ex:
            self.logger.error('Send user request to %s using uid %s: %s' % (path, self.uid, ex.value), exc_info=True)
            raise ApiManagerError(ex.value, code=ex.code)

        return res

    def admin_wait_task(self, subsystem, prefix, taskid, timeout=60, delta=3, maxtime=600, trace=None):
        """Wait for running task

        :param subsystem: subsystem
        :param prefix: api prefix like nws, nas, nrs
        :param taskid: task id
        :param timeout: request timeout [default=60]
        :param delta: loop delta time [default=3]
        :param maxtime: loop max time [default=600]
        :param trace: trace function [optional]
        :return: None
        """
        # propagate opernation.id to internal api call
        other_headers = {'request-id': operation.id, 'User-Agent': 'beehive-cmp'}

        try:
            if self.exist(self.uid) is False:
                self.create_token(other_headers=other_headers)
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex.value, code=ex.code)

        try:
            self.wait_task(subsystem, prefix, taskid, uid=self.uid, seckey=self.seckey, timeout=timeout, delta=delta,
                           maxtime=maxtime, trace=trace, other_headers=other_headers)
        except BeehiveApiClientError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
