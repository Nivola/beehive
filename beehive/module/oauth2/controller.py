'''
Created on May 3, 2017

@author: darkbk
'''
import logging
import urllib2
import time
import gevent
import ujson as json
from beecell.auth import extract
from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate, get_value
from beecell.db.manager import SqlManagerError
from beecell.server.uwsgi_server.resource import UwsgiManager, UwsgiManagerError
import os
from inspect import getfile
from datetime import datetime
from flask_babel import Babel
from beecell.flask.render import render_template
from flask.helpers import url_for, send_from_directory
from copy import deepcopy
from oauthlib.oauth2 import WebApplicationServer, \
                            MobileApplicationServer, \
                            LegacyApplicationServer, \
                            BackendApplicationServer
from oauthlib.oauth2 import FatalClientError, OAuth2Error
from beehive.module.auth.controller import AuthController, AuthObject
from beehive.module.oauth2.model import Oauth2DbManager, GrantType
from beehive.module.oauth2.validator import Oauth2RequestValidator
from beehive.module.oauth2.jwt import JwtApplicationServer
from beehive.common.apimanager import ApiManagerError
from beehive.common.data import operation

class Oauth2Controller(AuthController):
    """Oauth2 controller.
    """ 
    version = u'v1.0'
    
    # authorize state
    LOGIN = 0
    SCOPE = 1
    AUTHORIZE = 2
    
    def __init__(self, module):
        AuthController.__init__(self, module)
        
        # get module path 
        path = os.path.dirname(getfile(Oauth2Controller))

        try:
            self.path = path
            self.app = module.api_manager.app
            self.app.template_folder = u'%s/templates' % path
            self.app.static_folder = u'%s/static' % path
            self.app.babel = Babel(app=self.app, default_locale=u'it', 
                                   default_timezone=u'utc')
            
            self.languages = {
                u'en': u'English',
                u'it': u'Italian',
            }
            
            self.authmod = self.module.api_manager.get_module(u'AuthModule')
            
            self.manager = Oauth2DbManager()
        except: pass
    
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        pass
    
    @watch
    def get_server(self, grant_type):
        """
        """
        validator = Oauth2RequestValidator()
        
        if grant_type == GrantType.AUTHORIZATION_CODE:
            server = WebApplicationServer(validator)                
            
        elif grant_type == GrantType.IMPLICIT:
            server = MobileApplicationServer(validator)
        
        elif grant_type == GrantType.RESOURCE_OWNER_PASSWORD_CREDENTIAL:
            server = LegacyApplicationServer(validator)
        
        elif grant_type == GrantType.CLIENT_CRDENTIAL:
            server = BackendApplicationServer(validator)
            
        elif grant_type == GrantType.JWT_BEARER:
            server = JwtApplicationServer(validator)
            
        return server
    
    def authenticate_client(self, uri, http_method, body, headers):
        """Authenticate client and return credentials
        
        :param uri:
        :param http_method:
        :param body:
        :param headers:
        :return: client credentials
        :credentials:

            {u'state': u'0Zf9apA3I9HFPbR2r5sZGDlIgdj9mi', 
             u'redirect_uri': u'https://localhost:7443/authorize', 
             u'response_type': u'code', 
             u'client_id': u'8a994dd1-e96b-4092-8a14-ede3f77d8a2c'
             u'scope': [u'beehive', u'auth']}        
        """
        try:
            # get oauthlib.oauth2 server
            server = self.get_server(GrantType.AUTHORIZATION_CODE)
            
            scopes, credentials = server.validate_authorization_request(
                uri, http_method, body, headers)

            # Not necessarily in session but they need to be
            # accessible in the POST view after form submit.
            credentials.pop(u'request')
            credentials[u'scope'] = scopes
            
            self.logger.debug(u'Validate client credentials %s' % credentials)
            return credentials
        # Errors embedded in the redirect URI back to the client
        except OAuth2Error as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=420)
        
        # Errors that should be shown to the user on the provider website
        except FatalClientError as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=421)
        
        # Errors
        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=400)              

    def get_credentials(self, session):
        """Get client credentials from session
        
        :param session: flask session
        :return: client credentials
        """
        credentials = None
        if u'oauth2_credentials' in session:
            # get credentials
            credentials = session[u'oauth2_credentials']
        self.logger.debug(u'Get client credentials %s in session' % credentials)
        return credentials
    
    def save_credentials(self, session, credentials):
        """Save client credentials in session
        
        :param session: flask session
        :param credentials: client credentials
        :return: True
        """
        session[u'oauth2_credentials'] = credentials 
        self.logger.debug(u'Set client credentials %s in session' % credentials)
        
    def check_credentials(self, session, credentials):
        """Check client credentials in session
        
        :param session: flask session
        :param credentials: client credentials
        :return: True if credentials match. False if session is invalidated
        """
        # get credentials
        session_credentials = session[u'oauth2_credentials']
        
        # check credentials in session meet credentials provided
        if credentials.get(u'client_id') != session_credentials.get(u'client_id') or\
           credentials.get(u'state') != session_credentials.get(u'state'):
            # invalidate session
            self.invalidate_session(session)
            return False
        return True
    
    def invalidate_session(self, session):
        """Remove session from session manager
        
        :param session: flask session
        """
        self.app.session_interface.remove_session(session)
        self.logger.warn(u'Invalidate session %s' % truncate(session))
        return True
    
    def check_login(self, session):
        """
        
        :param session: flask session
        """
        # check resource owner already login
        user = session.get(u'oauth2_user', None)
        if user is not None:
            return user
        return None
    
    def check_login_scopes(self, user):
        """
        """
        user_scope = user.get(u'scope', None)
        if user_scope is not None:
            return user_scope
        return None
    
    def create_authorization(self, uri, http_method, body, headers, scopes, 
                             credentials):
        """Create authorization token 
        """
        try:
            # get oauthlib.oauth2 server
            server = self.get_server(GrantType.AUTHORIZATION_CODE)

            headers, body, status = server.create_authorization_response(
                uri, http_method=http_method, body=body, headers=headers, 
                scopes=scopes, credentials=credentials)

            res = [body, status, headers]
            self.logger.debug(u'Create authorization: %s' % res)
            return res
        
        # Errors embedded in the redirect URI back to the client
        except OAuth2Error as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=420)
        
        # Errors that should be shown to the user on the provider website
        except FatalClientError as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=421)
        
        # Errors
        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=400)

    @watch
    def get_client_scopes(self, session):
        """Get available client scopes to propose resource owner
        
        :param session: flask session
        """
        #validator = Oauth2RequestValidator()
        
        # get client state
        #state = session[u'oauth2_credentials'][u'state']
        
        msg = u''
        # get client_id
        client_id = session[u'oauth2_credentials'][u'client_id']
        # get client scope
        scope = session[u'oauth2_credentials'][u'scope']
        self.logger.debug(u'Get client %s scopes: %s' % (client_id, scope))
        return msg, client_id, scope
    
    @watch
    def set_user_scopes(self, session, scopes):
        """Set user scope in session
        
        :param session: flask session
        :param scopes: list of user scopes
        :return: credentials
        """
        credentials = session[u'oauth2_credentials']
        credentials[u'scope'] = scopes
        user = session[u'oauth2_user']
        user[u'scope'] = scopes

        self.logger.debug(u'Set user %s scopes: %s' % (user[u'name'], scopes))
        return deepcopy(credentials)
    
    @watch
    def create_token(self, uri, http_method, body, headers, session,login_ip):
        """Create access token
        
        :param body: request body
        :param session: flask session 
        :return: {u'res':.., u'code':.., u'headers':..}
        """
        try:
            # {u'code': u'bUCrCB2IMuIowKMt7fllpMh35H2aIY', 
            #  u'client_secret': u'exh7ez922so3eeQjbsJLgiSR3fW3AVc1dsmQiBIi', 
            #  u'grant_type': u'authorization_code', 
            #  u'client_id': u'8a994dd1-e96b-4092-8a14-ede3f77d8a2c', 
            #  u'redirect_uri': u'https://localhost:7443/authorize'}
            
            # get grant type
            #grant_type = request.body[u'grant_type']

            #credentials = session[u'oauth2_credentials']
            #user = session[u'oauth2_user']
            grant_type = get_value(body, u'grant_type', None, exception=True)
            #scope = get_value(body, u'scope', None)
            #state = get_value(body, u'state', None)

            # get oauthlib.oauth2 server
            credentials = None
            server = self.get_server(grant_type)
            headers, body, status = server.create_token_response(
                        uri, http_method, body, headers, credentials)

            # create identity
            data = json.loads(body)
            uid = data[u'access_token']
            user_id = data.pop(u'user')
            timestamp = datetime.now().strftime(u'%y-%m-%d-%H-%M')
            
            # get user
            user = self.manager.get_user(oid=user_id)[0][0]
                     
            # create identity
            identity = {u'uid':uid,
                        u'type':u'oauth2',
                        u'user':{
                            u'id':user_id,
                            u'name':user.name,
                            u'attribute':None,
                            u'active':user.active,
                            u'roles':None,
                            u'perms':None
                        },
                        u'timestamp':timestamp,
                        u'ip':login_ip}
            self.logger.debug(u'Create credentials %s identity: %s' % 
                              (credentials, truncate(identity)))
            
            # set user in thread local variable
            operation.user = (user.name, login_ip, None)            
            
            # save identity in redis
            self.set_identity(uid, identity, expire=True)
            
            return (body, status, headers)
        
        # Errors embedded in the redirect URI back to the client
        except OAuth2Error as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=420)
        
        # Errors that should be shown to the user on the provider website
        except FatalClientError as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=421)
        
        except Exception as e:
            self.logger.error(e, exc_info=True)
            raise ApiManagerError(e, code=400)
    
    #
    # login, logout
    #
    @watch
    def login(self, session, name, domain, password, login_ip):
        """Asymmetric keys authentication login
        
        :param session: flask session
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
        self.validate_login_params(name, domain, password, login_ip)
        
        # check user
        dbuser, dbuser_attribs = self.check_login_user(name, domain, 
                                                   password, login_ip)        
        
        # check user attributes
        
        # login user
        user, attrib = self.base_login(name, domain, password, login_ip, 
                                       dbuser, dbuser_attribs)
        
        #res = {u'uid':id_gen(20),
        #       u'user':user.get_dict(),
        #       u'timestamp':datetime.now().strftime(u'%y-%m-%d-%H-%M')}        
        
        # update session info
        session[u'oauth2_user'] = {u'id':dbuser.id, u'name':dbuser.name}
        
        User(self).event(u'login.oauth2', opts, (True))
        
        return True    
    
    @watch
    def login_domains(self):
        """Get authentication domains
        """
        try:
            auth_providers = self.authmod.authentication_manager.auth_providers
            domains = []
            for domain, auth_provider in auth_providers.iteritems():
                domains.append([domain, auth_provider.__class__.__name__])
            return domains
        except ApiManagerError as ex:
            self.logger.error(u'[%s] %s' % (ex.code, ex.value), exc_info=1)
            raise
    
    @watch
    def login_page(self, redirect_uri):
        """Configure login page
        """
        
        # verify that user is not already authenticated
        # TODO
        
        # get authentication domains
        try:
            domains = self.login_domains()
        except ApiManagerError as ex:
            msg = ex.value 
        
        if redirect_uri is None:
            redirect_uri = u'/%s/sso/identity/summary/' % self.version
        
        return domains, redirect_uri
    
    @watch
    def identity(self, style, token, summary=True):
        msg = None

        # get authentication domains
        try:
            controller = self.authmod.get_controller()
            identity = controller.get_identity(token)
            '''
            {'uid':..., 'user':..., 'timestamp':..., 'pubkey':..., 
             'seckey':...}            
            '''
            
        except ApiManagerError as ex:
            self.logger.error(u'[%s] %s' % (ex.code, ex.value))
            msg = ex.value 
        
        if summary is True:
            self.logger.debug(u'Use page style: %s' % style)    
            return render_template(u'identity.html', 
                                   msg=msg, 
                                   identity=identity,
                                   style=url_for(u'static', filename=style))
        else:
            return identity
        
class Oauth2Object(AuthObject):
    objtype = u'oauth2'
    objdef = u'abstract'
    objdesc = u'Oauth2 abstract object'
    
    @property
    def manager(self):
        return self.controller.manager
    
    

class Oauth2Scope(Oauth2Object):
    objdef = u'Oauth2Scope'
    objdesc = u'Oauth2 Scope'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        Oauth2Object.__init__(self, controller, oid=oid, objid=objid, name=name, 
                              desc=desc, active=active, model=model)
        self.update_object = self.manager.update_scope
        self.delete_object = self.manager.remove_scope
        self.register = True

class Oauth2Token(Oauth2Object):
    objdef = u'Oauth2Token'
    objdesc = u'Oauth2 Token'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        Oauth2Object.__init__(self, controller, oid=oid, objid=objid, name=name, 
                              desc=desc, active=active, model=model)
        self.delete_object = self.manager.remove_token
        
class Oauth2AuthorizationCode(Oauth2Object):
    objdef = u'Oauth2AuthorizationCode'
    objdesc = u'Oauth2 Authorization Code'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        Oauth2Object.__init__(self, controller, oid=oid, objid=objid, name=name, 
                              desc=desc, active=active, model=model)
        self.delete_object = self.manager.remove_authorization_code  
    
class Oauth2Client(Oauth2Object):
    objdef = u'Oauth2Client'
    objdesc = u'Oauth2 Client'
    
    def __init__(self, controller, oid=None, objid=None, name=None, desc=None, 
                 model=None, active=True):
        Oauth2Object.__init__(self, controller, oid=oid, objid=objid, name=name, 
                              desc=desc, active=active, model=model)
        self.update_object = self.manager.update_client
        self.delete_object = self.manager.remove_client
        self.register = True

    @watch
    def info(self):
        """Get oauth2 client info
        
        :return: Dictionary with oauth2 client info.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, 
                                            self.objid, u'view')
           
        creation_date = str2uni(self.model.creation_date\
                                .strftime(u'%d-%m-%y %H:%M:%S'))
        modification_date = str2uni(self.model.modification_date\
                                    .strftime(u'%d-%m-%y %H:%M:%S'))   
        return {
            u'id':self.oid, 
            #u'uuid':self.uuid,    
            u'type':self.objtype, 
            u'definition':self.objdef, 
            u'name':self.name, 
            u'objid':self.objid, 
            u'desc':self.desc,
            u'active':self.active, 
            u'date':{
                u'creation':creation_date,
                u'modified':modification_date
            }
        }
