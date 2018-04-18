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
from beehive.manager.sections.business import SpecializedServiceControllerChild

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


class DBaaServiceControllerChild(SpecializedServiceControllerChild):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'dbaas'
        stacked_type = 'nested'


class DBServiceInstanceController(DBaaServiceControllerChild):
    class Meta:
        label = 'db.instances'
        aliases = ['instances']
        aliases_only = True
        description = "Instances service management"

    @expose()
    @check_error
    def types(self):
        """List db instance types
        """
        data = urllib.urlencode({u'plugintype': u'DatabaseInstance'})
        uri = u'%s/srvcatalogs/all/defs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        headers = [u'id', u'uuid', u'instance_type', u'version', u'status', u'active', u'creation']
        fields = [u'id', u'uuid', u'name', u'version', u'status', u'active', u'date.creation']
        self.result(res, key=u'servicedefs', headers=headers, fields=fields)

    @expose(aliases=[u'list [field=<id1, id2>]'], aliases_only=True)
    @check_error
    def list(self):
        """List all database instances by field: owner-id.N, db-instance-id.N
        """
        dataSearch = {}
        dataSearch[u'owner-id.N'] = self.split_arg(u'owner-id.N') 
        dataSearch[u'db-instance-id.N'] = self.split_arg(u'db-instance-id.N')
        uri = u'%s/databaseservices/instance/describedbinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(dataSearch, doseq=True))
        res = res.get(u'DescribeDBInstancesResponse').get(u'DescribeDBInstancesResult').get(u'DBInstances', [])
        headers = [u'id', u'name', u'status', u'Engine', u'EngineVersion', u'MultiAZ',
                   u'AvailabilityZone', u'DBInstanceClass', u'Subnet', u'Listen', u'Port']
        fields = [u'DBInstanceIdentifier', u'name', u'DBInstanceStatus', u'Engine', u'EngineVersion', u'MultiAZ',
                  u'AvailabilityZone', u'DBInstanceClass', u'DBSubnetGroup.DBSubnetGroupName', u'Endpoint.Address',
                  u'Endpoint.Port']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get database instance info
        """
        pass

    @expose(aliases=[u'add <name> <account> <template> <subnet> <engine> <version> <security group> [field=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Create db instance 
    - field: can be Port, DBName, MasterUsername, MasterUserPassword, AvailabilityZone
        """
        name = self.get_arg(name=u'name')
        account = self.get_account(self.get_arg(name=u'account'))
        template = self.get_service_def(self.get_arg(name=u'template'))
        subnet = self.get_service_instance(self.get_arg(name=u'subnet'))
        engine = self.get_arg(name=u'engine')
        engine_version = self.get_arg(name=u'engine version')
        sg = self.get_service_instance(self.get_arg(name=u'security group'))

        data = {
            u'dbinstance': {
                u'AccountId': account,
                u'DBInstanceIdentifier': name,
                u'DBInstanceClass': template,
                u'DBSubnetGroupName': subnet,
                u'Engine': engine,
                u'EngineVersion': engine_version,
                u'VpcSecurityGroupIds': {u'VpcSecurityGroupId': sg.split(u',')},
                
                # u'CharacterSetName':  self.get_arg(name=u'CharacterSetName', default=u'', keyvalue=True),
                # u'DBName': self.get_arg(name=u'DBName', default=u'mydbname', keyvalue=True),
                # u'AvailabilityZone': self.get_arg(name=u'AvailabilityZone', default=None, keyvalue=True),
                # u'MasterUsername': self.get_arg(name=u'MasterUsername', default=u'root', keyvalue=True),
                u'MasterUserPassword': self.get_arg(name=u'MasterUserPassword', default=u'N!v0la12vr', keyvalue=True),
                # u'Port': self.get_arg(name=u'Port', default=u'', keyvalue=True),

                # u'SchemaName': u'schema name to use for a db instance postgres',
                # u'ExtensionName_N': [u'value1', u'value2'],
            }
        }   
        uri = u'%s/databaseservices/instance/createdbinstance' % (self.baseuri)
        res = self._call(uri, u'POST', data=data, timeout=600)
        logger.info(u'Add database instance: %s' % truncate(res))
        res = {u'msg': u'Add database instance %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete database instances
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/databaseservices/instance/deletedbinstance' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'DBInstanceIdentifier': uuid})
        res = res.get(u'DeleteDBInstanceResponse').get(u'DeleteDBInstanceResult').get(u'DBInstance', None)
        logger.info(u'Delete database instance: %s' % res)
        res = {u'msg': u'Delete database instance %s' % uuid}
        self.result(res, headers=[u'msg'])


class DBServiceInstanceUserController(DBaaServiceControllerChild):
    class Meta:
        label = 'users '
        description = "Database instance user management"     


dbaas_controller_handlers = [
    DBaaServiceController,
    # DBServiceContainerController,
    DBServiceInstanceController,
    DBServiceInstanceUserController
]         