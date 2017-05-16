'''
Created on May 3, 2017

@author: darkbk
'''
from __future__ import absolute_import, unicode_literals
from urllib import quote
from oauthlib.oauth2.rfc6749.clients.base import Client
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request
from oauthlib.oauth2.rfc6749.parameters import parse_token_response
from oauthlib.oauth2.rfc6749.endpoints.token import TokenEndpoint
from oauthlib.oauth1.rfc5849.endpoints.resource import ResourceEndpoint
from oauthlib.oauth2.rfc6749.endpoints.revocation import RevocationEndpoint
from oauthlib.oauth2.rfc6749.tokens import BearerToken
from oauthlib.oauth2.rfc6749.grant_types.client_credentials import ClientCredentialsGrant
from gibboncloudapi.module.oauth2.model import GrantType

class JWTClient(Client):
    """A client that implement the use case 'JWTs as Authorization Grants' of 
    the rfc7523.
    """

    def prepare_request_body(self, body='', scope=None, **kwargs):
        """Add the client credentials to the request body.

        The client makes a request to the token endpoint by adding the
        following parameters using the "application/x-www-form-urlencoded"
        format per `Appendix B`_ in the HTTP request entity-body:

        :param scope:   The scope of the access request as described by
                        `Section 3.3`_.
        :param kwargs:  Extra credentials to include in the token request.

        The client MUST authenticate with the authorization server as
        described in `Section 3.2.1`_.

        The prepared body will include all provided credentials as well as
        the ``grant_type`` parameter set to ``client_credentials``::

            >>> from oauthlib.oauth2 import BackendApplicationClient
            >>> client = BackendApplicationClient('your_id')
            >>> client.prepare_request_body(scope=['hello', 'world'])
            'grant_type=client_credentials&scope=hello+world'

        .. _`Appendix B`: http://tools.ietf.org/html/rfc6749#appendix-B
        .. _`Section 3.3`: http://tools.ietf.org/html/rfc6749#section-3.3
        .. _`Section 3.2.1`: http://tools.ietf.org/html/rfc6749#section-3.2.1
        """
        grant_type = GrantType.JWT_BEARER
        return prepare_token_request(grant_type, body=body,
                                     scope=scope, **kwargs)

class JwtApplicationServer(TokenEndpoint, ResourceEndpoint,
        RevocationEndpoint):
    """An all-in-one endpoint featuring Client Credentials grant and Bearer tokens."""

    def __init__(self, request_validator, token_generator=None,
            token_expires_in=None, **kwargs):
        """Construct a client credentials grant server.

        :param request_validator: An implementation of
                                  oauthlib.oauth2.RequestValidator.
        :param token_expires_in: An int or a function to generate a token
                                 expiration offset (in seconds) given a
                                 oauthlib.common.Request object.
        :param token_generator: A function to generate a token from a request.
        :param kwargs: Extra parameters to pass to authorization-,
                       token-, resource-, and revocation-endpoint constructors.
        """
        credentials_grant = ClientCredentialsGrant(request_validator)
        bearer = BearerToken(request_validator, token_generator,
                expires_in=token_expires_in)
        TokenEndpoint.__init__(self, default_grant_type='client_credentials',
                grant_types={'client_credentials': credentials_grant},
                default_token_type=bearer)
        ResourceEndpoint.__init__(self, default_token='Bearer',
                token_types={'Bearer': bearer})
        RevocationEndpoint.__init__(self, request_validator,
                supported_token_types=['access_token'])