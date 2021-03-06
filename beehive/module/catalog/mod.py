# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from .controller import CatalogController
from .view import CatalogAPI
from beehive.common.apimanager import ApiModule
from beehive.common.controller.authorization import AuthenticationManager


class CatalogModule(ApiModule):
    """Catalog Module. This module depends by Auth Module and does not work without it. Good deploy of this module is
    in server instance with Auth Module.

    :param module: ApiModule instance
    """
    def __init__(self, api_manger):
        self.name = 'CatalogModule'
        self.base_path = 'ncs'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [CatalogAPI]
        self.authentication_manager = AuthenticationManager(api_manger.auth_providers)
        self.controller = CatalogController(self)

    def get_controller(self):
        return self.controller
