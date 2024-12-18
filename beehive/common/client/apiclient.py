# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from uuid import uuid4

import requests
import ujson as json
import ssl
from copy import deepcopy
from time import time, sleep
from logging import getLogger
import binascii
from beecell.remote import NotFoundException
from beecell.types.type_string import truncate
from beecell.crypto import check_vault, sign_data
from beecell.password import obscure_data, obscure_string
from multiprocessing import current_process
from base64 import b64encode, b64decode
from beehive.common.jwtclient import JWTClient
from six.moves.urllib.parse import urlencode, quote
from six.moves import http_client
from six import PY3, ensure_text

from typing import Dict, List, Tuple


class BeehiveApiClientError(Exception):
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return "BeehiveApiClientError: %s" % self.value

    def __str__(self):
        return "%s, %s" % (self.value, self.code)


class BeehiveApiClient(object):
    """Beehive api client.

    :param auth_endpoints: api main endpoints
    :param authtype: api authentication filter: keyauth, aouth2, simplehttp
    :param user: api user
    :param pwd: api user password
    :param catalog_id: api catalog id
    :param key: [optional] fernet key used to decrypt encrypted password
    :param proxy: http proxy server {'host': .., 'port': ..} [optional]
    :param prefixuri: custom prefix path to use in uri [default='']
    :param oauth2_grant_type: oauth2 grant type. Can be jwt or client [default=jwt]
    """

    def __init__(
        self,
        auth_endpoints,
        authtype,
        user,
        pwd,
        secret=None,
        catalog_id=None,
        client_config=None,
        key=None,
        proxy=None,
        prefixuri="",
        oauth2_grant_type="jwt",
    ):
        self.logger = getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

        # check password is encrypted
        if pwd is not None:
            pwd = check_vault(pwd, key)

        self.pid = current_process().ident

        if len(auth_endpoints) > 0:
            self.main_endpoint = auth_endpoints[0]
        else:
            self.main_endpoint = None
        self.endpoints = {
            "auth": [],
            "event": [],
            "ssh": [],
            "resource": [],
            "service": [],
        }
        self.endpoint_weights = {
            "auth": [],
            "event": [],
            "ssh": [],
            "resource": [],
            "service": [],
        }
        self.api_authtype = authtype  # can be: simplehttp, oauth2, keyauth
        self.oauth2_grant_type = oauth2_grant_type
        self.api_user = user
        self.api_user_pwd = pwd
        self.api_user_secret = secret
        self.api_client_config = client_config

        self.catalog_id = catalog_id

        self.max_attempts = 3  # number of attempt to get a valid endpoint

        self.uid = None
        self.seckey = None
        self.filter = None

        self.proxy = proxy

        self.prefixuri = prefixuri

        # auth reference - http://10.102.160.240:6060
        for endpoint in auth_endpoints:
            self.endpoints["auth"].append([self.__parse_endpoint(endpoint), 0])
        self.logger.debug("Get main auth endpoints: %s" % self.endpoints["auth"])
        # load catalog
        # self.load_catalog()

    def __str__(self):
        try:
            client_id = self.api_client_config.get("uuid")
        except Exception:
            client_id = None
        return "<ApiClient(%s, %s, %s, %s, %s, %s, %s, %s)>" % (
            self.main_endpoint,
            self.api_authtype,
            self.api_user,
            self.catalog_id,
            client_id,
            self.proxy,
            self.prefixuri,
            self.oauth2_grant_type,
        )

    def __parse_endpoint(self, endpoint_uri: str) -> dict:
        """Parse endpoint http://10.102.160.240:6060

        :param endpoint: http://10.102.160.240:6060
        :return: {'proto':.., 'host':.., 'port':..}
        :rtype: dict
        """
        try:
            t1 = endpoint_uri.split("://")
            t2 = t1[1].split(":")
            return {"proto": t1[0], "host": t2[0], "port": int(t2[1])}
        except Exception as ex:
            self.logger.error("Error parsing endpoint %s: %s" % (endpoint_uri, ex))

    def set_endpoints(self, endpoints):
        for name, uri in endpoints.items():
            self.endpoints[name].append([self.__parse_endpoint(uri), 0])
        self.logger.debug("Set endpoints: %s" % self.endpoints)

    def endpoint(self, subsystem):
        """Select a subsystem endpoint from list

        :param subsystem: subsystem
        """
        endpoints = None
        endpoints = self.endpoints.get(subsystem)
        if len(endpoints) == 0:
            self.load_catalog()
            # if subsystem does not already exist return error
            try:
                endpoints = self.endpoints[subsystem]
            except Exception:
                raise BeehiveApiClientError("Subsystem %s reference is empty" % subsystem, code=404)

        # # if catalog does not contain subsystem reference, reload it
        # try:
        #     endpoints = self.endpoints.get(subsystem)
        # except:
        #     self.load_catalog()
        #     # if subsystem does not already exist return error
        #     try:
        #         endpoints = self.endpoints[subsystem]
        #     except:
        #         raise BeehiveApiClientError('Subsystem %s reference is empty' % subsystem, code=404)

        # order endpoint by lower weight
        endpoints = sorted(endpoints, key=lambda weight: weight[1])

        # select endpoint that ping:True
        endpoint = endpoints[0]

        # inc endpoint usage
        endpoint[1] += 1

        self.endpoints[subsystem] = endpoints

        return endpoint[0]

    def sign_request(self, seckey64, data):
        """Sign data using public/private key signature. Signature algorithm used is
        RSA. Hash algorithm is SHA256.

        :param seckey64: secret key encoded in base64
        :param data: data to sign
        :return: data signature
        :rtype: str
        """
        try:
            return sign_data(seckey64, data)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise BeehiveApiClientError("Error signing data: %s" % data, code=401)

    def http_client(
        self,
        proto,
        host,
        path,
        method,
        data="",
        headers={},
        port=80,
        timeout=30,
        print_curl=False,
        silent=False,
    ):
        """Http client. Usage: res = http_client2('https', 'host1', '/api', 'POST', port=443, data='', headers={})

        :param proto: Request proto. Ex. http, https
        :param host: Request host. Ex. 10.102.90.30
        :param port: Request port. [default=80]
        :param path: Request path. Ex. /api/
        :param method: Request method. Ex. GET, POST, PUT, DELETE
        :param headers: Request headers. [default={}]. Ex. {"Content-type": "application/x-www-form-urlencoded",
                                                            "Accept": "text/plain"}
        :param data: Request data. [default={}]. Ex. {'@number': 12524, '@type': 'issue', '@action': 'show'}
        :param timeout: Request timeout. [default=30s]
        :param print_curl: if True print curl request call
        :param silent: if True print curl request call
        :raise BeehiveApiClientError:
        """
        try:
            # start time
            start = time()
            method = method.upper()
            path = self.prefixuri + path

            # append request-id to headers
            if "request-id" not in headers:
                headers["request-id"] = str(uuid4())
            reqid = headers["request-id"]

            # append user agent
            if "User-Agent" not in headers:
                headers["User-Agent"] = "beehive/1.0"

            send_data = obscure_string(data)
            self.logger.info(
                "Api Request [%s] %s %s://%s:%s%s, timeout=%s" % (reqid, method, proto, host, port, path, timeout)
            )
            if silent is False:
                self.logger.debug(
                    "API Request: %s - Call: METHOD=%s, URI=%s://%s:%s%s, HEADERS=%s, DATA=%s"
                    % (
                        reqid,
                        method,
                        proto,
                        host,
                        port,
                        truncate(path),
                        headers,
                        truncate(send_data),
                    )
                )

            # format curl string
            if print_curl is True:
                curl_url = ["curl -k -v -S -X %s" % method.upper()]
                if data is not None and data != "":
                    curl_url.append("-d '%s'" % send_data)
                    curl_url.append('-H "Content-Type: application/json"')
                if headers is not None:
                    for header in headers.items():
                        curl_url.append('-H "%s: %s"' % header)
                curl_url.append("%s://%s:%s%s" % (proto, host, port, path))
                self.logger.debug(" ".join(curl_url))

            if proto == "http":
                conn = http_client.HTTPConnection(host, port, timeout=timeout)
                if self.proxy is not None and self.proxy.get("host") is not None:
                    conn.set_tunnel(self.proxy.get("host"), port=self.proxy.get("port"))
            else:
                try:
                    ssl._create_default_https_context = ssl._create_unverified_context
                except Exception:
                    pass
                if self.proxy is not None and self.proxy.get("host") is not None:
                    conn = http_client.HTTPSConnection(
                        self.proxy.get("host"),
                        port=self.proxy.get("port"),
                        timeout=timeout,
                    )
                    conn.set_tunnel(host, port=port)
                else:
                    conn = http_client.HTTPSConnection(host, port, timeout=timeout)

            # get response
            conn.request(method, path, data, headers)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise BeehiveApiClientError("Service Unavailable", code=503)

        response = None
        res = {}
        content_type = ""

        try:
            response = conn.getresponse()
            content_type = response.getheader("content-type")

            if response.status in [
                200,
                201,
                202,
                400,
                401,
                403,
                404,
                405,
                406,
                408,
                409,
                415,
            ]:
                res = response.read()
                if content_type is not None and content_type.find("application/json") >= 0:
                    res = json.loads(res)

                # insert for compliance with oauth2 error message
                if getattr(res, "error", None) is not None:
                    res["message"] = res["error_description"]
                    res["description"] = res["error_description"]
                    res["code"] = response.status

            elif response.status in [204]:
                res = {}
            elif response.status in [500]:
                res = {
                    "code": 500,
                    "message": "Internal Server Error",
                    "description": "Internal Server Error",
                }
            elif response.status in [501]:
                res = {
                    "code": 501,
                    "message": "Not Implemented",
                    "description": "Not Implemented",
                }
            elif response.status in [502]:
                res = {
                    "code": 502,
                    "message": "Bad Gateway Error",
                    "description": "Bad Gateway Error",
                }
            elif response.status in [503]:
                res = {
                    "code": 503,
                    "message": "Service Unavailable",
                    "description": "Service Unavailable",
                }
            else:
                res = {"code": response.status, "message": res, "description": res}
            conn.close()
        except Exception as ex:
            elapsed = time() - start
            self.logger.error(ex, exc_info=False)
            if silent is False:
                if response is not None:
                    self.logger.error(
                        "API Request: %s - Response: HOST=%s, STATUS=%s, CONTENT-TYPE=%s, RES=%s, "
                        "ELAPSED=%s"
                        % (
                            reqid,
                            response.getheader("remote-server", ""),
                            response.status,
                            content_type,
                            truncate(res),
                            elapsed,
                        )
                    )
                else:
                    self.logger.error(
                        "API Request: %s - Response: HOST=%s, STATUS=%s, CONTENT-TYPE=%s, RES=%s, "
                        "ELAPSED=%s" % (reqid, None, "Timeout", content_type, truncate(res), elapsed)
                    )

            raise BeehiveApiClientError(str(ex), code=400)

        if response.status in [200, 201, 202]:
            elapsed = time() - start
            if silent is False:
                self.logger.debug(
                    "API Request: %s - Response: HOST=%s, STATUS=%s, CONTENT-TYPE=%s, RES=%s, "
                    "ELAPSED=%s"
                    % (
                        reqid,
                        response.getheader("remote-server", ""),
                        response.status,
                        content_type,
                        truncate(res),
                        elapsed,
                    )
                )
        elif response.status in [204]:
            elapsed = time() - start
            if silent is False:
                self.logger.debug(
                    "API Request: %s - Response: HOST=%s, STATUS=%s, CONTENT-TYPE=%s, RES=%s, "
                    "ELAPSED=%s"
                    % (
                        reqid,
                        response.getheader("remote-server", ""),
                        response.status,
                        content_type,
                        truncate(res),
                        elapsed,
                    )
                )
        else:
            # self.logger.error('+++++ response.status: %s' % (response.status), exc_info=False)
            # self.logger.error('+++++ res: {}'.format(res), exc_info=False)
            if isinstance(res, dict):
                err = res.get("message", "")
                code = res.get("code", 400)
            else:
                err = res
                code = 400
            self.logger.error(err, exc_info=False)
            raise BeehiveApiClientError(err, code=int(code))

        return res

    def send_request(
        self,
        subsystem,
        path,
        method,
        data="",
        uid=None,
        seckey=None,
        other_headers=None,
        timeout=60,
        silent=False,
        print_curl=False,
        api_authtype=None,
    ):
        """Send api request

        :param subsystem: subsystem
        :param path: request path
        :param method: http method
        :param data: request data
        :param uid: token
        :param seckey: token seckey
        :param other_headers: other headers
        :param timeout: timeout
        :param silent: if True does not log request
        :return: request response
        :rtype: dict
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        # get endpoint
        endpoint = self.endpoint(subsystem)
        proto = endpoint["proto"]
        host = endpoint["host"]
        port = endpoint["port"]

        # create sign
        if uid is None and self.uid is not None:
            uid = self.uid
            seckey = self.seckey

        # set auth type
        if api_authtype is None:
            api_authtype = self.api_authtype

        headers = {"Accept": "application/json"}
        if api_authtype == "keyauth" and uid is not None:
            sign = self.sign_request(seckey, path)
            headers.update({"uid": uid, "sign": sign})

        elif api_authtype == "oauth2" and uid is not None:
            headers.update({"Authorization": "Bearer %s" % uid})

        elif api_authtype == "simplehttp":
            auth = b64encode("%s:%s" % (self.api_user, self.api_user_pwd))
            headers.update({"Authorization": "Basic %s" % auth})

        if other_headers is not None:
            headers.update(other_headers)

        # make request
        if isinstance(data, dict) or isinstance(data, list):
            if method.upper() == "GET":
                data = urlencode(data)
            else:
                data = json.dumps(data)

        if method.upper() == "GET":
            path = "%s?%s" % (path, data)

        res = self.http_client(
            proto,
            host,
            path,
            method,
            port=port,
            data=data,
            headers=headers,
            timeout=timeout,
            silent=silent,
            print_curl=print_curl,
        )
        return res

    def invoke(
        self,
        subsystem,
        path,
        method,
        data="",
        other_headers=None,
        parse=False,
        timeout=60,
        silent=False,
        print_curl=False,
    ):
        """Make api request using subsystem internal admin user credentials.

        :param subsystem: subsystem
        :param path: request path
        :param method: http method
        :param data: request data
        :param parse: if True parse input data
        :param timeout: timeout
        :param silent: if True does not log request
        :param print_curl: if True print curl like request in log
        :return: request response
        :rtype: dict
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        start = time()
        if isinstance(data, dict) or isinstance(data, list):
            send_data = obscure_data(deepcopy(data))
        else:
            send_data = obscure_string(data)
        self.logger.info("REQUEST: [%s] %s - uid=%s - data=%s" % (method, path, self.uid, send_data))
        try:
            if parse is True and isinstance(data, dict) or isinstance(data, list):
                data = json.dumps(data)

            res = self.send_request(
                subsystem,
                path,
                method,
                data,
                other_headers=other_headers,
                timeout=timeout,
                silent=silent,
                print_curl=print_curl,
            )
        except BeehiveApiClientError as ex:
            elapsed = time() - start
            self.logger.error("RESPONSE: [%s] %s - res=%s - %s - %s" % (method, path, ex.value, ex.code, elapsed))
            # Request is not authorized
            if ex.code in [401]:
                # try to get token and retry api call
                self.uid = None
                self.seckey = None
                self.create_token()
                res = self.send_request(
                    subsystem,
                    path,
                    method,
                    data,
                    other_headers=other_headers,
                    timeout=timeout,
                    silent=silent,
                )
            else:
                raise

        elapsed = time() - start
        self.logger.info("RESPONSE: [%s] %s - res=%s - %s" % (method, path, truncate(res, size=100), elapsed))

        return res

    #
    # task
    #
    def get_task_status(
        self,
        subsystem,
        prefix,
        taskid,
        uid=None,
        seckey=None,
        timeout=60,
        other_headers=None,
    ):
        """get task status

        :param subsystem:
        :param prefix:
        :param taskid:
        :param uid:
        :param seckey:
        :param timeout:
        :param other_headers: other headers
        :return:
        """
        if uid is None and self.uid is not None:
            uid = self.uid
            seckey = self.seckey

        try:
            path = "/v2.0/%s/worker/tasks/%s/status" % (prefix, taskid)
            res = self.send_request(
                subsystem,
                path,
                "get",
                data="",
                uid=uid,
                seckey=seckey,
                timeout=timeout,
                silent=True,
                other_headers=other_headers,
            )
            task = res.get("task_instance")
            status = task.get("status")
            return status
        except (NotFoundException, Exception):
            return "FAILURE"

    def get_task(
        self,
        subsystem,
        prefix,
        taskid,
        uid=None,
        seckey=None,
        timeout=60,
        other_headers=None,
    ):
        """get task

        :param subsystem:
        :param prefix:
        :param taskid:
        :param uid:
        :param seckey:
        :param timeout:
        :param other_headers: other headers
        :return:
        """
        if uid is None and self.uid is not None:
            uid = self.uid
            seckey = self.seckey

        try:
            path = "/v2.0/%s/worker/tasks/%s" % (prefix, taskid)
            res = self.send_request(
                subsystem,
                path,
                "get",
                data="",
                uid=uid,
                seckey=seckey,
                timeout=timeout,
                silent=True,
                other_headers=other_headers,
            )
            task = res.get("task_instance")
            self.logger.debug("Get task %s: %s" % (taskid, truncate(task)))
            return task
        except (NotFoundException, Exception) as ex:
            raise BeehiveApiClientError(str(ex))

    def wait_task(
        self,
        subsystem,
        prefix,
        taskid,
        uid=None,
        seckey=None,
        timeout=60,
        delta=3,
        maxtime=600,
        trace=None,
        other_headers=None,
    ):
        """Wait for running task

        :param subsystem: subsystem
        :param prefix: api prefix like nws, nas, nrs
        :param taskid: task id
        :param uid: authorization token [optional]
        :param seckey: seckey, only for keyauth aithorization [optional]
        :param timeout: request timeout [default=60]
        :param delta: loop delta time [default=3]
        :param maxtime: loop max time [default=600]
        :param trace: trace function [optional]
        :param other_headers: other headers
        :return: None
        """
        self.logger.info("wait for task %s" % taskid)
        status = self.get_task_status(
            subsystem,
            prefix,
            taskid,
            uid=uid,
            seckey=seckey,
            timeout=timeout,
            other_headers=other_headers,
        )
        elapsed = 0
        while status not in ["SUCCESS", "FAILURE", "TIMEOUT"]:
            sleep(delta)
            status = self.get_task_status(
                subsystem,
                prefix,
                taskid,
                uid=uid,
                seckey=seckey,
                timeout=timeout,
                other_headers=other_headers,
            )
            self.logger.debug("%s task %s status: %s" % (subsystem, taskid, status))
            if trace is not None:
                trace("%s task %s status: %s" % (subsystem, taskid, status))
            elapsed += delta
            if elapsed > maxtime:
                status = "TIMEOUT"

        # get task
        task = self.get_task(
            subsystem,
            prefix,
            taskid,
            uid=None,
            seckey=None,
            timeout=timeout,
            other_headers=other_headers,
        )

        if status == "TIMEOUT":
            msg = "%s task %s timeout" % (subsystem, taskid)
            self.logger.error(msg)
            if trace is not None:
                trace(msg)
            raise BeehiveApiClientError(msg)
        elif status == "FAILURE":
            msg = "%s task %s failure" % (subsystem, taskid)
            self.logger.error(msg)
            for err in task.get("traceback", []):
                self.logger.error(err.rstrip())
            if trace is not None:
                trace(msg)
            raise BeehiveApiClientError(msg)

        self.logger.info("%s task %s success" % (subsystem, taskid))

    #
    # authentication request
    #
    def ping(self, subsystem=None, endpoint=None):
        """Ping instance

        :param subsystem: subsystem to ping [optional]
        :param endpoint: endpoint to ping [optional]
        :return: if set endpoint return True or False. If set subsystem return list of all the endpoint with ping status
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        # make request
        res = False
        if endpoint is not None:
            if not isinstance(endpoint, dict):
                endpoint = self.__parse_endpoint(endpoint)
            proto = endpoint["proto"]
            host = endpoint["host"]
            port = endpoint["port"]
            try:
                resp = self.http_client(
                    proto,
                    host,
                    "/v1.0/server/ping",
                    "GET",
                    port=port,
                    data="",
                    timeout=0.5,
                )
                if "code" in resp:
                    return False
                return True
            except BeehiveApiClientError as ex:
                if ex.code in [500, 501, 503]:
                    res = False
        elif subsystem is not None:
            res = []
            for endpoint in self.endpoints.get(subsystem, []):
                try:
                    endpoint = endpoint[0]
                    proto = endpoint["proto"]
                    host = endpoint["host"]
                    port = endpoint["port"]
                    resp = self.http_client(
                        proto,
                        host,
                        "/v1.0/server/ping",
                        "GET",
                        port=port,
                        data="",
                        timeout=0.5,
                    )
                    if "code" in resp:
                        res.append([endpoint, False])
                    res.append([endpoint, True])
                except BeehiveApiClientError as ex:
                    if ex.code in [500, 501, 503]:
                        res.append([endpoint, False])
        return res

    def load_catalog(self, catalog_id=None):
        """Load catalog endpoint

        :param catalog_id: catalog id
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if catalog_id is not None:
            self.catalog_id = catalog_id

        if self.catalog_id is not None:
            # load catalog endpoints
            catalog = self.get_catalog(self.catalog_id)

            services = catalog["services"]
            for service in services:
                for endpoint in service["endpoints"]:
                    try:
                        self.endpoints[service["service"]].append([self.__parse_endpoint(endpoint), 0])
                    except Exception:
                        self.endpoints[service["service"]] = [[self.__parse_endpoint(endpoint), 0]]
        else:
            raise BeehiveApiClientError("Catalog id is undefined")

    def set_catalog_endpoint(self, service, endpoint, append=False):
        """Set new service endpoint manually

        :param service: beehive service
        :param endpoint: catalog endpoint
        :param append: if True append endpoint to existing list
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if append is True:
            self.endpoints[service].append([self.__parse_endpoint(endpoint), 0])
        else:
            self.endpoints[service] = [[self.__parse_endpoint(endpoint), 0]]

    def simplehttp_login(self, api_user=None, api_user_pwd=None, login_ip=None):
        """Login module internal user using simple http authentication

        :param api_user: api user
        :param api_user_pwd: api user password
        :param login_ip: login ip
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if api_user is None:
            api_user = self.api_user
        if api_user_pwd is None:
            api_user_pwd = self.api_user_pwd

        data = {"user": api_user, "password": api_user_pwd}
        # if login_ip is None:
        #     data['login-ip'] = self.host
        # else:
        #     data['login-ip'] = login_ip
        res = self.send_request("auth", "/v1.0/nas/simplehttp/login", "POST", data=json.dumps(data))
        self.logger.info("Login user %s: %s" % (self.api_user, res["uid"]))
        self.uid = None
        self.seckey = None
        self.filter = "simplehttp"

        return res

    def create_token(self, api_user=None, api_user_pwd=None, api_user_secret=None, other_headers=None):
        """Login module internal user

        :param api_user: api user
        :param api_user_pwd: api user password
        :param api_user_secret: api user secret
        :param other_headers: other headers
        :return: {'access_token': .. , 'seckey':.. }
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        res = None
        if api_user is None:
            api_user = self.api_user
        if api_user_pwd is None:
            api_user_pwd = self.api_user_pwd
        if api_user_secret is None:
            api_user_secret = self.api_user_secret

        if self.api_authtype == "keyauth":
            data = {"user": api_user, "password": api_user_pwd}
            res = self.send_request(
                "auth",
                "/v1.0/nas/keyauth/token",
                "POST",
                data=data,
                other_headers=other_headers,
            )
            self.logger.info("Login user %s with token: %s" % (self.api_user, res["access_token"]))
            self.uid = res["access_token"]
            self.seckey = res["seckey"]
        elif self.api_authtype == "oauth2" and self.oauth2_grant_type == "jwt":
            # get client
            client_id = self.api_client_config["uuid"]
            client_email = self.api_client_config["client_email"]
            client_scope = self.api_client_config["scopes"]
            private_key = binascii.a2b_base64(self.api_client_config["private_key"])
            client_token_uri = self.api_client_config["token_uri"]
            sub = "%s:%s" % (api_user, api_user_secret)

            res = JWTClient.create_token(
                client_id,
                client_email,
                client_scope,
                private_key,
                client_token_uri,
                sub,
            )
            self.uid = res["access_token"]
            self.seckey = ""
        elif self.api_authtype == "oauth2" and self.oauth2_grant_type == "client":
            data = {
                "grant_type": "client_credentials",
                "client_id": self.api_client_config["uuid"],
                "client_secret": self.api_client_config["secret"],
            }
            endpoint = self.endpoint("auth")
            # uri = '%s://%s:%s/v1.0/nas/oauth2/token' % (endpoint['proto'], endpoint['host'], endpoint['port'])
            uri = "%s://%s:%s%s/v1.0/nas/oauth2/token" % (
                endpoint["proto"],
                endpoint["host"],
                endpoint["port"],
                self.prefixuri,
            )
            res = requests.post(uri, data=data, headers=other_headers)
            res = res.json()
            # uri = '/v1.0/nas/oauth2/token?' + urlencode(data)
            # other_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            # res = self.send_request('auth', uri, 'POST', data='', other_headers=other_headers)
            self.logger.info("Login client %s with token: %s" % (self.api_client_config["uuid"], res["access_token"]))
            self.uid = res["access_token"]
            self.seckey = ""

        self.logger.debug("Get %s token: %s" % (self.api_authtype, self.uid))
        return res

    def exist(self, uid, other_headers=None):
        """Verify if identity exists

        :param uid: token
        :param other_headers: other headers
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if uid is None:
            return False
        try:
            self.send_request(
                "auth",
                "/v1.0/nas/tokens/%s" % uid,
                "GET",
                data="",
                uid=self.uid,
                seckey=self.seckey,
                silent=True,
                other_headers=other_headers,
            )
            res = True
            self.logger.debug("Check token %s is valid: %s" % (uid, res))
            return res
        except BeehiveApiClientError as ex:
            if ex.code == 401:
                return False

    #
    # configuration
    #
    def get_configuration(self, app_id):
        """Get configuration

        :param app_id: id used to get configuration. Default is portal
        """
        res = self.invoke("auth", "/api/config/%s", "GET", "")
        self.logger.debug("Get configuration from beehive")
        return res

    #
    # catalog request
    #
    def get_catalogs(self):
        """Get catalogs

        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        res = self.invoke("auth", "/v1.0/ncs/catalogs", "GET", "", silent=True)["catalogs"]
        self.logger.debug("Get catalogs")
        return res

    def get_catalog(self, catalog_id):
        """Get catalogs

        :param catalog_id: id of the catalog
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        res = self.invoke("auth", "/v1.0/ncs/catalogs/%s" % catalog_id, "GET", "", silent=True)["catalog"]
        self.logger.debug("Get catalog %s" % catalog_id)
        return res

    def create_catalog(self, name, zone):
        """Create catalogs

        :param name: catalog name
        :param zone: catalog zone
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"catalog": {"name": name, "desc": "catalog %s" % name, "zone": zone}}
        uri = "/v1.0/ncs/catalogs"
        res = self.invoke("auth", uri, "POST", json.dumps(data))
        self.logger.debug("Create catalog %s" % name)
        return res

    def delete_catalog(self, catalog_id):
        """Delete catalogs

        :param catalog_id: id of the catalog
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/ncs/catalogs/%s" % catalog_id
        self.invoke("auth", uri, "DELETE", "")
        self.logger.debug("Delete catalog %s" % catalog_id)

    #
    # endpoint request
    #
    def get_endpoints(self):
        """Get endpoints

        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        res = self.invoke("auth", "/v1.0/ncs/endpoints", "GET", "")
        self.logger.debug("Get endpoints")
        return res

    def get_endpoint(self, endpoint_id):
        """Get endpoints

        :param endpoint_id: id of the endpoint
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        res = self.invoke("auth", "/v1.0/ncs/endpoints/%s" % endpoint_id, "GET", "")
        self.logger.debug("Get endpoint %s" % endpoint_id)
        return res

    def create_endpoint(self, catalog_id, name, service, uri, uid=None, seckey=None):
        """Create endpoints

        :param catalog_id: id of the catalog
        :param name: endpoint name
        :param service: endpoint service
        :param uri: endpoint uri
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "endpoint": {
                "catalog": catalog_id,
                "name": name,
                "desc": "Endpoint %s" % name,
                "service": service,
                "uri": uri,
                "active": True,
            }
        }
        uri = "/v1.0/ncs/endpoints"
        res = self.invoke("auth", uri, "POST", json.dumps(data))
        self.logger.debug("Create endpoint %s" % name)
        return res

    def update_endpoint(
        self,
        oid,
        catalog_id=None,
        name=None,
        service=None,
        uri=None,
        uid=None,
        seckey=None,
    ):
        """Update endpoints

        :param oid: endpoint id/name
        :param catalog_id: id of the catalog
        :param new_name: endpoint name
        :param service: endpoint service
        :param uri: endpoint uri
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {}
        if catalog_id is not None:
            data["catalog"] = catalog_id
        if name is not None:
            data["name"] = name
        if service is not None:
            data["service"] = service
        if uri is not None:
            data["uri"] = uri

        data = {"endpoint": data}
        uri = "/v1.0/ncs/endpoints/%s" % oid
        res = self.invoke("auth", uri, "PUT", json.dumps(data))
        self.logger.debug("Create endpoint %s" % name)
        return res

    def delete_endpoint(self, endpoint_id):
        """Delete endpoints

        :param endpoint_id: id of the endpoint
        :param uid: identity id
        :param seckey: identity secret key
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/ncs/endpoints/%s" % endpoint_id
        self.invoke("auth", uri, "DELETE", "")
        self.logger.debug("Delete endpoint %s" % endpoint_id)

    #
    # authorization request
    #
    def add_object_types(self, objtype, objdef):
        """Add authorization object type

        :param objtype: obj type subsystem
        :param objdef: obj definition
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"object_types": [{"subsystem": objtype, "type": objdef}]}
        res = self.invoke("auth", "/v1.0/nas/objects/types", "POST", data, parse=True)
        self.logger.debug("Add object type: %s:%s" % (objtype, objdef))
        return res

    def add_object(self, objtype, objdef, objid, desc, **kvargs):
        """Add authorization object with all related permissions

        :param objtype: obj type
        :param objdef: obj definition
        :param objid: authorization id
        :param desc: object description
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        try:
            data = {"objects": [{"subsystem": objtype, "type": objdef, "objid": objid, "desc": desc}]}
            res = self.invoke("auth", "/v1.0/nas/objects", "POST", data, parse=True, silent=True)
            self.logger.debug("Add object: %s:%s %s" % (objtype, objdef, objid))
            return res
        except BeehiveApiClientError as ex:
            if ex.code == 409:
                pass
            else:
                raise

    def remove_object(self, objtype, objdef, objid, **kvargs):
        """Remove authorization object with all related permissions

        :param objtype: obj type
        :param objdef: obj definition
        :param objid: authorization id
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        # get object
        try:
            objid = objid.replace("//", "__")
            uri = "/v1.0/nas/objects/%s" % quote("%s:%s:%s" % (objtype, objdef, objid))
            res = self.invoke("auth", uri, "DELETE", "", parse=True, silent=True)
            self.logger.debug("Remove object: %s:%s %s" % (objtype, objdef, objid))
        except Exception:
            self.logger.warning("Object %s:%s can not be removed" % (objdef, objid), exc_info=True)
            return False

        return res

        # # get object
        # try:
        #     data = urlencode({'subsystem': objtype, 'type': objdef, 'objid': objid})
        #     uri = '/v1.0/nas/objects'
        #     res = self.invoke('auth', uri, 'GET', data, parse=True, silent=True).get('objects')
        # except:
        #     self.logger.warning('Object %s:%s can not be removed' % (objdef, objid))
        #     return False
        #
        # if len(res) <= 0:
        #     self.logger.warning('Object %s:%s can not be removed' % (objdef, objid))
        #     return False
        #
        # # remove object
        # uri = '/v1.0/nas/objects/%s' % res[0]['id']
        # res = self.invoke('auth', uri, 'DELETE', data, parse=True, silent=True)
        # self.logger.debug('Remove object: %s:%s %s' % (objtype, objdef, objid))
        # return res

    def get_permissions2(self, objtype, objdef, objid):
        """Get object permissions

        :param objtype: obj type list comma separated
        :param objdef: obj definition
        :param objid: authorization id
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = ""
        objid = objid.replace("//", "_")
        uri = "/api/nas/object/perm/T:%s+D:%s+I:%s" % (objtype, objdef, objid)
        res = self.invoke("auth", uri, "GET", data, silent=True)
        self.logger.debug("Get permission : %s:%s %s" % (objtype, objdef, objid))
        return res

    def get_permissions(self, objtype, objdef, objid, cascade=False, **kvargs):
        """Get object permissions

        :param objtype: obj type list comma separated
        :param objdef: obj definition
        :param objid: authorization id
        :param cascade: If true filter by objid and childs until objid+'//*//*//*//*//*//*'
        :param kvargs: kvargs
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "subsystem": objtype,
            "type": objdef,
            "objid": objid,
            "cascade": cascade,
        }
        data.update(kvargs)
        uri = "/v1.0/nas/objects/perms"
        res = self.invoke("auth", uri, "GET", urlencode(data), parse=True, silent=True)
        self.logger.debug("Get permission : %s:%s %s, cascade: %s" % (objtype, objdef, objid, cascade))
        return res.get("perms"), res.get("total")

    def append_role_permissions(self, role, objtype, objdef, objid, objaction):
        """Append permission to role

        :param role: role uuid
        :param objtype: obj type
        :param objdef: obj definition
        :param objid: authorization id
        :param objaction: obj action
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "role": {
                "perms": {
                    "append": [
                        {
                            "subsystem": objtype,
                            "type": objdef,
                            "objid": objid,
                            "action": objaction,
                        }
                    ],
                    "remove": [],
                }
            }
        }
        uri = "/v1.0/nas/roles/%s" % role
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append permission %s:%s %s %s to role %s" % (objtype, objdef, objid, objaction, role))
        return res

    def append_role_permission_list(self, role, perms):
        """Append permissions to role

        :param role: role uuid
        :param perms: list of {'subsystem': objtype, 'type': objdef, 'objid': objid, 'action': objaction}
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"role": {"perms": {"append": perms, "remove": []}}}
        uri = "/v1.0/nas/roles/%s" % role
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append permissions %s " % truncate(perms))
        return res

    def get_role(self, name):
        """Get role

        :param name: role name
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/nas/roles/%s" % name
        res = self.invoke("auth", uri, "GET", "", silent=True)
        self.logger.debug("Get role: %s" % name)
        return res

    def exist_role(self, name):
        """Check role exists

        :param name: role name
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = urlencode({"names": name})
        uri = "/v1.0/nas/roles"
        roles = self.invoke("auth", uri, "GET", data, silent=True).get("roles")
        res = None
        if len(roles) > 0:
            res = roles[0]
        self.logger.debug("Check role %s exists: %s" % (name, res))
        return res

    def add_role(self, name, desc):
        """Add role

        :param name: role name
        :param desc: role desc
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"role": {"name": name, "desc": desc}}
        uri = "/v1.0/nas/roles"
        res = self.invoke("auth", uri, "POST", data, parse=True, silent=True)
        self.logger.debug("Add role: %s" % name)
        return res

    def remove_role(self, oid):
        """Remove role

        :param oid: role uuid
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = ""
        uri = "/v1.0/nas/roles/%s" % oid
        res = self.invoke("auth", uri, "DELETE", data, parse=True, silent=True)
        self.logger.debug("Remove role: %s" % oid)
        return res

    def get_users(self, role=None):
        """Get users

        :param role: role uuid [optional]
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = urlencode({"role": role, "size": -1})
        uri = "/v1.0/nas/users"
        res = self.invoke("auth", uri, "GET", data, parse=True, silent=True).get("users", [])
        self.logger.debug("Get users: %s" % truncate(res))
        return res

    def get_user(self, name):
        """Get user

        :param name: user name
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/nas/users/%s" % name
        res = self.invoke("auth", uri, "GET", "", parse=True, silent=True)
        self.logger.debug("Get user: %s" % name)
        return res

    def get_perms_users(self, perms):
        """Get users associated to some permissions

        :param perms: list of permissions like (objtype, subsystem, objid, action)
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"size": -1, "perms.N": perms}
        uri = "/v1.0/nas/users"
        res = self.invoke("auth", uri, "GET", urlencode(data, doseq=True), parse=True, silent=True)
        self.logger.debug("Permissions %s are used by users: %s" % (perms, truncate(res)))
        return res.get("users")

    def add_user(self, name, password, desc):
        """Add user

        :param name: user name
        :param password: user password
        :param desc: user description
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "user": {
                "name": name,
                "desc": desc,
                "active": True,
                "expirydate": "2099-12-31",
                "password": password,
                "base": True,
            }
        }

        uri = "/v1.0/nas/users"
        res = self.invoke("auth", uri, "POST", data, parse=True, silent=True)
        self.logger.debug("Add base user: %s" % name)
        return res

    def add_system_user(self, name, password, desc):
        """Add system user

        :param name: user name
        :param password: user password
        :param desc: user description
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"user": {"name": name, "password": password, "desc": desc, "system": True}}
        uri = "/v1.0/nas/users"
        res = self.invoke("auth", uri, "POST", data, parse=True, silent=True)
        self.logger.debug("Add system user: %s" % name)
        return res

    def update_user(self, name, new_name, new_pwd, new_desc, uid=None, seckey=None):
        """Update user

        :param name: user name
        :param new_name: user new name
        :param new_pwd: user new password
        :param new_desc: user new description
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "user": {
                "name": new_name,
                "password": new_pwd,
                "desc": new_desc,
            }
        }
        uri = "/v1.0/nas/users/%s" % name
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Update user: %s" % name)
        return res

    def remove_user(self, oid):
        """Remove user

        :param oid: user uuid
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/nas/users/%s" % oid
        res = self.invoke("auth", uri, "DELETE", "", silent=True)
        self.logger.debug("Remove user: %s" % oid)
        return res

    def append_user_roles(self, oid, roles):
        """Append roles to user

        :param oid: user uuid
        :param roles: list of role uuids
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "user": {
                "roles": {"append": roles, "remove": []},
            }
        }
        uri = "/v1.0/nas/users/%s" % oid
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append roles %s to user %s" % (roles, oid))
        return res

    def remove_user_roles(self, oid, roles):
        """Remove roles from user

        :param oid: user uuid
        :param roles: list of role uuids
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "user": {
                "roles": {"append": [], "remove": roles},
            }
        }
        uri = "/v1.0/nas/users/%s" % oid
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Remove roles %s from user %s" % (roles, oid))
        return res

    def append_user_permissions(self, user, perms):
        """Append permissions to user

        :param user: user uuid
        :param perms: list of {'subsystem': objtype, 'type': objdef, 'objid': objid, 'action': objaction}
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"user": {"perms": {"append": perms, "remove": []}}}
        uri = "/v1.0/nas/users/%s" % user
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append user permissions %s " % truncate(perms))
        return res

    def remove_user_permissions(self, user, perms):
        """Remove permissions from user

        :param user: user uuid
        :param perms: list of {'subsystem': objtype, 'type': objdef, 'objid': objid, 'action': objaction}
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"user": {"perms": {"append": [], "remove": perms}}}
        uri = "/v1.0/nas/users/%s" % user
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append user permissions %s " % truncate(perms))
        return res

    #
    # auth group
    #
    def get_groups(self, role=None):
        """Get groups

        :param role: role uuid
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = urlencode({"role": role, "size": -1})
        uri = "/v1.0/nas/groups"
        res = self.invoke("auth", uri, "GET", data, parse=True, silent=True).get("groups", [])
        self.logger.debug("Get groups: %s" % truncate(res))
        return res

    def get_group(self, name):
        """Get group

        :param name: name
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/nas/groups/%s" % name
        res = self.invoke("auth", uri, "GET", "", parse=True, silent=True)
        self.logger.debug("Get group: %s" % name)
        return res

    def get_perms_groups(self, perms):
        """Get groups associated to some permissions

        :param perms: list of permissions like (objtype, subsystem, objid, action)
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"size": -1, "perms.N": perms}
        uri = "/v1.0/nas/groups"
        res = self.invoke("auth", uri, "GET", urlencode(data, doseq=True), parse=True, silent=True)
        self.logger.debug("Permissions %s are used by groups: %s" % (perms, truncate(res)))
        return res.get("groups")

    def append_group_roles(self, oid, roles):
        """Append roles to group

        :param oid: role uuid
        :param roles: list of role uuids
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "group": {
                "roles": {"append": roles, "remove": []},
            }
        }
        uri = "/v1.0/nas/groups/%s" % oid
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append roles %s to group %s" % (roles, oid))
        return res

    def remove_group_roles(self, oid, roles):
        """Remove roles from group

        :param oid: role uuid
        :param roles: list of role uuids
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "group": {
                "roles": {"append": [], "remove": roles},
            }
        }
        uri = "/v1.0/nas/groups/%s" % oid
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Remove roles %s from group %s" % (roles, oid))
        return res

    def append_group_permissions(self, group, perms):
        """Append permissions to group

        :param group: group uuid
        :param perms: list of {'subsystem': objtype, 'type': objdef, 'objid': objid, 'action': objaction}
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"group": {"perms": {"append": perms, "remove": []}}}
        uri = "/v1.0/nas/groups/%s" % group
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append group permissions %s " % truncate(perms))
        return res

    def remove_group_permissions(self, group, perms):
        """Remove permissions from group

        :param group: group uuid
        :param perms: list of {'subsystem': objtype, 'type': objdef, 'objid': objid, 'action': objaction}
        :return:
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"group": {"perms": {"append": [], "remove": perms}}}
        uri = "/v1.0/nas/groups/%s" % group
        res = self.invoke("auth", uri, "PUT", data, parse=True, silent=True)
        self.logger.debug("Append group permissions %s " % truncate(perms))
        return res

    #
    # services
    #
    def get_service_instance(self, plugintype=None, account=None, name=None):
        """Get service instance

        :param plugintype: plugin type
        :param account: account uuid
        :param name: service name
        :return:
        """
        data = urlencode({"account_id": account, "name": name, "plugintype": plugintype})
        uri = "/v2.0/nws/serviceinsts"
        res = self.invoke("service", uri, "GET", data, timeout=60)
        self.logger.debug("Get service instance: %s" % truncate(res))
        res = res.get("serviceinsts")
        if len(res) < 1:
            raise BeehiveApiClientError("Service instance %s does not exist" % name)
        if len(res) > 1:
            raise BeehiveApiClientError("Service instance %s multiplicity is > 1" % name)
        return res[0].get("uuid")

    def create_vpcaas_image(self, account=None, name=None, template=None, **kvargs):
        """Create business image

        :param account: account uuid
        :param name: name
        :param template: service definition uuid
        :param kvargs: key value args
        :return: image
        """
        data = {"ImageName": name, "owner_id": account, "ImageType": template}
        uri = "/v1.0/nws/computeservices/image/createimage"
        res = self.invoke("service", uri, "POST", data={"image": data}, timeout=600)
        self.logger.debug("Add image: %s" % truncate(res))
        res = res.get("CreateImageResponse").get("imageId")
        return res

    def create_vpcaas_vpc(self, account=None, name=None, template=None, **kvargs):
        """Create business vpc

        :param account: account uuid
        :param name: name
        :param template: service definition uuid
        :param kvargs: key value args
        :return: vpc
        """
        data = {"VpcName": name, "owner_id": account, "VpcType": template}
        uri = "/v1.0/nws/computeservices/vpc/createvpc"
        res = self.invoke("service", uri, "POST", data={"vpc": data}, timeout=600)
        self.logger.debug("Add vpc: %s" % truncate(res))
        res = res.get("CreateVpcResponse").get("vpc").get("vpcId")
        return res

    def create_vpcaas_subnet(self, account=None, name=None, vpc=None, zone=None, cidr=None, **kvargs):
        """Create business vpc subnet

        :param account: account uuid
        :param name: name
        :param vpc: vpc uuid
        :param zone: availability zone uuid
        :param cidr: subnet cidr
        :param kvargs: key value args
        :return: subnet
        """
        vpc_id = self.get_service_instance(plugintype="ComputeVPC", account=account, name=vpc)
        data = {
            "SubnetName": name,
            "VpcId": vpc_id,
            "AvailabilityZone": zone,
            "CidrBlock": cidr,
        }
        uri = "/v1.0/nws/computeservices/subnet/createsubnet"
        res = self.invoke("service", uri, "POST", data={"subnet": data}, timeout=600)
        self.logger.debug("Add subnet: %s" % truncate(res))
        res = res.get("CreateSubnetResponse").get("subnet").get("subnetId")
        return res

    def create_vpcaas_sg(self, account=None, name=None, vpc=None, template=None, **kvargs):
        """Create business vpc security group

        :param account: account uuid
        :param name: name
        :param vpc: vpc uuid
        :param template: service definition uuid
        :param kvargs: key value args
        :return: security group
        """
        vpc_id = self.get_service_instance(plugintype="ComputeVPC", account=account, name=vpc)
        data = {"GroupName": name, "VpcId": vpc_id}
        if template is not None:
            data["GroupType"] = template
        uri = "/v1.0/nws/computeservices/securitygroup/createsecuritygroup"
        res = self.invoke("service", uri, "POST", data={"security_group": data}, timeout=600)
        self.logger.debug("Add security group: %s" % truncate(res))
        res = res.get("CreateSecurityGroupResponse").get("groupId")
        return res

    def create_netaas_health_monitor(self, account=None, name=None, template=None, **kvargs):
        """Create business lb health monitor

        :param account: account uuid
        :param name: name
        :param template: service definition uuid
        :param kvargs: key value args
        :return: health monitor uuid
        """
        data = {
            "owner-id": account,
            "Name": name,
            "Protocol": kvargs.get("protocol").upper(),
        }
        if template is not None:
            data["MonitorTemplate"] = template
        uri = "/v1.0/nws/networkservices/loadbalancer/healthmonitor/createhealthmonitor"
        res = self.invoke("service", uri, "POST", data={"health_monitor": data}, timeout=600)
        self.logger.debug("Add health monitor: %s" % truncate(res))
        res = res.get("CreateHealthMonitorResponse").get("HealthMonitor").get("healthMonitorId")
        return res

    def create_netaas_listener(self, account=None, name=None, template=None, **kvargs):
        """Create business lb listener

        :param account: account uuid
        :param name: name
        :param template: service definition uuid
        :param kvargs: key value args
        :return: listener uuid
        """
        data = {
            "owner-id": account,
            "Name": name,
            "TrafficType": kvargs.get("traffic_type"),
            "Persistence": kvargs.get("persistence"),
        }
        if template is not None:
            data["ListenerTemplate"] = template
        uri = "/v1.0/nws/networkservices/loadbalancer/listener/createlistener"
        res = self.invoke("service", uri, "POST", data={"listener": data}, timeout=600)
        self.logger.debug("Add listener: %s" % truncate(res))
        res = res.get("CreateListenerResponse").get("Listener").get("listenerId")
        return res

    #
    # ssh module
    #
    def exist_ssh_group(self, oid):
        """Verify if ssh group already exists

        :param oid: ssh group id, uuid or name
        :return: True or False
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        try:
            uri = "/v1.0/gas/groups/%s" % quote(oid)
            res = self.invoke("ssh", uri, "GET", "", parse=True, silent=True)
            res = res.get("group")
            self.logger.debug("Ssh group %s exists" % oid)
            return True
        except Exception:
            self.logger.debug("Ssh group %s does not exist" % oid)
            return False

    def get_ssh_group(self, oid):
        """Get ssh group

        :param oid: ssh group id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/gas/groups/%s" % quote(oid)
        res = self.invoke("ssh", uri, "GET", "", parse=True, silent=True)
        res = res.get("group")
        self.logger.debug("Get ssh group %s: %s" % (oid, truncate(res)))
        return res

    def add_ssh_group(self, name, desc, attribute):
        """Add ssh group

        :param name: ssh group name
        :param desc: ssh group desc
        :param attribute: ssh group attribute
        :return: group uuid
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {"group": {"name": name, "desc": desc, "attribute": attribute}}
        uri = "/v1.0/gas/groups"
        res = self.invoke("ssh", uri, "POST", data, parse=True, silent=True)
        uuid = res.get("uuid")
        self.logger.debug("Add ssh group %s: %s" % (name, uuid))
        return uuid

    def delete_ssh_group(self, oid):
        """Delete ssh group

        :param oid: ssh group id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/gas/groups/%s" % oid
        res = self.invoke("ssh", uri, "DELETE", "", parse=True, silent=True)
        self.logger.debug("Delete ssh group %s: %s" % (oid, truncate(res)))
        return res

    def set_ssh_group_authorization(self, name, role, user=None, group=None):
        """Set ssh group authorization

        :param name: ssh group name
        :param role: ssh group role to assign
        :param user: user who receive authorization [optional]
        :param group: group who receive authorization [optional]
        :return: True
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if user is not None:
            prefix = "user"
            entity = user
        elif group is not None:
            prefix = "group"
            entity = group
        else:
            self.logger.error("User or group must be specified")
            raise BeehiveApiClientError("User or group must be specified")
        data = {prefix: {"%s_id" % prefix: entity, "role": role}}
        uri = "/v1.0/gas/groups/%s/%ss" % (name, prefix)
        res = self.invoke("ssh", uri, "POST", data, parse=True, silent=True)
        self.logger.debug("Set authorization to ssh group %s for %s %s with role %s" % (name, prefix, entity, role))
        return res

    def get_ssh_keys(self, oid=None):
        """Get ssh keys

        :param oid: ssh key id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = ""
        if oid is not None:
            try:
                uri = "/v1.0/gas/keys/%s" % oid
                res = self.invoke("ssh", uri, "GET", data, parse=True, silent=True)
                res = [res.get("key")]
            except BeehiveApiClientError as ex:
                # if ex.code == 404:
                #     res = []
                # else:
                raise
        else:
            uri = "/v1.0/gas/keys"
            res = self.invoke("ssh", uri, "GET", data, parse=True, silent=True)
            res = res.get("keys", [])

        for item in res:
            item.pop("__meta__")
            item.pop("priv_key")

        self.logger.debug("Get ssh keys %s: %s" % (oid, truncate(res)))
        return res

    def set_ssh_key_authorization(self, name, role, user=None, group=None):
        """Set ssh key authorization

        :param name: ssh key name
        :param role: ssh key role to assign
        :param user: user who receive authorization [optional]
        :param group: group who receive authorization [optional]
        :return: True
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        if user is not None:
            prefix = "user"
            entity = user
        elif group is not None:
            prefix = "group"
            entity = group
        else:
            self.logger.error("User or group must be specified")
            raise BeehiveApiClientError("User or group must be specified")
        data = {prefix: {"%s_id" % prefix: entity, "role": role}}
        uri = "/v1.0/gas/keys/%s/%ss" % (name, prefix)
        res = self.invoke("ssh", uri, "POST", data, parse=True, silent=True)
        self.logger.debug("Set authorization to ssh key %s for %s %s with role %s" % (name, prefix, entity, role))
        return res

    #
    # node user
    #
    def get_ssh_user(self, oid=None, node_id=None, username="root"):
        """Get ssh user

        :param oid: ssh user id, uuid or name [optional]
        :param node_id: node id [optional]
        :param username: username [default=root]
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        # get user
        user = None
        if oid is not None:
            uri = "/v1.0/gas/users/%s" % oid
            user = self.invoke("ssh", uri, "GET", "", parse=True, silent=True).get("user")
        else:
            uri = "/v1.0/gas/users"
            data = urlencode({"node_id": node_id, "username": username})
            res = self.invoke("ssh", uri, "GET", data, parse=True, silent=True).get("users")
            if len(res) > 0:
                user = res[0]  # get first user

        if user is None:
            self.logger.error("user not found: %s in node: %s" % (username, node_id))
            return None

        # user["username"]
        user["password"] = "xxx"  # after set password
        user["ssh_key_data"] = None
        self.logger.debug("Get ssh user %s: %s" % (oid, user))

        # get user password
        uri = "/v1.0/gas/users/%s/password" % user["id"]
        res = self.invoke("ssh", uri, "GET", "", parse=True, silent=True)
        password = res.get("password")
        user["password"] = password

        # get user ssh key
        key_id = user.get("key_id", None)
        if key_id is not None:
            uri = "/v1.0/gas/keys/%s" % key_id
            res = self.invoke("ssh", uri, "GET", "", parse=True, silent=True)
            key = res.get("key")
            user["ssh_key_data"] = b64decode(key.get("priv_key")).decode("utf-8")

        return user

    def add_ssh_user(self, node, user, key, password=""):
        """Add ssh node user

        :param node: node instance
        :param user: virtual machine user name
        :param key: ssh node user key
        :param password: ssh node user password
        :return: node uuid
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        user = {
            "name": "%s-%s" % (node.get("name"), user),
            "desc": user,
            "attribute": "",
            "node_id": node.get("uuid"),
            "key_id": key,
            "username": user,
            "password": password,
        }
        uri = "/v1.0/gas/users"
        node_user = self.invoke("ssh", uri, "POST", data={"user": user})
        self.logger.debug("Add ssh node %s user: %s" % (node.get("name"), node_user.get("uuid")))
        return node_user.get("uuid")

    def update_ssh_user(self, oid, password=None):
        """Update ssh node user

        :param node: node instance
        :param user: user id
        :param password: ssh node user password
        :return: node uuid
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        user = {"password": password}
        uri = "/v1.0/gas/users/%s" % oid
        node_user = self.invoke("ssh", uri, "PUT", data={"user": user})
        self.logger.debug("Update ssh node user %s" % oid)
        return node_user.get("uuid")

    def delete_ssh_user(self, oid):
        """Delete ssh node user

        :param oid: ssh node id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/gas/users/%s" % oid
        self.invoke("ssh", uri, "DELETE", "", parse=True, silent=True)
        self.logger.debug("Delete ssh node user %s" % oid)
        return True

    #
    # node
    #
    def get_ssh_node(self, oid):
        """Get ssh node

        :param oid: ssh node id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/gas/nodes/%s" % oid
        res = self.invoke("ssh", uri, "GET", "", parse=True, silent=True)
        res = res.get("node")
        self.logger.debug("Get ssh node %s: %s" % (oid, truncate(res)))
        return res

    def add_ssh_node(self, name, desc, ip_address, group, user, key, attribute="", password=""):
        """Add ssh node

        :param name: ssh node name
        :param desc: ssh node desc
        :param ip_address: ip_address
        :param group: ssh node group
        :param user: ssh node user
        :param key: ssh node user key
        :param password: ssh node user password
        :param attribute: ssh node attribute
        :return: node uuid
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        data = {
            "node": {
                "name": name,
                "desc": desc,
                "attribute": attribute,
                "group_id": group,
                "node_type": "user",
                "ip_address": ip_address,
            }
        }
        uri = "/v1.0/gas/nodes"
        res = self.invoke("ssh", uri, "POST", data, parse=True, silent=True)
        uuid = res.get("uuid")
        self.logger.debug("Add ssh node %s: %s" % (name, uuid))

        user = {
            "name": "%s-%s" % (name, user),
            "desc": user,
            "attribute": "",
            "node_id": uuid,
            "key_id": key,
            "username": user,
            "password": password,
        }
        uri = "/v1.0/gas/users"
        node_user = self.invoke("ssh", uri, "POST", data={"user": user})
        self.logger.debug("Add ssh node %s user: %s" % (name, node_user.get("uuid")))
        return uuid

    def delete_ssh_node(self, oid):
        """Delete ssh node

        :param oid: ssh node id, uuid or name
        :raises BeehiveApiClientError: raise :class:`BeehiveApiClientError`
        """
        uri = "/v1.0/gas/nodes/%s" % oid
        res = self.invoke("ssh", uri, "DELETE", "", parse=True, silent=True)
        self.logger.debug("Delete ssh node %s" % oid)

        return True
