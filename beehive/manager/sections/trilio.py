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
# veeam native platform
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
        self.util = TrilioManager(conn, self.key)
        self.uri = conf.get(u'uri')


class TrilioPlatformConfigController(TrilioPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']

    class Meta:
        label = 'trilio.platform.config'
        aliases = ['config']
        aliases_only = True
        description = "trilio server configuration "

    def _ext_parse_args(self):
        TrilioPlatformControllerChild._ext_parse_args(self)

    @expose(aliases=[u'getGlobalJobScheduler  <project_id>'], aliases_only=True)
    @check_error
    def getGlobalJobScheduler(self):
        """This command will display the status ( true or false ) of the Cloud Wide TrilioVault Job Scheduler
        <project_id> = Openstack project id"""

        href = self.get_arg(name=u'project_id')
        res = self.util.get_global_job_scheduler(href)

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


class TrilioPlatformJobController(TrilioPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']

    class Meta:
        label = 'trilio.platform.job'
        aliases = ['job']
        aliases_only = True
        description = "trilio Backup job management"

    def _ext_parse_args(self):
        TrilioPlatformControllerChild._ext_parse_args(self)



    @expose()
    @check_error
    def cmd1(self):
        """This is an example command
        """
        self.app.print_output(u'I am cmd1')
    
    @expose(aliases=[u'cmd2 <arg1> [arg2=value]'], aliases_only=True)
    @check_error
    def cmd2(self):
        """This is another example command
        """
        arg1 = self.get_arg(name=u'arg1')
        arg2 = self.get_arg(name=u'arg2', default=u'arg2_val', keyvalue=True)
        res = [
            {u'k': u'arg1', u'v': arg1},
            {u'k': u'arg2', u'v': arg2},
        ]
        self.result(res, headers=[u'key', u'value'], fields=[u'k', u'v'])

    @expose()
    @check_error
    def prova(self):
        """This is an example command
        """
        self.app.print_output(u'I am cmd1')
        res=self.util.jobs.get_backups_status()

    @expose(aliases=[u'status <UID>'], aliases_only=True)
    @check_error
    def status(self):
        """This command will list all the status of the backup job identified by UID
        """
        uid = self.get_arg(name=u'UID')

        urn, veeam, job, obj32 = uid.split(':')
        href= self.uri + '/api/jobs/'+obj32 + '/backupSessions'

        res = self.util.jobs.get_job_props(href)
        sessioni = len(res['data']['BackupJobSessions']['BackupJobSession'])

        Data="2000-01-01T00:00:00"
        i=0
        for element in res['data']['BackupJobSessions']['BackupJobSession']:
            if (element[u'CreationTimeUTC'] > Data):
                Data=element[u'CreationTimeUTC']
                indice = i
            i=i+1


        # TO DO: gestire l'errore con status diverso da OK
        self.result(res['data']['BackupJobSessions']['BackupJobSession'][indice], headers=[u'Job Name',u'Job UID',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC'],
                    fields=[ u'JobName',u'JobUid',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC'])




trilio_controller_handlers = [
    TrilioPlatformController,
    TrilioPlatformConfigController,
    TrilioPlatformJobController ]