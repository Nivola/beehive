# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import ujson as json
from logging import getLogger
from oauthlib.oauth2.rfc6749.clients.base import Client
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request
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
    AUTHORIZATION_CODE = "authorization_code"
    IMPLICIT = "implicit"
    RESOURCE_OWNER_PASSWORD_CREDENTIAL = "resource_owner_password_credentials"
    CLIENT_CRDENTIAL = "client_credentials"
    JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"


class OAuth2Error(errors.OAuth2Error):
    def __init__(
        self,
        description=None,
        uri=None,
        state=None,
        status_code=None,
        request=None,
        error=None,
    ):
        self.error = error
        errors.OAuth2Error.__init__(self, description, uri, state, status_code, request)


class JWTClient(Client):
    """A client that implement the use case 'JWTs as Authorization Grants' of  the rfc7523."""

    def prepare_request_body(self, body="", scope=None, **kwargs):
        """Add the client credentials to the request body

        :param body: request body
        :param scope: oauth2 scope
        :param kwargs: key value args
        :return:
        """
        grant_type = GrantType.JWT_BEARER
        return prepare_token_request(grant_type, body=body, scope=scope, **kwargs)

    def parse_request_body_response(self, body, scope=None, **kwargs):
        """Parse request body response

        :param body: request body
        :param scope: oauth2 scope
        :param kwargs: key value args
        :return:
        """
        self.token = self.__parse_token_response(body, scope=scope)
        # self._populate_attributes(self.token)
        self.populate_token_attributes(self.token)
        return self.token

    def __parse_token_response(self, body, scope=None):
        """Parse the JSON token response body into a dict.

        :param body: request body
        :param scope: oauth2 scope
        """
        try:
            params = json.loads(body)
        except ValueError:
            # Fall back to URL-encoded string, to support old implementations,
            # including (at time of writing) Facebook. See:
            #   https://github.com/idan/oauthlib/issues/267

            params = dict(urlparse.parse_qsl(body))
            for key in ("expires_in", "expires"):
                if key in params:  # cast a couple things to int
                    params[key] = int(params[key])

        if "scope" in params:
            params["scope"] = utils.scope_to_list(params["scope"])

        if "expires" in params:
            params["expires_in"] = params.pop("expires")

        if "expires_in" in params:
            params["expires_at"] = time() + int(params["expires_in"])

        params = tokens.OAuth2Token(params, old_scope=scope)
        self.__validate_token_parameters(params)
        return params

    def __validate_token_parameters(self, params):
        """Ensures token precence, token type, expiration and scope in params

        :param params: input params to validate
        """
        if "error" in params:
            kwargs = {
                "description": params.get("error_description"),
                "uri": params.get("error_uri"),
                "state": params.get("state"),
                "error": params.get("error"),
            }
            raise OAuth2Error(**kwargs)

        if not "access_token" in params:
            raise errors.MissingTokenError(description="Missing access token parameter.")

    @staticmethod
    def create_token(client_id, client_email, client_scope, private_key, client_token_uri, sub):
        """Create access token using jwt grant

        :param client_id: client uuid
        :param client_email: client email
        :param client_scope: oauth2 scope
        :param private_key: private key
        :param client_token_uri: token uri
        :param sub: sub field
        :return: token
        """
        client = JWTClient(client_id=client_id)
        oauth = OAuth2Session(client=client)

        now = datetime.utcnow()
        claims = {
            "iss": client_email,
            "sub": sub,
            "aud": "nivola",
            "exp": now + timedelta(seconds=60),
            "iat": now,
            "nbf": now,
        }
        encoded = jwt.encode(claims, private_key, algorithm="RS512")
        res = client.prepare_request_body(assertion=encoded, client_id=client_id, scope=client_scope)
        token = oauth.fetch_token(token_url=client_token_uri, body=res, verify=False)
        logger.info("Create new oauth2 jwt token for client %s and sub %s" % (client_id, sub))
        return token
