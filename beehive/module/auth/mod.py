# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from .controller import AuthController
from .views import AuthorizationAPI, SimpleHttpAuthApi, KeyAuthApi
from beehive.common.apimanager import ApiModule , ApiManager
from beehive.common.controller.authorization import AuthenticationManager
from ..basic.views.status import StatusAPI


class AuthModule(ApiModule):
    """Beehive Authorization Module

    :param module: ApiModule instance
    """
    def __init__(self, api_manger: ApiManager):
        self.name = 'AuthModule'
        self.base_path = 'nas'

        ApiModule.__init__(self, api_manger, self.name)

        self.apis = [
            AuthorizationAPI,
            SimpleHttpAuthApi,
            KeyAuthApi,
            StatusAPI
        ]
        self.authentication_manager = AuthenticationManager(api_manger.auth_providers)
        self.controller = AuthController(self)

    def get_controller(self):
        return self.controller

    def set_authentication_providers(self, auth_providers):
        self.authentication_manager.auth_providers = auth_providers
