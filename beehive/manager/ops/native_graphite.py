'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager, ComponentManager
import sys
import abc
from beedrones.vsphere.client import VsphereManager
from beecell.simple import truncate
from beedrones.graphite.client import GraphiteManager

logger = logging.getLogger(__name__)

class NativeGraphiteManager(ComponentManager):
    """
    SECTION: 
        native.graphite <orchestrator-id>
        
    PARAMS:
        nodes list                  get list of nodes configured in graphite.
        node metrics <oid> [<type>] [<minutes>]
                                    get node <oid> metrics.
                                    - type: virtual [default], physical
                                    - minutes: 1 [defualt]


    """    
    def __init__(self, auth_config, env, frmt=u'json', orchestrator_id=None):
        ComponentManager.__init__(self, auth_config, env, frmt)
        
        self.conf = auth_config.get(u'orchestrators')\
                               .get(u'graphite')\
                               .get(orchestrator_id)
        if self.conf is None:
            raise Exception(u'Orchestrator %s is not configured' % orchestrator_id)
    
    @staticmethod
    def get_params(args):
        try: cid = args.pop(0)
        except:
            raise Exception(u'ERROR : Graphite id is missing')
        return {u'orchestrator_id':cid}      
    
    def get_args(self, args):
        res = {}
        for arg in args:
            k,v = arg.split(u'=')
            if v in [u'False', u'false']:
                v = False
            elif v in [u'True', u'true']:
                v = True
            res[k] = v
        return res    
    
    def actions(self):
        actions = {
            u'nodes.list': self.list_nodes,
            u'node.metrics': self.get_metrics,
        }
        return actions    
    
    #
    # ansible
    #
    def list_nodes(self):
        """list nodes
        """
        client = GraphiteManager(self.conf.get(u'host'), 
                                 env=self.conf.get(u'search-path'))
        res = []
        data = client.get_nodes(self.conf.get(u'type'))
        for item in data:
            res.append({u'platform':self.conf.get(u'type'), u'node':item})
        self.result(res, headers=[u'platform', u'node'])
    
    def get_metrics(self, oid, *args):
        """Get node metrics
        """
        args = self.get_args(args)
        ntype = args.get(u'type', u'virtual')
        minutes = args.get(u'minutes', 2)
        platform = self.conf.get(u'type')
        client = GraphiteManager(self.conf.get(u'host'), 
                                 env=self.conf.get(u'search-path'))
        if ntype == u'virtual':
            metrics = client.get_virtual_node_metrics(platform, oid, minutes)
        elif ntype == u'physical':
            metrics = client.get_physical_node_metrics(platform, oid, minutes)
        data = client.format_metrics(oid, metrics, platform)
        self.logger.debug(data)
        res = []
        for k,v in data.items():
            for v1 in v:
                res.append({u'metric':k, u'timestamp':v1[1], u'value':v1[0]})
        self.result(res, headers=[u'metric', u'timestamp', u'value'])
        
