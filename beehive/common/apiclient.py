'''
Created on Jan 12, 2017

@author: darkbk
'''
import ujson as json
import json as sjson
import httplib
from urllib import urlencode
from time import time
from logging import getLogger
from beecell.perf import watch
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Random import atfork
import binascii
from beecell.simple import truncate, id_gen
from socket import gethostname
from itertools import repeat
from multiprocessing import current_process
from base64 import b64encode
from beehive.common.jwtclient import JWTClient

class BeehiveApiClientError(Exception):
    def __init__(self, value, code=400):
        self.code = code
        self.value = value
        Exception.__init__(self, value, code)

    def __repr__(self):
        return u'BeehiveApiClientError: %s' % self.value 

    def __str__(self):
        return u'%s, %s' % (self.value, self.code)

class BeehiveApiClient(object):
    """Beehive api client.
    
    :param auth_endpoints: api main endpoints
    :param authtype: api authentication filter
    :param user: api user
    :param pwd: api user password
    :param catalog_id: api catalog id
    
    Use:
    
    .. code-block:: python
    
    
    """
    def __init__(self, auth_endpoints, authtype, user, pwd, catalog_id=None,
                 client_config=None):
        self.logger = getLogger(self.__class__.__module__+ \
                                '.'+self.__class__.__name__)
        
        #atfork()
        self.pid = current_process().ident
        
        if len(auth_endpoints) > 0: self.main_endpoint = auth_endpoints[0]
        else: self.main_endpoint = None
        self.endpoints = {u'auth':[]}
        self.endpoint_weights = {u'auth':[]}
        self.api_authtype = authtype # can be: simplehttp, oauth2, keyauth
        self.api_user = user
        self.api_user_pwd = pwd
        self.api_client_config = client_config
        
        self.catalog_id = catalog_id
        
        self.max_attempts = 3 # number of attempt to get a valid endpoint
        
        self.uid = None
        self.seckey = None
        self.filter = None
        
        self.host = gethostname()
        
        # auth reference - http://10.102.160.240:6060
        for endpoint in auth_endpoints:
            self.endpoints[u'auth'].append([self.__parse_endpoint(endpoint), 0])
        self.logger.debug(u'Get main auth endpoints: %s' % self.endpoints[u'auth'])
        
        # load catalog
        #self.load_catalog()
        
    def __parse_endpoint(self, endpoint_uri):
        """Parse endpoint http://10.102.160.240:6060
        
        :param endpoint: http://10.102.160.240:6060
        :return: {u'proto':.., u'host':.., u'port':..}
        :rtype: dict
        """
        try:
            t1 = endpoint_uri.split('://')
            t2 = t1[1].split(':')
            return {u'proto':t1[0], u'host':t2[0],  u'port':int(t2[1])}
        except Exception as ex:
            self.logger.error('Error parsing endpoint %s: %s' % 
                              (endpoint_uri, ex))  

    def endpoint(self, subsystem):
        """Select a subsystem endpoint from list
        """
        '''
        endpoints = sorted(self.endpoint_weights[subsystem])
        endpoints = list(map(lambda x: x-(self.weight_mean/2), endpoints))
        endpoints[0] += self.weight_mean/2
        return self.endpoints[subsystem][0]'''
        endpoints = None
        # if catalog does not contain subsystem reference, reload it
        try:
            endpoints = self.endpoints[subsystem]
        except:
            self.load_catalog()
            # if subsystem does not already exist return error
            try:
                endpoints = self.endpoints[subsystem]
            except:
                raise BeehiveApiClientError(u'Subsystem %s reference is empty' % 
                                            subsystem, code=404)
                
        # order endpoint by lower weight
        endpoints = sorted(endpoints, key=lambda weight: weight[1])
        
        # select endpoint that ping:True
        endpoint = endpoints[0]
        '''for attempt in range(0, self.max_attempts):
            if self.ping(endpoint=endpoint[0]) is True:
                break
            else:
                try:
                    # remove item from the list
                    endpoints.pop(0)
                    endpoint = endpoints[0]
                except:
                    self.logger.warn(u'No suitable %s endpoint are available. Reload catalog' % subsystem)
                    self.load_catalog()
                    # if subsystem does not already exist return error
                    try:
                        endpoints = self.endpoints[subsystem]
                    except:
                        raise BeehiveApiClientError(u'Subsystem %s reference is empty' % 
                                                    subsystem, code=404)'''
        
        # inc endpoint usage
        endpoint[1] += 1
        
        self.endpoints[subsystem] = endpoints
                
        return endpoint[0]

    def sign_request(self, seckey64, data):
        """Sign data using public/private key signature. Signature algorithm used is 
        RSA. Hash algorithm is SHA256.
        
        :param seckey64: secret key encoded in base64
        :parad data: data to sign
        :return: data signature
        :rtype: str 
        """
        try:
            if current_process().ident != self.pid:
                atfork()
            
            # import key
            seckey = binascii.a2b_base64(seckey64)
            key = RSA.importKey(seckey)
            
            # create data hash
            hash_data = SHA256.new(data)#.digest()
            #self.logger.debug('Get data: %s' % data)
            #self.logger.debug('Created hash: %s' % binascii.b2a_base64(hash_data.digest()))
        
            # sign data
            signer = PKCS1_v1_5.new(key)
            signature = signer.sign(hash_data)
            
            # encode signature in base64
            #signature64 = binascii.b2a_base64(signature)
            signature64 = binascii.b2a_hex(signature)
            
            return signature64
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise BeehiveApiClientError(u'Error signing data: %s' % data, code=401)

    '''
    @watch
    def get_identity(self, uid):
        """Get identity.

        :param uid: identity id
        :return: dictionary like
        
                 .. code-block:: python
        
                    {u'uid':..., 
                     u'user':..., 
                     u'timestamp':..., 
                     u'pubkey':..., 
                     u'seckey':...}

        :raise BeehiveApiClientError: Error
        """
        identity = self.api_manager.redis_manager.get(self.prefix + uid)
        if identity is not None:
            data = pickle.loads(identity)
            data['ttl'] = self.module.redis_manager.ttl(self.prefix + uid)
            self.logger.debug('Get identity %s from redis: %s' % (uid, data))           
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise BeehiveApiClientError("Identity %s doen't exist or is expired" % uid, code=1014)'''

    def http_client(self, proto, host, path, method, 
                          data=u'', headers={}, port=80, timeout=30):
        """Http client. Usage:
        
            res = http_client2('https', 'host1', '/api', 'POST',
                                port=443, data='', headers={})        
        
        :param proto: Request proto. Ex. http, https
        :param host: Request host. Ex. 10.102.90.30
        :param port: Request port. [default=80]
        :param path: Request path. Ex. /api/
        :param method: Request method. Ex. GET, POST, PUT, DELETE
        :param headers: Request headers. [default={}]. Ex.
        
                        {"Content-type": "application/x-www-form-urlencoded",
                         "Accept": "text/plain"}
                         
        :param data: Request data. [default={}]. Ex.
        
                        {'@number': 12524, '@type': 'issue', '@action': 'show'}
                       
        :param timeout: Request timeout. [default=30s]
        :raise BeehiveApiClientError:
        """
        try:
            # start time
            start = time()
            
            # append request-id to headers
            headers[u'request-id'] = id_gen()
            
            #self.logger.info(u'Send http %s to %s://%s:%s%s' % 
            #                 (method, proto, host, port, path))
            #self.logger.debug('Send headers: %s' % headers)
            if data.lower().find(u'password') < 0:
                send_data = data
            else:
                send_data = u'xxxxxxx'
            self.logger.info(u'Call: METHOD=%s, URI=%s://%s:%s%s, '\
                             u'HEADERS=%s, DATA=%s' % (method, proto, host, 
                             port, path, headers, send_data))

            # format curl string
            curl_url = [u'curl -k -v -S -X %s' % method]
            if data is not None and data != u'':
                curl_url.append(u"-d '%s'" % data)
                curl_url.append(u'-H "Content-Type: application/json"')
            if headers is not None:
                for header in headers.items():
                    curl_url.append(u'-H "%s: %s"' % header)
            curl_url.append(u'%s://%s:%s%s' % (proto, host, port, path))
            self.logger.debug(u' '.join(curl_url))
            
            if proto == u'http':
                conn = httplib.HTTPConnection(host, port, timeout=timeout)
            else:
                conn = httplib.HTTPSConnection(host, port, timeout=timeout)

            # get response
            conn.request(method, path, data, headers)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise BeehiveApiClientError(u'Service Unavailable', code=503)
        
        try:            
            response = conn.getresponse()
            content_type = response.getheader(u'content-type')            

            if response.status in [200, 201, 202, 400, 401, 403, 404, 405, 
                                   406, 408, 409, 415]:
                res = response.read()
                if content_type.find(u'application/json') >= 0:
                    res = json.loads(res)

                # insert for compliance with oauth2 error message
                if u'error' in res:
                    #res[u'status'] = u'error'
                    res[u'message'] = res[u'error_description']
                    res[u'description'] = res[u'error_description']
                    res[u'code'] = response.status
                    
            elif response.status in [204]:
                #res = {u'status':u'ok', u'code':204, u'response':None}
                res = {}
            elif response.status in [500]:
                #res = {u'status':u'error',u'code':500, u'msg':u'Internal Server Error'}
                res = {u'code':500, 
                       u'message':u'Internal Server Error',
                       u'description':u'Internal Server Error'}
            elif response.status in [501]:
                #res = {u'status':u'error',u'code':501, u'msg':u'Not Implemented'}
                res = {u'code':501, 
                       u'message':u'Not Implemented',
                       u'description':u'Not Implemented'}
            elif response.status in [503]:
                #res = {u'status':u'error',u'code':503, u'msg':u'Service Unavailable'}
                res = {u'code':503, 
                       u'message':u'Service Unavailable',
                       u'description':u'Service Unavailable'}
            conn.close()
        except Exception as ex:
            elapsed = time() - start
            self.logger.error(ex, exc_info=True)
            self.logger.info(u'Response: STATUS=%s, CONTENT-TYPE=%s, RES=%s, '\
                             u'ELAPSED=%s' % (response.status, content_type, 
                             truncate(res), elapsed))
            
            raise BeehiveApiClientError(ex, code=400)
            
        #if res.get(u'status', u'') == u'ok':
        if response.status in [200, 201, 202]:
            res[u'status'] = u'ok'
            elapsed = time() - start
            self.logger.info(u'Response: STATUS=%s, CONTENT-TYPE=%s, RES=%s, '\
                             u'ELAPSED=%s' % (response.status, content_type, 
                             truncate(res), elapsed))
        #elif res.get(u'status', u'') == u'error':
        else:
            self.logger.error(res[u'message'])
            raise BeehiveApiClientError(res[u'message'], code=int(res[u'code']))
        
        return res
    
    def send_request(self, subsystem, path, method, data='', 
                     uid=None, seckey=None, other_headers=None):
        """
        
        :raise BeehiveApiClientError:
        """
        # get identity
        #identity = self.api_manager.get_identity(uid)
        #seckey = identity['seckey']
        # create sign
        headers = {u'Accept':u'application/json'}
        if self.api_authtype == u'keyauth' and self.uid is not None:
            sign = self.sign_request(seckey, path)
            headers.update({u'uid':uid, u'sign':sign})
        elif self.api_authtype == u'oauth2' and self.uid is not None:
            headers.update({u'Authorization':u'Bearer %s' % uid})
        elif self.api_authtype == u'simplehttp':
            auth = b64encode(u'%s:%s' % (self.api_user, self.api_user_pwd))
            headers.update({u'Authorization':u'Basic %s' % auth})            
            
        if other_headers is not None:
            headers.update(other_headers)            
            
        # make request
        endpoint = self.endpoint(subsystem)
        proto = endpoint[u'proto']
        host = endpoint[u'host']
        port = endpoint[u'port']
        if method ==u'GET':
            path = u'%s?%s' % (path, data)
        res = self.http_client(proto, host, path, method,
                               port=port, data=data, headers=headers)
        return res
    
    '''
    @watch
    def get_api_doc(self, subsystem, path, method, data=u'', sync=True, 
                    title=u'', desc= u'', output={}):
        """Generate api documentation
        """
        doc = [
            '.. expand::',
            '   :method: %s' % method,
            '   :auth: true',
            '   :sync: %s' % sync,
            '   :uri: %s' % path,
            '   :title: %s' % title,
            '   :desc: %s' % desc,
            ''
        ]
        
        if data != u'':
            doc.extend([
                '   **Inputs**',
                '',
                '   .. code-block:: python',
                '',
            ])
            input = sjson.dumps(data, indent=2).split(u'\n')
            input = map(lambda x: u'      %s' % x, input)
            doc.extend(input)
        doc.extend([
            '   **Outputs**',
            '',
            '   .. code-block:: python',
            '',
            
        ])
        output = sjson.dumps(output, indent=2).split(u'\n')
        output = map(lambda x: u'      %s' % x, output)
        doc.extend(output)
        return u'\n'.join(doc)'''

    @watch    
    def invoke(self, subsystem, path, method, data=u'', other_headers=None,
               parse=False):
        """Make api request using subsystem internal admin user credentials.
        
        :param parse: if True check if data is dict and transform in json
                    else accept data as passed
        :parma debug: if True return curl syntax with result
        :raise BeehiveApiClientError:
        """
        #if self.uid is None or self.exist(self.uid) is False:
        #    self.create_token()
        
        try:
            if parse is True and isinstance(data, dict):
                data = json.dumps(data)
            res = self.send_request(subsystem, path, method, data, 
                                    self.uid, self.seckey, other_headers)
        except BeehiveApiClientError as ex:
            self.logger.error(u'Send request to %s using uid %s: %s, %s' % 
                              (path, self.uid, ex.value, ex.code))
            # Request is not authorized
            if ex.code in [401]:
                # try to get token and retry api call
                self.uid = None
                self.seckey = None
                self.create_token()
                res = self.send_request(subsystem, path, method, data, 
                                        self.uid, self.seckey, other_headers)
            else:
                raise
        
        #if res[u'status'] == u'error':
        #    self.logger.error(u'Send request to %s using uid %s: %s' % 
        #                      (path, self.uid, res[u'msg']))
        #    raise BeehiveApiClientError(res[u'msg'], code=res[u'code'])
        #else:
        self.logger.info(u'Send request to %s using uid %s' % (path, self.uid))
        return res
        #return res[u'response']
    
    #
    # authentication request
    #
    @watch
    def ping(self, subsystem=None, endpoint=None):
        """Ping instance
        
        :param subsystem: subsystem to ping [optional]
        :param endpoint: endpoint to ping [optional]
        :return: if set endpoint return True or False. If set subsystem return 
                 list of all the endpoint with ping status
        """
        # make request
        res = []
        if endpoint is not None:
            if not isinstance(endpoint, dict):
                endpoint = self.__parse_endpoint(endpoint)
            proto = endpoint[u'proto']
            host = endpoint[u'host']
            port = endpoint[u'port']
            try:
                resp = self.http_client(proto, host, u'/v1.0/server/ping/', u'GET',
                                        port=port, data=u'', timeout=0.5)
                if resp[u'status'] == u'ok':
                    res = True
                else:
                    res = False
            except BeehiveApiClientError as ex:
                if ex.code in [500, 501, 503]:
                    res = False
        elif subsystem is not None:
            for endpoint in self.endpoints[subsystem]:
                try:
                    endpoint = endpoint[0]
                    proto = endpoint[u'proto']
                    host = endpoint[u'host']
                    port = endpoint[u'port']
                    resp = self.http_client(proto, host, u'/v1.0/server/ping/', u'GET',
                                            port=port, data=u'', timeout=0.5)
                    if resp[u'status'] == u'ok':
                        res.append([endpoint, True])
                    else:
                        res.append([endpoint, False])
                except BeehiveApiClientError as ex:
                    if ex.code in [500, 501, 503]:
                        res.append([endpoint, False])                 
        return res 
    
    def load_catalog(self, catalog_id=None):
        """Load catalog endpoint
        """
        if catalog_id is not None:
            self.catalog_id = catalog_id
            
        if self.catalog_id is not None:
            # load catalog endpoints
            catalog = self.get_catalog(self.catalog_id)
            endpoints = catalog[u'services']
            #endpoints.pop(u'auth')
            for service, uris in endpoints.items():
                for uri in uris:
                    try:
                        self.endpoints[service].append([self.__parse_endpoint(uri), 0])
                    except:
                        self.endpoints[service] = [[self.__parse_endpoint(uri), 0]]
        else:
            raise BeehiveApiClientError(u'Catalog id is undefined')
        
    def set_catalog_endpoint(self, service, endpoint, append=False):
        """Set new service endpoint manually
        
        :param subsystem:
        :parma endpoint: 
        """
        if append is True:
            self.endpoints[service].append([self.__parse_endpoint(endpoint), 0])
        else:
            self.endpoints[service] = [[self.__parse_endpoint(endpoint), 0]]
    
    @watch
    def simplehttp_login(self, api_user=None, api_user_pwd=None, login_ip=None):
        """Login module internal user using simple http authentication
        
        :raise BeehiveApiClientError:
        """
        if api_user == None: api_user = self.api_user
        if api_user_pwd == None: api_user_pwd = self.api_user_pwd            
        
        data = {u'user':api_user, u'password':api_user_pwd}
        if login_ip is None:
            data[u'login-ip'] = self.host
        else:
            data[u'login-ip'] = login_ip
        res = self.send_request(u'auth', u'/v1.0/simplehttp/login/', 
                                u'POST', data=json.dumps(data))
        #res = res[u'response']
        self.logger.info(u'Login user %s: %s' % (self.api_user, res[u'uid']))
        self.uid = None
        self.seckey = None
        self.filter = u'simplehttp'
        
        return res
    
    @watch
    def create_token(self, api_user=None, api_user_pwd=None, login_ip=None):
        """Login module internal user
        
        :raise BeehiveApiClientError:
        """
        res = None
        if api_user == None: api_user = self.api_user
        if api_user_pwd == None: api_user_pwd = self.api_user_pwd            
        
        if self.api_authtype == u'keyauth':
            data = {u'user':api_user, u'password':api_user_pwd}
            if login_ip is None:
                data[u'login-ip'] = self.host
            else:
                data[u'login-ip'] = login_ip
            res = self.send_request(u'auth', u'/v1.0/keyauth/token/', 
                                    u'POST', data=json.dumps(data))
            #res = res[u'response']
            self.logger.info(u'Login user %s with token: %s' % 
                             (self.api_user, res[u'access_token']))
            self.uid = res[u'access_token']
            self.seckey = res[u'seckey']
            #self.filter = u'keyauth'
        elif self.api_authtype == u'oauth2':
            # get client
            client_id = self.api_client_config[u'uuid']
            client_email = self.api_client_config[u'client_email']
            client_scope = self.api_client_config[u'scopes']
            private_key = binascii.a2b_base64(self.api_client_config[u'private_key'])
            client_token_uri = u'%s/v1.0/oauth2/token/' % self.main_endpoint
            aud = self.api_client_config[u'aud']

            res = JWTClient.create_token(client_id, client_email, client_scope, 
                                         private_key, client_token_uri, aud, 
                                         api_user, api_user_pwd)
            self.uid = res[u'access_token']
        
        self.logger.debug(u'Get %s token: %s' % (self.api_authtype, self.uid))
        return res

    @watch
    def logout(self, uid=None, seckey=None):
        """
        :raise BeehiveApiClientError:
        """
        if uid == None: uid = self.uid
        if seckey == None: seckey = self.seckey            
                    
        res = self.send_request(u'auth', u'/v1.0/keyauth/logout/', 
                                u'POST', data=u'', uid=uid, seckey=seckey)
        self.uid = None
        self.seckey = None
        self.filter = None
        self.logger.info(u'Logout user %s with uid: %s' % (self.api_user, self.uid))    
    
    @watch
    def exist(self, uid):
        """Verify if identity exists
        
        :raise BeehiveApiClientError:
        """
        try:
            res = self.send_request(
                u'auth', u'/v1.0/auth/tokens/%s/exist/' % uid, 
                u'GET', data=u'', uid=self.uid, seckey=self.seckey)
            return True
        except BeehiveApiClientError as ex:
            if ex.code == 401:
                return False

    #
    # configuration
    #
    def get_configuration(self, app_id, uid=None, seckey=None):
        """Get configuration
        
        :param app_id: id used to get configuration. Default is portal
        """
        res = self.invoke(u'auth', u'/api/config/%s/',
                          u'GET', u'')
        self.logger.debug(u'Get configuration from beehive')
        return res    

    #
    # configuration
    #
    def register_to_monitor(self, name, desc, conn, uid=None, seckey=None):
        """Register system in monitor"""
        data = {
            u'node':{
                u'name':name,
                u'desc':desc,
                u'type':u'portal',
                u'conn':conn,
                u'refresh':u'dynamic'
            }
        }
        res = self.invoke(u'monitor', u'/v1.0/monitor/node/',
                          u'POST', json.dumps(data))        
        self.logger.debug(u'Register in monitor')
        return res 

    #
    # catalog request
    #
    def get_catalogs(self, uid=None, seckey=None):
        """Get catalogs
        
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        res = self.invoke(u'auth', u'/v1.0/catalogs/', 
                          u'GET', u'')[u'catalogs']
        self.logger.debug(u'Get catalogs')
        return res
    
    def get_catalog(self, catalog_id, uid=None, seckey=None):
        """Get catalogs
        
        :param catalog_id: id of the catalog
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        res = self.invoke(u'auth', u'/v1.0/catalog/%s/' % catalog_id, 
                          u'GET', u'')[u'catalog']
        self.logger.debug(u'Get catalog %s' % catalog_id)
        return res
    
    def create_catalog(self, name, zone, uid=None, seckey=None):
        """Create catalogs
        
        :param name: catalog name
        :param zone: catalog zone
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        data = {
            u'catalog':{
                u'name':name, 
                u'desc':u'catalog %s' % name,
                u'zone':zone                        
            }
        }
        uri = u'/v1.0/catalog/'        
        res = self.invoke(u'auth', uri, u'POST', json.dumps(data))
        self.logger.debug(u'Create catalog %s' % name)
        return res
    
    def delete_catalog(self, catalog_id, uid=None, seckey=None):
        """Delete catalogs
        
        :param catalog_id: id of the catalog
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        uri = u'/v1.0/catalog/%s/' % catalog_id        
        self.invoke(u'auth', uri, u'DELETE', u'')
        self.logger.debug(u'Delete catalog %s' % catalog_id)   

    #
    # endpoint request
    #
    def get_endpoints(self, uid=None, seckey=None):
        """Get endpoints
        
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        res = self.invoke(u'auth', u'/v1.0/catalog/endpoints/', u'GET', u'')
        self.logger.debug(u'Get endpoints')
        return res
    
    def get_endpoint(self, endpoint_id, uid=None, seckey=None):
        """Get endpoints
        
        :param endpoint_id: id of the endpoint
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        res = self.invoke(u'auth', u'/v1.0/catalog/endpoint/%s/' % endpoint_id, u'GET', u'')
        self.logger.debug(u'Get endpoint %s' % endpoint_id)
        return res
    
    def create_endpoint(self, catalog_id, name, service, uri, 
                        uid=None, seckey=None):
        """Create endpoints
        
        :param catalog_id: id of the catalog
        :param name: endpoint name
        :param service: endpoint service
        :param uri: endpoint uri
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        data = {
            u'endpoint':{
                u'catalog':catalog_id,
                u'name':name, 
                u'desc':u'Endpoint %s' % name, 
                u'service':service, 
                u'uri':uri, 
                u'enabled':True                   
            }
        }
        uri = u'/v1.0/catalog/endpoint/'        
        res = self.invoke(u'auth', uri, u'POST', json.dumps(data))
        self.logger.debug(u'Create endpoint %s' % name)
        return res
    
    def update_endpoint(self, oid, catalog_id=None, 
                        name=None, service=None, uri=None, 
                        uid=None, seckey=None):
        """Update endpoints
        
        :param oid: endpoint id/name
        :param catalog_id: id of the catalog
        :param new_name: endpoint name
        :param service: endpoint service
        :param uri: endpoint uri
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        data = {}
        if catalog_id is not None:
            data[u'catalog'] = catalog_id
        if name is not None:
            data[u'name'] = name
        if service is not None:
            data[u'service'] = service
        if uri is not None:
            data[u'uri'] = uri
            
        data = {
            u'endpoint':data
        }
        uri = u'/v1.0/catalog/endpoint/%s/' % oid        
        res = self.invoke(u'auth', uri, u'PUT', json.dumps(data))
        self.logger.debug(u'Create endpoint %s' % name)
        return res    
    
    def delete_endpoint(self, endpoint_id, uid=None, seckey=None):
        """Delete endpoints
        
        :param endpoint_id: id of the endpoint
        :param uid: identity id
        :param seckey: identity secret key
        :return: 
        :raise BeehiveApiClientError:
        """
        uri = u'/v1.0/catalog/endpoint/%s/' % endpoint_id        
        self.invoke(u'auth', uri, u'DELETE', u'')
        self.logger.debug(u'Delete endpoint %s' % endpoint_id) 

    #
    # authorization request
    #    
    def add_object_types(self, objtype, objdef, uid=None, seckey=None):
        """Add authorization object type
        
        :param uid: identity id
        :param seckey: identity secret key
        :param objtype: object type
        :param objdef: object definition
        :raise BeehiveApiClientError:
        """
        #data = json.dumps([(objtype, objdef, class_name)])
        #res = self.invoke(u'auth', '/api/auth/object/type/', 'POST', data)
        data = {
            u'object-types':[
                {
                    u'subsystem':objtype,
                    u'type':objdef
                }
            ]
        }
        res = self.invoke(u'auth', u'/v1.0/auth/objects/types/', 
                          u'POST', data, parse=True)        
        self.logger.debug(u'Add object type: %s:%s' % (objtype, objdef))
        return res
    
    def add_object(self, objtype, objdef, objid, desc,
                   uid=None, seckey=None):
        """Add authorization object with all related permissions
        
        :param uid: identity id [optional]
        :param seckey: identity secret key [optional]
        :param objtype: object type
        :param objdef: object definition
        :param objid: object id
        :param desc: object description
        :raise BeehiveApiClientError:
        """
        try:
            #data = json.dumps([(objtype, objdef, objid, desc)])
            #res = self.invoke(u'auth', u'/api/auth/object/', u'POST', data)
            data = {
                u'objects':[
                    {
                        u'subsystem':objtype,
                        u'type':objdef,
                        u'objid':objid,
                        u'desc':desc
                    }
                ]
            }
            res = self.invoke(u'auth', u'/v1.0/auth/objects/', u'POST', 
                              data, parse=True)            
            self.logger.debug(u'Add object: %s:%s %s' % 
                              (objtype, objdef, objid))
            return res
        except BeehiveApiClientError as ex:
            if ex.code == 409:
                pass
            else:
                raise
    
    def remove_object(self, objtype, objdef, objid,
                      uid=None, seckey=None):
        """Remove authorization object with all related permissions
        
        :raise BeehiveApiClientError:
        """
        # get object
        try:
            #data = ''
            #uri = u'/api/auth/object/T:%s/D:%s/I:%s/' % (objtype, objdef, 
            #                                            objid.replace(u'//', u'_'))
            data = urlencode({u'subsystem':objtype,
                              u'type':objdef,
                              u'objid':objid})
            uri = u'/v1.0/auth/objects/'           
            res = self.invoke(u'auth', uri, u'GET', data, parse=True).get(u'objects')
        except:
            self.logger.warn(u'Object %s:%s can not be removed' % (objdef, objid))
            return False
        
        if len(res) <= 0:
            self.logger.warn(u'Object %s:%s can not be removed' % (objdef, objid))
            return False            
        
        # remove object
        #uri = u'/api/auth/object/%s/' % res[0][0]
        uri = u'/v1.0/auth/objects/%s/' % res[0][u'id']
        res = self.invoke(u'auth', uri, u'DELETE', data, parse=True)
        self.logger.debug(u'Remove object: %s:%s %s' % (objtype, objdef, objid))
        return res

    def get_permissions2(self, objtype, objdef, objid, uid=None, seckey=None):
        """Get object permissions
        
        :raise BeehiveApiClientError:
        """
        data = ''
        objid = objid.replace(u'//', u'_')
        uri = u'/api/auth/object/perm/T:%s+D:%s+I:%s/' % (objtype, objdef, objid)
        res = self.invoke(u'auth', uri, 'GET', data)
        self.logger.debug(u'Get permission : %s:%s %s' % (objtype, objdef, objid))
        return res
    
    def get_permissions(self, objtype, objdef, objid, uid=None, seckey=None):
        """Get object permissions
        
        :raise BeehiveApiClientError:
        """
        data = urlencode({u'subsystem':objtype,
                          u'type':objdef,
                          u'objid':objid, 
                          u'size':1000})
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data, parse=True)
        self.logger.debug(u'Get permission : %s:%s %s' % (objtype, objdef, objid))
        return res.get(u'perms', [])

    def append_role_permissions(self, role, objtype, objdef, objid, objaction,
                                uid=None, seckey=None):
        """Append permission to role
        
        :raise BeehiveApiClientError:
        """
        # data = json.dumps({"perm":{"append":[(0, 0, objtype, objdef, "", 
        #                                       objid, 0, objaction)], 
        #                           "remove":[]}})
        #uri = u'/api/auth/role/%s/' % role
        data = {
            u'role':{
                u'perms':{
                    u'append':[(0, 0, objtype, objdef, objid, 0, objaction)],
                    u'remove':[]
                }
            }
        }
        uri = u'/v1.0/auth/roles/%s/' % role
        res = self.invoke(u'auth', uri, u'PUT', data, parse=True)
        self.logger.debug(u'Append permission %s:%s %s %s to role %s' % 
                          (objtype, objdef, objid, objaction, role))
        return res
    
    def get_role(self, name):
        """Get role
        
        :raise BeehiveApiClientError:
        """
        #uri = u'/api/auth/role/%s/' % name
        uri = u'/v1.0/auth/roles/%s/' % name
        res = self.invoke(u'auth', uri, u'GET', u'')
        self.logger.debug('Get role: %s' % name)
        return res    
    
    def add_role(self, name, desc, uid=None, seckey=None):
        """Add role
        
        :raise BeehiveApiClientError:
        """
        #data = json.dumps({"name":name, "description":desc})
        #uri = u'/api/auth/role/'
        data = {
            u'role':{
                u'name':name,
                u'desc':desc
            }
        }
        uri = u'/v1.0/auth/roles/'        
        res = self.invoke(u'auth', uri, u'POST', data, parse=True)
        self.logger.debug('Add role: %s' % str(name))
        return res

    def remove_role(self, oid, uid=None, seckey=None):
        """Remove role
        
        :raise BeehiveApiClientError:
        """
        data = ''
        #uri = u'/api/auth/role/%s/' % oid
        uri = u'/v1.0/auth/roles/%s/' % oid
        res = self.invoke(u'auth', uri, u'DELETE', data, parse=True)
        self.logger.debug(u'Remove role: %s' % oid)
        return res
    
    def get_user(self, name):
        """Get user
        
        :raise BeehiveApiClientError:
        """
        uri = u'/v1.0/auth/users/%s/' % name
        res = self.invoke(u'auth', uri, u'GET', '', parse=True)
        self.logger.debug(u'Get user: %s' % name)
        return res
    
    def get_user_perms(self, name):
        """Get user permissions
        
        :raise BeehiveApiClientError:
        """
        data = urlencode({u'user':name,
                          u'size':1000})
        uri = u'/v1.0/auth/objects/perms/'
        res = self.invoke(u'auth', uri, u'GET', data, parse=True)
        self.logger.debug(u'Get user %s permission : %s' % (name, truncate(res)))
        return res.get(u'perms', [])
    
    def add_user(self, name, password, description, storetype=u'DBUSER',
                 uid=None, seckey=None):
        """Add user
        
        :raise BeehiveApiClientError:
        """
        data = {
            u'user':{
                u'anme':name,
                u'password':password,
                u'desc':description, 
                u'system':False,
                u'storetype':storetype,
                u'systype':u'USER',
                u'active':True
            }
        } 
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'POST', data, parse=True)
        self.logger.debug(u'Add system user: %s' % str(name))
        return res    
    
    def add_system_user(self, name, password, description, uid=None, seckey=None):
        """Add system user
        
        :raise BeehiveApiClientError:
        """
        data = {
            u'user':{
                u'name':name,
                u'password':password,
                u'desc':description, 
                u'system':True
            }
        } 
        uri = u'/v1.0/auth/users/'
        res = self.invoke(u'auth', uri, u'POST', data, parse=True)
        self.logger.debug(u'Add system user: %s' % str(name))
        return res
    
    def update_user(self, name, new_name, new_pwd, new_desc, 
                    uid=None, seckey=None):
        """Update user
        
        :raise BeehiveApiClientError:
        """
        data = {
            u'user':{
                u'name':new_name,
                u'password':new_pwd,
                u'desc':new_desc,
            }
        } 
        uri = u'/v1.0/auth/users/%s/' % name
        res = self.invoke(u'auth', uri, u'PUT', data, parse=True)
        self.logger.debug(u'Update user: %s' % str(name))
        return res
    
    def remove_user(self, oid, uid=None, seckey=None):
        """Remove user
        
        :raise BeehiveApiClientError:
        """
        uri = u'/v1.0/auth/users/%s/' % oid
        res = self.invoke(u'auth', uri, u'DELETE', u'')
        self.logger.debug(u'Remove user: %s' % str(oid))
        return res
    
    def append_user_roles(self, oid, roles, uid=None, seckey=None):
        """Append roles to user
        
        :raise BeehiveApiClientError:
        """
        data = {
            u'user':{
                u'roles':{
                    u'append':roles,
                    u'remove':[]
                },
            }
        }        
        uri = u'/v1.0/auth/users/%s/' % oid
        res = self.invoke(u'auth', uri, u'PUT', data, parse=True)
        self.logger.debug(u'Append roles %s to user %s' % (roles, oid))
        return res    
    