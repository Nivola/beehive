# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from .views.base import BaseAPI
from .controller import BasicController
from beehive.common.apimanager import ApiModule


class BasicModule(ApiModule):
    """Beehive Basic Module

    :param module: ApiModule instance
    """

    def __init__(self, api_manger):
        self.name = "BasicModule"

        ApiModule.__init__(self, api_manger, self.name)

        self.apis = [BaseAPI]
        self.controller = BasicController(self)

    def get_controller(self):
        return self.controller
