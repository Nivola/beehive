# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.apimanager import ApiModule
from beehive.module.config.view import ConfigAPI
from beehive.module.config.controller import ConfigController


class ConfigModule(ApiModule):
    """Beehive Config Module
    """
    def __init__(self, api_manger):
        """ """
        self.name = 'ConfigModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [ConfigAPI]
        self.controller = ConfigController(self)

    def get_controller(self):
        return self.controller
