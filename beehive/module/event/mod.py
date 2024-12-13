# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.module.basic.views.status import StatusAPI
from beehive.common.apimanager import ApiModule
from beehive.module.event.view import EventAPI
from beehive.module.event.controller import EventController


class EventModule(ApiModule):
    """Event Beehive Module

    :param module: ApiModule instance
    """

    def __init__(self, api_manger):
        self.name = "EventModule"
        self.base_path = "nes"

        ApiModule.__init__(self, api_manger, self.name)

        self.apis = [EventAPI, StatusAPI]
        self.controller = EventController(self)

    def get_controller(self):
        return self.controller
