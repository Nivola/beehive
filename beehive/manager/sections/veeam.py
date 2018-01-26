'''
Created on January 2018

@author: Mikebeauty
'''

import logging
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
    def list(self):
        """This is an example command
        """
        #self.app.print_output(u'I am getJobs')
        res = self.util.jobs.get_jobs()
        #self.result(res)  keys: [u'@UID', u'@Name', u'@Href', u'@Type', u'Links']
        self.result(res['data'], headers=[u'UID', u'Job Name',u'HREF',u'Type'], fields=[u'@UID', u'@Name', u'@Href'])


veeam_controller_handlers = [
    VeeamPlatformController,
    VeeamPlatformControllerChild,
    VeeamPlatformJobController]