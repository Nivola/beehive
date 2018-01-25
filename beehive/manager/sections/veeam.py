'''
Created on January 2018

@author: Mikebeauty
'''

import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error

logger = logging.getLogger(__name__)


class VeeamController(BaseController):
    class Meta:
        label = 'veeam'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Veeam section"
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

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
    
    
veeam_controller_handlers = [
    VeeamController]