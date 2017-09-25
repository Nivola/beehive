'''
Created on Sep 22, 2017

@author: darkbk
'''
import json
import yaml
import os
import textwrap
import sys
from beecell.simple import truncate, str2bool
from cement.core.controller import CementBaseController
from functools import wraps
import logging
from beecell.logger.helper import LoggerHelper
from beehive.common.log import ColorFormatter
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
from re import match, sub
from tabulate import tabulate
from time import sleep

logger = getLogger(__name__)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_error(error):
    """Print error
    """
    print(bcolors.FAIL + u'   ERROR : ' + bcolors.ENDC +
      bcolors.FAIL + bcolors.BOLD + str(error) + bcolors.ENDC)

def check_error(fn):
    """Use this decorator to return error message if an exception was raised
    
    Example::
    
        @check_error
        def fn(*args, **kwargs):
            ....    
    """
    @wraps(fn)
    def check_error_inner(*args, **kwargs):
        try:
            # call internal function
            res = fn(*args, **kwargs)
            return res      
        except Exception as ex:
            logger.error(ex, exc_info=1)
            print_error(ex)
            exit(1)
    return check_error_inner

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

class BaseController(CementBaseController):
    """
    """
    perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', u'aid', 
                    u'action', u'desc']    
    
    class Meta:
        label = u'abstract'
        description = "abstract"
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
        ]
    
        formats = [u'json', u'yaml', u'table', u'custom', u'native']
    
    def _setup(self, base_app):
        CementBaseController._setup(self, base_app)
        
        self.text = []
        self.pp = PrettyPrinter(width=200)
        self.app._meta.token_file = self.app._meta.token_file
        self.app._meta.seckey_file = self.app._meta.seckey_file
        
        # get configs
        self.configs = self.app.config.get_section_dict(u'configs')
        
    @property
    def _help_text(self):
        """Returns the help text displayed when '--help' is passed."""

        cmd_txt = ''
        for label in self._visible_commands:
            cmd = self._dispatch_map[label]
            if len(cmd['aliases']) > 0 and cmd['aliases_only']:
                if len(cmd['aliases']) > 1:
                    first = cmd['aliases'].pop(0)
                    cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                        (first, ', '.join(cmd['aliases']))
                else:
                    cmd_txt = cmd_txt + "  %s\n" % cmd['aliases'][0]
            elif len(cmd['aliases']) > 0:
                cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
                    (label, ', '.join(cmd['aliases']))
            else:
                cmd_txt = cmd_txt + "  %s\n" % label

            if cmd['help']:
                cmd_txt = cmd_txt + "    %s\n\n" % cmd['help']
            else:
                cmd_txt = cmd_txt + "\n"

        if len(cmd_txt) > 0:
            txt = '''%s

commands:
%s


        ''' % (self._meta.description, cmd_txt)
        else:
            txt = self._meta.description

        return textwrap.dedent(txt)        
    
    @check_error
    def _parse_args(self):
        CementBaseController._parse_args(self)
        
        configs = self.app.config.get_section_dict(u'configs')
        envs = u', '.join(configs[u'environments'].keys())
        default_env = configs[u'environments'].get(u'default', None)
        
        self.format = self.app.pargs.format
        if self.format is None:
            self.format = u'table'
        if self.app.pargs.format is None:
            self.color = True
        else:
            self.color = str2bool(self.app.pargs.format)
        self.env = self.app.pargs.env
        if self.env is None:
            if default_env is not None:
                self.env = default_env
            else:
                raise Exception(u'Platform environment must be defined. '\
                                u'Select from: %s' % envs)
        if self.env not in envs:
            raise Exception(u'Platform environment %s does not exist. Select '\
                            u'from: %s' % (self.env, envs))            
        
    @check_error  
    def run(self):
        """
        This function wraps everything together (after self._setup() is
        called) to run the application.

        :returns: Returns the result of the executed controller function if
          a base controller is set and a controller function is called,
          otherwise ``None`` if no controller dispatched or no controller
          function was called.

        """
        return_val = None

        logger.debug('running pre_run hook')
        for res in self.hook.run('pre_run', self):
            pass

        # If controller exists, then dispatch it
        if self.controller:
            return_val = self.controller._dispatch()
        else:
            self._parse_args()

        logger.debug('running post_run hook')
        for res in self.hook.run('post_run', self):
            pass

        return return_val
        
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
        else:
            self.__format(data, space)
    
    def result(self, data, delta=None, other_headers=[], headers=None, key=None, 
               fields=None, details=False, maxsize=50):
        """
        """
        logger.debug(u'result format: %s' % self.format)
        orig_data = data
        
        if self.format == u'native':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__jsonprint(data)          
        
        if key is not None:
            data = data[key]
        elif u'msg' in data:
            maxsize = 200
            headers = [u'msg']
    
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
                    if u'page' in orig_data:
                        print(u'Page: %s' % orig_data[u'page'])
                        print(u'Count: %s' % orig_data[u'count'])
                        print(u'Total: %s' % orig_data[u'total'])
                        print(u'Order: %s %s' % (orig_data.get(u'sort').get(u'field'), 
                                                 orig_data.get(u'sort').get(u'order')))
                        print(u'')                    
                    self.__tabularprint(data, other_headers=other_headers,
                                        headers=headers, fields=fields,
                                        maxsize=maxsize)
            
        elif self.format == u'custom':       
            self.format_text(data)
            if len(self.text) > 0:
                print(u'\n'.join(self.text))
                    
        elif self.format == u'doc':
            print(data)
    
    def error(self, error):
        print_error(error)
    
    def load_config(self, file_config):
        f = open(file_config, 'r')
        data = f.read()
        data = json.loads(data)
        f.close()
        return data
    
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
        print args
        for arg in args:
            t = arg.split(u'=')
            val[t[0]] = t[1]
        return val   
    
    def get_token(self):
        """Get token and secret key from file.
        
        :return: token
        """
        token = None
        if os.path.isfile(self.app._meta.token_file) is True:
            # get token
            f = open(self.app._meta.token_file, u'r')
            token = f.read()
            f.close()
        
        seckey = None
        if os.path.isfile(self.app._meta.seckey_file) is True:
            # get secret key
            f = open(self.app._meta.seckey_file, u'r')
            seckey = f.read()
            f.close()
        return token, seckey
    
    def save_token(self, token, seckey):
        """Save token and secret key on a file.
        
        :param token: token to save
        """
        # save token
        f = open(self.app._meta.token_file, u'w')
        f.write(token)
        f.close()
        # save secret key
        if seckey is not None:
            f = open(self.app._meta.seckey_file, u'w')
            f.write(seckey)
            f.close()
        
    @check_error
    def get_arg(self, default=None, name=None):
        arg = None
        try:
            arg = self.app.pargs.extra_arguments.pop(0)
        except:
            if default is not None:
                arg = default
            elif name is not None:
                raise Exception(u'Param %s is not defined' % name)
        return arg            
            
class ApiController(BaseController):
    subsytem = None
    baseuri = None    
    
    def _setup(self, base_app):
        super(BaseController, self)._setup(base_app)     
        
    @check_error
    def _parse_args(self):
        BaseController._parse_args(self)

        config = self.app.config.get_section_dict(u'configs')\
                    [u'environments'][self.env]
    
        if config[u'endpoint'] is None:
            raise Exception(u'Auth endpoint is not configured')
        
        client_config = config.get(u'oauth2-client', None)
        self.client = BeehiveApiClient(config[u'endpoint'],
                                       config[u'authtype'],
                                       config[u'user'], 
                                       config[u'pwd'],
                                       config[u'catalog'],
                                       client_config=client_config)
        
        # get token
        self.client.uid, self.client.seckey  = self.get_token()        
    
        if self.client.uid is None:
            # create token
            self.client.create_token()
        
            # set token
            self.save_token(self.client.uid, self.client.seckey)
    
    @check_error 
    def _call(self, uri, method, data=u'', headers=None):        
        # make request
        res = self.client.invoke(self.subsystem, uri, method, data=data, 
                                 other_headers=headers, parse=True)
        
        # set token
        self.save_token(self.client.uid, self.client.seckey)
        
        return res
    
    def __query_task_status(self, task_id):
        uri = u'/v1.0/worker/tasks/%s/' % task_id
        res = self._call(uri, u'GET').get(u'task-instance')
        return res
    
    @check_error 
    def query_task_status(self, task_id):
        while(True):
            res = self.__query_task_status(task_id)
            status = res[u'status']
            print status
            if status in [u'SUCCESS', u'FAILURE']:
                break
            sleep(1)
                      