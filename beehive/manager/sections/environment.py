'''
Created on Nov 4, 2017

@author: darkbk
'''
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, check_error
from re import match
from beecell.simple import str2bool
from cryptography.fernet import Fernet
import urllib

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
    @check_error
    def list(self):
        """List available environments
        """
        envs = self.configs[u'environments']
        defualt_env = envs.get(u'default')
        current_env = self.env

        res = []
        headers = [u'name', u'current', u'is_default', u'has_cmp']
        for env, value in envs.items():
            if env == u'default':
                continue
            item = {u'name': env, u'current': False, u'is_default': False, u'has_cmp': False}
            if env == defualt_env:
                item[u'is_default'] = True
            if env == current_env:
                item[u'current'] = True
            if len(value.get(u'cmp', {}).get(u'endpoint', [])) > 0:
                item[u'has_cmp'] = True
            orchestrators = value.get(u'orchestrators', {})
            for k, v in orchestrators.items():
                item[k] = u','.join(v.keys())
                if k not in headers:
                    headers.append(k)

            res.append(item)
        self.result(res, headers=headers)

    @expose()
    @check_error
    def get(self):
        """Get current environments
        """
        # object_ids = self.get_arg(name=u'ids').split(u',')
        
        for key in self._meta.env_keys:
            print(u'%-10s: %s' % (key, getattr(self.app._meta, key, None)))
        
    @expose(aliases=[u'set <key> <value>'], aliases_only=True)
    @check_error
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

    @expose()
    @check_error
    def generate_key(self):
        """Generate fernet key for symmetric encryption
        """
        key = Fernet.generate_key()
        self.result({u'key': key}, headers=[u'key'])

    @expose(aliases=[u'encrypt <data>'], aliases_only=True)
    @check_error
    def encrypt(self):
        """Encrypt data with symmetric encryption
        """
        self.check_secret_key()
        data = self.get_arg(name=u'data to encrypt')
        cipher_suite = Fernet(self.key)
        cipher_text = cipher_suite.encrypt(data)
        res = [
            {u'data_type': u'encrypt_data', u'data': cipher_text},
            {u'data_type': u'quoted_data', u'data': urllib.quote(cipher_text)}
        ]
        self.result(res, headers=[u'data_type', u'data'], maxsize=200)

    @expose(aliases=[u'decrypt <data>'], aliases_only=True)
    @check_error
    def decrypt(self):
        """Decrypt quoted data with symmetric encryption
        """
        self.check_secret_key()
        data = self.get_arg(name=u'data to decrypt')
        data = urllib.unquote(data)
        cipher_suite = Fernet(self.key)
        cipher_text = cipher_suite.decrypt(data)
        self.result({u'decrypt_data': cipher_text}, headers=[u'decrypt_data'], maxsize=200)


env_controller_handlers = [
    EnvController,
]            