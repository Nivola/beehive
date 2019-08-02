# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from .view import BaseAPI
from .controller import BasicController
from beehive.common.apimanager import ApiModule


class BasicModule(ApiModule):
    """Beehive Basic Module
    """
    def __init__(self, api_manger):
        self.name = u'BasicModule'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [BaseAPI]
        self.controller = BasicController(self)

    def get_controller(self):
        return self.controller