import json
import yaml
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
    use: manage.py [OPTION]... <SECTION> [PARAMs]...
    
    Beehive manager.
    
    OPTIONs:
        -c, --config        json auth config file
        -f, --format        output format: json, yaml, text, table
        -h, --help          manager help
        -e, --env           set environment to use. Ex. test, lab, prod
    
    Exit status:
        0  if OK,
        1  if problems occurred"""
    def __init__(self, auth_config, env, frmt):
        self.logger = getLogger(self.__class__.__module__+ \
                                u'.'+self.__class__.__name__)
        self.env = env
        self.json = None
        self.text = []
        self.pp = PrettyPrinter(width=200)        
        self.format = frmt      
        self.color = auth_config[u'color']
        
        self.perm_headers = [u'pid', u'oid', u'objtype', u'objdef', u'objid', 
                             u'action']
        self.perm_fields = [u'0.0', u'0.1', u'0.2', u'0.3', u'0.4', u'0.6']
        
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
    
    def __tabularprint(self, data, headers=None, other_headers=[], fields=None):
        '''if u'count' in data.keys():
            data.pop(u'count')
            values = data.values()[0]
        else:
            values = data.values()'''
        if not isinstance(data, list):
            values = [data]
        else:
            values = data
        if headers is None:
            headers = [u'id', u'uuid', u'name', u'parent_id', u'parent_name',
                       u'active', u'date.creation']
        headers.extend(other_headers)
        table = []
        if fields is None:
            fields = headers
        for item in values:
            raw = []
            for key in fields:
                val = self.__multi_get(item, key)
                raw.append(val)
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
               fields=None):
        """
        """
        if key is not None:
            data = data[key]
        
        if u'jobid' in data:
            print(u'Start JOB: %s' % data.get(u'jobid'))
            print(u'')
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
                if isinstance(data, dict) or isinstance(data, list):
                    self.__tabularprint(data, other_headers=other_headers,
                                        headers=headers, fields=fields)
            
        elif self.format == u'text':       
            self.format_text(data)
            if len(self.text) > 0:
                print(u'\n'.join(self.text))
                    
        elif self.format == u'doc':
            print(data)
        
        if delta is not None:
            sleep(delta)
            
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
    
    @staticmethod
    def main(auth_config, frmt, opts, args, env, component_class, 
             *vargs, **kvargs):
        """Component main
        
        :param auth_config: {u'pwd': u'..', 
                             u'endpoint': u'http://10.102.160.240:6060/api/', 
                             u'user': u'admin@local'}
        """
        #try:
        #    args[1]
        #except:
        #    print(ComponentManager.__doc__)
        #    print(component_class.__doc__)
        #    return 0

        logger.debug(u'Format %s' % frmt)
        logger.debug(u'Get component class %s' % component_class)
        
        client = component_class(auth_config, env, frmt=frmt, *vargs, **kvargs)
        actions = client.actions()
        logger.debug(u'Available actions %s' % 
                     PrettyPrinter(width=200).pformat(actions.keys()))
        
        if len(args) > 0:
            entity = args.pop(0)
            logger.debug(u'Get entity %s' % entity)
        else: 
            raise Exception(u'ERROR: ENTITY is not specified')
            return 1

        if len(args) > 0:
            operation = args.pop(0)
            logger.debug(u'Get operation %s' % operation)
            action = u'%s.%s' % (entity, operation)
        else: 
            raise Exception(u'ERROR: command is not specified')
            return 1
        
        #print(u'platform %s %s response:' % (entity, operation))
        #print(u'---------------------------------------------------------------')
        print(u'')
        
        if action is not None and action in actions.keys():
            func = actions[action]
            res = func(*args)
        else:
            raise Exception(u'ERROR: Entity and/or command are not correct')      
            return 1
        
        '''
        if frmt == u'text':
            if len(client.text) > 0:
                print(u'\n'.join(client.text))
        else:
            if client.json is not None:
                if isinstance(client.json, dict) or isinstance(client.json, list):
                    client.pp.pprint(client.json)
                else:
                    print(client.json)'''
            
        return 0

class ApiManager(ComponentManager):
    def __init__(self, auth_config, env, frmt=u'json'):
        ComponentManager.__init__(self, auth_config, env, frmt)
        config = auth_config[u'environments'][env]
    
        if config[u'endpoint'] is None:
            raise Exception(u'Auth endpoint is not configured')
        
        self.client = BeehiveApiClient(config[u'endpoint'], 
                                       config[u'user'], 
                                       config[u'pwd'],
                                       config[u'catalog'])
        self.subsytem = None
        self.baseuri = None
        
    def _call(self, uri, method, data=u'', headers=None):
        res = self.client.invoke(self.subsystem, uri, method, data=data, 
                                 other_headers=headers, parse=True)
        if self.format == u'doc':
            res = self.client.get_api_doc(self.subsystem, uri, method, data=data, 
                                          sync=True, title=u'', desc= u'', output=res)
        return res
    
    def load_config_file(self, filename):
        """
        """
        f = open(filename, 'r')
        config = f.read()
        config = json.loads(config)
        f.close()
        return config        