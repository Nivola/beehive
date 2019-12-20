# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from .view import SchedulerAPI, TaskAPI
from .controller import SchedulerController
from beehive.common.apimanager import ApiModule


class SchedulerModuleV2(ApiModule):
    """Beehive Scheduler Module

    :param module: ApiModule instance
    """
    def __init__(self, api_manger):
        self.name = 'SchedulerModuleV2'
        
        ApiModule.__init__(self, api_manger, self.name)
        
        self.apis = [
            SchedulerAPI, 
            TaskAPI
        ]
        self.api_plugins = {}
        self.controller = SchedulerController(self)

        # get related module
        try:
            self.related = api_manger.main_module
            self.base_path = self.related.base_path
        except:
            pass

    def get_controller(self):
        return self.controller

    def get_related_controller(self):
        return self.related.get_controller()
