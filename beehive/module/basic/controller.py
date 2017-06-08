'''
Created on Apr 1, 2016

@author: darkbk
'''
from beecell.auth import extract
from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate
from beecell.db.manager import SqlManagerError
from beecell.server.uwsgi_server.resource import UwsgiManager, UwsgiManagerError
from beehive.common.apimanager import ApiController, ApiManagerError
from beehive.common.model.config import ConfigDbManager
from beecell.db import TransactionError, QueryError
from beehive.common.model.authorization import AuthDbManager

class BaiscController(ApiController):
    """Basic Module controller.
    """
        
    version = u'v1.0'
    
    def __init__(self, module):
        ApiController.__init__(self, module)
        
        self.resource = UwsgiManager()
        self.dbauth = AuthDbManager()

        self.child_classes = [ApiManagerError]
    
    #
    # init
    #
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        
        :param args: 
        """
        # add actions
        try:
            actions = [u'*', u'view', u'insert', u'update', u'delete', u'use']
            self.dbauth.add_object_actions(actions)
        except TransactionError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)
        
        # init container
        for child in self.child_classes:
            child(self).init_object()
    
    def set_superadmin_permissions(self):
        """ """
        try:
            self.set_admin_permissions(u'ApiSuperadmin', [])
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)    
    
    def set_admin_permissions(self, role_name, args):
        """ """
        try:
            for item in self.child_classes:
                item(self).set_admin_permissions(role_name, args)
        except (QueryError, TransactionError) as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=ex.code)

    #
    # server info
    #
    def ping(self):
        """Ping server
        
        :raise ApiManagerError:
        """
        try:
            res = {'name':self.module.api_manager.app_name,
                   'id':self.module.api_manager.app_id}
            self.logger.debug('Ping server: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            return False
            #raise ApiManagerError(ex, code=8000)
        
    def info(self):
        """Server Info
        
        :raise ApiManagerError:
        """
        try:
            res = {'name':self.module.api_manager.app_name,
                   'id':self.module.api_manager.app_id,
                   'modules':{k:v.info() for k,v in 
                              self.module.api_manager.modules.iteritems()},
                   }
            self.logger.debug('Get server info: %s' % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)
        
    def processes(self):
        """Get server process tree
        
        :raise ApiManagerError:
        """
        try:
            res = self.resource.info()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)
        
    def workers(self):
        """Get server workers statistics
        
        :raise ApiManagerError:
        """
        try:
            res = self.resource.stats()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)
        
    def reload(self):
        """Reload server
        
        :raise ApiManagerError:
        """
        try:
            res = self.resource.reload()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)
    
    def get_configs(self, app='beehive'):
        """Get server configuration.
        
        :param app: app name [default=cloudapi]
        :return: Config instance list
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """
        try:
            manager = ConfigDbManager()
            confs = manager.get(app=app)
            
            res = []
            for c in confs:
                res.append({u'type':c.group, u'name':c.name, u'value':c.value})
            self.logger.debug('Get server configuration: %s' % truncate(res))
            return res
        except (TransactionError, Exception) as ex:
            self.logger.error(ex)     
            raise ApiManagerError(ex)
        
    def get_uwsgi_configs(self):
        """Get uwsgi configuration params. List all configurations saved in .ini
        configuration file of the uwsgi instance.
        
        :return: uwsgi configurations list
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """
        try:
            confs = self.module.api_manager.params
            
            res = []
            for k,v in confs.iteritems():
                res.append({u'key':k, u'value':v})
            self.logger.debug('Get uwsgi configuration: %s' % truncate(res))
            return res
        except (TransactionError, Exception) as ex:
            self.logger.error(ex)     
            raise ApiManagerError(ex)          
    
    #
    # database management
    #
    # TODO: profile methods
    @property
    def db_manager(self):
        return self.module.api_manager.db_manager
    
    def database_ping(self):
        return self.db_manager.ping()
        
    def database_tables(self):
        """List tables name   
        """
        try:
            tables = self.db_manager.get_tables_names()
            return tables
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
            
    def database_table_desc(self, table_name):
        """Describe a table

        :param table_name: name of the table
        :return: list of columns description (name, type, default, is index, 
                                              is nullable, is primary key,
                                              is unique)
        :raise ApiManagerError:
        """
        try:
            return self.db_manager.get_table_description(table_name)
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)            
            
    def database_count(self, table_name=None, where=None):
        """Count table rows
        
        :param table_name: name of the table to query [optional]
        :param where: query filter [optional]
        :return: rows count
        :raise ApiManagerError:
        """
        try:
            res = self.db_manager.count_table_rows(table_name=table_name, 
                                                   where=where)
            return res
        except (SqlManagerError, Exception) as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
            
    def database_query(self, table_name=None, where=None, fields='*', 
                          rows=100, offset=0):
        """Query a table
        
        :param table_name: name of the table to query [optional]
        :param where: query filter [optional]
        :param fields: list of fields to include in table qeury [optional]
        :param rows: number of rows to fetch [default=100]
        :param offset: row fecth offset [default=0]
        :return: query rows
        :raise ApiManagerError:
        """
        try:
            res = self.db_manager.query_table(table_name=table_name, 
                                              where=where, fields=fields, 
                                              rows=rows, offset=offset)
            return res
        except (SqlManagerError, Exception) as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400) 