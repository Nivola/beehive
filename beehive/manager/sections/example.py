"""
Created on Jan 18, 2018

@author: darkbk

passi principali:
- creo un modulo in sections
- creo un controller nested in base -> ExampleController
- creo una lista dove inserisco progressivamente tutti i controller -> example_controller_handlers
- aggiunto la lista dei controller alla app manager -> file manage.py riga 197

- per ogni nuovo controller ....
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController, check_error

logger = logging.getLogger(__name__)


class ExampleController(BaseController):
    class Meta:
        label = 'example'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Example section"
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(aliases=[u'cmd1 [key=value]'], aliases_only=True)
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


class Example2Controller(BaseController):
    class Meta:
        label = 'example2'
        stacked_on = 'example'
        stacked_type = 'nested'
        description = "Example nested section"
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*'))
        ]


example_controller_handlers = [
    ExampleController,
    Example2Controller,
]