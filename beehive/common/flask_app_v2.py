# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import logging
from uuid import uuid4
import ujson as json

# patch redis socket to use async comunication
from time import time
from socket import gethostname, gethostbyname
from flask import Flask, Response, request
from os import urandom
from six import b, ensure_text
from beecell.logger.helper import LoggerHelper
from beecell.logger.k8s_handler import K8shHandler

# from beecell.server.uwsgi_server.wrapper import uwsgi_util
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation

logger = logging.getLogger(__name__)


class BeehiveAppError(Exception):
    pass


class BeehiveAppV2(Flask):
    """Custom Flask app used to read configuration and initialize security.

    :param args: positional args
    :param kwargs: key value args
    """

    def __init__(self, *args, **kwargs):
        import sys

        logger.warn(sys.argv)
        config = kwargs.pop("config", None)
        super().__init__(*args, **kwargs)

        # set debug mode
        self.debug = False

        # flask secret
        self.secret_key = urandom(48)

        logger.warn("$$$$$$$$$$$$$$$$$$$$$$")

        # self.http_socket = uwsgi_util.opt['http-socket']
        # self.server_name = ensure_text(uwsgi_util.opt['api_host'])
        # self.server_fqdn = ensure_text(uwsgi_util.opt['api_fqdn'])
        # try:
        #     self.server_ip = ensure_text((uwsgi_util.opt['api_host']))
        # except:
        #     self.server_ip = '127.0.0.1'
        #
        # self.app_name = ensure_text(uwsgi_util.opt['api_name'])
        # self.app_id = ensure_text(uwsgi_util.opt['api_id'])
        # self.app_env = ensure_text(uwsgi_util.opt['api_env'])
        #
        # # api instance static config
        # self.params = uwsgi_util.opt
        #
        # # set logging path
        # log_path = '/var/log/%s/%s/' % (self.params['api_package'], self.params['api_env'])
        # self.log_path = self.params.get('api_log', log_path)
        #
        # def error405(e):
        #     operation.id = str(uuid4())
        #     error = {
        #         'code': 405,
        #         'message': 'Method Not Allowed',
        #         'description': 'Method Not Allowed'
        #     }
        #     logger.error('Api response: %s' % error)
        #     return Response(response=json.dumps(error), mimetype='application/json', status=405)
        # # self._register_error_handler(None, 405, error405)
        # self.register_error_handler(405, error405)
        #
        # def error404(e):
        #     operation.id = str(uuid4())
        #     error = {
        #         'code': 404,
        #         'message': 'Uri %s not found' % request.path,
        #         'description': 'Uri %s not found' % request.path
        #     }
        #     logger.error('Api response: %s' % error)
        #     return Response(response=json.dumps(error), mimetype='application/json', status=404)
        # # self._register_error_handler(None, 404, error404)
        # self.register_error_handler(404, error404)
        #
        # # setup loggers
        # loggin_level = int(self.params['api_logging_level'])
        #
        # class BeehiveLogRecord(logging.LogRecord):
        #     def __init__(self, *args, **kwargs):
        #         super(BeehiveLogRecord, self).__init__(*args, **kwargs)
        #         self.api_id = getattr(operation, 'id', 'xxx')
        #
        # logging.setLogRecordFactory(BeehiveLogRecord)
        #
        # self.setup_loggers(level=loggin_level)
        #
        logger.info("########## SERVER STARTING ##########")
        start = time()
        #
        # # api manager reference
        # self.api_manager = ApiManager(self.params, app=self, hostname=self.server_ip)
        #
        # # server configuration
        # # self.api_manager.configure_logger()
        # self.api_manager.configure()
        # # self.get_configurations()
        #
        # # load modules
        # self.api_manager.register_modules()
        #
        # # register in catalog
        # self.api_manager.register_catalog()
        #
        # logger.info('Setup server over: %s' % self.api_manager.app_uri)
        # logger.info('Setup server over: %s' % self.api_manager.uwsgi_uri)

        logger.info("########## SERVER STARTED ########## - %s" % round(time() - start, 2))

    def del_configurations(self):
        del self.db_uri
        del self.tcp_proxy

    def setup_loggers(self, level=LoggerHelper.DEBUG):
        """Setup loggers

        :param level:
        :return:
        """
        logname = uwsgi_util.opt["api_id"].decode("utf-8")

        # base logging
        # file_name = self.log_path.decode('utf-8') + logname + '.api.log'
        loggers = [
            logger,
            logging.getLogger("oauthlib"),
            logging.getLogger("beehive"),
            logging.getLogger("beecell"),
            logging.getLogger("beedrones"),
            logging.getLogger("beehive_oauth2"),
            logging.getLogger("beehive_service"),
            logging.getLogger("beehive_service_netaas"),
            logging.getLogger("beehive_resource"),
            logging.getLogger("beehive_ssh"),
            logging.getLogger("urllib3"),
            # logging.getLogger('beehive.common.data')
        ]
        frmt = (
            "%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s "
            "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
        )
        LoggerHelper.simple_handler(loggers, level, frmt=frmt, formatter=None, handler=K8shHandler)

    # def setup_additional_loggers(self, elasticsearch, level=LoggerHelper.DEBUG, tags=[], **custom_fields):
    #     """Setup loggers
    #
    #     :param elasticsearch: elasticsearch.Elasticsearch class instance
    #     :param level:
    #     :return:
    #     """
    #     loggers = [
    #         logger,
    #         logging.getLogger('oauthlib'),
    #         logging.getLogger('beehive'),
    #         logging.getLogger('beehive.db'),
    #         logging.getLogger('beecell'),
    #         logging.getLogger('beedrones'),
    #         logging.getLogger('beehive_oauth2'),
    #         logging.getLogger('beehive_service'),
    #         logging.getLogger('beehive_service_netaas'),
    #         logging.getLogger('beehive_resource'),
    #         logging.getLogger('beehive_ssh'),
    #         # logging.getLogger('beehive.common.data')
    #     ]
    #     # LoggerHelper.DEBUG2
    #     index = 'cmp-%s' % ensure_text(custom_fields['env'])
    #     LoggerHelper.elastic_handler(loggers, level, elasticsearch, index=index, tags=tags, **custom_fields)

    def open_db_session(self):
        """Open database session."""
        operation.session = self.api_manager.get_session()

    def release_db_session(self):
        """Release database session."""
        self.api_manager.release_session()
