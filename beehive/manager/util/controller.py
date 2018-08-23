'''
Created on Sep 22, 2017

@author: darkbk
'''
import binascii
import json
import urllib

import yaml
import os
import textwrap
import sys

from beecell.paramiko_shell.shell import ParamikoShell
from beecell.simple import truncate, str2bool, id_gen
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
from time import sleep, time
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
from base64 import b64decode
import sh

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

#     @property
#     def _help_text(self):
#         """Returns the help text displayed when '--help' is passed."""
#
#         cmd_txt = ''
#         for label in self._visible_commands:
#             cmd = self._dispatch_map[label]
#             if len(cmd['aliases']) > 0 and cmd['aliases_only']:
#                 if len(cmd['aliases']) > 1:
#                     first = cmd['aliases'].pop(0)
#                     cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
#                         (first, ', '.join(cmd['aliases']))
#                 else:
#                     cmd_txt = cmd_txt + "  %s\n" % cmd['aliases'][0]
#             elif len(cmd['aliases']) > 0:
#                 cmd_txt = cmd_txt + "  %s (aliases: %s)\n" % \
#                     (label, ', '.join(cmd['aliases']))
#             else:
#                 cmd_txt = cmd_txt + "  %s\n" % label
#
#             if cmd['help']:
#                 cmd_txt = cmd_txt + "    %s\n\n" % cmd['help']
#             else:
#                 cmd_txt = cmd_txt + "\n"
#
#         if len(cmd_txt) > 0:
#             txt = '''%s
#
# commands:
# %s
#
#
#         ''' % (self._meta.description, cmd_txt)
#         else:
#             txt = self._meta.description
#
#         return textwrap.dedent(txt)
    
    def _get_config(self, config):
        val = getattr(self.app.pargs, config, None)
        return val
        #if config in self.app.pargs.__dict__:
        #    return self.app.pargs.__dict__[config]
        #else:
        #    return None
    
    def _parse_args(self):
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
        self.notruncate = getattr(self.app.pargs, u'notruncate', None)
        self.truncate = getattr(self.app.pargs, u'truncate', None)

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

        if self.notruncate is True:
            self.notruncate = self.app._meta.notruncate
            setattr(self.app._parsed_args, u'notruncate', self.notruncate)
        if self.truncate is not None:
            self.truncate = self.app._meta.truncate
            setattr(self.app._parsed_args, u'truncate', self.truncate)

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
    
    def __tabularprint(self, data, table_style, headers=None, other_headers=None, fields=None, maxsize=20,
                       separator=u'.', transform={}, print_header=True):
        if data is None:
            data = u'-'
        if not isinstance(data, list):
            values = [data]
        else:
            values = data
        # if headers is None:
        #     headers = [u'id', u'name']
        if headers is not None and other_headers is not None:
            headers.extend(other_headers)
        table = []
        if fields is None:
            fields = headers
        # idx = 0
        for item in values:
            raw = []
            if isinstance(item, dict):
                for key in fields:
                    val = self.__multi_get(item, key, separator=separator)
                    raw.append(truncate(val, maxsize))
            else:
                raw.append(truncate(item, maxsize))
            for k, func in transform.items():
                raw_item = headers.index(k)
                raw[raw_item] = func(raw[raw_item])

            table.append(raw)
        if print_header is True:
            print(tabulate(table, headers=headers, tablefmt=table_style))
        else:
            print(tabulate(table, tablefmt=table_style))
    
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
    def result(self, data, other_headers=[], headers=None, key=None, fields=None, details=False, maxsize=60,
               key_separator=u'.', format=None, table_style=u'simple', transform={}, print_header=True):
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
        :param transform: dict with function to apply to columns set in headers [default={}]
        :param print_header: if True print table header [default=True]
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
                    if self.notruncate is True:
                        maxsize = 400
                    if self.truncate is not None:
                        maxsize = int(self.truncate)
                    if u'page' in orig_data:
                        print(u'Page: %s' % orig_data[u'page'])
                        print(u'Count: %s' % orig_data[u'count'])
                        print(u'Total: %s' % orig_data[u'total'])
                        print(u'Order: %s %s' % (orig_data.get(u'sort').get(u'field'), 
                                                 orig_data.get(u'sort').get(u'order')))
                        print(u'')               
                    self.__tabularprint(data, table_style, other_headers=other_headers, headers=headers, fields=fields,
                                        maxsize=maxsize, separator=key_separator, transform=transform,
                                        print_header=print_header)
                    
        elif self.format == u'doc':
            print(data)
    
    def output(self, data, color=u'WHITEonBLACK'):
        self.app.print_output(data, color=color)
    
    def error(self, error):
        self.app.print_error(error)
    
    def load_config(self, file_config):
        """Load dict from a json or yaml formatted file.

        :param file_config: file name
        :return: data
        :rtype: dict
        """
        f = open(file_config, u'r')
        data = f.read()
        extension = file_config[-4:].lower()
        if extension == 'json':
            data = json.loads(data)
        elif extension == 'yaml':
            data = yaml.load(data)
        elif extension == '.yml':
            data = yaml.load(data)
        else:
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

    def cache_data_on_disk(self, key, data):
        """Cache data on a file.

        :param key: key to cache
        :param data: data to cache
        :return: data
        :rtype: dict
        """
        homedir = os.path.expanduser(u'~')
        file_name = u'%s/.beehive/.cache.%s' % (homedir, key)
        f = open(file_name, u'w')
        f.write(json.dumps(data))
        f.close()

    def read_cache_from_disk(self, key):
        """Load data from a file.

        :param key: key to read from cache
        :return: data
        :rtype: dict
        """
        try:
            homedir = os.path.expanduser(u'~')
            file_name = u'%s/.beehive/.cache.%s' % (homedir, key)
            f = open(file_name, u'r')
            data = f.read()
            f.close()
            return json.loads(data)
        except:
            return {}

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

    def get_arg(self, default=None, name=None, keyvalue=False, required=False, note=u''):
        """Get arguments from command line. Arguments can be positional or key/value. Example::

            arg1 arg2 key1=val1

        **arg1** and **arg2** are positional, **key1** is key/value. To read this value correctly use::

            arg1 = get_arg(name=u'arg1')
            arg2 = get_arg(name=u'arg2')
            arg3 = get_arg(name=u'key1', default=u'value1', keyvalue=True)

        :param default: default value for keyvalue argument
        :param name: argument name
        :param keyvalue: if True argument is keyvalue, if False argument i postional
        :param required: if True a keyvalue arg is required
        :param note: additional note to print when field is not provided
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
            if required is True and name not in kvargs:
                raise Exception(u'Param %s=.. is required. %s' % (name, note))
            else:
                item = kvargs.get(name, default)
            return item

        arg = None
        try:
            arg = self.app.args.pop(0)
        except:
            if default is not None:
                arg = default
            elif name is not None:
                raise Exception(u'Param %s is required. %s' % (name, note))
        return arg

    def get_list_default_arg(self):
        """Get default arguments for list. size, page, field, order

        :return:
        """
        size = self.get_arg(name=u'size', keyvalue=True, default=10)
        page = self.get_arg(name=u'page', keyvalue=True, default=0)
        field = self.get_arg(name=u'field', keyvalue=True, default=u'id')
        order = self.get_arg(name=u'order', keyvalue=True, default=u'DESC')
        data = {
            u'size': size,
            u'page': page,
            u'field': field,
            u'order': order
        }
        return data

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
        if getattr(self.app.pargs, u'cmds', False) is True:
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
    def split_arg(self, key, default=None, keyvalue=True, required=False, splitWith=u',',):
        splitList = []
        
        values = self.get_arg(name=key, default=default, keyvalue=keyvalue, required=required)     
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

            authtype = config[u'authtype']

            user = config.get(u'user', None)
            pwd = None
            secret = None
            if user is None:
                raise Exception(u'CMP User must be specified')

            if authtype == u'keyauth':
                pwd = config.get(u'pwd', None)
                if pwd is None:
                    raise Exception(u'CMP User password must be specified')
            elif authtype == u'oauth2':
                secret = config.get(u'secret', None)
                if secret is None:
                    raise Exception(u'CMP User secret must be specified')

            # if user is not None:
            #     pwd = config.get(u'pwd', None)
            # else:
            #     domain = config.get(u'domain', u'local')
            #     user = u'%s@%s' % (sh.id(u'-u', u'-n').rstrip(), domain)
            #     pwd = None

            # client_config = config.get(u'oauth2-client', None)
            self.client = BeehiveApiClient(config[u'endpoint'],
                                           authtype,
                                           user,
                                           pwd,
                                           secret,
                                           config[u'catalog'],
                                           client_config=self.app.oauth2_client,
                                           key=self.key)
            # get token
            self.client.uid, self.client.seckey = self.get_token()

            if self.client.uid is None:
                # create token
                try:
                    self.client.create_token()
                except BeehiveApiClientError as ex:
                    if ex.code == 400:
                        self.client.uid, self.client.seckey = u'', u''
                        logger.warn(u'Authorization token can not be created')
                    else:
                        raise

                # set token
                self.save_token(self.client.uid, self.client.seckey)

    def _call(self, uri, method, data=u'', headers=None, timeout=30, silent=False):
        try:
            # make request
            resp = self.client.invoke(self.subsystem, uri, method, data=data, other_headers=headers, parse=True,
                                      timeout=timeout, silent=silent, print_curl=True)
        except BeehiveApiClientError as ex:
            raise Exception(ex.value)
        finally:
            # set token3
            if self.client.uid is not None:
                self.save_token(self.client.uid, self.client.seckey)

        return resp

    def get_job_state(self, jobid):
        try:
            res = self._call(u'%s/worker/tasks/%s' % (self.baseuri, jobid), u'GET', silent=True)
            state = res.get(u'task_instance').get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                data = self.app.colored_text.error(u'%s ..' % res[u'task_instance'][u'traceback'][-1])
                sys.stdout.write(data)
                sys.stdout.flush()
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
            data = self.app.colored_text.error(u'..TIMEOUT..')
            sys.stdout.write(data)
            sys.stdout.flush()
        elif state == u'FAILURE':
            # data = self.colored_text.error(u'- ERROR -')
            # sys.stdout.write(data)
            # sys.stdout.flush()
            pass

        print(u'END')

    def ssh2node(self, host_id=None, host_ip=None, host_name=None, user=None, key_file=None, key_string=None):
        """ssh to a node

        :param host: host ip address
        :param user: ssh user
        :param key_file: private ssh key file [optional]
        :param key_string: private ssh key string [optional]
        :return:
        """
        subsystem = self.subsystem
        self.subsystem = u'ssh'

        # get ssh node
        # if group_oid is not None:
        #     data = {u'group_oid': group_oid}
        data = {}
        uri = u'/v1.0/gas/sshnodes'
        if host_ip is not None:
            data[u'ip_address'] = host_ip
        elif host_name is not None:
            uri = u'/v1.0/gas/sshnodes/%s' % host_name
        elif host_id is not None:
            uri = u'/v1.0/gas/sshnodes/%s' % host_id
        sshnode = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True))
        if host_id is not None or host_name is not None:
            sshnode = sshnode.get(u'sshnode', None)
        else:
            sshnode = sshnode.get(u'sshnodes', [])
            if len(sshnode) == 0:
                name = host_ip
                if name is None:
                    name = host_name
                raise Exception(u'Host %s not found in managed ssh nodes' % name)
            sshnode = sshnode[0]

        # get ssh user
        data = {
            u'node': sshnode[u'id'],
            u'username': user
        }
        uri = u'/v1.0/gas/sshusers'
        sshuser = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True)).get(u'sshusers', [])
        if len(sshuser) == 0:
            raise Exception(u'Host %s user %s not found' % (sshnode[u'name'], user))

        sshuser = sshuser[0]

        # get ssh ksy
        if key_file is None and key_string is None:
            data = {
                u'user_oid': sshuser[u'id']
            }
            uri = u'/v1.0/gas/sshkeys'
            sshkey = self._call(uri, u'GET', data=urllib.urlencode(data, doseq=True)).get(u'sshkeys', [])[0]

            priv_key = sshkey.get(u'priv_key')
            key_string = b64decode(priv_key)

        ssh_session_id = id_gen()
        start_time = time()

        # audit function
        def pre_login():
            data = {
                u'action': u'login',
                u'action_id': ssh_session_id,
                u'params': {
                    u'user': {
                        u'key': sshkey[u'uuid'],
                        u'name': sshuser[u'username']
                    }
                }
            }
            uri = u'/v1.0/gas/sshnodes/%s/action' % sshnode[u'id']
            action = self._call(uri, u'PUT',  data=data)
            logger.debug(u'Send action: %s' % action)

        def post_logout(status):
            elapsed = round(time() - start_time, 2)

            data = {
                u'action': u'logout',
                u'action_id': ssh_session_id,
                u'status': status,
                u'params': {
                    u'user': {
                        u'key': sshkey[u'uuid'],
                        u'name': sshuser[u'username']
                    },
                    u'elapsed': elapsed
                }
            }
            uri = u'/v1.0/gas/sshnodes/%s/action' % sshnode[u'id']
            action = self._call(uri, u'PUT', data=data)
            logger.debug(u'Send action: %s' % action)

        client = ParamikoShell(sshnode[u'ip_address'], user, keyfile=key_file, keystring=key_string,
                               pre_login=pre_login, post_logout=post_logout)
        client.run()

        self.subsystem = subsystem
