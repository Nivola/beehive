import ujson as json
from pprint import PrettyPrinter
from beehive.common.apiclient import BeehiveApiClient

class ApiManager(object):
    def __init__(self, auth_config):
        if auth_config[u'endpoint'] is None:
            raise Exception(u'Auth endpoint is not configured')
        
        self.client = BeehiveApiClient(auth_config[u'endpoint'], 
                                       auth_config[u'user'], 
                                       auth_config[u'pwd'],
                                       auth_config[u'catalog'])
        self.pp = PrettyPrinter(width=200)
        self.subsytem = None
        self.logger = None
        self.baseuri = None
        
    def _call(self, uri, method, data=u'', headers=None):
        res = self.client.invoke(self.subsystem, uri, method, data=data, 
                                 other_headers=headers, parse=True)
        return res
    
    def load_config_file(self, filename):
        """
        """
        f = open(filename, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config        