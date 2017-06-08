'''
Created on Jun 7, 2017

@author: darkbk
'''
import ujson as json
from logging import getLogger
from oauthlib.oauth2.rfc6749.clients.base import Client
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request,\
    parse_token_response
from oauthlib.oauth2.rfc6749 import errors, tokens, utils
from requests_oauthlib.oauth2_session import OAuth2Session
import jwt
from datetime import datetime, timedelta
from time import time
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

logger = getLogger(__name__)

class GrantType(object):
    AUTHORIZATION_CODE = u'authorization_code'
    IMPLICIT = u'implicit'
    RESOURCE_OWNER_PASSWORD_CREDENTIAL = u'resource_owner_password_credentials'
    CLIENT_CRDENTIAL = u'client_credentials'
    JWT_BEARER = u'urn:ietf:params:oauth:grant-type:jwt-bearer'

class OAuth2Error(errors.OAuth2Error):
    def __init__(self, description=None, uri=None, state=None, status_code=None,
                 request=None, error=None):
        self.error = error
        errors.OAuth2Error.__init__(self, description, uri, state, status_code,
                                    request)

class JWTClient(Client):
    """A client that implement the use case 'JWTs as Authorization Grants' of 
    the rfc7523.
    """
    def prepare_request_body(self, body=u'', scope=None, **kwargs):
        """Add the client credentials to the request body.
        """
        grant_type = GrantType.JWT_BEARER
        return prepare_token_request(grant_type, body=body,
                                     scope=scope, **kwargs)
        
    def parse_request_body_response(self, body, scope=None, **kwargs):
        logger.warn(body)
        self.token = self.__parse_token_response(body, scope=scope)
        self._populate_attributes(self.token)
        return self.token     

    def __parse_token_response(self, body, scope=None):
        """Parse the JSON token response body into a dict.
        """
        try:
            params = json.loads(body)
        except ValueError:
    
            # Fall back to URL-encoded string, to support old implementations,
            # including (at time of writing) Facebook. See:
            #   https://github.com/idan/oauthlib/issues/267
    
            params = dict(urlparse.parse_qsl(body))
            for key in ('expires_in', 'expires'):
                if key in params:  # cast a couple things to int
                    params[key] = int(params[key])
    
        if 'scope' in params:
            params['scope'] = utils.scope_to_list(params['scope'])
    
        if 'expires' in params:
            params['expires_in'] = params.pop('expires')
    
        if 'expires_in' in params:
            params['expires_at'] = time() + int(params['expires_in'])
    
        params = tokens.OAuth2Token(params, old_scope=scope)
        self.__validate_token_parameters(params)
        return params
    
    def __validate_token_parameters(self, params):
        """Ensures token precence, token type, expiration and scope in params."""
        if 'error' in params:
            kwargs = {
                'description': params.get('error_description'),
                'uri': params.get('error_uri'),
                'state': params.get('state'),
                'error': params.get('error')
            }
            raise OAuth2Error(**kwargs)
    
        if not 'access_token' in params:
            raise errors.MissingTokenError(description="Missing access token parameter.")
    
    @staticmethod
    def create_token(client_id, client_email, client_scope, private_key, 
                     client_token_uri, aud, user, pwd):
        """Create access token using jwt grant
        
        :return: token
        """
        client = JWTClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        
        now = datetime.utcnow()
        claims = {
            u'iss':client_email,
            u'sub':u'%s:%s' % (user, pwd),
            u'scope':client_scope,
            u'aud':aud,
            u'exp':now + timedelta(seconds=60),
            u'iat':now,
            u'nbf':now
        }
        #priv_key = RSA.importKey(private_key)
        encoded = jwt.encode(claims, private_key, algorithm=u'RS512')
        #encoded = ''
        res = client.prepare_request_body(assertion=encoded, client_id=client_id)
        token = oauth.fetch_token(token_url=client_token_uri, 
                                  body=res, verify=False)
        logger.debug(u'Get token : %s' % token)
        return token
