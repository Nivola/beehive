'''
Created on July 2018

@author: Mikebeauty
'''

import logging
import datetime
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error

#from beedrones.veeam.client import VeeamManager, VeeamJob, VeeamClient
from beedrones.trilio.client import TrilioManager
import json

logger = logging.getLogger(__name__)


#
# trilio native platform
#
class TrilioPlatformController(BaseController):
    class Meta:
        label = 'trilio.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Trilio Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class TrilioPlatformControllerChild(BaseController):
    #headers = [u'id', u'name']
    #entity_class = None

    class Meta:
        stacked_on = 'trilio.platform'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-O', '--orchestrator'], dict(action='store', help='Trilio platform reference label')),
        ]

    @check_error
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)

        orchestrators = self.configs[u'environments'][self.env][u'orchestrators'].get(u'trilio')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Trilio platform label must be specified. '
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        '''
                       
         trilioconn = {"uriKeystone":"http://10.138.208.16:5000",
                        "uriTrilio":"http://10.138.208.69:8780",
                        "user":"admin",
                        "pwd":"*********",
                        "tenantName":"admin",
                        "verified":"False" }        
                 
        '''

        conn = {'uriKeystone': conf.get(u'uriKeystone'), 'uriTrilio':conf.get(u'uriTrilio'),'user':conf.get(u'user'), 'pwd':conf.get(u'pwd'), 'tenantName':conf.get(u'tenantName'),  'verified':conf.get(u'verified')}
        #print ("sono qui !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1111")
        #print (self.key)
        #print (conn)
        #print("sono in beehive")
        self.trilio = TrilioManager(conn, self.key)

        self.uri = conf.get(u'uri')


class TrilioPlatformConfigController(TrilioPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']

    class Meta:
        label = 'trilio.platform.config'
        aliases = ['config']
        aliases_only = True
        description = "trilio server global configuration "

    def _ext_parse_args(self):
        TrilioPlatformControllerChild._ext_parse_args(self)

    @expose(aliases=[u'getGlobalJobScheduler  <project_id> <tenant_name>'], aliases_only=True)
    @check_error
    def getGlobalJobScheduler(self):
        """This command will display the status ( true or false ) of the Cloud Wide TrilioVault Job Scheduler
        <project_id> = Openstack project id"""

        href = self.get_arg(name=u'project_id')
        tenant_name=self.get_arg(name=u'tenant_name')
        res = self.trilio.get_global_job_scheduler(href, tenant_name)

        if res[u'status'] == "OK":
            if int(res['data']['global_job_scheduler']):
                # valore True
                res['data']['global_job_scheduler'] = "Enabled"
            else:
                res['data']['global_job_scheduler'] = "Disabled"

            msg ={u'status': res[u'status'], u'status_code': res[u'status_code'],
              u'global_job_scheduler': res['data']['global_job_scheduler'],
              u'data': 'Successfully got the Cloud Wide TrilioVault Job Scheduler value'}

        else:
            msg = {u'status': res[u'status'], u'status_code': str(res[u'status_code']),
                   u'global_job_scheduler': '#####', u'data': res['data']}

        self.result(msg, headers=[u'status',u'global_job_scheduler'], fields=[u'status',u'global_job_scheduler'])

    @expose(aliases=[u'enableGlobalJobScheduler  <project_id>'], aliases_only=True)
    @check_error
    def enableGlobalJobScheduler(self):
        """TO DO: This command will ENABLE the Cloud Wide TrilioVault Job Scheduler
        <project_id> = Openstack project id"""

        href = self.get_arg(name=u'project_id')
        # TO DO


    @expose(aliases=[u'disableGlobalJobScheduler  <project_id>'], aliases_only=True)
    @check_error
    def disableGlobalJobScheduler(self):
        """TO DO: This command will DISABLE the Cloud Wide TrilioVault Job Scheduler
        <project_id> = Openstack project id"""

        href = self.get_arg(name=u'project_id')
        # TO DO

    @expose(aliases=[u'listOsTenants'], aliases_only=True)
    @check_error
    def list_os_tenants(self):
        """This command will display all the tenants/projects present in openstack """

        res = self.trilio.get_openstack_tenants()
        project = (res['data']['projects'])
        self.result(project, headers=[u'id', u'name', u'Description', u'enabled'],
                    fields=[u'id', u'name', u'description', u'enabled'])

    @expose(aliases=[u'get-all-workloads'], aliases_only=True)
    @check_error
    def get_all_workload(self):
        """This command will display ALL the workloads in the whole openstack environment """

        res = self.trilio.get_all_workloads()
        self.result(res['data'], headers=[u'Workload id', u'Workload name', u'Description', u'Project Name', u'status',
                                          u'Last\r\nSnapshot status', u'Last\r\nsnapshot date', u'Snapshot\r\ntype'],
                    fields=[u'id', u'name', u'description', u'project_name', u'status', u'snap_status', u'snap_date',
                            u'snap_type'])



class TrilioPlatformJobController(TrilioPlatformControllerChild):
    #headers = [u'id', u'name', u'domain_id']

    class Meta:
        label = 'trilio.platform.job'
        aliases = ['job']
        aliases_only = True
        description = "trilio Backup jobs (workloads) management"

    def _ext_parse_args(self):
        TrilioPlatformControllerChild._ext_parse_args(self)

    @expose(aliases=[u'list <project_id> <tenant_name>'], aliases_only=True)
    @check_error
    def list(self):
        """This command will display all the workloads of the specified openstack tenant;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name>  name of the openstack project or tenant;"""

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')

        res = self.trilio.workloads.get_workloads(project_id,tenant_name)

        if res[u'status'] == 'OK':
            msg = res[u'data']

        else:
            msg = {u'id': u'#####', u'name': u'', u'description': res[u'data'], u'created_at': u''}

        self.result(msg, headers=[u'id', u'name', u'description', u'status', u'created_at'],
                    fields=[u'id', u'name', u'description', u'status', u'created_at'])

    @expose(aliases=[u'show <project_id> <tenant_name> <workload_id>'], aliases_only=True)
    @check_error
    def show(self):
        """This command will Show the details of the workload_id in a specified openstack tenant;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name>  name of the openstack project or tenant;
        <workload_id> unique identifier of trilio workload """

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')
        workload_id = self.get_arg(name=u'workload_id')

        res = self.trilio.workloads.show_workload(project_id, tenant_name, workload_id)
        res_snaps = self.trilio.snapshots.check_last_snapshot(project_id, tenant_name, workload_id)

        if res_snaps[u'status'] == 'OK':
            last_snapshot_status = res_snaps[u'data'][u'status']
            last_snapshot_type = res_snaps[u'data'][u'snapshot_type']
            last_snapshot_created_at = res_snaps[u'data'][u'created_at']
        else:
            last_snapshot_status = '-'
            last_snapshot_type = '-'
            last_snapshot_created_at = '-'

        if res[u'status'] == 'OK':
            msg = {u'id': res['data']['id'], u'name': res['data']['name'],
                   u'workload_type_id': res['data']['workload_type_id'],
                   u'instances': len(res['data']['instances']),
                   u'storage_usage': res['data']['storage_usage']['usage'],
                   u'snapshot_number': res['data']['storage_usage']['full']['snap_count'] +
                                       res['data']['storage_usage']['incremental']['snap_count'],
                   u'schedule_enabled': res['data']['jobschedule']['enabled'],
                   u'last_snapshot_status': last_snapshot_status,
                   u'last_snapshot_type': last_snapshot_type,
                   u'last_snapshot_created_at': last_snapshot_created_at,
                   u'retention_policy_value': res['data']['jobschedule']['retention_policy_value'],
                   u'job_interval': res['data']['jobschedule']['interval'],
                   u'nextrun': res['data']['jobschedule']['nextrun']}

        else:
            msg = {u'id': u'#####', u'name': u'', u'description': res[u'data'], u'created_at': u''}

        self.result(msg, headers=[u'name', u'workload_type_id', u'VMs', u'storage usage \r\n(Bytes)', u'snapshot #',
                                  u'last snapshot\r\nstatus', u'scheduled', u'retention \r\npolicy', u'job_interval',
                                  u'nextrun \r\n(sec.)'],
                    fields=[u'name', u'workload_type_id', u'instances', u'storage_usage', u'snapshot_number',
                            u'last_snapshot_status', u'schedule_enabled', u'retention_policy_value', u'job_interval',
                            u'nextrun'])


class TrilioPlatformSnapshotController(TrilioPlatformControllerChild):

    class Meta:
        label = 'trilio.platform.snapshot'
        aliases = ['snapshot']
        aliases_only = True
        description = "trilio Backup snapshot management"

    def _ext_parse_args(self):
        TrilioPlatformControllerChild._ext_parse_args(self)

    @expose(aliases=[u'list <project_id> <tenant_name> <workload_id>'], aliases_only=True)
    @check_error
    def list(self):
        """This command will display all the snapshots of the specified workload;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name> name of the project or tenant;
        <workload_id> unique identifier of trilio workload """

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')
        workload_id = self.get_arg(name=u'workload_id')

        res = self.trilio.snapshots.get_snapshots(project_id, tenant_name, workload_id)
        self.result(res[u'data'], headers=[u'created_at', u'status', u'name', u'snapshot type', u'id'],
                    fields=[u'created_at', u'status', u'name', u'snapshot_type', u'id'])

    @expose(aliases=[u'show <project_id> <tenant_name> <snapshot_id>'], aliases_only=True)
    @check_error
    def show(self):
        """This command will display the datails of the shapshot ;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name> name of the project or tenant;
        <snapshot_id> unique identifier of snapshot """

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')
        snapshot_id = self.get_arg(name=u'snapshot_id')
        res = self.trilio.snapshots.show_snapshot(project_id, tenant_name,snapshot_id)
        self.result(res[u'data'], headers=[u'id', u'name', u'progress_percent', u'created at', u'size (Byte)',
                                           u'snapshot_type', u'status', u'time_taken (sec)'],
                    fields=[u'id', u'name', u'progress_percent', u'created_at', u'size', u'snapshot_type', u'status',
                            u'time_taken'])

    @expose(aliases=[u'check <project_id> <tenant_name> <snapshot_id>'], aliases_only=True)
    @check_error
    def check(self):
        """This command will display the status of the shapshot ;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name> name of the project or tenant;
        <snapshot_id> unique identifier of snapshot """

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')
        snapshot_id = self.get_arg(name=u'snapshot_id')

        res = self.trilio.snapshots.check_snapshot(project_id, tenant_name, snapshot_id)

        if res[u'status'] == 'OK':
            msg = {u'status': res[u'status'], u'status_code': str(res[u'status_code']),
                   u'snapshot_status': res[u'data'][u'status']}
        else:
            msg = {u'status': res[u'status'], u'status_code': str(res[u'status_code']),
                   u'snapshot_status': '#####', u'data': res['data']}

        self.result(msg, headers=[u'status code', u'snapshot status'], fields=[u'status_code', u'snapshot_status'])

    @expose(aliases=[u'check-last <project_id> <tenant_name> <workload_id>'], aliases_only=True)
    @check_error
    def check_last(self):
        """This command will display the snapshot status of the last snapshot found ;
        <project_id>  unique identifier of openstack project or tenant;
        <tenant_name> name of the project or tenant;
        <snapshot_id> unique identifier of trilio workload """

        project_id = self.get_arg(name=u'project_id')
        tenant_name = self.get_arg(name=u'tenant_name')
        workload_id = self.get_arg(name=u'workload_id')
        res = self.trilio.snapshots.check_last_snapshot(project_id, tenant_name, workload_id)

        if res[u'status'] == 'OK':

            msg = {u'status': res[u'status'], u'status_code': str(res[u'status_code']),
                   u'snapshot_status': res[u'data'][u'status'],
                   u'name':res[u'data'][u'name'], u'created_at':res[u'data'][u'created_at'],
                   u'snapshot_type': res[u'data'][u'snapshot_type'], u'host': res[u'data'][u'host'],
                   u'workload_id': res[u'data'][u'workload_id'], u'id': res[u'data'][u'id'],
                   u'description': res[u'data'][u'description']}

        else:

            msg = {u'status': res[u'status'], u'status_code': str(res[u'status_code']),
                   u'snapshot_status': '#####', u'data': res['data']}

        self.result(msg, headers=[u'status code', u'snapshot status', u'created at', u'snapshot id'],
                    fields=[u'status_code', u'snapshot_status', u'created_at', u'id'])




trilio_controller_handlers = [
    TrilioPlatformController,
    TrilioPlatformConfigController,
    TrilioPlatformJobController,
    TrilioPlatformSnapshotController]
