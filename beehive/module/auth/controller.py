'''
Created on Jan 16, 2014

@author: darkbk
'''
import logging
import pandas as pd
import binascii
import pickle
from datetime import datetime
#from Crypto.PublicKey import RSA
#from Crypto import Random
#from Crypto.Hash import SHA256
#from Crypto.Signature import PKCS1_v1_5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from beecell.auth import extract
from beecell.auth import AuthError
from beecell.perf import watch
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beehive.common.data import TransactionError, QueryError
from beehive.common.data import distributed_transaction, distributed_query
from beehive.common.data import operation
from beecell.simple import transaction_id_generator, str2uni, id_gen, truncate
from beehive.module.auth.model import AuthDbManager

class AuthenticationManager(object):
    """Manager used to login and logout user on authentication provider.
    
    """
    logger = logging.getLogger('gibbon.cloudapi')
    
    def __init__(self, auth_providers):
        self.auth_providers = auth_providers

    def __str__(self):
        return "<AuthenticationManager id:%s>" % id(self)

    @watch
    def login(self, username, password, domain, ipaddr):
        """Login user using ldap server.
        
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
            raise AuthError('', 'Authentication domain %s does not exist' % domain, 
                            code=10)
        
        # login over authentication provider and get user attributes
        username = u'%s@%s' % (username, domain)

        auth_user = auth_provider.login(username, password)

        # set user ip address
        auth_user.current_login_ip = ipaddr
        
        self.logger.debug(u'Login user: %s' % (username))
        return auth_user

class AuthController(ApiController):
    """Auth Module controller.
    """
    version = u'v1.0'    
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.dbauth = AuthDbManager()
        self.objects = Objects(self)
        
        self.child_classes = [Objects, Role, User]
    
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        # add actions
        try:
            actions = [u'*', u'view', u'insert', u'update', u'delete', u'use']
            self.dbauth.add_object_actions(actions)
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
        # init container
        for child in self.child_classes:
            child(self).init_object()
    
    @distributed_query
    def get_superadmin_permissions(self):
        """ """
        try:
            #perms = ApiModule.get_superadmin_permissions(self)
            perms = []
            for item in self.child_classes:
                perms.extend(self.dbauth.get_permission_by_object(
                                    objid=self._get_value(item.objdef, []),
                                    objtype=item.objtype,
                                    objdef=item.objdef,
                                    action=u'*'))
                perms.extend(self.dbauth.get_permission_by_object(
                                    objid=self._get_value(item.objdef, []),
                                    objtype=u'event',
                                    objdef=item.objdef,
                                    action=u'*'))
            return perms
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def count(self):
        """Count users, groups, roles and objects
        """
        try:
            res = {'users':self.dbauth.count_user(),
                   'groups':self.dbauth.count_group(),
                   'roles':self.dbauth.count_role(),
                   'objects':self.dbauth.count_object()}
            return res
        except QueryError as ex:
            raise ApiManagerError(ex, code=ex.code)    
    
    #
    # role manipulation methods
    #
    @watch
    def get_roles(self, oid=None, name=None, permission=None):
        """Get roles or single role.

        :param oid: role id [optional]
        :param name: role name [optional]
        :param permission: permission (type, value, action) [optional]
        :return: List of (role.id, role.name, role.desc)
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can('view', Role.objtype, definition=Role.objdef)        
        res = []
        
        # query roles
        try:
            # search roles by oid
            if oid is not None:
                roles = self.dbauth.get_role(oid=oid)
                if not roles:
                    self.logger.warn('Role %s was not found' % oid)
            
            # search roles by name        
            elif name is not None:
                roles = self.dbauth.get_role(name=name)
                if not roles:
                    self.logger.warn('Role %s was not found' % name)
            
            # search roles by permission
            elif permission is not None:
                # get permission
                # ("id", "oid", "type", "definition", "objclass", "objid", "aid", "action")
                objid = permission[5]
                objtype = permission[2]
                objdef = permission[3]
                action = permission[7]
                perm = self.dbauth.get_permission_by_object(objid=objid,
                                                            objtype=objtype, 
                                                            objdef=objdef,
                                                            action=action)[0]
                roles = self.dbauth.get_permission_roles(perm)
                
            # get all roles
            else:
                roles = self.dbauth.get_role()
            
            for role in roles:
                # check authorization
                objset = set(objs[Role.objdef])

                # create needs
                needs = self.get_needs([role.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    obj = Role(self, oid=role.id, objid=role.objid, name=role.name, 
                               desc=role.description, model=role)
                    res.append(obj)            
            
            self.logger.debug('Get roles: %s' % len(res))
            
            Role(self).event('role.view', 
                             {'oid':oid, 'name':name, 'permission':permission}, 
                             (True))
            return res
        except QueryError as ex:
            Role(self).event('role.view', 
                             {'oid':oid, 'name':name, 'permission':permission}, 
                             (False, ex))
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

    @watch
    def add_role(self, name, description=''):
        """Add new role.

        :param name: name of the role
        :param description: role description. [Optional]
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can('insert', Role.objtype, definition=Role.objdef)
        if len(objs) > 0 and objs[Role.objdef][0].split('//')[-1] != '*':
            raise ApiManagerError('You need more privileges to add role', 
                                  code=2000)
                
        try:
            objid = id_gen()
            role = self.dbauth.add_role(objid, name, description)
            # add object and permission
            Role(self).register_object([objid], desc=description)
            
            self.logger.debug('Add new role: %s' % name)
            Role(self).event('role.insert', 
                             {'name':name, 'description':description}, 
                             (True))
            
            return role
        except TransactionError as ex:
            Role(self).event('role.insert', 
                             {'name':name, 'description':description}, 
                             (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    @distributed_transaction
    def add_superadmin_role(self, perms):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_role('ApiSuperadmin', 'Beehive super admin role')
        
        # append permissions
        try:
            self.dbauth.append_role_permissions(role, perms)
            return role
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @distributed_transaction
    def add_guest_role(self):
        """Add cloudapi admin role with all the required permissions.
        
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # add role
        role = self.add_role('Guest', 'Beehive guest role')        
        return role

    @distributed_transaction
    def add_app_role(self, name):
        """Add role used by an app that want to connect to cloudapi 
        to get configuration and make admin action.
        
        :param name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        return self.add_role(name, 'Beehive app \'%s\' role' % name)

    #
    # user manipulation methods
    #
    @watch
    def get_users(self, oid=None, name=None, role=None):
        """Get users or single user.

        :param oid: user id [optional]
        :param name: user name [optional]
        :param role: role name [optional]
        :return: tupla (id, name, type, active, description, attribute
                        creation_date, modification_date)
        :rtype: :class:`SystemUser`
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can('view', User.objtype, definition=User.objdef)
        res = []
                
        try:
            # search users by id
            if oid:
                users = self.dbauth.get_user(oid=oid)
                if not users:
                    self.logger.warn('User %s was not found' % oid)
            
            # search users by name
            elif name:
                users = self.dbauth.get_user(name=name)
                if not users:
                    self.logger.warn('User %s was not found' % name)
                
            # search users by role
            elif role:
                role_obj = self.dbauth.get_role(name=role)[0]
                users = self.dbauth.get_role_users(role_obj)
            
            # get all users
            else:
                users = self.dbauth.get_user()
            
            for user in users:
                # check authorization
                objset = set(objs[User.objdef])

                # create needs
                needs = self.get_needs([user.objid])
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    obj = User(self, oid=user.id, objid=user.objid, 
                               name=user.name, active=user.active, 
                               desc=user.description, model=user)
                    res.append(obj)                
            
            self.logger.debug('Get users: %s' % len(res))
            User(self).event('user.view', 
                             {'oid':oid, 'name':name, 'role':role}, 
                             (True))            
            return res
        except QueryError as ex:
            User(self).event('user.view', 
                             {'oid':oid, 'name':name, 'role':role}, 
                             (False, ex))              
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

    @watch
    def add_user(self, username, storetype, systype, active=True, 
                       password=None, description=''):
        """Add new user.

        :param username: name of the user
        :param storetype: type of the user store. Can be DBUSER, LDAPUSER
        :param systype: type of user. User can be a human USER or a system 
                        module SYS
        :param profile: Profile name [Optional]
        :param active: User status. If True user is active [Optional] [Default=True]
        :param description: User description. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :return: True if user added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        objs = self.can('insert', 'auth', definition=User.objdef)
        if len(objs) > 0 and objs[User.objdef][0].split('//')[-1] != '*':
            raise ApiManagerError('You need more privileges to add user', 
                                  code=2000)
                
        try:
            objid = id_gen()
            user = self.dbauth.add_user(objid, username, [], active=active, 
                                        password=password, 
                                        description=description)
            # add object and permission
            User(self).register_object([objid], desc=description)
            
            # add default attributes
            self.dbauth.set_user_attribute(user, 'store_type', storetype, 
                                           'Type of user store')
            self.dbauth.set_user_attribute(user, 'sys_type', systype, 
                                           'Type of user')            
            
            self.logger.debug('Add new user: %s' % username)
            User(self).event('user.insert', 
                             {'username':username, 'storetype':storetype, 
                              'active':active,
                              'password':password, 'description':description}, 
                             (True))
            user = self.get_users(name=username)[0]         
            return user
        except TransactionError as ex:
            User(self).event('user.insert', 
                             {'username':username, 'storetype':storetype, 
                              'active':active,
                              'password':password, 'description':description}, 
                             (False, ex))              
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    @distributed_transaction
    def add_generic_user(self, name, storetype, password=None,
                         description=''):
        """Add cloudapi generic user. A generic user has a default role
        associated and the guest role. A generic user role has no permissions
        associated.
        
        :param name: user name
        :param storetype: type of the user. Can be DBUSER, LDAPUSER
        :param password: user password for DBUSER
        :param description: User description. [Optional]        
        :return: True if user is added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        profile = ''
        self.add_user(name, storetype, 'USER', active=True, 
                      password=password, description=description)
        user = self.get_users(name=name)[0]
        # create user role
        self.add_role("%sRole" % name.split('@')[0], 'User %s private role' % name)
        # append role to user
        user.append_role("%sRole" % name.split('@')[0])
        user.append_role("Guest")
        return user
    
    @distributed_transaction
    def add_system_user(self, name, password=None, description=''):
        """Add cloudapi system user. A system user is used by a module to 
        call the apis of the other modules.
        
        :param name: user name
        :param password: user password for DBUSER
        :param description: User description. [Optional]        
        :return: True if user is added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # create user
        self.add_user(name, 'DBUSER', 'SYS', active=True, 
                      password=password, description=description)
        user = self.get_users(name=name)[0]
        # create user role
        self.add_role("%sRole" % name.split('@')[0], 'User %s private role' % name)
        # append role to user
        user.append_role("ApiSuperadmin")
        return user  
    
    #
    # identity manipulation methods
    #
    @watch
    def set_identity(self, uid, identity, expire=True):
        val = pickle.dumps(identity)
        self.module.redis_manager.setex(self.prefix + uid, self.expire, val)
        if expire is False:
            self.module.redis_manager.persist(self.prefix + uid)
        self.logger.debug('Set identity %s in redis' % uid)
        User(self).event('user.identity.add', 
                         {'uid':uid}, 
                         (True))
    
    @watch
    def remove_identity(self, uid):
        if self.module.redis_manager.get(self.prefix + uid) is None:
            User(self).event('user.identity.delete', 
                             {'uid':uid}, 
                             (False, "Identity %s does not exist" % uid))            
            self.logger.error("Identity %s does not exist" % uid)
            raise ApiManagerError("Identity %s does not exist" % uid, code=1115)            
        
        try:
            self.module.redis_manager.delete(self.prefix + uid)
            self.logger.debug('Remove identity %s from redis' % uid)
            User(self).event('user.identity.delete', 
                             {'uid':uid}, 
                             (True))            
            return True
        except Exception as ex:
            User(self).event('user.identity.delete', 
                             {'uid':uid}, 
                             (False, ex))            
            self.logger.error("Can not remove identity %s" % uid)
            raise ApiManagerError("Can not remove identity %s" % uid, code=1115)       

    @watch
    def exist_identity(self, uid):
        """Get identity
        :return: True or False
        :rtype: dict
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error("Identity %s retrieve error: %s" % (uid, ex))
            raise ApiManagerError("Identity %s retrieve error" % uid, code=1014)
        
        if identity is not None:
            self.logger.debug('Identity %s exists' % (uid))           
            return True
        else:
            self.logger.debug('Identity does not %s exists' % (uid))           
            return False            
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=1014)

    @watch
    def get_identity(self, uid):
        """Get identity
        :return: {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 
                  'seckey':...}
        :rtype: dict
        """
        try:
            identity = self.module.redis_manager.get(self.prefix + uid)
        except Exception as ex:
            self.logger.error("Identity %s retrieve error: %s" % (uid, ex))
            raise ApiManagerError("Identity %s retrieve error" % uid, code=1014)
            
        if identity is not None:
            data = pickle.loads(identity)
            data['ttl'] = self.module.redis_manager.ttl(self.prefix + uid)
            self.logger.debug('Get identity %s from redis: %s' % (uid, data))           
            return data
        else:
            self.logger.error("Identity %s doen't exist or is expired" % uid)
            raise ApiManagerError("Identity %s doen't exist or is expired" % uid, code=1014)

    @watch
    def get_identities(self):
        try:
            res =  []
            for key in self.module.redis_manager.keys(self.prefix+'*'):
                identity = self.module.redis_manager.get(key)
                data = pickle.loads(identity)
                ttl = self.module.redis_manager.ttl(key)
                res.append({'uid':data['uid'], 'user':data['user']['name'],
                            'timestamp':data['timestamp'], 'ttl':ttl, 
                            'ip':data['ip']})
        except Exception as ex:
            self.logger.error('No identities found: %s' % ex)
            raise ApiManagerError('No identities found')
        
        User(self).event('user.identity.get', {}, (True))
        self.logger.debug('Get identities from redis: %s' % (res))
        return res    

    '''
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
            signature = binascii.a2b_base64(sign)
            pub_key = binascii.a2b_base64(pubkey64)
            key = RSA.importKey(pub_key)
            
            # create data hash
            hash_data = SHA256.new(data)
            self.logger.debug('Get data: %s' % data)
            self.logger.debug('Created hash: %s' % binascii.b2a_base64(
                                                        hash_data.digest()))

            # verify sign
            verifier = PKCS1_v1_5.new(key)
            res = verifier.verify(hash_data, signature)
            
            # extend expire time of the redis key
            if res is True:
                self.module.redis_manager.expire(self.prefix + uid, self.expire)
                self.logger.debug('Extend expire for identity %s: %ss' % (
                                                    uid, self.expire))
        except:
            self.debug.error("Data signature for identity %s is not valid" % uid)
            raise ApiManagerError("Data signature for identity %s \
                                   is not valid" % uid, code=1014)

        if not res:
            raise ApiManagerError("Data signature for identity %s \
                                   is not valid" % uid, code=1014)
        else:    
            self.logger.debug('Data signature is valid')

        return identity
    '''
    
    @watch
    def _gen_authorizaion_key(self, user, user_name, name, login_ip, attrib):
        '''
        Random.atfork()
        random_generator = Random.new().read
        key = RSA.generate(1024, random_generator)
        uid = transaction_id_generator(20)
        
        timestamp = datetime.now().strftime("%y-%m-%d-%H-%M")
        pubkey = binascii.b2a_base64(key.publickey().exportKey('DER'))
        seckey = binascii.b2a_base64(key.exportKey('DER'))
        '''
        uid = transaction_id_generator(20)
        timestamp = datetime.now().strftime("%y-%m-%d-%H-%M")        
        private_key = rsa.generate_private_key(public_exponent=65537,
                                               key_size=1024,
                                               backend=default_backend())        
        public_key = private_key.public_key()
        pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                      format=serialization.PublicFormat.SubjectPublicKeyInfo)    
        pubkey = binascii.b2a_base64(pem)
        pem = private_key.private_bytes(encoding=serialization.Encoding.DER,
                                        format=serialization.PrivateFormat.TraditionalOpenSSL, 
                                        encryption_algorithm=serialization.NoEncryption())    
        seckey = binascii.b2a_base64(pem)        
        
        # create identity
        identity = {'uid':uid,
                    'user':user.get_dict(),
                    'timestamp':timestamp,
                    'ip':login_ip,
                    'pubkey':pubkey,
                    'seckey':seckey}
        self.logger.debug('Create user %s identity: %s' % (user_name, 
                                                           truncate(identity)))
        operation.user = (user_name, login_ip, uid)
        
        # save identity in redis
        expire = True
        if attrib['sys_type'][0] == 'SYS':
            self.logger.debug('Login system user')
            #expire = False
        self.set_identity(uid, identity, expire=expire)

        res = {'uid':uid,
               'user':user.get_dict(),
               'timestamp':timestamp,
               'pubkey':pubkey,
               'seckey':seckey}
        
        return res
    
    @watch
    def _set_user_attribs(self, dbuser, user):
        """Get user attributes"""
        attrib = {a.name:(a.value, a.desc) for a in dbuser.attrib}
        user.set_attributes(attrib)
        return attrib  
    
    @watch
    def _set_user_perms(self, dbuser, user):
        """Set user permissions """
        perms = self.dbauth.get_user_permissions2(dbuser)
        '''if len(perms) == 0:
            raise QueryError('No permissions found')            
        user_perms = []
        for key, i in perms.iteritems():
            user_perms.append((i.id, i.obj.id, i.obj.type.objtype, 
                               i.obj.type.objdef, i.obj.type.objclass, 
                               i.obj.objid, i.action.id, i.action.value))'''
        user.set_perms(perms)
    
    @watch
    def _set_user_roles(self, dbuser, user):
        """Set user roles """    
        roles = self.dbauth.get_user_roles(dbuser)
        user.set_roles([r.name for r in roles])    
    
    # login, logout, refresh_user
    @distributed_transaction
    def login(self, name, domain, password, login_ip):
        """
        try:
            if request.method == 'POST':
                data = json.loads(request.data)
                name_domain = data['user'].split('@')
                name = name_domain[0]
                password = data['password']
                domain = name_domain[1]
                login_ip = data['login_ip']
        except:
            return self.get_error('Exception', 1001, 'Input parameter error')
        """
        if domain is None:
            domain = 'local'
        
        operation.user = (u'%s@%s' % (name, domain), login_ip, None)        
        
        # Validate input data and login user
        if name.strip() == '':
            User(self).event('user.login.insert', 
                             {'name':name, 'domain':domain, 
                              'password':'xxxxxxx', 'login_ip':login_ip}, 
                             (False, 'Username is not provided'))
            self.logger.error('Username is not provided')
            raise ApiManagerError('Username is not provided', code=1002)

        if password.strip() == '':
            User(self).event('user.login.insert', 
                             {'name':name, 'domain':domain, 
                              'password':'xxxxxxx', 'login_ip':login_ip}, 
                             (False, 'Password is not provided'))
            self.logger.error('Password is not provided')
            raise ApiManagerError('Password is not provided', code=1003)

        if domain.strip() == '':
            User(self).event('user.login.insert', 
                             {'name':name, 'domain':domain, 
                              'password':'xxxxxxx', 'login_ip':login_ip}, 
                             (False, 'Domain is not provided'))
            self.logger.error('Domain is not provided')
            raise ApiManagerError('Domain is not provided', code=1004)
        
        try:
            user = self.module.authentication_manager.login(name, password, 
                                                            domain, login_ip)
        except (AuthError) as ex:
            # 1 - Wrong user or password
            if ex.code == 1:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error('Invalid credentials')
                raise ApiManagerError('Invalid credentials', code=1005)
            # 2 - User is disabled
            elif ex.code == 2:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error('User is disabled')
                raise ApiManagerError('User is disabled', code=1006)
            # 3 - Password is expired
            elif ex.code == 3:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error('Password is expired')
                raise ApiManagerError('Password is expired', code=1007)
            # 7 - Connection error
            elif ex.code == 7:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error('Connection error')
                raise ApiManagerError('Connection error', code=1008)
            # 10 - Domain error
            elif ex.code == 7:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error(ex.desc)
                raise ApiManagerError(ex.desc, code=1009)
            # 0 - Not defined
            else:
                User(self).event('user.login.insert', 
                                 {'name':name, 'domain':domain, 
                                  'password':'xxxxxxx', 'login_ip':login_ip}, 
                                 (False, ex))
                self.logger.error(ex.desc)
                raise ApiManagerError(ex.desc, code=1010)
        
        self.logger.info('Login user: %s' % user)
        user_name = "%s@%s" % (name, domain)
        
        try:
            dbuser = self.dbauth.get_user(name=user_name)[0]
            # set user attributes
            attrib = self._set_user_attribs(dbuser, user)
            # set user permission
            self._set_user_perms(dbuser, user)
            # set user roles
            self._set_user_roles(dbuser, user)
        except QueryError as ex:
            User(self).event('user.login.insert', 
                             {'name':name, 'domain':domain, 
                              'password':'xxxxxxx', 'login_ip':login_ip}, 
                             (False, ex))
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=1011)

        try:
            res = self._gen_authorizaion_key(user, user_name, name, login_ip, attrib)
        except Exception as ex:
            User(self).event('user.login.insert', 
                             {'name':name, 'domain':domain, 
                              'password':'xxxxxxx', 'login_ip':login_ip}, 
                             (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=1012)
        
        User(self).event('user.login',
                         {'name':name, 'domain':domain, 'password':'xxxxxxx', 
                          'login_ip':login_ip},
                         (True))
        
        return res
    
    @distributed_transaction
    def logout(self, uid, sign, data):    
        # get identity and verify signature
        identity = self.verify_request_signature(uid, sign, data)
        operation.user = (identity['user']['name'], identity['ip'], identity['uid'])
        
        try:
            # remove identity from redis
            self.remove_identity(identity['uid'])
    
            res = 'Identity %s successfully logout' % identity['uid']
            self.logger.debug(res)
            User(self).event('user.login.delete', {'uid':uid}, (True))
        except Exception as ex:
            User(self).event('user.login.delete', {'uid':uid}, (False, ex))
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=1013)
                
        return res
    
    @distributed_transaction
    def refresh_user(self, uid, sign, data):
        """Refresh permissions stored in redis identity for a logged user"""
        
        # get identity and verify signature
        identity = self.verify_request_signature(uid, sign, data)
        operation.user = (identity['user']['name'], identity['ip'], identity['uid'])
        res = None

        try:
            user = identity['user']
            dbuser = self.dbauth.get_user(name=user['name'])[0]
            # get user attributes
            #user.set_attributes(dbuser.attribute)
            # get user permission
            perms = self.dbauth.get_user_permissions(dbuser)
            if len(perms) == 0:
                raise QueryError('No permissions found', code=404)            
            user_perms = []
            for key, i in perms.iteritems():
                user_perms.append((i.id, i.obj.id, i.obj.type.objtype, 
                                   i.obj.type.objdef,  
                                   i.obj.objid, i.action.id, i.action.value))
            user.set_perms(user_perms)
            identity['user'] = user.get_dict()
            
            # save identity in redis
            self.set_identity(uid, identity)            
            
            res = {'uid':uid,
                   'user':user.get_dict(),
                   'timestamp':identity['timestamp'],
                   'pubkey':identity['pubkey'],
                   'seckey':identity['seckey']}            
            
            self.logger.debug('Refresh identity %s permissions: %s' % 
                              (uid, user_perms))
            User(self).event('user.login.update', 
                             {'name':user['name'], 'login_ip':identity['ip']}, 
                             (True))    
        except (QueryError, Exception) as ex:
            User(self).event('user.login.update', 
                             {'name':user['name'], 'login_ip':identity['ip']}, 
                             (False, ex))
            self.logger.error(ex.desc)
            raise ApiManagerError(ex.desc, code=1011)        

        return res
    
class Objects(ApiObject):
    objtype = 'auth'
    objdef = 'objects'
    objdesc = 'Authorization objects'
    
    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid='', name='', desc='', active='')
    
    def __del__(self):
        pass    
    
    @property
    def dbauth(self):
        return self.controller.dbauth    
    
    #
    # System Object Type manipulation methods
    #    
    @watch
    def get_type(self, oid=None, objtype=None, objdef=None):
        """Get system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: List of Tuple (id, type, definition, objclass)
        :rtype: list
        :raises ApiManagerError if query empty return error.
        :raises ApiAuthorizationError if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)

        try:  
            data = self.dbauth.get_object_type(oid=oid, objtype=objtype, 
                                               objdef=objdef)

            res = [(i.id, i.objtype, i.objdef, i.objclass) for i in data 
                   if i.objtype != 'event']
            self.event('objects.type.view', 
                       {'oid':oid, 'objtype':objtype, 'objdef':objdef}, 
                       (True))
            return res
        except QueryError as ex:
            self.event('objects.type.view', 
                       {'oid':oid, 'objtype':objtype, 'objdef':objdef}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)
    
    @watch
    def add_types(self, obj_types):
        """Add a system object types
        
        :param obj_types: list of (type, definition, class) tuple
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('insert', self.objtype, definition=self.objdef)
        
        try:  
            res = self.dbauth.add_object_types(obj_types)
            self.event('objects.type.insert', {'obj_types':obj_types}, (True))
            return True
        except TransactionError as ex:
            self.event('objects.type.insert', {'obj_types':obj_types}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def remove_type(self, oid=None, objtype=None, objdef=None):
        """Remove system object type.
        
        :param oid: id of the system object type [optional]
        :param objtype: type of the system object type [optional]
        :param objdef: definition of the system object type [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('delete', self.objtype, definition=self.objdef)
                
        try:  
            res = self.dbauth.remove_object_type(oid=oid, objtype=objtype, 
                                                 objdef=objdef)
            self.event('objects.type.delete', 
                       {'oid':oid, 'objtype':objtype, 'objdef':objdef}, 
                       (True))            
            return res
        except TransactionError as ex:
            self.event('objects.type.delete', 
                       {'oid':oid, 'objtype':objtype, 'objdef':objdef}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object Action manipulation methods
    #
    @watch
    def get_action(self, oid=None, value=None):
        """Get system object action.
        
        :param oid: id of the system object action [optional]
        :param value: value of the system object action [optional]
        :return: List of Tuple (id, value)   
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)
                
        try:  
            data = self.dbauth.get_object_action(oid=oid, value=value)
            if data is None:
                raise QueryError('No data found')
            if type(data) is not list:
                data = [data]            
            res = [(i.id, i.value) for i in data]
            self.event('objects.action.view', {'oid':oid, 'value':value}, (True))
            return res
        except QueryError as ex:
            self.event('objects.action.view', {'oid':oid, 'value':value}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    @watch
    def add_actions(self, actions):
        """Add a system object action
        
        :param actions: list of string like 'use', 'view'
        :return: True if operation is successful   
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('insert', self.objtype, definition=self.objdef)

        try:  
            res = self.dbauth.add_object_actions(actions)
            self.event('objects.action.insert', {'actions':actions}, (True))
            return True
        except TransactionError as ex:
            self.event('objects.action.insert', {'actions':actions}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
    @watch
    def remove_action(self, oid=None, value=None):
        """Add a system object action
        
        :param oid: System object action id [optional]
        :param value: string like 'use', 'view' [optional]
        :return: True if operation is successful   
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('delete', self.objtype, definition=self.objdef)
                
        try:
            res = self.dbauth.remove_object_action(oid=oid, value=value)
            self.event('objects.action.delete', {'oid':oid, 'value':value}, (True))
            return res
        except TransactionError as ex:
            self.event('objects.action.delete', {'oid':oid, 'value':value}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # System Object manipulation methods
    #
    @watch
    def get(self, oid=None, objid=None, objtype=None, objdef=None):
        """Get system object filtering by id, by name or by type.

        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: type of the system object [optional]
        :param objdef: definition of the system object [optional]
        :return: List of Tuple (id, type, value) 
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)
                
        try:
            # get object types
            if objtype is not None or objdef is not None:
                obj_types = self.dbauth.get_object_type(objtype=objtype, 
                                                        objdef=objdef)
                # get objects
                data = []
                for obj_type in obj_types:
                    #if obj_type.objtype != 'event':
                    data.extend(self.dbauth.get_object(oid=oid, objid=objid, 
                                                       objtype=obj_type))
            else:
                data = self.dbauth.get_object(oid=oid, objid=objid)
                    
            res = [(i.id, i.type.objtype, i.type.objdef, i.objid, i.desc) 
                   for i in data]
            self.logger.debug('Get objects: %s' % len(res))
            self.event('objects.view', 
                       {'oid':oid, 'objid':objid, 'objtype':objtype, 
                        'objdef':objdef}, 
                       (True))
            return res
        except QueryError as ex:
            self.event('objects.view', 
                       {'oid':oid, 'objid':objid, 'objtype':objtype, 
                        'objdef':objdef}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

    @watch
    def add(self, objs):
        """Add a system object with all the permission related to available 
        action.
        
        :param objs: list of (objtype, definition, objid, objdesc) tuple
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('insert', self.objtype, definition=self.objdef)
                
        try:
            # get actions
            actions = self.dbauth.get_object_action()            
            
            # create objects
            data = []
            for obj in objs:
                obj_type = self.dbauth.get_object_type(objtype=obj[0], 
                                                       objdef=obj[1])[0]
                data.append((obj_type, obj[2], obj[3]))

            res = self.dbauth.add_object(data, actions)
            self.logger.debug('Add objects: %s' % res)
            self.event('objects.insert', {'objs':objs}, (True))        
            return True
        except (QueryError, TransactionError) as ex:
            self.event('objects.insert', {'objs':objs}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)  

    @watch
    def remove(self, oid=None, objid=None, objtype=None, objdef=None):
        """Delete system object filtering by id, by name or by type. System 
        remove also all the related permission. 
        
        Examples:
            manager.remove_object(oid='123242')
            manager.remove_object(value='', type="cloudstack.vm")
            manager.remove_object(value='clsk42_01.ROOT/CSI.')        
        
        :param oid: System object id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype: type of the system object [optional]
        :param objdef: definition of the system object [optional]
        :return: True if operation is successful
        :rtype: bool
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('delete', self.objtype, definition=self.objdef)
                
        try:
            if objtype is not None or objdef is not None:
                # get object types
                obj_types = self.dbauth.get_object_type(objtype=objtype, 
                                                        objdef=objdef)
                for obj_type in obj_types:            
                    res = self.dbauth.remove_object(oid=oid, objid=objid, 
                                                    objtype=obj_type)
            else:
                res = self.dbauth.remove_object(oid=oid, objid=objid)
            self.logger.debug('Remove objects: %s' % res)
            self.event('objects.delete', 
                       {'oid':oid, 'objid':objid, 'objtype':objtype, 
                        'objdef':objdef}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event('objects.delete', 
                       {'oid':oid, 'objid':objid, 'objtype':objtype, 
                        'objdef':objdef}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)          

    @watch
    def get_permission(self, permission_id=None, objid=None, objtype=None, 
                             objdef=None, action=None):
        """Get system object permisssion.
        
        :param permission_id: System Object Permission id [optional]
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :param action str: Object action [optional]
        :return: list of tuple like ("id", "oid", "type", "definition", 
                 "objclass", "objid", "aid", "action").
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)
                
        try:
            if permission_id is not None:
                res = self.dbauth.get_permission_by_id(permission_id=permission_id)
            elif objid is not None or objtype is not None or objdef is not None:
                res = self.dbauth.get_permission_by_object(objid=objid, 
                                                           objtype=objtype, 
                                                           objdef=objdef,
                                                           action=action)
            else:
                res = self.dbauth.get_permission_by_id()
            
            '''res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.type.objclass, i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]'''
            res = [(i.id, i.obj.id, i.obj.type.objtype, i.obj.type.objdef,
                    i.obj.objid, i.action.id, 
                    i.action.value, i.obj.desc) for i in res]            

            self.logger.debug('Get permissions: %s' % len(res))
            self.event('objects.permission.view', 
                       {'permission_id':permission_id, 'objid':objid, 
                        'objtype':objtype, 'objdef':objdef, 
                        'action':action}, 
                       (True))              
            return res
        except QueryError as ex:
            self.event('objects.permission.view', 
                       {'permission_id':permission_id, 'objid':objid, 
                        'objtype':objtype, 'objdef':objdef, 
                        'action':action}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

    def get_permissions_with_roles(self, objid=None, objtype=None, objdef=None):
        """Get system object permisssion with roles.
        
        :param objid: Total or partial objid [optional]
        :param objtype str: Object type [optional]
        :param objdef str: Object definition [optional]
        :return: list of tuple like (((id, rid, type, definition, 
                                       objclass, objid, aid, action, desc), 
                                      (role_id, role_name, role_desc))).
        :rtype: list
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)        
        
        try:
            if objtype == 'None': objtype = None
            if objdef == 'None': objdef = None
            if objid == 'None': objid = None
            
            res = []
            # get permissions
            perms = self.dbauth.get_permission_by_object(
                                        objid=objid,
                                        objtype=objtype,
                                        objdef=objdef)
            for p in perms:
                try:
                    roles = [(r.id, r.name, r.description) for r in 
                             self.dbauth.get_permission_roles(p)]
                except:
                    roles = []
                '''res.append(((p.id, p.obj.id, p.obj.type.objtype, 
                             p.obj.type.objdef, p.obj.type.objclass, 
                             p.obj.objid, p.action.id, p.action.value, 
                             p.obj.desc), roles))'''
                res.append(((p.id, p.obj.id, p.obj.type.objtype, 
                             p.obj.type.objdef, 
                             p.obj.objid, p.action.id, p.action.value, 
                             p.obj.desc), roles))
                
            self.logger.debug('Get permissions: %s' % len(res))
            self.event('objects.permission.view', 
                       {'objid':objid, 'objtype':objtype, 'objdef':objdef}, 
                       (True))              
            return res
        except QueryError as ex:
            self.event('objects.permission.view', 
                       {'objid':objid, 'objtype':objtype, 'objdef':objdef}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            return []
            #raise ApiManagerError(ex)

class Role(ApiObject):
    objtype = 'auth'
    objdef = 'role'
    objdesc = 'System roles'

    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                       model=None):
        ApiObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                                 desc=desc, active=True)
        self.model = model

    def __del__(self):
        pass

    @property
    def dbauth(self):
        return self.controller.dbauth

    @watch
    def info(self):
        """Get role info
        
        :return: Dictionary with role info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'view')
           
        creation_date = str2uni(self.model.creation_date.strftime("%d-%m-%y %H:%M:%S"))
        modification_date = str2uni(self.model.modification_date.strftime("%d-%m-%y %H:%M:%S"))   
        return {u'id':self.oid, u'type':self.objtype, u'definition':self.objdef, 
                u'name':self.name, u'objid':self.objid, u'desc':self.desc,
                u'active':self.active, u'date':{u'creation':creation_date,
                                                u'modified':modification_date}}

    @watch
    def update(self, new_name=None, new_description=None):
        """Update a role.
        
        :param new_name: new role name [optional]
        :param new_description: new role description [optional]
        :return: True if role updated correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:  
            res = self.dbauth.update_role(oid=self.oid, new_name=new_name, 
                                          new_description=new_description)
            # update object reference
            #self.dbauth.update_object(new_name, objid=self.objid)
            #self.objid = new_name
            
            self.logger.debug('Update role: %s' % self.name)
            self.event('role.update', 
                       {'name':self.name, 'new_name':new_name, 
                        'new_description':new_description}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event('role.update',
                       {'name':self.name, 'new_name':new_name, 
                        'new_description':new_description}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Delete role.
        
        :return: True if role deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'delete')
                
        try:  
            res = self.dbauth.remove_role(role_id=self.oid)
            # remove object and permissions
            self.deregister_object([self.objid])
            
            self.logger.debug('Delete role: %s' % self.name)
            self.event('role.delete', 
                       {'name':self.name}, 
                       (True))            
            return res
        except TransactionError as ex:
            self.event('role.delete', 
                       {'name':self.name}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def get_permissions(self):
        """Get role permissions.

        :param name: role name
        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError if query return error.
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'view')
                
        try:  
            perms = self.dbauth.get_role_permissions(self.name)
            
            role_perms = []
            for i in perms:
                role_perms.append((i.id, i.obj.id, i.obj.type.objtype, 
                                   i.obj.type.objdef, i.obj.type.objclass, 
                                   i.obj.objid, i.action.id, i.action.value,
                                   i.obj.desc))
            self.logger.debug('Get role %s permissions: %s' % (self.name, role_perms))
            
            self.event('role.permission.view', 
                       {'name':self.name}, 
                       (True))        
            return role_perms
        except QueryError as ex:
            self.event('role.permission.view', 
                       {'name':self.name}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)   

    @watch
    def append_permissions(self, perms):
        """Append permission to role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", 
                      "objclass", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                roleperms.extend(self.dbauth.get_permission_by_object(
                        objid=perm[5], objtype=perm[2], objdef=perm[3],
                        action=perm[7]))
            
            res = self.dbauth.append_role_permissions(self.model, roleperms)
            self.logger.debug('Append role %s permission : %s' % (self.name, perms))
            self.event('role.permission.update', 
                       {'name':self.name}, 
                       (True))               
            return res
        except QueryError as ex:
            self.event('role.permission.update', 
                       {'name':self.name}, 
                       (False, ex))             
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

    def remove_permissions(self, perms):
        """Remove permission from role
        
        :param name: Role name
        :param perms: list of tuple ("id", "oid", "type", "definition", 
                      "objclass", "objid", "aid", "action")
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:
            # get permissions
            roleperms = []
            for perm in perms:
                roleperms.extend(self.dbauth.get_permission_by_object(
                        objid=perm[5], objtype=perm[2], objdef=perm[3],
                        action=perm[7]))           
            
            res = self.dbauth.remove_role_permission(self.model, roleperms)
            self.logger.debug('Remove role %s permission : %s' % (self.name, perms))
            self.event('role.permission.update', 
                       {'name':self.name}, 
                       (True))             
            return res
        except QueryError as ex:
            self.event('role.permission.update', 
                       {'name':self.name}, 
                       (False, ex))              
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)

class User(ApiObject):
    objtype = 'auth'
    objdef = 'user'
    objdesc = 'System users'

    def __init__(self, controller, oid=None, objid=None, name=None, 
                       desc=None, active=None, model=None):
        ApiObject.__init__(self, controller, oid=oid, objid=objid, name=name, 
                                 desc=desc, active=active)
        self.model = model

    def __del__(self):
        pass

    @property
    def dbauth(self):
        return self.controller.dbauth

    @watch
    def info(self):
        """Get user info
        
        :return: Dictionary with user info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        creation_date = str2uni(self.model.creation_date.strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date.strftime(u'%d-%m-%y %H:%M:%S'))
        attrib = self.get_attribs()
        return {u'id':self.oid, u'type':self.objtype, u'definition':self.objdef, 
                u'name':self.name, u'objid':self.objid, u'desc':self.desc,
                u'password':self.model.password,  u'attribute':attrib,
                u'active':self.active, u'date':{u'creation':creation_date,
                                                u'modified':modification_date}}
        
    @watch
    def detail(self):
        """Get user detail
        
        :return: Dictionary with user detail.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`        
        """
        creation_date = str2uni(self.model.creation_date.strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date.strftime(u'%d-%m-%y %H:%M:%S'))
        attrib = self.get_attribs()
        return {u'id':self.oid, u'type':self.objtype, u'definition':self.objdef, 
                u'name':self.name, u'objid':self.objid, u'desc':self.desc,
                u'password':self.model.password,  u'attribute':attrib,
                u'roles':self.get_roles(), u'perms':self.get_perms(),
                u'groups':self.get_groups(), u'active':self.active, 
                u'date':{u'creation':creation_date,
                         u'modified':modification_date}}

    @watch
    def update(self, new_name=None, new_storetype=None, new_description=None, 
                     new_active=None, new_password=None):
        """Update a user.
        
        :param username: user name
        :param new_name: new user name [optional]
        :param new_storetype: new type of the user. Can be DBUSER, LDAPUSER [optional]
        :param new_description: new user description [optional]
        :param new_active: new user status [optional]
        :param new_password: new user password [optional]
        :return: True if user updated correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:
            res = self.dbauth.update_user(oid=self.oid, new_name=new_name,
                                          new_description=new_description, 
                                          new_active=new_active, 
                                          new_password=new_password)
            if new_storetype is not None:
                self.dbauth.set_user_attribute(self.model, 'store_type', 
                                               new_storetype)
            
            # update object reference
            #self.dbauth.update_object(new_name, objid=self.objid)
            #self.objid = new_name            
            
            self.logger.debug('Update user: %s' % self.name)
            self.event('user.update', 
                       {'name':self.name, 'new_name':new_name, 
                        'new_storetype':new_storetype, 
                        'new_description':new_description, 
                        'new_active':new_active, 'new_password':'xxxxxxxx'}, 
                       (True))               
            return res
        except TransactionError as ex:
            self.event('user.update', 
                       {'name':self.name, 'new_name':new_name, 
                        'new_storetype':new_storetype, 
                        'new_description':new_description, 
                        'new_active':new_active, 'new_password':'xxxxxxxx'}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def delete(self):
        """Delete a user.
        
        :return: True if user deleted correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'delete')
                
        try:
            res = self.dbauth.remove_user(username=self.name)
            # remove object and permission
            self.deregister_object([self.objid])
            
            try:
                # generic ueser has specific role associated. Delete also role
                role = self.controller.get_roles(name="%sRole" % self.name.split('@')[0])[0]
                role.delete()
            except Exception as ex:
                self.logger.warning('User %s has not role associated' % self.name)
            
            self.logger.debug('Delete user: %s' % self.name)
            self.event('user.delete', 
                       {'name':self.name}, 
                       (True))
            return res
        except TransactionError as ex:
            self.event('user.delete', 
                       {'name':self.name}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def get_attribs(self):
        attrib = {a.name:(a.value, a.desc) for a in self.model.attrib}
        self.logger.debug('User %s attributes: %s' % (self.name, attrib))
        return attrib   
    
    @watch
    def set_attribute(self, name, value, desc='', new_name=None):
        """Set an attribute
        
        :param user: User instance
        :param name: attribute name
        :param new_name: new attribute name
        :param value: attribute value
        :param desc: attribute description
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`        
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')

        try:
            res = self.dbauth.set_user_attribute(self.model, name, value=value, 
                                                 desc=desc, new_name=new_name)
            self.logger.debug('Set user %s attribute %s: %s' % 
                              (self.name, name, value))
            self.event('user.attribute.update', 
                       {'name':self.name, 'attrib':name, 'value':value}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event('user.attribute.update', 
                       {'name':self.name, 'attrib':name, 'value':value}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def remove_attribute(self, name):
        """Remove an attribute
        
        :param name: attribute name
        :return: True if attribute added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`           
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')

        try:
            res = self.dbauth.remove_user_attribute(self.model, name)
            self.logger.debug('Remove user %s attribute %s' % (self.name, name))
            self.event('user.attribute.update', 
                       {'name':self.name, 'attrib':name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event('user.attribute.update', 
                       {'name':self.name, 'attrib':name}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
    
    @watch
    def append_role(self, role_name):
        """Append role to user.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:
            role = self.dbauth.get_role(name=role_name)
            if len(role) <= 0:
                raise QueryError("Role %s does not exist" % role_name)
            else:
                role = role[0]
            
            res = self.dbauth.append_user_role(self.model, role)
            if res is True: 
                self.logger.debug('Append role %s to user %s' % (
                                            role, self.name))
            else:
                self.logger.debug('Role %s already linked with user %s' % (
                                            role, self.name))
            self.event('user.role.update', 
                       {'name':self.name, 'role':role_name}, 
                       (True))
            return res
        except (QueryError, TransactionError) as ex:
            self.event('user.role.update', 
                       {'name':self.name, 'role':role_name}, 
                       (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def remove_role(self, role_name):
        """Remove role from user.
        
        :param role_name: role name
        :return: True if role added correctly
        :rtype: bool
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, 'update')
                
        try:
            role = self.dbauth.get_role(name=role_name)
            if len(role) <= 0:
                raise QueryError("Role %s does not exist" % role_name)
            else:
                role = role[0]

            res = self.dbauth.remove_user_role(self.model, role)
            self.logger.debug('Remove role %s from user %s' % (role, self.name))
            self.event('user.role.update', 
                       {'name':self.name, 'role':role_name}, 
                       (True))            
            return res
        except (QueryError, TransactionError) as ex:
            self.event('user.role.update', 
                       {'name':self.name, 'role':role_name}, 
                       (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    @watch
    def get_roles(self):
        """Get users roles.

        :return: List of roles
        :rtype: list 
        :raises ApiManagerError: if query empty return error.
        """
        try:         
            roles = self.dbauth.get_user_roles(self.model)
            res = [(i.id, i.name, i.description) for i in roles]
            self.logger.debug('Get user %s roles: %s' % (self.name, res))
            self.event('user.role.view', {'name':self.name}, (True))
            return res
        except QueryError as ex:
            self.event('user.role.view', {'name':self.name}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex) 

    @watch
    def get_permissions(self):
        """Get users permissions.

        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        try:  
            perms = self.dbauth.get_user_permissions(self.model)
            if len(perms) == 0:
                return []          
            user_perms = []
            for key, i in perms.iteritems():
                user_perms.append((i.id, i.obj.id, i.obj.type.objtype, 
                                   i.obj.type.objdef, i.obj.type.objclass, 
                                   i.obj.objid, i.action.id, i.action.value,
                                   i.obj.desc))
            self.logger.debug('Get user %s permissions: %s' % (
                                        self.name, user_perms))
            self.event('user.permission.view', {'name':self.name}, (True))
            return user_perms
        except QueryError as ex:
            self.event('user.permission.view', {'name':self.name}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
    @watch
    def get_groups(self):
        """Get users groups.

        :return: Pandas Series with permissions (id, oid, value, type, aid, action)
        :rtype: pands.Series
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)
                
        try:        
            groups = self.dbauth.get_user_groups(self.model)
            res = [(i.id, i.name, i.description) for i in groups]
            self.logger.debug('Get user %s groups: %s' % (self.name, res))
            self.event('user.group.view', {'name':self.name}, (True))
            return res
        except QueryError as ex:
            self.event('user.group.view', {'name':self.name}, (False, ex))
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
    @watch
    def can(self, action, objtype, definition=None, name=None, perms=None):
        """Verify if  user can execute an action over a certain object type.
        Specify at least name or perms.
        
        :param perms: user permissions. Pandas Series with permissions 
                      (pid, oid, type, definition, class, objid, aid, action) [optional]
        :param objtype: object type. Es. 'reosurce', 'service,
        :param definition: object definition. Es. 'container.org.group.vm'                                        
        :param action: object action. Es. *, view, insert, update, delete, use
        :return: list of non redundant permission objids
        :rtype: list
        :raises ApiManagerError: if there are problems retrieving permissions
                                  or user is not enabled to execute action
                                  over object with type specified
        """
        # verify permissions
        self.controller.can('use', self.objtype, definition=self.objdef)
                
        if perms is None:
            try:
                perms = self.get_permissions(self.name)
            except QueryError as ex:
                self.logger.error(ex, exc_info=1)
                raise ApiManagerError(ex)

        try:
            objids = []
            defs = []
            for perm in perms:
                # perm = (pid, oid, type, definition, class, objid, aid, action)
                # Es: (5, 1, 'resource', 'container.org.group.vm', 'Vm', 'c1.o1.g1.*', 6, 'use')
                perm_objtype = perm[2]
                perm_objid = perm[5]
                perm_action = perm[7]
                perm_definition = perm[3]
                
                # no definition is specify
                if definition is not None:
                    # verify object type, definition and action. If they match 
                    # objid to values list
                    if (perm_objtype == objtype and
                        perm_definition == definition and
                        perm_action in ['*', action]):
                        objids.append(perm_objid)
                else:
                    if (perm_objtype == objtype and
                        perm_action in ['*', action]):
                        if perm_definition not in defs:
                            defs.append(perm_definition)

            # loop between object objids, compact objids and verify match
            if len(objids) > 0:
                res = extract(objids)
                self.logger.debug('User %s can %s objects {%s, %s, %s}' % 
                                  (self.name, action, objtype, definition, res))
                return res
            # loop between object definition
            elif len(defs) > 0:
                self.logger.debug('User %s can %s objects {%s, %s}' % 
                                  (self.name, action, objtype, defs))
                return defs
            else:
                raise Exception('User %s can not \'%s\' objects \'%s:%s\'' % 
                                (self.name, action, objtype, definition))
                
            User(self).event('user.can.use', 
                             {'action':action, 'objtype':objtype, 
                              'definition':definition, 'name':self.name, 
                              'perms':perms}, 
                             (True))                 
        except Exception as ex:
            User(self).event('user.can.use', 
                             {'action':action, 'objtype':objtype, 
                              'definition':definition, 'name':self.name, 
                              'perms':perms}, 
                             (False, ex))            
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)        