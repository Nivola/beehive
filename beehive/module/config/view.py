'''
Created on Jan 26, 2017

@author: darkbk
'''
from re import match
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError

class ConfigApiView(ApiView):
    def get_config(self, controller, oid):
        config = controller.get_configs(oid=int(oid))
        if len(config) == 0:
            raise ApiManagerError(u'Config %s not found' % oid, code=404)
        return config[0]

#
# config api
#
class ListConfigs(ConfigApiView):
    def dispatch(self, controller, name, data, *args, **kwargs):
        configs = controller.get_configs(app=name)
        res = [r.info() for r in configs]
        resp = {u'configs':res,
                u'count':len(res)}
        return resp

class GetConfig(ConfigApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        config = self.get_config(controller, oid)
        res = config.detail()
        resp = {u'config':res}        
        return resp
    
class CreateConfig(ConfigApiView):
    """ TODO
        {u'name':u'cloudapi', 
         u'desc':u'cloudapi config',
         u'zone':u'internal'}
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'config', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        zone = get_value(data, u'zone', None, exception=True)
        
        resp = controller.add_config(name, desc, zone)
        return (resp, 201)

class UpdateConfig(ConfigApiView):
    """ Update Config TODO
    """            
    def dispatch(self, controller, data, oid, *args, **kwargs):
        config = self.get_config(controller, oid)
        data = get_value(data, u'config', None, exception=True)
        name = get_value(data, u'name', None)
        desc = get_value(data, u'desc', None)
        zone = get_value(data, u'zone', None)
        resp = config.update(new_name=name, new_desc=desc, new_zone=zone)
        return resp
    
class DeleteConfig(ConfigApiView):
    """ TODO
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        config = self.get_config(controller, oid)
        resp = config.delete()
        return (resp, 204)

class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'configs/<name>', u'GET', ListConfigs, {}),
            (u'config/<oid>', u'GET', GetConfig, {}),
            (u'config', u'POST', CreateConfig, {}),
            (u'config/<oid>', u'PUT', UpdateConfig, {}),
            (u'config/<oid>', u'DELETE', DeleteConfig, {})
        ]

        ApiView.register_api(module, rules)
