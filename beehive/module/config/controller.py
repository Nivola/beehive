'''
Created on Jan 16, 2014

@author: darkbk
'''
import logging
import ujson as json
from beecell.auth import extract
#from beecell.perf import watch
from beecell.simple import id_gen
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beehive.common.model.config import ConfigDbManager
from beecell.db import TransactionError
from beehive.common.data import trace

class ConfigController(ApiController):
    """Basic Module controller.
    """
        
    version = u'v1.0'    
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.manager = ConfigDbManager()
        self.child_classes = [Config]
        
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        # register all child class
        for child_class in self.child_classes:
            child_class(self).init_object()

    #
    # base configuration
    #
    @trace(entity=u'Config', op=u'view')
    def get_configs(self, app=None, group=None, name=None):
        """Get generic configuration.
        
        :param app: app name [optional]
        :param group: group name [optional]
        :param name: name of the configuration [optional]
        :return: Config instance
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """
        #params = {u'app':app, u'group':group, u'name':name}
        
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
                try:
                    value = json.loads(c.value)
                except:
                    value = c.value                
                res.append(Config(self, oid=c.id, app=c.app, group=c.group, 
                                  name=c.name, value=value, model=c))
            self.logger.debug('Get generic configuration: %s' % res)
            #Config(self).send_event(u'view', params=params)
            return res
        except (TransactionError, Exception) as ex:
            #Config(self).send_event(u'view', params=params, exception=ex)
            self.logger.error(ex)     
            raise ApiManagerError(ex)
    
    @trace(entity=u'Config', op=u'insert')
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
        #params = {u'app':app, u'group':group, u'name':name}
        
        # verify permissions
        self.can(u'insert', Config.objtype, definition=Config.objdef)
        
        try:
            c = self.manager.add(app, group, name, value)
            res = Config(self, oid=c.id, app=c.app, group=c.group, 
                         name=c.name, value=c.value, model=c)
            self.logger.debug('Add generic configuration : %s' % res)
            #Config(self).send_event(u'view', params=params)
            return res
        except (TransactionError, Exception) as ex:
            #Config(self).send_event(u'view', params=params, exception=ex)
            self.logger.error(ex)
            raise ApiManagerError(ex)

    '''
    #
    # logger configuration
    #
    @watch
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
    
    @watch
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
    @watch
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
    
    @watch
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
        
        return self.add_config(app, group, domain, json.dumps(value))'''

class Config(ApiObject):
    objtype = u'config'
    objdef = u'Property'
    objdesc = u'System configurations'
    
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
    
    def info(self):
        """Get system capabilities.
        
        :return: Dictionary with system capabilities.
        :rtype: dict        
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        return {
            u'id':self.oid, 
            u'app':self.app, 
            u'group':self.group, 
            u'name':self.name, 
            u'objid':self.objid, 
            u'value':self.value
        }

    @trace(op=u'update')
    def update(self, value):
        """Update generic configuration.
            
        :param name: property name
        :param value: property value 
        :return:
        :rtype:  
        :raises ApiManagerError: if query empty return error.
        """
        #params = {u'name':self.name, u'value':value}
        
        # verify permissions
        self.verify_permisssions(u'update')
        
        try:
            res = self.manager.update(self.name, value)
            self.logger.debug(u'Update generic configuration %s : %s' % 
                              (self.name, res))
            #self.send_event(u'update', params=params)
            return res
        except (TransactionError, Exception) as ex:
            #self.send_event(u'update', params=params, exception=ex)
            self.logger.error(ex)
            raise ApiManagerError(ex)
    
    @trace(op=u'delete')
    def delete(self):
        """Update generic configuration.
            
        :param name: property name
        :param value: property value 
        :return:
        :rtype:  
        :raises ApiManagerError: if query empty return error.
        """
        #params = {u'name':self.name}
        
        # verify permissions
        self.verify_permisssions(u'delete')
        
        try:
            res = self.manager.delete(name=self.name)
            self.logger.debug(u'Delete generic configuration %s : %s' % (self.name, res))
            #self.send_event(u'delete', params=params)
            return res
        except (TransactionError, Exception) as ex:
            #self.send_event(u'delete', params=params, exception=ex)
            self.logger.error(ex)
            raise ApiManagerError(ex)