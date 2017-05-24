'''
Created on May 23, 2017

@author: darkbk
'''
from beehive.common.apimanager import ApiView

class ListConfig(ApiView):
    def dispatch(self, controller, data, app, *args, **kwargs):
        configs = controller.get_configs()
        res = [i.info() for i in configs]
        resp = {u'configs':res,
                u'count':len(res)}
        return resp

class FilterConfig(ApiView):
    def dispatch(self, controller, data, app, *args, **kwargs):
        configs = controller.get_configs(app=app)
        res = [i.info() for i in configs]
        resp = {u'configs':res,
                u'count':len(res)}
        return resp

class ConfigAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'configs/<app>', u'GET', ListConfig, {}),           
            (u'configs', u'GET', FilterConfig, {})
        ]

        ApiView.register_api(module, rules)