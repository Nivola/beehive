# -*- coding: utf-8 -*-
'''
Created on May 3, 2017

@author: darkbk
'''
import logging
import pandas as pd
from datetime import datetime, timedelta
from passlib.hash import sha256_crypt
from beecell.auth import AuthDbManagerError, AbstractAuthDbManager
from sqlalchemy import Column, Integer, String, Boolean, Table, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.sql import text
from beecell.perf import watch
from beecell.simple import truncate, id_gen
from gibboncloudapi.util.data import operation
from uuid import uuid4
from beecell.db import ModelError
from beehive.common.data import query, transaction

Base = declarative_base()

logger = logging.getLogger(__name__)

# Many-to-Many Relationship
consumer_scope = Table('oauth2_client_scope', Base.metadata,
    Column('consumer_id', Integer(), ForeignKey('oauth2_client.id')),
    Column('scope_id', Integer(), ForeignKey('oauth2_scope.id')))

token_scope = Table('oauth2_token_scope', Base.metadata,
    Column('token_id', Integer(), ForeignKey('oauth2_token.id')),
    Column('scope_id', Integer(), ForeignKey('oauth2_scope.id')))

authorization_scope = Table('oauth2_authorization_scope', Base.metadata,
    Column('authorization_id', Integer(), ForeignKey('oauth2_authorization_code.id')),
    Column('scope_id', Integer(), ForeignKey('oauth2_scope.id')))

class Oauth2User(Base):
    """This model map User in auth module
    """
    __tablename__ = 'user'
    __table_args__ = {'mysql_engine':'InnoDB'}    
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique = True)
    objid = Column(String(400))
    name = Column(String(50), unique=True)
    description = Column(String(255))
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    password = Column(String(150))
    active = Column(Boolean())

    def __init__(self, objid, username, roles=[], active=True, 
                       password=None, description=''):
        self.uuid = str(uuid4())
        self.objid = objid
        self.name = username
        self.role = roles
        self.active = active
        self.description = description
        
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date
        
        if password is not None:
            # generate new salt, and hash a password 
            self.password = sha256_crypt.encrypt(password)
    
    def __repr__(self):
        return "<Oauth2User id='%s' name='%s' desc='%s' active='%s'>" % (
                    self.id, self.name, self.description, self.active)

    @watch
    def _check_password(self, password):
        # verifying the password
        res = sha256_crypt.verify(password, self.password)
        return res

# Oauth2 Scope
class Oauth2Scope(Base):
    __tablename__ = 'oauth2_scope'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    objid = Column(String(150), unique = True)
    value = Column(String(100), unique = True)
    desc = Column(String(100))

    def __init__(self, objid, value, desc):
        """
        :param objid: scope objid
        :param value: scope value
        :param desc: scope description
        """        
        self.objid = objid
        self.value = value
        self.desc = desc

    def __repr__(self):
        return "<Oauth2Scope id='%s' value='%s' desc='%s')>" % ( \
                    self.id, self.value, self.desc)

# Oauth2 Consumer
class Oauth2Client(Base):
    __tablename__ = 'oauth2_client'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    objid = Column(String(150), unique = True)
    name = Column(String(80), unique=True)
    description = Column(String(255))    
    client_id = Column(String(100), unique=True)
    client_secret = Column(String(200), unique=True)
    private_key = Column(String(4096))
    public_key = Column(String(4096))
    user_id = Column(Integer(), ForeignKey('user.id'))
    user = relationship("Oauth2User")
    grant_type = Column(String(50), unique=True)
    response_type = Column(String(10))
    scope = relationship('Oauth2Scope', secondary=consumer_scope,
                         backref=backref('oauth2_client', lazy='dynamic'))
    redirect_uri = Column(String(256))
    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    active = Column(Boolean())

    def __init__(self, objid, name, client_id, client_secret, user_id, 
                 grant_type, redirect_uri, response_type=u'code', scope=[],
                 description= u'', active=True, private_key=None, public_key=None):
        """
        :param objid: client objid
        :param name: client name
        :param client_id: client id 
        :param client_secret: client secret used for all grant type except JWT
        :param user_id: user id associated to client
        :param description: client description
        :param private_key: private key used by Jwt grant type
        :param public_key: public key used by Jwt grant type
        :param grant_type: The grant type the client may utilize. This should 
                           only be one per client as each grant type has 
                           different security properties and it is best to keep 
                           them separate to avoid mistakes.
        :param response_type: If using a grant type with an associated response 
                              type (eg. Authorization Code Grant) or using a 
                              grant which only utilizes response types (eg. 
                              Implicit Grant). [default=code]
        :param scope: The list of scopes the client may request access to. If 
                      you allow multiple types of grants this will vary related 
                      to their different security properties. For example, the 
                      Implicit Grant might only allow read-only scopes but the 
                      Authorization Grant also allow writes.
        :param redirect_uri: These are the absolute URIs that a client may use 
                             to redirect to after authorization. You should 
                             never allow a client to redirect to a URI that has 
                             not previously been registered.
        :param active: True if client is active. False otherwise
        """
        self.objid = objid
        self.name = name
        self.description = description
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.grant_type = grant_type
        self.response_type = response_type
        self.redirect_uri = redirect_uri
        self.active = active
        self.private_key = private_key
        self.public_key = public_key
        self.scope = scope
        
        self.creation_date = datetime.today()
        self.modification_date = self.creation_date        
    
    def __repr__(self):
        return "<Oauth2Client id='%s' name='%s' desc='%s')>" % (
                    self.id, self.name, self.description)

# Oauth2 Token
class Oauth2Token(Base):
    """The most common type of OAuth 2 token. Through the documentation this 
    will be considered an object with several properties, such as token type 
    and expiration date, and distinct from the access token it contains. Think 
    of OAuth 2 tokens as containers and access tokens and refresh tokens as text.
    """
    __tablename__ = 'oauth2_token'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    client_id = Column(Integer(), ForeignKey('oauth2_client.id'))
    client = relationship("Oauth2Client")    
    user_id = Column(Integer(), ForeignKey('user.id'))
    user = relationship("Oauth2User")
    scope = relationship('Oauth2Scope', secondary=token_scope,
                         backref=backref('oauth2_token', lazy='dynamic'))
    access_token = Column(String(100), unique = True)
    refresh_token = Column(String(100), unique = True)
    expires_at = Column(DateTime())

    def __init__(self, client, user, access_token, refresh_token, expires_in):
        """
        :param client: Association with the client to whom the token was given.
        :param user: Association with the user to which protected resources 
                     this token grants access.
        :param access_token: An unguessable unique string of characters.
        :param refresh_token: An unguessable unique string of characters. This token 
                        is only supplied to confidential clients. For example 
                        the Authorization Code Grant or the Resource Owner 
                        Password Credentials Grant.
        :param expires_in: Exact time of expiration. Commonly this is one hour after 
                           creation.
        """
        self.client = client
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token
        #self.expires_at = expires_at
        self.expires_at = datetime.today() + timedelta(seconds=expires_in)

    def __repr__(self):
        return "<Oauth2Token id='%s' client_id='%s' user_id='%s' scope='%s' "\
               "access_token='%s', refresh_token='%s' expires_at='%s')>" % (
                self.id, self.client_id, self.user_id, self.scope, 
                self.access_token, self.refresh_token, self.expires_at)

# Oauth2 authorization code
class Oauth2AuthorizationCode(Base):
    """This is specific to the Authorization Code grant and represent the 
    temporary credential granted to the client upon successful authorization. 
    It will later be exchanged for an access token, when that is done it should 
    cease to exist. It should have a limited life time, less than ten minutes. 
    This model is similar to the Bearer Token as it mainly acts a temporary 
    storage of properties to later be transferred to the token.
    """
    __tablename__ = 'oauth2_authorization_code'
    __table_args__ = {'mysql_engine':'InnoDB'}
        
    id = Column(Integer(), primary_key=True)
    client_id = Column(Integer(), ForeignKey('oauth2_client.id'))
    client = relationship("Oauth2Client")  
    user_id = Column(Integer(), ForeignKey('user.id'))
    user = relationship("Oauth2User")
    scope = relationship('Oauth2Scope', secondary=authorization_scope,
                         backref=backref('oauth2_authorization_code', 
                                         lazy='dynamic'))
    code = Column(String(100), unique = True)
    expires_at = Column(DateTime())
    redirect_uri = Column(String(256))

    def __init__(self, client, user, code, redirect_uri):
        """
        :param client: Association with the client to whom the token was given.
        :param user: Association with the user to which protected resources 
                     this token grants access.
        :param code: An unguessable unique string of characters.
        :param expire: Exact time of expiration. Commonly this is one hour after 
                       creation.
        :param redirect_uri: These are the absolute URIs that a client may use 
                             to redirect to after authorization. You should 
                             never allow a client to redirect to a URI that has 
                             not previously been registered.                       
        """
        self.client = client
        self.user = user
        self.code = code
        self.redirect_uri = redirect_uri
        self.expires_at = datetime.today() + timedelta(minutes=60)
        
    def __repr__(self):
        return "<Oauth2AuthorizationCode id='%s' client_id='%s' user_id='%s' "\
               "scope='%s' redirect_uri='%s')>" % (
                self.id, self.client_id, self.user_id, self.scope, 
                self.redirect_uri)        

class GrantType(object):
    AUTHORIZATION_CODE = 'authorization_code'
    IMPLICIT = 'implicit'
    RESOURCE_OWNER_PASSWORD_CREDENTIAL = 'resource_owner_password_credentials'
    CLIENT_CRDENTIAL = 'client_credentials'
    JWT_BEARER = 'urn:ietf:params:oauth:grant-type:jwt-bearer'    

class Oauth2DbManager(AbstractAuthDbManager):
    """
    According to http://tools.ietf.org/html/rfc6749
    
    Authorization Grant

    An authorization grant is a credential representing the resource
    owner's authorization (to access its protected resources) used by the
    client to obtain an access token.  This specification defines four
    grant types: authorization code, implicit, resource owner password
    credentials, and client credentials, as well as an extensibility
    mechanism for defining additional types.    
    """
    logger = logging.getLogger('beehive.oauth2')

    def __init__(self, session=None):
        """ """
        self._session = session

    def __del__(self):
        pass

    def __repr__(self):
        return "<Oauth2DbManager id='%s'>" % id(self)

    def get_session(self):
        if self._session is None:
            return operation.session
        else:
            return self._session

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.create_all(engine)
            logger.info('Create oauth2 tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise AuthDbManagerError(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            Base.metadata.drop_all(engine)
            logger.info('Remove oauth2 tables from : %s' % db_uri)
            del engine
        except exc.DBAPIError, e:
            raise AuthDbManagerError(e)

    '''
    def set_initial_data(self):
        """Set initial data.
        """
        @transaction(self.get_session())
        def func(session):
            # object actions
            actions = ['*', 'view', 'insert', 'update', 'delete', 'use']
            data = []
            for item in actions:
                data.append(SysObjectAction(item))
            session.add_all(data) 
            self.logger.debug("Add object actions: %s" % actions)
        return func()'''

    #
    # scope
    #
    @query
    def count_scopes(self):
        """Get scopes count.
        
        :rtype: scopes number
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(Oauth2Scope).count()
            
        self.logger.debug(u'Count scopes: %s' % res)
        return res    
    
    @query
    def get_scopes(self, oid=None, value=None):
        """Get scopes.
        
        :param oid str: scope id. [optional]
        :param value str: scope value. [optional]
        :rtype: list of :class:`Oauth2Scope`
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Scope).filter_by(id=oid)
        elif value is not None:
            res = session.query(Oauth2Scope).filter_by(value=value)            
        else:
            res = session.query(Oauth2Scope)
        
        res = res.all()

        if len(res) == 0:
            self.logger.error(u'No scopes found')
            raise ModelError(u'No scopes found', code=404)
                 
        self.logger.debug(u'Get scopes: %s' % truncate(res))
        return res

    @transaction
    def add_scope(self, value, desc):
        """Add a scope.
        
        :param value str: scope value.
        :param desc str: desc
        :return: new scope
        :rtype: Oauth2Scope
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()        
        record = Oauth2Scope(value, desc)
        session.add(record)
        session.flush()
        self.logger.debug(u'Add scope: %s' % record)
        return record
    
    @transaction
    def update_scope(self, oid=None, value=None, new_value=None, new_desc=None):
        """Update scope.

        :param oid str: scope id. [optional]
        :param value str: scope value. [optional]
        :param new_value str: new scope value. [optional]
        :param new_desc str: new scope desc. [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`        
        """        
        session = self.get_session()
        # get container
        if oid is not None:  
            rec = session.query(Oauth2Scope).filter_by(id=oid)
        elif value is not None:
            rec = session.query(Oauth2Scope).filter_by(value=value)                
        else:
            self.logger.error(u'Specify oid or value')
            raise ModelError(u'Specify oid or value')

        scope = rec.first()
        if scope is None:
            self.logger.error(u'No scope found')
            raise ModelError(u'No scope found', code=404)
        
        # create data dict with update
        data = {}
        if new_value is not None:
            data['value'] = new_value
        if new_desc is not None:
            data['desc'] = new_desc

        res = rec.update(data)
            
        self.logger.debug(u'Update scope %s with data: %s' % (scope, data))
        return True    
    
    @transaction
    def remove_scope(self, oid=None, value=None):
        """Remove scope.
        
        :param oid str: scope id.
        :param value str: scope value.
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Scope).filter_by(id=oid).first()
        elif value is not None:
            res = session.query(Oauth2Scope).filter_by(value=value).first()                           
        else:
            self.logger.error(u'Specify at least one params')
            raise ModelError(u'Specify at least one params')
        
        if res is not None:
            session.delete(res)
        else:
            self.logger.error(u'No scope found')
            raise ModelError(u'No scope found', code=404)
        self.logger.debug(u'Remove scope: %s' % res)
        return True

    #
    # client
    #
    @query
    def count_clients(self):
        """Get clients count.
        
        :rtype: clients number
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(Oauth2Client).count()
            
        self.logger.debug(u'Count clients: %s' % res)
        return res    
    
    @query
    def get_clients(self, oid=None, name=None, client_id=None):
        """Get clients.
        
        :param oid str: client database id. [optional]
        :param name str: client name. [optional]
        :param client_id str: client id. [optional]
        :rtype: list of :class:`ContainerType`
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Client).filter_by(id=oid)
        elif name is not None:
            res = session.query(Oauth2Client).filter_by(name=name)
        elif client_id is not None:
            res = session.query(Oauth2Client).filter_by(client_id=client_id)       
        else:
            res = session.query(Oauth2Client)
            
        res = res.all()
            
        if len(res) == 0:
            self.logger.error(u'No clients found')
            raise ModelError(u'No clients found', code=404)
                 
        self.logger.debug(u'Get clients: %s' % truncate(res))
        return res

    @transaction
    def add_client(self, objid, name, client_id, client_secret, user_id, 
                   grant_type, redirect_uri, response_type=u'code', scope=[],
                   description= u'', active=True, private_key=None, public_key=None):
        """Create new client.
        
        :param objid: client objid
        :param name: client name
        :param client_id: client id 
        :param client_secret: client secret used for all grant type except JWT
        :param user_id: user id associated to client
        :param description: client description
        :param private_key: private key used by Jwt grant type
        :param public_key: public key used by Jwt grant type
        :param grant_type: The grant type the client may utilize. This should 
                           only be one per client as each grant type has 
                           different security properties and it is best to keep 
                           them separate to avoid mistakes.
        :param response_type: If using a grant type with an associated response 
                              type (eg. Authorization Code Grant) or using a 
                              grant which only utilizes response types (eg. 
                              Implicit Grant). [default=code]
        :param scope: The list of scopes the client may request access to. If 
                      you allow multiple types of grants this will vary related 
                      to their different security properties. For example, the 
                      Implicit Grant might only allow read-only scopes but the 
                      Authorization Grant also allow writes.
        :param redirect_uri: These are the absolute URIs that a client may use 
                             to redirect to after authorization. You should 
                             never allow a client to redirect to a URI that has 
                             not previously been registered.
        :param active: True if client is active. False otherwise
        :param value str: client value.
        :param objid str: objid
        
        :return: new client
        :rtype: Oauth2Client
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()        
        record = Oauth2Client(objid, name, client_id, client_secret, user_id, 
                              grant_type, redirect_uri, response_type, scope,
                              description, active, private_key, public_key)
        session.add(record)
        session.flush()
        self.logger.debug(u'Add client: %s' % record)
        return record
    
    @transaction
    def update_client(self, oid=None, value=None, new_value=None):
        """Update client.
        TODO:
        :param oid str: client id. [optional]
        :param value str: client value. [optional]
        :param new_value str: new client value. [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`        
        """        
        session = self.get_session()
        # get container
        if oid is not None:  
            rec = session.query(Oauth2Client).filter_by(id=oid)
        elif value is not None:
            rec = session.query(Oauth2Client).filter_by(value=value)                
        else:
            self.logger.error(u'Specify oid or value')
            raise ModelError(u'Specify oid or value')

        client = rec.first()
        if client is None:
            self.logger.error(u'No client found')
            raise ModelError(u'No client found', code=404)
        
        # create data dict with update
        data = {}    
        if new_value is not None:
            data['value'] = new_value

        res = rec.update(data)
            
        self.logger.debug(u'Update client %s with data: %s' % (client, data))
        return True
    
    @transaction
    def remove_client(self, oid=None, name=None, client_id=None):
        """Delete client.
        
        :param oid str: client database id. [optional]
        :param name str: client name. [optional]
        :param client_id str: client id. [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Client).filter_by(id=oid).first()
        elif name is not None:
            res = session.query(Oauth2Client).filter_by(name=name).first()
        elif client_id is not None:
            res = session.query(Oauth2Client).filter_by(client_id=client_id).first()                       
        else:
            self.logger.error(u'Specify at least one params')
            raise ModelError(u'Specify at least one params')
        
        if res is not None:
            session.delete(res)
        else:
            self.logger.error(u'No client found')
            raise ModelError(u'No client found', code=404)
        self.logger.debug(u'Remove client: %s' % res)
        return True

    #
    # user
    #
    @query
    def get_user(self, name=None, oid=None, objid=None, uuid=None,
                 page=0, size=10, order=u'DESC', field=u'id'):
        """Get user with certain name. If name is not specified return all the 
        users.
        
        :param oid: user id [optional]
        :param objid: user objid [optional]
        :param uuid: user uuid [optional]
        :param name: name of the user [Optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]        
        :return: User instances
        :rtype: :class:`User`
        :raises QueryError: raise :class:`QueryError`     
        """
        session = self.get_session()
        if oid is not None:
            user = session.query(Oauth2User).filter_by(id=oid)
        elif objid is not None:
            user = session.query(Oauth2User).filter_by(objid=objid)
        elif uuid is not None:
            user = session.query(Oauth2User).filter_by(uuid=uuid)            
        elif name is not None:
            user = session.query(Oauth2User).filter_by(name=name)
        else:
            user = session.query(Oauth2User)
        
        total = user.count()
        
        start = size * page
        end = size * (page + 1)
        user = user.order_by(u'%s %s' % (field, order))[start:end]
        
        self.logger.debug(u'Get users: %s' % truncate(user))
        return user, total

    @transaction
    def add_user(self, objid, username, roles, active=True, 
                       password=None, description=''):
        """Add user.
        
        :param objid:
        :param username: name of the user
        :param usertype: type of the user. Can be DBUSER, LDAPUSER
        :param roles: List with Role instances
        :param active: User status. If True user is active [Default=True]
        :param description: User description. [Optional]
        :param password: Password of the user. Set only for user like 
                         <user>@local [Optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        # verify if object already exists
        user = session.query(Oauth2User).filter_by(name=username).first()
        if user is not None:
            self.logger.error(u'User %s already exists' % user)
            raise ModelError(u'User %s already exists' % user, code=409)  
        
        data = Oauth2User(objid, username, roles, active=active, 
                          password=password, description=description)
        session.add(data)
        session.flush()
        self.logger.debug('Add user: %s' % (data))
        return data
    
    @transaction
    def remove_user(self, user_id=None, username=None):
        """Remove a user. Specify at least user id or user name.
        
        :param user_id: id of the user [optional]
        :param username: name of user [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if user_id is not None:  
            user = session.query(Oauth2User).filter_by(id=user_id).first()
        elif username is not None:
            user = session.query(Oauth2User).filter_by(name=username).first()
        
        if user is None:
            self.logger.error('User %s/%s does not exist' % (user_id, username))
            raise ModelError('User %s/%s does not exist' % (user_id, username))
        
        # delete object type
        session.delete(user)
        
        self.logger.debug('Remove user: %s' % (user))
        return True    

    @query
    def verify_user_password(self, user, password):
        """Verify user password.
        
        :param user: Orm User istance
        :param password: Password to verify
        :return: True if password is correct, False otherwise.
        :rtype: bool
        :raises QueryError: raise :class:`QueryError`      
        """
        # verifying the password
        res = user._check_password(password)
        
        self.logger.debug(u'Verify user %s password: %s' % (user, res))
        return res

    #
    # token
    #
    @query
    def count_tokens(self):
        """Get tokens count.
        
        :rtype: tokens number
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(Oauth2Token).count()
            
        self.logger.debug(u'Count tokens: %s' % res)
        return res    
    
    @query
    def get_tokens(self, oid=None, client_id=None, user_id=None,
                   access_token=None, refresh_token=None, expires_at=None):
        """Get tokens.
        
        :param oid: token database id. [optional]
        :param client_id: token client_id. [optional]
        :param user_id: user_id. [optional]
        :param access_token: access_token. [optional]
        :param refresh_token: refresh_token. [optional]
        :param expires_at: filter token by expire date. 
            If token expire time < expires_at token is not returned. [optional]
        :rtype: list of :class:`ContainerType`
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Token).filter_by(id=oid)
        elif client_id is not None:
            res = session.query(Oauth2Token).filter_by(client_id=client_id)
        elif user_id is not None:
            res = session.query(Oauth2Token).filter_by(user_id=user_id)
        elif access_token is not None:
            res = session.query(Oauth2Token).filter_by(access_token=access_token) 
        elif refresh_token is not None:
            res = session.query(Oauth2Token).filter_by(refresh_token=refresh_token)
        elif expires_at is not None:
            res = session.query(Oauth2Token).filter_by(expires_at>expires_at)            
        else:
            res = session.query(Oauth2Token)
            
        res = res.all()
            
        if len(res) == 0:
            self.logger.error(u'No tokens found')
            raise ModelError(u'No tokens found', code=404)
                 
        self.logger.debug(u'Get tokens: %s' % truncate(res))
        return res

    @transaction
    def add_token(self, client, user, access_token, refresh_token, expires_in):
        """Create new token.
        
        :param client: Association with the client to whom the token was given.
        :param user: Association with the user to which protected resources 
                     this token grants access.
        :param access_token: An unguessable unique string of characters.
        :param refresh_token: An unguessable unique string of characters. This token 
                        is only supplied to confidential clients. For example 
                        the Authorization Code Grant or the Resource Owner 
                        Password Credentials Grant.
        :param expires_in: Exact time of expiration. Commonly this is one hour after 
                           creation.
        :return: new token
        :rtype: Oauth2Token
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()        
        record = Oauth2Token(client, user, access_token, refresh_token, expires_in)
        session.add(record)
        session.flush()
        self.logger.debug(u'Add token: %s' % record)
        return record
    
    @transaction
    def remove_token(self, oid=None, access_token=None):
        """Delete token.
        
        :param oid str: token database id. [optional]
        :param access_token str: access_token. [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2Token).filter_by(id=oid).first()
        elif access_token is not None:
            res = session.query(Oauth2Token).filter_by(access_token=access_token).first()                    
        else:
            self.logger.error(u'Specify at least one params')
            raise ModelError(u'Specify at least one params')
        
        if res is not None:
            session.delete(res)
        else:
            self.logger.error(u'No token found')
            raise ModelError(u'No token found', code=404)
        self.logger.debug(u'Remove token: %s' % res)
        return True
    
    #
    # authorization_code
    #
    @query
    def count_authorization_codes(self):
        """Get authorization_codes count.
        
        :rtype: authorization_codes number
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(Oauth2AuthorizationCode).count()
            
        self.logger.debug(u'Count authorization_codes: %s' % res)
        return res    
    
    @query
    def get_authorization_codes(self, oid=None, name=None, authorization_code_id=None):
        """Get authorization_codes.
        
        :param oid str: authorization_code database id. [optional]
        :param name str: authorization_code name. [optional]
        :param authorization_code_id str: authorization_code id. [optional]
        :rtype: list of :class:`ContainerType`
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2AuthorizationCode).filter_by(id=oid)
        elif name is not None:
            res = session.query(Oauth2AuthorizationCode).filter_by(name=name)
        elif authorization_code_id is not None:
            res = session.query(Oauth2AuthorizationCode).filter_by(authorization_code_id=authorization_code_id)       
        else:
            res = session.query(Oauth2AuthorizationCode)
            
        res = res.all()
            
        if len(res) == 0:
            self.logger.error(u'No authorization_codes found')
            raise ModelError(u'No authorization_codes found', code=404)
                 
        self.logger.debug(u'Get authorization_codes: %s' % truncate(res))
        return res

    @transaction
    def add_authorization_code(self, objid, name, authorization_code_id, authorization_code_secret, user_id, 
                   grant_type, redirect_uri, response_type=u'code', scope=[],
                   description= u'', active=True, private_key=None, public_key=None):
        """Create new authorization_code.
        
        :param objid: authorization_code objid
        :param name: authorization_code name
        :param authorization_code_id: authorization_code id 
        :param authorization_code_secret: authorization_code secret used for all grant type except JWT
        :param user_id: user id associated to authorization_code
        :param description: authorization_code description
        :param private_key: private key used by Jwt grant type
        :param public_key: public key used by Jwt grant type
        :param grant_type: The grant type the authorization_code may utilize. This should 
                           only be one per authorization_code as each grant type has 
                           different security properties and it is best to keep 
                           them separate to avoid mistakes.
        :param response_type: If using a grant type with an associated response 
                              type (eg. Authorization Code Grant) or using a 
                              grant which only utilizes response types (eg. 
                              Implicit Grant). [default=code]
        :param scope: The list of scopes the authorization_code may request access to. If 
                      you allow multiple types of grants this will vary related 
                      to their different security properties. For example, the 
                      Implicit Grant might only allow read-only scopes but the 
                      Authorization Grant also allow writes.
        :param redirect_uri: These are the absolute URIs that a authorization_code may use 
                             to redirect to after authorization. You should 
                             never allow a authorization_code to redirect to a URI that has 
                             not previously been registered.
        :param active: True if authorization_code is active. False otherwise
        :param value str: authorization_code value.
        :param objid str: objid
        
        :return: new authorization_code
        :rtype: Oauth2AuthorizationCode
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()        
        record = Oauth2AuthorizationCode(objid, name, authorization_code_id, authorization_code_secret, user_id, 
                              grant_type, redirect_uri, response_type, scope,
                              description, active, private_key, public_key)
        session.add(record)
        session.flush()
        self.logger.debug(u'Add authorization_code: %s' % record)
        return record
    
    @transaction
    def remove_authorization_code(self, oid=None, name=None, authorization_code_id=None):
        """Delete authorization_code.
        
        :param oid str: authorization_code database id. [optional]
        :param name str: authorization_code name. [optional]
        :param authorization_code_id str: authorization_code id. [optional]
        :return: True if operation is successful, False otherwise
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        if oid is not None:  
            res = session.query(Oauth2AuthorizationCode).filter_by(id=oid).first()
        elif name is not None:
            res = session.query(Oauth2AuthorizationCode).filter_by(name=name).first()
        elif authorization_code_id is not None:
            res = session.query(Oauth2AuthorizationCode).filter_by(authorization_code_id=authorization_code_id).first()                       
        else:
            self.logger.error(u'Specify at least one params')
            raise ModelError(u'Specify at least one params')
        
        if res is not None:
            session.delete(res)
        else:
            self.logger.error(u'No authorization_code found')
            raise ModelError(u'No authorization_code found', code=404)
        self.logger.debug(u'Remove authorization_code: %s' % res)
        return True
    
    
    


