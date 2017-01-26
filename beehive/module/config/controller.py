'''
Created on Jan 16, 2014

@author: darkbk
'''
import logging
import ujson as json
from beecell.auth import extract
from beehive.common.data import TransactionError, QueryError
from beehive.common.data import distributed_transaction, distributed_query
from beehive.common.config import ConfigDbManagerError, ConfigDbManager
from beecell.perf import watch
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beehive.common.apimanager import ApiEvent
from beecell.simple import id_gen

class ConfigController(ApiController):
    """Config Module controller.
    """
    version = u'v1.0'    
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.manager = ConfigDbManager()
        
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        Config(self).init_object()
        
        # add full permissions to superadmin role
        #perms = self.set_superadmin_permissions() 
    
    '''
    @distributed_query
    def set_superadmin_permissions(self):
        """ """
        try:
            #perms = ApiModule.get_superadmin_permissions(self)
            perms = []
            for item in [Config]:
                self.api_client.append_role_permissions(
                                    'ApiSuperadmin',
                                    item.objtype,
                                    item.objdef,
                                    self._get_value(item.objdef, []),
                                    '*')
                self.api_client.append_role_permissions(
                                    'ApiSuperadmin',
                                    'event',
                                    item.objdef,
                                    self._get_value(item.objdef, []),
                                    '*')
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)    '''

    #
    # base configuration
    #
    @distributed_query
    def get_configs(self, app=None, group=None, name=None):
        """Get generic configuration.
        
        :param app: app name [optional]
        :param group: group name [optional]
        :param name: name of the configuration [optional]
        :return: Config instance
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """        
        # verify permissions
        self.can(u'view', Config.objtype, definition=Config.objdef)
        
        try:
            if app is not None or group is not None:
                confs = self.manager.get(app=app, group=group)
            elif name is not None:
                confs = self.manager.get(name=name)
            else:
                confs = self.manager.get()
            
            res = []
            for c in confs:
                res.append(Config(self, oid=c.id, app=c.app, group=c.group, 
                                  name=c.name, value=c.value, model=c))
            self.logger.debug('Get generic configuration: %s' % res)
            Config(self).event('config.view', 
                               {'app':app, 'group':group, 'name':name}, 
                               (True))
            return res
        except (TransactionError, Exception) as ex:
            Config(self).event('config.view', 
                               {'app':app, 'group':group, 'name':name}, 
                               (False, ex))
            self.logger.error(ex)     
            raise ApiManagerError(ex)
    
    @distributed_transaction
    def add_config(self, app, group, name, value):
        """Add generic configuration.
        
        :param app: app name
        :param group: group name       
        :param name: property name
        :param value: property value 
        :return:
        :rtype:  
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.can('insert', Config.objtype, definition=Config.objdef)
        
        try:
            c = self.manager.add(app, group, name, value)
            res = Config(self, oid=c.id, app=c.app, group=c.group, 
                         name=c.name, value=c.value, model=c)
            self.logger.debug('Add generic configuration : %s' % res)
            Config(self).event('config.insert', 
                               {'app':app, 'group':group, 'name':name}, 
                               (True))
            return res
        except (TransactionError, Exception) as ex:
            Config(self).event('config.insert', 
                               {'app':app, 'group':group, 'name':name}, 
                               (False, ex))
            self.logger.error(ex)
            raise ApiManagerError(ex)

    #
    # logger configuration
    #
    @distributed_query
    def get_log_config(self, app):
        """
        :param app: app proprietary of the log
        :param log_name: logger name like 'gibbon.cloud'
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        confs = self.get_config(app=app, group='logging')
        for conf in confs:
            conf.value = json.loads(conf.value)
            # get logger level
            level = conf.value['level']
            if level == 'DEBUG':
                conf.value['level'] = logging.DEBUG
            elif level == 'INFO':
                conf.value['level'] = logging.INFO
            elif level == 'WARN':
                conf.value['level'] = logging.WARN
            elif level == 'ERROR':
                conf.value['level'] = logging.ERROR                             
        return confs       
    
    @distributed_transaction
    def add_log_config(self, app, name, log_name, log_conf):
        """
        :param app: app proprietary of the log
        :param name: logger reference name
        :param log_name: logger name like 'gibbon.cloud'
        :param log_conf: logger conf ('DEBUG', 'log/portal.watch', <log format>)
                         <log format> is optional
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        group = 'logging'
        value = {'logger':log_name, 'level':log_conf[0], 'store':log_conf[1]}
        try: value['format'] = log_conf[2]
        except: pass
        
        return self.add_config(app, group, name, json.dumps(value))

    #
    # auth configuration
    #
    @distributed_query
    def get_auth_config(self):
        """Get configuration for authentication provider.
        
        Ex. 
        [{'type':'db', 'host':'localhost', 
          'domain':'local', 'ssl':False, 'timeout':30},
         {'type':'ldap', 'host':'ad.regione.piemonte.it', 
          'domain':'regione.piemonte.it', 'ssl':False, 'timeout':30}]
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        confs = self.get_config(app='cloudapi', group='auth')
        for conf in confs:
            conf.value = json.loads(conf.value)                  
        return confs       
    
    @distributed_transaction
    def add_auth_config(self, auth_type, host, domain, ssl=False, 
                              timeout=30, port=None):
        """Set configuration for authentication provider.
        
        :param auth_type: One value among db, ldap, ...
        :param host: hostname of authentication provider
        :param port: port of authentication provider [optional]
        :param domain: authentication domain
        :param ssl: ssl enabled/disabled [default=False]
        :param timeout: connection timeout [default=30s]
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        app = 'cloudapi'
        group = 'auth'
        
        value = {'type':auth_type, 'domain':domain, 'host':host, 
                'ssl':ssl, 'timeout':timeout}
        if port is not None:
            value['port'] = port
        
        return self.add_config(app, group, domain, json.dumps(value))
    
    '''
    #
    # ssh configuration
    #    
    @distributed_query
    def get_ssh_config(self, id_key=None):
        """Get configuration for authentication provider.
        Ex. 
        [{'id':id_key, 'priv_key':priv_key, 'pub_key':pub_key},
         {'id':id_key, 'priv_key':priv_key, 'pub_key':pub_key}]
         
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)        
        
        try:
            if id_key:
                data = [self.manager.get_property(name=id_key)]
            else:
                data = self.manager.get_properties('cloudapi', 'ssh')
            res = []
            for item in data:
                data = json.loads(item.value)
                data['id'] = item.name
                res.append(data)
            self.logger.debug('Get ssh configuration')
            return res
        except (TransactionError, Exception), e:
            raise ApiManagerError(e)        
    
    @distributed_transaction
    def set_ssh_config(self, id_key, priv_key, pub_key):
        """Set ssh key used when connect remote server.
        :param id_key: id of the ssh key
        :param priv_key: private key. Ex. rsa key 
        :param pub_key: public key
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('insert', self.objtype, definition=self.objdef)        
        
        try:
            data = {'priv_key':priv_key, 'pub_key':pub_key}
            
            self.manager.add_property('cloudapi', 'ssh', id_key, json.dumps(data))
            self.logger.debug('Set ssh configuration')
        except (TransactionError, Exception), e:
            raise ApiManagerError(e)
    
    #
    # uri configuration
    #    
    @distributed_query
    def get_uri_config(self, app=None, uri_id=None):
        """Get uri configuration.
        
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef)        
        
        try:
            if uri_id:
                res = [self.manager.get_property(name=uri_id)]
            elif app:
                res = self.manager.get_properties(app=app, group='uri')
            else:
                res = self.manager.get_properties()
            self.logger.debug('Get uri configuration')
            return res
        except (TransactionError, Exception), e:
            raise ApiManagerError(e)        
    
    @distributed_transaction
    def set_uri_config(self, app, uri_id, uri):
        """Set uri configuration.
        :param app: app name     
        :param uri_id: id of the uri
        :param uri: uri value
        :return: 
        :rtype: 
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('insert', self.objtype, definition=self.objdef)        
        
        try:
            self.manager.add_property(app, 'uri', uri_id, uri)
            self.logger.debug('Set uri configuration')
        except (TransactionError, Exception), e:
            raise ApiManagerError(e)
    '''

class Config(ApiObject):
    objtype = 'config'
    objdef = 'property'
    objdesc = 'System configurations'
    
    def __init__(self, controller, oid=None, app=None, group=None, 
                       name=None, value=None, model=None):
        ApiObject.__init__(self, controller, oid=oid, objid=name, name=name, 
                                 desc=name, active=True)
        self.app = app
        self.group  = group
        self.value = value
        self.model = model
    
    @property
    def manager(self):
        return self.controller.manager
    
    @distributed_query
    def info(self):
        """Get system capabilities.
        
        :return: Dictionary with system capabilities.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.controller.can('view', self.objtype, definition=self.objdef) 
        return {u'id':self.oid, u'app':self.app, u'group':self.group, 
                u'name':self.name, u'objid':self.objid, u'value':self.value}

    @distributed_transaction
    def update(self, value):
        """Update generic configuration.
            
        :param name: property name
        :param value: property value 
        :return:
        :rtype:  
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('update', self.objtype, definition=self.objdef)
        
        try:
            res = self.manager.update(self.name, value)
            self.logger.debug('Update generic configuration %s : %s' % (self.name, res))
            self.event('config.update', {'name':self.name, 'value':value}, (True))
            
            return res
        except (TransactionError, Exception) as ex:
            self.event('config.update', {'name':self.name, 'value':value}, (False, ex))
            self.logger.error(ex)
            raise ApiManagerError(ex)
    
    def delete(self):
        """Update generic configuration.
            
        :param name: property name
        :param value: property value 
        :return:
        :rtype:  
        :raises ApiManagerError: if query empty return error.
        """
        # verify permissions
        self.controller.can('update', self.objtype, definition=self.objdef)
        
        try:
            res = self.manager.delete(name=self.name)
            self.logger.debug('Delete generic configuration %s : %s' % (self.name, res))
            self.event('config.delete', {'name':self.name}, (True))
            return res
        except (TransactionError, Exception) as ex:
            self.event('config.delete', {'name':self.name}, (False, ex))
            self.logger.error(ex)
            raise ApiManagerError(ex)