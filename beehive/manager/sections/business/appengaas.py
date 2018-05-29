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


class AppEngineServiceController(BaseController):
    class Meta:
        label = 'appeng'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "AppEngine as a Service management"
        arguments = []
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class AppEngineServiceControllerChild(SpecializedServiceControllerChild):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        stacked_on = 'appeng'
        stacked_type = 'nested'


class AppEngineInstanceController(AppEngineServiceControllerChild):
    class Meta:
        label = 'appeng.instances'
        aliases = ['instances']
        aliases_only = True
        description = "Instances service management"

    @expose()
    @check_error
    def types(self):
        """List app engine instance types
        """
        data = urllib.urlencode({u'plugintype': u'AppEngineInstance'})
        uri = u'%s/srvcatalogs/all/defs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        headers = [u'id', u'uuid', u'instance_type', u'version', u'status', u'active', u'creation']
        fields = [u'id', u'uuid', u'name', u'version', u'status', u'active', u'date.creation']
        self.result(res, key=u'servicedefs', headers=headers, fields=fields)

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all app engine instances
    - field: account, ids, size
        - accounts: list of account id comma separated
        - ids: list of image id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'db-instance-id.N'] = self.split_arg(u'ids')
        data_search[u'MaxRecords'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Marker'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/appengineservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeInstancesResponse')
        page = data_search[u'Marker']
        resp = {
            u'count': len(res.get(u'instancesSet')),
            u'page': page,
            u'total': res.get(u'instancesTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'instancesSet')
        }

        headers = [u'id', u'name', u'status', u'account', u'Engine', u'EngineVersion',
                   u'AvailabilityZone', u'Subnet', u'Uris',  u'Date']
        fields = [u'instanceId', u'name', u'instanceState.name', u'OwnerAlias', u'engine', u'version',
                  u'placement.availabilityZone', u'subnetName',
                  u'uris', u'launchTime']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get app engine instance info
        """
        data_search = {}
        data_search[u'InstanceId.N'] = self.split_arg(u'id')

        uri = u'%s/appengineservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeInstancesResponse')

        if len(res.get(u'instancesSet')) > 0:
            resp = res.get(u'instancesSet')[0]
            self.result(resp, details=True)

    @expose(aliases=[u'add <name> <account> <template> <subnet> <security group> <farm name> [field=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Create app engine instance 
    - field: can be key_name
        - key_name: name of the openstack key
        """
        name = self.get_arg(name=u'name')
        account = self.get_account(self.get_arg(name=u'account'))
        template = self.get_service_def(self.get_arg(name=u'template'))
        subnet = self.get_service_instance(self.get_arg(name=u'subnet'))
        sg = self.get_service_instance(self.get_arg(name=u'security group'))
        farm_name = self.get_service_instance(self.get_arg(name=u'farm name'))
        key_name = self.get_service_instance(self.get_arg(name=u'keyname', keyvalue=True, default=None))

        data = {
            u'instance': {
                u'owner_id': account,
                u'Name': name,
                u'AdditionalInfo': name,
                u'InstanceType': template,
                u'SubnetId': subnet,
                u'SecurityGroupId.N': sg,
                u'EngineConfigs': {u'FarmName': farm_name}
            }
        }
        if key_name is not None:
            data[u'instance'][u'KeyName'] = key_name
        uri = u'%s/appengineservices/instance/runinstances' % self.baseuri
        res = self._call(uri, u'POST', data=data, timeout=600).get(u'RunInstanceResponse').get(u'instanceId')
        logger.info(u'Add app engine instance: %s' % truncate(res))
        res = {u'msg': u'Add app engine instance %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'import-resource <template> <resource>'], aliases_only=True)
    @check_error
    def import_resource(self):
        """Import app engine instance from an existing resource
    - field: can be Port, DBName, MasterUsername, MasterUserPassword, AvailabilityZone
        """
        template = self.get_service_def(self.get_arg(name=u'template'))
        resource = self.get_service_def(self.get_arg(name=u'resource'))

        data = {
            u'instance': {
                u'InstanceType': template,
                u'ResourceId': resource
            }
        }
        uri = u'%s/appengineservices/instance/runinstances' % self.baseuri
        res = self._call(uri, u'POST', data=data, timeout=120).get(u'RunInstanceResponse').get(u'instanceId')
        logger.info(u'Add app engine instance: %s' % truncate(res))
        res = {u'msg': u'Add app engine instance %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete app engine instances
        """
        uuid = self.get_arg(name=u'id')
        uri = u'%s/appengineservices/instance/terminateinstances' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'InstanceId.N': [uuid], u'preserve': True}, timeout=600)
        res = res.get(u'TerminateInstancesResponse')
        logger.info(u'Delete app engine instance: %s' % res)
        res = {u'msg': u'Delete app engine instance %s' % uuid}
        self.result(res, headers=[u'msg'])


appengine_controller_handlers = [
    AppEngineServiceController,
    AppEngineInstanceController
]         