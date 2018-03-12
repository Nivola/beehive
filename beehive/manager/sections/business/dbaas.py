"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
import urllib

from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class DBaaServiceController(BaseController):
    class Meta:
        label = 'dbaas'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Database as a Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
        
class DBaaServiceControllerChild(ApiController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    def split_arg (self, key, splitWith=u','):
        
        splitList = []
        
        values = self.get_arg(name=key, default=None, keyvalue=True)     
        if values is not None:
            for value in values.split(splitWith):
                splitList.append(value)
                
        return splitList
 
    class Meta:
        stacked_on = 'dbaas'
        stacked_type = 'nested'
        
# class DBServiceContainerController(DBaaServiceControllerChild): 
#     
#     class Meta:
#         label = 'container '
#         description = "Database container management"    
           

class DBServiceInstanceController(DBaaServiceControllerChild):
    class Meta:
        label = 'dbinstances'
        description = "Instances service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all database instances by field: db_instance_id_N, owner_id
        """

        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner_id_N') 
        dataSearch[u'db-instance-id.N'] = self.split_arg(u'db_instance_id_N')  
        logger.info(u'$$$$$$$ describes dataSearch=%s' % dataSearch)
                    
        uri = u'%s/databaseservices/instance/describedbinstances' % self.baseuri
        res = self._call(uri, u'GET', data=dataSearch).get(u'DBInstances').get(u'DBInstance')       
        for item in res:
            logger.info(u'$$$$$$$ describes response item=%s' % item) 
            self.result(item,
                    headers=[u'DBInstanceIdentifier', u'DBInstanceStatus', u'DBName', u'DbInstance', u'Port', u'Engine', u'EngineVersion', u'Endpoint'],
                    filters=[u'DBInstanceIdentifier', u'DBInstanceStatus', u'DBName', u'DbInstance', u'Port', u'Engine', u'EngineVersion', u'Endpoint'],                   
                    maxsize=40)
        
  
    @expose(aliases=[u'create <AccountId> <DBInstanceIdentifier> <DBInstanceClass> <DBSubnetGroupName> [Engine] [EngineVersion] [Port]'\
                     u'[DBName=..] [MasterUsername=..] [MasterUserPassword=..]'\
                     u'[AvailabilityZone=..] [VpcSecurityGroupIds=..]'],
            aliases_only=True)
    @check_error
    def create(self):
        """create db instance <DBInstanceIdentifier> <DBInstanceClass> <AccountId> <Engine> <EngineVersion>
            - field: can be Port, DBName, MasterUsername, MasterUserPassword, DBSubnetGroupName, AvailabilityZone, VpcSecurityGroupIds 
        """
                
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        data = {
            u'dbinstance': {
                u'AccountId' : self.get_arg(name=u'AccountId'),
                u'DBInstanceIdentifier' : self.get_arg(name=u'DBInstanceIdentifier'),
                u'DBInstanceClass' : self.get_arg(name=u'DBInstanceClass'),
                u'DBSubnetGroupName' : self.get_arg(name=u'DBSubnetGroupName'),   
                u'Engine' : self.get_arg(name=u'Engine'),
                u'EngineVersion' : self.get_arg(name=u'EngineVersion'),               
                u'DBName' : params.get(u'DBName', u'mydbname'),
                
                u'AvailabilityZone' : params.get(u'AvailabilityZone', None),           
                u'MasterUsername' : params.get(u'MasterUsername', u'root'),
                u'MasterUserPassword' : params.get(u'MasterUserPassword', u'cs1$topix'),
                u'Port' : self.get_arg(name=u'Port'),
                u'VpcSecurityGroupIds' : { u'VpcSecurityGroupId': self.split_arg(u'VpcSecurityGroupIds') }  ,
#                 u'SchemaName' : u'schema name to use for a db instance postgres',
#                 u'ExtensionName_N' : [u'value1', u'value2'],
                }
        }
        logger.info(u'$$$$$$$ dbinstance data=%s' % data)         
        uri = u'%s/databaseservices/instance/createdbinstance' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        logger.info(u'Add database instance: %s' % truncate(res))
        res = {u'msg': u'Add database instance %s' % res}
        self.result(res, headers=[u'msg'])
  
        
class DBServiceInstanceUserController(DBaaServiceControllerChild):
    class Meta:
        label = 'users '
        description = "Database instance user management"     

dbaas_controller_handlers = [
    DBaaServiceController,
#     DBServiceContainerController,
    DBServiceInstanceController,
    DBServiceInstanceUserController
]         