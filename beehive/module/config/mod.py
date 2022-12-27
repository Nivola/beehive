# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from beehive.common.apimanager import ApiModule
from beehive.module.config.view import ConfigAPI
from beehive.module.config.controller import ConfigController


class ConfigModule(ApiModule):
    """Beehive Config Module

    :param module: ApiModule instance
    """
    def __init__(self, api_manger):
        """ """
        self.name = 'ConfigModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [ConfigAPI]
        self.controller = ConfigController(self)

    def get_controller(self):
        return self.controller
