'''
Created on Mar 24, 2017

@author: darkbk
'''
import logging
from beehive.manager import ApiManager, ComponentManager
from beecell.simple import truncate
from re import match

logger = logging.getLogger(__name__)

class ConfigManager(ApiManager):
    """
    SECTION: 
        auth
        
    PARAMS:
        configs list
    """      
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        
        self.baseuri = u'/v1.0/configs'
        self.subsystem = u'event'
        self.logger = logger
        self.msg = None
        
        self.headers = [u'group', u'name', u'app', u'value']
                            
    def actions(self):
        actions = {
            u'configs.list': self.get_configs,
        }
        return actions

    #
    # configs
    #
    def get_configs(self, app=None):
        if app is None:
            uri = u'%s/%s/' % (self.baseuri, app)
        else:
            uri = u'%s/' % (self.baseuri)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get configs: %s' % truncate(res))
        self.result(res, key=u'configs', headers=self.headers)
