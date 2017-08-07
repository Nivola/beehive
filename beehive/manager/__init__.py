import json
import yaml
import os
from beecell.simple import truncate
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from pprint import PrettyPrinter
from beehive.common.apiclient import BeehiveApiClient
from logging import getLogger
from urllib import urlencode
from time import sleep
from pygments import highlight
from pygments import lexers
from pygments.formatters import Terminal256Formatter
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Token
from pygments.filter import Filter
from pprint import pformat
from re import match
from tabulate import tabulate
from time import sleep

logger = getLogger(__name__)

class JsonStyle(Style):
    default_style = ''
    styles = {
        Token.Name.Tag: u'bold #ffcc66',
        Token.Literal.String.Double: u'#fff',
        Token.Literal.Number: u'#0099ff',
        Token.Keyword.Constant: u'#ff3300'
    }
    
class YamlStyle(Style):
    default_style = ''
    styles = {
        Token.Literal.Scalar.Plain: u'bold #ffcc66',
        Token.Literal.String: u'#fff',
        Token.Literal.Number: u'#0099ff',
        Token.Operator: u'#ff3300'
    }    

class JsonFilter(Filter):
    def __init__(self, **options):
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        for ttype, value in stream:
            rtype = ttype
            if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}'\
                     u'-[0-9a-f]{12}', value.strip(u'"')):
                rtype = Token.Literal.Number            
            yield rtype, value

class YamlFilter(Filter):
    def __init__(self, **options):
        Filter.__init__(self, **options)
        self.prev_tag1 = None
        self.prev_tag2 = None

    def filter(self, lexer, stream):
        for ttype, value in stream:
            rtype = ttype
            if self.prev_tag1 == u':' and \
               self.prev_tag2 == u' ' and \
               ttype == Token.Literal.Scalar.Plain:
                rtype = Token.Literal.String
            elif self.prev_tag1 != u'-' and \
                 self.prev_tag2 == u' ' and \
                 ttype == Token.Literal.Scalar.Plain:
                rtype = Token.Literal.String
            try:
                int(value)
                rtype = Token.Literal.Number
            except: pass
            if value == u'null':
                rtype = Token.Operator
            if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}'\
                     u'-[0-9a-f]{12}', value):
                rtype = Token.Literal.Number
            self.prev_tag1 = self.prev_tag2
            self.prev_tag2 = value
            yield rtype, value

class ComponentManager(object):
    """
    use: beehive [OPTION]... <SECTION> [PARAMs]...
    
    Beehive manager.
    
    OPTIONs:
        -c, --config        json auth config file [default=/etc/beehive/manage.conf]
        -f, --format        output format: json, yaml, custom, table [default]
        -h, --help          get beehive <SECTION> help
        -e, --env           set environment to use. Ex. test, lab, prod
    
    PARAMs:
        <custom param>, ..  <SECTION> params 
        HELP                get beehive <SECTION> help
    
    Exit status:
        0  if OK,
        1  if problems occurred  
    """
    formats = [u'json', u'yaml', u'table', u'custom']
    
    def __init__(self, auth_config, env, frmt):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)
        self.env = env
        self.json = None
        self.text = []
        self.pp = PrettyPrinter(width=200)        
        self.format = frmt      
        self.color = auth_config[u'color']
        self.token_file = auth_config[u'token_file']
        self.seckey_file = auth_config[u'seckey_file']
        
        self.perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', 
                             u'aid', u'action', u'desc']
        
    def __jsonprint(self, data):
        data = json.dumps(data, indent=2)
        if self.color == 1:
            l = lexers.JsonLexer()
            l.add_filter(JsonFilter())
            #for i in l.get_tokens(data):
            #    print i        
            print highlight(data, l, Terminal256Formatter(style=JsonStyle))
        else:
            print data
        
    def __yamlprint(self, data):
        data = yaml.safe_dump(data, default_flow_style=False)
        if self.color == 1:
            l = lexers.YamlLexer()
            l.add_filter(YamlFilter())
            #for i in l.get_tokens(data):
            #    print i
            from pygments import lex
            #for item in lex(data, l):
            #    print item       
            print highlight(data, l, Terminal256Formatter(style=YamlStyle))
        else:
            print data
        
    def __textprint(self, data):
        if self.color == 1:
            #lexer = lexers.
            lexer = lexers.VimLexer
            l = lexer()          
            print highlight(data, l, Terminal256Formatter())
        else:
            print data
    
    def __multi_get(self, data, key):
        keys = key.split(u'.')
        res = data
        for k in keys:
            if isinstance(res, list):
                res = res[int(k)]
            else:
                res = res.get(k, {})
        return res
    
    def __tabularprint(self, data, headers=None, other_headers=[], fields=None,
                       maxsize=20):
        if not isinstance(data, list):
            values = [data]
        else:
            values = data
        if headers is None:
            headers = [u'id', u'name']
        headers.extend(other_headers)
        table = []
        if fields is None:
            fields = headers
        for item in values:
            raw = []
            if isinstance(item, dict):
                for key in fields:
                    val = self.__multi_get(item, key)
                    raw.append(truncate(val, maxsize))
            else:
                raw.append(truncate(item, maxsize))
            table.append(raw)
        print(tabulate(table, headers=headers, tablefmt=u'fancy_grid'))
        print(u'')
    
    def __format(self, data, space=u'', delimiter=u':', key=None):
        """
        """
        if isinstance(data, str) or isinstance(data, unicode):
            data = u'%s' % data
        if key is not None:
            frmt = u'%s%-s%s %s'
        else:
            frmt = u'%s%s%s%s'
            key = u''

        if isinstance(data, str):
            data = data.rstrip().replace(u'\n', u'')
            self.text.append(frmt % (space, key, delimiter, data))
        elif isinstance(data, unicode):
            data = data.rstrip().replace(u'\n', u'')
            self.text.append(frmt % (space, key, delimiter, data))
        elif isinstance(data, int):
            self.text.append(frmt % (space, key, delimiter, data))
        elif isinstance(data, tuple):
            self.text.append(frmt % (space, key, delimiter, data))            
    
    def format_text(self, data, space=u'  '):
        """
        """
        if isinstance(data, dict):
            for k,v in data.items():
                if isinstance(v, dict) or isinstance(v, list):
                    self.__format(u'', space, u':', k)
                    self.format_text(v, space+u'  ')
                else:
                    self.__format(v, space, u':', k)
        elif isinstance(data, list):
            for v in data:
                if isinstance(v, dict) or isinstance(v, list):
                    self.format_text(v, space+u'  ')
                else:
                    self.__format(v, space, u'', u'')
                #if space == u'  ':                
                #    self.text.append(u'===================================')
                #self.__format(u'===================================', space, u'', None)
        else:
            self.__format(data, space)
    
    def result(self, data, delta=None, other_headers=[], headers=None, key=None, 
               fields=None, details=False, maxsize=50):
        """
        """
        if key is not None:
            data = data[key]
    
        if isinstance(data, dict) and u'jobid' in data:
            jobid = data.get(u'jobid')
            print(u'Start JOB: %s' % jobid)
            self.query_task_status(jobid)
            return None
        
        if self.format == u'json':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__jsonprint(data)                
            
        elif self.format == u'yaml':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__yamlprint(data)
            
        elif self.format == u'table':
            if data is not None:
                # convert input data for query with one raw
                if details is True:
                    resp = []
                    
                    def __format_table_data(k, v):
                        if isinstance(v, list):
                            i = 0
                            for n in v:
                                __format_table_data(u'%s.%s' % (k,i), n)
                                i += 1
                        elif isinstance(v, dict):
                            for k1,v1 in v.items():
                                __format_table_data(u'%s.%s' % (k,k1), v1)
                        else:
                            resp.append({u'attrib':k, 
                                         u'value':truncate(v, size=80)})                        
                    
                    for k,v in data.items():
                        __format_table_data(k, v)

                    data = resp
                    headers=[u'attrib', u'value']
                    maxsize = 100

                if isinstance(data, dict) or isinstance(data, list):
                    self.__tabularprint(data, other_headers=other_headers,
                                        headers=headers, fields=fields,
                                        maxsize=maxsize)
            
        elif self.format == u'custom':       
            self.format_text(data)
            if len(self.text) > 0:
                print(u'\n'.join(self.text))
                    
        elif self.format == u'doc':
            print(data)
        
        #if delta is not None:
        #    sleep(delta)
            
    def load_config(self, file_config):
        f = open(file_config, 'r')
        auth_config = f.read()
        auth_config = json.loads(auth_config)
        f.close()
        return auth_config
    
    def format_http_get_query_params(self, *args):
        """
        """
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        return urlencode(val)
    
    def get_query_params(self, *args):
        """
        """
        val = {}
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        return val   
    
    def get_token(self):
        """Get token and secret key from file.
        
        :return: token
        """
        token = None
        if os.path.isfile(self.token_file) is True:
            # get token
            f = open(self.token_file, u'r')
            token = f.read()
            f.close()
        
        seckey = None
        if os.path.isfile(self.seckey_file) is True:
            # get secret key
            f = open(self.seckey_file, u'r')
            seckey = f.read()
            f.close()
        return token, seckey
    
    def save_token(self, token, seckey):
        """Save token and secret key on a file.
        
        :param token: token to save
        """
        # save token
        f = open(self.token_file, u'w')
        f.write(token)
        f.close()
        # save secret key
        if seckey is not None:
            f = open(self.seckey_file, u'w')
            f.write(seckey)
            f.close() 
    
    @staticmethod
    def get_params(args):
        return {}
    
    @classmethod
    def main(cls, auth_config, frmt, opts, args, env, *vargs, **kvargs):
        """Component main
        
        :param auth_config: {u'pwd': u'..', 
                             u'endpoint': u'http://10.102.160.240:6060/api/', 
                             u'user': u'admin@local'}
        :param frt:
        :param opts:
        :param args:
        :param env:
        :param vargs: custom params
        :param kvargs: custom dict params
        """
        #try:
        #    args[1]
        #except:
        #    print(ComponentManager.__doc__)
        #    print(component_class.__doc__)
        #    return 0

        logger.debug(u'Format %s' % frmt)
        logger.debug(u'Get component class %s' % cls.__name__)

        kvargs = cls.get_params(args)
        client = cls(auth_config, env, frmt=frmt, *vargs, **kvargs)
        actions = client.actions()
        logger.debug(u'Available actions %s' % actions.keys())
        #PrettyPrinter(width=200).pformat(actions.keys()))
        
        if len(args) > 0:
            entity = args.pop(0)
            logger.debug(u'Get entity %s' % entity)
        else: 
            raise Exception(u'Entity must be specified')
            return 1

        if len(args) > 0:
            operation = args.pop(0)
            logger.debug(u'Get operation %s' % operation)
            action = u'%s.%s' % (entity, operation)
        else: 
            raise Exception(u'Command must be specified')
            return 1
        
        #print(u'platform %s %s response:' % (entity, operation))
        #print(u'---------------------------------------------------------------')
        print(u'')
        
        if action is not None and action in actions.keys():
            func = actions[action]
            func(*args)
        else:
            raise Exception(u'Entity and/or command are not correct')      
            return 1
            
        return 0

class ApiManager(ComponentManager):
    def __init__(self, auth_config, env, frmt=u'json'):
        ComponentManager.__init__(self, auth_config, env, frmt)
        config = auth_config[u'environments'][env]
    
        if config[u'endpoint'] is None:
            raise Exception(u'Auth endpoint is not configured')
        
        client_config = config.get(u'oauth2-client', None)
        self.client = BeehiveApiClient(config[u'endpoint'],
                                       config[u'authtype'],
                                       config[u'user'], 
                                       config[u'pwd'],
                                       config[u'catalog'],
                                       client_config=client_config)
        self.subsytem = None
        self.baseuri = None
        
        # get token
        self.client.uid, self.client.seckey  = self.get_token()        
    
        if self.client.uid is None:
            # create token
            self.client.create_token()
        
            # set token
            self.save_token(self.client.uid, self.client.seckey)        
        
    def _call(self, uri, method, data=u'', headers=None):        
        # make request
        res = self.client.invoke(self.subsystem, uri, method, data=data, 
                                 other_headers=headers, parse=True)
        if self.format == u'doc':
            res = self.client.get_api_doc(self.subsystem, uri, method, data=data, 
                                          sync=True, title=u'', desc= u'', output=res)
        #self.client.logout()
        
        # set token
        self.save_token(self.client.uid, self.client.seckey)
        
        return res
    
    def __query_task_status(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/' % task_id
        res = self._call(uri, u'GET').get(u'task-instance')
        #print res
        #self.logger.info(res)
        #resp = []
        #resp.append(res)
        #resp.extend(res.get(u'children'))
        #self.result(resp, headers=[u'task_id', u'type', u'status', u'name', 
        #                          u'start_time', u'stop_time', u'elapsed'])
        return res
        
    def query_task_status(self, task_id):
        while(True):
            res = self.__query_task_status(task_id)
            status = res[u'status']
            print status
            if status in [u'SUCCESS', u'FAILURE']:
                break
            sleep(1)
    
    def load_config_file(self, filename):
        """
        """
        f = open(filename, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config        