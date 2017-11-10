'''
Created on Nov 4, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController
from re import match
from beecell.simple import str2bool

logger = logging.getLogger(__name__)

class EnvController(BaseController):
    class Meta:
        label = 'env'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "cli environemnt management"
        env_keys = [u'env', u'format', u'color', u'verbosity']

    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
    @expose()
    def get(self):
        """Get current environments
        """
        #object_ids = self.get_arg(name=u'ids').split(u',')
        
        for key in self._meta.env_keys:
            print(u'%-10s: %s' % (key, getattr(self.app._meta, key, None)))
        
    @expose(aliases=[u'set <key> <value>'], aliases_only=True)
    def set(self):
        """Set current environments
        """
        key = self.get_arg(name=u'environment key')
        value = self.get_arg(name=u'environment key value')
        if key == u'color':
            value = str2bool(value)
            if value is None:
                raise Exception(u'color value must be true or false')
        if key == u'format':
            if value not in self._meta.formats:
                raise Exception(u'format value must be one of: %s' % self._meta.formats)
        if key == u'env':
            envs = u', '.join(self.configs[u'environments'].keys())
            if value not in envs:
                raise Exception(u'Platform environment %s does not exist. Select '\
                                u'from: %s' % (self.env, envs))
        if key == u'verbosity':
            try:
                value = int(value)
            except:
                raise Exception(u'verbosity must be an integer. Ex. 0, 1, 2, 3') 
        setattr(self.app._meta, key, value)
        
env_controller_handlers = [
    EnvController,
]            