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

    class Meta:
        stacked_on = 'dbaas'
        stacked_type = 'nested'
        
class DBServiceInstanceController(DBaaServiceControllerChild):
    class Meta:
        label = 'dbinstances'
        description = "Instances service management"

    @expose(aliases=[u'describes [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def describes(self):
        """List all database instances by field: owner-id.N, db-instance-id.N
        """

        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'db-instance-id.N'] = self.split_arg(u'db-instance-id.N')
        logger.warning(u'$$$$$ %s' % dataSearch) 
        uri = u'%s/databaseservices/instance/describedbinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch,doseq=True)).get(u'DescribeDBInstancesResponse').get(u'DescribeDBInstancesResult').get(u'DBInstances',[])       
        logger.warning(u'$$$$$ %s' % res)
        self.result(res,
                    headers=[u'DBInstanceIdentifier', u'DBInstanceStatus', 
                             u'DBName', u'DbInstance', u'Port', u'Engine', 
                             u'EngineVersion', u'Endpoint'],                  
                    maxsize=40)
        
  
    @expose(aliases=[u'create <AccountId> <DBInstanceIdentifier> <DBInstanceClass> <DBSubnetGroupName> <Engine> <EngineVersion>'\
                     u'[Port][DBName=..] [MasterUsername=..] [MasterUserPassword=..]'\
                     u'[CharacterSetName] [AvailabilityZone=..] [VpcSecurityGroupIds=..]'],
            aliases_only=True)
    @check_error
    def create(self):
        """create db instance <AccountId> <DBInstanceIdentifier> <DBInstanceClass> <DBSubnetGroupName> <Engine> <EngineVersion>
            - field: can be Port, DBName, MasterUsername, MasterUserPassword, AvailabilityZone, VpcSecurityGroupIds 
        """
        data = {
            u'dbinstance': {
                u'AccountId' : self.get_arg(name=u'AccountId'),
                u'DBInstanceIdentifier' : self.get_arg(name=u'DBInstanceIdentifier'),
                u'DBInstanceClass' : self.get_arg(name=u'DBInstanceClass'),
                u'DBSubnetGroupName' : self.get_arg(name=u'DBSubnetGroupName'),   
                u'Engine' : self.get_arg(name=u'Engine'),
                u'EngineVersion' : self.get_arg(name=u'EngineVersion'),
                
                u'CharacterSetName':  self.get_arg(name=u'CharacterSetName', default=u'', keyvalue=True),              
                u'DBName' : self.get_arg(name=u'DBName', default=u'mydbname', keyvalue=True),
                u'AvailabilityZone' : self.get_arg(name=u'AvailabilityZone', default=None, keyvalue=True),           
                u'MasterUsername' : self.get_arg(name=u'MasterUsername', default=u'root', keyvalue=True),
                u'MasterUserPassword' : self.get_arg(name=u'MasterUserPassword', default=u'cs1$topix', keyvalue=True),
                u'Port' : self.get_arg(name=u'Port', keyvalue=True),
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