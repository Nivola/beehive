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
from cement.core.controller import CementBaseController, expose
from functools import wraps
import logging
from beecell.logger.helper import LoggerHelper
from beehive.common.log import ColorFormatter
from beecell.cement_cmd.foundation import CementCmdBaseController
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from pprint import PrettyPrinter
from beehive.common.apiclient import BeehiveApiClient, BeehiveApiClientError
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
from cryptography.fernet import Fernet

try:
    import asciitree
    asciitree_loaded = True
except:
    asciitree_loaded = False

logger = getLogger(__name__)


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
            args[0].app.print_error(ex)
            raise
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


class BaseController(CementCmdBaseController):
    """
    """
    perm_headers = [u'id', u'oid', u'objid', u'subsystem', u'type', u'aid', u'action', u'desc']
    
    class Meta:
        label = u'abstract'
        description = "abstract"
        arguments = [
            (['extra_arguments'], dict(action='store', nargs='*')),
        ]
    
        formats = [u'json', u'yaml', u'table', u'tree', u'custom', u'native']
    
    def _setup(self, base_app):
        CementCmdBaseController._setup(self, base_app)

        self.text = []
        self.pp = PrettyPrinter(width=200)
        
        # get configs
        self.configs = self.app.config.get_section_dict(u'configs')

    @property
    def _help_cmd_list(self):
        """Returns the help visible command list."""
        return self._visible_commands

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
    
    def _get_config(self, config):
        val = getattr(self.app.pargs, config, None)
        return val
        #if config in self.app.pargs.__dict__:
        #    return self.app.pargs.__dict__[config]
        #else:
        #    return None
    
    def _parse_args(self):
        self.app.args.cmd_list = self._help_cmd_list

        CementCmdBaseController._parse_args(self)

        envs = u', '.join(self.configs[u'environments'].keys())
        default_env = self.configs[u'environments'].get(u'default', None)
        if getattr(self.app._meta, u'env', None) is None:
            self.app._meta.env = default_env

        # get environment config from app custom args
        self.format = getattr(self.app.pargs, u'format', None)
        self.color = getattr(self.app.pargs, u'color', None)
        self.env = getattr(self.app.pargs, u'env', None)
        self.envs = getattr(self.app.pargs, u'envs', None)
        self.verbosity = getattr(self.app.pargs, u'verbosity', None)
        self.key = getattr(self.app.pargs, u'key', None)
        self.vault = getattr(self.app.pargs, u'vault', None)

        if self.format is None:
            self.format = self.app._meta.format
            setattr(self.app._parsed_args, u'format', self.format)
        if self.color is None:
            self.color = self.app._meta.color
            setattr(self.app._parsed_args, u'color', self.color)
        if self.verbosity is None:
            self.verbosity = self.app._meta.verbosity
            setattr(self.app._parsed_args, u'verbosity', self.verbosity)            
        if self.env is None:
            if self.app._meta.env is not None:
                self.env = self.app._meta.env
                setattr(self.app._parsed_args, u'env', self.env)
            else:
                raise Exception(u'Platform environment must be defined. Select from: %s' % envs)
        if self.env not in envs:
            raise Exception(u'Platform environment %s does not exist. Select from: %s' % (self.env, envs))
        if self.envs is not None:
            self.envs = self.envs.split(u',')

        # fernet key
        if self.key is None:
            self.key = self.app.fernet

        # ansible vault pwd
        if self.vault is None:
            self.vault = self.app.vault

        self.app._meta.token_file = self.app._meta.token_file + u'.' + self.env
        self.app._meta.seckey_file = self.app._meta.seckey_file + u'.' + self.env

    def check_secret_key(self):
        if self.key is None:
            raise Exception(u'Secret key is not defined')

    '''
    @check_error
    def _dispatch(self):
        """
        Takes the remaining arguments from self.app.argv and parses for a
        command to dispatch, and if so... dispatches it.

        """
        if hasattr(self._meta, 'epilog'):
            if self._meta.epilog is not None:
                self.app.args.epilog = self._meta.epilog

        self._arguments, self._commands = self._collect()
        self._process_commands()
        self._get_dispatch_command()

        if self._dispatch_command:
            if self._dispatch_command['func_name'] == '_dispatch':
                func = getattr(self._dispatch_command['controller'], '_dispatch')
                return func()
            else:
                self._process_arguments()
                self._parse_args()
                if not self._dispatch_command['func_name'] == 'default':
                    self._ext_parse_args()
                func = getattr(self._dispatch_command['controller'], self._dispatch_command['func_name'])
                return func()
        else:
            self._process_arguments()
            self._parse_args()'''
        
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
            lexer = lexers.VimLexer
            l = lexer()          
            print highlight(data, l, Terminal256Formatter())
        else:
            print data
    
    def __multi_get(self, data, key, separator=u'.'):
        keys = key.split(separator)
        res = data
        for k in keys:
            if isinstance(res, list):
                try:
                    res = res[int(k)]
                except:
                    res = {}
            else:
                res = res.get(k, {})
        if isinstance(res, list):
            res = json.dumps(res)
            # res = u','.join(str(res))
        if res is None or res == {}:
            res = u'-'
        
        return res
    
    def __tabularprint(self, data, table_style, headers=None, other_headers=[], fields=None, maxsize=20,
                       separator=u'.'):
        if data is None:
            data = u'-'
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
                    val = self.__multi_get(item, key, separator=separator)
                    raw.append(truncate(val, maxsize))
            else:
                raw.append(truncate(item, maxsize))
            
            table.append(raw)
        print(tabulate(table, headers=headers, tablefmt=table_style))
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

        :param data:
        :param space:
        :return:
        """
        if isinstance(data, dict):
            for k, v in data.items():
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

    @check_error
    def result(self, data, other_headers=[], headers=None, key=None, fields=None, details=False, maxsize=50,
               key_separator=u'.', format=None, table_style=u'simple'):
        """Print result with a certain format

        :param data: data to print
        :param other_headers:
        :param headers: list of headers to print with tabular format
        :param key: if set use data from data.get(key)
        :param fields: list of fields key used to print data with tabular format
        :param details: if True and format tabular print a vertical table where first column is the key and second
            column is the value
        :param maxsize: max field value length [default=50, 200 with details=True]
        :param key_separator: key separator used when parsing key [default=.]
        :param format: format used when print [default=text]
        :param table_style: table style used when format is tabular [defualt=simple]
        :return:
        """
        logger.debug(u'Result format: %s' % self.format)
        orig_data = data

        if format is None:
            format = self.format

        if format == u'native':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__jsonprint(data)          
        
        if key is not None:
            data = data[key]
        elif getattr(data, u'msg', None) is not None:
            maxsize = 200
            headers = [u'msg']
        
        if format == u'json':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__jsonprint(data)         
            
        elif format == u'yaml':
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    self.__yamlprint(data)

        elif format == u'tree':
            tr = asciitree.LeftAligned()
            print(tr(data))

        elif format == u'table' or format == u'text':
            if data is not None:
                # convert input data for query with one raw
                if details is True:
                    resp = []
                    maxsize = 200
                    
                    def __format_table_data(k, v):
                        if isinstance(v, list):
                            i = 0
                            for n in v:
                                __format_table_data(u'%s.%s' % (k, i), n)
                                i += 1
                        elif isinstance(v, dict):
                            for k1, v1 in v.items():
                                __format_table_data(u'%s.%s' % (k, k1), v1)
                        else:
                            resp.append({u'attrib': k, u'value': truncate(v, size=maxsize)})
                    
                    for k, v in data.items():
                        __format_table_data(k, v)

                    data = resp
                    headers = [u'attrib', u'value']
                    # maxsize = 100

                if isinstance(data, dict) or isinstance(data, list):
                    if u'page' in orig_data:
                        print(u'Page: %s' % orig_data[u'page'])
                        print(u'Count: %s' % orig_data[u'count'])
                        print(u'Total: %s' % orig_data[u'total'])
                        print(u'Order: %s %s' % (orig_data.get(u'sort').get(u'field'), 
                                                 orig_data.get(u'sort').get(u'order')))
                        print(u'')               
                    self.__tabularprint(data, table_style, other_headers=other_headers, headers=headers, fields=fields,
                                        maxsize=maxsize, separator=key_separator)
                    
        elif self.format == u'doc':
            print(data)
    
    def output(self, data, color=u'WHITEonBLACK'):
        self.app.print_output(data, color=color)
    
    def error(self, error):
        self.app.print_error(error)
    
    def load_config(self, file_config):
        """Load dict from a json formtted file.

        :param file_config: file name
        :return: data
        :rtype: dict
        """
        f = open(file_config, u'r')
        data = f.read()
        data = json.loads(data)
        f.close()
        return data

    def load_file(self, file_config):
        """Load data from a file.

        :param file_config: file name
        :return: data
        :rtype: dict
        """
        f = open(file_config, u'r')
        data = f.read()
        f.close()
        return data

    @check_error
    def format_http_get_query_params(self, *args):
        """
        """
        val = {}
        for arg in args:
            t = arg.split(u'=')
            if len(t) != 2:
                raise Exception(u'Param syntax must be key=value')
            val[t[0]] = t[1]
        return urlencode(val)

    def get_query_params(self, *args):
        """
        """
        val = {}
        for arg in args:
            t = arg.split(u'=')
            if len(t) == 2:
                if t[1] == 'null':
                    t[1] = None
                if t[1] == 'True' or t[1] == 'true':
                    t[1] = True
                if t[1] == 'False' or t[1] == 'false':
                    t[1] = False
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
        :param seckey: secret key to save
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

    def get_arg(self, default=None, name=None, keyvalue=False):
        """Get arguments from command line. Arguments can be positional or key/value. Example::

            arg1 arg2 key1=val1

        **arg1** and **arg2** are positional, **key1** is key/value. To read this value correctly use::

            arg1 = get_arg(name=u'arg1')
            arg2 = get_arg(name=u'arg2')
            arg3 = get_arg(name=u'key1', default=u'value1', keyvalue=True)

        :param default: default value for keyvalue argument
        :param name: argument name
        :param keyvalue: if True argument is keyvalue, if False argument i postional
        :return: argument value
        """
        if len(self.app.pargs.extra_arguments) > 0:
            self.app.args = []
            self.app.kvargs = {}

        while len(self.app.pargs.extra_arguments) > 0:
            item = self.app.pargs.extra_arguments.pop(0)
            if item.find(u'=') >= 0:
                t = item.split(u'=')
                if len(t) == 2:
                    if t[1] == 'null':
                        t[1] = None
                    elif t[1] == 'True' or t[1] == 'true':
                        t[1] = True
                    elif t[1] == 'False' or t[1] == 'false':
                        t[1] = False
                    elif t[1].find(u'{') >= 0:
                        t[1] = json.loads(t[1])
                    self.app.kvargs[t[0]] = t[1]
            else:
                self.app.args.append(item)

        if keyvalue is True:
            kvargs = getattr(self.app, u'kvargs', {})
            item = kvargs.get(name, default)
            return item

        arg = None
        try:
            arg = self.app.args.pop(0)
        except:
            if default is not None:
                arg = default
            elif name is not None:
                raise Exception(u'Param %s is not defined' % name)
        return arg

    def decrypt(self, data):
        """Decrypt data with symmetric encryption
        """
        self.check_secret_key()
        cipher_suite = Fernet(self.key)
        cipher_text = cipher_suite.decrypt(data)
        return cipher_text

    @expose(hide=True)
    def default(self):
        """Default controller command
        """
        if self.app.pargs.cmds is True:
            self.app.print_cmd_list()
        else:
            self.app.print_help()


class ApiController(BaseController):
    subsytem = None
    baseuri = None
    setup_cmp = True
    
    def _setup(self, base_app):
        BaseController._setup(self, base_app)
    
    @check_error    
    def split_arg(self, key, splitWith=u','):
        
        splitList = []
        
        values = self.get_arg(name=key, default=None, keyvalue=True)     
        if values is not None:
            for value in values.split(splitWith):
                splitList.append(value) 
        return splitList

    @check_error
    def _parse_args(self):
        BaseController._parse_args(self)

        if self.setup_cmp is True:
            logger.debug(u'--- Setup cmp ---')

            config = self.configs[u'environments'][self.env][u'cmp']

            if config[u'endpoint'] is None:
                raise Exception(u'Auth endpoint is not configured')

            # get user and password
            user_env = os.environ.get(u'BEEHIVE_CMP_USER', None)
            user_pwd_env = os.environ.get(u'BEEHIVE_CMP_USER_PWD', None)
            user = config.get(u'user', user_env)
            pwd = config.get(u'pwd', user_pwd_env)

            client_config = config.get(u'oauth2-client', None)
            self.client = BeehiveApiClient(config[u'endpoint'],
                                           config[u'authtype'],
                                           user,
                                           pwd,
                                           config[u'catalog'],
                                           client_config=client_config,
                                           key=self.key)

            # get token
            self.client.uid, self.client.seckey = self.get_token()

            if self.client.uid is None:
                # create token
                self.client.create_token()

                # set token
                self.save_token(self.client.uid, self.client.seckey)

    def _call(self, uri, method, data=u'', headers=None, timeout=30, silent=False):
        try:
            # make request
            resp = self.client.invoke(self.subsystem, uri, method, data=data, other_headers=headers, parse=True,
                                      timeout=timeout, silent=silent, print_curl=True)
        except BeehiveApiClientError as ex:
            raise
        finally:
            # set token3
            if self.client.uid is not None:
                self.save_token(self.client.uid, self.client.seckey)

        return resp
    
    # def __query_task_status(self, task_id):
    #     uri = u'%s/worker/tasks/%s' % (self.baseuri, task_id)
    #     res = self._call(uri, u'GET').get(u'task_instance')
    #     return res
    #
    # @check_error
    # def query_task_status(self, task_id):
    #     while True:
    #         res = self.__query_task_status(task_id)
    #         status = res[u'status']
    #         sys.stdout.write(u'.')
    #         # print(u'.')
    #         if status in [u'SUCCESS', u'FAILURE']:
    #             break
    #         sleep(1)

    def get_job_state(self, jobid):
        try:
            res = self._call(u'%s/worker/tasks/%s' % (self.baseuri, jobid), u'GET', silent=True)
            state = res.get(u'task_instance').get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                # print(res)
                self.app.print_error(res[u'task_instance'][u'traceback'][-1])
            return state
        except (Exception):
            return u'EXPUNGED'

    def wait_job(self, jobid, delta=2, maxtime=180):
        """Wait job
        """
        logger.debug(u'wait for job: %s' % jobid)
        state = self.get_job_state(jobid)
        sys.stdout.write(u'JOB:%s' % jobid)
        sys.stdout.flush()
        elapsed = 0
        while state not in [u'SUCCESS', u'FAILURE', u'TIMEOUT']:
            sys.stdout.write(u'.')
            sys.stdout.flush()
            # logger.info(u'.')
            # print(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)
            elapsed += delta
            if elapsed > maxtime:
                state = u'TIMEOUT'

        if state == u'TIMEOUT':
            self.app.print_error(u'- TIMEOUT -')
        elif state == u'FAILURE':
            self.app.print_error(u'- ERROR -')

        print(u'END')
