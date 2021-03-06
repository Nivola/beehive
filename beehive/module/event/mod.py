# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.apimanager import ApiModule
from beehive.module.event.view import EventAPI
from beehive.module.event.controller import EventController


class EventModule(ApiModule):
    """Event Beehive Module

    :param module: ApiModule instance
    """
    def __init__(self, api_manger):
        self.name = 'EventModule'
        self.base_path = 'nes'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [EventAPI]
        self.controller = EventController(self)

    def get_controller(self):
        return self.controller
