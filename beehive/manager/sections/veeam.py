'''
Created on January 2018

@author: Mikebeauty
'''

import logging
import datetime
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error

from beedrones.veeam.client import VeeamManager, VeeamJob, VeeamClient
import json

logger = logging.getLogger(__name__)


#
# veeam native platform
#
class VeeamPlatformController(BaseController):
    class Meta:
        label = 'veeam.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Veeam Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class VeeamPlatformControllerChild(BaseController):
    #headers = [u'id', u'name']
    #entity_class = None

    class Meta:
        stacked_on = 'veeam.platform'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-O', '--orchestrator'], dict(action='store', help='Veeam platform reference label')),
        ]

    @check_error
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)

        orchestrators = self.configs[u'environments'][self.env][u'orchestrators'].get(u'veeam')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Veeam platform label must be specified. '
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        '''
        veeamTest = {'uri':'http://tst-veeamsrv.tstsddc.csi.it:9399',
                 'user':'Administrator',
                 'pwd':'cs1$topix', 'verified':False}
        '''

        conn = {'uri': conf.get(u'uri'), 'user':conf.get(u'user'),'pwd':conf.get(u'pwd'),'verified':conf.get(u'verified')}
        self.util = VeeamManager(conn)
        self.uri = conf.get(u'uri')

class VeeamPlatformJobController(VeeamPlatformControllerChild):
    headers = [u'id', u'name', u'domain_id']

    class Meta:
        label = 'veeam.platform.job'
        aliases = ['job']
        aliases_only = True
        description = "Veeam Backup job management"

    def _ext_parse_args(self):
        VeeamPlatformControllerChild._ext_parse_args(self)

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

    @expose()
    @check_error
    def list(self):
        """This command will list all the backup job configured on veeam server
        """

        res = self.util.jobs.get_jobs()
        # TO DO: gestire l'errore con status diverso da OK
        self.result(res['data'], headers=[u'UID', u'Job Name',u'HREF',u'Type'], fields=[u'@UID', u'@Name', u'@Href'])


    @expose(aliases=[u'showbyhref <href>'], aliases_only=True)
    @check_error
    def showbyhref(self):
        """This command will list all the properties of the backup job identified by href
        """
        href = self.get_arg(name=u'href')

        res = self.util.jobs.get_job_props(href)
        # TO DO: gestire l'errore con status diverso da OK
        '''  
        "JobType": "Backup", 
          "Platform": "VMware", 
          "Description": "Created by TST-VEEAMSRV\\Administrator at 26/04/2016 15:42.", 
          "ScheduleConfigured": "true", 
          "ScheduleEnabled": "false", 
        '''
        # TO DO: gestire l'errore con status diverso da OK
        self.result(res['data']['Job'], headers=[u'Job Name',u'Description',u'JobType',u'Platform',u'ScheduleConfigured',u'ScheduleEnabled'],
                    fields=[ u'@Name',u'Description',u'JobType',u'Platform',u'ScheduleConfigured',u'ScheduleEnabled'])

    @expose(aliases=[u'show <UID>'], aliases_only=True)
    @check_error
    def show(self):
        """This command will list all the properties of the backup job identified by UID
        """
        uid = self.get_arg(name=u'UID')

        urn, veeam, job, obj32 = uid.split(':')
        href= self.uri + '/api/jobs/'+obj32

        #self.app.print_output(u'Href = '+href)
        res = self.util.jobs.get_job_props(href)
        # TO DO: gestire l'errore con status diverso da OK
        self.result(res['data']['Job'], headers=[u'Job Name',u'Description',u'JobType',u'Platform',u'ScheduleConfigured',u'ScheduleEnabled'],
                    fields=[ u'@Name',u'Description',u'JobType',u'Platform',u'ScheduleConfigured',u'ScheduleEnabled'])


    @expose()
    @check_error
    def statusall(self):
        """This command will list the status of ALL the backup jobs configured on server
        """

        res = self.util.jobs.get_backups_status()
        #print(res)
        self.result(res['data'], headers=[u'Job Name',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC',u'elapsed'],
                    fields=[ u'JobName',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC',u'ElapsedTime'])


    @expose(aliases=[u'status <UID>'], aliases_only=True)
    @check_error
    def status(self):
        """This command will list all the status of the backup job identified by UID
        """
        uid = self.get_arg(name=u'UID')

        urn, veeam, job, obj32 = uid.split(':')
        href= self.uri + '/api/jobs/'+obj32 + '/backupSessions'

        #self.app.print_output(u'Href = '+href)
        res = self.util.jobs.get_job_props(href)
        sessioni = len(res['data']['BackupJobSessions']['BackupJobSession'])
        #sessionezero=res['data']['BackupJobSessions']['BackupJobSession'][0].keys()

        #self.app.print_output(u'Numero sessioni = ' + str(sessioni))
        #self.app.print_output(u'keys sessione 0 = ' + str(sessionezero))
        # keys sessionezero = [u'@Href', u'@Type', u'@Name',
        # u'@UID', u'Links', u'JobUid', u'JobName', u'JobType', u'CreationTimeUTC', u'EndTimeUTC',
        # u'State', u'Result', u'Progress', u'IsRetry']
        #self.app.print_output(u'data Creatione 0 = '
        #                      + str(res['data']['BackupJobSessions']['BackupJobSession'][0]['CreationTimeUTC']))
        #self.app.print_output(u'data Creatione ultima = '
        #                      + str(res['data']['BackupJobSessions']['BackupJobSession'][sessioni-1]['CreationTimeUTC']))

        Data="2000-01-01T00:00:00"
        i=0
        for element in res['data']['BackupJobSessions']['BackupJobSession']:
            if (element[u'CreationTimeUTC'] > Data):
                Data=element[u'CreationTimeUTC']
                indice = i
                #FineJob=element[u'EndTimeUTC']
                #Stato=element[u'State']
                #Result=element[u'Result']
            i=i+1

        # TO DO: gestire l'errore con status diverso da OK
        #durata = (res['data']['BackupJobSessions']['BackupJobSession'][indice]['EndTimeUTC'])-int(res['data']['BackupJobSessions']['BackupJobSession'][indice]['CreationTimeUTC'])
        #self.app.print_output(u'durata = '+ durata)

        # TO DO: gestire l'errore con status diverso da OK
        self.result(res['data']['BackupJobSessions']['BackupJobSession'][indice], headers=[u'Job Name',u'Job UID',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC'],
                    fields=[ u'JobName',u'JobUid',u'Result',u'State',u'CreationTimeUTC',u'EndTimeUTC'])




veeam_controller_handlers = [
    VeeamPlatformController,
    VeeamPlatformControllerChild,
    VeeamPlatformJobController]