# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from .view import SchedulerAPI, TaskAPI
from .controller import SchedulerController
from beehive.common.apimanager import ApiModule


class SchedulerModule(ApiModule):
    """Beehive Scheduler Module"""

    def __init__(self, api_manger):
        self.name = "SchedulerModule"

        ApiModule.__init__(self, api_manger, self.name)

        self.apis = [SchedulerAPI, TaskAPI]
        self.api_plugins = {}
        self.controller = SchedulerController(self)

        # get related module
        try:
            self.related = api_manger.main_module
            self.base_path = self.related.base_path
        except Exception:
            pass

    def get_controller(self):
        return self.controller

    def get_related_controller(self):
        return self.related.get_controller()
