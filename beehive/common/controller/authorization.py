# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import binascii
import pickle
import ujson as json
from logging import getLogger
from six import ensure_text
from beecell.auth import AuthError
from beehive.common.apimanager import ApiController, ApiManagerError, ApiInternalObject
from beehive.common.model.authorization import AuthDbManager
from beecell.db import QueryError, TransactionError
from ipaddress import IPv4Network
from beecell.simple import truncate, id_gen, token_gen, dict_get
from beehive.common.data import operation, trace
from zlib import compress
from datetime import datetime, timedelta
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from beehive.common.model.authorization import User as ModelUser
# from beecell.simple import jsonDumps


class AuthenticationManager(object):
    """Manager used to login and logout user on authentication provider.

    :param auth_providers: list of authentication providers
    """
    def __init__(self, auth_providers):
        self.logger = getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
        
        self.auth_providers = auth_providers

    def __str__(self):
        return '<AuthenticationManager id:%s>' % id(self)

    def check(self, user_uuid, username, domain, ipaddr):
        """Login user using identity provider.

        :param user_uuid: user uuid
        :param username: user email or name
        :param domain: authentication provider
        :param ipaddr: ip address
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug('Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug('Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error('Authentication domain %s does not exist' % domain)
            raise AuthError('', 'Authentication domain %s does not exist' % domain, code=10)

        auth_user = auth_provider.check(user_uuid, username)

        # set user ip address
        auth_user.domain = domain
        auth_user.current_login_ip = ipaddr
        auth_user.id = user_uuid

        self.logger.debug('Login user: %s' % username)
        return auth_user

    def login(self, user_uuid, username, password, domain, ipaddr):
        """Login user using identity provider.

        :param user_uuid: user uuid
        :param username: user email or name
        :param domain: authentication provider
        :param ipaddr: ip address
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug('Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug('Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error('Authentication domain %s does not exist' % domain)
            raise AuthError('', 'Authentication domain %s does not exist' % domain, code=10)

        auth_user = auth_provider.login(username, password)

        # set user ip address
        auth_user.current_login_ip = ipaddr
        auth_user.domain = domain
        auth_user.id = user_uuid
        
        self.logger.debug('Login user: %s' % username)
        return auth_user

    def refresh(self, uid, username, domain):
        """Refresh user.
        
        :return: System User
        :rtype: :class:`SystemUser`
        :raises AuthError: raise :class:`AuthError`
        """
        # get authentication provider
        try:
            self.logger.debug('Authentication providers: %s' % self.auth_providers)
            auth_provider = self.auth_providers[domain]
            self.logger.debug('Get authentication provider: %s' % auth_provider)
        except KeyError:
            self.logger.error('Authentication domain %s does not exist' % domain)
            raise AuthError('', 'Authentication domain %s does not exist' % domain, code=10)
        
        # login over authentication provider and get user attributes
        # username = '%s@%s' % (username, domain)
        auth_user = auth_provider.refresh(username, uid)
        
        self.logger.debug('Login user: %s' % username)
        return auth_user   

    def get_user_class(self, domain):
        """Return authentication provider user class"""
        auth_provider = self.auth_providers[domain]
        return auth_provider.user_class


class BaseAuthController(ApiController):
    """Auth Module base controller.
    
    :param module: Beehive module
    """
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.manager = AuthDbManager()
        self.auth_manager = AuthDbManager()
    
    def set_superadmin_permissions(self):
        """Set superadmin permissions
        
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            self.set_admin_permissions('ApiSuperadmin', [])
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)    
    
    def set_admin_permissions(self, role_name, args):
        """Set admin permissions
        
        :param role_name: role name
        :param args: permission args
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            for item in self.child_classes:
                item(self).set_admin_permissions(role_name, args)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=ex.code)
    
    def verify_simple_http_credentials(self, user, pwd, user_ip):
        """Verify simple http credentials.
        
        :param user: user
        :param pwd: password
        :param user_ip: user ip address
        :return: identity
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        name, domain = user.split('@')
        identity = self.simple_http_login(name, domain, pwd, user_ip)

        return identity
    
    #
    # identity manipulation methods
    #
    @trace(entity='Token', op='insert', noargs=True)
    def set_identity(self, uid, identity, expire=True, expire_time=None):
        """Set beehive identity with token uid
        
        :param uid: authorization token
        :param identity: dictionary with login identity
        :param expire: if True identity key expire after xx seconds
        :param expire_time: [optional] det expire time in seconds
        """
        if expire_time is None:
            expire_time = self.expire

        val = pickle.dumps(identity)
        user = dict_get(identity, 'user.id')
        self.module.redis_identity_manager.conn.setex(self.prefix + uid, expire_time, val)
        if expire is False:
            self.module.redis_identity_manager.conn.persist(self.prefix + uid)

        # add identity to identity user index
        self.module.redis_identity_manager.conn.lpush(self.prefix_index + user, uid)
        # set index expire time
        self.module.redis_identity_manager.conn.expire(self.prefix_index + user, expire_time)

        self.logger.info('Set identity %s in redis' % uid)
    
    @trace(entity='Token', op='delete')
    def remove_identity(self, uid):
        """Remove beehive identity with token uid
        
        :param uid: authorization token
        :return: None
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, '*', 'delete')

        identity = self.module.redis_identity_manager.conn.get(self.prefix + uid)
        data = pickle.loads(identity)
        user = dict_get(data, 'user.id')

        if identity is None:
            err = 'Identity %s does not exist' % uid
            User(self).send_event('identity.delete', params={'uid': uid}, exception=err)
            self.logger.error(err)
            raise ApiManagerError(err, code=404)            
        
        try:
            self.module.redis_identity_manager.conn.delete(self.prefix + uid)

            # delete identity from identity user index
            self.module.redis_identity_manager.conn.lrem(self.prefix_index + user, 1, uid)

            self.logger.debug('Remove identity %s from redis' % uid)
            return None
        except Exception as ex:
            err = 'Can not remove identity %s' % uid
            self.logger.error(err)
            raise ApiManagerError(err, code=400)

    @trace(entity='Token', op='view')
    def exist_identity(self, uid):
        """Verify identity exists
        
        :return: True or False
        :rtype: bool
        """
        try:
            identity = self.module.redis_identity_manager.conn.get(self.prefix + uid)
        except Exception as ex:
            self.logger.warning('Identity %s retrieve error: %s' % (uid, ex))
            return False
        
        if identity is not None:
            self.logger.debug('Identity %s exists' % (uid))           
            return True
        else:
            self.logger.warning('Identity does not %s exists' % (uid))           
            return False

    @trace(entity='Token', op='view')
    def get_identity(self, uid):
        """Get identity
        
        :return: {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 'seckey':...}
        :rtype: dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            identity = self.module.redis_identity_manager.conn.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error('Identity %s retrieve error: %s' % (uid, ex))
            raise ApiManagerError('Identity %s retrieve error' % uid, code=404)
            
        if identity is not None:
            data = pickle.loads(identity)
            data['ttl'] = self.module.redis_identity_manager.conn.ttl(self.prefix + uid)
            self.logger.debug('Get identity %s from redis: %s' % (uid, truncate(data)))
            return data
        else:
            self.logger.error('Identity %s does not exist or is expired' % uid)
            raise ApiManagerError('Identity %s does not exist or is expired' % uid, code=404)

    @trace(entity='Token', op='view')
    def get_identities(self):
        """Get list of active identities

        :return: list of {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 'seckey':...}
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.check_authorization(Token.objtype, Token.objdef, '*', 'view')

        res = []
        for key in self.module.redis_identity_manager.conn.keys(self.prefix+'*'):
            try:
                identity = self.module.redis_identity_manager.conn.get(key)
                data = pickle.loads(identity)
                data['ttl'] = self.module.redis_identity_manager.conn.ttl(key)
                res.append(data)
            except Exception as ex:
                self.logger.warning('Identity %s can not be retrieved: %s' % (key, ex))

        self.logger.debug('Get identities from redis: %s' % truncate(res))
        return res    
    
    #
    # base inner login
    #
    @trace(entity='Token', op='insert', noargs=True)
    def validate_login_params(self, name, domain, password, login_ip):
        """Validate main login params.
        
        TODO : riattivare il controllo dell'ip
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :raises ApiManagerError: raise :class:`ApiManagerError`        
        """
        if domain is None:
            domain = 'local'    
    
        # set user in thread local variable
        operation.user = ('%s@%s' % (name, domain), login_ip, None)    
    
        # Validate input data and login user
        try:
            if name.strip() == '':
                msg = 'Username is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if password is not None and password.strip() == '':
                msg = 'Password is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)
            if domain.strip() == '':
                msg = 'Domain is not provided or syntax is wrong'
                self.logger.error(msg)
                raise ApiManagerError(msg, code=400)

            # try:
            #     login_ip = gethostbyname(login_ip)
            #     IPv4Address(ensure_text(login_ip))
            # except Exception as ex:
            #     msg = 'Ip address is not provided or syntax is wrong'
            #     self.logger.error(msg, exc_info=True)
            #     raise ApiManagerError(msg, code=400)
            
            self.logger.debug('User %s@%s:%s validated' % (name, domain, login_ip))
        except ApiManagerError as ex:
            raise ApiManagerError(ex.value, code=ex.code)
    
    @trace(entity='Token', op='insert', noargs=True)
    def check_login_user(self, name, domain, password, login_ip):
        """Simple http authentication login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: database user instance, user attributes as dict
        :raises ApiManagerError: raise :class:`ApiManagerError`        
        """
        # verify user exists in beehive database
        try:
            user_name = '%s@%s' % (name, domain)
            dbuser = self.auth_manager.get_entity(ModelUser, user_name)
            # get user attributes
            dbuser_attribs = {a.name: (a.value, a.desc) for a in dbuser.attrib}
        except (QueryError, Exception) as ex:
            msg = 'User %s does not exist' % user_name
            self.logger.error(msg, exc_info=True)
            raise ApiManagerError(msg, code=404)
        
        self.logger.debug('User %s exists' % user_name)
        
        return dbuser, dbuser_attribs

    @trace(entity='Token', op='insert', noargs=True)
    def set_user_last_login(self, name, domain):
        """Set user last login

        :param name: user name
        :param domain: user domain [unused]
        :return:
        """
        user = name
        try:
            self.auth_manager.set_user_last_login(user)
        except:
            self.logger.warning('User %s last login date can not be updated' % user, exc_info=True)

    def get_login_email(self, dbuser):
        """Get valid login email

        :param dbuser: database user instance
        :return: valid email
        """
        if dbuser.email is not None:
            return dbuser.email
        return dbuser.name

    @trace(entity='Token', op='insert', noargs=True)
    def base_login(self, name, domain, password, login_ip, dbuser, dbuser_attribs):
        """Base login.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param dbuser: database user instance
        :param dbuser_attribs: user attributes as dict
        :return: SystemUser instance, user attributes as dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # login user
        try:
            user = self.module.authentication_manager.login(dbuser.name, self.get_login_email(dbuser), password,
                                                            domain, login_ip)
        except AuthError as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)
        
        self.logger.info('Login user: %s' % user)

        self.set_user_last_login(dbuser.name, domain)
        
        # append attributes, roles and perms to SystemUser
        try:
            # set user attributes
            # self.__set_user_attribs(user, dbuser_attribs)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
        except QueryError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=401)
        
        return user, dbuser_attribs

    @trace(entity='Token', op='insert', noargs=True)
    def extended_login(self, name, domain, password, login_ip, dbuser, dbuser_attribs):
        """Extended login. Like base login but if password check fails make secret check using password.

        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param dbuser: database user instance
        :param dbuser_attribs: user attributes as dict
        :return: SystemUser instance, user attributes as dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # login user
        try:
            user = self.module.authentication_manager.login(dbuser.name, self.get_login_email(dbuser), password,
                                                            domain, login_ip)
        except AuthError as ex:
            self.logger.warning(ex.desc)

            # check secret
            res = self.auth_manager.verify_user_secret(dbuser, password)

            user_class = self.module.authentication_manager.get_user_class(domain)
            email = dbuser.email
            if email is None:
                email = dbuser.name
            user = user_class(dbuser.name, email, password, dbuser.active, login_ip=login_ip, domain=domain)

            if res is False:
                raise ApiManagerError(ex.desc, code=401)

        self.logger.info('Login user: %s' % user)

        self.set_user_last_login(dbuser.name, domain)

        # append attributes, roles and perms to SystemUser
        try:
            # set user attributes
            # self.__set_user_attribs(user, dbuser_attribs)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
        except QueryError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=401)

        return user, dbuser_attribs

    @trace(entity='Token', op='insert', noargs=True)
    def check_base_login(self, name, domain, secret, login_ip, dbuser, dbuser_attribs):
        """Base check login.

        :param name: user name
        :param domain: user authentication domain
        :param secret: user secret
        :param login_ip: user login_ip
        :param dbuser: database user instance
        :param dbuser_attribs: user attributes as dict
        :return: SystemUser instance, user attributes as dict
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # login user
        try:
            user = self.module.authentication_manager.check(dbuser.name, self.get_login_email(dbuser), domain, login_ip)
        except AuthError as ex:
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=401)

        if secret is not None and dbuser.secret != secret:
            self.logger.error('User secret is wrong')
            raise ApiManagerError('User secret is wrong', code=401)
        self.logger.debug('User %s secret is correct' % dbuser.uuid)

        self.logger.info('Login user: %s' % user)

        self.set_user_last_login(dbuser.name, domain)

        # append attributes, roles and perms to SystemUser
        try:
            # set user attributes
            # self.__set_user_attribs(user, dbuser_attribs)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
        except QueryError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=401)

        return user, dbuser_attribs

    def __set_user_attribs(self, user, attribs):
        """Set user attributes

        :param user: user object
        :param attribs: user attributes
        :return:
        """
        user.set_attributes(attribs)
    
    def __set_user_perms(self, dbuser, user):
        """Set user permissions

        :param dbuser: orm user class instance
        :param user: user object
        :return:
        """
        perms = self.auth_manager.get_login_permissions(dbuser)
        compress_perms = binascii.b2a_base64(compress(json.dumps(perms).encode('utf-8')))
        user.set_perms(compress_perms)
    
    def __set_user_roles(self, dbuser, user):
        """Set user roles

        :param dbuser: orm user class instance
        :param user: user object
        :return:
        """
        roles = self.auth_manager.get_login_roles(dbuser)
        user.set_roles([r.name for r in roles])      
    
    #
    # simple http login
    #
    @trace(entity='Token', op='insert', noargs=True)
    def simple_http_login(self, name, domain, password, login_ip):
        """Simple http authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        user_name = '%s@%s' % (name, domain)
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise
        
        # check user has authentication filter
        auth_filters = dbuser_attribs.get('auth-filters', ('', None))[0].split(',')
        if 'simplehttp' not in auth_filters:
            msg = 'Simple http authentication is not allowed for user %s' % user_name
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)
        
        # check user ip is in allowed cidr
        auth_cidrs = dbuser_attribs.get('auth-cidrs', '')[0].split(',')
        allowed = False
        for auth_cidr in auth_cidrs:
            allowed_cidr = IPv4Network(ensure_text(auth_cidr))
            user_ip = IPv4Network('%s/32' % login_ip)
            if user_ip.overlaps(allowed_cidr) is True:
                allowed = True
                break
        
        if allowed is False:
            msg = 'User %s ip %s can not perform simple http authentication' % (user_name, login_ip)
            self.logger.error(msg)
            raise ApiManagerError(msg, code=401)            
        
        # login user
        try:
            user, attrib = self.base_login(self.get_login_email(dbuser), domain, password, login_ip, dbuser,
                                           dbuser_attribs)
        except ApiManagerError as ex:
            raise
        
        res = {'uid': id_gen(20),
               'type': 'simplehttp',
               'user': user.get_dict(),
               'timestamp': datetime.now().strftime('%y-%m-%d-%H-%M')}
        
        return res
    
    #
    # keyauth login, logout, refresh_user
    #
    # @trace(entity='Token', op='insert')
    def gen_authorization_key(self, user, domain, name, login_ip, attrib):
        """Generate asymmetric key for keyauth filter.
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :param attrib: user attributes
        :raises ApiManagerError: raise :class:`ApiManagerError` 
        """
        user_name = '%s@%s' % (name, domain) 
        
        try:
            uid = token_gen()
            timestamp = datetime.now()
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024, backend=default_backend())
            public_key = private_key.public_key()
            pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                          format=serialization.PublicFormat.SubjectPublicKeyInfo)
            pubkey = binascii.b2a_base64(pem)
            pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                                            encryption_algorithm=serialization.NoEncryption())
            seckey = binascii.b2a_base64(pem)
            
            # create identity
            identity = {'uid': uid,
                        'type': 'keyauth',
                        'user': user.get_dict(),
                        'timestamp': timestamp,
                        'ip': login_ip,
                        'pubkey': pubkey,
                        'seckey': seckey}
            self.logger.debug('Create user %s identity: %s' % (user_name, truncate(identity)))
            operation.user = (user.id, login_ip, uid)
            
            # save identity in redis
            expire = True
            if attrib['sys_type'][0] == 'SYS':
                self.logger.debug('Login system user')
            self.set_identity(uid, identity, expire=expire)

            expires_at = timestamp+timedelta(seconds=self.expire)
            res = {
                'token_type': 'Bearer',
                'user': user.get_dict().get('id'),
                'access_token': uid,
                'pubkey': pubkey,
                'seckey': seckey,
                'expires_in': self.expire,
                'expires_at': expires_at.timestamp(),
            }
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=401)            
        
        return res    
    
    @trace(entity='Token', op='insert', noargs=True)
    def create_keyauth_token(self, user=None, password=None, login_ip=None):
        """Create asymmetric keys authentication token
        
        :param user: user name with authentication domain <user>@<domain>
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        name, domain = user.split('@')
        
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise     
        
        # check user attributes
        
        # login user
        try:
            user, attrib = self.base_login(self.get_login_email(dbuser), domain, password, login_ip, dbuser,
                                           dbuser_attribs)
        except ApiManagerError as ex:
            raise
        
        # generate asymmetric keys
        res = self.gen_authorization_key(user, domain, name, login_ip, attrib)

        return res    
    
    @trace(entity='Token', op='insert', noargs=True)
    def login(self, name, domain, password, login_ip):
        """Asymmetric keys authentication login
        
        :param name: user name
        :param domain: user authentication domain
        :param password: user password
        :param login_ip: user login_ip
        :return: True
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # validate input params
        try:
            self.validate_login_params(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise
        
        # check user
        try:
            dbuser, dbuser_attribs = self.check_login_user(name, domain, password, login_ip)
        except ApiManagerError as ex:
            raise     
        
        # check user attributes
        
        # login user
        try:
            user, attrib = self.base_login(self.get_login_email(dbuser), domain, password, login_ip, dbuser,
                                           dbuser_attribs)
        except ApiManagerError as ex:
            raise
        
        # generate asymmetric keys
        res = self.gen_authorization_key(user, domain, name, login_ip, attrib)
        
        return res
    
    @trace(entity='Token', op='insert')
    def logout(self, uid, sign, data):
        """Logout user

        :param uid: identity id
        :param sign: [not used]
        :param data: [not used]
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # get identity and verify signature
        identity = self.get_identity(uid)
        
        try:
            # remove identity from redis
            self.remove_identity(identity['uid'])
    
            res = 'Identity %s successfully logout' % identity['uid']
            self.logger.debug(res)
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
                
        return None
    
    @trace(entity='Token', op='insert')
    def refresh_user(self, uid, sign, data):
        """Refresh permissions stored in redis identity for a logged user

        :param uid: identity id
        :param sign: [not used]
        :param data: [not used]
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        self.logger.info('Refresh identity: %s' % uid)        
        identity = self.get_identity(uid)
        #user = identity['user']
        
        user_name = operation.user[0]
        name, domain = user_name.split('@')
        res = None
        
        try:
            # reresh user in authentication manager
            user = self.module.authentication_manager.refresh(uid, name, domain)            
            # get user reference in db
            dbuser = self.auth_manager.get_entity(ModelUser, user_name)
            # set user attributes
            #self.__set_user_attribs(dbuser, user)
            # set user permission
            self.__set_user_perms(dbuser, user)
            # set user roles
            self.__set_user_roles(dbuser, user)
            
            # set user in identity
            identity['user'] = user.get_dict()
            
            # save identity in redis
            self.set_identity(uid, identity)
            
            res = {'uid': uid,
                   'user': user.get_dict(),
                   'timestamp': identity['timestamp'],
                   'pubkey': identity['pubkey'],
                   'seckey': identity['seckey']}

            User(self).send_event('keyauth-login.uodate', params={'uid':uid})
        except QueryError as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=400)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise ApiManagerError(ex, code=400)        

        return res    


class AuthObject(ApiInternalObject):
    module = 'AuthModule'


class User(AuthObject):
    objdef = 'User'
    objdesc = 'System users'


class Token(AuthObject):
    objdef = 'Token'
    objdesc = 'Authorization Token'
