"""
Created on Dec 20, 2017

@author: darkbk
"""
import logging
from time import sleep
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate
from beedrones.vsphere.client import VsphereManager
from beecell.remote import RemoteClient

logger = logging.getLogger(__name__)


#
# graphite native platform
#
class GraphitePlatformController(BaseController):
    class Meta:
        label = 'graphite.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Graphite Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class GraphitePlatformControllerChild(BaseController):
    entity_class = None

    class Meta:
        stacked_on = 'graphite.platform'
        stacked_type = 'nested'
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
            (['-O', '--orchestrator'],
             dict(action='store', help='Graphite platform reference label')),
        ]

    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)

        orchestrators = self.configs.get(u'orchestrators').get(u'graphite')
        label = self.app.pargs.orchestrator
        if label is None:
            raise Exception(u'Graphite platform label must be specified. ' \
                            u'Valid label are: %s' % u', '.join(orchestrators.keys()))

        if label not in orchestrators:
            raise Exception(u'Valid label are: %s' % u', '.join(orchestrators.keys()))
        conf = orchestrators.get(label)

        # self.client = VsphereManager(conf.get(u'vcenter'), conf.get(u'nsx'))


class GraphiteNodePlatformController(GraphitePlatformControllerChild):
    class Meta:
        label = 'graphite.platform.nodes'
        aliases = ['nodes']
        aliases_only = True
        description = "Graphite Nodes management"

    def _ext_parse_args(self):
        GraphitePlatformControllerChild._ext_parse_args(self)

        # self.entity_class = self.client.datacenter

    @expose(aliases=[u'list [field=value]'], aliases_only=True)
    def list(self):
        '''
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        objs = self.entity_class.list(**params)
        res = []
        for o in objs:
            res.append({
                u'id': o[u'obj']._moId,
                u'name': o[u'name'],
            })
        logger.info(res)'''
        res = [{u'name': u'pippo', u'id': 1}]
        self.result(res, headers=[u'id', u'name'])



graphite_controller_handlers = [
    GraphitePlatformController,
    GraphiteNodePlatformController,
]