# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from beehive.common.apimanager import ApiView


class ListConfig(ApiView):
    def get(self, controller, data, app, *args, **kwargs):
        configs = controller.get_configs()
        res = [i.info() for i in configs]
        resp = {'configs': res,
                'count': len(res)}
        return resp


class FilterConfig(ApiView):
    def get(self, controller, data, app, *args, **kwargs):
        configs = controller.get_configs(app=app)
        res = [i.info() for i in configs]
        resp = {'configs': res,
                'count': len(res)}
        return resp


class ConfigAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('configs/<app>', 'GET', ListConfig, {}),           
            ('configs', 'GET', FilterConfig, {})
        ]

        ApiView.register_api(module, rules)
