'''
Created on Jun 8, 2017

@author: darkbk
'''
import binascii
import pickle
import ujson as json
from logging import getLogger
from beecell.auth import AuthError
#from beecell.perf import watch
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject,\
    ApiEvent, ApiInternalEvent, ApiInternalObject
from beehive.common.model.authorization import AuthDbManager
from beecell.db import QueryError, TransactionError
from ipaddress import IPv4Address, IPv4Network
from beecell.simple import truncate, str2uni, id_gen, token_gen
from beehive.common.data import operation, trace
from socket import gethostbyname
from zlib import compress
from datetime import datetime, timedelta
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class AuthenticationManager(object):
    """Manager used to login and logout user on authentication provider.
    
    """
    def __init__(self, auth_providers):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)        
        
        self.auth_providers = auth_providers

    def __str__(self):
        return "<AuthenticationManager id:%s>" % id(self)

    def login(self, username, password, domain, ipaddr):
        """Login user using ldap server.
        
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug(u'Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug(u'Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error(u'Authentication domain %s does not exist' % domain)
            raise AuthError(u'', u'Authentication domain %s does not exist' % domain, 
                            code=10)
        
        # login over authentication provider and get user attributes
        username = u'%s@%s' % (username, domain)

        auth_user = auth_provider.login(username, password)

        # set user ip address
        auth_user.current_login_ip = ipaddr
        
        self.logger.debug(u'Login user: %s' % (username))
        return auth_user
    
    def refresh(self, uid, username, domain):
        """Refresh user.
        
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug(u'Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug(u'Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error(u'Authentication domain %s does not exist' % domain)
            raise AuthError(u'', u'Authentication domain %s does not exist' % domain, 
                            code=10)
        
        # login over authentication provider and get user attributes
        username = u'%s@%s' % (username, domain)
        auth_user = auth_provider.refresh(username, uid)
        
        self.logger.debug(u'Login user: %s' % (username))
        return auth_user   

class BaseAuthController(ApiController):
    """Auth Module base controller.
    
    :param module: Beehive module
    """
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.manager = AuthDbManager()
    
    '''
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        # init container
        for child in self.child_classes:
            child(self).init_object()'''
    
    def set_superadmin_permissions(self):
        """ """
        try:
            self.set_admin_permissions(u'ApiSuperadmin', [])
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    def set_admin_permissions(self, role_name, args):
        """ """
        try:
            for item in self.child_classes:
                item(self).set_admin_permissions(role_name, args)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple ahttp credentials.
        
        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        :raise ApiManagerError:
        """
        name, domain = user.split(u'@')
        identity = self.simple_http_login(name, domain, pwd, user_ip)

        return identity
    
    #
    # identity manipulation methods
    #
    @trace(entity=u'Token', op=u'insert')
    def set_identity(self, uid, identity, expire=True, expire_time=None):
        """Set beehive identity with token uid
        
        :param uid: authorization token
        :param identity: dictionary with login identity
        :param expire: if True identity key expire after xx seconds
        :param expire_time: [optional] det expire time in seconds
        """
        #self.check_authorization(Token.objtype, Token.objdef, u'*', u'insert')
        
        if expire_time is None:
            expire_time = self.expire
        val = pickle.dumps(identity)
        self.module.redis_manager.setex(self.prefix + uid, expire_time, val)
        if expire is False:
            self.module.redis_manager.persist(self.prefix + uid)
        self.logger.info(u'Set identity %s in redis' % uid)
        #User(self).send_event(u'identity.insert', params={u'uid':uid})
    
    @trace(entity=u'Token', op=u'delete')
    def remove_identity(self, uid):
        """Remove beehive identity with token uid
        
        :param uid: authorization token
        """
        self.check_authorization(Token.objtype, Token.objdef, u'*', u'delete')
        
        if self.module.redis_manager.get(self.prefix + uid) is None:
            err = u'Identity %s does not exist' % uid
            User(self).send_event(u'identity.delete', params={u'uid':uid}, 
                                  exception=err)
            self.logger.error(err)
            raise ApiManagerError(err, code=404)            
        
        try:
            self.module.redis_manager.delete(self.prefix + uid)
            self.logger.debug(u'Remove identity %s from redis' % uid)
            #User(self).send_event(u'identity.delete', params={u'uid':uid})      
            return uid
        except Exception as ex:
            err = u'Can not remove identity %s' % uid
            #User(self).send_event(u'identity.delete', params={u'uid':uid}, 
            #                      exception=err)  
            self.logger.error(err)
            raise ApiManagerError(err, code=400)       

    @trace(entity=u'Token', op=u'view')
    def exist_identity(self, uid):
        """Verify identity exists
        
        :return: True or False
        :rtype: bool
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.warn(u'Identity %s retrieve error: %s' % (uid, ex))
            return False
        
        if identity is not None:
            self.logger.debug(u'Identity %s exists' % (uid))           
            return True
        else:
            self.logger.warn(u'Identity does not %s exists' % (uid))           
            return False

    @trace(entity=u'Token', op=u'view')
    def get_identity(self, uid):
        """Get identity
        
        :return: {u'uid':..., u'user':..., u'timestamp':..., u'pubkey':..., 
                  'seckey':...}
        :rtype: dict
        """
        #self.check_authorization(Token.objtype, Token.objdef, u'*', u'view')
        
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error(u'Identity %s retrieve error: %s' % (uid, ex))
            raise ApiManagerError(u'Identity %s retrieve error' % uid, code=404)
            
        if identity is not None:
            data = pickle.loads(identity)
            data[u'ttl'] = self.module.redis_manager.ttl(self.prefix + uid)
            #User(self).send_event(u'identity.get', params={u'uid':uid})
            self.logger.debug(u'Get identity %s from redis: %s' % 
                              (uid, truncate(data)))   
            return data
        else:
            self.logger.error(u'Identity %s does not exist or is expired' % uid)
            raise ApiManagerError(u'Identity %s does not exist or is '\
                                  u'expired' % uid, code=404)

    @trace(entity=u'Token', op=u'view')
    def get_identities(self):
        """Get list of active identities
        """
        self.check_authorization(Token.objtype, Token.objdef, u'*', u'view')
        
        try:
            res =  []
            for key in self.module.redis_manager.keys(self.prefix+'*'):
                identity = self.module.redis_manager.get(key)
                data = pickle.loads(identity)
                data[u'ttl'] = self.module.redis_manager.ttl(key)
                res.append(data)
        except Exception as ex:
            self.logger.error(u'No identities found: %s' % ex)
            raise ApiManagerError(u'No identities found')
        
        #User(self).send_event(u'identity.view', params={}) 
        self.logger.debug(u'Get identities from redis: %s' % truncate(res))
        return res    
    
    #
    # base inner login
    #
    @trace(entity=u'Token', op=u'login.params.insert')
    def validate_login_params(self, name, domain, password, login_ip):
        """Validate main login params.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        
        :raise ApiManagerError:        
        """
        if domain is None:
            domain = u'local'    
    
        # set user in thread local variable
        operation.user = (u'%s@%s' % (name, domain), login_ip, None)    
    
        # Validate input data and login user
        try:
            if name.strip() == u'':
                msg = u'Username is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if password.strip() == u'':
                msg = u'Password is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if domain.strip() == u'':
                msg = u'Domain is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            
            try:
                login_ip = gethostbyname(login_ip)
                IPv4Address(str2uni(login_ip))
            except Exception as ex:
                msg = u'Ip address is not provided or syntax is wrong'
                self.logger.error(msg, exc_info=1)
                raise ApiManagerError(msg, code=400)
            
            self.logger.debug(u'User %s@%s:%s validated' % 
                              (name, domain, login_ip))        
        except ApiManagerError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
    
    @trace(entity=u'Token', op=u'login.check.insert')
    def check_login_user(self, name, domain, password, login_ip):
        """Simple http authentication login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        
        :return: database user instance, user attributes as dict
        :raise ApiManagerError:        
        """
        # verify user exists in beehive database
        try:
            user_name = u'%s@%s' % (name, domain)
            dbuser = self.manager.get_users(name=user_name)[0][0]
            # get user attributes
            dbuser_attribs = {a.name:(a.value, a.desc) for a in dbuser.attrib}
        except (QueryError, Exception) as ex:
            msg = u'User %s does not exist' % user_name
            self.logger.error(msg, exc_info=1)
            raise ApiManagerError(msg, code=404)
        
        self.logger.debug(u'User %s exists' % user_name)
        
        return dbuser, dbuser_attribs   
    
    @trace(entity=u'Token', op=u'login.base.insert')
    def base_login(self, name, domain, password, login_ip, 
                     dbuser, dbuser_attribs):
        """Base login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param dbuser: database user instance
        :param dbuser_attribs: user attributes as dict
        :return: SystemUser instance, user attributes as dict
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }        
        
        # login user
        try:
            user = self.module.authentication_manager.login(name, password, 
                                                            domain, login_ip)
        except (AuthError) as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)
        
        self.logger.info(u'Login user: %s' % user)
        
        # append attributes, roles and perms to SystemUser
        try:
            # set user attributes
            #self.__set_user_attribs(user, dbuser_attribs)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
        except QueryError as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)
        
        return user, dbuser_attribs
    
    def __set_user_attribs(self, user, attribs):
        """Set user attributes"""
        user.set_attributes(attribs)
    
    def __set_user_perms(self, dbuser, user):
        """Set user permissions """
        #perms = self.manager.get_user_permissions2(dbuser)
        perms = self.manager.get_login_permissions(dbuser)
        compress_perms = binascii.b2a_base64(compress(json.dumps(perms)))
        user.set_perms(compress_perms)
        #user.set_perms(perms)
    
    def __set_user_roles(self, dbuser, user):
        """Set user roles """    
        roles, total = self.manager.get_user_roles(dbuser)
        user.set_roles([r.name for r in roles])      
    
    #
    # simple http login
    #
    @trace(entity=u'Token', op=u'login.simple.insert')
    def simple_http_login(self, name, domain, password, login_ip):
        """Simple http authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }
        user_name = u'%s@%s' % (name, domain)
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            #User(self).send_event(u'simplehttp.login.insert', params=opts, 
            #                      exception=ex)
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                       password, login_ip)
        except ApiManagerError as ex:
            #User(self).send_event(u'simplehttp.login.insert', params=opts, 
            #                      exception=ex)
            raise
        
        # check user has authentication filter
        auth_filters = dbuser_attribs.get(u'auth-filters', (u'', None))[0].split(u',')
        if u'simplehttp' not in auth_filters:
            msg = u'Simple http authentication is not allowed for user %s' % \
                  user_name
            #User(self).send_event(u'simplehttp.login.insert', params=opts, 
            #                      exception=msg)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)
        
        # check user ip is in allowed cidr
        auth_cidrs = dbuser_attribs.get(u'auth-cidrs', u'')[0].split(u',')
        allowed = False
        for auth_cidr in auth_cidrs:
            allowed_cidr = IPv4Network(str2uni(auth_cidr))
            user_ip = IPv4Network(u'%s/32' % login_ip)
            if user_ip.overlaps(allowed_cidr) is True:
                allowed = True
                break
        
        if allowed is False:
            msg = u'User %s ip %s can not perform simple http authentication' % \
                  (user_name, login_ip)
            #User(self).send_event(u'simplehttp.login.insert', params=opts, 
            #                      exception=msg)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)            
        
        # login user
        try:
            user, attrib = self.base_login(name, domain, password, login_ip, 
                                           dbuser, dbuser_attribs)
        except ApiManagerError as ex:
            #User(self).send_event(u'simplehttp.login.insert', params=opts, 
            #                      exception=ex)
            raise
        
        res = {u'uid':id_gen(20),
               u'type':u'simplehttp',
               u'user':user.get_dict(),
               u'timestamp':datetime.now().strftime(u'%y-%m-%d-%H-%M')}        
    
        #User(self).send_event(u'simplehttp.login.insert', params=opts)
        
        return res
    
    #
    # keyauth login, logout, refresh_user
    #
    #@trace(entity=u'Token', op=u'login.key.insert')
    def gen_authorizaion_key(self, user, domain, name, login_ip, attrib):
        '''Generate asymmetric key for keyauth filter.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param attrib: user attributes
        
        :raise ApiManagerError: 
        '''
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }
        user_name = u'%s@%s' % (name, domain) 
        
        try:
            #uid = id_gen(20)
            uid = token_gen()
            timestamp = datetime.now()#.strftime(u'%H-%M_%d-%m-%Y')     
            private_key = rsa.generate_private_key(public_exponent=65537,
                                                   key_size=1024,
                                                   backend=default_backend())        
            public_key = private_key.public_key()
            pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo)    
            pubkey = binascii.b2a_base64(pem)
            pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL, 
                        encryption_algorithm=serialization.NoEncryption())    
            seckey = binascii.b2a_base64(pem)
            
            # create identity
            identity = {u'uid':uid,
                        u'type':u'keyauth',
                        u'user':user.get_dict(),
                        u'timestamp':timestamp,
                        u'ip':login_ip,
                        u'pubkey':pubkey,
                        u'seckey':seckey}
            self.logger.debug(u'Create user %s identity: %s' % 
                              (user_name, truncate(identity)))
            operation.user = (user_name, login_ip, uid)
            
            # save identity in redis
            expire = True
            if attrib[u'sys_type'][0] == u'SYS':
                self.logger.debug(u'Login system user')
                #expire = False
            self.set_identity(uid, identity, expire=expire)

            res = {
                u'token_type':u'Bearer',
                u'user':user.get_dict().get(u'id'),
                u'access_token':uid,
                u'pubkey':pubkey,
                u'seckey':seckey,
                u'expires_in':self.expire,
                u'expires_at':timestamp+timedelta(seconds=self.expire),
            }  
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=401)            
        
        return res    
    
    @trace(entity=u'Token', op=u'login.keyauth.insert')
    def login(self, name, domain, password, login_ip):
        """Asymmetric keys authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raise ApiManagerError:
        """
        opts = {
            u'name':name, 
            u'domain':domain, 
            u'password':u'xxxxxxx', 
            u'login_ip':login_ip
        }        
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            #User(self).send_event(u'keyauth.token.insert', params=opts, 
            #                      exception=ex)
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                       password, login_ip)
        except ApiManagerError as ex:
            #User(self).send_event(u'keyauth.token.insert', params=opts, 
            #                      exception=ex)
            raise     
        
        # check user attributes
        
        # login user
        try:
            user, attrib = self.base_login(name, domain, password, login_ip, 
                                           dbuser, dbuser_attribs)
        except ApiManagerError as ex:
            raise
            #User(self).send_event(u'keyauth.token.insert', params=opts, 
            #                      exception=ex)
        
        # generate asymmetric keys
        res = self.gen_authorizaion_key(user, domain, name, login_ip, attrib)

        #User(self).send_event(u'keyauth.token.insert', params=opts)
        
        return res
    
    @trace(entity=u'Token', op=u'logout.keyauth.insert')
    def logout(self, uid, sign, data):
        """Logout user
        """
        # get identity and verify signature
        #identity = self.verify_request_signature(uid, sign, data)
        #operation.user = (identity[u'user'][u'name'], identity[u'ip'], identity[u'uid'])
        identity = self.get_identity(uid)
        
        try:
            # remove identity from redis
            self.remove_identity(identity[u'uid'])
    
            res = u'Identity %s successfully logout' % identity[u'uid']
            self.logger.debug(res)
            #User(self).send_event(u'keyauth-login.delete', params={u'uid':uid})
        except Exception as ex:
            #User(self).send_event(u'keyauth-login.delete', params={u'uid':uid}, 
            #                      exception=ex)
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=400)
                
        return res
    
    @trace(entity=u'Token', op=u'refresh.keyauth.insert')
    def refresh_user(self, uid, sign, data):
        """Refresh permissions stored in redis identity for a logged user
        """
        self.logger.info(u'Refresh identity: %s' % uid)        
        identity = self.get_identity(uid)
        #user = identity[u'user']
        
        user_name = operation.user[0]
        name, domain = user_name.split(u'@')
        res = None
        
        try:
            # reresh user in authentication manager
            user = self.module.authentication_manager.refresh(uid, name, domain)            
            # get user reference in db
            dbuser = self.manager.get_users(name=user_name)[0]
            # set user attributes
            #self.__set_user_attribs(dbuser, user)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
            
            # set user in identity
            identity[u'user'] = user.get_dict()
            
            # save identity in redis
            self.set_identity(uid, identity)
            
            res = {u'uid':uid,
                   u'user':user.get_dict(),
                   u'timestamp':identity[u'timestamp'],
                   u'pubkey':identity[u'pubkey'],
                   u'seckey':identity[u'seckey']}   

            User(self).send_event(u'keyauth-login.uodate', params={u'uid':uid})
        except QueryError as ex:
            #User(self).send_event(u'keyauth-login.uodate', params={u'uid':uid}, 
            #                      exception=ex)
            self.logger.error(ex.desc, exc_info=1)
            raise ApiManagerError(ex.desc, code=400)
        except Exception as ex:
            #User(self).send_event(u'keyauth-login.uodate', params={u'uid':uid}, 
            #                      exception=ex)
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)        

        return res    
    
class AuthObject(ApiInternalObject):
    pass
    
class User(AuthObject):
    objdef = u'User'
    objdesc = u'System users'
    
class Token(AuthObject):
    objdef = u'Token'
    objdesc = u'Authorization Token'
        